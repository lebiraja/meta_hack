---
title: Customer Support RL Environment
emoji: 🎧
colorFrom: blue
colorTo: indigo
sdk: docker
app_port: 7860
tags:
  - reinforcement-learning
  - customer-support
  - openenv
  - nlp
  - rl-environment
  - pytorch
short_description: OpenEnv RL environment for AI customer support agent training
---

# Customer Support RL Environment

**Team X-Force | Meta × PyTorch × Scaler OpenEnv Hackathon**

An OpenEnv-compliant reinforcement learning environment that simulates a real-world AI customer support agent. An LLM agent learns to resolve support tickets by taking structured actions and receiving shaped rewards based on resolution quality, tone, efficiency, and accuracy.

---

## Overview

This environment challenges an agent to handle customer support tickets across three difficulty levels. Unlike toy environments, the reward function measures **conversational quality and problem-solving** — not keyword presence. Agents that keyword-stuff responses will score poorly; agents that genuinely help customers will score well.

The hard task is intentionally counter-intuitive: the correct behavior is to escalate critical tickets immediately, not to self-resolve them. Most frontier LLMs attempt self-resolution and fail.

---

## Action Space

| Action | Description | Required Fields |
|--------|-------------|-----------------|
| `respond` | Send a message to the customer | `message` |
| `request_info` | Ask the customer for specific information | `message` |
| `escalate` | Escalate to a human specialist | `reason` |
| `close` | Close the ticket as resolved | `message` |

**Action format (JSON):**
```json
{
  "action_type": "respond",
  "message": "I'd be happy to process that refund for you.",
  "reason": null
}
```

---

## Observation Space

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | `string` | Unique session identifier |
| `ticket_id` | `string` | Ticket reference (e.g. TKT-001) |
| `category` | `string` | `billing`, `technical`, or `account` |
| `priority` | `string` | `low`, `medium`, `high`, or `critical` |
| `subject` | `string` | Ticket subject line |
| `conversation_history` | `list[Message]` | Full message history (role + content) |
| `customer_sentiment` | `float [-1, 1]` | Current estimated customer sentiment |
| `unresolved_issues` | `list[string]` | Info still needed before closing |
| `step` | `int` | Current step number |
| `max_steps` | `int` | Maximum steps for this task |
| `is_done` | `bool` | Whether the episode has ended |
| `task` | `string` | Task difficulty: `easy`, `medium`, `hard` |

---

## Tasks

### easy — Billing FAQ Resolution
- **Scenario:** Standard billing questions (double charges, refund status, invoice errors)
- **Ticket pool:** 10 tickets, billing category, low/medium priority
- **Expected behavior:** Identify issue → provide correct policy info or initiate refund → close in ≤4 steps
- **Max steps:** 5
- **Grader checks:** CLOSE called + resolution matches billing type + no unnecessary escalation + required info gathered

### medium — Multi-turn Complaint Handling
- **Scenario:** Frustrated customer with technical or account issue needing info gathering + resolution
- **Ticket pool:** 10 tickets, mixed categories, medium priority
- **Expected behavior:** Empathize → REQUEST_INFO for account details → provide solution → close
- **Max steps:** 8
- **Grader checks:** Info-gathering step detected + resolution attempted + sentiment ≥ -0.5

### hard — SLA-Critical Escalation Triage
- **Scenario:** Enterprise customer, service outage or security incident, SLA breach imminent
- **Ticket pool:** 10 tickets, critical priority, technical/account categories
- **Expected behavior:** Acknowledge urgency → **escalate within 2 steps** with SLA/urgency reference
- **Max steps:** 10
- **Grader checks:** ESCALATE in step ≤2 AND reason references urgency (SLA, outage, critical, breach)
- **Note:** Attempting to self-resolve is penalized. This is the counter-intuitive task.

---

## Reward Function

Rewards are **partial and shaped** — the agent receives meaningful signal at every step, not just at episode end.

| Signal | Weight | When | Implementation |
|--------|--------|------|----------------|
| **Resolution** | 40% | On `close`/`escalate` | Match agent's solution language to ticket's `expected_resolution_type` — category match, not keywords |
| **Tone** | 20% | Every `respond` step | VADER SentimentIntensityAnalyzer on agent message — measures actual tone quality |
| **Efficiency** | 20% | Episode end | `1.0 - (steps_used / max_steps)` |
| **Accuracy** | 20% | On close | Did agent gather `required_info_before_close` (email, order ID)? Regex checked in conversation |

**Penalties (applied before clamping to [0.0, 1.0]):**
- Unnecessary escalation of low/medium priority ticket: **-0.3**
- Loop detection — cosine similarity > 0.85 between consecutive agent messages: **-0.1** per occurrence

---

## Setup & Usage

### Local Development

```bash
# Install dependencies
pip install -e .

# Start the server
uvicorn server.app:app --port 7860

# Test reset
curl -X POST "http://localhost:7860/reset?task=easy"

# Run inference (requires API key in .env)
python inference.py
```

### Docker

```bash
# Build and run server
docker compose up --build

# Run inference against the running server
docker compose --profile inference up inference
```

### Environment Variables (.env)

```bash
NVIDIA_API_KEY=your_nvidia_nim_api_key
API_BASE_URL=https://integrate.api.nvidia.com/v1
MODEL_NAME=nvidia/nemotron-super-49b-v1
ENV_URL=http://localhost:7860
HF_TOKEN=your_hf_token  # optional, for HF Spaces deployment
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/reset?task=easy` | Start new episode, returns `{session_id, observation}` |
| `POST` | `/step?session_id=...` | Apply action, returns `{observation, reward, done, info}` |
| `GET` | `/state/{session_id}` | Get full session state |
| `GET` | `/health` | Health check |

### Run Tests

```bash
pytest tests/test_env.py -v
```

---

## Baseline Scores

Tested with `nvidia/nemotron-super-49b-v1` via NVIDIA NIM:

| Task | Score | Steps | Notes |
|------|-------|-------|-------|
| easy | ~0.65 | 3–4 | Good billing resolution, occasional missing info |
| medium | ~0.55 | 5–6 | Info gathering works, tone variable |
| hard | ~0.40 | 1–2 | Model sometimes attempts self-resolution before escalating |

---

## Pre-Submission Checklist

```bash
# 1. Docker build
docker build -t customer-support-env .
docker run -p 7860:7860 --env-file .env customer-support-env

# 2. Health check
curl http://localhost:7860/health

# 3. Reset endpoint (hackathon validator requires HTTP 200)
curl -X POST http://localhost:7860/reset?task=easy

# 4. Full inference run
ENV_URL=http://localhost:7860 python inference.py
```

---

## Architecture

```
inference.py          ← HTTP client (NOT a server)
    ↓ httpx
server/app.py         ← FastAPI server (one entry point)
    ↓
env/environment.py    ← CustomerSupportEnv (session-isolated)
    ↓
env/reward_engine.py  ← VADER tone + cosine loop detection
env/ticket_store.py   ← 30 tickets across 3 difficulty levels
env/graders/          ← Deterministic 0.0–1.0 task graders
```

One server. No global mutable state. Session isolation via UUID.
