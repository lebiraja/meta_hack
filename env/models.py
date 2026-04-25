"""
Typed models for the Customer Support RL Environment.

Supports both single-agent (Round 1) and hierarchical multi-agent (Round 2) modes.
Backward compatible: single-agent actions still work by defaulting role to 'support_agent'.
"""

from pydantic import BaseModel, Field, model_validator
from typing import Optional, List, Literal, Dict, Any
from enum import Enum


# ── Agent Roles ────────────────────────────────────────────────────────────────

class AgentRole(str, Enum):
    SUPPORT_AGENT = "support_agent"
    SUPERVISOR = "supervisor"
    MANAGER = "manager"


class SupervisorDecision(str, Enum):
    APPROVE = "approve"                # L1 action is good, send to customer
    REJECT = "reject"                  # L1 action is bad, redo
    FEEDBACK = "feedback"              # L1 action needs adjustment, provide guidance
    ESCALATE_TO_MANAGER = "escalate_to_manager"  # Too complex for L2, send to L3


class ManagerDecision(str, Enum):
    OVERRIDE = "override"              # Manager takes over and responds directly
    APPROVE_ESCALATION = "approve_escalation"  # Approve L1's escalation request
    RESOLVE_DIRECTLY = "resolve_directly"      # Manager resolves the issue
    SEND_BACK = "send_back"            # Send back to L1 with directive


# ── Action Types ───────────────────────────────────────────────────────────────

class ActionType(str, Enum):
    # L1 Support Agent actions
    RESPOND = "respond"
    ESCALATE = "escalate"
    CLOSE = "close"
    REQUEST_INFO = "request_info"
    # L1 DB query actions (internal, no customer reply)
    QUERY_USER_PROFILE = "query_user_profile"
    QUERY_ORDER_DETAILS = "query_order_details"
    # L2 Supervisor actions
    SUPERVISOR_APPROVE = "supervisor_approve"
    SUPERVISOR_REJECT = "supervisor_reject"
    SUPERVISOR_FEEDBACK = "supervisor_feedback"
    SUPERVISOR_ESCALATE = "supervisor_escalate"
    # L3 Manager actions
    MANAGER_OVERRIDE = "manager_override"
    MANAGER_RESOLVE = "manager_resolve"
    MANAGER_SEND_BACK = "manager_send_back"


# Map action types to their originating role
ACTION_ROLE_MAP: Dict[ActionType, AgentRole] = {
    ActionType.RESPOND: AgentRole.SUPPORT_AGENT,
    ActionType.ESCALATE: AgentRole.SUPPORT_AGENT,
    ActionType.CLOSE: AgentRole.SUPPORT_AGENT,
    ActionType.REQUEST_INFO: AgentRole.SUPPORT_AGENT,
    ActionType.QUERY_USER_PROFILE: AgentRole.SUPPORT_AGENT,
    ActionType.QUERY_ORDER_DETAILS: AgentRole.SUPPORT_AGENT,
    ActionType.SUPERVISOR_APPROVE: AgentRole.SUPERVISOR,
    ActionType.SUPERVISOR_REJECT: AgentRole.SUPERVISOR,
    ActionType.SUPERVISOR_FEEDBACK: AgentRole.SUPERVISOR,
    ActionType.SUPERVISOR_ESCALATE: AgentRole.SUPERVISOR,
    ActionType.MANAGER_OVERRIDE: AgentRole.MANAGER,
    ActionType.MANAGER_RESOLVE: AgentRole.MANAGER,
    ActionType.MANAGER_SEND_BACK: AgentRole.MANAGER,
}

# L1 action types (for backward compatibility checks)
L1_ACTION_TYPES = {
    ActionType.RESPOND, ActionType.ESCALATE,
    ActionType.CLOSE, ActionType.REQUEST_INFO,
    ActionType.QUERY_USER_PROFILE, ActionType.QUERY_ORDER_DETAILS,
}

