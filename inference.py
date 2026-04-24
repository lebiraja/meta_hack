"""
inference.py — CustomerSupportEnv inference script.

Backend selection (INFERENCE_BACKEND env var):
  local  (default) — runs local HuggingFace model via Unsloth 4-bit
  nim              — calls NVIDIA NIM API (for comparison / fallback)

Model for local backend:
  INFERENCE_MODEL env var → TRAIN_MODEL env var → unsloth/Qwen2.5-1.5B-Instruct
  After training: set INFERENCE_MODEL=merged_model/
"""

import json
import os
import re
import sys

import httpx
from dotenv import load_dotenv

load_dotenv()

INFERENCE_BACKEND = os.getenv("INFERENCE_BACKEND", "local")   # "local" | "nim"
INFERENCE_MODEL   = (
    os.getenv("INFERENCE_MODEL")
    or os.getenv("TRAIN_MODEL")
    or "unsloth/Qwen2.5-1.5B-Instruct"
)
ENV_URL    = os.getenv("ENV_URL", "http://localhost:7860")
BENCHMARK  = "customer-support-env"
TASKS           = ["easy", "medium", "hard"]
HIERARCHY_TASKS = ["hierarchy_easy", "hierarchy_medium", "hierarchy_hard"]
MAX_STEPS = 15

# ── Local model (loaded once at startup) ──────────────────────────────────────

_model     = None
_tokenizer = None


def _load_local_model():
    global _model, _tokenizer
    if _model is not None:
        return _model, _tokenizer

    print(f"[MODEL] Loading local model: {INFERENCE_MODEL}", file=sys.stderr)
    try:
        from unsloth import FastLanguageModel
        _model, _tokenizer = FastLanguageModel.from_pretrained(
            model_name=INFERENCE_MODEL,
            max_seq_length=4096,
            dtype=None,
            load_in_4bit=True,
        )
        FastLanguageModel.for_inference(_model)
    except Exception as e:
        print(f"[ERROR] Failed to load local model: {e}", file=sys.stderr)
        sys.exit(1)

    if _tokenizer.pad_token is None:
        _tokenizer.pad_token = _tokenizer.eos_token

    print(f"[MODEL] Ready — {INFERENCE_MODEL}", file=sys.stderr)
    return _model, _tokenizer


def _call_local(messages: list) -> str:
    import torch
    model, tokenizer = _load_local_model()

    try:
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True, enable_thinking=False,
        )
    except TypeError:
        prompt = tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True,
        )

    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=256,
            temperature=0.6,
            top_p=0.95,
            do_sample=True,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )

    completion = tokenizer.decode(
        output_ids[0, inputs["input_ids"].shape[1]:],
        skip_special_tokens=True,
    )
    return re.sub(r"<think>[\s\S]*?</think>", "", completion, flags=re.IGNORECASE).strip()


# ── NIM API backend ───────────────────────────────────────────────────────────

_NIM_MODEL = os.getenv("MODEL_NAME", "meta/llama-3.3-70b-instruct")
_API_BASE  = os.getenv("API_BASE_URL", "https://integrate.api.nvidia.com/v1")
_API_KEYS  = [k for k in [
    os.getenv("NVIDIA_API_KEY_1"),
    os.getenv("NVIDIA_API_KEY_2"),
    os.getenv("NVIDIA_API_KEY_3"),
] if k and k.strip()]
_active_key_index = 0


def _call_nim(messages: list) -> str:
    global _active_key_index
    if not _API_KEYS:
        raise RuntimeError("No NIM API keys set. Add NVIDIA_API_KEY_1 to .env")
    from openai import OpenAI
    last_exc = None
    for attempt in range(len(_API_KEYS)):
        idx = (_active_key_index + attempt) % len(_API_KEYS)
        try:
            resp = OpenAI(api_key=_API_KEYS[idx], base_url=_API_BASE).chat.completions.create(
                model=_NIM_MODEL, messages=messages,
                temperature=0.6, top_p=0.95, max_tokens=512,
            )
            _active_key_index = idx
            return resp.choices[0].message.content.strip()
        except Exception as exc:
            last_exc = exc
            print(f"[WARN] NIM key {idx+1} failed: {exc}", file=sys.stderr)
    raise RuntimeError(f"All NIM keys failed: {last_exc}") from last_exc


def call_llm(messages: list) -> str:
    if INFERENCE_BACKEND == "nim":
        return _call_nim(messages)
    return _call_local(messages)


# ── System prompts ────────────────────────────────────────────────────────────

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
- "respond"      -> send a message to the customer         -> requires: "message"
- "request_info" -> ask for specific missing information   -> requires: "message"
- "close"        -> close the ticket as resolved           -> requires: "message"
- "escalate"     -> hand off to a specialist               -> requires: "reason" (NOT message)

OUTPUT FORMAT — return ONLY this JSON, no code fences, no preamble:
{"action_type": "...", "message": "..."}   <- for respond / request_info / close
{"action_type": "escalate", "reason": "..."} <- for escalate

