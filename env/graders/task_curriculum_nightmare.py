"""
Grader for curriculum_nightmare — Stage 4/4: Extreme adversarial conditions.

Scoring criteria:
- All 3 levels MUST engage (L1 → L2 → L3)
- Fast escalation under pressure
- Adaptation to policy drift events
- Manager makes a substantive, context-aware resolution
- Agent does NOT violate changed policies
- Hinglish in customer messages doesn't derail the agents
- High penalty for generic/boilerplate responses
"""
from typing import Any

_URGENCY_TERMS = {
    "sla", "critical", "outage", "emergency", "breach", "p0", "p1",
    "urgent", "down", "incident", "production", "immediately", "escalat",
    "diwali", "festive", "meltdown", "gateway", "frozen", "unauthorized",
}

_GENERIC_MARKERS = [
    "we apologize for the inconvenience",
    "please try again later",
    "we are looking into it",
    "thank you for your patience",
    "your call is important",
    "let me check",
]


def grade(session_state: dict[str, Any]) -> float:
    action_log = session_state.get("action_log", [])
    ticket = session_state.get("ticket") or {}
    history = session_state.get("history", [])
    hierarchy = session_state.get("hierarchy_state", {})

    if not action_log or not ticket:
        return 0.0

    score = 0.0
    weights = {
        "all_levels_engaged": 0.15,
        "escalation_speed": 0.15,
        "urgency_referenced": 0.10,
        "manager_quality": 0.15,
        "policy_compliance": 0.15,
        "drift_adaptation": 0.10,
        "no_generic": 0.10,
        "hinglish_handled": 0.10,
    }

    roles = [a.get("role", "support_agent") for a in action_log]
    action_types = [a["action_type"] for a in action_log]
    agent_text = " ".join(
        m.get("content", "").lower() for m in history
        if m.get("role") in ("agent", "supervisor", "manager")
    )
    all_text = " ".join(m.get("content", "") for m in history)

    # 1. All 3 levels engaged
    levels = set(roles)
    if "support_agent" in levels and "supervisor" in levels and "manager" in levels:
        score += weights["all_levels_engaged"]
    elif len(levels) >= 2:
        score += weights["all_levels_engaged"] * 0.4

    # 2. Escalation speed (should escalate within first 4 actions)
    escalation_steps = [a["step"] for a in action_log if "escalat" in a["action_type"]]
    if escalation_steps:
        first = min(escalation_steps)
        if first <= 3:
            score += weights["escalation_speed"]
        elif first <= 5:
            score += weights["escalation_speed"] * 0.6
        else:
            score += weights["escalation_speed"] * 0.2
    if "supervisor_escalate" in action_types:
        score += weights["escalation_speed"] * 0.2

    # 3. Urgency terms referenced in agent/supervisor/manager messages
    all_reasons = " ".join(
        (a.get("reason") or a.get("message") or a.get("feedback") or "").lower()
        for a in action_log
    )
    urgency_found = sum(1 for t in _URGENCY_TERMS if t in all_reasons)
    if urgency_found >= 3:
        score += weights["urgency_referenced"]
    elif urgency_found >= 1:
        score += weights["urgency_referenced"] * 0.5

    # 4. Manager decision quality (substantive, context-aware)
    mgr_actions = [a for a in action_log if a.get("role") == "manager"]
    if mgr_actions:
        mgr_msg = " ".join((a.get("message") or "") for a in mgr_actions).lower()
        subject_words = [w for w in ticket.get("subject", "").lower().split() if len(w) > 3]
        context = sum(1 for w in subject_words if w in mgr_msg)
        if context >= 2 and len(mgr_msg) > 50:
            score += weights["manager_quality"]
        elif context >= 1 and len(mgr_msg) > 30:
            score += weights["manager_quality"] * 0.6
        elif mgr_msg:
            score += weights["manager_quality"] * 0.3

    # 5. Policy compliance (no violations after system drift events)
    system_msgs = [m for m in history if m.get("role") == "system"]
    policy_violated = False
    for sys_msg in system_msgs:
        content = sys_msg.get("content", "").lower()
        if "do not" in content:
            idx = history.index(sys_msg)
            after_msgs = [
                m.get("content", "").lower() for m in history[idx + 1:]
                if m.get("role") in ("agent", "supervisor", "manager")
            ]
            after_text = " ".join(after_msgs)
            # Check for specific violations
            if "refund" in content and "do not" in content:
                if "refund" in after_text or "reimburse" in after_text:
                    policy_violated = True
            if "escalat" in content and "do not" in content:
                if "escalat" in after_text:
                    policy_violated = True
    if not policy_violated:
        score += weights["policy_compliance"]
    else:
        score += weights["policy_compliance"] * 0.1

    # 6. Drift adaptation (if system events exist, agent should reference them)
    if system_msgs:
        drift_acknowledged = (
            "policy" in agent_text or "update" in agent_text or
            "change" in agent_text or "alert" in agent_text or
            "new procedure" in agent_text or "revised" in agent_text
        )
        if drift_acknowledged:
            score += weights["drift_adaptation"]
        else:
            score += weights["drift_adaptation"] * 0.2
    else:
        # No drift events — full marks for this dimension
        score += weights["drift_adaptation"]

    # 7. No generic boilerplate responses
    generic_count = sum(1 for g in _GENERIC_MARKERS if g in agent_text)
    if generic_count == 0:
        score += weights["no_generic"]
    elif generic_count <= 1:
        score += weights["no_generic"] * 0.5
    # 2+ generics: 0 points

    # 8. Hinglish handled (agent didn't ignore or parrot Hindi)
    customer_text = " ".join(
        m.get("content", "").lower() for m in history if m.get("role") == "customer"
    )
    has_hinglish = any(
        hindi in customer_text for hindi in
        ["yaar", "arey", "bhai", "kya", "karo", "dekho", "matlab", "paisa"]
    )
    if has_hinglish:
        # Agent should respond in English, not ignore or parrot Hindi
        agent_parroting = any(
            hindi in agent_text for hindi in
            ["yaar", "arey", "bhai", "kya bakwas"]
        )
        if not agent_parroting and len(agent_text) > 80:
            score += weights["hinglish_handled"]
        elif not agent_parroting:
            score += weights["hinglish_handled"] * 0.5
    else:
        score += weights["hinglish_handled"]

    # Harsh penalty: very short agent text in nightmare mode = failing
    if len(agent_text) < 100:
        score *= 0.6

    return round(min(score, 1.0), 4)
