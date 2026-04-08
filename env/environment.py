"""
CustomerSupportEnv — core RL environment.

Each instance is bound to one episode (one ticket, one session).
Session isolation is enforced at the server layer (server/app.py).
"""

import random
import re
import uuid
from typing import Optional

from env.models import Action, ActionType, Message, Observation, Reward
from env.reward_engine import compute_step_reward, _INFO_PATTERNS
from env.ticket_store import ticket_store

# ── Task config ────────────────────────────────────────────────────────────────
TASK_CONFIG = {
    "easy":   {"max_steps": 5},
    "medium": {"max_steps": 8},
    "hard":   {"max_steps": 10},
}

# ── Simulated customer follow-up responses by persona ──────────────────────────
_FOLLOW_UPS: dict[str, dict[str, list[str]]] = {
    "impatient": {
        "respond": [
            "That doesn't solve my problem. I need this fixed NOW.",
            "Still not helpful. What are you actually going to DO about it?",
            "I've been waiting too long. This is terrible service.",
            "Fine. But I expect this resolved within the hour.",
        ],
        "request_info": [
            "Why do you need that? Just look at my account!",
            "I already gave you that information. Can't you just fix it?",
            "Ugh. Fine. {follow_up_info}",
            "{follow_up_info} — now please hurry.",
        ],
    },
    "polite": {
        "respond": [
            "Thank you for looking into this. I appreciate your help.",
            "I understand, please take your time. I just want this resolved.",
            "That makes sense. What would you suggest as the next step?",
            "OK, I see. Let me know if you need anything else from me.",
        ],
        "request_info": [
            "Of course! {follow_up_info}",
            "Sure, happy to help. {follow_up_info}",
            "No problem. {follow_up_info}",
            "Here you go: {follow_up_info}",
        ],
    },
    "confused": {
        "respond": [
            "I'm not sure I understand. Can you explain that more simply?",
            "Wait, so what does that mean for me exactly?",
            "I'm confused. I thought this would be straightforward to fix.",
            "OK... but I'm still not sure what I'm supposed to do.",
        ],
        "request_info": [
            "Oh, ok. Is this the right thing? {follow_up_info}",
            "I think this is what you mean: {follow_up_info}",
            "Here's what I have: {follow_up_info} — is that what you need?",
            "Not sure if this helps but: {follow_up_info}",
        ],
    },
}

# ── Sentiment delta per action type ────────────────────────────────────────────
_SENTIMENT_DELTA: dict[ActionType, float] = {
    ActionType.RESPOND:       0.0,   # adjusted by tone score in update
    ActionType.REQUEST_INFO:  0.05,
    ActionType.ESCALATE:      0.0,   # adjusted by priority in update
    ActionType.CLOSE:         0.1,
}


