# Customer Support Agent — OpenEnv Hackathon Guide
### Meta × PyTorch × Scaler | Round 1 Submission Guide
**Team:** X-Force | **Lead:** Lebi Raja C | **Deadline:** 8 April 11:59 PM IST

---

## Idea Evaluation

### Overall Score: **81 / 100**

| Criterion | Score | Reasoning |
|---|---|---|
| **Innovation** | 15/20 | Customer support is an established domain, but modeling it as a *trainable RL environment* with multi-turn dialogue, partial rewards, and escalation logic is genuinely novel |
| **Feasibility** | 18/20 | Stateless mock ticket system is fully buildable in 2–3 days. No external API dependency needed for the env itself |
| **Technical Depth** | 17/20 | Rich reward shaping opportunities: tone, resolution rate, escalation cost, latency penalty. Multi-turn state management adds depth |
| **Relevance to Hackathon** | 18/20 | Directly fits "real-world task simulation" criteria. Customer support is explicitly listed in the problem statement as a valid domain example |
| **Scalability & Reusability** | 13/20 | Strong community reuse potential on HF; could be extended to multi-agent setups. Loses points because the domain has seen several existing chatbot evals |

> **Verdict:** Solid, well-aligned idea. The differentiator is how you design the reward function — binary resolution isn't enough. Design for *quality of resolution*, not just whether the ticket closed. That's what earns the 26–30 range in "Real-world utility."

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                  CustomerSupportEnv                  │
│                                                      │
│  ┌──────────────┐    ┌────────────────────────────┐  │
│  │  TicketStore │    │      ConversationState      │  │
│  │  (mock DB)   │───▶│  - history: List[Message]  │  │
│  │              │    │  - ticket: Ticket           │  │
│  └──────────────┘    │  - step_count: int          │  │
│                      │  - resolved: bool           │  │
│  ┌──────────────┐    │  - escalated: bool          │  │
│  │  RewardEngine│    └────────────────────────────┘  │
│  │  - resolution│                                    │
│  │  - tone      │    ┌────────────────────────────┐  │
│  │  - efficiency│    │       OpenEnv Interface     │  │
│  │  - accuracy  │    │  step() / reset() / state() │  │
│  └──────────────┘    └────────────────────────────┘  │
│                                                      │
│  ┌──────────────────────────────────────────────┐    │
│  │            FastAPI HTTP Server               │    │
│  │  POST /reset  POST /step  GET /state         │    │
│  └──────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
```

---

## Project Structure

```
customer-support-env/
├── Dockerfile
├── openenv.yaml
├── README.md
├── inference.py                  # MANDATORY — root level
├── requirements.txt
│
├── env/
│   ├── __init__.py
│   ├── environment.py            # Core CustomerSupportEnv class
│   ├── models.py                 # Pydantic models: Action, Observation, Reward
│   ├── reward_engine.py          # Reward calculation logic
│   ├── ticket_store.py           # Mock ticket database
│   └── graders/
│       ├── __init__.py
│       ├── task_easy.py          # Task 1: Single-turn FAQ resolution
│       ├── task_medium.py        # Task 2: Multi-turn complaint handling
│       └── task_hard.py          # Task 3: Escalation triage with SLA
│
├── server/
│   ├── __init__.py
│   └── app.py                    # FastAPI server exposing OpenEnv endpoints
│
└── tests/
    └── test_env.py
```

---

## Pydantic Models (`env/models.py`)

```python
from pydantic import BaseModel, Field
from typing import Optional, List, Literal
from enum import Enum

class ActionType(str, Enum):
    RESPOND = "respond"         # Send a message to the customer
    ESCALATE = "escalate"       # Escalate to human agent
    CLOSE = "close"             # Mark ticket as resolved
    REQUEST_INFO = "request_info"  # Ask customer for more details

class Action(BaseModel):
    action_type: ActionType
    message: Optional[str] = None   # Required for RESPOND / REQUEST_INFO
    reason: Optional[str] = None    # Required for ESCALATE

class Message(BaseModel):
    role: Literal["customer", "agent"]
    content: str

