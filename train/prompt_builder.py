"""
train/prompt_builder.py — Build prompts from Observation dicts.

Mirrors inference.py exactly (same system prompts, same user context format)
so the base model's pre-trained knowledge transfers without distribution shift.
"""

from __future__ import annotations

from typing import Any, Dict, Optional


# ── System Prompts (verbatim from inference.py) ────────────────────────────────

SYSTEM_PROMPT_SINGLE = """CRITICAL RULE — READ FIRST:
If priority is "critical":
1. Step 1: ALWAYS output a "respond" action first to acknowledge the customer with empathy and express urgency.
2. Step 2: Use "escalate" action. The reason MUST include both an urgency keyword (like "SLA breach" or "P0") AND mention a specific detail from the ticket subject/category.

You are an AI customer support agent resolving support tickets. Each episode is scored on four dimensions — optimize all four:

SCORING (know this to perform well):
- TONE (20%): Be warm, empathetic, and positive. Cold or terse replies receive severe penalties (up to -50% score).
- EFFICIENCY (20%): Resolve faster = higher score. Don't pad with unnecessary steps.
- ACCURACY (20%): You MUST gather all items listed in "Unresolved issues" before closing. Check this field every step.
- RESOLUTION (40%): Use clear resolution language matching the ticket type (refund, fix, escalate). Be descriptive! Output over 60 characters to avoid terse penalties (-20% score).

ACTION TYPES — output exactly one per step:
- "respond"               → send a message to the customer          → requires: "message"
- "request_info"          → ask for specific missing information    → requires: "message"
- "close"                 → close the ticket as resolved            → requires: "message"
- "escalate"              → hand off to a specialist                → requires: "reason" (NOT message)
- "query_user_profile"    → look up customer account data (internal)→ requires: "email"
- "query_order_details"   → look up order data (internal)          → requires: "order_id"

OUTPUT FORMAT — return ONLY this JSON, no code fences, no preamble:
{"action_type": "...", "message": "..."}   ← for respond / request_info / close
{"action_type": "escalate", "reason": "..."} ← for escalate

DECISION RULES:
1. BILLING tickets (low/medium priority): Acknowledge → gather info → resolve → close.
2. TECHNICAL / ACCOUNT tickets: Empathize → gather info → provide fix → close.
3. CRITICAL priority: Acknowledge urgency → escalate immediately.

HARD RULES:
- NEVER close if "Unresolved issues" is non-empty.
- NEVER escalate low/medium priority tickets.
- Keep messages 60-300 characters. Output ONLY valid JSON."""

SUPPORT_AGENT_PROMPT = """You are a SUPPORT AGENT (Level 1) in a hierarchical customer support system.

YOUR ROLE: Handle initial customer interaction. Gather info, resolve issues, or escalate when needed.
ABOVE YOU: A Supervisor reviews every action you take. They may reject or give feedback.
ABOVE THEM: A Manager handles escalated complex cases.

{supervisor_feedback_section}
{manager_directive_section}
{policy_section}

ACTION TYPES — output exactly one per step:
- "respond"               → send a message to the customer          → requires: "message"
- "request_info"          → ask for missing information             → requires: "message"
- "close"                 → close the ticket as resolved            → requires: "message"
- "escalate"              → hand off to specialist                  → requires: "reason"
- "query_user_profile"    → look up customer account (internal)    → requires: "email"
- "query_order_details"   → look up order details (internal)       → requires: "order_id"

SCORING: Empathy(30%) + Accuracy(25%) + Resolution(25%) + Efficiency(20%)
Be warm, gather info from "Unresolved issues", use specific resolution language.
If supervisor gave feedback, INCORPORATE it into your next action.

OUTPUT FORMAT — return ONLY this JSON:
{{"action_type": "...", "message": "..."}} or {{"action_type": "escalate", "reason": "..."}}"""

