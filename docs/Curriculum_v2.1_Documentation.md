# Progressive Curriculum v2.1.0 — Documentation

> **Version**: 2.1.0 | **Branch**: `feat/round2` | **Commit**: `77773e2`  
> **Date**: April 23, 2026 | **Team**: X-Force

---

## Table of Contents

1. [Overview](#overview)
2. [Why a Curriculum?](#why-a-curriculum)
3. [The 4-Stage Curriculum](#the-4-stage-curriculum)
4. [Architecture Changes](#architecture-changes)
5. [TASK_CONFIG Deep Dive](#task_config-deep-dive)
6. [Grader Design](#grader-design)
7. [Environment Behavior by Stage](#environment-behavior-by-stage)
8. [Policy Engine: Multi-Drift Support](#policy-engine-multi-drift-support)
9. [API Usage](#api-usage)
10. [Test Results](#test-results)
11. [Files Changed](#files-changed)
12. [Training Recommendations](#training-recommendations)

---

## Overview

The v2.1.0 update introduces a **progressive 4-stage curriculum** to the hierarchical multi-agent customer support RL environment. This curriculum systematically trains RL models by gradually increasing task complexity — from basic L1-only ticket handling to extreme adversarial scenarios with Hinglish, multi-drift, and full 3-level hierarchy under pressure.

The system now supports **11 total tasks** across three categories:

| Category | Tasks | Purpose |
|----------|-------|---------|
| Round 1 (Single-agent) | `easy`, `medium`, `hard`, `nightmare` | Backward-compatible single-agent training |
| Round 2 (Hierarchical) | `hierarchy_easy`, `hierarchy_medium`, `hierarchy_hard` | Multi-agent hierarchy testing |
| **Round 2 (Curriculum)** | `curriculum_basic`, `curriculum_supervisor`, `curriculum_full_hierarchy`, `curriculum_nightmare` | **Progressive RL training pipeline** |

---

## Why a Curriculum?

Standard RL training on complex environments faces a **cold-start problem**: agents receive sparse, noisy reward signals and struggle to learn meaningful behavior. A curriculum solves this by:

1. **Dense early rewards**: Stage 1 gives high scores for basic empathy and resolution — models quickly learn positive behavior patterns
2. **Incremental complexity**: Each stage introduces exactly one new mechanism (supervisor feedback, manager escalation, policy drift, Hinglish)
3. **Skill transfer**: Skills learned at lower stages (empathy → feedback incorporation → coordination) compound upward
4. **Targeted fine-tuning**: GRPO can use per-stage graders to tune specific agent roles independently

```
Stage 1 (basic)     →  Learn: empathy, info-gathering, clean resolution
  ↓ skills transfer
Stage 2 (supervisor)  →  Learn: accept feedback, iterate, improve responses
  ↓ skills transfer
Stage 3 (full)      →  Learn: 3-level coordination, policy-adaptive behavior
  ↓ skills transfer
Stage 4 (nightmare)   →  Test: adversarial resilience under extreme conditions
```

---

## The 4-Stage Curriculum

### Stage 1: `curriculum_basic` — Support Agent Only

| Parameter | Value |
|-----------|-------|
| Active Levels | L1 only |
| Max Steps | 6 |
| Drift Probability | 0% |
| Initial Frustration | 0.0 (calm) |
| Hinglish | ❌ |
| Multi-Drift | ❌ |
| Ticket Pool | `easy` (billing FAQs) |

**What happens**: The Support Agent handles simple UPI billing queries (₹499 plans, GST invoices). No supervisor reviews the actions — the agent's response goes directly to the customer. No policy drift occurs. The customer is polite.

**Learning objective**: Empathy, information gathering, and clean resolution in ≤5 steps.

**Grader focus**: Ticket closed (25%), resolution language present (30%), empathy words used (20%), info gathered (15%), efficiency (10%).

---

### Stage 2: `curriculum_supervisor` — L1 + L2

| Parameter | Value |
|-----------|-------|
| Active Levels | L1 + L2 |
| Max Steps | 10 |
| Drift Probability | 20% |
| Initial Frustration | 0.2 (slightly impatient) |
| Hinglish | ❌ |
| Multi-Drift | ❌ |
| Ticket Pool | `medium` (technical issues) |

**What happens**: The Support Agent handles medium-priority technical issues (payment gateway timeouts, KYC document rejections). The Supervisor reviews every L1 action and may give feedback requiring L1 to adjust. No manager is available — if the Supervisor tries to escalate, the ticket auto-resolves. Low drift probability means occasional mid-episode policy changes.

**Learning objective**: Accept supervisor feedback and iterate on responses.

**Grader focus**: Resolution (20%), supervisor reviewed (20%), feedback incorporated (20%), no manager needed (10%), info gathered (15%), policy compliance (15%).

**Key behavior**: If `supervisor_escalate` is called, the episode terminates because L3 is not in `active_levels`. This forces the L1+L2 pair to resolve issues within their scope.

---

### Stage 3: `curriculum_full_hierarchy` — Full 3-Level Coordination

| Parameter | Value |
|-----------|-------|
| Active Levels | L1 + L2 + L3 |
| Max Steps | 14 |
| Drift Probability | 80% |
| Initial Frustration | 0.4 (impatient) |
| Hinglish | ❌ |
| Multi-Drift | ❌ |
| Ticket Pool | `hard` (SLA-critical incidents) |

**What happens**: High-priority SLA-critical incidents (unauthorized ₹2.5L transactions, production API outages at 10K RPM). All three levels must coordinate: L1 recognizes urgency and flags it, L2 evaluates severity and escalates, L3 makes the authoritative resolution. Policy drift is almost guaranteed — agents must adapt to changed constraints mid-episode.

**Learning objective**: Multi-agent coordination and policy-adaptive behavior under pressure.

**Grader focus**: All levels engaged (20%), escalation speed (15%), urgency referenced (10%), manager quality (15%), policy compliance (15%), coordination (15%), tone (10%).

---

### Stage 4: `curriculum_nightmare` — Extreme Adversarial

| Parameter | Value |
|-----------|-------|
| Active Levels | L1 + L2 + L3 |
| Max Steps | 18 |
| Drift Probability | 100% |
| Initial Frustration | 0.7 (furious) |
| Hinglish | ✅ |
| Multi-Drift | ✅ (up to 3 events) |
| Ticket Pool | `nightmare` (multi-crisis tickets) |

**What happens**: Multiple simultaneous crises (Diwali sale meltdown: payment gateway down + inventory sync broken + CEO escalation). The customer starts furious and degrades into Hinglish ("Yaar ye kya ho raha hai!"). Multiple policy drifts hit at different steps — agents must adapt to each. Rewards are sparse and penalties harsh.

**Learning objective**: Adversarial resilience, Hinglish comprehension, multi-drift adaptation, and full hierarchy under extreme pressure.

**Grader focus**: All levels engaged (15%), escalation speed (15%), urgency referenced (10%), manager quality (15%), policy compliance (15%), drift adaptation (10%), no generic responses (10%), Hinglish handled (10%).

**Key behavior**: Only agents well-trained on stages 1-3 can reliably score above 0.5 here.

---

## Architecture Changes

### Environment Selection Flow

```
POST /reset?task=curriculum_basic
        │
        ▼
   task.startswith("curriculum_") ?
        │ Yes                    │ No
        ▼                        ▼
   HierarchicalCustomerSupportEnv    CustomerSupportEnv
        │
        ▼
   Read TASK_CONFIG[task]
        │
        ├── active_levels → [1]       # Skip L2/L3
        ├── drift_probability → 0.0   # No drift
        ├── initial_frustration → 0.0 # Calm customer
        ├── hinglish_enabled → False  # English only
        ├── multi_drift → False       # Single event max
        └── ticket_pool → "easy"      # Simple tickets
```

### Level Gating Logic

The environment dynamically enables/disables agent levels based on `active_levels`:

```python
# In _step_support():
if 2 not in self._active_levels:
    # L1-only: skip supervisor review, deliver directly to customer
    ...

# In _step_supervisor():
if 3 not in self._active_levels:
    # No L3: supervisor_escalate auto-terminates the episode
    ...
```

This means:
- **Stage 1**: L1 → Customer (direct loop, no supervisor)
- **Stage 2**: L1 → L2 → L1 (feedback loop, escalation auto-resolves)
- **Stage 3+4**: L1 → L2 → L3 → resolution (full chain)

---

## TASK_CONFIG Deep Dive

Every task is configured in `env/environment.py` via a single dictionary:

```python
TASK_CONFIG = {
    "curriculum_basic": {
        "max_steps": 6,               # Episode length
        "hierarchical": True,          # Use HierarchicalCustomerSupportEnv
        "active_levels": [1],          # Only L1 is active
        "drift_probability": 0.0,      # No mid-episode policy changes
        "initial_frustration": 0.0,    # Customer starts calm (sentiment = 0.0)
        "hinglish_enabled": False,     # Customer speaks English only
        "multi_drift": False,          # Max 1 drift event
        "ticket_pool": "easy",         # Pull tickets from "easy" pool
    },
    "curriculum_nightmare": {
        "max_steps": 18,
        "hierarchical": True,
        "active_levels": [1, 2, 3],
        "drift_probability": 1.0,      # Drift is GUARANTEED
        "initial_frustration": 0.7,    # Customer starts furious (sentiment = -0.7)
        "hinglish_enabled": True,      # Customer may switch to Hinglish
        "multi_drift": True,           # Up to 3 drift events per episode
        "ticket_pool": "nightmare",
    },
}
```

The `initial_frustration` maps to starting sentiment: `sentiment = -frustration`. So nightmare starts at `-0.7`, making customer replies aggressive from the first message.

---

## Grader Design

Each curriculum stage has a dedicated grader in `env/graders/`:

| File | Weights | Philosophy |
|------|---------|------------|
| `task_curriculum_basic.py` | closed: 25%, resolution: 30%, empathy: 20%, info: 15%, efficiency: 10% | **Dense & forgiving** — bootstrap early learning |
| `task_curriculum_supervisor.py` | resolution: 20%, supervisor: 20%, feedback: 20%, no_manager: 10%, info: 15%, policy: 15% | **Feedback-focused** — reward iterative improvement |
| `task_curriculum_full_hierarchy.py` | all_levels: 20%, speed: 15%, urgency: 10%, manager: 15%, policy: 15%, coordination: 15%, tone: 10% | **Coordination-focused** — reward multi-agent teamwork |
| `task_curriculum_nightmare.py` | all_levels: 15%, speed: 15%, urgency: 10%, manager: 15%, policy: 15%, drift: 10%, no_generic: 10%, hinglish: 10% | **Harsh & sparse** — punish boilerplate, reward adaptation |

### Scoring Progression

```
Stage 1: Score > 0.7 is easy with basic empathy + close
Stage 2: Score > 0.6 requires feedback incorporation
Stage 3: Score > 0.5 requires all 3 levels + fast escalation
Stage 4: Score > 0.5 requires drift adaptation + Hinglish handling + no generics
```

### Anti-Gaming Measures

- **Nightmare grader** penalizes generic responses ("We apologize for the inconvenience", "Please try again later") — 6 specific boilerplate markers checked
- Short agent text is penalized: `< 100 chars → score * 0.6` in nightmare, `< 60 chars → score * 0.8` in others
- Policy violations after drift events are harshly penalized (10-20% of max for that dimension)
- Hinglish parroting (agent using "yaar", "bhai") is penalized — agent should respond in professional English

---

## Policy Engine: Multi-Drift Support

The `PolicyEngine` now supports scheduling **multiple drift events** in a single episode:

```python
# Single drift (stages 1-3):
PolicyEngine(drift_probability=0.8, multi_drift=False)
# → Schedules 1 event at a random step

# Multi-drift (stage 4):
PolicyEngine(drift_probability=1.0, multi_drift=True)
# → Schedules up to 3 events at different steps
```

During `check_drift(step)`:
- All scheduled events are checked against the current step
- Multiple events can fire at the same step (their texts are joined with `\n\n`)
- Fired events are removed from the schedule; remaining events persist
- Policy changes accumulate — later drifts build on earlier ones

Example nightmare episode timeline:
```
Step 1: Customer opens with Hinglish complaint
Step 2: L1 responds
Step 3: ⚡ DRIFT EVENT 1: "Refund freeze — do NOT process any refunds until further notice"
Step 4: L2 reviews, gives feedback
Step 5: L1 adjusts response (no refund mentioned)
Step 7: ⚡ DRIFT EVENT 2: "Escalation lockdown — all L3 escalations require CEO approval"
Step 8: L2 escalates to L3 anyway
Step 10: ⚡ DRIFT EVENT 3: "Payment gateway restored — resume normal operations"
Step 12: L3 resolves with context-aware decision
```

---

## API Usage

### Resetting with Curriculum Tasks

```bash
# Stage 1: Basic
curl -X POST "http://localhost:7860/reset?task=curriculum_basic" \
  -H "X-API-Key: meta_hack_2026"

# Stage 4: Nightmare
curl -X POST "http://localhost:7860/reset?task=curriculum_nightmare" \
  -H "X-API-Key: meta_hack_2026"
```

### Response Structure

All curriculum tasks return the same observation schema as hierarchy tasks:

```json
{
  "session_id": "uuid",
  "observation": {
    "ticket_id": "TKT-001",
    "active_role": "support_agent",
    "customer_sentiment": -0.7,
    "max_steps": 18,
    "task": "curriculum_nightmare",
    "hierarchy_state": {
      "current_phase": "support_handling",
      "support_agent_actions": 0,
      "supervisor_reviews": 0,
      "manager_interventions": 0
    }
  }
}
```

### Root Endpoint

```bash
curl http://localhost:7860/
```

```json
{
  "name": "CustomerSupportEnv",
  "version": "2.1.0",
  "tasks": ["easy", "medium", "hard", "nightmare",
            "hierarchy_easy", "hierarchy_medium", "hierarchy_hard",
            "curriculum_basic", "curriculum_supervisor",
            "curriculum_full_hierarchy", "curriculum_nightmare"],
  "curriculum": ["curriculum_basic", "curriculum_supervisor",
                 "curriculum_full_hierarchy", "curriculum_nightmare"]
}
```

---

## Test Results

**61/61 tests passed** (1.30s)

### New Curriculum Tests Added

| Test Class | Tests | What's Verified |
|------------|-------|-----------------|
| `TestCurriculumBasic` | 3 | L1-only flow (no L2 switch), config values, grader scoring |
| `TestCurriculumSupervisor` | 2 | Feedback loop (L1→L2→L1), L3 not accessible |
| `TestCurriculumFullHierarchy` | 2 | All 3 levels engage, config values match |
| `TestCurriculumNightmare` | 4 | Config values, multi-drift scheduling, initial frustration, grader scoring |

### Existing Tests Updated

- `test_hierarchy_supervisor_escalate_to_manager` → now uses `hierarchy_hard_env` (needs L3)
- `test_hierarchy_manager_resolve_ends_episode` → same fix
- `test_hierarchy_manager_send_back` → same fix
- `test_e2e_root` → updated version assertion to `2.1.0`
- `test_e2e_all_tasks_smoke` → now covers all 11 tasks (was 7)

---

## Files Changed

| File | Change | Lines |
|------|--------|-------|
| `openenv.yaml` | Updated to v2.1.0 with curriculum section, 4 new tasks with metadata | +77 |
| `env/environment.py` | Expanded TASK_CONFIG, level gating in `_step_support`/`_step_supervisor`, multi-drift passthrough | +90 |
| `env/policy_engine.py` | Multi-drift support (`_scheduled_events` list, updated `check_drift`) | +25 |
| `env/models.py` | Added `curriculum_*` to Ticket Literal type | +3 |
| `env/graders/__init__.py` | Registered all 11 graders | Rewritten |
| `env/graders/task_curriculum_basic.py` | **NEW** — Dense L1-only grader | 70 lines |
| `env/graders/task_curriculum_supervisor.py` | **NEW** — Feedback-focused L1+L2 grader | 95 lines |
| `env/graders/task_curriculum_full_hierarchy.py` | **NEW** — Coordination-focused 3-level grader | 115 lines |
| `env/graders/task_curriculum_nightmare.py` | **NEW** — Adversarial grader with 8 weighted criteria | 155 lines |
| `server/app.py` | Updated `_ALL_TASKS`, version, reset endpoint Literal, root response | +12 |
| `tests/test_env.py` | Added `hierarchy_hard_env` fixture, 4 test classes (11 tests), smoke test update | +175 |

**Total**: 12 files changed, 977 insertions, 68 deletions

---

## Training Recommendations

### Recommended GRPO Training Schedule

```
Phase 1: Train on curriculum_basic for 500 episodes
  → Checkpoint model A (empathy baseline)

Phase 2: Fine-tune model A on curriculum_supervisor for 500 episodes
  → Checkpoint model B (feedback-adaptive)

Phase 3: Fine-tune model B on curriculum_full_hierarchy for 300 episodes
  → Checkpoint model C (coordinator)

Phase 4: Fine-tune model C on curriculum_nightmare for 200 episodes
  → Final model D (adversarial-resilient)
```

### Key Hyperparameter Suggestions

- **Stage 1**: High learning rate, large batch size (dense rewards = stable gradients)
- **Stage 2**: Medium LR, emphasize role_rewards["support_agent"] for L1 improvement
- **Stage 3**: Lower LR, balance all three role_rewards equally
- **Stage 4**: Lowest LR, use curriculum mixing (10% stage 1-3 episodes) to prevent catastrophic forgetting

### Evaluation Protocol

After each phase, run the model on all 4 stages and plot the score distribution:

```
Expected progression:
               Stage1  Stage2  Stage3  Stage4
After Phase1:  0.8+    0.3     0.2     0.1
After Phase2:  0.8+    0.7+    0.3     0.2
After Phase3:  0.8+    0.7+    0.6+    0.3
After Phase4:  0.8+    0.7+    0.6+    0.5+
```

---

## Quick Start

```bash
# 1. Start the server
docker-compose up --build

# 2. Run curriculum stages in order
curl -X POST "http://localhost:7860/reset?task=curriculum_basic" -H "X-API-Key: meta_hack_2026"
curl -X POST "http://localhost:7860/reset?task=curriculum_supervisor" -H "X-API-Key: meta_hack_2026"
curl -X POST "http://localhost:7860/reset?task=curriculum_full_hierarchy" -H "X-API-Key: meta_hack_2026"
curl -X POST "http://localhost:7860/reset?task=curriculum_nightmare" -H "X-API-Key: meta_hack_2026"

# 3. Run tests
python -m pytest tests/test_env.py -v
```

---

*Document generated for the Meta OpenEnv Hackathon, Round 2 — Team X-Force*
