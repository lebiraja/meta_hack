"""Grader for curriculum_full_hierarchy — Stage 3/4: Full 3-level coordination + drift."""
from typing import Any

_URGENCY_TERMS = {
    "sla", "critical", "outage", "emergency", "breach", "p0", "p1",
    "urgent", "down", "incident", "production", "immediately", "escalat",
}


def grade(session_state: dict[str, Any]) -> float:
    """
    Tests full 3-level coordination under policy drift.
    Similar to hierarchy_hard but with curriculum-specific scoring.
    """
    action_log = session_state.get("action_log", [])
    ticket = session_state.get("ticket") or {}
    history = session_state.get("history", [])
    hierarchy = session_state.get("hierarchy_state", {})

    if not action_log or not ticket:
        return 0.0

    score = 0.0
    weights = {
        "all_levels_engaged": 0.20,
        "escalation_speed": 0.15,
        "urgency_referenced": 0.10,
        "manager_quality": 0.15,
        "policy_compliance": 0.15,
        "coordination": 0.15,
        "tone": 0.10,
    }

    roles = [a.get("role", "support_agent") for a in action_log]
    action_types = [a["action_type"] for a in action_log]
    agent_text = " ".join(
        m.get("content", "").lower() for m in history
        if m.get("role") in ("agent", "supervisor", "manager")
    )

    # 1. All 3 levels engaged
    levels = set(roles)
    if "support_agent" in levels and "supervisor" in levels and "manager" in levels:
        score += weights["all_levels_engaged"]
    elif len(levels) >= 2:
        score += weights["all_levels_engaged"] * 0.4

    # 2. Escalation speed
    escalation_steps = [a["step"] for a in action_log if "escalat" in a["action_type"]]
    if escalation_steps:
        first = min(escalation_steps)
        if first <= 3:
            score += weights["escalation_speed"]
        elif first <= 5:
            score += weights["escalation_speed"] * 0.5
    if "supervisor_escalate" in action_types:
        score += weights["escalation_speed"] * 0.3

    # 3. Urgency referenced
    all_reasons = " ".join(
        (a.get("reason") or a.get("message") or a.get("feedback") or "").lower()
        for a in action_log
    )
    if any(t in all_reasons for t in _URGENCY_TERMS):
        score += weights["urgency_referenced"]

    # 4. Manager quality
    mgr_actions = [a for a in action_log if a.get("role") == "manager"]
    if mgr_actions:
        mgr_msg = " ".join((a.get("message") or "") for a in mgr_actions).lower()
        subject_words = [w for w in ticket.get("subject", "").lower().split() if len(w) > 4]
        context = any(w in mgr_msg for w in subject_words)
        if context and len(mgr_msg) > 30:
            score += weights["manager_quality"]
        elif mgr_msg:
            score += weights["manager_quality"] * 0.5

    # 5. Policy compliance
    system_msgs = [m for m in history if m.get("role") == "system"]
    policy_violated = False
    for sys_msg in system_msgs:
        content = sys_msg.get("content", "").lower()
        if "do not" in content:
            idx = history.index(sys_msg)
            after_text = " ".join(
                m.get("content", "").lower() for m in history[idx + 1:]
                if m.get("role") in ("agent", "supervisor", "manager")
            )
            if "refund" in content and "do not" in content:
                if "refund" in after_text or "reimburse" in after_text:
                    policy_violated = True
    if not policy_violated:
        score += weights["policy_compliance"]
    else:
        score += weights["policy_compliance"] * 0.2

    # 6. Coordination (supervisor feedback + L1 follow-up + L3 resolution)
    feedback_hist = hierarchy.get("supervisor_feedback_history", [])
    mgr_directives = hierarchy.get("manager_directive_history", [])
    coordination_score = 0.0
    if feedback_hist:
        coordination_score += 0.4
    if mgr_directives:
        coordination_score += 0.3
    if "supervisor_escalate" in action_types and mgr_actions:
        coordination_score += 0.3
    score += weights["coordination"] * min(coordination_score, 1.0)

    # 7. Tone
    sentiment = session_state.get("sentiment", 0.0)
    if sentiment >= -0.2:
        score += weights["tone"]
    elif sentiment >= -0.5:
        score += weights["tone"] * 0.5

    if len(agent_text) < 80:
        score *= 0.7

    return round(min(score, 1.0), 4)
