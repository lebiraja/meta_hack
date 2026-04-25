"""
train/grpo_trainer.py — Core GRPO loss computation.

GRPO (Group Relative Policy Optimization):
  1. Generate G rollouts for the same task
  2. Compute total episode reward for each rollout
  3. Normalize within the group: A_i = (R_i − μ) / (σ + ε)
  4. Apply PPO-clipped policy gradient + KL penalty vs reference model

Loss per token:
    ratio   = exp(log π_θ(a|s) − log π_θ_old(a|s))
    clipped = clip(ratio, 1−ε, 1+ε)
    pg_loss = −A · min(ratio, clipped)
    kl      = log π_θ(a|s) − log π_ref(a|s)
    loss    = pg_loss + β_kl · kl

Total loss = mean over all completion tokens across all steps in all rollouts.
"""

from __future__ import annotations

from typing import List, Tuple

import torch
import torch.nn.functional as F

from train.config import TrainConfig
from train.model_utils import compute_log_probs_from_ids
from train.reward_aggregator import EpisodeRecord, StepRecord


def _seq_log_prob_ids(
    model,
    prompt_ids: torch.Tensor,
    completion_ids: torch.Tensor,
    device: str,
    requires_grad: bool = False,
) -> Tuple[torch.Tensor, int]:
    """
    Compute sequence log-probs from raw token IDs (deterministic — no string
    re-tokenization). Returns (per_token_log_probs, n_tokens).
    Returns zeros tensor of length 1 on failure.
    """
    try:
        lp = compute_log_probs_from_ids(
            model, prompt_ids, completion_ids, device, requires_grad=requires_grad,
        )
        return lp, max(1, lp.shape[0])
    except Exception as e:
        return torch.zeros(1, device=device, requires_grad=True), 1


def grpo_loss(
    rollouts: List[EpisodeRecord],
    advantages: List[float],
    model,
    ref_model,
    tokenizer,
    config: TrainConfig,
    device: str = "cuda",
) -> torch.Tensor:
    """
    Compute the full GRPO loss over a batch of rollouts.

    rollouts:   list of EpisodeRecord (length = episodes_per_step * group_size)
    advantages: list of floats, same length as rollouts
                (already normalised by grpo_advantages())
    """
    total_loss = torch.tensor(0.0, device=device)
    total_tokens = 0
    skipped_empty = 0
    skipped_mismatch = 0
    used = 0

    for episode, adv in zip(rollouts, advantages):
        if episode.invalid or not episode.steps:
            continue

        adv_tensor = torch.tensor(adv, device=device, dtype=torch.float32)

        for step in episode.steps:
            # Need the actual token IDs to recompute log-probs deterministically.
            if (step.prompt_ids is None or step.completion_ids is None
                or not isinstance(step.completion_ids, torch.Tensor)
                or step.completion_ids.shape[0] == 0):
                skipped_empty += 1
                continue

            # ── Current policy log-probs (with gradient) ──────────────────────
            cur_lp, n_tok = _seq_log_prob_ids(
                model, step.prompt_ids, step.completion_ids, device,
                requires_grad=True,
            )

            if cur_lp.shape[0] <= 1 or not cur_lp.requires_grad:
                skipped_empty += 1
                continue

            # ── Old log-probs (at generation time) ────────────────────────────
            # Same completion_ids was used to compute step.log_probs, so length
            # is guaranteed equal — no alignment / mismatch handling needed.
            if step.log_probs is not None and isinstance(step.log_probs, torch.Tensor):
                old_lp = step.log_probs.to(device).detach()
                min_len = min(cur_lp.shape[0], old_lp.shape[0])
                cur_lp_aligned = cur_lp[:min_len]
                old_lp_aligned = old_lp[:min_len]
            else:
                cur_lp_aligned = cur_lp
                old_lp_aligned = cur_lp.detach()

            # ── Reference model log-probs (no gradient) ───────────────────────
            with torch.no_grad():
                ref_lp, _ = _seq_log_prob_ids(
                    ref_model, step.prompt_ids, step.completion_ids, device,
                )
            min_len2 = min(cur_lp.shape[0], ref_lp.shape[0])
            cur_lp_for_kl = cur_lp[:min_len2]
            ref_lp_aligned = ref_lp[:min_len2].to(device)

            # ── PPO-clipped policy gradient ────────────────────────────────────
            log_ratio = cur_lp_aligned - old_lp_aligned
            ratio = log_ratio.exp()
            clipped = ratio.clamp(1.0 - config.clip_eps, 1.0 + config.clip_eps)

            # Standard PPO clip: -min(ratio·A, clip(ratio,1±ε)·A)
            # Do NOT multiply adv_tensor outside — that would square the advantage.
            pg = -torch.min(ratio * adv_tensor, clipped * adv_tensor)

            # ── KL divergence penalty ─────────────────────────────────────────
            kl = cur_lp_for_kl - ref_lp_aligned.detach()

            # ── Combine ───────────────────────────────────────────────────────
            step_loss = pg.mean() + config.kl_coef * kl.mean()
            total_loss = total_loss + step_loss * min(n_tok, cur_lp_aligned.shape[0])
            total_tokens += min(n_tok, cur_lp_aligned.shape[0])
            used += 1

    # Periodic diagnostic: print rate of skipped steps so we can monitor whether
    # the empty-completion / tokenizer-mismatch problem is widespread.
    total_attempted = used + skipped_empty + skipped_mismatch
    if total_attempted > 0:
        skip_rate = (skipped_empty + skipped_mismatch) / total_attempted
        if skip_rate > 0.3:
            grpo_loss._high_skip_warns = getattr(grpo_loss, "_high_skip_warns", 0) + 1  # type: ignore[attr-defined]
            if grpo_loss._high_skip_warns % 20 == 1:  # type: ignore[attr-defined]
                print(
                    f"[GRPO] high skip rate {skip_rate:.0%} "
                    f"(used={used} empty={skipped_empty} mismatch={skipped_mismatch}) — "
                    f"means generation failed or completion_ids were empty"
                )

    if total_tokens == 0:
        return torch.tensor(0.0, device=device, requires_grad=True)

    return total_loss / total_tokens
