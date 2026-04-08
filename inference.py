"""
inference.py — CustomerSupportEnv baseline inference script.

Root directory. HTTP client to ENV_URL (FastAPI server).
Uses NVIDIA NIM API with streaming + reasoning via OpenAI-compatible client.
Emits mandatory [START]/[STEP]/[END] stdout format.

Environment variables (loaded from .env):
  NVIDIA_API_KEY_1/2/3 — Three NVIDIA NIM API keys (failover in order)
  API_BASE_URL         — API base URL (default: https://integrate.api.nvidia.com/v1)
  MODEL_NAME           — Model to use (default: nvidia/nemotron-super-49b-v1)
  ENV_URL              — Environment server URL (default: http://localhost:7860)
  HF_TOKEN             — Optional: Hugging Face token (last-resort key)
"""

import json
import os
import sys

import httpx
from dotenv import load_dotenv
from openai import OpenAI

# ── Load .env ──────────────────────────────────────────────────────────────────
load_dotenv()

API_BASE_URL = os.getenv("API_BASE_URL", "https://integrate.api.nvidia.com/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "nvidia/nemotron-super-49b-v1")
ENV_URL = os.getenv("ENV_URL", "http://localhost:7860")

# ── Load all API keys — try each in order until one works ─────────────────────
_API_KEYS: list[str] = [
    k for k in [
        os.getenv("NVIDIA_API_KEY_1"),
        os.getenv("NVIDIA_API_KEY_2"),
        os.getenv("NVIDIA_API_KEY_3"),
        os.getenv("HF_TOKEN"),
        os.getenv("API_KEY"),
    ]
    if k and k.strip()
]

if not _API_KEYS:
    print("[ERROR] No API keys found. Set NVIDIA_API_KEY_1/2/3 in .env", file=sys.stderr)
    sys.exit(1)

# Track which key index is currently active (shared across calls)
_active_key_index = 0

BENCHMARK = "customer-support-env"
TASKS = ["easy", "medium", "hard"]
MAX_STEPS = 10

SYSTEM_PROMPT = """You are an AI customer support agent resolving support tickets. Each episode is scored on four dimensions — optimize all four:

SCORING (know this to perform well):
- TONE (20%): Be warm, empathetic, and positive. Cold or vague replies score lower.
- EFFICIENCY (20%): Resolve faster = higher score. Don't pad with unnecessary steps.
- ACCURACY (20%): You MUST gather all items listed in "Unresolved issues" before closing. Check this field every step.
- RESOLUTION (40%): Use clear resolution language matching the ticket type (refund, fix, escalate). Vague closures score low.

ACTION TYPES — output exactly one per step:
- "respond"      → send a message to the customer         → requires: "message"
- "request_info" → ask for specific missing information   → requires: "message"
- "close"        → close the ticket as resolved           → requires: "message"
- "escalate"     → hand off to a specialist               → requires: "reason" (NOT message)

OUTPUT FORMAT — return ONLY this JSON, no code fences, no preamble, no explanation:
{"action_type": "...", "message": "..."}   ← for respond / request_info / close
{"action_type": "escalate", "reason": "..."} ← for escalate

DECISION RULES:

1. CRITICAL priority (outage, SLA breach, security incident, data loss):
   - Escalate on step 1 or 2. Do NOT attempt to self-resolve.
   - reason MUST contain urgency language: use words like "SLA breach", "critical outage", "P0 incident", "emergency escalation", "production down", "immediate engineering required"
   - Example: {"action_type": "escalate", "reason": "P0 critical outage — SLA breach imminent, escalating to senior engineering immediately."}

2. BILLING tickets (low/medium priority — refunds, double charges, invoice errors):
   - Step 1: Acknowledge and empathize warmly.
   - Step 2: Use request_info to gather account email if "account_email" is in Unresolved issues.
   - Step 3: Confirm refund/resolution and close.
   - Do NOT escalate billing tickets. Penalty: -0.3.
   - Example close: {"action_type": "close", "message": "I have processed a full refund for the duplicate charge. You will see the credit in 3-5 business days."}

3. TECHNICAL / ACCOUNT tickets (medium priority):
   - Step 1: Empathize — acknowledge the frustration directly.
   - Step 2: Use request_info to gather required info (account email, device info, order ID).
   - Step 3: Provide a concrete, actionable solution or workaround.
   - Step 4: Close once Unresolved issues is empty.
   - Example: {"action_type": "request_info", "message": "Could you please share your account email and the device you are using? This will help me investigate right away."}

HARD RULES (violations are penalized):
- NEVER close if "Unresolved issues" list is non-empty — gather that info first.
- NEVER escalate low or medium priority tickets — resolve them yourself.
- Keep messages under 300 words. Be direct, not verbose.
- Do not repeat yourself. Sending the same message twice gets a loop penalty.
- Output ONLY valid JSON. No markdown. No explanation outside the JSON."""


def _make_client(key: str) -> OpenAI:
    return OpenAI(api_key=key, base_url=API_BASE_URL)


def call_llm(messages: list[dict]) -> tuple[str, str]:
    """
    Call NVIDIA NIM with streaming + reasoning.
    Tries API keys in order (key 1 → key 2 → key 3).
    If a key fails (rate limit, auth error, timeout), automatically falls
    over to the next key and retries the same request.
    Returns (action_json_str, reasoning_text).
    """
    global _active_key_index

    last_exc: Exception | None = None

    # Try from the currently active key, wrap around through all keys
    for attempt in range(len(_API_KEYS)):
        key_idx = (_active_key_index + attempt) % len(_API_KEYS)
        key = _API_KEYS[key_idx]
        client = _make_client(key)

        full_content = ""
        reasoning_content = ""

        try:
            completion = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                temperature=0.6,
                top_p=0.95,
                max_tokens=1024,
                extra_body={
                    "chat_template_kwargs": {"enable_thinking": True},
                    "reasoning_budget": 4096,
                },
                stream=True,
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

            # Success — lock in this key for future calls
            if key_idx != _active_key_index:
                print(
                    f"[INFO] Switched to API key {key_idx + 1} after key {_active_key_index + 1} failed",
                    file=sys.stderr,
                )
                _active_key_index = key_idx

            return full_content.strip(), reasoning_content

        except Exception as exc:
            last_exc = exc
            print(
                f"[WARN] API key {key_idx + 1} failed: {type(exc).__name__}: {exc}. "
                f"Trying next key...",
                file=sys.stderr,
            )
            continue

    raise RuntimeError(
        f"All {len(_API_KEYS)} API keys exhausted. Last error: {last_exc}"
    ) from last_exc


def _safe_action_log(action: dict) -> str:
    """Sanitize action for log output — strip newlines, truncate message."""
    safe = {"action_type": action.get("action_type", "unknown")}
    msg = action.get("message") or action.get("reason") or ""
    msg = msg.replace("\n", " ").replace("\r", "")[:120]
    if msg:
        safe["msg_preview"] = msg
    return json.dumps(safe)


def build_prompt(obs: dict) -> str:
    history_text = "\n".join(
        f"{m['role'].upper()}: {m['content']}"
        for m in obs.get("conversation_history", [])
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


def run_task(task_name: str) -> None:
    # ── Reset environment ──────────────────────────────────────────────────────
    try:
        r = httpx.post(f"{ENV_URL}/reset", params={"task": task_name}, timeout=30)
        r.raise_for_status()
    except Exception as exc:
        print(f"[ERROR] Failed to reset env for task={task_name}: {exc}", file=sys.stderr)
        return

    data = r.json()
    obs = data["observation"]
    session_id = data["session_id"]

    print(f"[START] task={task_name} env={BENCHMARK} model={MODEL_NAME}")

    rewards: list[float] = []
    step = 0
    done = False
    score = 0.0
    last_error = None

    while not done and step < MAX_STEPS:
        # ── Build LLM prompt ───────────────────────────────────────────────────
        user_prompt = build_prompt(obs)
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ]

        # ── Call LLM ───────────────────────────────────────────────────────────
        try:
            action_str, _ = call_llm(messages)
            # Strip markdown code fences if present
            if action_str.startswith("```"):
                lines = action_str.split("\n")
                action_str = "\n".join(
                    l for l in lines if not l.startswith("```")
                ).strip()
            action = json.loads(action_str)
            last_error = None
        except Exception as exc:
            action = {"action_type": "close", "message": "Closing ticket due to error."}
            action_str = json.dumps(action)
            last_error = str(exc)

        # ── Step environment ───────────────────────────────────────────────────
        try:
            step_r = httpx.post(
                f"{ENV_URL}/step",
                params={"session_id": session_id},
                json=action,
                timeout=30,
            )
            step_r.raise_for_status()
            result = step_r.json()
        except Exception as exc:
            last_error = str(exc)
            print(
                f"[STEP] step={step + 1} action={_safe_action_log(action)} "
                f"reward=0.00 done=false error={last_error}"
            )
            break

        obs = result["observation"]
        reward_obj = result["reward"]
        reward_val = reward_obj["value"]
        done = result["done"]
        server_error = result.get("info", {}).get("error")
        error_out = last_error or server_error

        rewards.append(reward_val)
        step += 1
        score = result.get("final_score", reward_val) if done else reward_val

        print(
            f"[STEP] step={step} action={_safe_action_log(action)} "
            f"reward={reward_val:.2f} done={'true' if done else 'false'} "
            f"error={'null' if not error_out else error_out}"
        )

    success = done and score >= 0.5
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={'true' if success else 'false'} steps={step} "
        f"score={score:.2f} rewards={rewards_str}"
    )


if __name__ == "__main__":
    # Run all three tasks sequentially
    for task in TASKS:
        run_task(task)
        print()  # blank line between tasks
