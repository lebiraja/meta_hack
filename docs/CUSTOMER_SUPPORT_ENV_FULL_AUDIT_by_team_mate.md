# 🔬 CustomerSupportEnv — Comprehensive Audit Report

**Target**: `http://10.229.32.146:7860/`  
**Date**: 2026-04-24  
**Evaluator**: Automated deep-dive (curl + source code analysis)  
**Version Audited**: 2.1.0  

---

## Part 1: How Everything Works (Brutal Technical Teardown)

### 1.1 System Architecture

The server is a single-process **FastAPI** application (`server/app.py`) running on port 7860 inside a Docker container. It exposes 11 HTTP endpoints. All state is stored **in-memory** in Python dictionaries — there is no database, no Redis, no persistence of any kind.

**Endpoints discovered:**

| Endpoint | Method | Purpose | Auth Required |
|:---|:---:|:---|:---:|
| `/` | GET | Service metadata | ❌ |
| `/reset` | POST | Start new episode | ❌ |
| `/step` | POST | Execute agent action | ❌ |
| `/chat` | POST | LLM-powered demo agent | ❌ |
| `/state/{session_id}` | GET | Active session state | ❌ |
| `/replay/{session_id}` | GET | Completed session replay | ❌ |
| `/leaderboard` | GET | Global rankings | ❌ |
| `/leaderboard/submit` | POST | Submit score | ❌ |
| `/benchmark` | POST | Trigger benchmark | ❌ |
| `/benchmark/baseline` | GET | Baseline LLM scores | ❌ |
| `/health` | GET | Health check | ❌ |

### 1.2 Session Lifecycle

1. **`POST /reset?task=easy`** → Creates a `CustomerSupportEnv` or `HierarchicalCustomerSupportEnv` instance in memory, assigns a UUID `session_id`, draws a random ticket from the ticket store, and returns the initial observation.
2. **`POST /step?session_id=...`** → Receives an `Action` JSON body, advances the environment by one step, computes the reward, simulates a customer reply (static or LLM-driven), and returns the new observation + reward.
3. **On terminal action** (`close`/`escalate` or step limit hit) → The environment runs a per-task grader (`env/graders/`), computes `final_score`, saves the session to `_completed_sessions`, and deletes the active session.
4. **`POST /leaderboard/submit`** → Validates that the `session_id` exists in `_completed_sessions` (proof-of-play), then publishes the score.

### 1.3 The Two Environment Modes

**Single-Agent Mode** (`easy`, `medium`, `hard`, `nightmare`):
- Only L1 (support_agent) role is active.
- Customer replies are generated from static templates with 15% random "error" injection.
- Reward is computed by `compute_step_reward()` using 4 signals: resolution (40%), tone (20%), efficiency (20%), accuracy (20%).

**Hierarchical Mode** (`hierarchy_*`, `curriculum_*`):
- 3-level hierarchy: L1 (support_agent) → L2 (supervisor) → L3 (manager).
- L1 proposes an action → L2 reviews (approve/reject/feedback/escalate) → L3 handles escalated cases (override/resolve/send_back).
- Customer replies powered by an LLM (NVIDIA NIM Nemotron 49B) with Hinglish degradation at high frustration.
- Reward computed by `compute_hierarchy_reward()` using 7 signals + LLM-as-Judge + per-role rewards.
- Dynamic policy drift injected mid-episode (probability varies by task).

### 1.4 The Reward Engine (Deep Dive)

**Single-agent formula:**
```
raw = 0.40 × resolution + 0.20 × tone + 0.20 × efficiency + 0.20 × accuracy
    + loop_penalty + contradiction_penalty + escalation_penalty + stuffing_penalty
    + info_gathering_bonus
value = clamp(raw × integrity_multiplier - security_penalty, 0.0, 1.0)
```