DECISION RULES:
1. BILLING tickets (low/medium priority): Acknowledge -> gather info -> resolve -> close.
2. TECHNICAL / ACCOUNT tickets: Empathize -> gather info -> provide fix -> close.
3. CRITICAL priority: Acknowledge urgency -> escalate immediately.

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
- "respond"      -> send a message to the customer  -> requires: "message"
- "request_info" -> ask for missing information      -> requires: "message"
- "close"        -> close the ticket as resolved     -> requires: "message"
- "escalate"     -> hand off to specialist           -> requires: "reason"

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
- "supervisor_approve"   -> The L1 action is good. Send to customer.       -> requires: "message"
- "supervisor_reject"    -> The L1 action is bad. Send back.               -> requires: "feedback_to_agent"
- "supervisor_feedback"  -> The L1 action needs adjustment.                -> requires: "feedback_to_agent"
- "supervisor_escalate"  -> Too complex for L1/L2. Escalate to Manager.    -> requires: "reason"

OUTPUT FORMAT — return ONLY this JSON:
{{"action_type": "supervisor_approve", "message": "Approved: good empathy and resolution."}}
{{"action_type": "supervisor_feedback", "feedback_to_agent": "Add empathy before closing."}}
{{"action_type": "supervisor_escalate", "reason": "Critical SLA breach needs manager."}}"""

MANAGER_PROMPT = """You are a MANAGER (Level 3) in a hierarchical customer support system.

YOUR ROLE: Handle escalated cases, resolve conflicts, make final decisions.
ESCALATION REASON: {escalation_reason}
CURRENT POLICY: {policy}

ACTION TYPES — output exactly one:
- "manager_override"  -> Take over and respond directly. -> requires: "message"
- "manager_resolve"   -> Resolve with authority.         -> requires: "message"
- "manager_send_back" -> Send back to L1 with directive. -> requires: "feedback_to_agent"

