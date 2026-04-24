"""
train/reward_aggregator.py — Aggregate per-step rewards + terminal grader score
into a single scalar for GRPO advantage computation.

Formula:
    R_episode = α · Σ(t=0..T) γᵗ · R_step(t)   +   β · R_final

where:
    α = config.step_weight      (default 0.30)
    β = config.terminal_weight  (default 0.70)
    γ = config.gamma            (default 0.95)
    R_step(t) = reward.value from /step at step t
    R_final   = final_score from /step when done=True (0.0 if not available)

Invalid episodes (parse errors / wrong role actions) return config.invalid_penalty.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from train.config import TrainConfig
from train.env_client import StepResult


@dataclass
class EpisodeRecord:
    """All data collected during a single episode rollout."""
    steps: List["StepRecord"] = field(default_factory=list)
    invalid: bool = False           # True if first action was unparseable
    invalid_reason: str = ""
    task: str = ""


@dataclass
class StepRecord:
    """Data for one step within an episode."""
    prompt: str
    completion: str
    log_probs: object          # torch.Tensor of shape (comp_tokens,)
    completion_len: int
    reward_value: float
    done: bool
    final_score: Optional[float]
    # Component scores (for logging only)
    empathy_score: float = 0.0
    policy_adherence_score: float = 0.0
    resolution_score: float = 0.0
    tone_score: float = 0.0
    efficiency_score: float = 0.0
    accuracy_score: float = 0.0
    role_rewards: dict = field(default_factory=dict)
    # DB grounding signals (non-zero only during multi_domain episodes)
    db_signals: dict = field(default_factory=dict)


def aggregate_reward(episode: EpisodeRecord, config: TrainConfig) -> float:
    """
    Compute the scalar reward for a full episode.

    GRPO uses this scalar to compute group-normalised advantages.
    """
    if episode.invalid:
        return config.invalid_penalty

    if not episode.steps:
        return 0.0

    # Discounted average of per-step rewards (normalized to [0,1] regardless of episode length)
    # Using average (not sum) so that step_weight actually means what it says: if step_weight=0.30
    # then step rewards contribute 30% of total signal regardless of episode length.
    n = len(episode.steps)
    discounted_sum = sum(
        (config.gamma ** t) * s.reward_value
        for t, s in enumerate(episode.steps)
    )
    normalizer = sum(config.gamma ** t for t in range(n)) or 1.0
    step_avg = discounted_sum / normalizer  # weighted average, stays in [0,1]

    # Terminal grader score (only present on the last step when done=True)
    final_score = episode.steps[-1].final_score or 0.0

    return config.step_weight * step_avg + config.terminal_weight * final_score


def grpo_advantages(rewards: List[float], eps: float = 1e-8) -> List[float]:
    """
    Compute GRPO group-normalised advantages.

    A_i = (R_i − μ) / (σ + ε)

    If all rewards in the group are identical (σ = 0), all advantages are 0.
    """
    if not rewards:
        return []
    n = len(rewards)
    mu = sum(rewards) / n
    var = sum((r - mu) ** 2 for r in rewards) / n
    sigma = var ** 0.5
    return [(r - mu) / (sigma + eps) for r in rewards]
