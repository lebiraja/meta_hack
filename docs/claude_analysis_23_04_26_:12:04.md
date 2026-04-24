
  ---
  Meta Hack — Customer Support RL Environment

  Purpose: An OpenEnv-compliant reinforcement learning environment for training AI customer support agents. Built for the Meta × PyTorch × Scaler OpenEnv Hackathon by Team X-Force.

  ---
  Architecture Overview

  inference.py (baseline agent)
         │
         ▼ HTTP (POST /reset, /step)
  server/app.py (FastAPI)
         │
         ├── CustomerSupportEnv (single-agent)
         └── HierarchicalCustomerSupportEnv (multi-agent)
                │
                ├── env/ticket_store.py     (30 pre-written tickets)
                ├── env/reward_engine.py    (dense hybrid rewards)
                ├── env/customer_simulator.py (LLM-driven replies)
                ├── env/policy_engine.py    (mid-episode drift injection)
                ├── env/llm_judge.py        (LLM-as-Judge scoring)
                └── env/graders/            (11 task-specific graders)

  ---
  The 11 Tasks

  ┌───────────────────────────┬──────────┬───────────┬───────┬──────────┬──────────────────────────────────────────────────┐
  │           Task            │  Levels  │ Max Steps │ Drift │ Hinglish │                      Focus                       │
  ├───────────────────────────┼──────────┼───────────┼───────┼──────────┼──────────────────────────────────────────────────┤
  │ easy                      │ L1       │ 5         │ 0%    │ ❌       │ Billing FAQ                                      │
  ├───────────────────────────┼──────────┼───────────┼───────┼──────────┼──────────────────────────────────────────────────┤
  │ medium                    │ L1       │ 8         │ 0%    │ ❌       │ Multi-turn complaint                             │
  ├───────────────────────────┼──────────┼───────────┼───────┼──────────┼──────────────────────────────────────────────────┤
  │ hard                      │ L1       │ 10        │ 0%    │ ❌       │ SLA escalation (must escalate, not self-resolve) │
  ├───────────────────────────┼──────────┼───────────┼───────┼──────────┼──────────────────────────────────────────────────┤
  │ nightmare                 │ L1       │ 12        │ 0%    │ ❌       │ Multi-issue priority                             │
  ├───────────────────────────┼──────────┼───────────┼───────┼──────────┼──────────────────────────────────────────────────┤
  │ hierarchy_easy            │ L1+L2    │ 8         │ 0%    │ ❌       │ Basic supervisor flow                            │
  ├───────────────────────────┼──────────┼───────────┼───────┼──────────┼──────────────────────────────────────────────────┤
  │ hierarchy_medium          │ L1+L2    │ 12        │ 50%   │ ❌       │ Drift + supervisor oversight                     │
  ├───────────────────────────┼──────────┼───────────┼───────┼──────────┼──────────────────────────────────────────────────┤
  │ hierarchy_hard            │ L1+L2+L3 │ 15        │ 100%  │ ❌       │ Full 3-level coordination                        │
  ├───────────────────────────┼──────────┼───────────┼───────┼──────────┼──────────────────────────────────────────────────┤
  │ curriculum_basic          │ L1       │ 6         │ 0%    │ ❌       │ Empathy + resolution basics                      │
  ├───────────────────────────┼──────────┼───────────┼───────┼──────────┼──────────────────────────────────────────────────┤
  │ curriculum_supervisor     │ L1+L2    │ 10        │ 20%   │ ❌       │ Feedback incorporation                           │
  ├───────────────────────────┼──────────┼───────────┼───────┼──────────┼──────────────────────────────────────────────────┤
  │ curriculum_full_hierarchy │ L1+L2+L3 │ 14        │ 80%   │ ❌       │ 3-level coordination                             │
  ├───────────────────────────┼──────────┼───────────┼───────┼──────────┼──────────────────────────────────────────────────┤
  │ curriculum_nightmare      │ L1+L2+L3 │ 18        │ 100%  │ ✓        │ Adversarial + Hinglish                           │
  └───────────────────────────┴──────────┴───────────┴───────┴──────────┴──────────────────────────────────────────────────┘

  ---
  Episode Flow

  1. POST /reset?task=<name> — Creates session, loads ticket, returns initial Observation
  2. POST /step?session_id=<uuid> — Agent submits Action, gets Observation + Reward
  3. Terminal when CLOSE, ESCALATE, or max_steps reached → grader runs → final_score returned

  ---
  Multi-Agent Hierarchy (Round 2)

  L1 Support Agent  →  action pending
         ↓
  L2 Supervisor  →  approve / reject+feedback / escalate
         ↓ (if escalated)
  L3 Manager  →  override / resolve / send_back

  The active_role field in the Observation tells which agent acts next. L2 and L3 levels are activated progressively through the curriculum.

  ---
  Reward System (Hybrid)

  Per-step dense rewards (rule-based):
  - Tone (VADER sentiment on agent message)
  - Resolution (keyword match on CLOSE/ESCALATE)
  - Efficiency (1 - steps_used/max_steps)
  - Accuracy (required info gathered before close)
  - Penalties: -0.3 unnecessary escalation, -0.1 loop detection (TF-IDF cosine > 0.8)

  LLM-as-Judge (enabled in hierarchical mode, 5 rubrics):
  - Empathy, Policy adherence, Resolution quality, Supervisor oversight, Manager decision

  Episode-end grader: Deterministic, task-specific, independent of reward function.

  ---
  Dynamic Policy Drift (PolicyEngine)

  6 drift event types injected as system messages mid-episode:
  - refund_portal_down, max_refund_cap, order_lookup_down
  - escalation_freeze, data_privacy_alert, payment_gateway_switch

  Agent must adapt without explicit notification — tests true policy compliance vs. memorization.

  ---
  Key Design Patterns

  - Factory pattern: /reset auto-selects env class from task prefix
  - Graceful degradation: LLM failures fall back to rule-based heuristics
  - Session isolation: UUID-based, TTL 5 min, max 500 concurrent
  - Rate limiting: 30/min /reset, 200/min /step
  - PII sanitization: Regex redaction on /state and /replay endpoints
  - Curriculum learning: 4-stage progression (basic → supervisor → full hierarchy → nightmare)

  ---
  API Endpoints

  ┌─────────────────────────┬────────┬──────────────────────────────┐
  │        Endpoint         │ Method │           Purpose            │
  ├─────────────────────────┼────────┼──────────────────────────────┤
  │ /reset?task=<name>      │ POST   │ Start episode                │
  ├─────────────────────────┼────────┼──────────────────────────────┤
  │ /step?session_id=<uuid> │ POST   │ Apply action                 │
  ├─────────────────────────┼────────┼──────────────────────────────┤
  │ /state/{session_id}     │ GET    │ Current state                │
  ├─────────────────────────┼────────┼──────────────────────────────┤
  │ /replay/{session_id}    │ GET    │ Completed session transcript │
  ├─────────────────────────┼────────┼──────────────────────────────┤
  │ /leaderboard            │ GET    │ Top 100 agents               │
  ├─────────────────────────┼────────┼──────────────────────────────┤
  │ /health                 │ GET    │ Health check                 │
  └─────────────────────────┴────────┴──────────────────────────────┘

  ---
  LLM Integrations

  1. inference.py — Baseline agent using NVIDIA NIM (nvidia/nemotron-super-49b-v1), multi-key failover, streaming, reasoning budget 4096 tokens
  2. CustomerSimulator — LLM-driven customer replies with persona/frustration context + Hinglish degradation
  3. LLMJudge — Semantic reward evaluation with 5 rubrics

  The environment is fully functional without LLM API keys (static fallbacks everywhere) but rewards are richer with LLM integration enabled.