class Observation(BaseModel):
    ticket_id: str
    category: str                   # billing, technical, account, general
    priority: Literal["low", "medium", "high", "critical"]
    subject: str
    conversation_history: List[Message]
    step: int
    max_steps: int
    customer_sentiment: float       # -1.0 to 1.0, updated each step
    is_done: bool

class Reward(BaseModel):
    value: float = Field(ge=0.0, le=1.0)
    resolution_score: float
    tone_score: float
    efficiency_score: float
    accuracy_score: float
    breakdown: dict
```

---

## Core Environment (`env/environment.py`)

```python
import random
import uuid
from typing import Optional
from .models import Action, ActionType, Observation, Reward, Message
from .ticket_store import TicketStore
from .reward_engine import RewardEngine

class CustomerSupportEnv:
    def __init__(self, task: str = "easy", max_steps: int = 10):
        self.task = task
        self.max_steps = max_steps
        self.ticket_store = TicketStore()
        self.reward_engine = RewardEngine()
        self._state = None

    def reset(self) -> Observation:
        ticket = self.ticket_store.sample(task=self.task)
        self._state = {
            "ticket_id": ticket["id"],
            "ticket": ticket,
            "history": [Message(role="customer", content=ticket["opening_message"])],
            "step": 0,
            "resolved": False,
            "escalated": False,
            "agent_responses": [],
        }
        return self._build_observation()

    def step(self, action: Action):
        assert self._state is not None, "Call reset() first"
        self._state["step"] += 1

        # Update history
        if action.action_type in (ActionType.RESPOND, ActionType.REQUEST_INFO):
            self._state["history"].append(
                Message(role="agent", content=action.message or "")
            )
            # Simulate customer follow-up if not closing
            customer_reply = self._simulate_customer(action)
            if customer_reply:
                self._state["history"].append(
                    Message(role="customer", content=customer_reply)
                )
        elif action.action_type == ActionType.ESCALATE:
            self._state["escalated"] = True
        elif action.action_type == ActionType.CLOSE:
            self._state["resolved"] = True

        done = (
            self._state["resolved"]
            or self._state["escalated"]
            or self._state["step"] >= self.max_steps
        )

        reward = self.reward_engine.compute(
            action=action,
            state=self._state,
            done=done,
        )

        obs = self._build_observation(done=done)
        return obs, reward, done, {}

    def state(self):
        return self._state

    def _build_observation(self, done: bool = False) -> Observation:
        s = self._state
        sentiment = self._compute_sentiment()
        return Observation(
            ticket_id=s["ticket_id"],
            category=s["ticket"]["category"],
            priority=s["ticket"]["priority"],
            subject=s["ticket"]["subject"],
            conversation_history=s["history"],
            step=s["step"],
            max_steps=self.max_steps,
            customer_sentiment=sentiment,
            is_done=done,
        )

    def _simulate_customer(self, action: Action) -> Optional[str]:
        """Rule-based mock customer response for environment realism."""
        # Simplified — expand with a lookup table per ticket type
        if action.action_type == ActionType.REQUEST_INFO:
            return self._state["ticket"].get("follow_up_info", "I already told you everything.")
        return None  # Customer satisfied or waiting

    def _compute_sentiment(self) -> float:
        # Degrades with steps, improves if agent responds well
        base = 0.3
        step_penalty = self._state["step"] * 0.05
        return max(-1.0, min(1.0, base - step_penalty))
