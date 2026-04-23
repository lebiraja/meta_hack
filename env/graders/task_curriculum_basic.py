"""Grader for curriculum_basic — Stage 1/4: Support Agent only, simple tickets."""
from typing import Any


def grade(session_state: dict[str, Any]) -> float:
    """
    Dense, forgiving grader for Stage 1.
    Rewards empathy, info-gathering, and clean resolution.
    No hierarchy expected — just L1 doing its job well.
    """
    action_log = session_state.get("action_log", [])
    ticket = session_state.get("ticket") or {}
    history = session_state.get("history", [])

    if not action_log or not ticket:
        return 0.0

    score = 0.0
    weights = {"closed": 0.25, "resolution": 0.30, "empathy": 0.20,
               "info_gathered": 0.15, "efficiency": 0.10}

    action_types = [a["action_type"] for a in action_log]
    agent_text = " ".join(
        m.get("content", "").lower() for m in history if m.get("role") == "agent"
    )

    # 1. Ticket was closed
    if "close" in action_types:
        score += weights["closed"]
    elif action_types[-1] in ("close", "supervisor_approve"):
        score += weights["closed"] * 0.8

    # 2. Resolution language present
    expected = ticket.get("expected_resolution_type", "")
    keywords_map = {
        "refund_initiated": ["refund", "reimburse", "credit", "money back", "processed"],
        "billing_clarification": ["clarif", "explain", "correct", "update", "resolve", "fixed"],
    }
    keywords = keywords_map.get(expected, ["resolv", "fix", "solution"])
    if any(kw in agent_text for kw in keywords):
        score += weights["resolution"]
    elif "close" in action_types:
        score += weights["resolution"] * 0.4

    # 3. Empathy shown
    empathy_words = ["understand", "sorry", "apologi", "hear", "frustrat",
                     "inconvenien", "appreciate", "help", "assist"]
    empathy_count = sum(1 for w in empathy_words if w in agent_text)
    if empathy_count >= 3:
        score += weights["empathy"]
    elif empathy_count >= 1:
        score += weights["empathy"] * 0.6
    else:
        score += weights["empathy"] * 0.1

    # 4. Info gathered
    if "request_info" in action_types:
        score += weights["info_gathered"]
    elif len([m for m in history if m.get("role") == "customer"]) > 1:
        score += weights["info_gathered"] * 0.5

    # 5. Efficiency (resolved in ≤ 4 steps)
    total_steps = len(action_log)
    if total_steps <= 3:
        score += weights["efficiency"]
    elif total_steps <= 5:
        score += weights["efficiency"] * 0.6

    # Penalty: hostile tone cancels out good behaviour
    sentiment: float = session_state.get("sentiment", 0.0)
    if sentiment < -0.5:
        score *= 0.4
    elif sentiment < -0.2:
        score *= 0.75

    # Penalty: very short agent text
    if len(agent_text) < 60:
        score *= 0.8

    return round(min(score, 1.0), 4)