# DB query action types (internal lookups, no customer reply)
DB_QUERY_ACTION_TYPES = {
    ActionType.QUERY_USER_PROFILE,
    ActionType.QUERY_ORDER_DETAILS,
}
L2_ACTION_TYPES = {
    ActionType.SUPERVISOR_APPROVE, ActionType.SUPERVISOR_REJECT,
    ActionType.SUPERVISOR_FEEDBACK, ActionType.SUPERVISOR_ESCALATE,
}
L3_ACTION_TYPES = {
    ActionType.MANAGER_OVERRIDE, ActionType.MANAGER_RESOLVE,
    ActionType.MANAGER_SEND_BACK,
}


# ── Core Models ────────────────────────────────────────────────────────────────

class Action(BaseModel):
    action_type: ActionType
    message: Optional[str] = Field(default=None, max_length=2000)
    reason: Optional[str] = Field(default=None, max_length=500)
    # DB query fields (L1 internal actions)
    email: Optional[str] = Field(default=None, max_length=254, description="Email for query_user_profile")
    order_id: Optional[str] = Field(default=None, max_length=100, description="Order ID for query_order_details")
    # Hierarchy fields (default for backward compat)
    role: AgentRole = Field(default=AgentRole.SUPPORT_AGENT)
    internal_note: Optional[str] = Field(
        default=None, max_length=1000,
        description="Internal reasoning, not shown to customer"
    )
    feedback_to_agent: Optional[str] = Field(
        default=None, max_length=1000,
        description="Supervisor/Manager feedback to the lower-level agent"
    )

    model_config = {"use_enum_values": True}

    @model_validator(mode="after")
    def validate_content(self):
        at = ActionType(self.action_type)
        # L1 validations
        if at == ActionType.RESPOND:
            if not self.message or not self.message.strip():
                raise ValueError("message cannot be empty when action_type is 'respond'")
        if at == ActionType.ESCALATE:
            if not self.reason or not self.reason.strip():
                raise ValueError("reason cannot be empty when action_type is 'escalate'")
        # DB query validations
        if at == ActionType.QUERY_USER_PROFILE:
            if not self.email or not self.email.strip():
                raise ValueError("email required for query_user_profile")
        if at == ActionType.QUERY_ORDER_DETAILS:
            if not self.order_id or not self.order_id.strip():
                raise ValueError("order_id required for query_order_details")
        # L2 validations
        if at == ActionType.SUPERVISOR_FEEDBACK:
            if not self.feedback_to_agent or not self.feedback_to_agent.strip():
                raise ValueError("feedback_to_agent required for supervisor_feedback")
        if at == ActionType.SUPERVISOR_ESCALATE:
            if not self.reason or not self.reason.strip():
                raise ValueError("reason required for supervisor_escalate")
        # L3 validations
        if at in (ActionType.MANAGER_OVERRIDE, ActionType.MANAGER_RESOLVE):
            if not self.message or not self.message.strip():
                raise ValueError("message required for manager_override/manager_resolve")
        if at == ActionType.MANAGER_SEND_BACK:
            if not self.feedback_to_agent or not self.feedback_to_agent.strip():
                raise ValueError("feedback_to_agent required for manager_send_back")
        # Auto-set role from action_type if not explicitly provided
        expected_role = ACTION_ROLE_MAP.get(at)
        if expected_role and self.role != expected_role:
            self.role = expected_role
        return self


class Message(BaseModel):
    role: Literal["customer", "agent", "supervisor", "manager", "system"]
    content: str


class HierarchyState(BaseModel):
    """Internal state of the agent hierarchy within an episode."""
    support_agent_actions: int = 0
    supervisor_reviews: int = 0
    manager_interventions: int = 0
    current_phase: str = Field(
        default="support_handling",
        description="Current phase: support_handling, supervisor_review, manager_override"
    )
    escalation_reason: Optional[str] = None
    supervisor_feedback_history: List[str] = Field(default_factory=list)
    manager_directive_history: List[str] = Field(default_factory=list)
    pending_l1_action: Optional[Dict[str, Any]] = Field(
        default=None,
        description="The L1 action waiting for supervisor review"
    )


