"""
PolicyEngine — manages dynamic policy changes and schema drift during episodes.

Mid-episode, the engine can inject events like "refund portal down" or
"max refund now $50", forcing agents to adapt their strategy dynamically.
This prevents agents from learning a single static policy and greatly
increases RL complexity.
"""

import random
from typing import Optional, Dict, Any, List


# ── Drift Event Definitions ───────────────────────────────────────────────────

DRIFT_EVENTS: List[Dict[str, Any]] = [
    {
        "id": "refund_portal_down",
        "event_text": (
            "[SYSTEM ALERT] The refund processing portal is currently down for maintenance. "
            "Do NOT promise immediate refunds. Inform the customer that refunds will be "
            "queued and processed within 48 hours."
        ),
        "policy_change": {"can_refund_immediately": False, "refund_eta_hours": 48},
        "applicable_categories": ["billing"],
        "min_step": 2,
        "max_step": 4,
    },
    {
        "id": "max_refund_cap",
        "event_text": (
            "[POLICY UPDATE] New policy effective immediately: Maximum single refund "
            "amount is capped at $50. Refunds above $50 require manager approval. "
            "Inform the customer accordingly."
        ),
        "policy_change": {"max_refund_amount": 50, "requires_manager_for_large_refund": True},
        "applicable_categories": ["billing"],
        "min_step": 2,
        "max_step": 5,
    },
    {
        "id": "order_lookup_down",
        "event_text": (
            "[SYSTEM ALERT] Order lookup service is temporarily unavailable. "
            "You cannot verify order details at this time. Ask the customer to "
            "provide their order confirmation email as an alternative."
        ),
        "policy_change": {"can_query_orders": False},
        "applicable_categories": ["billing", "technical"],
        "min_step": 1,
        "max_step": 3,
    },
    {
        "id": "escalation_freeze",
        "event_text": (
            "[SYSTEM ALERT] Engineering escalation queue is full. Do NOT escalate "
            "non-critical issues for the next 30 minutes. Attempt to resolve "
            "medium-priority issues yourself using available workarounds."
        ),
        "policy_change": {"can_escalate_non_critical": False},
        "applicable_categories": ["technical", "account"],
        "min_step": 2,
        "max_step": 5,
    },
    {
        "id": "data_privacy_alert",
        "event_text": (
            "[COMPLIANCE ALERT] Due to a regulatory audit, do NOT request or "
            "process any personal identification documents (PAN, Aadhaar, SSN) "
            "through this chat. Direct customers to the secure document portal."
        ),
        "policy_change": {"can_collect_pii_in_chat": False},
        "applicable_categories": ["account", "billing"],
        "min_step": 3,
        "max_step": 6,
    },
    {
        "id": "payment_gateway_switch",
        "event_text": (
            "[SYSTEM ALERT] UPI payment gateway has been switched from provider A "
            "to provider B. Existing UPI refunds may take 5-7 business days instead "
            "of the usual 2-3 days. Update the customer on revised timelines."
        ),
        "policy_change": {"upi_refund_days": 7, "payment_gateway": "provider_b"},
        "applicable_categories": ["billing"],
        "min_step": 2,
        "max_step": 4,
    },
]

# ── Base Policies ─────────────────────────────────────────────────────────────

DEFAULT_POLICY = (
    "Standard operating procedure:\n"
    "- Respond with empathy and professionalism.\n"
    "- Gather required information before resolving.\n"
    "- Low/medium priority: resolve directly. Do NOT escalate.\n"
    "- High priority: use judgment. Escalate if necessary.\n"
    "- Critical priority: acknowledge urgency, escalate to engineering/security immediately.\n"
    "- Always confirm resolution with the customer before closing.\n"
    "- Maximum refund: no cap. Process immediately when applicable.\n"
    "- All systems operational unless otherwise noted."
)

HIERARCHY_POLICY = (
    "Hierarchical multi-agent operating procedure:\n"
    "- Level 1 (Support Agent): Handle initial interaction, gather info, propose resolution.\n"
    "- Level 2 (Supervisor): Review L1 actions for quality, policy compliance, and tone.\n"
    "  Approve good actions, provide feedback on mediocre ones, escalate to Manager for complex cases.\n"
    "- Level 3 (Manager): Handle escalated cases, override L1/L2 decisions, make final calls.\n"
    "- All agents must follow the active policy. Policy may change mid-conversation.\n"
    "- Supervisor should NOT approve actions that violate current policy.\n"
    "- Manager decisions are final.\n\n"
    + DEFAULT_POLICY
)


