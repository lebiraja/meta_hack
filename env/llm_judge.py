"""
LLMJudge — semantic reward evaluation using LLM-as-a-Judge.

Evaluates agent responses on dimensions that rule-based methods cannot:
empathy, policy adherence, resolution quality, supervisor oversight,
and manager decision quality. Uses strict rubrics to prevent gaming.

Each evaluation returns a float in [0.0, 1.0].
Falls back to rule-based heuristics if the LLM call fails.
"""

import os
import json
import logging
import re
import threading
from itertools import cycle
from typing import List, Optional, Dict, Any

from openai import OpenAI

from env.models import Message

logger = logging.getLogger(__name__)

def _load_api_keys() -> list[str]:
    """Collect all NVIDIA_API_KEY_N env vars (N=1..10) that are non-empty."""
    keys = []
    for i in range(1, 11):
        k = os.getenv(f"NVIDIA_API_KEY_{i}", "").strip()
        if k:
            keys.append(k)
    return keys

# ── Rubric Prompts ────────────────────────────────────────────────────────────

RUBRIC_EMPATHY = """You are an expert evaluator grading a customer support agent's EMPATHY.

Score the agent's message on a scale of 0.0 to 1.0:

1.0 — EXCELLENT: Agent acknowledges the specific issue, validates the customer's feelings, uses warm language, shows genuine understanding of the impact on the customer.
0.7 — GOOD: Agent is polite and acknowledges the issue but doesn't deeply empathize or validate emotions.
0.5 — NEUTRAL: Agent is professional but cold/robotic. No emotional acknowledgment.
0.3 — POOR: Agent is dismissive, uses canned responses, or ignores the customer's emotional state.
0.0 — TERRIBLE: Agent is rude, hostile, uses all-caps aggressively, or mocks the customer.

RED FLAGS (automatically score 0.2 or below):
- Generic phrases without addressing the specific issue (e.g., "I understand your concern" without specifics)
- Keyword stuffing (repeating empathy words like "understand understand sorry sorry")
- Contradicting empathy with dismissive actions

TICKET CONTEXT: {ticket_context}
CONVERSATION HISTORY:
{conversation}

AGENT'S MESSAGE TO EVALUATE:
{message}

Output ONLY a JSON object: {{"score": <float>, "reason": "<brief explanation>"}}"""

RUBRIC_POLICY = """You are an expert evaluator grading a customer support agent's POLICY ADHERENCE.

ACTIVE POLICY:
{policy}

TICKET DETAILS:
- Category: {category}
- Priority: {priority}
- Expected Resolution: {expected_resolution}

AGENT'S ACTION: {action_type}
AGENT'S MESSAGE: {message}

Score on 0.0 to 1.0:
1.0 — Fully compliant: follows every aspect of the active policy.
0.7 — Mostly compliant: minor deviations that don't harm the customer.
0.5 — Partially compliant: noticeable policy gaps but not harmful.
0.3 — Non-compliant: clear policy violation (e.g., promising refund when portal is down).
0.0 — Severely non-compliant: dangerous action violating policy (e.g., sharing PII, escalating when frozen).

Output ONLY a JSON object: {{"score": <float>, "reason": "<brief explanation>"}}"""

RUBRIC_RESOLUTION = """You are an expert evaluator grading the RESOLUTION QUALITY of a support interaction.

TICKET: {subject}
CATEGORY: {category}
EXPECTED RESOLUTION: {expected_resolution}
REQUIRED INFO: {required_info}

FULL CONVERSATION:
{conversation}

Score on 0.0 to 1.0:
1.0 — Perfect: Issue fully resolved, all required info gathered, customer confirmed satisfaction.
0.7 — Good: Issue addressed with appropriate resolution, most info gathered.
0.5 — Partial: Attempted resolution but missing key steps or info.
0.3 — Poor: Closed without resolving, or resolved wrong issue.
0.0 — Failed: No resolution attempted, or actively made the situation worse.

RED FLAGS:
- Claiming resolution without actually doing anything specific
- Keyword stuffing resolution language without substance
- Closing ticket with unresolved issues still pending

Output ONLY a JSON object: {{"score": <float>, "reason": "<brief explanation>"}}"""

RUBRIC_SUPERVISOR = """You are evaluating a SUPERVISOR's review of a support agent's action.

THE SUPPORT AGENT'S ACTION:
Type: {l1_action_type}
Message: {l1_message}

THE SUPERVISOR'S DECISION: {supervisor_decision}
SUPERVISOR'S FEEDBACK: {supervisor_feedback}

TICKET CONTEXT:
- Subject: {subject}
- Priority: {priority}
- Category: {category}

ACTIVE POLICY: {policy}

Score the supervisor's review quality on 0.0 to 1.0:
1.0 — Excellent oversight: Correct decision (approve good actions, reject bad ones), actionable feedback.
0.7 — Good: Right decision but feedback could be more specific.
0.5 — Acceptable: Decision is debatable but not harmful.
0.3 — Poor: Wrong decision (approved a bad action or rejected a good one).
0.0 — Terrible: Rubber-stamped without review, or gave contradictory feedback.

Output ONLY a JSON object: {{"score": <float>, "reason": "<brief explanation>"}}"""

