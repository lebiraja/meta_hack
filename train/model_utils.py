"""
train/model_utils.py — Unsloth + LoRA model loading and checkpoint management.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Tuple

import torch

from train.config import TrainConfig


def load_model(config: TrainConfig):
    """
    Load the policy model with Unsloth 4-bit LoRA.
    Returns (model, tokenizer).
    """
    try:
        from unsloth import FastLanguageModel
    except ImportError as e:
        raise ImportError(
            "unsloth is required for training. Install with:\n"
            "  uv sync --extra train\n"
            "or: pip install 'unsloth[cu124-torch240]'"
        ) from e

    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=config.model_name,
        max_seq_length=config.max_seq_len,
        dtype=None,                         # auto-detect bfloat16/float16
        load_in_4bit=config.load_in_4bit,
    )

    model = FastLanguageModel.get_peft_model(
        model,
        r=config.lora_r,
        target_modules=[
            "q_proj", "k_proj", "v_proj", "o_proj",
            "gate_proj", "up_proj", "down_proj",
        ],
        lora_alpha=config.lora_alpha,
        lora_dropout=config.lora_dropout,
        bias="none",
        use_gradient_checkpointing="unsloth",   # 2× longer context at same VRAM
        random_state=42,
    )

    # Ensure pad token exists (Llama has no pad token by default)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id

    return model, tokenizer


def load_ref_model(config: TrainConfig):
    """
    Load the frozen reference model for KL divergence penalty.
    Same base weights as policy, no LoRA, all parameters frozen.
    """
    try:
        from unsloth import FastLanguageModel
    except ImportError as e:
        raise ImportError("unsloth required") from e

    ref_model, _ = FastLanguageModel.from_pretrained(
        model_name=config.model_name,
        max_seq_length=config.max_seq_len,
        dtype=None,
        load_in_4bit=config.load_in_4bit,
    )
    for p in ref_model.parameters():
        p.requires_grad_(False)
    ref_model.eval()
    return ref_model


def compute_log_probs_from_ids(
    model,
    prompt_ids: torch.Tensor,        # shape (P,) or (1, P)
    completion_ids: torch.Tensor,    # shape (C,)
    device: str = "cuda",
    requires_grad: bool = False,
) -> torch.Tensor:
    """
    Compute per-token log-probabilities of completion_ids given prompt_ids.

    Uses the EXACT token sequences (no string re-tokenization), so the result
    is deterministic and the length always equals C. This avoids the BPE
    boundary bug that plagues prompt+completion string concatenation.

    Returns a 1-D tensor of shape (C,) — log p(completion_ids[i] | prompt_ids, completion_ids[:i]).
    """
    if prompt_ids.dim() == 1:
        prompt_ids = prompt_ids.unsqueeze(0)
    prompt_ids = prompt_ids.to(device)
    completion_ids = completion_ids.to(device)

    P = prompt_ids.shape[1]
    C = completion_ids.shape[0]
    if C == 0:
        return torch.zeros(1, device=device, requires_grad=requires_grad)

    full_ids = torch.cat([prompt_ids, completion_ids.unsqueeze(0)], dim=1)  # (1, P+C)

    if requires_grad:
        out = model(input_ids=full_ids)
    else:
        with torch.no_grad():
            out = model(input_ids=full_ids)

    logits = out.logits[0]                                  # (P+C, vocab)
    log_probs_all = torch.log_softmax(logits, dim=-1)

    # Position t predicts token t+1. Completion tokens are at absolute positions
    # [P, P+1, ..., P+C-1]. Their predicting logits sit at [P-1, P, ..., P+C-2].
    comp_logit_positions = log_probs_all[P - 1 : P + C - 1]  # (C, vocab)
    per_token_lp = comp_logit_positions.gather(
        1, completion_ids.unsqueeze(1)
    ).squeeze(1)                                            # (C,)
    return per_token_lp


# Backward-compat shim: the old string-based API is kept only so any stale
# import doesn't crash. New code paths must use compute_log_probs_from_ids.
def compute_log_probs(
    model,
    tokenizer,
    prompt: str,
    completion: str,
    device: str = "cuda",
    requires_grad: bool = False,
) -> torch.Tensor:
    enc_prompt = tokenizer(prompt, return_tensors="pt").to(device)
    enc_comp = tokenizer(completion, add_special_tokens=False, return_tensors="pt").to(device)
    return compute_log_probs_from_ids(
        model, enc_prompt["input_ids"], enc_comp["input_ids"][0], device, requires_grad
    )


def model_generate(
    model,
    tokenizer,
    prompt: str,
    config: TrainConfig,
    device: str = "cuda",
) -> Tuple[str, torch.Tensor, torch.Tensor, torch.Tensor]:
    """
    Generate a completion. Returns (completion_text, prompt_ids, completion_ids, log_probs).

    completion_text — the decoded string with <think> blocks stripped, used by
                      the action parser. May differ from completion_ids.
    prompt_ids      — exact tokenized prompt (1-D tensor on device).
    completion_ids  — exact generated tokens from model.generate (1-D, on device).
    log_probs       — per-token log-probs aligned with completion_ids (1-D, on device).

    Storing prompt_ids + completion_ids is what lets grpo_loss recompute
    log-probs deterministically — no string round-trip, no BPE boundary bug.
    """
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    prompt_ids = inputs["input_ids"]                # (1, P)
    P = prompt_ids.shape[1]

    with torch.no_grad():
        output_ids = model.generate(
            **inputs,
            max_new_tokens=config.max_new_tokens,
            temperature=config.temperature,
            top_p=config.top_p,
            do_sample=config.do_sample,
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )

    completion_ids = output_ids[0, P:].detach()      # (C,)
    completion_text = tokenizer.decode(completion_ids, skip_special_tokens=True)

    # Strip <think>...</think> blocks for the parser. We still train on the
    # full completion_ids (think tokens included) — this matches what the
    # model actually generated and keeps the log-prob math consistent.
    import re as _re
    parsed_text = _re.sub(
        r"<think>[\s\S]*?</think>", "", completion_text, flags=_re.IGNORECASE
    ).strip() or completion_text

    # Compute old log-probs from the actual generated IDs (no re-tokenization)
    log_probs = compute_log_probs_from_ids(
        model, prompt_ids, completion_ids, device, requires_grad=False
    ).detach()

    # .clone() converts inference-mode tensors to regular tensors so they can
    # participate in autograd when reused in grpo_loss (for_inference uses
    # torch.inference_mode() internally, which marks tensors as non-autograd).
    return parsed_text, prompt_ids[0].detach().clone(), completion_ids.clone(), log_probs.clone()


# ── Checkpointing ─────────────────────────────────────────────────────────────

def save_checkpoint(model, tokenizer, step: int, config: TrainConfig, tag: str | None = None) -> str:
    """Save LoRA adapter weights + tokenizer. Returns the checkpoint path."""
    name = tag if tag else f"step_{step:06d}"
    ckpt_path = Path(config.ckpt_dir) / name
    ckpt_path.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(ckpt_path))
    tokenizer.save_pretrained(str(ckpt_path))
    print(f"[CKPT] Saved checkpoint: {ckpt_path}")
    return str(ckpt_path)


def load_checkpoint(model, tokenizer, ckpt_path: str):
    """Load LoRA adapter weights from a checkpoint directory."""
    from peft import PeftModel
    model = PeftModel.from_pretrained(model, ckpt_path)
    print(f"[CKPT] Loaded checkpoint: {ckpt_path}")
    return model, tokenizer
