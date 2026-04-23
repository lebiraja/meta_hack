"""
train/run_train.py — Entry point for GRPO training.

Usage:
    # Full curriculum run (5000 steps)
    python -m train.run_train

    # Single-stage short run
    python -m train.run_train --task curriculum_basic --total_steps 100 --group_size 4

    # Smoke test: single rollout (no gradient update)
    python -m train.run_train --mode rollout_test --task curriculum_basic

    # Smoke test: GRPO loss computation (fake rewards, no env)
    python -m train.run_train --mode loss_test
"""

from __future__ import annotations

import argparse
import os
import sys
import time
from dataclasses import asdict
from pathlib import Path

import torch
from torch.optim import AdamW
from torch.optim.lr_scheduler import CosineAnnealingLR

from train.config import TrainConfig
from train.curriculum import CurriculumScheduler
from train.env_client import EnvClient
from train.evaluate import evaluate
from train.grpo_trainer import grpo_loss
from train.model_utils import load_model, load_ref_model, save_checkpoint
from train.reward_aggregator import EpisodeRecord, aggregate_reward, grpo_advantages
from train.rollout_collector import collect_group, run_one_episode


# ── Argument parsing ──────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="GRPO training for customer-support-env")
    p.add_argument("--mode", default="train",
                   choices=["train", "rollout_test", "loss_test"],
                   help="train=full training, rollout_test=single episode, loss_test=loss smoke")
    p.add_argument("--model",         default=None, help="Override model_name")
    p.add_argument("--task",          default=None, help="Override starting task")
    p.add_argument("--total_steps",   type=int, default=None)
    p.add_argument("--group_size",    type=int, default=None)
    p.add_argument("--lr",            type=float, default=None)
    p.add_argument("--episodes",      type=int, default=None,
                   help="Episodes per gradient step (episodes_per_step)")
    p.add_argument("--no_wandb",      action="store_true")
    p.add_argument("--ckpt_dir",      default=None)
    p.add_argument("--device",        default="cuda" if torch.cuda.is_available() else "cpu")
    return p.parse_args()


# ── Wandb helper ──────────────────────────────────────────────────────────────

def init_wandb(config: TrainConfig, args):
    if not config.use_wandb:
        return None
    try:
        import wandb
        run = wandb.init(
            project=config.wandb_project,
            name=config.wandb_run_name or f"grpo_{int(time.time())}",
            config=asdict(config) if hasattr(config, "__dataclass_fields__") else vars(config),
        )
        return wandb
    except Exception as e:
        print(f"[WARN] wandb init failed: {e} — continuing without logging")
        return None


def log_wandb(wb, step: int, data: dict):
    if wb is None:
        return
    try:
        wb.log({"step": step, **data})
    except Exception:
        pass


# ── Smoke tests ───────────────────────────────────────────────────────────────

def rollout_test(config: TrainConfig, task: str, device: str):
    """Run a single episode and print each step."""
    print(f"\n[ROLLOUT TEST] task={task} model={config.model_name}")
    model, tokenizer = load_model(config)
    env_client = EnvClient(config)
    ep = run_one_episode(model, tokenizer, env_client, task, config, device, verbose=True)
    if ep.invalid:
        print(f"[INVALID] {ep.invalid_reason}")
    else:
        final = ep.steps[-1].final_score or 0.0
        print(f"\n[DONE] steps={len(ep.steps)} final_score={final:.3f}")
        reward = aggregate_reward(ep, config)
        print(f"[REWARD] R_episode={reward:.4f}")