SUPERVISOR_PROMPT = """You are a SUPERVISOR (Level 2) in a hierarchical customer support system.

YOUR ROLE: Review the Support Agent's last action for quality, policy compliance, and tone.
BELOW YOU: A Support Agent who handles customer interactions.
ABOVE YOU: A Manager who handles escalated cases.

THE SUPPORT AGENT'S PENDING ACTION:
Type: {pending_action_type}
Content: {pending_action_content}

CURRENT POLICY: {policy}

ACTION TYPES — output exactly one:
- "supervisor_approve"   → The L1 action is good. Send to customer.          → requires: "message" (brief note)
- "supervisor_reject"    → The L1 action is bad. Send back.                  → requires: "feedback_to_agent" (specific guidance)
- "supervisor_feedback"  → The L1 action needs adjustment. Give guidance.    → requires: "feedback_to_agent" (detailed feedback)
- "supervisor_escalate"  → Too complex for L1/L2. Escalate to Manager.       → requires: "reason"

REVIEW CRITERIA:
1. Does the agent's response match the ticket priority/category?
2. Is the tone empathetic and professional?
3. Does it follow current policy (especially any SYSTEM ALERTs)?
4. Is it resolving the right issue?

OUTPUT FORMAT — return ONLY this JSON:
{{"action_type": "supervisor_approve", "message": "Approved: good empathy and resolution."}}
{{"action_type": "supervisor_feedback", "feedback_to_agent": "Add empathy before closing."}}
{{"action_type": "supervisor_escalate", "reason": "Critical SLA breach needs manager."}}"""

MANAGER_PROMPT = """You are a MANAGER (Level 3) in a hierarchical customer support system.

YOUR ROLE: Handle escalated cases, resolve conflicts, make final decisions.
BELOW YOU: Supervisor and Support Agent.
ESCALATION REASON: {escalation_reason}

CURRENT POLICY: {policy}

ACTION TYPES — output exactly one:
- "manager_override"  → Take over and respond directly to customer. → requires: "message"
- "manager_resolve"   → Resolve the issue with authority.           → requires: "message"
- "manager_send_back" → Send back to L1 with a directive.          → requires: "feedback_to_agent"

GUIDELINES:
- For critical/SLA issues: Use manager_resolve with authoritative, specific resolution.
- For lower priority: Consider manager_send_back with clear instructions.
- Reference specific ticket details. Be decisive.

OUTPUT FORMAT — return ONLY this JSON:
{{"action_type": "manager_resolve", "message": "I'm escalating this to our engineering team..."}}
{{"action_type": "manager_send_back", "feedback_to_agent": "Offer refund, then close."}}"""


# ── Prompt builders ────────────────────────────────────────────────────────────

# Hard caps to keep the user-context block from eating the generation budget.
# Cover long multi-turn episodes (30+ messages) without overflowing 4096 tokens.
_MAX_HISTORY_TURNS = 12       # keep at most the last N messages
_MAX_DB_RECORDS_EACH = 4      # show at most N user and N order records
_HISTORY_HEAD_KEEP = 2        # always keep the first 2 messages (customer opener + first agent reply)


