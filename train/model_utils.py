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


def compute_log_probs(
    model,
    tokenizer,
    prompt: str,
    completion: str,
    device: str = "cuda",
) -> torch.Tensor:
    """
    Compute per-token log-probabilities of `completion` given `prompt`.

    Returns a 1-D tensor of shape (completion_tokens,).
    """
    full_text = prompt + completion
    enc_full = tokenizer(full_text, return_tensors="pt").to(device)
    enc_prompt = tokenizer(prompt, return_tensors="pt").to(device)

    prompt_len = enc_prompt["input_ids"].shape[1]

    with torch.no_grad():
        out = model(**enc_full)

    logits = out.logits[0]                          # (seq_len, vocab)
    log_probs_all = torch.log_softmax(logits, dim=-1)

    # Completion token positions: prompt_len-1 to seq_len-1 (shift by 1 for next-token)
    comp_ids = enc_full["input_ids"][0, prompt_len:]  # (comp_len,)
    # logits at position t predict token t+1, so we read logits[prompt_len-1 : -1]
    comp_logits_positions = log_probs_all[prompt_len - 1 : prompt_len - 1 + len(comp_ids)]

    if len(comp_logits_positions) == 0 or len(comp_ids) == 0:
        return torch.zeros(1, device=device)

    min_len = min(len(comp_logits_positions), len(comp_ids))
    per_token_lp = comp_logits_positions[:min_len].gather(
        1, comp_ids[:min_len].unsqueeze(1)
    ).squeeze(1)

    return per_token_lp


def model_generate(
    model,
    tokenizer,
    prompt: str,
    config: TrainConfig,
    device: str = "cuda",
) -> Tuple[str, torch.Tensor]:
    """
    Generate a completion for a prompt and return (completion_text, log_probs).

    log_probs: 1-D tensor of per-token log-probs at the time of generation
               (used as π_θ_old in the GRPO ratio computation).
    """
    inputs = tokenizer(prompt, return_tensors="pt").to(device)
    prompt_len = inputs["input_ids"].shape[1]

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

    completion_ids = output_ids[0, prompt_len:]
    completion_text = tokenizer.decode(completion_ids, skip_special_tokens=True)

    # Strip Qwen3 <think>...</think> blocks from the completion text.
    # We train only on the final JSON action, not the chain-of-thought reasoning.
    # Keeping think tokens would waste ~95% of the gradient on non-action text.
    import re as _re
    completion_for_training = _re.sub(
        r"<think>[\s\S]*?</think>", "", completion_text, flags=_re.IGNORECASE
    ).strip()
    if not completion_for_training:
        # Model only output a think block with no action — treat as empty
        completion_for_training = completion_text

    # Compute log-probs for the generated tokens (used as old_log_probs)
    log_probs = compute_log_probs(model, tokenizer, prompt, completion_for_training, device)

    return completion_for_training, log_probs


# ── Checkpointing ─────────────────────────────────────────────────────────────

def save_checkpoint(model, tokenizer, step: int, config: TrainConfig) -> str:
    """Save LoRA adapter weights + tokenizer. Returns the checkpoint path."""
    ckpt_path = Path(config.ckpt_dir) / f"step_{step:06d}"
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