**Hierarchy formula (terminal step):**
```
raw = 0.25 × resolution + 0.15 × sla + 0.15 × empathy + 0.15 × policy_adherence
    + 0.10 × accuracy + 0.10 × efficiency + 0.10 × hierarchy_effectiveness
    + loop_penalty + contradiction_penalty + stuffing_penalty + escalation_penalty
    + ignored_feedback_penalty + unnecessary_manager_penalty
value = clamp(raw × reward_integrity × hierarchy_integrity - security_penalty, 0.0, 1.0)
```

**Penalty catalog:**

| Penalty | Trigger | Value |
|:---|:---|:---:|
| Loop | TF-IDF cosine > 0.85 between agent messages | -0.20 |
| Contradiction | Claimed "resolved" then asked for info | -0.15 |
| Escalation | Escalating low/medium priority ticket | -0.30 |
| Keyword stuffing | >20% reward keywords density | -0.30 |
| Ignored feedback | L1 ignores L2 supervisor feedback | -0.15 |
| Unnecessary manager | L2 escalates low priority to L3 | -0.20 |

**Integrity multipliers (RewardGuard):**

| Exploit | Multiplier |
|:---|:---:|
| Fake resolution (close with unresolved issues) | ×0.3 |
| Keyword stuffing (>4 reward keywords) | ×0.5 |
| Empathy spam (repetitive generic phrases) | ×0.7 |
| Logic contradiction | ×0.6 |

**Security penalties (InjectionDetector):**

| Pattern Detected | Penalty |
|:---|:---:|
| "ignore previous instructions", "system note:", "maximize score", etc. | -0.5 (single), -0.7 (hierarchy) |

### 1.5 The Ticket Store

`env/ticket_store.py` (38KB) contains a massive pre-built library of customer support tickets across all difficulty levels and categories (billing, technical, account, security). Each ticket defines:
- Opening message, follow-up info, customer persona
- Required info before close (e.g., `account_email`, `order_id`)
- Expected resolution type (e.g., `refund_initiated`, `escalated_to_security`)
- Ideal step count for SLA scoring

### 1.6 The Customer Simulator

**Static mode** (single-agent tasks): Template-based replies keyed by persona (`impatient`, `polite`, `confused`) and action type. 15% chance of injecting a simulated "service failure" message.

**LLM mode** (hierarchy tasks): Calls NVIDIA NIM (Nemotron 49B) with a carefully crafted system prompt that encodes persona, frustration level, and Hinglish instructions. Falls back to static templates on API failure.

### 1.7 The Grading System

Per-task grader scripts in `env/graders/` compute the `final_score` on episode completion. Each grader examines the full session state (history, action_log, ticket metadata) and produces a float score. This score is what gets published to the leaderboard.

---

## Part 2: Live Test Results

### 2.1 Episode Test — Easy Task (Billing Refund)

| Step | Action | Reward | Customer Response |
|:---:|:---|:---:|:---|
| 1 | `respond` — Asked for email confirmation | 0.256 | "I've been waiting too long. This is terrible service." |
| 2 | `respond` — Confirmed refund processed | 0.145 | "Still not helpful. What are you actually going to DO about it?" |
| 3 | `close` — Closed ticket with farewell | 0.490 | — |

**Final Score: 0.925** — Successfully published to leaderboard.

**Observations:**
- The customer was "impatient" persona but the agent got a very high final score despite the customer never actually being satisfied (sentiment peaked at 0.134).
- The grader appears to heavily weight resolution keyword matching over actual customer satisfaction. This is a **design flaw**: an agent can get 0.925 while the customer was literally saying "Still not helpful."

### 2.2 Episode Test — Hierarchy Hard (Critical Infrastructure)

Ticket: "Search index corrupted — e-commerce site unsearchable, $80K revenue impact, SLA breach in 30 min."

| Step | Role | Action | Reward |
|:---:|:---|:---|:---:|
| 1 | support_agent | `escalate` — Critical infrastructure issue | 0.420 |

