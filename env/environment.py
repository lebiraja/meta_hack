"""
CustomerSupportEnv — core RL environment.
Supports both single-agent (Round 1) and hierarchical multi-agent (Round 2).
"""

import random
import re
import uuid
from typing import Optional, Dict, Any, List

from env.models import (
    Action, ActionType, AgentRole, Message, Observation, Reward,
    HierarchyState, L1_ACTION_TYPES, L2_ACTION_TYPES, L3_ACTION_TYPES,
)
from env.reward_engine import compute_step_reward, compute_hierarchy_reward, _INFO_PATTERNS
from env.ticket_store import ticket_store
from env.customer_simulator import get_customer_simulator
from env.policy_engine import PolicyEngine

# ── Task config ────────────────────────────────────────────────────────────────
# Each task specifies:
#   max_steps         — episode length
#   hierarchical      — whether HierarchicalCustomerSupportEnv is used
#   active_levels     — which agent levels are active (1=L1, 2=L2, 3=L3)
#   drift_probability — chance of mid-episode policy drift
#   initial_frustration — starting customer frustration (0.0 = calm, 1.0 = furious)
#   hinglish_enabled  — whether Hinglish degradation can trigger
#   multi_drift       — allow >1 drift events in a single episode
#   ticket_pool       — which ticket pool to draw from in ticket_store

TASK_CONFIG = {
    # ── Round 1: Single-agent (backward compat) ───────────────────────────────
    "easy":      {"max_steps": 5,  "hierarchical": False, "active_levels": [1],
                  "drift_probability": 0.0, "initial_frustration": 0.0,
                  "hinglish_enabled": False, "multi_drift": False, "ticket_pool": "easy"},
    "medium":    {"max_steps": 8,  "hierarchical": False, "active_levels": [1],
                  "drift_probability": 0.0, "initial_frustration": 0.1,
                  "hinglish_enabled": False, "multi_drift": False, "ticket_pool": "medium"},
    "hard":      {"max_steps": 10, "hierarchical": False, "active_levels": [1],
                  "drift_probability": 0.0, "initial_frustration": 0.2,
                  "hinglish_enabled": False, "multi_drift": False, "ticket_pool": "hard"},
    "nightmare": {"max_steps": 12, "hierarchical": False, "active_levels": [1],
                  "drift_probability": 0.0, "initial_frustration": 0.3,
                  "hinglish_enabled": False, "multi_drift": False, "ticket_pool": "nightmare"},
    # ── Round 2: Hierarchical tasks ───────────────────────────────────────────
    "hierarchy_easy":   {"max_steps": 8,  "hierarchical": True, "active_levels": [1, 2],
                         "drift_probability": 0.3, "initial_frustration": 0.1,
                         "hinglish_enabled": False, "multi_drift": False, "ticket_pool": "easy"},
    "hierarchy_medium": {"max_steps": 12, "hierarchical": True, "active_levels": [1, 2],
                         "drift_probability": 0.5, "initial_frustration": 0.2,
                         "hinglish_enabled": False, "multi_drift": False, "ticket_pool": "medium"},
    "hierarchy_hard":   {"max_steps": 15, "hierarchical": True, "active_levels": [1, 2, 3],
                         "drift_probability": 0.8, "initial_frustration": 0.3,
                         "hinglish_enabled": False, "multi_drift": False, "ticket_pool": "hard"},
    # ── Round 2: Progressive Curriculum ───────────────────────────────────────
    "curriculum_basic":          {"max_steps": 6,  "hierarchical": True, "active_levels": [1],
                                  "drift_probability": 0.0, "initial_frustration": 0.0,
                                  "hinglish_enabled": False, "multi_drift": False, "ticket_pool": "easy"},
    "curriculum_supervisor":     {"max_steps": 10, "hierarchical": True, "active_levels": [1, 2],
                                  "drift_probability": 0.2, "initial_frustration": 0.2,
                                  "hinglish_enabled": False, "multi_drift": False, "ticket_pool": "medium"},
    "curriculum_full_hierarchy": {"max_steps": 14, "hierarchical": True, "active_levels": [1, 2, 3],
                                  "drift_probability": 0.8, "initial_frustration": 0.4,
                                  "hinglish_enabled": False, "multi_drift": False, "ticket_pool": "hard"},
    "curriculum_nightmare":      {"max_steps": 18, "hierarchical": True, "active_levels": [1, 2, 3],
                                  "drift_probability": 1.0, "initial_frustration": 0.7,
                                  "hinglish_enabled": True, "multi_drift": True, "ticket_pool": "nightmare"},
}

