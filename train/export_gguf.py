"""
train/export_gguf.py — Export a merged 16-bit model to GGUF Q4_K_M and push to HF.

Usage:
    python -m train.export_gguf \\
        --model /workspace/merged_model \\
        --out   /workspace/merged_model/gguf/model-q4_k_m.gguf \\
        --quant q4_k_m \\
        --push \\
        --repo  lebiraja/customer-support-grpo-v2-gguf \\
        --token hf_xxx

The pushed repo follows the standard HF GGUF convention, making the model
compatible with:
  - ollama run hf.co/lebiraja/customer-support-grpo-v2-gguf
  - Llama.from_pretrained("lebiraja/customer-support-grpo-v2-gguf", filename="model-q4_k_m.gguf")
  - Any llama.cpp-based tool
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path


MODEL_CARD = """\
---
language:
- en
license: apache-2.0
tags:
- customer-support
- gguf
- llama-cpp
- q4_k_m
base_model: unsloth/Meta-Llama-3.1-8B-Instruct-bnb-4bit
---

# customer-support-grpo-v2-gguf

GGUF Q4_K_M quantization of [lebiraja/customer-support-grpo-v2](https://huggingface.co/lebiraja/customer-support-grpo-v2).

Fine-tuned with GRPO reinforcement learning on a customer support environment.
Trained to handle multi-level support hierarchies (L1 agent → L2 supervisor → L3 manager).

## Usage

### Ollama (direct from HuggingFace)
```bash
ollama run hf.co/lebiraja/customer-support-grpo-v2-gguf
```

### llama-cpp-python
```python
from llama_cpp import Llama

llm = Llama.from_pretrained(
    repo_id="lebiraja/customer-support-grpo-v2-gguf",
    filename="model-q4_k_m.gguf",
    n_ctx=2048,
)
response = llm("Customer: I was charged twice. Agent:", max_tokens=128)
print(response["choices"][0]["text"])
```

### llama.cpp CLI
```bash
./llama-cli -m model-q4_k_m.gguf -p "Customer: I was charged twice. Agent:" -n 128
```

## Model Details
- Base: Meta-Llama-3.1-8B-Instruct
- Training: GRPO (Group Relative Policy Optimization)
- Quantization: Q4_K_M (~4.5 GB)
- Context: 4096 tokens
"""


def export_gguf(
    model_path: str,
    out_path: str,
    quant: str = "q4_k_m",
    push: bool = False,
    repo: str = "",
    token: str = "",
):
    from unsloth import FastLanguageModel

    print(f"\n[GGUF] Loading merged model from {model_path} ...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_path,
        max_seq_length=4096,
        load_in_4bit=False,
    )

    out_dir = Path(out_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    print(f"[GGUF] Quantizing to {quant.upper()} → {out_path} ...")
    # Unsloth saves to {model_path}_gguf/ directory, NOT to out_dir
    model.save_pretrained_gguf(model_path, tokenizer, quantization_method=quant)

    # Locate the generated file — Unsloth creates {model_path}_gguf/{name}.{QUANT}.gguf
    model_basename = Path(model_path).name
    unsloth_out_dir = Path(model_path).parent / f"{model_basename}_gguf"
    generated = list(unsloth_out_dir.glob("*.gguf")) if unsloth_out_dir.exists() else []
    if not generated:
        # Fallback: search parent directory
        generated = list(Path(model_path).parent.rglob("*.gguf"))

    if not generated:
        raise FileNotFoundError(f"No GGUF file found after export. Checked: {unsloth_out_dir}")

    src = generated[0]
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    src.rename(out_path)
    print(f"[GGUF] Moved {src} → {out_path}")

    print(f"[GGUF] Export complete: {out_path} ({Path(out_path).stat().st_size / 1e9:.1f} GB)")

    if push and repo and token:
        print(f"[GGUF] Pushing to HF: {repo} ...")
        from huggingface_hub import HfApi

        api = HfApi(token=token)
        api.create_repo(repo_id=repo, repo_type="model", exist_ok=True, private=False)

        # Push GGUF file
        api.upload_file(
            path_or_fileobj=out_path,
            path_in_repo=Path(out_path).name,
            repo_id=repo,
            repo_type="model",
        )

        # Push model card
        card_path = out_dir / "README.md"
        card_path.write_text(MODEL_CARD)
        api.upload_file(
            path_or_fileobj=str(card_path),
            path_in_repo="README.md",
            repo_id=repo,
            repo_type="model",
        )

        print(f"[GGUF] Pushed to https://huggingface.co/{repo} ✓")
        print(f"[GGUF] Run with: ollama run hf.co/{repo}")


def main():
    p = argparse.ArgumentParser(description="Export merged model to GGUF and optionally push to HF")
    p.add_argument("--model",  required=True, help="Path to merged 16-bit model")
    p.add_argument("--out",    required=True, help="Output .gguf path")
    p.add_argument("--quant",  default="q4_k_m", help="Quantization method (default: q4_k_m)")
    p.add_argument("--push",   action="store_true", help="Push to HuggingFace Hub")
    p.add_argument("--repo",   default="", help="HF repo id, e.g. username/model-name-gguf")
    p.add_argument("--token",  default=os.environ.get("HF_TOKEN", ""), help="HF token")
    args = p.parse_args()

    export_gguf(
        model_path=args.model,
        out_path=args.out,
        quant=args.quant,
        push=args.push,
        repo=args.repo,
        token=args.token,
    )


if __name__ == "__main__":
    main()
