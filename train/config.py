"""
train/config.py — All hyperparameters for the GRPO training pipeline.

Model selection (in priority order):
  1. --model CLI arg  (run_train.py overrides config.model_name after init)
  2. TRAIN_MODEL env var  (set in .env or as HF Space secret)
  3. Default: unsloth/Qwen3-8B  (production / HF Spaces)

Local testing on small GPU (≤6GB VRAM):
  export TRAIN_MODEL=unsloth/Qwen2.5-1.5B-Instruct   # ~1GB at 4-bit
  export TRAIN_MODEL=unsloth/Qwen2.5-3B-Instruct     # ~2GB at 4-bit
"""

import os
from dataclasses import dataclass, field
from typing import Optional

_DEFAULT_MODEL = "unsloth/Qwen3-8B"


@dataclass
class TrainConfig:
    # ── Model ──────────────────────────────────────────────────────────────────
    model_name: str = os.environ.get("TRAIN_MODEL", _DEFAULT_MODEL)
    max_seq_len: int = 4096
    lora_r: int = 16
    lora_alpha: int = 32
    lora_dropout: float = 0.05
    load_in_4bit: bool = True

    # ── Environment API ────────────────────────────────────────────────────────
    env_url: str = "http://localhost:7860"
    api_key: str = "meta_hack_2026"
    env_timeout: int = 60          # seconds per /step call

    # ── GRPO ──────────────────────────────────────────────────────────────────
    group_size: int = 4            # G rollouts per batch item
    clip_eps: float = 0.2          # PPO clip epsilon
    kl_coef: float = 0.04          # KL penalty weight vs reference model

    # ── Reward aggregation ────────────────────────────────────────────────────
    # R_episode = step_weight * Σ(γ^t * r_t)  +  terminal_weight * final_score
    step_weight: float = 0.30
    terminal_weight: float = 0.70
    gamma: float = 0.95            # discount factor
    invalid_penalty: float = -0.5  # reward for unparseable / wrong-role actions

    # ── Training schedule ─────────────────────────────────────────────────────
    learning_rate: float = 5e-5
    total_steps: int = 5000
    episodes_per_step: int = 1     # episode batches per gradient step
    grad_accum: int = 2
    max_grad_norm: float = 0.5
    warmup_steps: int = 50

    # ── Parallel rollout collection ───────────────────────────────────────────
    # Number of threads to use for parallel episode collection.
    # Set to 1 to disable parallelism (useful for debugging).
    rollout_workers: int = 4

    # ── Local judge (Qwen3-1.5B) ─────────────────────────────────────────────
    # When set, loads a small local model for intermediate step evaluation
    # instead of calling the API judge. API judge is still used at terminal step.
    # Set to "" to disable local judge (use API judge for all steps — slower).
    local_judge_model: str = os.environ.get("LOCAL_JUDGE_MODEL", "unsloth/Qwen3-1.5B-Instruct")

    # ── Generation ────────────────────────────────────────────────────────────
    max_new_tokens: int = 128
    temperature: float = 0.8
    top_p: float = 0.95
    do_sample: bool = True

    # ── Curriculum ────────────────────────────────────────────────────────────
    # Stages in order — advance when eval mean_score >= curriculum_threshold
    curriculum_stages: list = field(default_factory=lambda: [
        "curriculum_basic",           # stage 0: L1 only, no drift
        "curriculum_supervisor",      # stage 1: L1+L2, 20% drift
        "curriculum_full_hierarchy",  # stage 2: L1+L2+L3, 80% drift
        "curriculum_nightmare",       # stage 3: all levels, 100% drift, Hinglish
        "multi_domain",               # stage 4: DB-grounded queries, 30 diverse tickets
    ])
    curriculum_thresholds: list = field(default_factory=lambda: [
        0.65,   # advance from basic
        0.60,   # advance from supervisor
        0.55,   # advance from full_hierarchy
        0.50,   # advance from nightmare → multi_domain
        # multi_domain: final stage, no advancement
    ])
    eval_interval: int = 100       # gradient steps between evals
    eval_episodes: int = 50
    ckpt_interval: int = 200
    ckpt_dir: str = "checkpoints"

    # Safety: if mean_score < recovery_threshold for recovery_window steps → halve LR
    recovery_threshold: float = 0.30
    recovery_window: int = 200

    # ── Logging ───────────────────────────────────────────────────────────────
    wandb_project: str = "meta_hack_grpo"
    wandb_run_name: Optional[str] = None
    log_interval: int = 10
    use_wandb: bool = True
