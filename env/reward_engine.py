"""
Reward engine — measures conversational quality and problem-solving.

Signals:
  - Tone (20%):       VADER sentiment on agent messages
  - Resolution (40%): Keyword-category match on CLOSE/ESCALATE
  - Efficiency (20%): Steps used vs max_steps
  - Accuracy (20%):   Required info gathered before closing

Penalties (applied before clamping):
  - Unnecessary escalation of low/medium priority: -0.3
  - Loop detection via TF-IDF cosine + char similarity: -0.1
  - Contradiction (claimed done then asked for info): -0.15
"""

from difflib import SequenceMatcher
import re
from typing import List

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

from env.models import Action, ActionType, Message, Reward

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
            "info_gathering_bonus": info_gathering_bonus,
            "is_terminal": is_terminal,
        },
    )
