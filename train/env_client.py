"""
train/env_client.py — HTTP client wrapping the /reset and /step environment API.

Returns typed dataclasses so the rest of the pipeline never touches raw dicts.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Dict, Optional

import httpx

from train.config import TrainConfig


@dataclass
class StepResult:
    """Parsed result of a single /step call."""
    reward_value: float
    done: bool
    observation: Dict[str, Any]
    final_score: Optional[float] = None       # only present when done=True
    reward_breakdown: Dict[str, Any] = field(default_factory=dict)
    role_rewards: Dict[str, float] = field(default_factory=dict)
    # Component scores for logging
    empathy_score: float = 0.0
    policy_adherence_score: float = 0.0
    resolution_score: float = 0.0
    tone_score: float = 0.0
    efficiency_score: float = 0.0
    accuracy_score: float = 0.0


class EnvClient:
    """Thin synchronous HTTP wrapper for the customer-support-env REST API."""

    def __init__(self, config: TrainConfig):
        self.base_url = config.env_url.rstrip("/")
        self.headers = {
            "X-API-Key": config.api_key,
            "Content-Type": "application/json",
        }
        self.timeout = config.env_timeout

    # ── reset ─────────────────────────────────────────────────────────────────

    def reset(self, task: str) -> tuple[str, Dict[str, Any]]:
        """
        Reset the environment for a given task.
        Returns (session_id, initial_observation_dict).
        """
        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(
                f"{self.base_url}/reset",
                params={"task": task},
                headers=self.headers,
            )
            r.raise_for_status()
            data = r.json()

        session_id = data["session_id"]
        obs = data["observation"]
        return session_id, obs

    # ── step ──────────────────────────────────────────────────────────────────

    def step(self, session_id: str, action: dict) -> StepResult:
        """
        Submit an action and return a StepResult.
        action must be a plain dict (not a Pydantic model).
        """
        with httpx.Client(timeout=self.timeout) as client:
            r = client.post(
                f"{self.base_url}/step",
                params={"session_id": session_id},
                content=json.dumps(action),
                headers=self.headers,
            )
            r.raise_for_status()
            data = r.json()

        reward = data.get("reward", {})
        return StepResult(
            reward_value=float(reward.get("value", 0.0)),
            done=bool(data.get("done", False)),
            observation=data.get("observation", {}),
            final_score=data.get("final_score"),
            reward_breakdown=reward.get("breakdown", {}),
            role_rewards=reward.get("role_rewards", {}),
            empathy_score=float(reward.get("empathy_score", 0.0)),
            policy_adherence_score=float(reward.get("policy_adherence_score", 0.0)),
            resolution_score=float(reward.get("resolution_score", 0.0)),
            tone_score=float(reward.get("tone_score", 0.0)),
            efficiency_score=float(reward.get("efficiency_score", 0.0)),
            accuracy_score=float(reward.get("accuracy_score", 0.0)),
        )
