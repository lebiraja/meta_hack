"""
train/rollout_collector.py — Run full episodes using the local model and
collect (prompt, completion, log_probs, reward) trajectories.

Each call to run_one_episode():
1. Resets the environment
2. Loops: build prompt → model.generate → parse action → env.step
3. Returns an EpisodeRecord with all StepRecords
"""

from __future__ import annotations

from typing import List

from train.action_parser import get_fallback_action, parse_action
from train.config import TrainConfig
from train.env_client import EnvClient
from train.model_utils import model_generate
from train.prompt_builder import build_prompt_string
from train.reward_aggregator import EpisodeRecord, StepRecord

# Curriculum task → use hierarchical prompts?
_HIERARCHICAL_TASKS = {
    "hierarchy_easy", "hierarchy_medium", "hierarchy_hard",
    "curriculum_basic", "curriculum_supervisor",
    "curriculum_full_hierarchy", "curriculum_nightmare",
}


def run_one_episode(
    model,
    tokenizer,
    env_client: EnvClient,
    task: str,
    config: TrainConfig,
    device: str = "cuda",
    verbose: bool = False,
) -> EpisodeRecord:
    """
    Run a single full episode. Returns an EpisodeRecord.

    If the very first action is unparseable the episode is marked invalid
    and assigned config.invalid_penalty without wasting API quota.
    """
    hierarchical = task in _HIERARCHICAL_TASKS
    episode = EpisodeRecord(task=task)

    # ── Reset ──────────────────────────────────────────────────────────────────
    try:
        session_id, obs = env_client.reset(task)
    except Exception as e:
        episode.invalid = True
        episode.invalid_reason = f"reset failed: {e}"
        return episode

    done = False
    step_idx = 0

    while not done:
        active_role = obs.get("active_role", "support_agent")

        # ── Build prompt ───────────────────────────────────────────────────────
        prompt = build_prompt_string(obs, tokenizer, hierarchical=hierarchical)

        # ── Generate ───────────────────────────────────────────────────────────
        try:
            completion, log_probs = model_generate(
                model, tokenizer, prompt, config, device
            )
        except Exception as e:
            # GPU OOM or other generation error — use fallback
            completion = ""
            log_probs = None
            if verbose:
                print(f"  [WARN] Generation failed at step {step_idx}: {e}")

        # ── Parse action ───────────────────────────────────────────────────────
        action, parse_err = parse_action(completion, active_role)

        if action is None:
            if step_idx == 0:
                # First step invalid — mark whole episode invalid
                episode.invalid = True
                episode.invalid_reason = parse_err or "parse failed"
                # Add a dummy step so aggregate_reward sees episode.invalid=True
                return episode
            else:
                # Mid-episode parse error — use fallback and continue
                action = get_fallback_action(active_role)
                if verbose:
                    print(f"  [WARN] Parse error at step {step_idx}: {parse_err} → fallback")

        # ── Step environment ───────────────────────────────────────────────────
        try:
            result = env_client.step(session_id, action)
        except Exception as e:
            # Network or server error — end episode with partial rewards
            if verbose:
                print(f"  [WARN] step() failed at step {step_idx}: {e}")
            break

        done = result.done

        # ── Record ─────────────────────────────────────────────────────────────
        episode.steps.append(StepRecord(
            prompt=prompt,
            completion=completion,
            log_probs=log_probs,
            completion_len=len(tokenizer.encode(completion)) if completion else 1,
            reward_value=result.reward_value,
            done=done,
            final_score=result.final_score,
            empathy_score=result.empathy_score,
            policy_adherence_score=result.policy_adherence_score,
            resolution_score=result.resolution_score,
            tone_score=result.tone_score,
            efficiency_score=result.efficiency_score,
            accuracy_score=result.accuracy_score,
            role_rewards=result.role_rewards,
        ))

        obs = result.observation
        step_idx += 1

        if verbose:
            action_type = action.get("action_type", "?")
            print(
                f"  [STEP {step_idx:02d}] role={active_role} "
                f"action={action_type} "
                f"reward={result.reward_value:.3f} "
                f"done={done}"
            )

        # Safety: respect env's max_steps
        if step_idx >= obs.get("max_steps", 20) + 2:
            break

    return episode


def collect_group(
    model,
    tokenizer,
    env_client: EnvClient,
    task: str,
    config: TrainConfig,
    device: str = "cuda",
    verbose: bool = False,
) -> List[EpisodeRecord]:
    """
    Run config.group_size independent episodes for the same task.
    Returns a list of EpisodeRecords (one per rollout).
    """
    return [
        run_one_episode(model, tokenizer, env_client, task, config, device, verbose)
        for _ in range(config.group_size)
    ]