OUTPUT FORMAT — return ONLY this JSON:
{{"action_type": "manager_resolve", "message": "I am escalating this to our engineering team immediately."}}
{{"action_type": "manager_send_back", "feedback_to_agent": "Offer refund, then close."}}"""


# ── Prompt builders ───────────────────────────────────────────────────────────

def _user_context(obs: dict) -> str:
    history    = "\n".join(f"{m['role'].upper()}: {m['content']}" for m in obs.get("conversation_history", []))
    unresolved = ", ".join(obs.get("unresolved_issues", [])) or "none"
    ctx = (
        f"Ticket: {obs['subject']}\n"
        f"Category: {obs['category']} | Priority: {obs['priority']} | "
        f"Step: {obs['step']}/{obs['max_steps']}\n"
        f"Sentiment: {obs['customer_sentiment']:.2f}\n"
        f"Unresolved: {unresolved}\n"
    )
    if obs.get("environment_event"):
        ctx += f"\nENVIRONMENT EVENT: {obs['environment_event']}\n"
    ctx += f"\nConversation:\n{history}\n\nOutput JSON only."
    return ctx


def build_messages(obs: dict) -> list:
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user",   "content": _user_context(obs)},
    ]


def build_hierarchy_messages(obs: dict, role: str) -> list:
    policy    = obs.get("policy_context", "Standard operating procedure.")
    hierarchy = obs.get("hierarchy_state") or {}

    if role == "support_agent":
        sup_fb  = obs.get("supervisor_feedback")
        mgr_dir = obs.get("manager_directive")
        system  = SUPPORT_AGENT_PROMPT.format(
            supervisor_feedback_section=(
                f"\nSUPERVISOR FEEDBACK: {sup_fb}\nYou MUST address this feedback." if sup_fb else ""
            ),
            manager_directive_section=(
                f"\nMANAGER DIRECTIVE: {mgr_dir}\nFollow this directive exactly." if mgr_dir else ""
            ),
            policy_section=f"\nACTIVE POLICY:\n{policy}",
        )
    elif role == "supervisor":
        pending = hierarchy.get("pending_l1_action") or {}
        system  = SUPERVISOR_PROMPT.format(
            pending_action_type=pending.get("action_type", "unknown"),
            pending_action_content=pending.get("message") or pending.get("reason") or "N/A",
            policy=policy,
        )
    elif role == "manager":
        system = MANAGER_PROMPT.format(
            escalation_reason=hierarchy.get("escalation_reason", "Not specified"),
            policy=policy,
        )
    else:
        system = SYSTEM_PROMPT

    return [
        {"role": "system", "content": system},
        {"role": "user",   "content": _user_context(obs)},
    ]


# ── Action parsing ────────────────────────────────────────────────────────────

def parse_action(raw: str) -> dict:
    raw = re.sub(r"```[a-z]*\n?", "", raw).strip()
    m   = re.search(r"\{[\s\S]*?\}", raw)
    if m:
        return json.loads(m.group())
    return json.loads(raw)


def _safe_log(action: dict) -> str:
    msg = action.get("message") or action.get("reason") or action.get("feedback_to_agent") or ""
    return json.dumps({"action_type": action.get("action_type", "?"), "msg_preview": msg[:120]})


_FALLBACKS = {
    "support_agent": {"action_type": "respond",           "message": "I understand your concern. Let me look into this immediately and resolve it for you."},
    "supervisor":    {"action_type": "supervisor_approve", "message": "Approved — good empathy and clear resolution."},
    "manager":       {"action_type": "manager_resolve",    "message": "I am personally escalating this to our senior engineering team for immediate resolution."},
}


# ── Episode runners ───────────────────────────────────────────────────────────

def run_task(task_name: str) -> None:
    try:
        r = httpx.post(f"{ENV_URL}/reset", params={"task": task_name}, timeout=30)
        r.raise_for_status()
    except Exception as exc:
        print(f"[ERROR] Reset failed task={task_name}: {exc}", file=sys.stderr)
        return

    data       = r.json()
    obs        = data["observation"]
    session_id = data["session_id"]
    model_tag  = INFERENCE_MODEL if INFERENCE_BACKEND == "local" else _NIM_MODEL
    print(f"[START] task={task_name} env={BENCHMARK} model={model_tag} backend={INFERENCE_BACKEND}")

    rewards, step, done, score = [], 0, False, 0.0
    while not done and step < MAX_STEPS:
        try:
            raw    = call_llm(build_messages(obs))
            action = parse_action(raw)
        except Exception as exc:
            print(f"[WARN] LLM/parse error: {exc}", file=sys.stderr)
            action = _FALLBACKS["support_agent"]

        try:
            sr = httpx.post(f"{ENV_URL}/step", params={"session_id": session_id}, json=action, timeout=30)
            sr.raise_for_status()
            result = sr.json()
        except Exception as exc:
            print(f"[STEP] step={step+1} action={_safe_log(action)} reward=0.00 done=false error={exc}")
            break

        obs        = result["observation"]
        reward_val = result["reward"]["value"]
        done       = result["done"]
        rewards.append(reward_val)
        step      += 1
        score      = result.get("final_score", reward_val) if done else reward_val
        print(f"[STEP] step={step} action={_safe_log(action)} reward={reward_val:.2f} done={'true' if done else 'false'} error=null")

    print(f"[END] success={'true' if done and score >= 0.5 else 'false'} steps={step} score={score:.2f} rewards={','.join(f'{r:.2f}' for r in rewards)}")


def run_hierarchy_task(task_name: str) -> None:
    try:
        r = httpx.post(f"{ENV_URL}/reset", params={"task": task_name}, timeout=30)
        r.raise_for_status()
    except Exception as exc:
        print(f"[ERROR] Reset failed task={task_name}: {exc}", file=sys.stderr)
        return

    data       = r.json()
    obs        = data["observation"]
    session_id = data["session_id"]
    model_tag  = INFERENCE_MODEL if INFERENCE_BACKEND == "local" else _NIM_MODEL
    print(f"[START] task={task_name} env={BENCHMARK} model={model_tag} backend={INFERENCE_BACKEND} mode=hierarchical")

    rewards, step, done, score = [], 0, False, 0.0
    while not done and step < MAX_STEPS:
        role     = obs.get("active_role", "support_agent")
        messages = build_hierarchy_messages(obs, role)
        try:
            raw    = call_llm(messages)
            action = parse_action(raw)
        except Exception as exc:
            print(f"[WARN] LLM/parse error role={role}: {exc}", file=sys.stderr)
            action = _FALLBACKS.get(role, _FALLBACKS["support_agent"])

        try:
            sr = httpx.post(f"{ENV_URL}/step", params={"session_id": session_id}, json=action, timeout=60)
            sr.raise_for_status()
            result = sr.json()
        except Exception as exc:
            print(f"[STEP] step={step+1} role={role} action={_safe_log(action)} reward=0.00 done=false error={exc}")
            break

        obs          = result["observation"]
        reward_val   = result["reward"]["value"]
        done         = result["done"]
        rewards.append(reward_val)
        step        += 1
        score        = result.get("final_score", reward_val) if done else reward_val
        role_rewards = result["reward"].get("role_rewards", {})
        print(
            f"[STEP] step={step} role={role} action={_safe_log(action)} "
            f"reward={reward_val:.2f} role_rewards={json.dumps(role_rewards)} "
            f"done={'true' if done else 'false'} error=null"
        )

    print(f"[END] success={'true' if done and score >= 0.5 else 'false'} steps={step} score={score:.2f} rewards={','.join(f'{r:.2f}' for r in rewards)}")


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if INFERENCE_BACKEND == "local":
        _load_local_model()

    print("=" * 60)
    print(f"ROUND 1: Single-Agent Tasks  [{INFERENCE_BACKEND.upper()} backend]")
    print("=" * 60)
    for task in TASKS:
        run_task(task)
        print()

    print("=" * 60)
    print(f"ROUND 2: Hierarchical Tasks  [{INFERENCE_BACKEND.upper()} backend]")
    print("=" * 60)
    for task in HIERARCHY_TASKS:
        run_hierarchy_task(task)
        print()