class Observation(BaseModel):
    session_id: str
    ticket_id: str
    category: str
    priority: Literal["low", "medium", "high", "critical"]
    subject: str
    conversation_history: List[Message]
    step: int
    max_steps: int
    customer_sentiment: float = Field(ge=-1.0, le=1.0)
    mood_trajectory: List[float] = Field(default_factory=list)
    unresolved_issues: List[str]
    is_done: bool
    task: str
    # DB query results (accumulated across episode)
    retrieved_data: Dict[str, Dict[str, Any]] = Field(
        default_factory=lambda: {"users": {}, "orders": {}},
        description="Data fetched via query_user_profile / query_order_details"
    )
    # ── Hierarchy fields (Round 2) ─────────────────────────────────────────────
    active_role: str = Field(
        default="support_agent",
        description="Which agent should act next: support_agent, supervisor, manager"
    )
    supervisor_feedback: Optional[str] = Field(
        default=None,
        description="Latest feedback from supervisor to support agent"
    )
    manager_directive: Optional[str] = Field(
        default=None,
        description="Latest directive from manager"
    )
    hierarchy_state: Optional[HierarchyState] = None
    environment_event: Optional[str] = Field(
        default=None,
        description="Schema drift / policy change event"
    )
    policy_context: str = Field(
        default="Standard operating procedure. Follow all default policies.",
        description="Current active policy text"
    )
    escalation_chain: List[str] = Field(
        default_factory=list,
        description="History of escalations in this episode"
    )


class Reward(BaseModel):
    value: float = Field(ge=0.0, le=1.0)
    resolution_score: float
    tone_score: float
    efficiency_score: float
    accuracy_score: float
    breakdown: Dict[str, Any]
    # ── Hierarchy reward fields (Round 2) ──────────────────────────────────────
    empathy_score: float = Field(default=0.0, description="LLM-judged empathy")
    oversight_score: float = Field(default=0.0, description="Supervisor oversight quality")
    decision_quality_score: float = Field(default=0.0, description="Manager decision quality")
    policy_adherence_score: float = Field(default=0.0, description="LLM-judged policy adherence")
    role_rewards: Dict[str, float] = Field(
        default_factory=dict,
        description="Per-role reward breakdown: {support_agent: x, supervisor: y, manager: z}"
    )

    @model_validator(mode="after")
    def _round_floats(self):
        self.value = round(self.value, 4)
        self.resolution_score = round(self.resolution_score, 4)
        self.tone_score = round(self.tone_score, 4)
        self.efficiency_score = round(self.efficiency_score, 4)
        self.accuracy_score = round(self.accuracy_score, 4)
        self.empathy_score = round(self.empathy_score, 4)
        self.oversight_score = round(self.oversight_score, 4)
        self.decision_quality_score = round(self.decision_quality_score, 4)
        self.policy_adherence_score = round(self.policy_adherence_score, 4)
        self.role_rewards = {k: round(v, 4) for k, v in self.role_rewards.items()}
        return self


class Ticket(BaseModel):
    id: str
    category: str
    priority: Literal["low", "medium", "high", "critical"]
    subject: str
    opening_message: str
    follow_up_info: str
    required_info_before_close: List[str]
    expected_resolution_type: str
    ideal_max_steps: int
    customer_persona: Literal["impatient", "polite", "confused"]
    task: Literal["easy", "medium", "hard", "nightmare",
                  "hierarchy_easy", "hierarchy_medium", "hierarchy_hard",
                  "curriculum_basic", "curriculum_supervisor",
                  "curriculum_full_hierarchy", "curriculum_nightmare",
                  "multi_domain"]
    # DB linkage fields (optional; legacy tickets leave these empty)
    customer_email: Optional[str] = None
    related_order_ids: List[str] = Field(default_factory=list)