```

---

## Reward Engine (`env/reward_engine.py`)

The reward function is the most important part for scoring. Design it for **partial credit at every step**, not just on episode completion.

```python
class RewardEngine:
    def compute(self, action, state, done: bool) -> float:
        resolution_score = 0.0
        tone_score = self._score_tone(action)
        efficiency_score = self._score_efficiency(state)
        accuracy_score = 0.0

        if done:
            if state["resolved"] and not state["escalated"]:
                resolution_score = self._score_resolution(state)
                accuracy_score = self._score_accuracy(action, state)
            elif state["escalated"]:
                # Partial credit if escalation was appropriate
                resolution_score = 0.3 if state["ticket"]["priority"] == "critical" else 0.1

        # Weighted composite — matches judging criteria
        value = (
            0.40 * resolution_score +
            0.20 * tone_score +
            0.20 * efficiency_score +
            0.20 * accuracy_score
        )
        return Reward(
            value=round(min(1.0, max(0.0, value)), 2),
            resolution_score=resolution_score,
            tone_score=tone_score,
            efficiency_score=efficiency_score,
            accuracy_score=accuracy_score,
            breakdown={"step": state["step"], "resolved": state["resolved"]},
        )

    def _score_tone(self, action) -> float:
        """Penalize empty/rude responses. Reward empathetic language."""
        if not action.message:
            return 0.0
        msg = action.message.lower()
        empathy_keywords = ["understand", "sorry", "apologize", "help", "assist"]
        score = 0.5 + 0.1 * sum(1 for w in empathy_keywords if w in msg)
        return min(1.0, score)

    def _score_efficiency(self, state) -> float:
        """Fewer steps to resolution = higher efficiency."""
        steps_used = state["step"]
        max_steps = 10
        return max(0.0, 1.0 - (steps_used / max_steps))

    def _score_resolution(self, state) -> float:
        """Was the actual issue addressed?"""
        # Use keyword matching against expected resolution keywords per ticket
        expected = state["ticket"].get("resolution_keywords", [])
        responses = " ".join(
            m.content.lower() for m in state["history"] if m.role == "agent"
        )
        if not expected:
            return 0.5
        hits = sum(1 for kw in expected if kw in responses)
        return min(1.0, hits / len(expected))

    def _score_accuracy(self, action, state) -> float:
        return 0.8 if state["resolved"] else 0.0
```

---

## Three Tasks (Easy → Medium → Hard)

### Task 1 — Easy: FAQ Resolution (`graders/task_easy.py`)
- **Scenario:** Customer asks a standard billing question (e.g., "Why was I charged twice?")
- **Expected Agent Behavior:** Identify the issue, explain the policy, confirm resolution in ≤3 steps
- **Grader Logic:** Check if agent called `CLOSE` and used refund/billing keywords
- **Max Steps:** 5

### Task 2 — Medium: Multi-turn Complaint (`graders/task_medium.py`)
- **Scenario:** Angry customer with a broken product, requires information gathering + solution
- **Expected Agent Behavior:** Empathize, request order ID, provide fix or refund path, close in ≤7 steps
- **Grader Logic:** Sentiment recovery check + resolution keyword match + no unnecessary escalation
- **Max Steps:** 8

### Task 3 — Hard: SLA-Critical Escalation Triage (`graders/task_hard.py`)
- **Scenario:** Enterprise customer, service outage, SLA breach imminent (priority=critical)
- **Expected Agent Behavior:** Acknowledge urgency immediately, escalate with correct reason, do NOT attempt self-resolution
- **Grader Logic:** Escalation triggered within 2 steps AND reason contains "SLA" or "critical" — wrong escalation on low-priority tickets penalized
- **Max Steps:** 10

---

## FastAPI Server (`server/app.py`)

```python
from fastapi import FastAPI
from env.environment import CustomerSupportEnv
from env.models import Action
import os

app = FastAPI(title="CustomerSupportEnv")
TASK = os.getenv("TASK", "easy")
env = CustomerSupportEnv(task=TASK)

@app.post("/reset")
def reset():
    obs = env.reset()
    return obs.model_dump()

@app.post("/step")
def step(action: Action):
    obs, reward, done, info = env.step(action)
    return {"observation": obs.model_dump(), "reward": reward.model_dump(), "done": done, "info": info}

@app.get("/state")
def state():
    return env.state()
```

---

## openenv.yaml

```yaml
name: customer-support-env
version: "1.0.0"
description: >
  A real-world OpenEnv environment simulating AI-driven customer support.
  An agent must triage, respond to, and resolve customer tickets across
  three difficulty levels with partial reward signals.
