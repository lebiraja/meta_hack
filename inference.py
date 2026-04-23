"""
inference.py — CustomerSupportEnv baseline inference script.

Supports both single-agent (Round 1) and hierarchical multi-agent (Round 2).
Uses NVIDIA NIM API with streaming + reasoning via OpenAI-compatible client.
Emits mandatory [START]/[STEP]/[END] stdout format.
"""

import json
import os
import sys

import httpx
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "https://integrate.api.nvidia.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "nvidia/nemotron-super-49b-v1")
ENV_URL = os.getenv("ENV_URL", "http://localhost:7860")

_API_KEYS: list[str] = [
    k for k in [
        os.getenv("NVIDIA_API_KEY_1"), os.getenv("NVIDIA_API_KEY_2"),
        os.getenv("NVIDIA_API_KEY_3"), os.getenv("HF_TOKEN"), os.getenv("API_KEY"),
    ] if k and k.strip()
]

if not _API_KEYS:
    print("[ERROR] No API keys found. Set NVIDIA_API_KEY_1/2/3 in .env", file=sys.stderr)
    sys.exit(1)

_active_key_index = 0

BENCHMARK = "customer-support-env"
TASKS = ["easy", "medium", "hard"]
HIERARCHY_TASKS = ["hierarchy_easy", "hierarchy_medium", "hierarchy_hard"]
MAX_STEPS = 15

# ── System Prompts ─────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """CRITICAL RULE — READ FIRST:
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
- "respond"      → send a message to the customer         → requires: "message"
- "request_info" → ask for specific missing information   → requires: "message"
- "close"        → close the ticket as resolved           → requires: "message"
- "escalate"     → hand off to a specialist               → requires: "reason" (NOT message)

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
- "respond"      → send a message to the customer  → requires: "message"
- "request_info" → ask for missing information      → requires: "message"
- "close"        → close the ticket as resolved     → requires: "message"
- "escalate"     → hand off to specialist           → requires: "reason"

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


def _make_client(key: str) -> OpenAI:
    return OpenAI(api_key=key, base_url=API_BASE_URL)


def call_llm(messages: list[dict]) -> tuple[str, str]:
    global _active_key_index
    last_exc = None
    for attempt in range(len(_API_KEYS)):
        key_idx = (_active_key_index + attempt) % len(_API_KEYS)
        client = _make_client(_API_KEYS[key_idx])
        full_content, reasoning_content = "", ""
        try:
            completion = client.chat.completions.create(
                model=MODEL_NAME, messages=messages,
                temperature=0.6, top_p=0.95, max_tokens=1024, stream=True,
                extra_body={"chat_template_kwargs": {"enable_thinking": True}, "reasoning_budget": 4096},
            )
            for chunk in completion:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                reasoning = getattr(delta, "reasoning_content", None)
                if reasoning:
                    reasoning_content += reasoning
                if delta.content:
                    full_content += delta.content
            if key_idx != _active_key_index:
                print(f"[INFO] Switched to API key {key_idx + 1}", file=sys.stderr)
                _active_key_index = key_idx
            return full_content.strip(), reasoning_content
        except Exception as exc:
            last_exc = exc
            print(f"[WARN] Key {key_idx + 1} failed: {exc}", file=sys.stderr)
    raise RuntimeError(f"All keys exhausted. Last: {last_exc}") from last_exc


def _safe_action_log(action: dict) -> str:
    safe = {"action_type": action.get("action_type", "unknown")}
    msg = action.get("message") or action.get("reason") or action.get("feedback_to_agent") or ""
    safe["msg_preview"] = msg.replace("\n", " ")[:120]
    return json.dumps(safe)


def build_prompt(obs: dict) -> str:
    history_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in obs.get("conversation_history", [])
    )
    unresolved = ", ".join(obs.get("unresolved_issues", [])) or "none"
    return (
        f"Ticket: {obs['subject']}\n"
        f"Category: {obs['category']} | Priority: {obs['priority']} | "
        f"Step: {obs['step']}/{obs['max_steps']}\n"
        f"Customer sentiment: {obs['customer_sentiment']:.2f}\n"
        f"Unresolved issues: {unresolved}\n\n"
        f"Conversation:\n{history_text}\n\n"
        f"What is your next action? Output JSON only."
    )


def build_hierarchy_prompt(obs: dict, role: str) -> tuple[str, str]:
    """Build role-specific system prompt and user prompt for hierarchy mode."""
    history_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}" for m in obs.get("conversation_history", [])
    )
    unresolved = ", ".join(obs.get("unresolved_issues", [])) or "none"
    policy = obs.get("policy_context", "Standard operating procedure.")
    env_event = obs.get("environment_event")
    hierarchy = obs.get("hierarchy_state") or {}

    base_context = (
        f"Ticket: {obs['subject']}\n"
        f"Category: {obs['category']} | Priority: {obs['priority']} | "
        f"Step: {obs['step']}/{obs['max_steps']}\n"
        f"Sentiment: {obs['customer_sentiment']:.2f}\n"
        f"Unresolved: {unresolved}\n"
    )
    if env_event:
        base_context += f"\n⚠️ ENVIRONMENT EVENT: {env_event}\n"

    base_context += f"\nConversation:\n{history_text}\n\nOutput JSON only."

    if role == "support_agent":
        sup_fb = obs.get("supervisor_feedback")
        mgr_dir = obs.get("manager_directive")
        sys_prompt = SUPPORT_AGENT_PROMPT.format(
            supervisor_feedback_section=(
                f"\n⚠️ SUPERVISOR FEEDBACK: {sup_fb}\nYou MUST address this feedback." if sup_fb else ""
            ),
            manager_directive_section=(
                f"\n🔴 MANAGER DIRECTIVE: {mgr_dir}\nFollow this directive exactly." if mgr_dir else ""
            ),
            policy_section=f"\nACTIVE POLICY:\n{policy}",
        )
    elif role == "supervisor":
        pending = hierarchy.get("pending_l1_action", {})
        sys_prompt = SUPERVISOR_PROMPT.format(
            pending_action_type=pending.get("action_type", "unknown"),
            pending_action_content=pending.get("message") or pending.get("reason") or "N/A",
            policy=policy,
        )
    elif role == "manager":
        sys_prompt = MANAGER_PROMPT.format(
            escalation_reason=hierarchy.get("escalation_reason", "Not specified"),
            policy=policy,
        )
    else:
        sys_prompt = SYSTEM_PROMPT

    return sys_prompt, base_context


