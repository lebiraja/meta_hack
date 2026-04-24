"""
train/evaluate.py — Run N evaluation episodes and return aggregate stats.

Uses the model greedily (temperature=0, do_sample=False) to get deterministic
scores that can be compared across checkpoints.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from train.config import TrainConfig
from train.env_client import EnvClient
from train.reward_aggregator import EpisodeRecord, aggregate_reward
from train.rollout_collector import run_one_episode


@dataclass
class EvalResult:
    mean_final_score: float = 0.0
    mean_step_reward: float = 0.0
    mean_empathy: float = 0.0
    mean_policy: float = 0.0
    mean_resolution: float = 0.0
    mean_tone: float = 0.0
    mean_efficiency: float = 0.0
    mean_accuracy: float = 0.0
    mean_role_rewards: Dict[str, float] = field(default_factory=dict)
    invalid_rate: float = 0.0
    n_episodes: int = 0
    # DB grounding metrics (non-zero only for multi_domain episodes)
    mean_db_query_match: float = 0.0       # query was relevant to the ticket
    mean_db_grounded_response: float = 0.0 # response cited verbatim DB data
    mean_db_hallucination: float = 0.0     # agent invented facts not in DB
    mean_db_wasted_query: float = 0.0      # query had no bearing on the ticket

    @property
    def mean(self) -> float:
        """Primary metric used for curriculum advancement."""
        return self.mean_final_score


def evaluate(
    model,
    tokenizer,
    env_client: EnvClient,
    task: str,
    config: TrainConfig,
    n_episodes: int = None,
    device: str = "cuda",
) -> EvalResult:
    """
    Run n_episodes evaluation episodes (greedy decoding) and return EvalResult.
    """
    n = n_episodes or config.eval_episodes

    # Use greedy decoding during eval
    eval_config = TrainConfig(**config.__dict__)
    eval_config.do_sample = False
    eval_config.temperature = 1.0   # ignored when do_sample=False
    eval_config.top_p = 1.0

    episodes: List[EpisodeRecord] = []
    for i in range(n):
        ep = run_one_episode(
            model, tokenizer, env_client, task, eval_config, device, verbose=False
        )
        episodes.append(ep)
        if (i + 1) % 10 == 0:
            print(f"  [EVAL] {i+1}/{n} episodes complete")

    # ── Aggregate ─────────────────────────────────────────────────────────────
    valid_eps = [ep for ep in episodes if not ep.invalid and ep.steps]
    invalid_eps = [ep for ep in episodes if ep.invalid]

    if not valid_eps:
        return EvalResult(invalid_rate=1.0, n_episodes=n)

    def mean_field(fn) -> float:
        vals = [fn(ep) for ep in valid_eps]
        return sum(vals) / len(vals)

    def last_step(ep: EpisodeRecord):
        return ep.steps[-1]

    mean_final = mean_field(lambda ep: last_step(ep).final_score or 0.0)
    mean_step  = mean_field(
        lambda ep: sum(s.reward_value for s in ep.steps) / max(1, len(ep.steps))
    )
    mean_emp   = mean_field(
        lambda ep: sum(s.empathy_score for s in ep.steps) / max(1, len(ep.steps))
    )
    mean_pol   = mean_field(
        lambda ep: sum(s.policy_adherence_score for s in ep.steps) / max(1, len(ep.steps))
    )
    mean_res   = mean_field(
        lambda ep: sum(s.resolution_score for s in ep.steps) / max(1, len(ep.steps))
    )
    mean_tone  = mean_field(
        lambda ep: sum(s.tone_score for s in ep.steps) / max(1, len(ep.steps))
    )
    mean_eff   = mean_field(
        lambda ep: last_step(ep).efficiency_score
    )
    mean_acc   = mean_field(
        lambda ep: last_step(ep).accuracy_score
    )

    # Per-role rewards (hierarchy tasks)
    role_keys: set = set()
    for ep in valid_eps:
        for s in ep.steps:
            role_keys.update(s.role_rewards.keys())

    mean_role: Dict[str, float] = {}
    for role in role_keys:
        vals = []
        for ep in valid_eps:
            for s in ep.steps:
                if role in s.role_rewards:
                    vals.append(s.role_rewards[role])
        mean_role[role] = sum(vals) / len(vals) if vals else 0.0

    # DB grounding metrics (non-zero only for multi_domain episodes)
    def _mean_db_signal(key: str) -> float:
        vals = [
            s.db_signals.get(key, 0.0)
            for ep in valid_eps
            for s in ep.steps
            if s.db_signals
        ]
        return sum(vals) / len(vals) if vals else 0.0

    return EvalResult(
        mean_final_score=mean_final,
        mean_step_reward=mean_step,
        mean_empathy=mean_emp,
        mean_policy=mean_pol,
        mean_resolution=mean_res,
        mean_tone=mean_tone,
        mean_efficiency=mean_eff,
        mean_accuracy=mean_acc,
        mean_role_rewards=mean_role,
        invalid_rate=len(invalid_eps) / n,
        n_episodes=n,
        mean_db_query_match=_mean_db_signal("query_match_bonus"),
        mean_db_grounded_response=_mean_db_signal("grounded_response_bonus"),
        mean_db_hallucination=_mean_db_signal("hallucination_penalty"),
        mean_db_wasted_query=_mean_db_signal("wasted_query_penalty"),
    )