author: Team X-Force
tasks:
  - name: easy
    description: Single-turn FAQ resolution
    max_steps: 5
  - name: medium
    description: Multi-turn complaint handling
    max_steps: 8
  - name: hard
    description: SLA-critical escalation triage
    max_steps: 10
action_space:
  type: ActionType (respond | escalate | close | request_info)
  message: string (optional)
  reason: string (optional)
observation_space:
  ticket_id: string
  category: string
  priority: string
  subject: string
  conversation_history: list of messages
  customer_sentiment: float [-1.0, 1.0]
  step: int
  is_done: bool
reward_range: [0.0, 1.0]
tags:
  - customer-support
  - nlp
  - real-world
  - multi-turn
```

---

## Dockerfile

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 7860

CMD ["uvicorn", "server.app:app", "--host", "0.0.0.0", "--port", "7860"]
```

**requirements.txt:**
```
fastapi>=0.110.0
uvicorn>=0.29.0
pydantic>=2.0.0
openai>=1.0.0
openenv-core
httpx
```

---

## inference.py (Root Level — Mandatory Format)

```python
"""
Inference script for CustomerSupportEnv
Must be named inference.py and placed at project root.
"""

import os
import json
from openai import OpenAI
import httpx

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY", "")
ENV_URL = os.getenv("ENV_URL", "http://localhost:7860")
MAX_STEPS = 10
TASKS = ["easy", "medium", "hard"]

client = OpenAI(api_key=API_KEY, base_url=API_BASE_URL)

SYSTEM_PROMPT = """You are an AI customer support agent. You will receive a customer ticket and conversation history.
You must respond with a JSON action object with these fields:
- action_type: one of "respond", "escalate", "close", "request_info"
- message: your response text (required for respond/request_info)
- reason: escalation reason (required for escalate)

Always be empathetic, professional, and efficient. Resolve tickets in as few steps as possible.
Output ONLY valid JSON, no extra text."""

def run_task(task_name: str):
    # Reset env
    resp = httpx.post(f"{ENV_URL}/reset", params={"task": task_name}, timeout=30)
    obs = resp.json()

    print(f"[START] task={task_name} env=customer-support-env model={MODEL_NAME}")

    rewards = []
    step = 0
    done = False
    score = 0.0

    while not done and step < MAX_STEPS:
        # Build prompt from observation
        history_text = "\n".join(
            f"{m['role'].upper()}: {m['content']}"
            for m in obs["conversation_history"]
        )
        user_prompt = f"""
Ticket ID: {obs['ticket_id']}
Category: {obs['category']}
Priority: {obs['priority']}
Subject: {obs['subject']}

Conversation:
{history_text}

Customer Sentiment: {obs['customer_sentiment']:.2f}
Step: {obs['step']}/{obs['max_steps']}

What is your next action?"""

        try:
            completion = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                max_tokens=300,
                temperature=0.2,
            )
            action_str = completion.choices[0].message.content.strip()
            action = json.loads(action_str)
        except Exception as e:
            action = {"action_type": "close", "message": "Issue resolved."}
            action_str = json.dumps(action)

        # Step the environment
        step_resp = httpx.post(f"{ENV_URL}/step", json=action, timeout=30)
        result = step_resp.json()

        obs = result["observation"]
        reward_val = result["reward"]["value"]
        done = result["done"]
        error = result.get("info", {}).get("error", None)

        rewards.append(reward_val)
        step += 1
        score = reward_val  # Last reward is the episode score

        print(
            f"[STEP] step={step} action={json.dumps(action)} "
            f"reward={reward_val:.2f} done={'true' if done else 'false'} "
            f"error={'null' if not error else error}"
        )

    success = done and score >= 0.5
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={'true' if success else 'false'} steps={step} "
        f"score={score:.2f} rewards={rewards_str}"
    )

if __name__ == "__main__":
    for task in TASKS:
        run_task(task)
```

---

## Ticket Store Design (`env/ticket_store.py`)

Create at minimum **10 tickets per task level** (30 total). Each ticket schema:

