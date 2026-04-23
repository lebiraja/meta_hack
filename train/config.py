"""
train/config.py — All hyperparameters for the GRPO training pipeline.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class TrainConfig:
    # ── Model ──────────────────────────────────────────────────────────────────
    model_name: str = "unsloth/Qwen3-8B"
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
    group_size: int = 8            # G rollouts per batch item
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
    episodes_per_step: int = 4     # parallel episode batches per gradient step
    grad_accum: int = 4
    max_grad_norm: float = 0.5
    warmup_steps: int = 50

    # ── Generation ────────────────────────────────────────────────────────────
    max_new_tokens: int = 256
    temperature: float = 0.8
    top_p: float = 0.95
    do_sample: bool = True

    # ── Curriculum ────────────────────────────────────────────────────────────
    # Stages in order — advance when eval mean_score >= curriculum_threshold
    curriculum_stages: list = field(default_factory=lambda: [
        "curriculum_basic",
        "curriculum_supervisor",
        "curriculum_full_hierarchy",
        "curriculum_nightmare",
    ])
    curriculum_thresholds: list = field(default_factory=lambda: [
        0.65,   # advance from basic
        0.60,   # advance from supervisor
        0.55,   # advance from full_hierarchy
        # nightmare: final stage, no advancement
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