# ── Legacy follow-ups (fallback for single-agent mode) ─────────────────────────
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

_SENTIMENT_DELTA: dict[ActionType, float] = {
    ActionType.RESPOND:       0.0,
    ActionType.REQUEST_INFO:  0.05,
    ActionType.ESCALATE:      0.0,
    ActionType.CLOSE:         0.1,
}


class CustomerSupportEnv:
    """Single-agent environment (Round 1 backward compat)."""

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
        self._sentiment_history: list[float] = []
        self._done: bool = False
        self._action_log: list[dict] = []
        self._is_hierarchical = TASK_CONFIG[task].get("hierarchical", False)

    def reset(self) -> Observation:
        cfg = TASK_CONFIG[self.task]
        ticket_pool = cfg.get("ticket_pool", self.task)
        self._ticket = ticket_store.get_random_by_task(ticket_pool)
        self._history = [Message(role="customer", content=self._ticket["opening_message"])]
        self._step = 0
        self._sentiment = -cfg.get("initial_frustration", 0.0)  # negative = customer unhappy
        self._sentiment_history = []
        self._done = False
        self._action_log = []
        return self._build_observation()

    def step(self, action: Action) -> tuple[Observation, Reward, bool, dict]:
        if self._done:
            raise RuntimeError("Episode is done. Call reset() to start a new episode.")
        if self._ticket is None:
            raise RuntimeError("Environment not initialized. Call reset() first.")

        self._step += 1
        is_terminal = self._is_terminal_action(action)
        agent_content = action.message or action.reason or f"[{action.action_type}]"
        self._history.append(Message(role="agent", content=agent_content))

        reward = compute_step_reward(
            action=action, ticket=self._ticket, history=self._history,
            steps_used=self._step, max_steps=self._max_steps,
            is_terminal=is_terminal or self._step >= self._max_steps,
        )
        self._update_sentiment(action, reward.tone_score)
        self._action_log.append({
            "step": self._step, "action_type": action.action_type,
            "message": action.message, "reason": action.reason, "reward": reward.value,
        })

        done = is_terminal or self._step >= self._max_steps
        if not done:
            customer_reply = self._simulate_customer_reply(action)
            self._history.append(Message(role="customer", content=customer_reply))

        self._done = done
        obs = self._build_observation()
        info = {"ticket_id": self._ticket["id"], "action_log": self._action_log, "error": None}
        return obs, reward, done, info

    def state(self) -> dict:
        return {
            "session_id": self.session_id, "task": self.task,
            "ticket": self._ticket,
            "history": [m.model_dump() for m in self._history],
            "step": self._step, "max_steps": self._max_steps,
            "sentiment": self._sentiment, "done": self._done,
            "action_log": self._action_log,
        }

    def _build_observation(self) -> Observation:
        assert self._ticket is not None
        unresolved = self._compute_unresolved_issues()
        history_window = self._history[-20:]
        return Observation(
            session_id=self.session_id, ticket_id=self._ticket["id"],
            category=self._ticket["category"], priority=self._ticket["priority"],
            subject=self._ticket["subject"], conversation_history=history_window,
            step=self._step, max_steps=self._max_steps,
            customer_sentiment=round(self._sentiment, 3),
            mood_trajectory=self._sentiment_history[-3:],
            unresolved_issues=unresolved, is_done=self._done, task=self.task,
        )

    def _is_terminal_action(self, action: Action) -> bool:
        return action.action_type in (ActionType.CLOSE, ActionType.ESCALATE)

    def _update_sentiment(self, action: Action, tone_score: float) -> None:
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
        self._sentiment_history.append(round(self._sentiment, 3))

    def _simulate_customer_reply(self, action: Action) -> str:
        assert self._ticket is not None
        persona = self._ticket.get("customer_persona", "polite")

        if self._is_hierarchical:
            sim = get_customer_simulator()
            frustration = max(0.0, min(1.0, (1.0 - self._sentiment) / 2.0))
            return sim.generate_reply(
                persona=persona, frustration_level=frustration,
                history=self._history, ticket=self._ticket,
                action_type=action.action_type,
            )

        persona_replies = _FOLLOW_UPS.get(persona, _FOLLOW_UPS["polite"])
        action_key = "request_info" if action.action_type == ActionType.REQUEST_INFO else "respond"
        replies = persona_replies.get(action_key, persona_replies["respond"])

        if random.random() < 0.15:
            return random.choice([
                "I'm not seeing any update on my end. Did that go through?",
                "I got an error message when I tried that — it says 'service unavailable'.",
                "Something seems wrong, I'm still seeing the same issue.",
            ])

        template = random.choice(replies)
        follow_up = self._ticket.get("follow_up_info", "")
        return template.format(follow_up_info=follow_up)

    def _compute_unresolved_issues(self) -> list[str]:
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