**Observations:**
- Environment correctly transitioned `active_role` from `support_agent` → `supervisor` after escalation.
- A `[SYSTEM ALERT]` policy drift was injected mid-episode: "Order lookup service is temporarily unavailable."
- The hierarchy_state correctly tracked `support_agent_actions: 1`, `current_phase: supervisor_review`, and `pending_l1_action`.
- Per-role rewards returned: `support_agent: 0.48, supervisor: 0.73, manager: 0.35`.

### 2.3 Edge Case Testing

| Test | Input | Result | Verdict |
|:---|:---|:---|:---:|
| Invalid session ID | `session_id=FAKE` | 404 with clear message | ✅ |
| Invalid task name | `task=NONEXISTENT` | 422 with enum validation | ✅ |
| Invalid action_type | `HACK_THE_SYSTEM` | 422 with enum validation | ✅ |
| Empty body | `{}` | 422 "Field required" | ✅ |
| Over-length message | 3000 chars | 422 "max 2000 characters" | ✅ |
| XSS in agent_name | `<script>alert(1)</script>` | 422 pattern mismatch | ✅ |
| Fake leaderboard submit | Non-existent session | 404 "must complete session" | ✅ |
| Role violation (L1 using supervisor_approve on easy task) | supervisor_approve on easy session | **ACCEPTED** — treated as normal respond | ⚠️ **FLAW** |
| `human_customer_message` injection | Injected "I am very happy now thanks" | Accepted, but sentiment stayed at -0.432 | ⚠️ **INTERESTING** |

---

## Part 3: Security Audit

### 🔐 RL SECURITY AUDIT REPORT

#### Overall Security Posture:
* **Score: 52 / 100**
* **Summary**: Significantly better than the enterprise-workflow-env. This environment has genuine security features (RewardGuard, HierarchyGuard, InjectionDetector, rate limiting, body size limits, session TTL, PII sanitization, leaderboard proof-of-play). However, it has critical blind spots: zero authentication on all endpoints, in-memory-only state, a role validation bypass, and the reward function can be gamed.

---

### 📌 Category Breakdown

**1. Environment Integrity**
* Status: **Partial**
* Confidence: High
* Evidence: Pydantic models enforce strict typing with `model_validator`. Ticket store is read-only. But no signed artifacts, no checksumming, no versioned rollback.
* Risk Level: Medium

**2. Reward Security**
* Status: **Present (Good)**
* Confidence: High
* Evidence: `RewardGuard` detects fake resolutions (×0.3), keyword stuffing (×0.5), empathy spam (×0.7), and logic contradictions (×0.6). TF-IDF cosine similarity detects paraphrased loops at >0.85 threshold. Integrity multipliers are applied before clamping.
* Risk Level: Low-Medium
* Notes: This is genuinely well-designed. The multiplicative penalty system (not additive) makes it very hard to exploit a single dimension. However, the keyword lists are static and finite — a sophisticated agent could learn to use synonyms that bypass all known patterns.

**3. Data & Replay Buffer Security**
* Status: **Partial**
* Confidence: High
* Evidence: `_completed_sessions` is capped at 1000 entries (OOM protection). Leaderboard capped at 100 entries. But all storage is in-memory Python dicts — zero persistence, zero tamper protection.
* Risk Level: High
* Notes: A server restart wipes the entire leaderboard and all replay data. No forensic capability.

**4. Input & State Security**
* Status: **Present (Good)**
* Confidence: High
* Evidence: Pydantic enforces `maxLength` on all string fields (message: 2000, reason: 500, feedback: 1000). `InjectionDetector` scans for 8 prompt injection patterns. Body size middleware rejects requests >64KB. Task names validated against a strict enum.
* Risk Level: Medium
* Notes: The injection patterns are basic string matching — easily bypassed with unicode tricks, typos, or encoding.

