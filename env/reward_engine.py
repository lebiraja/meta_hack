"""
Reward engine — hybrid dense reward system for single-agent and hierarchical modes.

Combines rule-based signals (efficiency, accuracy, loop detection) with
LLM-as-Judge evaluations (empathy, policy adherence, resolution quality).
Includes role-specific rewards for the 3-level hierarchy.

Signals:
  Single-agent mode (backward compat):
    - Tone (20%):       VADER sentiment on agent messages
    - Resolution (40%): Keyword-category match on CLOSE/ESCALATE
    - Efficiency (20%): Steps used vs max_steps
    - Accuracy (20%):   Required info gathered before closing

  Hierarchy mode:
    Overall: resolution(0.25) + sla(0.15) + satisfaction(0.15) + policy(0.15)
             + accuracy(0.10) + efficiency(0.10) + hierarchy_effectiveness(0.10)
    Per-role: see compute_hierarchy_reward()

Penalties (applied before clamping):
  - Unnecessary escalation of low/medium priority: -0.3
  - Loop detection via TF-IDF cosine + char similarity: -0.1
  - Contradiction (claimed done then asked for info): -0.15
  - Policy violation (agent violates active policy): -0.25
  - Keyword stuffing (high keyword density without substance): -0.30
  - Ignored supervisor feedback: -0.15
  - Unnecessary manager escalation: -0.20
"""

from difflib import SequenceMatcher
import re
from typing import List, Optional, Dict, Any

import numpy as np
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from env.models import Action, ActionType, Message, Reward
from env.llm_judge import get_llm_judge

_analyzer = SentimentIntensityAnalyzer()

# Resolution signal keywords per expected_resolution_type
_RESOLUTION_SIGNALS: dict[str, list[str]] = {
    "refund_initiated": [
        "refund", "reimburse", "credit", "return the charge",
        "process a refund", "issue a refund", "money back",
    ],
    "billing_clarification": [
        "clarif", "explain", "adjust", "correct", "update",
        "fix", "change", "resolve", "address",
    ],
    "technical_fix_provided": [
        "fix", "resolv", "solution", "workaround", "update",
        "patch", "restart", "reinstall", "clear cache", "try",
        "follow these steps", "here's how",
    ],
    "account_access_restored": [
        "reset", "unlock", "restore", "access", "re-enable",
        "send you a link", "recover",
    ],
    "escalated_to_engineering": [
        "escalat", "engineering", "senior", "technical team",
        "on-call", "specialist", "transfer",
    ],
    "escalated_to_security": [
        "escalat", "security team", "incident response",
        "lockdown", "revoke", "specialist",
    ],
}

