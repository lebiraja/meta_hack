from pydantic import BaseModel, Field
from typing import Optional, List, Literal, Dict, Any
from enum import Enum


class ActionType(str, Enum):
    RESPOND = "respond"
    ESCALATE = "escalate"
    CLOSE = "close"
    REQUEST_INFO = "request_info"


class Action(BaseModel):
    action_type: ActionType
    message: Optional[str] = None
    reason: Optional[str] = None

    model_config = {"use_enum_values": True}


class Message(BaseModel):
    role: Literal["customer", "agent"]
    content: str


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
    unresolved_issues: List[str]
    is_done: bool
    task: str


class Reward(BaseModel):
    value: float = Field(ge=0.0, le=1.0)
    resolution_score: float
    tone_score: float
    efficiency_score: float
    accuracy_score: float
    breakdown: Dict[str, Any]


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
    task: Literal["easy", "medium", "hard"]
