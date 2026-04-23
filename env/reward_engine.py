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
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from env.models import Action, ActionType, Message, Reward
from env.llm_judge import get_llm_judge

_analyzer = SentimentIntensityAnalyzer()

# Module-level TF-IDF singleton — reused across all calls
_tfidf = TfidfVectorizer()

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
    Detects repeated agent messages via TF-IDF cosine similarity
    AND character-level SequenceMatcher ratio.
    Returns -0.1 if either threshold exceeded.
    """
    agent_msgs = _agent_messages(history)
    if len(agent_msgs) < 2:
        return 0.0
    last_two = agent_msgs[-2:]
    if not all(m.strip() for m in last_two):
        return 0.0

    char_sim = SequenceMatcher(None, last_two[0], last_two[1]).ratio()
    try:
        vec = _tfidf.fit_transform(last_two)
        cos_sim = cosine_similarity(vec[0], vec[1])[0][0]
        return -0.1 if (cos_sim > 0.80 or char_sim > 0.85) else 0.0
    except Exception:
        return -0.1 if char_sim > 0.85 else 0.0


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
# Single-Agent Step Reward (Round 1 backward compat)
# ═══════════════════════════════════════════════════════════════════════════════

def compute_step_reward(
    action: Action,
    ticket: dict,
    history: List[Message],
    steps_used: int,
    max_steps: int,
    is_terminal: bool,
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
    ignored_feedback_penalty = 0.0
    if hierarchy_state and role == "support_agent":
        feedback_history = hierarchy_state.get("supervisor_feedback_history", [])
        if len(feedback_history) > 0 and tone_msg:
            # If supervisor gave feedback but agent's response doesn't reflect it
            last_feedback = feedback_history[-1].lower()
            if last_feedback and len(last_feedback) > 10:
                # Simple check: does the agent's message address the feedback?
                feedback_words = set(last_feedback.split())
                msg_words = set(tone_msg.lower().split())
                overlap = len(feedback_words & msg_words)
                if overlap < 2:
                    ignored_feedback_penalty = -0.15

    # ── Unnecessary manager escalation penalty ─────────────────────────────────
    unnecessary_manager_penalty = 0.0
    if role == "supervisor" and action.action_type == ActionType.SUPERVISOR_ESCALATE:
        if ticket.get("priority") in ("low", "medium"):
            unnecessary_manager_penalty = -0.20

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

    # Supervisor role reward
    l2_raw = (
        0.35 * oversight_score
        + 0.30 * (1.0 + escalation_penalty + unnecessary_manager_penalty)
        + 0.20 * policy_adherence_score
        + 0.15 * (1.0 if steps_used <= ideal_steps else 0.5)
    )
    role_rewards["supervisor"] = float(np.clip(l2_raw, 0.0, 1.0))

    # Manager role reward
    l3_raw = (
        0.40 * decision_quality_score
        + 0.30 * (resolution_llm_score if is_terminal else 0.5)
        + 0.30 * (1.0 if is_terminal else 0.0)
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
            "is_terminal": is_terminal,
            "role": role,
        },
    )
