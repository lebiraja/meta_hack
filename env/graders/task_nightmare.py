"""
Grader for Task Nightmare — Multi-Issue Compound Tickets.

Deterministic 0.0–1.0 score. Checks:
  1. Info gathering (required info collected before close)
  2. Resolution attempted with appropriate language
  3. Multi-turn conversation (agent asked, customer responded)
  4. Sentiment stayed stable (customer not driven off)
  5. Closed or escalated (didn't time out)
"""

import re
from typing import Any

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", re.IGNORECASE)
_ID_QUESTION_RE = re.compile(
    r"\b(?:order\s*(?:id|number)|account\s*(?:id|email|username)|can\s+you\s+(?:share|provide|give)|what\s+is\s+your)\b",
    re.IGNORECASE,
)
_RESOLUTION_KEYWORDS = [
    "refund", "credit", "reimburse", "fix", "resolv", "solution",
    "reset", "unlock", "restore", "access", "escalat", "transfer",
    "workaround", "steps", "here's", "update", "patch",
]


def grade(session_state: dict[str, Any]) -> float:
    action_log: list[dict] = session_state.get("action_log", [])
    ticket: dict = session_state.get("ticket") or {}
    history: list[dict] = session_state.get("history", [])
    sentiment: float = session_state.get("sentiment", 0.0)

    if not action_log or not ticket:
        return 0.0

    weights = {
        "info_gathered": 0.30,
        "resolution_attempted": 0.25,
        "multi_turn": 0.15,
        "sentiment_ok": 0.15,
        "terminal_action": 0.15,
    }

    score = 0.0
    action_types = [a["action_type"] for a in action_log]
    agent_texts = [m.get("content", "") for m in history if m.get("role") == "agent"]
    agent_full_text = " ".join(agent_texts).lower()
    all_text = " ".join(m.get("content", "") for m in history)

    # ── 1. Required info gathered ─────────────────────────────────────────────
    required: list[str] = ticket.get("required_info_before_close", [])
    gathered = 0
    for info_type in required:
        if info_type == "account_email" and _EMAIL_RE.search(all_text):
            gathered += 1
        elif info_type not in ("account_email",):
            customer_turns = sum(1 for m in history if m.get("role") == "customer")
            if customer_turns > 1:
                gathered += 1

    if required:
        score += weights["info_gathered"] * (gathered / len(required))
    else:
        score += weights["info_gathered"]

    # ── 2. Resolution attempted ───────────────────────────────────────────────
    if any(kw in agent_full_text for kw in _RESOLUTION_KEYWORDS):
        score += weights["resolution_attempted"]
    elif action_types and action_types[-1] in ("close", "escalate"):
        score += weights["resolution_attempted"] * 0.3

    # ── 3. Multi-turn (nightmare should take several steps) ────────────────────
    total_turns = len(history)
    if total_turns >= 6:
        score += weights["multi_turn"]
    elif total_turns >= 4:
        score += weights["multi_turn"] * 0.6
    elif total_turns >= 2:
        score += weights["multi_turn"] * 0.3

    # ── 4. Customer sentiment didn't crash ────────────────────────────────────
    if sentiment >= -0.3:
        score += weights["sentiment_ok"]
    elif sentiment >= -0.6:
        score += weights["sentiment_ok"] * 0.5

    # ── 5. Terminal action taken (didn't just time out) ────────────────────────
    last_action = action_types[-1] if action_types else ""
    if last_action in ("close", "escalate"):
        score += weights["terminal_action"]

    # Penalty: very short agent text
    if len(agent_full_text) < 80:
        score *= 0.8

    return round(min(score, 1.0), 4)
