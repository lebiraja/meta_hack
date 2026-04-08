"""
Grader for Task Medium — Multi-turn Complaint Handling.

Deterministic 0.0–1.0 score. Checks:
  1. Info-gathering step detected (REQUEST_INFO used, or agent asked for ID/email)
  2. Resolution attempted before closing
  3. Customer sentiment didn't crash below -0.5
  4. Conversation was multi-turn (≥3 exchanges)
  5. Required info was gathered
"""

import re
from typing import Any

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", re.IGNORECASE)
_ID_QUESTION_RE = re.compile(
    r"\b(?:order\s*(?:id|number)|account\s*(?:id|email|username)|can\s+you\s+(?:share|provide|give)|what\s+is\s+your)\b",
    re.IGNORECASE,
)


def grade(session_state: dict[str, Any]) -> float:
    action_log: list[dict] = session_state.get("action_log", [])
    ticket: dict = session_state.get("ticket") or {}
    history: list[dict] = session_state.get("history", [])
    sentiment: float = session_state.get("sentiment", 0.0)

    if not action_log or not ticket:
        return 0.0

    score = 0.0
    weights = {
        "info_gathered": 0.30,
        "resolution_attempted": 0.30,
        "sentiment_ok": 0.20,
        "multi_turn": 0.10,
        "required_info": 0.10,
    }

    action_types = [a["action_type"] for a in action_log]
    agent_texts = [m.get("content", "") for m in history if m.get("role") == "agent"]
    agent_full_text = " ".join(agent_texts).lower()

    # ── 1. Info gathering detected ────────────────────────────────────────────
    info_gathered = False
    if "request_info" in action_types:
        info_gathered = True
    elif any(_ID_QUESTION_RE.search(t) for t in agent_texts):
        info_gathered = True
    elif _EMAIL_RE.search(" ".join(m.get("content", "") for m in history)):
        info_gathered = True

    if info_gathered:
        score += weights["info_gathered"]

    # ── 2. Resolution attempted ───────────────────────────────────────────────
    resolution_keywords = [
        "fix", "resolv", "solution", "try", "steps", "workaround",
        "reset", "unlock", "access", "update", "patch", "reinstall",
        "here's", "please follow", "can you try",
    ]
    resolution_attempted = any(kw in agent_full_text for kw in resolution_keywords)
    last_action = action_log[-1]["action_type"] if action_log else ""

    if resolution_attempted or last_action in ("close",):
        score += weights["resolution_attempted"]
    elif last_action == "escalate":
        # Escalation on medium task is allowed but not ideal
        score += weights["resolution_attempted"] * 0.4

    # ── 3. Sentiment didn't crash ─────────────────────────────────────────────
    if sentiment >= -0.5:
        score += weights["sentiment_ok"]
    elif sentiment >= -0.7:
        score += weights["sentiment_ok"] * 0.5

    # ── 4. Multi-turn conversation ────────────────────────────────────────────
    total_turns = len(history)
    if total_turns >= 4:
        score += weights["multi_turn"]
    elif total_turns >= 2:
        score += weights["multi_turn"] * 0.5

    # ── 5. Required info gathered ─────────────────────────────────────────────
    all_text = " ".join(m.get("content", "") for m in history)
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
        score += weights["required_info"] * (gathered / len(required))
    else:
        score += weights["required_info"]

    return round(min(score, 1.0), 4)
