"""
train/sft_warmstart.py — Supervised Fine-Tuning warm-start before GRPO.

WHY:
  The hackathon docs explicitly recommend: "do a little SFT first, then RL."
  A warm-start teaches the model the correct action format (JSON) and
  basic task structure before GRPO improves policy quality.

HOW:
  1. Collect "gold" episodes by running the NIM baseline agent against the env
     and keeping only high-scoring completions (final_score >= threshold).
  2. Package them as (prompt, completion) pairs in HuggingFace Dataset format.
  3. Fine-tune with TRL's SFTTrainer for a small number of steps.

Usage:
    # Step 1: Collect gold data (requires running env at localhost:7860)
    python -m train.sft_warmstart --mode collect --n_episodes 200 --out sft_data.jsonl

    # Step 2: Train SFT on collected data
    python -m train.sft_warmstart --mode train --data sft_data.jsonl --steps 500

    # Combined (collect then train)
    python -m train.sft_warmstart --mode all --n_episodes 200 --steps 500
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Optional

import httpx

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


# ── Gold episode collection ───────────────────────────────────────────────────

def _call_env(client: httpx.Client, url: str, method: str, **kwargs) -> dict:
    headers = {"X-API-Key": os.environ.get("ENV_API_KEY", "meta_hack_2026")}
    if method == "POST":
        r = client.post(url, headers=headers, **kwargs)
    else:
        r = client.get(url, headers=headers, **kwargs)
    r.raise_for_status()
    return r.json()


def collect_gold_episodes(
    n_episodes: int = 200,
    score_threshold: float = 0.65,
    tasks: list[str] | None = None,
    env_url: str = "http://localhost:7860",
    out_path: str = "sft_data.jsonl",
) -> int:
    """
    Run the inference agent against the env and keep high-scoring trajectories.
    Returns the number of gold examples collected.

    Each line in out_path is a JSON object:
      { "prompt": "...", "completion": "..." }

    The prompt follows the chat-template format from prompt_builder.py.
    The completion is the raw action JSON the agent produced.
    """
    from train.prompt_builder import build_prompt_string
    from train.env_client import EnvClient, StepResult
    from train.config import TrainConfig
    from train.action_parser import parse_action

    # Try to import the inference module to generate gold actions via NIM
    try:
        import inference as inf_module
        _has_inference = True
    except ImportError:
        _has_inference = False
        print("[WARN] inference.py not found — using random valid actions as placeholder")

    if tasks is None:
        tasks = ["curriculum_basic", "easy", "medium"]

    config = TrainConfig(env_url=env_url)
    env_client = EnvClient(config)

    gold_records: list[dict] = []
    episodes_run = 0
    episodes_accepted = 0

    print(f"[SFT COLLECT] target={n_episodes} threshold={score_threshold}")

    while episodes_accepted < n_episodes:
        task = tasks[episodes_run % len(tasks)]
        episodes_run += 1

        try:
            obs, session_id = env_client.reset(task)
        except Exception as e:
            print(f"[SKIP] reset failed: {e}")
            continue

        episode_records: list[dict] = []
        done = False

        while not done:
            prompt = build_prompt_string(obs, tokenizer=None)

            if _has_inference:
                # Use the NIM agent to generate the gold completion
                try:
                    action_dict = inf_module.get_action(obs.__dict__ if hasattr(obs, '__dict__') else {})
                    completion = json.dumps(action_dict, ensure_ascii=False)
                except Exception:
                    completion = '{"action_type": "respond", "message": "Thank you for contacting us. How can I help?"}'
            else:
                # Fallback: use a simple valid action
                completion = '{"action_type": "respond", "message": "I understand your concern. Let me help you resolve this issue."}'

            action, parse_err = parse_action(completion, getattr(obs, "active_role", "support_agent"))
            if parse_err or action is None:
                break

            try:
                step_result: StepResult = env_client.step(session_id, action)
            except Exception as e:
                print(f"[SKIP] step failed: {e}")
                break

            episode_records.append({"prompt": prompt, "completion": completion})
            obs = step_result.observation
            done = step_result.done

            if done and step_result.final_score and step_result.final_score >= score_threshold:
                gold_records.extend(episode_records)
                episodes_accepted += 1
                if episodes_accepted % 10 == 0:
                    print(f"[SFT COLLECT] {episodes_accepted}/{n_episodes} gold episodes "
                          f"(ran {episodes_run} total, "
                          f"accept rate={episodes_accepted/episodes_run:.1%})")

        if episodes_run > n_episodes * 5:
            print(f"[WARN] Ran {episodes_run} episodes but only got {episodes_accepted} gold. "
                  f"Consider lowering --threshold.")
            break

    # Write to file
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        for rec in gold_records:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")

    print(f"[SFT COLLECT] Done. Wrote {len(gold_records)} examples to {out_path} "
          f"({episodes_run} episodes run, {episodes_accepted} gold)")
    return len(gold_records)


# ── SFT Training ──────────────────────────────────────────────────────────────

def run_sft(
    data_path: str = "sft_data.jsonl",
    output_dir: str = "checkpoints/sft",
    max_steps: int = 500,
    batch_size: int = 4,
    lr: float = 2e-4,
    model_name: str = "unsloth/Qwen3-8B",
    max_seq_len: int = 2048,
):
    """
    Fine-tune the model on gold (prompt, completion) pairs using TRL SFTTrainer.
    Uses Unsloth 4-bit LoRA for efficiency.
    """
    try:
        from unsloth import FastLanguageModel
    except ImportError:
        raise ImportError(
            "unsloth not installed. Run: pip install 'unsloth[cu124-torch240]'"
        )

    from datasets import Dataset
    from trl import SFTTrainer
    from transformers import TrainingArguments

    print(f"\n[SFT TRAIN] model={model_name}")
    print(f"[SFT TRAIN] data={data_path}  steps={max_steps}")

    # ── Load model ─────────────────────────────────────────────────────────────
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=max_seq_len,
        dtype=None,
        load_in_4bit=True,
    )
    model = FastLanguageModel.get_peft_model(
        model,
        r=16,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                         "gate_proj", "up_proj", "down_proj"],
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        use_gradient_checkpointing="unsloth",
    )

    # ── Load dataset ───────────────────────────────────────────────────────────
    records = []
    with open(data_path) as f:
        for line in f:
            rec = json.loads(line.strip())
            # Combine prompt + completion into a single training text
            text = rec["prompt"] + rec["completion"] + tokenizer.eos_token
            records.append({"text": text})

    dataset = Dataset.from_list(records)
    print(f"[SFT TRAIN] Dataset: {len(dataset)} examples")

    # ── Trainer ────────────────────────────────────────────────────────────────
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=dataset,
        dataset_text_field="text",
        max_seq_length=max_seq_len,
        args=TrainingArguments(
            output_dir=output_dir,
            max_steps=max_steps,
            per_device_train_batch_size=batch_size,
            gradient_accumulation_steps=4,
            learning_rate=lr,
            warmup_steps=20,
            fp16=not _is_bfloat16_supported(),
            bf16=_is_bfloat16_supported(),
            logging_steps=10,
            save_steps=250,
            save_total_limit=2,
            report_to="none",
        ),
    )

    print("[SFT TRAIN] Starting training…")
    trainer.train()

    # ── Save ───────────────────────────────────────────────────────────────────
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    model.save_pretrained(output_dir)
    tokenizer.save_pretrained(output_dir)
    print(f"[SFT TRAIN] Done. Saved to {output_dir}")
    print("[SFT TRAIN] To continue with GRPO:")
    print(f"  python -m train.run_train --model {output_dir} --total_steps 5000")


def _is_bfloat16_supported() -> bool:
    try:
        import torch
        return torch.cuda.is_bf16_supported()
    except Exception:
        return False


# ── Entry point ───────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="SFT warm-start before GRPO")
    p.add_argument("--mode", choices=["collect", "train", "all"], default="all")
    p.add_argument("--n_episodes", type=int, default=200,
                   help="Number of gold episodes to collect")
    p.add_argument("--threshold", type=float, default=0.65,
                   help="Minimum final_score to count as gold")
    p.add_argument("--data", default="sft_data.jsonl",
                   help="Path to JSONL dataset")
    p.add_argument("--steps", type=int, default=500,
                   help="SFT training steps")
    p.add_argument("--out_dir", default="checkpoints/sft",
                   help="Output directory for SFT checkpoint")
    p.add_argument("--model", default=os.environ.get("TRAIN_MODEL", "unsloth/Qwen3-8B"))
    p.add_argument("--env_url", default="http://localhost:7860")
    return p.parse_args()


def main():
    args = parse_args()

    if args.mode in ("collect", "all"):
        n = collect_gold_episodes(
            n_episodes=args.n_episodes,
            score_threshold=args.threshold,
            env_url=args.env_url,
            out_path=args.data,
        )
        if n == 0:
            print("[ERROR] No gold episodes collected. Check env is running and threshold.")
            return

    if args.mode in ("train", "all"):
        run_sft(
            data_path=args.data,
            output_dir=args.out_dir,
            max_steps=args.steps,
            model_name=args.model,
        )


if __name__ == "__main__":
    main()