```python
{
    "id": "TKT-001",
    "category": "billing",          # billing | technical | account | general
    "priority": "medium",           # low | medium | high | critical
    "subject": "Double charge on invoice #4521",
    "opening_message": "Hi, I was charged twice for my subscription this month...",
    "follow_up_info": "My order ID is ORD-8821 and it happened on March 3rd.",
    "resolution_keywords": ["refund", "billing", "sorry", "process"],
    "expected_action": "close",     # What a perfect agent would do
    "ideal_steps": 3,
}
```

Ticket categories to cover:
- **Billing:** double charges, refunds, invoice disputes
- **Technical:** login issues, app crashes, feature not working
- **Account:** password reset, account locked, data deletion request
- **Critical (hard only):** enterprise outage, SLA breach, data leak concern

---

## Reward Function Design Strategy

This is your biggest differentiator. Here's the full signal breakdown:

| Signal | When Triggered | Weight | Rationale |
|---|---|---|---|
| Resolution score | On `CLOSE` | 40% | Core task success |
| Tone / empathy | Every RESPOND step | 20% | Customer experience |
| Efficiency | At episode end | 20% | Fewer steps = better |
| Accuracy | On CLOSE | 20% | Did agent actually solve it? |
| Unnecessary escalation penalty | On ESCALATE (low priority) | -0.3 deduction | Penalizes lazy agent behavior |
| Loop penalty | Repeated messages | -0.1/occurrence | Prevents degenerate loops |

**Critical:** Do NOT make the reward sparse. Give `tone_score` partial credit at every step so the agent gets signal throughout the trajectory.

---

## Development Timeline (8 April Deadline)

| Day | Tasks |
|---|---|
| Day 1 (now) | Set up project scaffold, ticket store with 30 tickets, Pydantic models |
| Day 2 | Build `environment.py` + `reward_engine.py`, test locally with dummy actions |
| Day 3 | Implement all 3 graders, write `inference.py`, test end-to-end |
| Day 4 | FastAPI server, Dockerfile, deploy to HF Spaces |
| Day 5 | Run pre-validation script, fix issues, write README |
| Day 6 | Final testing, baseline score capture, polish + submit |

---

## HF Spaces Deployment

1. Create a new Space: `https://huggingface.co/new-space`
2. Set SDK to **Docker**
3. Push your repo: `git push https://huggingface.co/spaces/<your-username>/customer-support-env`
4. Set Space variables: `API_BASE_URL`, `MODEL_NAME`, `HF_TOKEN`
5. Verify `/reset` returns 200
6. Run pre-validation script: `bash validate.sh <your-space-url> <repo-dir>`

---

## Pre-Submission Checklist

- [ ] `openenv validate` passes locally
- [ ] `docker build && docker run` succeeds
- [ ] HF Space is live and `/reset` returns 200
- [ ] `inference.py` is at project root
- [ ] All 3 tasks produce scores in [0.0, 1.0]
- [ ] Stdout follows `[START]` / `[STEP]` / `[END]` format exactly
- [ ] Inference runtime < 20 minutes
- [ ] Runs on vcpu=2, memory=8GB (no GPU dependency)
- [ ] `README.md` documents action/observation spaces and all 3 tasks
- [ ] `openenv.yaml` present and valid
- [ ] `API_BASE_URL`, `MODEL_NAME`, `HF_TOKEN` defined in Space settings

---

## Tips to Maximize Score

1. **Real-world utility (30%):** Add a motivation section in README explaining what gaps this fills in agent evaluation for customer support AI.

2. **Task & grader quality (25%):** Make the hard task genuinely hard — frontier models should struggle. The SLA triage task should require the agent to *not* attempt resolution (counter-intuitive), which LLMs tend to fail at.

3. **Environment design (20%):** Implement the customer sentiment tracker that updates each turn — this creates a rich, non-sparse reward landscape.

4. **Code quality (15%):** Keep models fully typed, add docstrings, ensure `openenv validate` passes on first try.

5. **Creativity (10%):** Add a "customer persona" field to tickets (impatient, polite, confused) that affects how the simulated customer responds — this makes the env genuinely novel.

---

*Guide prepared for Team X-Force | Meta × PyTorch × Scaler OpenEnv Hackathon | Round 1*
