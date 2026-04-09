"""
Grader for Task Hard — SLA-Critical Escalation Triage.

Deterministic 0.0–1.0 score. Checks:
  1. ESCALATE was the action taken (not CLOSE or RESPOND indefinitely)
  2. Escalation happened within step ≤2
  3. Reason for escalation references urgency (SLA, critical, outage, emergency, P0, breach)
  4. Agent did NOT attempt to self-resolve before escalating (penalized)
  5. Speed bonus for escalating on step 1

Counter-intuitive task: Most LLMs will try to help the customer themselves.
The correct behavior is to acknowledge urgency immediately and escalate.
"""

from typing import Any

_URGENCY_TERMS = {
    "sla", "critical", "outage", "emergency", "breach", "p0", "p1",
    "urgent", "down", "incident", "production", "immediately", "escalat",
    "senior", "engineering", "specialist", "on-call", "oncall",
}

_SELF_RESOLVE_KEYWORDS = [
    "try ", "please try", "can you try", "have you tried",
    "restart", "reinstall", "clear cache", "log out and", "check your",
    "here are the steps", "follow these", "troubleshoot",
]


def grade(session_state: dict[str, Any]) -> float:
    action_log: list[dict] = session_state.get("action_log", [])
    ticket: dict = session_state.get("ticket") or {}
    history: list[dict] = session_state.get("history", [])

    if not action_log or not ticket:
        return 0.0

    score = 0.0
    weights = {
        "escalated": 0.20,
        "escalated_early": 0.20,
        "urgency_referenced": 0.50,
        "no_self_resolve": 0.10,
    }

    action_types = [a["action_type"] for a in action_log]
    escalate_steps = [
        a["step"] for a in action_log if a["action_type"] == "escalate"
    ]

    # ── 1. ESCALATE was used ───────────────────────────────────────────────────
    if "escalate" in action_types:
        score += weights["escalated"]
    else:
        # No escalation at all — partial credit only if closed
        if "close" in action_types:
            score += weights["escalated"] * 0.1
        return round(min(score, 1.0), 4)  # Can't score on later criteria without escalation

    # ── 2. Escalation was early (≤2 steps) ────────────────────────────────────
    first_escalation_step = min(escalate_steps)
    if first_escalation_step <= 1:
        score += weights["escalated_early"]  # Perfect — immediately escalated
    elif first_escalation_step == 2:
        score += weights["escalated_early"] * 0.85
    elif first_escalation_step == 3:
        score += weights["escalated_early"] * 0.4
    # No credit for escalating at step 4+

    # ── 3. Urgency referenced in escalation reason ────────────────────────────
    escalation_entries = [a for a in action_log if a["action_type"] == "escalate"]
    urgency_found = False
    for entry in escalation_entries:
        reason = (entry.get("reason") or entry.get("message") or "").lower()
        if any(term in reason for term in _URGENCY_TERMS):
            urgency_found = True
            break

    if urgency_found:
        score += weights["urgency_referenced"]
    elif escalation_entries:
        # Escalated but with no urgency language — no credit for urgency
        pass

    # ── 4. No self-resolve attempt before escalation ───────────────────────────
    # Check agent messages BEFORE the first escalation for troubleshooting language
    self_resolve_detected = False
    for entry in action_log:
        if entry["action_type"] == "escalate":
            break
        msg = (entry.get("message") or "").lower()
        if any(kw in msg for kw in _SELF_RESOLVE_KEYWORDS):
            self_resolve_detected = True
            break

    if not self_resolve_detected:
        score += weights["no_self_resolve"]

    return round(min(score, 1.0), 4)