def loss_test(config: TrainConfig, device: str):
    """Compute GRPO loss on fake data to verify the training loop."""
    print(f"\n[LOSS TEST] model={config.model_name}")
    model, tokenizer = load_model(config)
    ref_model = load_ref_model(config)

    # Build fake episodes with random rewards
    import random
    from train.reward_aggregator import StepRecord

    fake_episodes = []
    for _ in range(4):
        ep = EpisodeRecord(task="curriculum_basic")
        ep.steps = [
            StepRecord(
                prompt="Fake prompt",
                completion='{"action_type": "respond", "message": "Hello"}',
                log_probs=torch.zeros(5, device=device),
                completion_len=5,
                reward_value=random.uniform(0.2, 0.8),
                done=True,
                final_score=random.uniform(0.3, 0.9),
            )
        ]
        fake_episodes.append(ep)

    rewards = [aggregate_reward(ep, config) for ep in fake_episodes]
    advantages = grpo_advantages(rewards)
    print(f"[LOSS TEST] rewards={[f'{r:.3f}' for r in rewards]}")
    print(f"[LOSS TEST] advantages={[f'{a:.3f}' for a in advantages]}")

    loss = grpo_loss(fake_episodes, advantages, model, ref_model, tokenizer, config, device)
    print(f"[LOSS TEST] loss={loss.item():.6f}")
    loss.backward()
    print("[LOSS TEST] backward() OK — gradients computed successfully")


# ── Main training loop ────────────────────────────────────────────────────────

