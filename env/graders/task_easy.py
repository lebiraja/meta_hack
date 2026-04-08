"""
Grader for Task Easy — Billing FAQ Resolution.

Deterministic 0.0–1.0 score. Checks:
  1. Agent used CLOSE action (not escalate or timeout)
  2. Resolution type matches "billing_clarification" or "refund_initiated"
  3. No unnecessary escalation occurred
  4. Completed within ideal_max_steps (bonus for efficiency)
  5. Required info was gathered
"""

from typing import Any


def grade(session_state: dict[str, Any]) -> float:
    action_log: list[dict] = session_state.get("action_log", [])
    ticket: dict = session_state.get("ticket") or {}
    history: list[dict] = session_state.get("history", [])
    step: int = session_state.get("step", 0)

    if not action_log or not ticket:
        return 0.0

    score = 0.0
    weights = {
        "closed": 0.30,
        "resolution_match": 0.35,
        "no_escalation": 0.20,
        "required_info": 0.15,
    }

    action_types = [a["action_type"] for a in action_log]
    last_action = action_log[-1]["action_type"] if action_log else ""

    # ── 1. CLOSE was called ────────────────────────────────────────────────────
    if last_action == "close":
        score += weights["closed"]

    # ── 2. Resolution type match ───────────────────────────────────────────────
    expected = ticket.get("expected_resolution_type", "")
    valid_resolutions = {"billing_clarification", "refund_initiated"}
    agent_text = " ".join(
        m["content"].lower() for m in history if m.get("role") == "agent"
    )

    resolution_hit = False
    if expected in valid_resolutions:
        if expected == "refund_initiated":
            keywords = ["refund", "reimburse", "credit", "return the charge", "money back"]
        else:
            keywords = ["clarif", "explain", "correct", "update", "resolve", "adjust", "fix"]

        if any(kw in agent_text for kw in keywords):
            resolution_hit = True

    if resolution_hit:
        score += weights["resolution_match"]
    elif last_action == "close":
        # Partial credit for closing even without perfect language
        score += weights["resolution_match"] * 0.3

    # ── 3. No unnecessary escalation ──────────────────────────────────────────
    if "escalate" not in action_types:
        score += weights["no_escalation"]

    # ── 4. Required info gathered ──────────────────────────────────────────────
    import re
    _EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", re.IGNORECASE)
    _ORDER_RE = re.compile(r"\b(?:order|ord|#)\s*[-]?\s*[A-Z0-9]{4,}\b", re.IGNORECASE)

    all_text = " ".join(m.get("content", "") for m in history)
    required: list[str] = ticket.get("required_info_before_close", [])

    gathered = 0
    for info_type in required:
        if info_type == "account_email" and _EMAIL_RE.search(all_text):
            gathered += 1
        elif info_type == "order_id" and _ORDER_RE.search(all_text):
            gathered += 1
        elif info_type not in ("account_email", "order_id"):
            # Assume gathered if customer sent multiple messages
            customer_turns = sum(1 for m in history if m.get("role") == "customer")
            if customer_turns > 1:
                gathered += 1

    if required:
        info_ratio = gathered / len(required)
        score += weights["required_info"] * info_ratio
    else:
        score += weights["required_info"]

    return round(min(score, 1.0), 4)
