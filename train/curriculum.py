"""
train/curriculum.py — Curriculum scheduler.

Tracks evaluation scores and advances through training stages when
performance crosses the configured threshold.

Stages (in order):
  1. curriculum_basic          → L1 only, no drift
  2. curriculum_supervisor     → L1+L2, 20% drift
  3. curriculum_full_hierarchy → L1+L2+L3, 80% drift
  4. curriculum_nightmare      → all levels, 100% drift, Hinglish
"""

from __future__ import annotations

from typing import List, Optional


class CurriculumScheduler:
    def __init__(self, stages: List[str], thresholds: List[float]):
        """
        stages:     ordered list of task names
        thresholds: score thresholds for advancing from each stage
                    (length = len(stages) - 1, last stage has no threshold)
        """
        assert len(stages) >= 1
        assert len(thresholds) == len(stages) - 1, (
            f"Need {len(stages)-1} thresholds for {len(stages)} stages"
        )
        self.stages = stages
        self.thresholds = thresholds
        self._stage_idx = 0

        # Per-stage eval history
        self._eval_scores: List[float] = []
        # Steps since last eval where score was above recovery threshold
        self._low_score_steps: int = 0

    # ── Current state ─────────────────────────────────────────────────────────

    def current_task(self) -> str:
        return self.stages[self._stage_idx]

    def current_stage(self) -> int:
        return self._stage_idx

    def is_final_stage(self) -> bool:
        return self._stage_idx >= len(self.stages) - 1

    # ── Score reporting ───────────────────────────────────────────────────────

    def report_eval(self, mean_score: float, recovery_threshold: float = 0.30) -> bool:
        """
        Record an eval result. Returns True if curriculum advanced.

        mean_score: mean final_score over eval_episodes
        """
        self._eval_scores.append(mean_score)

        if mean_score < recovery_threshold:
            self._low_score_steps += 1
        else:
            self._low_score_steps = 0

        if self.is_final_stage():
            return False

        threshold = self.thresholds[self._stage_idx]
        if mean_score >= threshold:
            self._stage_idx += 1
            self._eval_scores = []   # reset history for new stage
            print(
                f"[CURRICULUM] Advanced to stage {self._stage_idx}: "
                f"{self.current_task()} (score={mean_score:.3f} >= {threshold})"
            )
            return True

        return False

    def should_recover(self, recovery_window: int = 200) -> bool:
        """True if performance has been below recovery_threshold for too long."""
        return self._low_score_steps >= recovery_window

    def reset_low_score_counter(self):
        self._low_score_steps = 0

    # ── Status ────────────────────────────────────────────────────────────────

    def status(self) -> dict:
        last = self._eval_scores[-1] if self._eval_scores else None
        threshold = (
            self.thresholds[self._stage_idx]
            if not self.is_final_stage() else None
        )
        return {
            "stage": self._stage_idx,
            "task": self.current_task(),
            "last_score": last,
            "advance_threshold": threshold,
            "low_score_steps": self._low_score_steps,
        }
