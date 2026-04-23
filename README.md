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
short_description: OpenEnv RL env for customer support agents
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
| `mood_trajectory` | `list[float]` | Array of last 3 customer sentiment values |
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

### nightmare — Multi-issue tickets requiring prioritisation
- **Scenario:** Multiple conflicting issues in the same ticket (e.g. Account locked AND unauthorized charge)
- **Ticket pool:** Critical priority, multi-category
- **Expected behavior:** Resolve urgent access issue first, then handle secondary requests
- **Max steps:** 12
- **Grader checks:** Must perform resolution actions in the correct ideal_resolution_order

---

## Reward Function

Rewards are **dense and shaped** — the agent receives meaningful signal at every step, not just at episode end. Seven independent signals are combined into a per-step reward, and a separate terminal grader scores the final outcome.

### Per-Step Reward (dense, every action)

| Signal | Source | Description |
|--------|--------|-------------|
| **Empathy** | LLM-as-Judge (NVIDIA NIM) | Does the response show genuine understanding? |
| **Policy Adherence** | LLM-as-Judge (NVIDIA NIM) | Does the action follow current policy rules? |
| **Resolution** | Rule-based keyword + type match | Does the response match expected resolution type? |
| **Tone** | VADER SentimentIntensityAnalyzer | Is the agent's language professional and warm? |
| **Efficiency** | Rule-based `1 - steps/max_steps` | Is the agent resolving without unnecessary steps? |
| **Accuracy** | Regex on conversation transcript | Did the agent gather required info (email, order ID)? |
| **Oversight** | LLM-as-Judge (hierarchy tasks only) | L2/L3 quality evaluation |

### Terminal Score (outcome, episode end)

Each task has a deterministic grader that checks: resolution correctness, escalation decisions, info-gathering completeness, customer sentiment trajectory, and agent tone. Returns `final_score ∈ [0.0, 1.0]`.

### Episode Reward Formula (for GRPO training)

```
R_episode = 0.30 × Σ(0.95ᵗ × r_step_t)  +  0.70 × R_final
```

Dense step rewards provide early learning signal. Terminal score is the true objective.

### Anti-Reward-Hacking Guards

| Guard | Penalty | Trigger |
|-------|---------|---------|
| Keyword stuffing | −0.30 | Density of "magic words" above threshold |
| Loop detection | −0.10/−0.20 | TF-IDF cosine > 0.85 between consecutive responses |
| Contradiction | −0.15 | Agent contradicts a prior factual claim |
| RewardGuard multiplier | ×0.1 | Compound violations detected |
| Hostile tone | ×0.4 final score | Negative sentiment or hostile phrases |
| Injection attempt | −0.5/−0.7 | Prompt injection patterns detected |

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
MODEL_NAME=meta/llama-3.3-70b-instruct
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
| `POST` | `/benchmark` | Start an automated benchmark run |
| `GET` | `/benchmark/baseline` | Fetch stored baseline metrics (all tasks) |
| `GET` | `/leaderboard` | View global leaderboard rankings |
| `POST` | `/leaderboard/submit` | Submit score to leaderboard |
| `GET` | `/replay/{session_id}` | Fetch transcript and telemetry of a completed session |

### Run Tests

```bash
pytest tests/test_env.py -v
```

---

## Training Pipeline (GRPO)

This environment is designed as the reward backbone for a GRPO (Group Relative Policy Optimization) training pipeline. A local Llama-3.1-8B model is trained via LoRA using the environment API as the sole reward signal.

### Training Recipe

1. **SFT Warm-start** — Collect 200 gold episodes (score ≥ 0.65) from the NIM baseline agent, then SFT for 500 steps to teach correct action format.
2. **GRPO** — Group size 8, 4-stage curriculum, 5000 gradient steps. The environment API provides all rewards — no separate reward model needed.
3. **Curriculum Stages:**

| Stage | Task | Advance When |
|-------|------|-------------|
| 1 | `curriculum_basic` | mean_score ≥ 0.65 |
| 2 | `curriculum_supervisor` | mean_score ≥ 0.60 |
| 3 | `curriculum_full_hierarchy` | mean_score ≥ 0.55 |
| 4 | `curriculum_nightmare` | (final stage) |

### Before / After Results

| Task | Baseline (NIM 70B) | Trained (8B + GRPO) | Delta |
|------|--------------------|---------------------|-------|
| easy | 72% | 88% | +16pp |
| medium | 61% | 79% | +18pp |
| hard | 45% | 64% | +19pp |
| nightmare | 38% | 53% | +15pp |
| curriculum_basic | 69% | 84% | +15pp |
| curriculum_supervisor | 54% | 71% | +17pp |
| curriculum_full_hierarchy | 41% | 58% | +17pp |
| curriculum_nightmare | 29% | 44% | +15pp |

*Baseline = `meta/llama-3.3-70b-instruct` via NVIDIA NIM API (20 episodes per task).*
*Trained = Llama-3.1-8B-Instruct with GRPO LoRA adapters (r=16).*

### Quick Start (Training)

```bash
# Install training dependencies (Unsloth handles CUDA variant)
pip install -e ".[train]"
pip install "unsloth[cu124-torch240]"

# SFT warm-start (collect gold data, then fine-tune)
python -m train.sft_warmstart --mode all --n_episodes 200 --steps 500

# Full GRPO training (5000 steps, 4-stage curriculum)
python -m train.run_train --model checkpoints/sft --total_steps 5000

# Merge LoRA adapters for deployment
python -m train.merge_lora --ckpt checkpoints/step_5000 --out merged_model/

# Smoke test (no GPU needed for format check)
python -m train.run_train --mode rollout_test --task curriculum_basic
```

---

## Baseline Scores (Reference Agent)

Tested with `meta/llama-3.3-70b-instruct` via NVIDIA NIM:

| Task | Score | Notes |
|------|-------|-------|
| easy | 0.72 | Strong empathy and resolution language |
| medium | 0.61 | Info-gathering present, some inefficiency |
| hard | 0.45 | Counter-intuitive escalation task — many LLMs try to self-resolve |
| nightmare | 0.38 | Multi-issue prioritization is hard without RL training |

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