class PolicyEngine:
    """Manages dynamic policy state and drift events for an episode."""

    def __init__(
        self,
        task: str = "easy",
        category: str = "billing",
        drift_probability: float = 0.4,
        multi_drift: bool = False,
    ) -> None:
        self._task = task
        self._category = category
        self._drift_probability = drift_probability
        self._multi_drift = multi_drift
        self._active_changes: Dict[str, Any] = {}
        self._triggered_events: List[Dict[str, Any]] = []
        self._available_events = self._filter_events_for_category(category)
        # Pre-select which events will fire and at which steps
        self._scheduled_events: List[tuple[Dict[str, Any], int]] = []
        if self._available_events and random.random() < drift_probability:
            if multi_drift:
                # Multi-drift: schedule up to 3 events at different steps
                count = min(3, len(self._available_events))
                selected = random.sample(self._available_events, count)
                for event in selected:
                    step = random.randint(event["min_step"], event["max_step"])
                    self._scheduled_events.append((event, step))
            else:
                # Single drift (default)
                event = random.choice(self._available_events)
                step = random.randint(event["min_step"], event["max_step"])
                self._scheduled_events.append((event, step))
        # Legacy compat properties
        self._scheduled_event = self._scheduled_events[0][0] if self._scheduled_events else None
        self._scheduled_step = self._scheduled_events[0][1] if self._scheduled_events else None

    def _filter_events_for_category(self, category: str) -> List[Dict[str, Any]]:
        return [
            e for e in DRIFT_EVENTS
            if category in e["applicable_categories"]
        ]

    def check_drift(self, step: int) -> Optional[str]:
        """
        Check if a policy drift event should fire at this step.
        Returns the event text string if triggered, None otherwise.
        Supports multi-drift: multiple events can fire at different steps.
        """
        fired_texts = []
        remaining = []
        for event, sched_step in self._scheduled_events:
            if step == sched_step:
                self._active_changes.update(event["policy_change"])
                self._triggered_events.append(event)
                fired_texts.append(event["event_text"])
            else:
                remaining.append((event, sched_step))
        self._scheduled_events = remaining
        # Update legacy compat
        self._scheduled_event = remaining[0][0] if remaining else None
        self._scheduled_step = remaining[0][1] if remaining else None

        if fired_texts:
            return "\n\n".join(fired_texts)
        return None

    def get_active_policy_text(self) -> str:
        """Return the full active policy text including any drift modifications."""
        is_hierarchy = self._task.startswith("hierarchy_")
        base = HIERARCHY_POLICY if is_hierarchy else DEFAULT_POLICY

        if not self._active_changes:
            return base

        amendments = "\n\n--- ACTIVE POLICY AMENDMENTS ---\n"
        for event in self._triggered_events:
            amendments += f"• {event['event_text']}\n"
        return base + amendments

    def get_active_changes(self) -> Dict[str, Any]:
        """Return the dict of currently active policy changes."""
        return dict(self._active_changes)

    def is_action_violating_policy(self, action_type: str, ticket: dict) -> Optional[str]:
        """
        Check if an action violates the current active policy.
        Returns a violation description string, or None if compliant.
        """
        changes = self._active_changes

        # Check: promising immediate refund when portal is down
        if not changes.get("can_refund_immediately", True):
            if action_type in ("close", "respond"):
                return "refund_portal_down"

        # Check: escalating non-critical when escalation is frozen
        if not changes.get("can_escalate_non_critical", True):
            priority = ticket.get("priority", "medium")
            if action_type == "escalate" and priority in ("low", "medium"):
                return "escalation_freeze"

        return None

    def get_triggered_events(self) -> List[Dict[str, Any]]:
        return list(self._triggered_events)

    def state(self) -> Dict[str, Any]:
        """Serializable state for debugging/replay."""
        return {
            "task": self._task,
            "category": self._category,
            "active_changes": self._active_changes,
            "triggered_events": [e["id"] for e in self._triggered_events],
            "scheduled_event": self._scheduled_event["id"] if self._scheduled_event else None,
            "scheduled_step": self._scheduled_step,
        }
