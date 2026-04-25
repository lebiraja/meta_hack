"""
serve_inference.py — Local model inference server for the frontend Auto-Play.

Runs on port 8001. The frontend's /api/ai-action calls this instead of NIM.

Usage:
    .venv/bin/python serve_inference.py

Environment:
    INFERENCE_MODEL  — model to load (default: TRAIN_MODEL from .env or Qwen2.5-1.5B)
    INFERENCE_PORT   — port to listen on (default: 8001)
"""

import os, re, sys
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Priority: INFERENCE_MODEL env var → merged_model/ dir → TRAIN_MODEL → default
def _resolve_model() -> str:
    if os.getenv("INFERENCE_MODEL"):
        return os.getenv("INFERENCE_MODEL")
    # Auto-detect merged model from training output
    for candidate in ["merged_model", "checkpoints/final"]:
        if os.path.isdir(candidate) and any(
            f.endswith(".safetensors") for f in os.listdir(candidate)
        ):
            print(f"[SERVE] Auto-detected trained model at {candidate}/")
            return candidate
    return os.getenv("TRAIN_MODEL") or "unsloth/Qwen2.5-1.5B-Instruct"

INFERENCE_MODEL = _resolve_model()
PORT = int(os.getenv("INFERENCE_PORT", "8001"))

app = FastAPI(title="Local Inference Server")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Model (loaded once on startup) ────────────────────────────────────────────

_model = None
_tokenizer = None


def _load():
    global _model, _tokenizer
    print(f"[SERVE] Loading {INFERENCE_MODEL}…")
    from unsloth import FastLanguageModel
    _model, _tokenizer = FastLanguageModel.from_pretrained(
        model_name=INFERENCE_MODEL,
        max_seq_length=4096,
        dtype=None,
        load_in_4bit=True,
    )
    FastLanguageModel.for_inference(_model)
    if _tokenizer.pad_token is None:
        _tokenizer.pad_token = _tokenizer.eos_token
    print(f"[SERVE] Model ready on GPU")


def _generate(messages: list) -> str:
    import torch
    try:
        prompt = _tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True, enable_thinking=False,
        )
    except TypeError:
        prompt = _tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True,
        )

    inputs = _tokenizer(prompt, return_tensors="pt").to("cuda")
    with torch.no_grad():
        out = _model.generate(
            **inputs,
            max_new_tokens=256,
            temperature=0.6,
            top_p=0.95,
            do_sample=True,
            pad_token_id=_tokenizer.pad_token_id,
            eos_token_id=_tokenizer.eos_token_id,
        )
    text = _tokenizer.decode(out[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    return re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE).strip()


# ── API ───────────────────────────────────────────────────────────────────────

class AgentRequest(BaseModel):
    observation: dict
    virtualMessages: list = []


@app.post("/agent-action")
def agent_action(req: AgentRequest):
    """Called by the frontend Auto-Play instead of NIM API."""
    from inference import build_messages, build_hierarchy_messages, parse_action, _FALLBACKS

    obs  = req.observation
    role = obs.get("active_role", "support_agent")

    if obs.get("hierarchy_state") or role in ("supervisor", "manager"):
        messages = build_hierarchy_messages(obs, role)
    else:
        messages = build_messages(obs)

    try:
        raw    = _generate(messages)
        action = parse_action(raw)
        return {"action": action}
    except Exception as exc:
        print(f"[SERVE] Error: {exc} | raw={raw!r:.120}" if 'raw' in dir() else f"[SERVE] Error: {exc}")
        return {"action": _FALLBACKS.get(role, _FALLBACKS["support_agent"]), "fallback": True}


@app.get("/health")
def health():
    return {"status": "ok", "model": INFERENCE_MODEL, "ready": _model is not None}


if __name__ == "__main__":
    _load()
    uvicorn.run(app, host="0.0.0.0", port=PORT)
