"""
serve_inference.py — GGUF inference server for the frontend Auto-Play and /chat endpoint.

Downloads lebiraja/customer-support-grpo-v5-gguf (model-q4_k_m.gguf, ~4.9 GB) on first start,
then serves it on port 8001 via llama-cpp-python (CPU, no GPU required).

Usage:
    python serve_inference.py

Environment:
    GGUF_REPO         — HF repo id  (default: lebiraja/customer-support-grpo-v5-gguf)
    GGUF_FILE         — filename     (default: model-q4_k_m.gguf)
    INFERENCE_PORT    — port         (default: 8001)
    N_CTX             — context len  (default: 4096)
    N_THREADS         — CPU threads  (default: all cores)
    HF_TOKEN          — optional token for private repos
"""

import os
import re
import sys
from dotenv import load_dotenv

load_dotenv()

GGUF_REPO = os.getenv("GGUF_REPO", "lebiraja/customer-support-grpo-v5-gguf")
GGUF_FILE = os.getenv("GGUF_FILE", "model-q4_k_m.gguf")
PORT      = int(os.getenv("INFERENCE_PORT", "8001"))
N_CTX     = int(os.getenv("N_CTX",     "4096"))
N_THREADS = int(os.getenv("N_THREADS", str(os.cpu_count() or 4)))
HF_TOKEN  = os.getenv("HF_TOKEN")

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

app = FastAPI(title="GGUF Inference — customer-support-grpo-v5")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Model (loaded once at startup) ────────────────────────────────────────────

_llm = None


def _load():
    global _llm
    from huggingface_hub import hf_hub_download
    from llama_cpp import Llama

    print(f"[SERVE] Downloading {GGUF_REPO}/{GGUF_FILE} …", flush=True)
    model_path = hf_hub_download(
        repo_id=GGUF_REPO,
        filename=GGUF_FILE,
        token=HF_TOKEN or None,
    )
    print(f"[SERVE] Loading GGUF from {model_path} …", flush=True)
    _llm = Llama(
        model_path=model_path,
        n_ctx=N_CTX,
        n_threads=N_THREADS,
        chat_format="llama-3",
        verbose=False,
    )
    print(f"[SERVE] ✓ Model ready — {GGUF_REPO} ({GGUF_FILE})", flush=True)


def _generate(messages: list) -> str:
    resp = _llm.create_chat_completion(
        messages=messages,
        max_tokens=256,
        temperature=0.6,
        top_p=0.95,
        stop=["<|eot_id|>", "<|end_of_text|>"],
    )
    text = resp["choices"][0]["message"]["content"] or ""
    return re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE).strip()


# ── API ───────────────────────────────────────────────────────────────────────

class AgentRequest(BaseModel):
    observation: dict
    virtualMessages: list = []


@app.post("/agent-action")
def agent_action(req: AgentRequest):
    """Called by frontend Auto-Play and by the /chat endpoint."""
    from inference import build_messages, build_hierarchy_messages, parse_action, _FALLBACKS

    obs  = req.observation
    role = obs.get("active_role", "support_agent")

    if obs.get("hierarchy_state") or role in ("supervisor", "manager"):
        messages = build_hierarchy_messages(obs, role)
    else:
        messages = build_messages(obs)

    raw = ""
    try:
        raw    = _generate(messages)
        action = parse_action(raw)
        return {"action": action, "model": GGUF_REPO}
    except Exception as exc:
        preview = raw[:120] if raw else "(no output)"
        print(f"[SERVE] Error: {exc} | raw={preview!r}", flush=True)
        return {"action": _FALLBACKS.get(role, _FALLBACKS["support_agent"]), "fallback": True}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "model": f"{GGUF_REPO}/{GGUF_FILE}",
        "ready": _llm is not None,
    }


if __name__ == "__main__":
    _load()
    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="warning")