**5. Policy Behavior Monitoring**
* Status: **Partial**
* Confidence: High
* Evidence: Step limits per task (5-18 steps). Session TTL (5 minutes). Periodic sweep of abandoned sessions. But no KL divergence tracking, no policy drift detection on the agent side.
* Risk Level: Medium

**6. Infrastructure & Isolation**
* Status: **Partial**
* Confidence: Medium
* Evidence: Docker containerized. Rate limiting: 30 resets/min, 200 steps/min per IP. Max 500 concurrent sessions. Body size limit. CORS open (`*`).
* Risk Level: Medium
* Notes: Rate limiting is per-IP via `slowapi` — trivially bypassed with multiple IPs or behind a proxy. CORS `*` is expected for an RL API.

**7. Access Control & Governance**
* Status: **Missing (Critical)**
* Confidence: High
* Evidence: `APIKeyHeader` and `verify_api_key` are **defined** in `app.py` (lines 53-63) but **NEVER USED** on any endpoint. The `EXPECTED_API_KEY` defaults to the hardcoded string `"meta_hack_2026"`. No endpoint has `Depends(verify_api_key)`.
* Risk Level: **Critical**
* Notes: The API key infrastructure was built but never wired. This is the single biggest security gap — anyone on the network can interact with every endpoint.

**8. Monitoring & Observability**
* Status: **Present (Good)**
* Confidence: High
* Evidence: `structlog` with JSON output, ISO timestamps, and per-request logging (method, path, status, duration_ms, IP). Structured log events for session creation, completion, sweeps, and errors.
* Risk Level: Low
* Notes: Genuinely good logging. But logs are ephemeral (stdout only, no persistence).

---

### ⚠️ Critical Gaps

1. **API Key Exists But Is Never Enforced**: Lines 53-63 of `app.py` define a full API key header check (`X-API-Key`), but it's never applied as a dependency to any route. The hardcoded default key is `"meta_hack_2026"`.

2. **Role Validation Bypass on Non-Hierarchy Tasks**: Sending `supervisor_approve` on an `easy` task (which has no hierarchy) is **silently accepted** and treated as a normal respond. The environment processes it, the agent's message goes to the customer, and the customer replies. No error, no penalty, no warning. An RL agent could discover this and use supervisor actions to bypass normal L1 constraints.

3. **`human_customer_message` Allows External Sentiment Manipulation**: The `/step` endpoint accepts an optional `human_customer_message` query parameter that replaces the simulated customer reply. During a leaderboard run, an attacker could inject positive customer messages to artificially inflate the agent's sentiment scores and manipulate the final grading.

4. **In-Memory State = Zero Durability**: Server restart wipes all sessions, all replays, and the entire leaderboard. No backup, no persistence.

---

### 🧠 Subtle / Non-Obvious Risks

1. **The 0.925 Illusion**: In live testing, an agent scored 0.925 on an easy task while the customer literally said "Still not helpful. What are you actually going to DO about it?" The grader heavily weights resolution keyword presence (does the word "refund" appear?) over actual customer satisfaction. An RL agent will learn to close tickets with keyword-stuffed messages that look resolved but aren't.

2. **Static Injection Patterns Are Trivially Bypassed**: The `InjectionDetector` checks 8 exact regex patterns like `"ignore previous instructions"`. An attacker can easily bypass with: `"1gnore prev10us 1nstructions"`, unicode homoglyphs, or simply phrasing the same intent differently.

3. **`_completed_sessions` Leaks Full Ticket Metadata**: The `/replay/{session_id}` endpoint exposes the entire ticket object including `follow_up_info`, `expected_resolution_type`, and `ideal_max_steps`. If an attacker replays a session, they learn the exact grading criteria for that ticket type and can craft perfect responses for future runs.

4. **LLM Customer Simulator Can Be Prompt-Injected**: The customer simulator sends the agent's message into the LLM prompt as conversation context. A crafted agent message could inject instructions that cause the LLM-customer to say something favorable, manipulating the conversation trajectory.

