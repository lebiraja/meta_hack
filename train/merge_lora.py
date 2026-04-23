"""
train/merge_lora.py — Merge LoRA adapters into the base model for deployment.

WHY:
  After GRPO training, the checkpoint contains LoRA adapter weights only.
  To serve the model (HuggingFace Space, inference.py, etc.) you need to
  merge the adapter into the base weights.

  WARNING: Do NOT naively upcast 4-bit → 16-bit then merge. This degrades
  quality. Use Unsloth's built-in merge path instead.

Usage:
    # Merge latest GRPO checkpoint
    python -m train.merge_lora --ckpt checkpoints/step_5000 --out merged_model/

    # Merge SFT warmstart checkpoint
    python -m train.merge_lora --ckpt checkpoints/sft --out merged_model/sft/

    # Push to HuggingFace Hub after merging
    python -m train.merge_lora --ckpt checkpoints/step_5000 --out merged_model/ --push --repo your-hf-name/model-name
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path


def merge_and_save(
    ckpt_dir: str,
    out_dir: str,
    model_name: str | None = None,
    push_to_hub: bool = False,
    hub_repo: str | None = None,
    hf_token: str | None = None,
):
    """
    Merge LoRA adapters into the base model and save as a standard HF model.

    Uses Unsloth's save_pretrained_merged which correctly handles 4-bit models.
    """
    try:
        from unsloth import FastLanguageModel
    except ImportError:
        raise ImportError(
            "unsloth not installed. Run: pip install 'unsloth[cu124-torch240]'"
        )

    ckpt_path = Path(ckpt_dir)
    out_path  = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    # Detect model name from the adapter config if not provided
    if model_name is None:
        adapter_config = ckpt_path / "adapter_config.json"
        if adapter_config.exists():
            import json
            cfg = json.loads(adapter_config.read_text())
            model_name = cfg.get("base_model_name_or_path", "unsloth/Meta-Llama-3.1-8B-Instruct")
        else:
            model_name = "unsloth/Meta-Llama-3.1-8B-Instruct"

    print(f"[MERGE] base model : {model_name}")
    print(f"[MERGE] adapters   : {ckpt_dir}")
    print(f"[MERGE] output     : {out_dir}")

    # Load with LoRA adapters
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=str(ckpt_path),
        max_seq_length=4096,
        dtype=None,
        load_in_4bit=True,
    )

    # Merge using Unsloth's correct path (does NOT naively upcast 4-bit)
    print("[MERGE] Merging adapters into base weights…")
    model.save_pretrained_merged(
        str(out_path),
        tokenizer,
        save_method="merged_16bit",   # fp16 merged model, safe to serve
    )

    print(f"[MERGE] Done. Merged model saved to {out_dir}")

    if push_to_hub:
        if not hub_repo:
            raise ValueError("--repo is required when using --push")
        token = hf_token or os.environ.get("HF_TOKEN")
        if not token:
            raise ValueError("HF_TOKEN env var or --token required for push")

        print(f"[MERGE] Pushing to HuggingFace Hub: {hub_repo}")
        model.push_to_hub_merged(
            hub_repo,
            tokenizer,
            save_method="merged_16bit",
            token=token,
        )
        print(f"[MERGE] Pushed to https://huggingface.co/{hub_repo}")


def parse_args():
    p = argparse.ArgumentParser(description="Merge LoRA adapters into base model")
    p.add_argument("--ckpt", required=True, help="Path to LoRA checkpoint directory")
    p.add_argument("--out",  required=True, help="Output directory for merged model")
    p.add_argument("--model", default=None, help="Base model name (auto-detected if omitted)")
    p.add_argument("--push", action="store_true", help="Push merged model to HuggingFace Hub")
    p.add_argument("--repo", default=None, help="HuggingFace repo (e.g. lebiraja/customer-support-grpo)")
    p.add_argument("--token", default=None, help="HuggingFace API token (or set HF_TOKEN env var)")
    return p.parse_args()


def main():
    args = parse_args()
    merge_and_save(
        ckpt_dir=args.ckpt,
        out_dir=args.out,
        model_name=args.model,
        push_to_hub=args.push,
        hub_repo=args.repo,
        hf_token=args.token,
    )


if __name__ == "__main__":
    main()