# Info patterns for accuracy scoring
_INFO_PATTERNS: dict[str, re.Pattern] = {
    "account_email": re.compile(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", re.IGNORECASE),
    "order_id": re.compile(r"\b(?:order|ord|#)\s*[-]?\s*[A-Z0-9]{4,}\b", re.IGNORECASE),
    "account_username": re.compile(
        r"\b(?:username|user\s*name|account\s*name|login)\b.*?:\s*\S+", re.IGNORECASE
    ),
    "device_info": re.compile(
        r"\b(?:iphone|android|ios|windows|mac|chrome|firefox|safari|app version)\b",
        re.IGNORECASE,
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# Rule-Based Components (shared by both modes)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_tone_score(message: str) -> float:
    """VADER compound score mapped from [-1, 1] → [0, 1]."""
    if not message or not message.strip():
        return 0.5
    scores = _analyzer.polarity_scores(message)
    return (scores["compound"] + 1.0) / 2.0


def _agent_messages(history: List[Message]) -> List[str]:
    return [m.content for m in history if m.role == "agent"]


def compute_loop_penalty(history: List[Message]) -> float:
    """
    Detect repeated agent messages. Checks the last 4 agent messages and
    penalises any pair whose SequenceMatcher ratio exceeds 0.80. This catches
    both adjacent repeats and alternating-paraphrase loops that try to evade
    a strict adjacency check.

    Returns -0.12 if any pair is over threshold, else 0.0.
    """
    agent_msgs = [m for m in _agent_messages(history) if m and m.strip()]
    if len(agent_msgs) < 2:
        return 0.0

    window = agent_msgs[-4:]
    for i in range(len(window)):
        for j in range(i + 1, len(window)):
            if SequenceMatcher(None, window[i], window[j]).ratio() > 0.80:
                return -0.12
    return 0.0


def compute_resolution_score(
    action: Action,
    ticket: dict,
    history: List[Message],
) -> float:
    """
    On CLOSE/ESCALATE: checks agent conversation for category-matched
    resolution language. NOT keyword stuffing — requires substantive language.
    """
    if action.action_type not in (ActionType.CLOSE, ActionType.ESCALATE):
        return 0.0

    expected = ticket.get("expected_resolution_type", "")
    signals = _RESOLUTION_SIGNALS.get(expected, [])
    if not signals:
        return 0.5

    agent_text = " ".join(
        m.content.lower() for m in history if m.role == "agent"
    )
    if action.message:
        agent_text += " " + action.message.lower()
    if action.reason:
        agent_text += " " + action.reason.lower()

    matched = sum(1 for sig in signals if sig in agent_text)
    score = min(matched / max(len(signals) * 0.4, 1), 1.0)

    # Escalation tasks: ESCALATE is the correct resolution
    if expected.startswith("escalated_to") and action.action_type == ActionType.ESCALATE:
        if action.reason:
            urgency_words = [
                "sla", "critical", "outage", "urgent", "emergency",
                "breach", "down", "p0", "p1", "incident",
            ]
            if any(w in action.reason.lower() for w in urgency_words):
                return min(score + 0.5, 1.0)
        return max(score, 0.3)

    # Penalize escalation on non-escalation tasks
    if expected not in ("escalated_to_engineering", "escalated_to_security") \
            and action.action_type == ActionType.ESCALATE:
        return max(score - 0.4, 0.0)

    return score


def compute_efficiency_score(steps_used: int, max_steps: int) -> float:
    """1.0 - (steps_used / max_steps), floored at 0.0."""
    if max_steps <= 0:
        return 0.0
    return max(0.0, 1.0 - (steps_used / max_steps))


def compute_accuracy_score(history: List[Message], ticket: dict) -> float:
    """Fraction of required_info_before_close items found in conversation."""
    required: List[str] = ticket.get("required_info_before_close", [])
    if not required:
        return 1.0

    all_text = " ".join(m.content for m in history)
    gathered = 0
    for info_type in required:
        pattern = _INFO_PATTERNS.get(info_type)
        if pattern and pattern.search(all_text):
            gathered += 1
        elif info_type not in _INFO_PATTERNS:
            customer_msgs = [m for m in history if m.role == "customer"]
            if len(customer_msgs) > 1:
                gathered += 1

    return gathered / len(required)


def compute_escalation_penalty(action: Action, ticket: dict) -> float:
    """-0.3 if agent escalates a low or medium priority ticket."""
    if action.action_type != ActionType.ESCALATE:
        return 0.0
    if ticket.get("priority") in ("low", "medium"):
        return -0.3
    return 0.0


def compute_contradiction_penalty(action: Action, history: List[Message]) -> float:
    """Penalize agent for claiming resolution then asking for info already provided."""
    agent_msgs = [m.content.lower() for m in history if m.role == "agent"]
    if len(agent_msgs) < 2:
        return 0.0
    completion_claims = ["processed", "resolved", "fixed", "refund", "restored"]
    info_request_words = ["could you provide", "can you share", "please give me", "what is your"]
    last = (action.message or "").lower()
    prev_claimed_done = any(w in " ".join(agent_msgs[-3:]) for w in completion_claims)
    now_asking_info = any(w in last for w in info_request_words)
    return -0.15 if (prev_claimed_done and now_asking_info) else 0.0


def compute_premature_query_penalty(action: Action, history: List[Message]) -> float:
    """
    -0.15 if the agent fires a DB query before ever greeting the customer.

    A professional support agent always acknowledges the customer first.
    Querying the DB as the opening move is robotic, hurts empathy scores, and
    signals the model is pattern-matching identifiers rather than conversing.

    Only triggers when there are zero prior agent messages in the history, so
    legitimate second-or-later queries (after a greeting) are never penalized.
    """
    if action.action_type not in (
        ActionType.QUERY_USER_PROFILE, ActionType.QUERY_ORDER_DETAILS
    ):
        return 0.0
    prior_agent = [m for m in history if m.role == "agent" and m.content.strip()]
    if not prior_agent:
        return -0.15
    return 0.0


def compute_keyword_stuffing_penalty(message: str) -> float:
    """
    Detect and penalize keyword stuffing.
    Returns -0.30 if high keyword density detected.
    """
    if not message or len(message) < 20:
        return 0.0

    words = message.lower().split()
    if len(words) < 5:
        return 0.0

    reward_keywords = {
        "refund", "resolved", "fixed", "processed", "credit",
        "reimburse", "understand", "sorry", "apologize", "appreciate",
        "empathy", "restore", "reset", "update", "solution",
    }

    keyword_count = sum(1 for w in words if w in reward_keywords)
    density = keyword_count / len(words)

    if density > 0.20:
        return -0.30
    return 0.0


# ═══════════════════════════════════════════════════════════════════════════════
# DB Signal Helper (grounded response rewards / hallucination penalties)
# ═══════════════════════════════════════════════════════════════════════════════

# Patterns for detecting claimed facts in agent messages. Word-bounded so we
# can compare against the same pattern extracted from customer text and from DB
# values, rather than doing raw substring matching (which mis-flags legitimate
# facts that the customer already mentioned).
_FACT_PATTERNS = {
    "email": re.compile(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", re.IGNORECASE),
    "order_id": re.compile(r"\b(?:ORD|ORDER|#)[-\s]?[A-Z]{0,3}[-\s]?\d{3,}\b", re.IGNORECASE),
    # Amount: ₹NNN, Rs NNN, NNN rupees, NNN INR — require word boundary so
    # "approx 500 rupees" matches cleanly and later also matches from customer text.
    "amount": re.compile(
        r"(?:₹\s*\d{2,}|\brs\.?\s*\d{2,}\b|\b\d{2,}\s*(?:rupees?|inr)\b|\brupees?\s+\d{2,}\b)",
        re.IGNORECASE,
    ),
    "date": re.compile(
        r"\b\d{4}-\d{2}-\d{2}\b|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s+\d{1,2}\b",
        re.IGNORECASE,
    ),
}


def _normalise_claim(claim: str) -> str:
    """Normalise a pattern match so semantically-identical claims compare equal.

    Collapses whitespace, lowercases, and strips the currency symbol from
    amounts so '₹999' == 'rs 999' == '999 rupees' for comparison purposes.
    """
    c = re.sub(r"\s+", "", claim.lower())
    c = c.replace("₹", "").replace("rs.", "").replace("rs", "")
    c = c.replace("rupees", "").replace("rupee", "").replace("inr", "")
    return c.strip()


# Hard caps on DB signal totals so no combination of bonuses can dominate the
# weighted reward sum and push raw above 1.0 before clipping.
DB_TOTAL_MIN = -0.30
DB_TOTAL_MAX = 0.25

# Minimum response length (chars) required to earn the grounded-response bonus.
# Prevents the farm where the agent replies with a single DB field and claims +0.10.
_GROUNDED_MIN_LEN = 30

# Actions that legitimately "react to not_found" — only these earn the bonus.
_GOOD_NOT_FOUND_ACTIONS = None  # populated lazily to avoid import cycle


def _collect_grounded_values(retrieved_data: dict) -> List[str]:
    """Flatten every string-ish value from users + orders into one lowercase list."""
    values: List[str] = []
    users_data = retrieved_data.get("users", {}) or {}
    orders_data = retrieved_data.get("orders", {}) or {}
    for record in list(users_data.values()) + list(orders_data.values()):
        if not isinstance(record, dict):
            continue
        for v in record.values():
            if isinstance(v, list):
                values.extend(str(i).lower() for i in v if i is not None)
            elif v is not None:
                values.append(str(v).lower())
    return values


def compute_db_signals(
    action: "Action",
    ticket: dict,
    history: List[Message],
    retrieved_data: dict,
) -> dict:
    """
    Compute DB-grounding reward signals for an action step.

    Signals (all clamped; absolute values are modest so they never overwhelm
    the core reward components):

      query_match_bonus       +0.08  — queried the email/order_id the ticket is about
      wasted_query_penalty    -0.08  — queried an email/order never mentioned by the customer
      grounded_response_bonus +0.10  — cited verbatim DB data in a substantive (≥30-char) reply
      not_found_handling_bonus+0.08  — responded to a not_found with REQUEST_INFO / ESCALATE
      hallucination_penalty   -0.25  — invented a fact (amount, date, email, order-id) that is in
                                       neither the DB nor the customer's own messages

    Returns all zeros when no DB interaction has happened (backward-compatible).
    """
    from env.models import ActionType

    global _GOOD_NOT_FOUND_ACTIONS
    if _GOOD_NOT_FOUND_ACTIONS is None:
        _GOOD_NOT_FOUND_ACTIONS = {
            ActionType.REQUEST_INFO,
            ActionType.ESCALATE,
            ActionType.SUPERVISOR_ESCALATE,
        }

    signals: dict = {
        "query_match_bonus": 0.0,
        "grounded_response_bonus": 0.0,
        "not_found_handling_bonus": 0.0,
        "hallucination_penalty": 0.0,
        "wasted_query_penalty": 0.0,
    }

    at = ActionType(action.action_type)
    ticket_email = (ticket.get("customer_email") or "").lower()
    ticket_order_ids: List[str] = ticket.get("related_order_ids", []) or []
    users_data: dict = retrieved_data.get("users", {}) or {}
    orders_data: dict = retrieved_data.get("orders", {}) or {}

    customer_text = " ".join(
        m.content for m in history if m.role == "customer"
    )
    customer_text_lower = customer_text.lower()
    customer_text_upper = customer_text.upper()

    # ── Query match bonus / wasted-query penalty ──────────────────────────────
    if at == ActionType.QUERY_USER_PROFILE and action.email:
        queried_email = action.email.strip().lower()
        if ticket_email and queried_email == ticket_email:
            signals["query_match_bonus"] = 0.08
        elif queried_email and queried_email not in customer_text_lower:
            signals["wasted_query_penalty"] = -0.08

    if at == ActionType.QUERY_ORDER_DETAILS and action.order_id:
        queried_oid = action.order_id.strip().upper()
        if ticket_order_ids and queried_oid in [o.upper() for o in ticket_order_ids]:
            signals["query_match_bonus"] = 0.08
        elif queried_oid and queried_oid not in customer_text_upper:
            signals["wasted_query_penalty"] = -0.08

    # ── Not-found handling bonus ───────────────────────────────────────────────
    # Only award when retrieved_data contains at least one "not_found" sentinel
    # AND the current action is a recovery move (ask for info or escalate).
    any_not_found = (
        "not_found" in users_data.values() or "not_found" in orders_data.values()
    )
    if any_not_found and at in _GOOD_NOT_FOUND_ACTIONS:
        signals["not_found_handling_bonus"] = 0.08

    # ── Grounded response & hallucination (only on response-like actions) ─────
    response_actions = {
        ActionType.RESPOND, ActionType.CLOSE, ActionType.REQUEST_INFO,
        ActionType.MANAGER_OVERRIDE, ActionType.MANAGER_RESOLVE,
    }
    msg_text_raw = action.message or action.reason or ""
    msg_text = msg_text_raw.lower()

    if msg_text and at in response_actions:
        grounded_values = _collect_grounded_values(retrieved_data)

        # Grounded-response bonus: the reply must be substantive (≥30 chars)
        # AND cite at least one verbatim DB value (≥4 chars, to avoid rewarding
        # trivia like `499` that any reply could include).
        if grounded_values and len(msg_text_raw.strip()) >= _GROUNDED_MIN_LEN:
            if any(len(gv) >= 4 and gv in msg_text for gv in grounded_values):
                signals["grounded_response_bonus"] = 0.10

        # Hallucination: a fact pattern appears in the agent's text that is
        # present in neither the customer's messages nor the DB values. Compare
        # via _normalise_claim so "₹999" == "rs 999" == "999 rupees".
        known_claims: set[str] = set()
        for text in (customer_text_lower, " ".join(grounded_values)):
            for pat in _FACT_PATTERNS.values():
                for m in pat.finditer(text):
                    known_claims.add(_normalise_claim(m.group(0)))

        for pat in _FACT_PATTERNS.values():
            for m in pat.finditer(msg_text):
                if _normalise_claim(m.group(0)) not in known_claims:
                    signals["hallucination_penalty"] = -0.25
                    break
            if signals["hallucination_penalty"] < 0:
                break

    return signals


def _clamp_db_total(signals: dict) -> float:
    """Sum signals and clamp to [DB_TOTAL_MIN, DB_TOTAL_MAX] so the bucket can't
    overwhelm the weighted-sum reward components."""
    total = sum(v for v in signals.values() if isinstance(v, (int, float)))
    return float(np.clip(total, DB_TOTAL_MIN, DB_TOTAL_MAX))


# ═══════════════════════════════════════════════════════════════════════════════
# Single-Agent Step Reward (Round 1 backward compat)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_step_reward(
    action: Action,
    ticket: dict,
    history: List[Message],
    steps_used: int,
    max_steps: int,
    is_terminal: bool,
    retrieved_data: Optional[Dict[str, Any]] = None,
) -> Reward:
    """
    Compute shaped reward for a single step.
    Weights: resolution=0.40, tone=0.20, efficiency=0.20, accuracy=0.20
    Penalties applied before clamping to [0.0, 1.0].
    """
    tone_msg = action.message or action.reason or ""
    tone_score = compute_tone_score(tone_msg)
    loop_penalty = compute_loop_penalty(history)
    contradiction_penalty = compute_contradiction_penalty(action, history)
    stuffing_penalty = compute_keyword_stuffing_penalty(tone_msg)
    premature_query_penalty = compute_premature_query_penalty(action, history)

    if is_terminal:
        resolution_score = compute_resolution_score(action, ticket, history)
        efficiency_score = compute_efficiency_score(steps_used, max_steps)
        accuracy_score = compute_accuracy_score(history, ticket)
        escalation_penalty = compute_escalation_penalty(action, ticket)
    else:
        resolution_score = 0.0
        efficiency_score = compute_efficiency_score(steps_used, max_steps) * 0.3
        accuracy_score = compute_accuracy_score(history, ticket) * 0.5
        escalation_penalty = 0.0

    info_gathering_bonus = 0.0
    if action.action_type == ActionType.REQUEST_INFO:
        if ticket.get("required_info_before_close"):
            info_gathering_bonus = 0.1

    # DB grounding signals (all zero when no queries made)
    _rd = retrieved_data or {"users": {}, "orders": {}}
    db_signals = compute_db_signals(action, ticket, history, _rd)
    db_total = _clamp_db_total(db_signals)

    raw = (
        0.40 * resolution_score
        + 0.20 * tone_score
        + 0.20 * efficiency_score
        + 0.20 * accuracy_score
        + loop_penalty
        + contradiction_penalty
        + escalation_penalty
        + stuffing_penalty
        + info_gathering_bonus
        + premature_query_penalty
        + db_total
    )

    value = float(np.clip(raw, 0.0, 1.0))

    return Reward(
        value=value,
        resolution_score=round(resolution_score, 4),
        tone_score=round(tone_score, 4),
        efficiency_score=round(efficiency_score, 4),
        accuracy_score=round(accuracy_score, 4),
        breakdown={
            "raw": round(raw, 4),
            "loop_penalty": loop_penalty,
            "contradiction_penalty": contradiction_penalty,
            "escalation_penalty": escalation_penalty,
            "keyword_stuffing_penalty": stuffing_penalty,
            "info_gathering_bonus": info_gathering_bonus,
            "premature_query_penalty": premature_query_penalty,
            **{f"db_{k}": v for k, v in db_signals.items()},
            "is_terminal": is_terminal,
        },
    )


# ═══════════════════════════════════════════════════════════════════════════════
# Hierarchy Reward System (Round 2)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_hierarchy_reward(
    action: Action,
    ticket: dict,
    history: List[Message],
    steps_used: int,
    max_steps: int,
    is_terminal: bool,
    policy_text: str = "",
    hierarchy_state: Optional[Dict[str, Any]] = None,
    use_llm_judge: bool = True,
    retrieved_data: Optional[Dict[str, Any]] = None,
) -> Reward:
    """
    Compute the full hierarchical reward with LLM-as-Judge components.

    Overall weights:
        resolution: 0.25, sla_compliance: 0.15, satisfaction: 0.15,
        policy_adherence: 0.15, accuracy: 0.10, efficiency: 0.10,
        hierarchy_effectiveness: 0.10

    Role-specific rewards are computed in parallel and stored in role_rewards.
    """
    tone_msg = action.message or action.reason or action.feedback_to_agent or ""
    role = action.role if hasattr(action, 'role') else "support_agent"

    # ── Rule-based components ──────────────────────────────────────────────────
    tone_score = compute_tone_score(tone_msg)
    loop_penalty = compute_loop_penalty(history)
    contradiction_penalty = compute_contradiction_penalty(action, history)
    stuffing_penalty = compute_keyword_stuffing_penalty(tone_msg)
    premature_query_penalty = compute_premature_query_penalty(action, history)
    efficiency_score = compute_efficiency_score(steps_used, max_steps)
    accuracy_score = compute_accuracy_score(history, ticket)

    # ── LLM-as-Judge components ────────────────────────────────────────────────
    empathy_score = 0.5
    policy_adherence_score = 0.5
    resolution_llm_score = 0.5
    oversight_score = 0.5
    decision_quality_score = 0.5

    if use_llm_judge:
        judge = get_llm_judge()

        # Only evaluate empathy for L1 respond/close actions
        if role == "support_agent" and tone_msg:
            empathy_score = judge.evaluate_empathy(tone_msg, history, ticket)

        # Policy adherence for L1 terminal actions
        if is_terminal and policy_text:
            policy_adherence_score = judge.evaluate_policy_adherence(
                action.action_type, tone_msg, ticket, policy_text
            )

        # Resolution quality on terminal
        if is_terminal:
            resolution_llm_score = judge.evaluate_resolution(history, ticket)

        # Supervisor oversight
        if role == "supervisor" and hierarchy_state:
            pending = hierarchy_state.get("pending_l1_action", {})
            if pending:
                oversight_score = judge.evaluate_supervisor_oversight(
                    l1_action_type=pending.get("action_type", ""),
                    l1_message=pending.get("message", ""),
                    supervisor_decision=action.action_type,
                    supervisor_feedback=action.feedback_to_agent or "",
                    ticket=ticket,
                    policy=policy_text,
                )

        # Manager decision quality
        if role == "manager" and hierarchy_state:
            escalation_reason = hierarchy_state.get("escalation_reason", "")
            decision_quality_score = judge.evaluate_manager_decision(
                manager_decision=action.action_type,
                manager_message=tone_msg,
                escalation_reason=escalation_reason,
                history=history,
                ticket=ticket,
            )

    # ── Rule-based resolution (kept for non-LLM fallback blending) ─────────────
    resolution_rule = 0.0
    escalation_penalty = 0.0
    if is_terminal:
        resolution_rule = compute_resolution_score(action, ticket, history)
        escalation_penalty = compute_escalation_penalty(action, ticket)

    # Blend rule-based and LLM resolution scores
    resolution_score = (0.4 * resolution_rule + 0.6 * resolution_llm_score) if is_terminal else 0.0

    # ── SLA compliance ─────────────────────────────────────────────────────────
    ideal_steps = ticket.get("ideal_max_steps", max_steps)
    sla_score = 1.0 if steps_used <= ideal_steps else max(0.0, 1.0 - (steps_used - ideal_steps) * 0.15)

    # ── Hierarchy effectiveness ────────────────────────────────────────────────
    hierarchy_score = 0.5  # neutral default
    if hierarchy_state:
        sup_reviews = hierarchy_state.get("supervisor_reviews", 0)
        mgr_interventions = hierarchy_state.get("manager_interventions", 0)
        l1_actions = hierarchy_state.get("support_agent_actions", 0)

        # Good: supervisor reviewed, manager only if needed
        if sup_reviews > 0:
            hierarchy_score += 0.2
        # Bad: manager intervened on easy ticket
        if mgr_interventions > 0 and ticket.get("priority") in ("low", "medium"):
            hierarchy_score -= 0.2
        # Good: L1 made progress before supervisor
        if l1_actions >= 2:
            hierarchy_score += 0.1
        hierarchy_score = max(0.0, min(1.0, hierarchy_score))

    # ── Ignored supervisor feedback penalty ────────────────────────────────────
    _STOP = {"the", "a", "an", "is", "are", "was", "be", "to", "of", "in",
             "you", "your", "for", "and", "or", "it", "this", "that", "i",
             "me", "my", "we", "our", "with", "on", "at", "by", "not",
             "please", "should", "must", "need", "more", "also", "next"}
    ignored_feedback_penalty = 0.0
    if hierarchy_state and role == "support_agent":
        feedback_history = hierarchy_state.get("supervisor_feedback_history", [])
        if len(feedback_history) > 0 and tone_msg:
            last_feedback = feedback_history[-1].lower()
            if last_feedback and len(last_feedback) > 10:
                # Check meaningful (non-stop) words from feedback appear in agent response
                fb_words = set(last_feedback.split()) - _STOP
                msg_words = set(tone_msg.lower().split()) - _STOP
                if fb_words and len(fb_words & msg_words) < 1:
                    ignored_feedback_penalty = -0.15

    # ── Unnecessary manager escalation penalty ─────────────────────────────────
    unnecessary_manager_penalty = 0.0
    if role == "supervisor" and action.action_type == ActionType.SUPERVISOR_ESCALATE:
        if ticket.get("priority") in ("low", "medium"):
            unnecessary_manager_penalty = -0.20

    # ── DB grounding signals ───────────────────────────────────────────────────
    _rd = retrieved_data or {"users": {}, "orders": {}}
    db_signals = compute_db_signals(action, ticket, history, _rd)
    db_total = _clamp_db_total(db_signals)

    # ── Compute overall raw reward ─────────────────────────────────────────────
    if is_terminal:
        raw = (
            0.25 * resolution_score
            + 0.15 * sla_score
            + 0.15 * empathy_score
            + 0.15 * policy_adherence_score
            + 0.10 * accuracy_score
            + 0.10 * efficiency_score
            + 0.10 * hierarchy_score
            + loop_penalty
            + contradiction_penalty
            + stuffing_penalty
            + escalation_penalty
            + ignored_feedback_penalty
            + unnecessary_manager_penalty
            + premature_query_penalty
            + db_total
        )
    else:
        # Non-terminal: lighter weights, focus on step-level quality
        raw = (
            0.30 * empathy_score
            + 0.20 * tone_score
            + 0.15 * efficiency_score * 0.3
            + 0.15 * accuracy_score * 0.5
            + 0.10 * hierarchy_score
            + 0.10 * policy_adherence_score
            + loop_penalty
            + stuffing_penalty
            + ignored_feedback_penalty
            + unnecessary_manager_penalty
            + premature_query_penalty
            + db_total
        )

    value = float(np.clip(raw, 0.0, 1.0))

    # ── Compute per-role rewards ───────────────────────────────────────────────
    role_rewards: Dict[str, float] = {}

    # Support Agent role reward
    l1_raw = (
        0.30 * empathy_score
        + 0.25 * accuracy_score
        + 0.25 * (resolution_llm_score if is_terminal else tone_score)
        + 0.20 * efficiency_score
    )
    role_rewards["support_agent"] = float(np.clip(l1_raw, 0.0, 1.0))

    # Supervisor role reward — escalation_penalty and unnecessary_manager_penalty
    # are both ≤0; we clamp their sum first so a single bad call can drag the
    # supervisor score down by at most 0.5 (the blended term below still leaves
    # room for a recovery signal).
    sup_decision_score = float(np.clip(
        1.0 + escalation_penalty + unnecessary_manager_penalty, 0.0, 1.0
    ))
    l2_raw = (
        0.35 * oversight_score
        + 0.30 * sup_decision_score
        + 0.20 * policy_adherence_score
        + 0.15 * (1.0 if steps_used <= ideal_steps else 0.5)
    )
    role_rewards["supervisor"] = float(np.clip(l2_raw, 0.0, 1.0))

    # Manager role reward. Previously a flat "terminal or zero" term punished
    # legitimate MANAGER_SEND_BACK actions. We now use decision quality (from
    # the LLM judge) as the primary signal and give a smaller bonus for actually
    # resolving vs deferring, without crushing the score for a correct deferral.
    manager_act_type = ActionType(action.action_type) if hasattr(action, "action_type") else None
    if manager_act_type in {ActionType.MANAGER_RESOLVE, ActionType.MANAGER_OVERRIDE}:
        resolve_bonus = 1.0
    elif manager_act_type == ActionType.MANAGER_SEND_BACK:
        resolve_bonus = 0.7  # legitimate deferral, still valuable
    else:
        resolve_bonus = 0.5  # non-manager action, neutral default
    l3_raw = (
        0.45 * decision_quality_score
        + 0.30 * (resolution_llm_score if is_terminal else 0.5)
        + 0.25 * resolve_bonus
    )
    role_rewards["manager"] = float(np.clip(l3_raw, 0.0, 1.0))

    return Reward(
        value=value,
        resolution_score=round(resolution_score, 4),
        tone_score=round(tone_score, 4),
        efficiency_score=round(efficiency_score, 4),
        accuracy_score=round(accuracy_score, 4),
        empathy_score=round(empathy_score, 4),
        oversight_score=round(oversight_score, 4),
        decision_quality_score=round(decision_quality_score, 4),
        policy_adherence_score=round(policy_adherence_score, 4),
        role_rewards=role_rewards,
        breakdown={
            "raw": round(raw, 4),
            "resolution_rule": round(resolution_rule, 4),
            "resolution_llm": round(resolution_llm_score, 4),
            "sla_score": round(sla_score, 4),
            "hierarchy_score": round(hierarchy_score, 4),
            "loop_penalty": loop_penalty,
            "contradiction_penalty": contradiction_penalty,
            "escalation_penalty": escalation_penalty,
            "keyword_stuffing_penalty": stuffing_penalty,
            "ignored_feedback_penalty": ignored_feedback_penalty,
            "unnecessary_manager_penalty": unnecessary_manager_penalty,
            "premature_query_penalty": premature_query_penalty,
            **{f"db_{k}": v for k, v in db_signals.items()},
            "is_terminal": is_terminal,
            "role": role,
        },
    )
