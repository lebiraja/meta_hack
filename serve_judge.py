"""
serve_judge.py — Local LLM judge server (OpenAI-compatible API).

Loads Qwen2.5-1.5B 4-bit locally and exposes /v1/chat/completions so
env/llm_judge.py can point to localhost:8002 instead of NVIDIA NIM.

Zero changes to judge rubrics — just set JUDGE_BASE_URL=http://localhost:8002/v1

Usage:
    .venv/bin/python serve_judge.py

Then set in .env:
    JUDGE_BASE_URL=http://localhost:8002/v1
    JUDGE_MODEL=local-judge
    JUDGE_API_KEY=local
"""

import os, re, json, time
from dotenv import load_dotenv
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import uvicorn

JUDGE_MODEL_NAME = (
    os.getenv("LOCAL_JUDGE_MODEL")
    or os.getenv("TRAIN_MODEL")
    or "unsloth/Qwen2.5-1.5B-Instruct-unsloth-bnb-4bit"
)
PORT = int(os.getenv("JUDGE_PORT", "8002"))

app = FastAPI(title="Local Judge Server")

_model = None
_tokenizer = None


def _load():
    global _model, _tokenizer
    print(f"[JUDGE] Loading {JUDGE_MODEL_NAME}…")
    from unsloth import FastLanguageModel
    _model, _tokenizer = FastLanguageModel.from_pretrained(
        model_name=JUDGE_MODEL_NAME,
        max_seq_length=1024,
        dtype=None,
        load_in_4bit=True,
    )
    FastLanguageModel.for_inference(_model)
    if _tokenizer.pad_token is None:
        _tokenizer.pad_token = _tokenizer.eos_token
    print(f"[JUDGE] Ready on GPU — listening on :{PORT}")


def _generate(messages: list, max_new_tokens: int = 150) -> str:
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
            max_new_tokens=max_new_tokens,
            temperature=0.1,
            do_sample=False,
            pad_token_id=_tokenizer.pad_token_id,
            eos_token_id=_tokenizer.eos_token_id,
        )
    text = _tokenizer.decode(out[0, inputs["input_ids"].shape[1]:], skip_special_tokens=True)
    # Strip thinking tags if any
    text = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE).strip()
    return text


# ── OpenAI-compatible /v1/chat/completions ─────────────────────────────────────

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    body = await request.json()
    messages = body.get("messages", [])
    max_tokens = body.get("max_tokens", 150)
    model = body.get("model", "local-judge")

    t0 = time.time()
    try:
        content = _generate(messages, max_new_tokens=max_tokens)
    except Exception as e:
        content = '{"score": 0.5, "reason": "local judge error"}'
        print(f"[JUDGE] Generation error: {e}")

    elapsed = time.time() - t0
    print(f"[JUDGE] {elapsed*1000:.0f}ms → {content[:80]}")

    return JSONResponse({
        "id": f"local-{int(t0)}",
        "object": "chat.completion",
        "created": int(t0),
        "model": model,
        "choices": [{
            "index": 0,
            "message": {"role": "assistant", "content": content},
            "finish_reason": "stop",
        }],
        "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
    })


@app.get("/v1/models")
def list_models():
    return {"object": "list", "data": [{"id": "local-judge", "object": "model"}]}


@app.get("/health")
def health():
    return {"status": "ok", "model": JUDGE_MODEL_NAME, "ready": _model is not None}


if __name__ == "__main__":
    _load()
    uvicorn.run(app, host="0.0.0.0", port=PORT)
