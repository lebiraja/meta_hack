"""
Grader for Task multi_domain — DB-backed grounded response task.

Checks:
  1. At least one correct DB query was issued     (+0.35)
  2. Final response cites verbatim data from retrieved_data  (+0.30)
  3. not_found handled correctly when it occurred (+0.20)
  4. No hallucinated facts in agent messages      (+0.15)
"""

from typing import Any
import re


_EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", re.IGNORECASE)
_ORDER_RE = re.compile(r"\b(?:order|ord|#)\s*[-]?\s*[A-Z0-9]{4,}\b", re.IGNORECASE)
_FACT_PATTERNS = [
    re.compile(r"₹\s*\d+|\brs\.?\s*\d+|\brupees?\s*\d+", re.IGNORECASE),
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    _EMAIL_RE,
    _ORDER_RE,
]


def grade(session_state: dict[str, Any]) -> float:
    action_log: list[dict] = session_state.get("action_log", [])
    ticket: dict = session_state.get("ticket") or {}
    history: list[dict] = session_state.get("history", [])
    retrieved_data: dict = session_state.get("retrieved_data", {"users": {}, "orders": {}})

    if not action_log or not ticket:
        return 0.0

    score = 0.0
    ticket_email = ticket.get("customer_email", "")
    ticket_order_ids: list[str] = [o.upper() for o in ticket.get("related_order_ids", [])]

    # ── 1. Correct DB query issued (+0.35) ────────────────────────────────────
    correct_query = False
    for entry in action_log:
        at = entry.get("action_type", "")
        if at == "query_user_profile":
            queried = (entry.get("email") or "").lower().strip()
            if ticket_email and queried == ticket_email.lower():
                correct_query = True
                break
        if at == "query_order_details":
            queried = (entry.get("order_id") or "").upper().strip()
            if ticket_order_ids and queried in ticket_order_ids:
                correct_query = True
                break

    if correct_query:
        score += 0.35

    # ── 2. Final response cites verbatim DB data (+0.30) ─────────────────────
    agent_messages = [m.get("content", "") for m in history if m.get("role") == "agent"]
    last_agent_msg = agent_messages[-1].lower() if agent_messages else ""

    # Collect all string values from retrieved_data
    grounded_values: list[str] = []
    for user_record in retrieved_data.get("users", {}).values():
        if isinstance(user_record, dict):
            grounded_values.extend(str(v).lower() for v in user_record.values())
    for order_record in retrieved_data.get("orders", {}).values():
        if isinstance(order_record, dict):
            for v in order_record.values():
                if isinstance(v, list):
                    grounded_values.extend(str(i).lower() for i in v)
                else:
                    grounded_values.append(str(v).lower())

    if grounded_values and last_agent_msg:
        cites_data = any(gv in last_agent_msg for gv in grounded_values if len(gv) > 3)
        if cites_data:
            score += 0.30

    # ── 3. not_found handled correctly (+0.20) ────────────────────────────────
    any_not_found = (
        "not_found" in retrieved_data.get("users", {}).values()
        or "not_found" in retrieved_data.get("orders", {}).values()
    )
    if any_not_found:
        # Check if agent correctly requested info or escalated after not_found
        action_types = [a["action_type"] for a in action_log]
        good_handling = any(
            at in ("request_info", "escalate", "supervisor_escalate")
            for at in action_types
        )
        if good_handling:
            score += 0.20
    else:
        # No not_found → give partial credit (situation didn't arise)
        score += 0.10

    # ── 4. No hallucinated facts (+0.15) ──────────────────────────────────────
    all_agent_text = " ".join(agent_messages).lower()
    customer_text = " ".join(
        m.get("content", "") for m in history if m.get("role") == "customer"
    ).lower()
    all_known_text = customer_text + " " + " ".join(grounded_values)

    hallucinated = False
    for pat in _FACT_PATTERNS:
        for match in pat.finditer(all_agent_text):
            claimed = match.group(0).lower()
            if claimed not in all_known_text:
                hallucinated = True
                break
        if hallucinated:
            break

    if not hallucinated:
        score += 0.15

    # ── Penalties ─────────────────────────────────────────────────────────────
    sentiment = session_state.get("sentiment", 0.0)
    if sentiment < -0.3:
        score *= 0.5
    elif sentiment < 0.0:
        score *= 0.75

    return round(min(score, 1.0), 4)
