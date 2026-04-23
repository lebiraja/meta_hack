"""Grader for hierarchy_medium — Multi-turn with supervisor feedback and possible policy drift."""
from typing import Any

def grade(session_state: dict[str, Any]) -> float:
    action_log = session_state.get("action_log", [])
    ticket = session_state.get("ticket") or {}
    history = session_state.get("history", [])
    hierarchy = session_state.get("hierarchy_state", {})

    if not action_log or not ticket:
        return 0.0

    score = 0.0
    weights = {"resolution": 0.25, "supervisor_quality": 0.20, "info_gathered": 0.15,
               "multi_turn": 0.15, "policy_compliance": 0.15, "sentiment": 0.10}

    roles = [a.get("role", "support_agent") for a in action_log]
    action_types = [a["action_type"] for a in action_log]
    agent_text = " ".join(m.get("content", "").lower() for m in history if m.get("role") == "agent")
    all_text = " ".join(m.get("content", "") for m in history)

    # 1. Resolution
    resolution_kw = ["fix", "resolv", "solution", "workaround", "reset", "unlock", "restore",
                     "refund", "credit", "escalat", "transfer"]
    if any(kw in agent_text for kw in resolution_kw):
        score += weights["resolution"]
    elif action_types[-1] in ("close", "manager_resolve"):
        score += weights["resolution"] * 0.3

    # 2. Supervisor reviewed AND gave feedback
    sup_reviews = hierarchy.get("supervisor_reviews", 0)
    feedback_hist = hierarchy.get("supervisor_feedback_history", [])
    if sup_reviews > 0:
        score += weights["supervisor_quality"] * 0.5
    if len(feedback_hist) > 0:
        score += weights["supervisor_quality"] * 0.5

    # 3. Info gathered
    import re
    _EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", re.IGNORECASE)
    required = ticket.get("required_info_before_close", [])
    gathered = 0
    for info_type in required:
        if info_type == "account_email" and _EMAIL_RE.search(all_text):
            gathered += 1
        elif info_type != "account_email":
            if sum(1 for m in history if m.get("role") == "customer") > 1:
                gathered += 1
    if required:
        score += weights["info_gathered"] * (gathered / len(required))
    else:
        score += weights["info_gathered"]

    # 4. Multi-turn
    total_turns = len(history)
    if total_turns >= 6:
        score += weights["multi_turn"]
    elif total_turns >= 4:
        score += weights["multi_turn"] * 0.6

    # 5. Policy compliance (check if system events were respected)
    system_msgs = [m for m in history if m.get("role") == "system"]
    policy_violated = False
    for sys_msg in system_msgs:
        content = sys_msg.get("content", "").lower()
        if "do not" in content:
            # Check if agent violated after this message
            idx = history.index(sys_msg)
            after_msgs = [m.get("content", "").lower() for m in history[idx+1:] if m.get("role") == "agent"]
            after_text = " ".join(after_msgs)
            if "refund" in content and "do not" in content and ("refund" in after_text or "reimburse" in after_text):
                policy_violated = True
    if not policy_violated:
        score += weights["policy_compliance"]
    else:
        score += weights["policy_compliance"] * 0.2

    # 6. Sentiment
    sentiment = session_state.get("sentiment", 0.0)
    if sentiment >= -0.3:
        score += weights["sentiment"]
    elif sentiment >= -0.6:
        score += weights["sentiment"] * 0.5

    if len(agent_text) < 60:
        score *= 0.8

    return round(min(score, 1.0), 4)