RUBRIC_MANAGER = """You are evaluating a MANAGER's decision on an escalated support case.

ESCALATION CONTEXT:
- Why it was escalated: {escalation_reason}
- Ticket Subject: {subject}
- Priority: {priority}
- Category: {category}

MANAGER'S DECISION: {manager_decision}
MANAGER'S MESSAGE: {manager_message}

CONVERSATION HISTORY:
{conversation}

Score on 0.0 to 1.0:
1.0 — Excellent: Decisive, appropriate response that resolves the escalation correctly.
0.7 — Good: Reasonable decision that addresses the core issue.
0.5 — Acceptable: Decision is okay but could be better.
0.3 — Poor: Decision doesn't address the escalation well, or is unnecessarily heavy-handed.
0.0 — Failed: Wrong decision, or punted the issue back without adding value.

Output ONLY a JSON object: {{"score": <float>, "reason": "<brief explanation>"}}"""


class LLMJudge:
    """LLM-as-Judge for semantic reward evaluation with round-robin key load balancing."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
    ) -> None:
        # JUDGE_BASE_URL overrides API_BASE_URL — use it to point at serve_judge.py locally
        self._base_url = base_url or os.getenv(
            "JUDGE_BASE_URL",
            os.getenv("API_BASE_URL", "https://integrate.api.nvidia.com/v1"),
        )
        self._model = model or os.getenv(
            "JUDGE_MODEL",
            os.getenv("MODEL_NAME", "nvidia/nemotron-super-49b-v1"),
        )

        # Local judge shortcut: single client, no API key rotation needed
        _local_url = os.getenv("JUDGE_BASE_URL", "")
        if _local_url and ("localhost" in _local_url or "127.0.0.1" in _local_url):
            api_key = os.getenv("JUDGE_API_KEY", "local")
            self._clients = []
            try:
                self._clients = [OpenAI(api_key=api_key, base_url=self._base_url)]
            except Exception as e:
                logger.warning(f"Failed to create local judge client: {e}")
            self._lock = threading.Lock()
            self._key_cycle = cycle(range(len(self._clients))) if self._clients else cycle([])
            self._current_idx = 0
            logger.info(f"LLMJudge → local server {self._base_url} model={self._model}")
            return

        # Build one OpenAI client per API key for true round-robin load balancing
        keys = _load_api_keys()
        self._clients: list[OpenAI] = []
        for key in keys:
            try:
                self._clients.append(OpenAI(api_key=key, base_url=self._base_url))
            except Exception as e:
                logger.warning(f"Failed to create LLM client for key ...{key[-6:]}: {e}")

        if not self._clients:
            logger.warning(
                "LLMJudge: no NVIDIA_API_KEY_N vars found — all semantic scores default to 0.5. "
                "Set NVIDIA_API_KEY_1 through NVIDIA_API_KEY_6 to enable the judge."
            )

        # Thread-safe round-robin cursor
        self._lock = threading.Lock()
        self._key_cycle = cycle(range(len(self._clients))) if self._clients else cycle([])
        self._current_idx = 0

        logger.info(f"LLMJudge initialized with {len(self._clients)} API keys, model={self._model}")

    def _next_client(self) -> Optional[OpenAI]:
        if not self._clients:
            return None
        with self._lock:
            idx = next(self._key_cycle)
            self._current_idx = idx
        return self._clients[idx]

    def _call_judge(self, prompt: str) -> float:
        """Call the LLM judge, retrying the next key on failure."""
        if not self._clients:
            return 0.5  # neutral fallback — no keys configured

        num_keys = len(self._clients)
        for attempt in range(num_keys):
            client = self._next_client()
            if client is None:
                return 0.5
            try:
                completion = client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": "You are a precise evaluation judge. Output ONLY valid JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    temperature=0.1,
                    max_tokens=150,
                    top_p=0.9,
                )
                raw = completion.choices[0].message.content or ""
                raw = raw.strip()
                # Extract JSON from response (handle markdown fences)
                if "```" in raw:
                    raw = re.sub(r"```json?\s*", "", raw)
                    raw = raw.replace("```", "").strip()
                result = json.loads(raw)
                score = float(result.get("score", 0.5))
                return max(0.0, min(1.0, score))
            except Exception as e:
                logger.warning(f"LLM Judge call failed (attempt {attempt+1}/{num_keys}): {e}")
                # Try next key on next iteration
        return 0.3  # below-neutral fallback — all keys failed

    @staticmethod
    def _format_history(history: List[Message], max_messages: int = 10) -> str:
        """Format conversation history for judge prompts."""
        recent = history[-max_messages:]
        return "\n".join(
            f"{m.role.upper()}: {m.content}" for m in recent
        )

    def evaluate_empathy(
        self,
        message: str,
        history: List[Message],
        ticket: dict,
    ) -> float:
        """Evaluate the empathy quality of an agent's message."""
        # Anti-gaming: check for keyword stuffing first
        stuffing_score = self._check_keyword_stuffing(message)
        if stuffing_score is not None:
            return stuffing_score

        prompt = RUBRIC_EMPATHY.format(
            ticket_context=f"{ticket.get('subject', '')} ({ticket.get('category', '')})",
            conversation=self._format_history(history),
            message=message,
        )
        return self._call_judge(prompt)

    def evaluate_policy_adherence(
        self,
        action_type: str,
        message: str,
        ticket: dict,
        policy: str,
    ) -> float:
        """Evaluate whether the agent's action follows the active policy."""
        prompt = RUBRIC_POLICY.format(
            policy=policy,
            category=ticket.get("category", ""),
            priority=ticket.get("priority", ""),
            expected_resolution=ticket.get("expected_resolution_type", ""),
            action_type=action_type,
            message=message,
        )
        return self._call_judge(prompt)

    def evaluate_resolution(
        self,
        history: List[Message],
        ticket: dict,
    ) -> float:
        """Evaluate the overall resolution quality of the conversation."""
        prompt = RUBRIC_RESOLUTION.format(
            subject=ticket.get("subject", ""),
            category=ticket.get("category", ""),
            expected_resolution=ticket.get("expected_resolution_type", ""),
            required_info=", ".join(ticket.get("required_info_before_close", [])),
            conversation=self._format_history(history, max_messages=20),
        )
        return self._call_judge(prompt)

    def evaluate_supervisor_oversight(
        self,
        l1_action_type: str,
        l1_message: str,
        supervisor_decision: str,
        supervisor_feedback: str,
        ticket: dict,
        policy: str,
    ) -> float:
        """Evaluate the quality of a supervisor's review decision."""
        prompt = RUBRIC_SUPERVISOR.format(
            l1_action_type=l1_action_type,
            l1_message=l1_message,
            supervisor_decision=supervisor_decision,
            supervisor_feedback=supervisor_feedback or "No feedback provided.",
            subject=ticket.get("subject", ""),
            priority=ticket.get("priority", ""),
            category=ticket.get("category", ""),
            policy=policy,
        )
        return self._call_judge(prompt)

    def evaluate_manager_decision(
        self,
        manager_decision: str,
        manager_message: str,
        escalation_reason: str,
        history: List[Message],
        ticket: dict,
    ) -> float:
        """Evaluate the quality of a manager's decision."""
        prompt = RUBRIC_MANAGER.format(
            escalation_reason=escalation_reason or "Not specified",
            subject=ticket.get("subject", ""),
            priority=ticket.get("priority", ""),
            category=ticket.get("category", ""),
            manager_decision=manager_decision,
            manager_message=manager_message,
            conversation=self._format_history(history),
        )
        return self._call_judge(prompt)

    @staticmethod
    def _check_keyword_stuffing(message: str) -> Optional[float]:
        """
        Detect keyword stuffing. Returns a low score if detected, None if clean.
        Anti-gaming measure: high density of resolution/empathy keywords
        without substantive content is penalized.
        """
        if not message or len(message) < 10:
            return 0.1

        words = message.lower().split()
        if len(words) < 3:
            return None

        empathy_keywords = {
            "understand", "sorry", "apologize", "appreciate", "empathy",
            "empathize", "sympathize", "care", "concern",
        }
        resolution_keywords = {
            "refund", "resolved", "fixed", "processed", "credit",
            "reimburse", "restore", "reset", "update",
        }
        all_keywords = empathy_keywords | resolution_keywords

        keyword_count = sum(1 for w in words if w in all_keywords)
        density = keyword_count / len(words)

        # If 20%+ of words are reward keywords, it's stuffing
        if density >= 0.20 and len(words) > 5:
            logger.info(f"Keyword stuffing detected: density={density:.2f}")
            return 0.15  # Heavy penalty
        return None


# ── Singleton ─────────────────────────────────────────────────────────────────

_judge_instance: Optional[LLMJudge] = None


def get_llm_judge() -> LLMJudge:
    """Get or create the singleton LLM judge (load-balanced across all configured keys)."""
    global _judge_instance
    if _judge_instance is None:
        _judge_instance = LLMJudge()
    return _judge_instance
