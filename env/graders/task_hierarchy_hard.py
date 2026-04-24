"""Grader for hierarchy_hard — All 3 levels must engage. Critical SLA + schema drift."""
from typing import Any

_URGENCY_TERMS = {
    "sla", "critical", "outage", "emergency", "breach", "p0", "p1",
    "urgent", "down", "incident", "production", "immediately", "escalat",
}

def grade(session_state: dict[str, Any]) -> float:
    action_log = session_state.get("action_log", [])
    ticket = session_state.get("ticket") or {}
    history = session_state.get("history", [])
    hierarchy = session_state.get("hierarchy_state", {})

    if not action_log or not ticket:
        return 0.0

    score = 0.0
    weights = {"all_levels_engaged": 0.20, "escalation_speed": 0.20,
               "urgency_referenced": 0.20, "manager_quality": 0.15,
               "policy_compliance": 0.15, "no_self_resolve": 0.10}

    roles = [a.get("role", "support_agent") for a in action_log]
    action_types = [a["action_type"] for a in action_log]

    # 1. All 3 levels engaged
    levels = set(roles)
    if "support_agent" in levels and "supervisor" in levels and "manager" in levels:
        score += weights["all_levels_engaged"]
    elif len(levels) >= 2:
        score += weights["all_levels_engaged"] * 0.5

    # 2. Escalation speed (within first 4 steps)
    # Only count L1 escalate actions to avoid double-counting supervisor_escalate
    l1_escalation_steps = [a["step"] for a in action_log if a["action_type"] == "escalate"]
    sup_escalation_steps = [a["step"] for a in action_log if a["action_type"] == "supervisor_escalate"]
    all_escalation_steps = l1_escalation_steps or sup_escalation_steps
    if all_escalation_steps:
        first = min(all_escalation_steps)
        if first <= 3:
            score += weights["escalation_speed"]
        elif first <= 5:
            score += weights["escalation_speed"] * 0.5

    # 3. Urgency referenced
    all_reasons = " ".join(
        (a.get("reason") or a.get("message") or a.get("feedback") or "").lower()
        for a in action_log
    )
    urgency_found = any(t in all_reasons for t in _URGENCY_TERMS)
    if urgency_found:
        score += weights["urgency_referenced"]

    # 4. Manager decision quality
    mgr_actions = [a for a in action_log if a.get("role") == "manager"]
    if mgr_actions:
        mgr_msg = " ".join((a.get("message") or "") for a in mgr_actions).lower()
        subject_words = [w for w in ticket.get("subject", "").lower().split() if len(w) > 4]
        context = any(w in mgr_msg for w in subject_words)
        if context and len(mgr_msg) > 30:
            score += weights["manager_quality"]
        elif mgr_msg:
            score += weights["manager_quality"] * 0.5

    # 5. Policy compliance (no self-resolve attempts on critical)
    _SELF_RESOLVE = ["try ", "please try", "restart", "reinstall", "clear cache",
                     "here are the steps", "troubleshoot"]
    agent_text = " ".join(
        m.get("content", "").lower() for m in history if m.get("role") == "agent"
    )
    self_resolve = any(kw in agent_text for kw in _SELF_RESOLVE)
    if not self_resolve:
        score += weights["policy_compliance"]
    else:
        score += weights["policy_compliance"] * 0.2

    # 6. No unnecessary self-resolution before escalation
    pre_escalation = []
    for a in action_log:
        if "escalat" in a["action_type"]:
            break
        pre_escalation.append(a)
    pre_msgs = " ".join((a.get("message") or "").lower() for a in pre_escalation)
    if not any(kw in pre_msgs for kw in _SELF_RESOLVE):
        score += weights["no_self_resolve"]

    return round(min(score, 1.0), 4)
