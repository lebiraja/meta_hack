"""
train/rollout_collector.py — Run full episodes using the local model and
collect (prompt, completion, log_probs, reward) trajectories.

Each call to run_one_episode():
1. Resets the environment
2. Loops: build prompt → model.generate → parse action → env.step
3. Returns an EpisodeRecord with all StepRecords
"""

from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Optional

from train.action_parser import get_fallback_action, parse_action
from train.config import TrainConfig
from train.env_client import EnvClient
from train.model_utils import model_generate
from train.prompt_builder import build_prompt_string
from train.reward_aggregator import EpisodeRecord, StepRecord

# Generation is not thread-safe — one thread at a time through the GPU
_generate_lock = threading.Lock()

# Tasks that use HierarchicalCustomerSupportEnv → need role-specific prompts
_HIERARCHICAL_TASKS = {
    "hierarchy_easy", "hierarchy_medium", "hierarchy_hard",
    "curriculum_basic", "curriculum_supervisor",
    "curriculum_full_hierarchy", "curriculum_nightmare",
    "multi_domain",
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

        # ── Generate (serialized through GPU lock) ─────────────────────────────
        prompt_ids = None
        completion_ids = None
        try:
            with _generate_lock:
                completion, prompt_ids, completion_ids, log_probs = model_generate(
                    model, tokenizer, prompt, config, device
                )
        except Exception as e:
            completion = ""
            log_probs = None
            print(f"  [ERROR] Generation failed ep={task} step={step_idx} role={active_role}: {type(e).__name__}: {e}")

        # ── Parse action ───────────────────────────────────────────────────────
        _is_fallback = False
        action, parse_err = parse_action(completion, active_role)

        if action is None:
            if step_idx == 0:
                episode.invalid = True
                episode.invalid_reason = parse_err or "parse failed"
                print(f"  [INVALID] task={task} step=0 reason='{parse_err}' output={completion[:80]!r}")
                return episode
            else:
                action = get_fallback_action(active_role)
                print(f"  [FALLBACK] task={task} step={step_idx} role={active_role} reason='{parse_err}'")
                _is_fallback = True

        # ── Step environment ───────────────────────────────────────────────────
        try:
            result = env_client.step(session_id, action)
        except Exception as e:
            print(f"  [ERROR] env step() failed ep={task} step={step_idx}: {type(e).__name__}: {e}")
            break

        done = result.done

        # ── Record ─────────────────────────────────────────────────────────────
        db_signals = result.reward_breakdown.get("db_signals", {}) if result.reward_breakdown else {}
        episode.steps.append(StepRecord(
            prompt=prompt,
            completion=completion,
            log_probs=log_probs,
            completion_len=int(completion_ids.shape[0]) if completion_ids is not None else 1,
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
            db_signals=db_signals,
            prompt_ids=prompt_ids,
            completion_ids=completion_ids,
        ))

        # Penalize FALLBACK steps so the model isn't rewarded for garbled output
        if _is_fallback:
            episode.steps[-1].reward_value = config.invalid_penalty
            print(f"  [FALLBACK-PENALIZED] reward overridden to {config.invalid_penalty}")

        obs = result.observation
        step_idx += 1

        action_type = action.get("action_type", "?")
        if verbose:
            print(
                f"  [STEP {step_idx:02d}] role={active_role} "
                f"action={action_type} "
                f"reward={result.reward_value:.3f} "
                f"done={done}"
            )

        # Safety: respect env's max_steps
        if step_idx >= obs.get("max_steps", 20) + 2:
            break

    if episode.steps:
        final_score = episode.steps[-1].final_score
        final_str = f"{final_score:.3f}" if final_score is not None else "N/A"
        step_rewards = [s.reward_value for s in episode.steps]
        rewards_str = ", ".join(f"{r:.2f}" for r in step_rewards)
        print(f"  [EP] task={task} steps={step_idx} final={final_str} step_rewards=[{rewards_str}]")
    return episode


def collect_group(
    model,
    tokenizer,
    env_client: EnvClient,
    task: str,
    config: TrainConfig,
    device: str = "cuda",
    verbose: bool = False,
    local_judge=None,
) -> List[EpisodeRecord]:
    """
    Run config.group_size independent episodes in parallel using ThreadPoolExecutor.

    GPU generation is serialized via _generate_lock; env I/O and local judge
    calls run concurrently across threads, giving ~rollout_workers× speedup
    over sequential collection.
    """
    workers = getattr(config, "rollout_workers", 1)

    def _run(_):
        ep = run_one_episode(model, tokenizer, env_client, task, config, device, verbose)
        if local_judge is not None and not ep.invalid:
            _apply_local_judge(ep, local_judge)
        return ep

    if workers <= 1 or config.group_size <= 1:
        return [_run(None) for _ in range(config.group_size)]

    results: List[EpisodeRecord] = [None] * config.group_size  # type: ignore
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(_run, i): i for i in range(config.group_size)}
        for fut in as_completed(futures):
            idx = futures[fut]
            try:
                results[idx] = fut.result()
            except Exception as e:
                ep = EpisodeRecord(task=task)
                ep.invalid = True
                ep.invalid_reason = f"thread error: {e}"
                results[idx] = ep
    return results


def _apply_local_judge(episode: EpisodeRecord, local_judge) -> None:
    """
    Post-hoc: replace non-terminal empathy scores with local judge scores.
    Terminal step scores come from the API judge (higher quality).
    """
    for i, step in enumerate(episode.steps):
        if step.done:
            continue  # terminal already has API-judged scores
        try:
            # Local judge only scores empathy for non-terminal steps
            new_empathy = local_judge.score_empathy_fast(step.prompt, step.completion)
            if new_empathy is not None:
                step.empathy_score = new_empathy
        except Exception:
            pass  # keep original score on any error