def parse_action(action_str: str) -> dict:
    """Parse LLM output into action dict, handling markdown fences."""
    if action_str.startswith("```"):
        lines = action_str.split("\n")
        action_str = "\n".join(l for l in lines if not l.startswith("```")).strip()
    return json.loads(action_str)


# ── Single-agent task runner ───────────────────────────────────────────────────

def run_task(task_name: str) -> None:
    try:
        r = httpx.post(f"{ENV_URL}/reset", params={"task": task_name}, timeout=30)
        r.raise_for_status()
    except Exception as exc:
        print(f"[ERROR] Reset failed for task={task_name}: {exc}", file=sys.stderr)
        return

    data = r.json()
    obs = data["observation"]
    session_id = data["session_id"]
    print(f"[START] task={task_name} env={BENCHMARK} model={MODEL_NAME}")

    rewards, step, done, score = [], 0, False, 0.0
    while not done and step < MAX_STEPS:
        messages = [{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": build_prompt(obs)}]
        try:
            action_str, _ = call_llm(messages)
            action = parse_action(action_str)
        except Exception:
            action = {"action_type": "close", "message": "Closing ticket due to error."}

        try:
            step_r = httpx.post(f"{ENV_URL}/step", params={"session_id": session_id}, json=action, timeout=30)
            step_r.raise_for_status()
            result = step_r.json()
        except Exception as exc:
            print(f"[STEP] step={step+1} action={_safe_action_log(action)} reward=0.00 done=false error={exc}")
            break

        obs = result["observation"]
        reward_val = result["reward"]["value"]
        done = result["done"]
        rewards.append(reward_val)
        step += 1
        score = result.get("final_score", reward_val) if done else reward_val
        print(f"[STEP] step={step} action={_safe_action_log(action)} reward={reward_val:.2f} done={'true' if done else 'false'} error=null")

    print(f"[END] success={'true' if done and score >= 0.5 else 'false'} steps={step} score={score:.2f} rewards={','.join(f'{r:.2f}' for r in rewards)}")


# ── Hierarchical task runner ───────────────────────────────────────────────────

def run_hierarchy_task(task_name: str) -> None:
    try:
        r = httpx.post(f"{ENV_URL}/reset", params={"task": task_name}, timeout=30)
        r.raise_for_status()
    except Exception as exc:
        print(f"[ERROR] Reset failed for task={task_name}: {exc}", file=sys.stderr)
        return

    data = r.json()
    obs = data["observation"]
    session_id = data["session_id"]
    print(f"[START] task={task_name} env={BENCHMARK} model={MODEL_NAME} mode=hierarchical")

    rewards, step, done, score = [], 0, False, 0.0

    while not done and step < MAX_STEPS:
        active_role = obs.get("active_role", "support_agent")
        sys_prompt, user_prompt = build_hierarchy_prompt(obs, active_role)

        messages = [{"role": "system", "content": sys_prompt}, {"role": "user", "content": user_prompt}]
        try:
            action_str, _ = call_llm(messages)
            action = parse_action(action_str)
        except Exception as exc:
            # Fallback actions per role
            if active_role == "supervisor":
                action = {"action_type": "supervisor_approve", "message": "Approved."}
            elif active_role == "manager":
                action = {"action_type": "manager_resolve", "message": "Escalating to engineering team immediately."}
            else:
                action = {"action_type": "close", "message": "Closing due to error."}

        try:
            step_r = httpx.post(f"{ENV_URL}/step", params={"session_id": session_id}, json=action, timeout=60)
            step_r.raise_for_status()
            result = step_r.json()
        except Exception as exc:
            print(f"[STEP] step={step+1} role={active_role} action={_safe_action_log(action)} reward=0.00 done=false error={exc}")
            break

        obs = result["observation"]
        reward_val = result["reward"]["value"]
        done = result["done"]
        rewards.append(reward_val)
        step += 1
        score = result.get("final_score", reward_val) if done else reward_val

        role_rewards = result["reward"].get("role_rewards", {})
        print(
            f"[STEP] step={step} role={active_role} action={_safe_action_log(action)} "
            f"reward={reward_val:.2f} role_rewards={json.dumps(role_rewards)} "
            f"done={'true' if done else 'false'} error=null"
        )

    print(f"[END] success={'true' if done and score >= 0.5 else 'false'} steps={step} score={score:.2f} rewards={','.join(f'{r:.2f}' for r in rewards)}")


if __name__ == "__main__":
    print("=" * 60)
    print("ROUND 1: Single-Agent Tasks")
    print("=" * 60)
    for task in TASKS:
        run_task(task)
        print()

    print("=" * 60)
    print("ROUND 2: Hierarchical Multi-Agent Tasks")
    print("=" * 60)
    for task in HIERARCHY_TASKS:
        run_hierarchy_task(task)
        print()