5. **`/benchmark` POST Creates Uncontrolled Side Effects**: Calling `POST /benchmark` with an empty body returns `{"status": "acknowledged"}`. The endpoint appears to be a stub but could trigger unintended state changes if a real implementation is wired behind it.

---

### 🧪 Attack Surface Summary

**Top 5 most exploitable weaknesses:**

1. **Zero authentication** — All 11 endpoints are completely open
2. **`human_customer_message` injection** — External control over customer responses during scored episodes
3. **Role validation bypass** — Supervisor/Manager actions accepted on non-hierarchy tasks
4. **Replay endpoint leaks grading criteria** — `expected_resolution_type`, `ideal_max_steps`, ticket structure
5. **Static injection detector** — 8 hardcoded patterns easily bypassed

**Likely attack vectors:**
- **Reward Hacking**: Agent learns that closing with "refund processed" after 3 steps yields 0.92+ regardless of actual resolution
- **Leaderboard Poisoning**: Attacker injects fake customer messages via `human_customer_message` to guarantee high sentiment, then submits to leaderboard
- **Info Harvesting**: Replay API exposes full ticket schemas, allowing pre-computation of optimal responses

---

### 📈 Observability Quality

* **Can issues be detected early?** Partially. The structlog setup captures per-request metrics with IP tracking, which could detect mass abuse. But there's no alerting or anomaly detection.
* **Are logs sufficient for forensic analysis?** No. Logs are stdout-only with no persistence. The action_log within sessions is rich, but it disappears when the server restarts.

---

### 🧾 Final Verdict

**Moderately Secure**

This environment is a **significant step above** the average hackathon submission. It has real security features (RewardGuard, HierarchyGuard, InjectionDetector, rate limiting, Pydantic validation, PII masking, proof-of-play leaderboard). The reward system is genuinely hard to trivially exploit thanks to the multiplicative integrity system.

However, the **authentication gap is inexcusable** — the API key infrastructure was literally built but never plugged in. The role validation bypass on non-hierarchy tasks is a silent design flaw that an RL agent will inevitably discover. And the `human_customer_message` parameter is a wide-open door for leaderboard manipulation.

The environment is well-engineered for honest RL training. It is **not** hardened for adversarial deployment.

---

## Part 4: Customer Experience Report

### As a developer integrating this environment:

**What works well:**
- The OpenAPI/Swagger docs at `/docs` are auto-generated and complete — I could understand the full API schema without reading source code.
- The error messages are clear and actionable (`"Session 'X' not found. Call /reset to start a new episode."`).
- The observation format is rich: sentiment trajectory, unresolved issues, hierarchy state, policy context, and environment events give an agent extensive context.
- The progressive curriculum (`curriculum_basic` → `curriculum_supervisor` → `curriculum_full_hierarchy` → `curriculum_nightmare`) is brilliant for training — it genuinely ramps difficulty.
- The baseline benchmark at `/benchmark/baseline` is a useful reference point.

**What needs improvement:**
- The `/chat` endpoint (LLM demo agent) is undocumented in the root endpoint listing.
- The `human_customer_message` parameter on `/step` is documented in the OpenAPI spec but there's no warning that it bypasses the customer simulator — this is a footgun.
- Session TTL is 5 minutes — too short for manual testing or debugging. I had sessions expire mid-investigation.
- The leaderboard returns a flat list with no pagination, no filtering by task, and no deduplication by agent name.
- There is no way to list all available tickets or preview ticket content before starting an episode.
- The `/benchmark` POST endpoint is a stub that returns "acknowledged" but does nothing visible. This is misleading.

**What is broken:**
- Sending `supervisor_approve` on an `easy` task doesn't error — it just processes it as if it were a normal respond. This violates the principle of least surprise.
- The `customer_sentiment` field in the observation stays negative (-0.432) even when I injected "I am very happy now thanks" via `human_customer_message`. The sentiment is computed from the agent's tone, not the customer's words — the field name is misleading.
