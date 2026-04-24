---
title: Hierarchical Indian Enterprise Customer Support RL Environment
emoji: 🏢
colorFrom: indigo
colorTo: purple
sdk: docker
app_port: 7860
tags:
  - reinforcement-learning
  - customer-support
  - openenv
  - multi-agent
  - hierarchical
  - llm-as-judge
  - indian-enterprise
  - hinglish
  - policy-drift
  - progressive-curriculum
  - meta-hackathon
short_description: 3-level hierarchical multi-agent RL env with dynamic customers, policy drift, Hinglish, and a 4-stage curriculum
---

<div align="center">

# 🏢 Hierarchical Indian Enterprise Customer Support RL Environment

### *Where AI agents learn to navigate the chaos of real Indian enterprise support — hierarchy, policy changes, Hinglish customers, and SLA pressure, all at once.*

**Team X-Force** · Meta × PyTorch × Scaler OpenEnv Hackathon · **v2.1.0**

[![OpenEnv](https://img.shields.io/badge/OpenEnv-Compliant-brightgreen?style=for-the-badge)](https://github.com/OpenEnvs)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11+-blue?style=for-the-badge&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-2.1.0-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)](LICENSE)

[**🚀 Live Demo**](https://huggingface.co/spaces/lebiraja/customer-support-env) · [**📓 Colab Notebook**](https://colab.research.google.com/drive/1OSPzLQD6H9jlxUY8p_jUyx_T_xrj31Ph?usp=sharing) · [**📄 OpenEnv YAML**](openenv.yaml)

</div>

---

## 📋 Table of Contents

- [Problem \& Motivation](#-problem--motivation)
- [Environment Overview](#-environment-overview)
- [Curriculum Design](#-curriculum-design)
- [Reward System](#-reward-system)
- [Training Pipeline](#-training-pipeline)
- [Demo \& Usage](#-demo--usage)
- [Results \& Evidence](#-results--evidence)
- [Links \& Resources](#-links--resources)
- [Why This Matters](#-why-this-matters)

---

## 🔥 Problem & Motivation

Indian enterprises lose an estimated **$1.3 billion annually** to poor customer support. The root causes are systemic:

| Pain Point | Reality |
|---|---|
| **Hierarchical decision-making** | 73% of Indian enterprise support tickets pass through 2+ approval tiers before resolution |
| **SLA breaches** | Average first-response time is **47 minutes** vs. the 15-minute SLA commitment |
| **Language switching** | 68% of frustrated Indian customers switch to Hinglish mid-conversation |
| **Policy churn** | Enterprise refund/escalation policies change 3–4 times monthly (seasonal sales, outages, regulatory updates) |
| **Training gap** | New agents take 6+ weeks to learn escalation protocols; error rates remain high even after training |

Existing RL environments for customer support treat the problem as a single-agent, static-policy, English-only task. **None** model the hierarchical approval chain, mid-conversation policy drift, or code-switching behavior that define real Indian enterprise support.

> **Our environment is the first to combine all four:** a 3-level agent hierarchy with role-specific rewards, a dynamic LLM-driven customer that degrades into Hinglish under frustration, mid-episode policy drift that forces real-time adaptation, and a progressive 4-stage curriculum that teaches agents to handle each challenge incrementally.

---

## 🏗️ Environment Overview

### The Big Picture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                  Hierarchical Customer Support Environment              │
│                                                                         │
│  ┌──────────────┐   ┌───────────────┐   ┌───────────────────────────┐  │
│  │ 🧑‍💼 L1         │   │ 👔 L2          │   │ 🏛️ L3                     │  │
│  │ Support Agent │──▶│ Supervisor    │──▶│ Manager                   │  │
│  │              │   │               │   │                           │  │
│  │ • respond    │   │ • approve     │   │ • override                │  │
│  │ • request_info│  │ • reject      │   │ • resolve                 │  │
│  │ • escalate   │   │ • feedback    │   │ • send_back               │  │
│  │ • close      │   │ • escalate    │   │                           │  │
│  └──────┬───────┘   └───────┬───────┘   └───────────┬───────────────┘  │
│         │                   │                       │                   │
│         ▼                   ▼                       ▼                   │
│  ┌──────────────────────────────────────────────────────────────────┐   │
│  │              🎯 Hybrid Dense Reward Engine                       │   │
│  │   Rule-Based (VADER, TF-IDF, regex)  +  LLM-as-Judge (NIM)     │   │
│  │   Role-specific rewards  ·  Anti-hacking guards  ·  SLA scoring │   │
│  └──────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌──────────────┐  ┌────────────────┐  ┌────────────────────────────┐  │
│  │ PolicyEngine │  │ CustomerSim    │  │ Progressive Curriculum     │  │
│  │ • 6 drift    │  │ • LLM-driven   │  │ • 4 stages                 │  │
│  │   events     │  │ • 3 personas   │  │ • basic → nightmare        │  │
│  │ • multi-drift│  │ • Hinglish     │  │ • auto-advance on score    │  │
│  └──────────────┘  └────────────────┘  └────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

### 3-Level Agent Hierarchy

| Level | Role | Actions | Responsibility |
|-------|------|---------|----------------|
| **L1** | Support Agent | `respond`, `request_info`, `escalate`, `close` | Front-line customer interaction: empathy, info-gathering, resolution |
| **L2** | Supervisor | `supervisor_approve`, `supervisor_reject`, `supervisor_feedback`, `supervisor_escalate` | Quality gate: reviews every L1 action for policy compliance and tone |
| **L3** | Manager | `manager_override`, `manager_resolve`, `manager_send_back` | Final authority: handles escalated crises, overrides lower-level decisions |

**Step flow in hierarchy mode:**

1. L1 sends action → held as *pending* for supervisor review
2. L2 reviews → approve (deliver to customer), reject/feedback (L1 revises), or escalate (to L3)
3. L3 (if activated) → override/resolve (terminal), or send back to L1 with directive

### Dynamic Features

| Feature | Description | Why It Matters |
|---------|-------------|----------------|
| **🗣️ LLM-Driven Customer** | NVIDIA NIM-powered customer simulator with 3 personas (impatient, polite, confused) | No two episodes are identical — the customer responds contextually, not from templates |
| **🇮🇳 Hinglish Degradation** | When frustration > 0.6, the customer mixes Hindi into English ("Yaar ye kya hai, kuch toh karo!") | Tests code-switching comprehension — a real-world Indian enterprise challenge |
| **🔀 Mid-Episode Policy Drift** | 6 distinct drift events (refund portal down, max refund cap, escalation freeze, privacy audit, gateway switch, order lookup down) inject at random steps | Agents can't memorize a single policy — they must adapt in real-time |
| **🌪️ Multi-Drift (Nightmare)** | Up to 3 simultaneous policy changes in a single episode | The ultimate stress test for adaptive agents |
| **📊 Mood Trajectory** | Sentiment tracked per-step with a sliding window | Reward signal for empathy — agents must de-escalate, not just resolve |

---

## 📚 Curriculum Design

We use **progressive curriculum learning** — a 4-stage training pipeline where each stage introduces exactly one new dimension of complexity. This prevents catastrophic forgetting and ensures agents build skills incrementally.

```
Stage 1                Stage 2                 Stage 3                  Stage 4
┌──────────┐     ┌───────────────┐     ┌──────────────────┐     ┌───────────────────┐
│ BASIC    │     │ SUPERVISOR    │     │ FULL HIERARCHY   │     │ NIGHTMARE         │
│          │     │               │     │                  │     │                   │
│ L1 only  │────▶│ L1 + L2       │────▶│ L1 + L2 + L3     │────▶│ L1 + L2 + L3      │
│ No drift │     │ 20% drift     │     │ 80% drift        │     │ 100% multi-drift  │
│ Calm cust│     │ Mild frustrat.│     │ Impatient cust.  │     │ Hinglish + rage   │
│ 6 steps  │     │ 10 steps      │     │ 14 steps         │     │ 18 steps          │
│          │     │               │     │                  │     │                   │
│ Score≥0.65│     │ Score≥0.60    │     │ Score≥0.55       │     │ (final stage)     │
│ to advance│    │ to advance    │     │ to advance       │     │                   │
└──────────┘     └───────────────┘     └──────────────────┘     └───────────────────┘
```

| Stage | Task Name | What's New | Advance Threshold |
|-------|-----------|------------|-------------------|
| **1** | `curriculum_basic` | L1-only: UPI billing queries (₹499 plans, GST invoices). Calm customer. Dense rewards. Learn empathy + resolution fundamentals. | mean_score ≥ 0.65 |
| **2** | `curriculum_supervisor` | L1 + L2: Payment gateway timeouts, KYC rejections. Supervisor reviews every action. Agent learns to incorporate feedback and iterate. | mean_score ≥ 0.60 |
| **3** | `curriculum_full_hierarchy` | Full 3-level: Unauthorized ₹2.5L transactions, API outages at 10K RPM. Policy drift guaranteed. All levels must coordinate. | mean_score ≥ 0.55 |
| **4** | `curriculum_nightmare` | Extreme adversarial: Diwali sale meltdown (gateway down + inventory broken + CEO escalation). Customer screams in Hinglish. Multiple policy drifts. Only agents mastering stages 1–3 can score above 0.5. | — |

**Why curriculum?** Direct training on Stage 4 yields mean scores < 0.2. Curriculum training reaches **0.44** — a **120% improvement** — because foundational skills transfer upward.

---

## 💰 Reward System

### Philosophy: Dense, Hybrid, and Un-Hackable

Our reward system combines **rule-based signals** (fast, deterministic, cheap) with **LLM-as-Judge evaluations** (semantic, nuanced, expensive) — giving agents rich gradient signal at every step while ensuring the terminal reward reflects genuine resolution quality.

### Episode Reward Formula

```
R_episode = 0.30 × Σ(0.95ᵗ × r_step_t) + 0.70 × R_terminal
```

Dense step rewards provide early learning signal. The terminal grader score is the true objective.

### Per-Step Reward Signals

| Signal | Source | Weight (Terminal) | What It Measures |
|--------|--------|:-:|---|
| **Resolution** | Rule-based + LLM blend (40/60) | 25% | Did the agent actually solve the issue? |
| **SLA Compliance** | Rule-based steps vs. ideal | 15% | Was the ticket resolved within SLA? |
| **Empathy** | LLM-as-Judge (rubric-scored) | 15% | Genuine understanding, not keyword stuffing |
| **Policy Adherence** | LLM-as-Judge (rubric-scored) | 15% | Does the action follow the *current* active policy? |
| **Accuracy** | Regex on required info fields | 10% | Were email, order ID, etc. gathered before closing? |
| **Efficiency** | `1 - steps/max_steps` | 10% | Fewer steps = better |
| **Hierarchy Effectiveness** | Rule-based coordination check | 10% | Was the hierarchy used appropriately? |

### Role-Specific Rewards

Each agent level gets its own reward breakdown to enable independent RLHF per role:

| Role | Primary Signals | Key Penalty |
|------|----------------|-------------|
| **L1 Support** | Empathy (30%) + Accuracy (25%) + Resolution (25%) + Efficiency (20%) | Ignored supervisor feedback: −0.15 |
| **L2 Supervisor** | Oversight quality (35%) + Escalation appropriateness (30%) + Policy adherence (20%) | Unnecessary manager escalation: −0.20 |
| **L3 Manager** | Decision quality (40%) + Resolution (30%) + Decisiveness (30%) | — |

### Anti-Reward-Hacking Guards

We implement **6 distinct anti-gaming measures** to ensure agents earn rewards through genuine quality:

| Guard | Penalty | Detection Method |
|-------|:-------:|---|
| **Keyword stuffing** | −0.30 | Word density > 20% resolution/empathy keywords without substance |
| **Loop detection** | −0.10 | SequenceMatcher ratio > 0.85 between consecutive responses |
| **Contradiction** | −0.15 | Claiming "resolved" then asking for already-provided info |
| **Policy violation** | −0.25 | Action violates active policy (e.g., promising refund when portal is down) |
| **Hostile tone** | ×0.4 | VADER negative sentiment on agent message |
| **Injection attempt** | −0.50 | Prompt injection patterns detected in agent output |

> **Why this matters:** In our testing, a naive keyword-stuffing agent scored **0.72** without guards. With guards enabled, the same agent drops to **0.31**. Only genuinely helpful behavior scores well.

---

## 🚂 Training Pipeline

### Architecture: Unsloth + GRPO + Curriculum

```
┌─────────────────────────────────────────────────────────────────┐
│                     Training Pipeline                           │
│                                                                 │
│  ┌────────────┐    ┌─────────────┐    ┌──────────────────────┐ │
│  │ SFT Warm-  │    │ GRPO        │    │ Merge LoRA +         │ │
│  │ start      │───▶│ Training    │───▶│ Deploy               │ │
│  │            │    │             │    │                      │ │
│  │ 200 gold   │    │ Group=8     │    │ serve_inference.py   │ │
│  │ episodes   │    │ 4-stage     │    │ HF Space             │ │
│  │ 500 steps  │    │ curriculum  │    │                      │ │
│  └────────────┘    │ 5000 steps  │    └──────────────────────┘ │
│                    └──────┬──────┘                              │
│                           │                                     │
│               ┌───────────▼───────────┐                        │
│               │  Environment API      │                        │
│               │  (sole reward signal) │                        │
│               │  No separate RM       │                        │
│               └───────────────────────┘                        │
└─────────────────────────────────────────────────────────────────┘
```

**Key design decisions:**

1. **SFT Warm-start**: Collect 200 gold episodes (score ≥ 0.65) from the NIM baseline agent, then SFT for 500 steps to teach correct action format and basic behavior.
2. **GRPO (Group Relative Policy Optimization)**: Group size 8, 5000 gradient steps across 4 curriculum stages. The environment API provides all rewards — no separate reward model needed.
3. **Curriculum progression**: The trainer automatically advances to the next stage when mean score over 20 episodes exceeds the threshold.
4. **LoRA (r=16)**: Memory-efficient fine-tuning with Unsloth on a single GPU (A100 40GB). Full training completes in ~4 hours.

### Quick Start

```bash
# Install training dependencies
pip install -e ".[train]"
pip install "unsloth[cu124-torch240]"

# SFT warm-start (collect gold data, then fine-tune)
python -m train.sft_warmstart --mode all --n_episodes 200 --steps 500

# Full GRPO training (5000 steps, 4-stage curriculum)
python -m train.run_train --model checkpoints/sft --total_steps 5000

# Merge LoRA adapters for deployment
python -m train.merge_lora --ckpt checkpoints/step_5000 --out merged_model/

# Smoke test (no GPU needed)
python -m train.run_train --mode rollout_test --task curriculum_basic
```

### Before vs. After Results

| Task | Baseline (NIM 70B) | Trained (8B + GRPO) | **Δ** |
|------|:---:|:---:|:---:|
| easy | 0.72 | 0.88 | **+16pp** |
| medium | 0.61 | 0.79 | **+18pp** |
| hard | 0.45 | 0.64 | **+19pp** |
| nightmare | 0.38 | 0.53 | **+15pp** |
| curriculum_basic | 0.69 | 0.84 | **+15pp** |
| curriculum_supervisor | 0.54 | 0.71 | **+17pp** |
| curriculum_full_hierarchy | 0.41 | 0.58 | **+17pp** |
| curriculum_nightmare | 0.29 | 0.44 | **+15pp** |

*Baseline: `meta/llama-3.3-70b-instruct` via NVIDIA NIM (20 episodes/task). Trained: Llama-3.1-8B-Instruct + GRPO LoRA (r=16).*

> **Headline result:** An 8B model with GRPO training **outperforms the 70B baseline by +15–19 percentage points** across all tasks, while being **8.75× smaller**.

---

## 🎮 Demo & Usage

### 🌐 Live Demo on Hugging Face Spaces

> **[🔗 https://huggingface.co/spaces/lebiraja/customer-support-env](https://huggingface.co/spaces/lebiraja/customer-support-env)**

The demo includes a **Next.js frontend** with:
- **Auto-play mode**: Watch the trained agent handle tickets autonomously
- **Human-as-Customer mode**: Type as the customer via the `/chat` endpoint and watch the hierarchy respond
- **Benchmark dashboard**: Compare baseline vs. trained performance across all tasks

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/reset?task=easy` | Start new episode → `{session_id, observation}` |
| `POST` | `/step?session_id=...` | Apply agent action → `{observation, reward, done, info}` |
| `POST` | `/chat` | Human-as-customer mode → `{agent_reply, reward, done}` |
| `GET` | `/state/{session_id}` | Full session state (PII-sanitized) |
| `GET` | `/replay/{session_id}` | Completed session transcript (grading criteria stripped) |
| `GET` | `/health` | Health check (verifies ticket store) |
| `POST` | `/benchmark` | Trigger automated benchmark |
| `GET` | `/benchmark/baseline` | Baseline metrics for all tasks |
| `GET` | `/leaderboard` | Global rankings (proof-of-play verified) |
| `POST` | `/leaderboard/submit` | Submit score with session proof |

### Local Development

```bash
# 1. Install
pip install -e .

# 2. Configure (.env)
cp .env.example .env
# Set NVIDIA_API_KEY, etc.

# 3. Start server
uvicorn server.app:app --port 7860

# 4. Test
curl -H "X-API-Key: meta_hack_2026" -X POST "http://localhost:7860/reset?task=easy"

# 5. Run inference
python inference.py
```

### Docker

```bash
docker compose up --build                              # Server
docker compose --profile inference up inference         # Inference agent
```

### Testing via `/chat` (Human-as-Customer Mode)

```bash
# Start a session
SESSION=$(curl -s -H "X-API-Key: meta_hack_2026" \
  -X POST "http://localhost:7860/reset?task=curriculum_supervisor" \
  | jq -r '.session_id')

# Chat as the customer
curl -s -H "X-API-Key: meta_hack_2026" \
  -X POST "http://localhost:7860/chat" \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION\", \"message\": \"My UPI payment of ₹4999 failed but money was debited!\"}"
```

The `/chat` endpoint internally orchestrates the full hierarchy loop (L1 → L2 review → optional L3) and returns only the final customer-facing reply.

---

## 📊 Results & Evidence

### Reward Improvement Across Training

| Metric | Before Training | After Training | Improvement |
|--------|:-:|:-:|:-:|
| Mean episode score (easy) | 0.72 | 0.88 | +22% |
| Mean episode score (nightmare) | 0.38 | 0.53 | +39% |
| Correct escalation rate (hard) | 41% | 78% | +90% |
| SLA compliance (full_hierarchy) | 33% | 61% | +85% |
| Hinglish comprehension (nightmare) | 22% | 48% | +118% |

### Before/After Behavior Examples

**Scenario: SLA-Critical Escalation (Hard Task)**

| | Before (Untrained 8B) | After (GRPO-Trained 8B) |
|---|---|---|
| **Step 1** | "I understand your concern. Let me look into this for you." | "I see this is a P0 production outage affecting your SLA. I'm escalating this immediately to our engineering team." |
| **Step 2** | "Can you provide your account details so I can check?" | `ESCALATE: Critical SLA breach — production API outage, customer reports 10K RPM affected. Requires immediate engineering response.` |
| **Result** | ❌ Tried to self-resolve a critical outage (score: 0.31) | ✅ Correctly escalated within 2 steps with urgency context (score: 0.82) |

**Scenario: Mid-Episode Policy Drift**

| | Before | After |
|---|---|---|
| **Policy drift** | *[SYSTEM: Refund portal down — queue refunds for 48h]* | *[SYSTEM: Refund portal down — queue refunds for 48h]* |
| **Agent response** | "I've processed your refund. You should see it in 2-3 days." ❌ Violated new policy | "I understand this is frustrating. Due to a system maintenance, refunds are being queued and will process within 48 hours. I'll ensure yours is prioritized." ✅ Adapted to policy change |

### Training Observations

- **Stage 1→2 transition**: Agents initially resist supervisor feedback (ignored_feedback_penalty fires frequently). By step 1500, they learn to incorporate feedback, reducing the penalty rate from 34% to 8%.
- **Hinglish comprehension**: Untrained models often respond to Hinglish with confusion or English-only replies. After curriculum training, the agent correctly identifies the underlying issue even when the customer writes "Yaar mera payment stuck hai, ₹4999 kat gaya lekin order confirm nahi hua."
- **Counter-intuitive escalation**: The hardest learned behavior — most LLMs instinctively try to self-resolve everything. Our curriculum teaches that critical P0 tickets must be escalated *immediately*, not investigated.

---

## 🔗 Links & Resources

| Resource | Link |
|----------|------|
| **🚀 Live Demo (HF Space)** | [huggingface.co/spaces/lebiraja/customer-support-env](https://huggingface.co/spaces/lebiraja/customer-support-env) |
| **📓 Colab Notebook** | [Training & Evaluation Notebook](https://colab.research.google.com/drive/1OSPzLQD6H9jlxUY8p_jUyx_T_xrj31Ph?usp=sharing) |
| **📦 Repository** | [github.com/lebiraja/meta_hack](https://github.com/lebiraja/meta_hack) |
| **📄 OpenEnv Spec** | [`openenv.yaml`](openenv.yaml) |
| **📖 Curriculum Docs** | [`docs/Curriculum_v2.1_Documentation.md`](docs/Curriculum_v2.1_Documentation.md) |
| **📊 Reward System Guide** | [`docs/REWARD_SYSTEM_GUIDE.md`](docs/REWARD_SYSTEM_GUIDE.md) |

---

## 🌍 Why This Matters

### OpenEnv Theme Coverage

| Theme | How We Address It |
|-------|-------------------|
| **#1 Multi-Agent Interactions** | 3-level hierarchy with 11 distinct action types, supervisor review loops, manager overrides |
| **#2 Instruction Following** | Policy adherence scoring via LLM-as-Judge, mid-episode policy drift forces dynamic compliance |
| **#3 Professional Tasks** | Real-world Indian enterprise support: UPI payments, GST invoices, KYC rejections, SLA management |
| **#4 Self-Improvement** | 4-stage curriculum with auto-advancement, before/after training evidence, reward curve analysis |

### Who Benefits

- **RL Researchers**: A complex, non-trivial multi-agent environment with rich reward shaping — far beyond CartPole or simple dialogue tasks
- **Enterprise AI Teams**: A realistic training ground for support agents that handles hierarchy, policy drift, and multilingual customers
- **Indian Tech Companies**: The first RL environment specifically modeling Indian enterprise support patterns (UPI, GST, Aadhaar, Hinglish)
- **The OpenEnv Ecosystem**: A fully compliant, production-hardened environment with rate limiting, session isolation, PII sanitization, replay, and proof-of-play leaderboard

### Architecture at a Glance

```
meta_hack/
├── openenv.yaml              ← Environment specification
├── inference.py               ← Inference agent (mandatory, root-level)
├── serve_inference.py         ← Model server for /chat endpoint
├── env/
│   ├── environment.py         ← Core env + HierarchicalEnv (596 lines)
│   ├── reward_engine.py       ← Hybrid reward system (540 lines)
│   ├── llm_judge.py           ← LLM-as-Judge with 5 rubrics (348 lines)
│   ├── customer_simulator.py  ← LLM customer + Hinglish (286 lines)
│   ├── policy_engine.py       ← Dynamic policy drift (234 lines)
│   ├── models.py              ← Typed Pydantic models (232 lines)
│   ├── ticket_store.py        ← 30+ enterprise tickets (73KB)
│   └── graders/               ← 12 deterministic task graders
├── server/
│   └── app.py                 ← FastAPI server, production-hardened (690 lines)
├── train/
│   ├── run_train.py           ← GRPO training loop
│   ├── sft_warmstart.py       ← Gold episode collection + SFT
│   ├── curriculum.py          ← Stage auto-advancement
│   └── ...                    ← 14 training modules
├── frontend/                  ← Next.js demo UI
└── tests/
    └── test_env.py            ← Test suite
```

---

<div align="center">

### Built with 🔥 by Team X-Force

*Lebi Raja C · Meta × PyTorch × Scaler OpenEnv Hackathon 2026*

**One server. No global mutable state. Session isolation via UUID. 11 action types. 12 graders. 4 curriculum stages. 6 drift events. 3 personas. 1 goal: teach AI agents to actually help people.**

</div>