class CustomerSupportEnv:
    def __init__(self, task: str = "easy") -> None:
        if task not in TASK_CONFIG:
            raise ValueError(f"Unknown task '{task}'. Choose from: {list(TASK_CONFIG)}")
        self.task = task
        self.session_id: str = str(uuid.uuid4())
        self._ticket: Optional[dict] = None
        self._history: list[Message] = []
        self._step: int = 0
        self._max_steps: int = TASK_CONFIG[task]["max_steps"]
        self._sentiment: float = 0.0
        self._done: bool = False
        self._action_log: list[dict] = []

    # ── Public API ─────────────────────────────────────────────────────────────

    def reset(self) -> Observation:
        """Pick a fresh ticket and return initial observation."""
        self._ticket = ticket_store.get_random_by_task(self.task)
        self._history = [
            Message(role="customer", content=self._ticket["opening_message"])
        ]
        self._step = 0
        self._sentiment = 0.0
        self._done = False
        self._action_log = []
        return self._build_observation()

    def step(self, action: Action) -> tuple[Observation, Reward, bool, dict]:
        """Apply action, compute reward, update state, return (obs, reward, done, info)."""
        if self._done:
            raise RuntimeError("Episode is done. Call reset() to start a new episode.")
        if self._ticket is None:
            raise RuntimeError("Environment not initialized. Call reset() first.")

        self._step += 1
        is_terminal = self._is_terminal_action(action)

        # Add agent message to history
        agent_content = action.message or action.reason or f"[{action.action_type}]"
        self._history.append(Message(role="agent", content=agent_content))

        # Compute reward before customer follow-up (history = up to agent msg)
        reward = compute_step_reward(
            action=action,
            ticket=self._ticket,
            history=self._history,
            steps_used=self._step,
            max_steps=self._max_steps,
            is_terminal=is_terminal or self._step >= self._max_steps,
        )

        # Update sentiment based on tone and action type
        self._update_sentiment(action, reward.tone_score)

        # Log action
        self._action_log.append({
            "step": self._step,
            "action_type": action.action_type,
            "message": action.message,
            "reason": action.reason,
            "reward": reward.value,
        })

        # Simulate customer reply if not terminal
        done = is_terminal or self._step >= self._max_steps
        if not done:
            customer_reply = self._simulate_customer_reply(action)
            self._history.append(Message(role="customer", content=customer_reply))

        self._done = done
        obs = self._build_observation()
        info = {
            "ticket_id": self._ticket["id"],
            "action_log": self._action_log,
            "error": None,
        }
        return obs, reward, done, info

    def state(self) -> dict:
        """Return full internal state (for /state endpoint and graders)."""
        return {
            "session_id": self.session_id,
            "task": self.task,
            "ticket": self._ticket,
            "history": [m.model_dump() for m in self._history],
            "step": self._step,
            "max_steps": self._max_steps,
            "sentiment": self._sentiment,
            "done": self._done,
            "action_log": self._action_log,
        }

    # ── Internal helpers ───────────────────────────────────────────────────────

    def _build_observation(self) -> Observation:
        assert self._ticket is not None
        unresolved = self._compute_unresolved_issues()
        # Return only the last 20 messages in the observation payload to cap
        # response size. Full history is kept internally for grading accuracy.
        history_window = self._history[-20:]
        return Observation(
            session_id=self.session_id,
            ticket_id=self._ticket["id"],
            category=self._ticket["category"],
            priority=self._ticket["priority"],
            subject=self._ticket["subject"],
            conversation_history=history_window,
            step=self._step,
            max_steps=self._max_steps,
            customer_sentiment=round(self._sentiment, 3),
            unresolved_issues=unresolved,
            is_done=self._done,
            task=self.task,
        )

    def _is_terminal_action(self, action: Action) -> bool:
        return action.action_type in (ActionType.CLOSE, ActionType.ESCALATE)

    def _update_sentiment(self, action: Action, tone_score: float) -> None:
        """
        Adjust customer sentiment based on action type and tone quality.
        tone_score is in [0, 1]; 0.5 is neutral.
        """
        if action.action_type == ActionType.RESPOND:
            delta = (tone_score - 0.5) * 0.4
        elif action.action_type == ActionType.REQUEST_INFO:
            delta = 0.05
        elif action.action_type == ActionType.ESCALATE:
            priority = self._ticket.get("priority", "medium") if self._ticket else "medium"
            delta = 0.3 if priority == "critical" else -0.2
        elif action.action_type == ActionType.CLOSE:
            delta = 0.1
        else:
            delta = 0.0

        self._sentiment = max(-1.0, min(1.0, self._sentiment + delta))

    def _simulate_customer_reply(self, action: Action) -> str:
        """Generate a contextually appropriate customer reply based on persona."""
        assert self._ticket is not None
        persona = self._ticket.get("customer_persona", "polite")
        persona_replies = _FOLLOW_UPS.get(persona, _FOLLOW_UPS["polite"])

        action_key = "respond"
        if action.action_type == ActionType.REQUEST_INFO:
            action_key = "request_info"

        replies = persona_replies.get(action_key, persona_replies["respond"])
        template = random.choice(replies)

        follow_up = self._ticket.get("follow_up_info", "")
        return template.format(follow_up_info=follow_up)

    def _compute_unresolved_issues(self) -> list[str]:
        """
        Returns list of required info items not yet gathered from the conversation.
        Uses top-level `re` and `_INFO_PATTERNS` imports (not inline).
        """
        if not self._ticket:
            return []
        required = self._ticket.get("required_info_before_close", [])
        all_text = " ".join(m.content for m in self._history)

        unresolved = []
        for info_type in required:
            pattern = _INFO_PATTERNS.get(info_type)
            if pattern:
                if not pattern.search(all_text):
                    unresolved.append(info_type)
            elif sum(1 for m in self._history if m.role == "customer") < 2:
                unresolved.append(info_type)

        return unresolved