def train(config: TrainConfig, start_task: str | None, device: str):
    print(f"\n{'='*60}")
    print(f"GRPO Training — {config.model_name}")
    print(f"Device: {device}")
    print(f"Total steps: {config.total_steps}")
    print(f"Group size: {config.group_size}")
    print(f"LR: {config.learning_rate}")
    print(f"{'='*60}\n")

    # ── Setup ─────────────────────────────────────────────────────────────────
    model, tokenizer = load_model(config)
    ref_model = load_ref_model(config)
    model.to(device)
    ref_model.to(device)

    optimizer = AdamW(
        filter(lambda p: p.requires_grad, model.parameters()),
        lr=config.learning_rate,
        weight_decay=0.01,
    )
    scheduler = CosineAnnealingLR(
        optimizer,
        T_max=config.total_steps,
        eta_min=config.learning_rate * 0.1,
    )

    env_client = EnvClient(config)
    curriculum = CurriculumScheduler(
        config.curriculum_stages,
        config.curriculum_thresholds,
    )
    if start_task and start_task in config.curriculum_stages:
        # Jump to the specified starting stage
        idx = config.curriculum_stages.index(start_task)
        curriculum._stage_idx = idx
        print(f"[CURRICULUM] Starting at stage {idx}: {start_task}")

    wb = init_wandb(config, None)

    # ── Training loop ─────────────────────────────────────────────────────────
    grad_step = 0
    accum_loss = 0.0
    accum_count = 0

    for global_step in range(config.total_steps * config.grad_accum):
        task = curriculum.current_task()

        # ── Collect rollouts (episodes_per_step × group_size episodes) ────────
        all_episodes: list[EpisodeRecord] = []
        all_advantages: list[float] = []

        for _ in range(config.episodes_per_step):
            group = collect_group(model, tokenizer, env_client, task, config, device)
            rewards = [aggregate_reward(ep, config) for ep in group]
            advantages = grpo_advantages(rewards)
            all_episodes.extend(group)
            all_advantages.extend(advantages)

        # ── Compute GRPO loss ─────────────────────────────────────────────────
        model.train()
        loss = grpo_loss(
            all_episodes, all_advantages,
            model, ref_model, tokenizer, config, device
        )

        (loss / config.grad_accum).backward()
        accum_loss += loss.item()
        accum_count += 1

        # ── Gradient update ───────────────────────────────────────────────────
        if (global_step + 1) % config.grad_accum == 0:
            torch.nn.utils.clip_grad_norm_(
                filter(lambda p: p.requires_grad, model.parameters()),
                config.max_grad_norm,
            )
            optimizer.step()
            scheduler.step()
            optimizer.zero_grad()
            grad_step += 1

            # ── Logging ───────────────────────────────────────────────────────
            if grad_step % config.log_interval == 0:
                mean_loss = accum_loss / max(1, accum_count)
                valid_eps = [e for e in all_episodes if not e.invalid and e.steps]
                mean_reward = (
                    sum(aggregate_reward(e, config) for e in valid_eps) / len(valid_eps)
                    if valid_eps else 0.0
                )
                invalid_rate = sum(1 for e in all_episodes if e.invalid) / max(1, len(all_episodes))
                lr_now = optimizer.param_groups[0]["lr"]

                cs = curriculum.status()
                print(
                    f"[step {grad_step:05d}] "
                    f"stage={cs['stage']} task={cs['task']} "
                    f"loss={mean_loss:.4f} "
                    f"reward={mean_reward:.3f} "
                    f"invalid={invalid_rate:.2f} "
                    f"lr={lr_now:.2e}"
                )
                log_wandb(wb, grad_step, {
                    "train/loss": mean_loss,
                    "train/mean_reward": mean_reward,
                    "train/invalid_rate": invalid_rate,
                    "train/lr": lr_now,
                    "curriculum/stage": cs["stage"],
                })
                accum_loss = 0.0
                accum_count = 0

            # ── Eval & curriculum advancement ──────────────────────────────────
            if grad_step % config.eval_interval == 0:
                print(f"\n[EVAL] step={grad_step} task={curriculum.current_task()}")
                model.eval()
                result = evaluate(model, tokenizer, env_client, curriculum.current_task(),
                                  config, device=device)
                model.train()

                print(
                    f"[EVAL] mean_score={result.mean_final_score:.3f} "
                    f"mean_step={result.mean_step_reward:.3f} "
                    f"empathy={result.mean_empathy:.3f} "
                    f"policy={result.mean_policy:.3f} "
                    f"invalid_rate={result.invalid_rate:.2f}"
                )
                log_wandb(wb, grad_step, {
                    "eval/mean_final_score":    result.mean_final_score,
                    "eval/mean_step_reward":    result.mean_step_reward,
                    "eval/mean_empathy":        result.mean_empathy,
                    "eval/mean_policy":         result.mean_policy,
                    "eval/mean_resolution":     result.mean_resolution,
                    "eval/mean_tone":           result.mean_tone,
                    "eval/mean_efficiency":     result.mean_efficiency,
                    "eval/mean_accuracy":       result.mean_accuracy,
                    "eval/invalid_rate":        result.invalid_rate,
                    **{f"eval/role_{k}": v for k, v in result.mean_role_rewards.items()},
                })

                # Curriculum advancement
                advanced = curriculum.report_eval(
                    result.mean_final_score, config.recovery_threshold
                )
                if advanced:
                    log_wandb(wb, grad_step, {"curriculum/stage": curriculum.current_stage()})

                # Recovery: halve LR if stuck
                if curriculum.should_recover(config.recovery_window):
                    old_lr = optimizer.param_groups[0]["lr"]
                    for pg in optimizer.param_groups:
                        pg["lr"] = pg["lr"] / 2
                    new_lr = optimizer.param_groups[0]["lr"]
                    curriculum.reset_low_score_counter()
                    print(f"[RECOVERY] Score below threshold for {config.recovery_window} "
                          f"steps. LR: {old_lr:.2e} → {new_lr:.2e}")
                print()

            # ── Checkpointing ─────────────────────────────────────────────────
            if grad_step % config.ckpt_interval == 0:
                save_checkpoint(model, tokenizer, grad_step, config)

    # ── Final checkpoint ──────────────────────────────────────────────────────
    final_path = Path(config.ckpt_dir) / "final"
    final_path.mkdir(parents=True, exist_ok=True)
    model.save_pretrained(str(final_path))
    tokenizer.save_pretrained(str(final_path))
    print(f"\n[DONE] Training complete. Final model saved to {final_path}")

    if wb:
        wb.finish()


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    args = parse_args()

    config = TrainConfig()
    if args.model:      config.model_name = args.model
    if args.total_steps: config.total_steps = args.total_steps
    if args.group_size:  config.group_size = args.group_size
    if args.lr:          config.learning_rate = args.lr
    if args.episodes:    config.episodes_per_step = args.episodes
    if args.no_wandb:    config.use_wandb = False
    if args.ckpt_dir:    config.ckpt_dir = args.ckpt_dir

    device = args.device

    if args.mode == "rollout_test":
        task = args.task or config.curriculum_stages[0]
        rollout_test(config, task, device)

    elif args.mode == "loss_test":
        loss_test(config, device)

    else:
        train(config, start_task=args.task, device=device)


if __name__ == "__main__":
    main()
