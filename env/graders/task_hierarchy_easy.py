"""Grader for hierarchy_easy — Support Agent handles billing, Supervisor approves."""
from typing import Any

def grade(session_state: dict[str, Any]) -> float:
    action_log = session_state.get("action_log", [])
    ticket = session_state.get("ticket") or {}
    history = session_state.get("history", [])
    hierarchy = session_state.get("hierarchy_state", {})

    if not action_log or not ticket:
        return 0.0

    score = 0.0
    weights = {"closed": 0.20, "resolution": 0.25, "supervisor_reviewed": 0.20,
               "no_manager": 0.15, "info_gathered": 0.10, "tone": 0.10}

    roles = [a.get("role", "support_agent") for a in action_log]
    action_types = [a["action_type"] for a in action_log]
    agent_text = " ".join(m.get("content", "").lower() for m in history if m.get("role") == "agent")

    # 1. Ticket was closed
    if action_types[-1] in ("close", "supervisor_approve") or "close" in action_types:
        score += weights["closed"]

    # 2. Resolution language present
    expected = ticket.get("expected_resolution_type", "")
    keywords_map = {
        "refund_initiated": ["refund", "reimburse", "credit", "money back"],
        "billing_clarification": ["clarif", "explain", "correct", "update", "resolve"],
    }
    keywords = keywords_map.get(expected, [])
    if any(kw in agent_text for kw in keywords):
        score += weights["resolution"]
    elif "close" in action_types:
        score += weights["resolution"] * 0.3

    # 3. Supervisor reviewed at least once
    if "supervisor" in roles or hierarchy.get("supervisor_reviews", 0) > 0:
        score += weights["supervisor_reviewed"]

    # 4. No manager needed (ideal for easy)
    if "manager" not in roles and hierarchy.get("manager_interventions", 0) == 0:
        score += weights["no_manager"]

    # 5. Required info gathered
    import re
    _EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", re.IGNORECASE)
    all_text = " ".join(m.get("content", "") for m in history)
    required = ticket.get("required_info_before_close", [])
    gathered = sum(1 for i in required if (i == "account_email" and _EMAIL_RE.search(all_text)) or i != "account_email")
    if required:
        score += weights["info_gathered"] * (gathered / len(required))
    else:
        score += weights["info_gathered"]

    # 6. Tone check
    sentiment = session_state.get("sentiment", 0.0)
    if sentiment >= 0:
        score += weights["tone"]
    elif sentiment >= -0.3:
        score += weights["tone"] * 0.5

    if len(agent_text) < 60:
        score *= 0.8

    return round(min(score, 1.0), 4)