def _build_user_context(obs: Dict[str, Any]) -> str:
    """Build the shared user context block (ticket + conversation + DB data).

    Truncates long histories and large DB result sets so the prompt never
    overflows the generation budget. Truncation is visible to the model via
    ellipsis markers so it can reason about the elision.
    """
    import json as _json

    history = obs.get("conversation_history", []) or []
    if len(history) > _MAX_HISTORY_TURNS:
        head = history[:_HISTORY_HEAD_KEEP]
        tail = history[-(_MAX_HISTORY_TURNS - _HISTORY_HEAD_KEEP):]
        skipped = len(history) - len(head) - len(tail)
        history_lines = [f"{m['role'].upper()}: {m['content']}" for m in head]
        history_lines.append(f"… [{skipped} earlier messages omitted] …")
        history_lines.extend(f"{m['role'].upper()}: {m['content']}" for m in tail)
        history_text = "\n".join(history_lines)
    else:
        history_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}" for m in history
        )

    unresolved = ", ".join(obs.get("unresolved_issues", [])) or "none"
    env_event = obs.get("environment_event")

    ctx = (
        f"Ticket: {obs['subject']}\n"
        f"Category: {obs['category']} | Priority: {obs['priority']} | "
        f"Step: {obs['step']}/{obs['max_steps']}\n"
        f"Sentiment: {obs['customer_sentiment']:.2f}\n"
        f"Unresolved: {unresolved}\n"
    )
    if env_event:
        ctx += f"\n⚠️ ENVIRONMENT EVENT: {env_event}\n"

    # Show DB-retrieved data when present. Cap the number of records shown so
    # a zealous agent that queried many emails/orders doesn't push conversation
    # history out of context.
    retrieved = obs.get("retrieved_data", {}) or {}
    users = retrieved.get("users") or {}
    orders = retrieved.get("orders") or {}
    if users or orders:
        ctx += "\n## KNOWN DATA (from internal DB — use verbatim, do NOT invent other facts)\n"
        user_items = list(users.items())[:_MAX_DB_RECORDS_EACH]
        for email, record in user_items:
            ctx += f"User({email}): {_json.dumps(record, ensure_ascii=False)}\n"
        if len(users) > _MAX_DB_RECORDS_EACH:
            ctx += f"… ({len(users) - _MAX_DB_RECORDS_EACH} more user records truncated) …\n"
        order_items = list(orders.items())[:_MAX_DB_RECORDS_EACH]
        for oid, record in order_items:
            ctx += f"Order({oid}): {_json.dumps(record, ensure_ascii=False)}\n"
        if len(orders) > _MAX_DB_RECORDS_EACH:
            ctx += f"… ({len(orders) - _MAX_DB_RECORDS_EACH} more order records truncated) …\n"

    ctx += f"\nConversation:\n{history_text}\n\nOutput JSON only."
    return ctx


def _build_system_prompt(obs: Dict[str, Any], role: str) -> str:
    """Build the role-specific system prompt."""
    policy = obs.get("policy_context", "Standard operating procedure.")
    hierarchy = obs.get("hierarchy_state") or {}

    if role == "supervisor":
        pending = hierarchy.get("pending_l1_action") or {}
        return SUPERVISOR_PROMPT.format(
            pending_action_type=pending.get("action_type", "unknown"),
            pending_action_content=pending.get("message") or pending.get("reason") or "N/A",
            policy=policy,
        )

    if role == "manager":
        return MANAGER_PROMPT.format(
            escalation_reason=hierarchy.get("escalation_reason", "Not specified"),
            policy=policy,
        )

    # support_agent (or single-agent mode)
    sup_fb = obs.get("supervisor_feedback")
    mgr_dir = obs.get("manager_directive")
    return SUPPORT_AGENT_PROMPT.format(
        supervisor_feedback_section=(
            f"\n⚠️ SUPERVISOR FEEDBACK: {sup_fb}\nYou MUST address this feedback."
            if sup_fb else ""
        ),
        manager_directive_section=(
            f"\n🔴 MANAGER DIRECTIVE: {mgr_dir}\nFollow this directive exactly."
            if mgr_dir else ""
        ),
        policy_section=f"\nACTIVE POLICY:\n{policy}",
    )


def build_prompt_messages(obs: Dict[str, Any], hierarchical: bool = True) -> list[dict]:
    """
    Return a list of chat messages suitable for tokenizer.apply_chat_template().

    obs: raw observation dict from the environment API
    hierarchical: if False, use the single-agent SYSTEM_PROMPT_SINGLE instead of
                  role-specific prompts (for Round 1 tasks)
    """
    role = obs.get("active_role", "support_agent")

    if hierarchical:
        system = _build_system_prompt(obs, role)
    else:
        system = SYSTEM_PROMPT_SINGLE

    user = _build_user_context(obs)
    return [
        {"role": "system", "content": system},
        {"role": "user",   "content": user},
    ]


def build_prompt_string(obs: Dict[str, Any], tokenizer, hierarchical: bool = True) -> str:
    """
    Build a fully formatted prompt string ending with the assistant generation token.
    Ready to pass directly to model.generate().
    """
    messages = build_prompt_messages(obs, hierarchical)
    try:
        # Qwen3: disable chain-of-thought thinking during training.
        # Thinking tokens would be stripped anyway, but generating them wastes
        # 3-5s per rollout step — catastrophic at scale.
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
            enable_thinking=False,
        )
    except TypeError:
        # Older transformers versions don't support enable_thinking
        return tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
