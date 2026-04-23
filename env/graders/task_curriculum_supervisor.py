"""Grader for curriculum_supervisor — Stage 2/4: Support Agent + Supervisor."""
from typing import Any


def grade(session_state: dict[str, Any]) -> float:
    """
    Tests whether L1 can incorporate supervisor feedback and improve.
    Rewards feedback loops and iterative improvement.
    """
    action_log = session_state.get("action_log", [])
    ticket = session_state.get("ticket") or {}
    history = session_state.get("history", [])
    hierarchy = session_state.get("hierarchy_state", {})

    if not action_log or not ticket:
        return 0.0

    score = 0.0
    weights = {"resolution": 0.20, "supervisor_reviewed": 0.20,
               "feedback_incorporated": 0.20, "no_manager": 0.10,
               "info_gathered": 0.15, "policy_compliance": 0.15}

    roles = [a.get("role", "support_agent") for a in action_log]
    action_types = [a["action_type"] for a in action_log]
    agent_text = " ".join(
        m.get("content", "").lower() for m in history if m.get("role") == "agent"
    )

    # 1. Resolution
    resolution_kw = ["fix", "resolv", "solution", "workaround", "reset", "unlock",
                     "restore", "refund", "credit", "processed", "completed"]
    if any(kw in agent_text for kw in resolution_kw):
        score += weights["resolution"]
    elif action_types[-1] in ("close", "supervisor_approve"):
        score += weights["resolution"] * 0.3

    # 2. Supervisor reviewed
    sup_reviews = hierarchy.get("supervisor_reviews", 0)
    if sup_reviews >= 2:
        score += weights["supervisor_reviewed"]
    elif sup_reviews >= 1:
        score += weights["supervisor_reviewed"] * 0.6

    # 3. Feedback incorporated — L1 acted differently AFTER receiving feedback
    feedback_hist = hierarchy.get("supervisor_feedback_history", [])
    if feedback_hist:
        # Check if there are L1 actions after the feedback
        feedback_given = False
        post_feedback_l1_actions = 0
        for a in action_log:
            if a.get("action_type") in ("supervisor_feedback", "supervisor_reject"):
                feedback_given = True
            elif feedback_given and a.get("role") == "support_agent":
                post_feedback_l1_actions += 1
        if post_feedback_l1_actions > 0:
            score += weights["feedback_incorporated"]
        else:
            score += weights["feedback_incorporated"] * 0.2
    else:
        # No feedback given — partial credit for clean first pass
        score += weights["feedback_incorporated"] * 0.4

    # 4. No manager needed (ideal for Stage 2)
    if "manager" not in roles and hierarchy.get("manager_interventions", 0) == 0:
        score += weights["no_manager"]

    # 5. Info gathered
    if "request_info" in action_types:
        score += weights["info_gathered"]
    elif len([m for m in history if m.get("role") == "customer"]) > 2:
        score += weights["info_gathered"] * 0.5

    # 6. Policy compliance
    system_msgs = [m for m in history if m.get("role") == "system"]
    policy_violated = False
    for sys_msg in system_msgs:
        content = sys_msg.get("content", "").lower()
        if "do not" in content:
            idx = history.index(sys_msg)
            after_text = " ".join(
                m.get("content", "").lower() for m in history[idx + 1:]
                if m.get("role") == "agent"
            )
            if "refund" in content and ("refund" in after_text or "reimburse" in after_text):
                policy_violated = True
    if not policy_violated:
        score += weights["policy_compliance"]
    else:
        score += weights["policy_compliance"] * 0.2

    if len(agent_text) < 60:
        score *= 0.8

    return round(min(score, 1.0), 4)