class HierarchicalCustomerSupportEnv(CustomerSupportEnv):
    """
    3-level hierarchical multi-agent environment.

    Step flow:
    1. Client sends L1 (support_agent) action → env stores as pending
    2. Env returns obs with active_role='supervisor' for review
    3. Client sends L2 (supervisor) action:
       - approve → customer reply generated, next turn
       - reject/feedback → obs returned with feedback, active_role='support_agent'
       - escalate → obs with active_role='manager'
    4. Client sends L3 (manager) action:
       - override/resolve → customer reply, episode may end
       - send_back → returns to L1 with directive
    """

    def __init__(self, task: str = "hierarchy_medium") -> None:
        super().__init__(task=task)
        self._hierarchy = HierarchyState()
        self._policy_engine: Optional[PolicyEngine] = None
        self._pending_l1_action: Optional[Action] = None
        self._active_role: AgentRole = AgentRole.SUPPORT_AGENT
        self._escalation_chain: List[str] = []
        self._supervisor_feedback: Optional[str] = None
        self._manager_directive: Optional[str] = None
        self._environment_event: Optional[str] = None

    def reset(self) -> Observation:
        obs = super().reset()
        assert self._ticket is not None
        cfg = TASK_CONFIG[self.task]
        self._active_levels: List[int] = cfg.get("active_levels", [1, 2, 3])
        self._hinglish_enabled: bool = cfg.get("hinglish_enabled", False)
        self._multi_drift: bool = cfg.get("multi_drift", False)
        self._hierarchy = HierarchyState()
        self._policy_engine = PolicyEngine(
            task=self.task,
            category=self._ticket.get("category", "billing"),
            drift_probability=cfg.get("drift_probability", 0.3),
            multi_drift=self._multi_drift,
        )
        self._pending_l1_action = None
        self._active_role = AgentRole.SUPPORT_AGENT
        self._escalation_chain = []
        self._supervisor_feedback = None
        self._manager_directive = None
        self._environment_event = None
        return self._build_observation()

    def step(self, action: Action) -> tuple[Observation, Reward, bool, dict]:
        if self._done:
            raise RuntimeError("Episode is done. Call reset().")
        if self._ticket is None:
            raise RuntimeError("Not initialized. Call reset().")

        at = ActionType(action.action_type)

        if at in L1_ACTION_TYPES:
            return self._step_support(action)
        elif at in L2_ACTION_TYPES:
            return self._step_supervisor(action)
        elif at in L3_ACTION_TYPES:
            return self._step_manager(action)
        else:
            raise ValueError(f"Unknown action_type: {action.action_type}")

    def _step_support(self, action: Action) -> tuple[Observation, Reward, bool, dict]:
        """L1 Support Agent acts — action is held for supervisor review."""
        self._step += 1
        self._hierarchy.support_agent_actions += 1
        self._supervisor_feedback = None
        self._manager_directive = None

        agent_content = action.message or action.reason or f"[{action.action_type}]"
        self._history.append(Message(role="agent", content=agent_content))

        # Check for policy drift
        if self._policy_engine:
            drift = self._policy_engine.check_drift(self._step)
            if drift:
                self._environment_event = drift
                self._history.append(Message(role="system", content=drift))

        # Store pending action for supervisor review
        self._pending_l1_action = action
        self._hierarchy.pending_l1_action = {
            "action_type": action.action_type,
            "message": action.message,
            "reason": action.reason,
        }

        # Compute preliminary L1 reward
        is_terminal_intent = action.action_type in (ActionType.CLOSE, ActionType.ESCALATE)
        reward = compute_hierarchy_reward(
            action=action, ticket=self._ticket, history=self._history,
            steps_used=self._step, max_steps=self._max_steps,
            is_terminal=False,
            policy_text=self._policy_engine.get_active_policy_text() if self._policy_engine else "",
            hierarchy_state=self._hierarchy.model_dump(),
            use_llm_judge=True,
        )
        self._update_sentiment(action, reward.tone_score)

        self._action_log.append({
            "step": self._step, "role": "support_agent",
            "action_type": action.action_type,
            "message": action.message, "reason": action.reason,
            "reward": reward.value,
        })

        # ── Curriculum: Skip supervisor if L2 not in active_levels ─────────
        if 2 not in self._active_levels:
            # L1-only mode (curriculum_basic): auto-approve, deliver to customer
            if is_terminal_intent:
                self._done = True
            elif not self._done:
                customer_reply = self._simulate_customer_reply(action)
                self._history.append(Message(role="customer", content=customer_reply))
            self._pending_l1_action = None
            self._hierarchy.pending_l1_action = None
            obs = self._build_observation()
            info = {"ticket_id": self._ticket["id"], "action_log": self._action_log, "error": None}
            return obs, reward, self._done, info

        # Normal hierarchy: switch to supervisor for review
        self._active_role = AgentRole.SUPERVISOR
        self._hierarchy.current_phase = "supervisor_review"

        obs = self._build_observation()
        info = {"ticket_id": self._ticket["id"], "action_log": self._action_log, "error": None}
        return obs, reward, False, info

    def _step_supervisor(self, action: Action) -> tuple[Observation, Reward, bool, dict]:
        """L2 Supervisor reviews the pending L1 action."""
        self._step += 1
        self._hierarchy.supervisor_reviews += 1
        at = ActionType(action.action_type)

        # Log supervisor action
        sup_content = action.feedback_to_agent or action.reason or f"[{action.action_type}]"
        self._history.append(Message(role="supervisor", content=f"[SUPERVISOR] {sup_content}"))

        reward = compute_hierarchy_reward(
            action=action, ticket=self._ticket, history=self._history,
            steps_used=self._step, max_steps=self._max_steps,
            is_terminal=False,
            policy_text=self._policy_engine.get_active_policy_text() if self._policy_engine else "",
            hierarchy_state=self._hierarchy.model_dump(),
            use_llm_judge=True,
        )

        self._action_log.append({
            "step": self._step, "role": "supervisor",
            "action_type": action.action_type,
            "feedback": action.feedback_to_agent, "reason": action.reason,
            "reward": reward.value,
        })

        done = False

        if at == ActionType.SUPERVISOR_APPROVE:
            # Approved — deliver the L1 action to customer
            pending = self._pending_l1_action
            if pending and pending.action_type in (ActionType.CLOSE, ActionType.ESCALATE):
                done = True
                self._done = True
            elif not done:
                customer_reply = self._simulate_customer_reply(pending or action)
                self._history.append(Message(role="customer", content=customer_reply))
            self._active_role = AgentRole.SUPPORT_AGENT
            self._hierarchy.current_phase = "support_handling"
            self._pending_l1_action = None
            self._hierarchy.pending_l1_action = None

        elif at in (ActionType.SUPERVISOR_REJECT, ActionType.SUPERVISOR_FEEDBACK):
            # Rejected or feedback — send back to L1
            self._supervisor_feedback = action.feedback_to_agent
            self._hierarchy.supervisor_feedback_history.append(
                action.feedback_to_agent or "No specific feedback."
            )
            self._active_role = AgentRole.SUPPORT_AGENT
            self._hierarchy.current_phase = "support_handling"
            self._pending_l1_action = None
            self._hierarchy.pending_l1_action = None

        elif at == ActionType.SUPERVISOR_ESCALATE:
            # Escalate to manager (only if L3 is active in this curriculum stage)
            if 3 not in self._active_levels:
                # L3 not available in this curriculum stage — treat as terminal
                self._escalation_chain.append(
                    f"Supervisor escalated (auto-resolved, no L3 in curriculum): {action.reason or 'complex case'}"
                )
                done = True
                self._done = True
            else:
                self._escalation_chain.append(
                    f"Supervisor escalated: {action.reason or 'complex case'}"
                )
                self._hierarchy.escalation_reason = action.reason
                self._active_role = AgentRole.MANAGER
                self._hierarchy.current_phase = "manager_override"

        # Check step limit
        if self._step >= self._max_steps:
            done = True
            self._done = True

        obs = self._build_observation()
        if done:
            # Compute terminal reward
            terminal_reward = compute_hierarchy_reward(
                action=action, ticket=self._ticket, history=self._history,
                steps_used=self._step, max_steps=self._max_steps,
                is_terminal=True,
                policy_text=self._policy_engine.get_active_policy_text() if self._policy_engine else "",
                hierarchy_state=self._hierarchy.model_dump(),
                use_llm_judge=True,
            )
            reward = terminal_reward

        info = {"ticket_id": self._ticket["id"], "action_log": self._action_log, "error": None}
        return obs, reward, done, info

    def _step_manager(self, action: Action) -> tuple[Observation, Reward, bool, dict]:
        """L3 Manager handles escalated case."""
        self._step += 1
        self._hierarchy.manager_interventions += 1
        at = ActionType(action.action_type)

        mgr_content = action.message or action.feedback_to_agent or f"[{action.action_type}]"
        self._history.append(Message(role="manager", content=f"[MANAGER] {mgr_content}"))

        done = False

        if at in (ActionType.MANAGER_OVERRIDE, ActionType.MANAGER_RESOLVE):
            # Manager resolves directly
            done = True
            self._done = True
            if not self._done or at == ActionType.MANAGER_OVERRIDE:
                customer_reply = self._simulate_customer_reply(action)
                self._history.append(Message(role="customer", content=customer_reply))

        elif at == ActionType.MANAGER_SEND_BACK:
            # Send back to L1 with directive
            self._manager_directive = action.feedback_to_agent
            self._hierarchy.manager_directive_history.append(
                action.feedback_to_agent or "Handle with care."
            )
            self._active_role = AgentRole.SUPPORT_AGENT
            self._hierarchy.current_phase = "support_handling"
            self._pending_l1_action = None
            self._hierarchy.pending_l1_action = None

        if self._step >= self._max_steps:
            done = True
            self._done = True

        is_terminal = done
        reward = compute_hierarchy_reward(
            action=action, ticket=self._ticket, history=self._history,
            steps_used=self._step, max_steps=self._max_steps,
            is_terminal=is_terminal,
            policy_text=self._policy_engine.get_active_policy_text() if self._policy_engine else "",
            hierarchy_state=self._hierarchy.model_dump(),
            use_llm_judge=True,
        )

        self._action_log.append({
            "step": self._step, "role": "manager",
            "action_type": action.action_type,
            "message": action.message, "feedback": action.feedback_to_agent,
            "reward": reward.value,
        })

        obs = self._build_observation()
        info = {"ticket_id": self._ticket["id"], "action_log": self._action_log, "error": None}
        return obs, reward, done, info

    def _build_observation(self) -> Observation:
        assert self._ticket is not None
        unresolved = self._compute_unresolved_issues()
        history_window = self._history[-20:]
        return Observation(
            session_id=self.session_id, ticket_id=self._ticket["id"],
            category=self._ticket["category"], priority=self._ticket["priority"],
            subject=self._ticket["subject"], conversation_history=history_window,
            step=self._step, max_steps=self._max_steps,
            customer_sentiment=round(self._sentiment, 3),
            mood_trajectory=self._sentiment_history[-3:],
            unresolved_issues=unresolved, is_done=self._done, task=self.task,
            active_role=self._active_role.value,
            supervisor_feedback=self._supervisor_feedback,
            manager_directive=self._manager_directive,
            hierarchy_state=self._hierarchy,
            environment_event=self._environment_event,
            policy_context=(
                self._policy_engine.get_active_policy_text()
                if self._policy_engine else "Standard operating procedure."
            ),
            escalation_chain=self._escalation_chain,
        )

    def state(self) -> dict:
        base = super().state()
        base["hierarchy_state"] = self._hierarchy.model_dump()
        base["active_role"] = self._active_role.value
        base["escalation_chain"] = self._escalation_chain
        if self._policy_engine:
            base["policy_engine"] = self._policy_engine.state()
        return base
