# 🔴 ADVERSARIAL AUDIT REPORT — `customer_support_env`

> **Auditor:** Automated Systems Architect + Security Auditor  
> **Date:** 2026-04-08  
> **Verdict:** ❌ **DEMO-LEVEL / HACKATHON GRADE — NOT production viable**  
> **Risk Class:** HIGH — Silent failures, zero isolation, zero security, zero observability

---

## PHASE 1: SURFACE-LEVEL FAILURE SCAN

### 🔴 CRITICAL

| # | File | Issue | Severity |
|---|------|-------|----------|
| 1 | `inference.py:21-26` | **Global mutable `session_state` dict** — single shared dict for ALL users/requests. One user's session overwrites another's. This is not state management; it is a data collision engine. | **CRITICAL** |
| 2 | `server/app.py:21` | **Global mutable `envs` dict** — same problem. All concurrent users share the same dict keyed by `task_name`, meaning two users running `password_reset` clobber each other. | **CRITICAL** |
| 3 | `inference.py:103` | **`reward` is hardcoded to `1.0`** — ALWAYS. Every step. Every input. The environment literally never scores anything. The entire grading system in `env.py` is dead code from the perspective of `inference.py`. This is not a scoring system; it is a participation trophy dispenser. | **CRITICAL** |
| 4 | `inference.py:104` | **`done` is hardcoded to `False`** — episodes never end. The agent loops forever. There is no termination condition. The `max_steps` from `env.py` is completely ignored. | **CRITICAL** |
| 5 | `inference.py:16` | **`HF_TOKEN` is loaded but never used anywhere.** Dead variable. If the system actually needed authentication, it would fail silently. | **HIGH** |
| 6 | `inference.py:14-15` | **`API_BASE_URL` and `MODEL_NAME` loaded but never used in any API call.** The `get_response` function is pure keyword matching — no LLM is ever called. The env vars are decorative. | **HIGH** |

### 🟠 HIGH

| # | File | Issue | Severity |
|---|------|-------|----------|
| 7 | `server/app.py:42` | Error returns are plain dicts (e.g., `{"error": "Unknown task"}`) with **HTTP 200 status**. Clients cannot distinguish success from failure by status code. Every error looks like success. | **HIGH** |
| 8 | `env.py:82-89` | **Fake tools always succeed.** `check_order_status()`, `process_refund()`, `escalate_to_manager()` never fail, never throw, never simulate error conditions. Agents trained here will be blindsided by real-world tool failures. | **HIGH** |
| 9 | `server/app.py:8` | **`sys.path.insert(0, ...)`** — Runtime `sys.path` manipulation is a fragile hack. It breaks under refactoring, deployment changes, or any non-trivial packaging. | **HIGH** |
| 10 | `Dockerfile:6` | Dockerfile installs `openenv==0.1.13` but `requirements.txt` also lists it. `pyproject.toml` also lists it. Three sources of truth for the same dependency, with potential version drift. | **MEDIUM** |

### 🟡 MEDIUM

| # | File | Issue | Severity |
|---|------|-------|----------|
| 11 | `env.py:21` | Inline Hindi comments (`# AI ka poora response`) mixed with English. This is unprofessional for a shared/open-source codebase. | **LOW** |
| 12 | `env.py:104` | `raw.split(":", 1)[1].strip().split()[0]` — If the action is `use_tool:   ` (with trailing whitespace and no tool name), `.split()[0]` raises `IndexError`. No try/except. | **MEDIUM** |
| 13 | `openenv.yaml:25-26` | Declares `OPENAI_API_KEY: required: true` but nothing in the code uses OpenAI's API. The actual inference server (`inference.py`) uses keyword matching. | **MEDIUM** |
| 14 | `requirements.txt` vs `pyproject.toml` | `requirements.txt` pins `openai==1.40.0` (exact), `pyproject.toml` uses `openai>=1.40.0` (range). Conflicting version strategies. | **MEDIUM** |

---

## PHASE 2: LOGIC & STATE CONSISTENCY

### The Two Servers Problem

There are **two completely independent server implementations** that do not talk to each other:

1. **`inference.py`** — A FastAPI app with keyword-matching `get_response()`, global `session_state`, hardcoded rewards.
2. **`server/app.py`** — A FastAPI app that actually uses `CustomerSupportEnv` from `env.py`.

**Neither references the other.** The `Dockerfile` and `pyproject.toml` point to different entrypoints:
- `Dockerfile` → `inference:app` (uses `inference.py`)
- `pyproject.toml` → `server.app:main` (uses `server/app.py`)

This means:
- **The `env.py` grading logic is never used in Docker deployment.**
- **The `server/app.py` environment logic is never used in Docker deployment.**
- **The entire `env.py` file (290 lines of environment + grader + pydantic models) is dead code in production.**

### State Desync Risks

| Scenario | What Happens |
|----------|-------------|
| User A calls `/reset`, User B calls `/step` | User B operates on User A's freshly reset state (inference.py) |
| Two users run `password_reset` simultaneously | Server/app.py: one user's env gets overwritten in `envs["password_reset"]` |
| `/step` called without `/reset` (inference.py) | Auto-resets silently via `await reset()` — user has no idea their state was wiped |
| `/step` called after episode is done | `inference.py`: never detects done, runs forever. `server/app.py`: `env.step()` raises `RuntimeError` — returned as 500 with no structured error |

### Loop Detection is Trivially Bypassable

`env.py:221`: Loop detection only checks if the **exact same string** is repeated consecutively. Adding a single space or character change defeats it entirely. This is not loop detection; it is string equality comparison pretending to be intelligence.

---

## PHASE 3: API & CONTRACT RELIABILITY

### No Input Validation

| Endpoint | Issue |
|----------|-------|
| `POST /step` (inference.py) | Accepts ANY string. No length limit. No sanitization. A 10MB payload is happily processed. |
| `POST /step` (server/app.py) | `action` defaults to `""` — an empty action is silently accepted and graded. |
| `POST /reset` (server/app.py) | Returns error as `{"error": "..."}` with HTTP 200. Client cannot rely on status codes. |
| `GET /state/{task_name}` | No authentication. Anyone can read any task's state. |

### Schema Fragility

- `inference.py` returns `{"observation": {"reply": ..., "history": ...}}` 
- `server/app.py` returns `{"observation": {"task": ..., "difficulty": ..., "message": ...}}`
- **Completely different schemas for the same endpoint name.** Any client that works with one server will break on the other.

### No API Versioning

No `/v1/` prefix. No version headers. Any schema change is a breaking change with no migration path.

---

## PHASE 4: FAILURE & RESILIENCE TESTING

| Failure Mode | Handling | Verdict |
|-------------|----------|---------|
| Network timeout | None | ❌ No timeout config on uvicorn |
| Malformed JSON body | FastAPI handles it (only good thing) | ⚠️ Default error format |
| Server OOM from history growth | `session_state["history"]` grows unbounded | ❌ Memory leak |
| Concurrent request race | Global dict mutation without locks | ❌ Data corruption |
| Process crash | No state persistence | ❌ All state lost |
| Partial failure mid-step | No transactions, no rollback | ❌ Corrupted state |

### No Retry Strategy
Zero. Anywhere. None.

### No Idempotency
Calling `/step` twice with the same action produces different `step_count` values. No idempotency keys. No deduplication.

### No Rate Limiting
An attacker can call `/step` in a tight loop, growing `session_state["history"]` until memory exhaustion.

---

## PHASE 5: SCALABILITY & CONCURRENCY

### This System Cannot Handle > 1 User

**`inference.py`**: A single global `session_state` dict. Period. Two users = data corruption.

**`server/app.py`**: `envs` dict keyed by `task_name`. Two users on the same task = one overwrites the other.

### Memory Leaks

- `session_state["history"]` in `inference.py` grows without bound. No pruning except showing last 4 in response (but storing all).
- `envs` dict in `server/app.py` grows with each new task reset. Old environments are never cleaned up.
- `self._rewards` list in `CustomerSupportEnv` grows per step. Minor, but still unbounded.

### No Horizontal Scaling

Global in-process state makes this impossible to run behind a load balancer. Sticky sessions won't help because state is per-process, not per-session.

### Bottleneck

The keyword-matching `get_response()` is fast, but if this were ever swapped for actual LLM inference (as the config *pretends* it does), the synchronous call would block the event loop because `get_response` is a sync function called from an async handler.

---

## PHASE 6: SECURITY & ABUSE VECTORS

### 🔴 Injection Vectors

| Vector | Details |
|--------|---------|
| **Log injection** | `inference.py:94` — user input `action.message` is directly interpolated into print statements. An attacker can inject fake log lines: `action.message = '"refund" reward=1.00 done=false error=null\n[STEP] step=999 action="hacked"'` |
| **State pollution** | Any user can overwrite any other user's state by calling `/reset` or `/step` |
| **Denial of Service** | No rate limiting + unbounded history = trivial memory exhaustion |
| **Information disclosure** | `GET /state` exposes full session history including all user messages |

### No Authentication. Zero.

- No API keys
- No JWT tokens
- No session tokens
- No CORS configuration
- No HTTPS enforcement

Any person on the internet can call every endpoint.

### No Input Sanitization

User messages are `.lower()`'d and substring-matched. That's it. No XSS filtering (if history is ever rendered in a frontend). No SQL injection prevention (irrelevant now, but dangerous if a database is added later).

---

## PHASE 7: ARCHITECTURAL WEAKNESS

### Coupling

- `server/app.py` imports directly from `env.py` via `sys.path` hacking
- `inference.py` is a standalone server that duplicate-implements everything `env.py` does, but worse
- Two servers, two schemas, two state models, zero shared contracts

### Modularity: F Grade

```
env.py          → Full RL environment (290 lines) — UNUSED in Docker
inference.py    → Keyword-matching chatbot pretending to be an RL env — USED in Docker
server/app.py   → Proper env wrapper — NOT used in Docker
```

The codebase contradicts itself. `env.py` is a reasonably structured RL environment. `inference.py` throws it all away and replaces it with 5 if-statements.

### Separation of Concerns: Nonexistent

`env.py` contains:
- Data models (Pydantic)
- Business logic (grading)
- Environment simulation
- Tool implementations
- Action parsing

All in one file. No separation. One change risks breaking everything.

### Extensibility

Adding a new task requires:
1. Adding to `TASKS` dict in `env.py`
2. Possibly adding to `openenv.yaml`
3. Adding keyword cases to `get_response()` in `inference.py`
4. **Nothing in `inference.py` reads from `TASKS`** — so the two systems drift further apart

---

## PHASE 8: OBSERVABILITY & DEBUGGING

### Logging: Decorative

```python
print(f'[STEP] step={step_no} action="{action.message}" reward=1.00 done=false error=null')
```

- Reward is hardcoded `1.00` — the log LIES
- `done` is hardcoded `false` — the log LIES
- `error` is hardcoded `null` — the log LIES
- No log levels (INFO/WARN/ERROR)
- No structured logging (JSON)
- No request IDs or correlation IDs
- No timestamps in logs

**If this breaks in production, the logs will actively mislead you.**

### Monitoring: Zero

- No metrics endpoint (`/metrics`)
- No Prometheus integration
- No health check beyond `{"status": "ok"}` which tells you nothing about actual health
- No readiness/liveness probe differentiation

### Traceability: Impossible

- No request IDs
- No distributed tracing headers
- No audit trail
- `episode_id` is generated but never logged

---

## PHASE 9: PERFORMANCE & EFFICIENCY

### Redundant Operations

- `inference.py:85`: If status isn't "ready", it calls `await reset()` — an internal function call that also resets `session_state`. This means every first `/step` call triggers a double state initialization.
- `env.py:225`: Concatenates `raw_action + " " + tool_result` for grading, creating a new string every step for no reason when tool_result is empty.

### Blocking Operations

- `get_response()` is synchronous. Currently fast (keyword matching), but the architecture signals LLM integration. When someone inevitably swaps this for an actual API call, it will block the async event loop.

### Unnecessary History Storage

- `inference.py:101` returns `session_state["history"][-4:]` but stores the entire history forever
- No pagination, no archival, no TTL

---

## PHASE 10: RL / SYSTEM INTENT MISUSE

### The Core Betrayal

`env.py` implements a legitimate RL environment with:
- State transitions
- Reward shaping (keyword matching + politeness + tool usage + efficiency - loop penalty)
- Episode termination conditions
- Multi-task difficulty progression

**`inference.py` throws ALL of it away.** It:
- Returns `reward: 1.0` always (no learning signal)
- Returns `done: False` always (no episode boundary)
- Uses keyword matching instead of the grading system
- Ignores task structure entirely
- Never instantiates `CustomerSupportEnv`

**The RL environment exists. The deployed system doesn't use it.** This is the most fundamental design failure: the system's primary value proposition — adaptive agent training — is completely absent from the production entrypoint.

### Reward Hacking in env.py

Even if `env.py` were used, the reward function is trivially gameable:
- Include "please sorry help reset email order" in every response → instant max keyword + polite score
- Use any tool on first step → tool_score + efficiency_score
- Result: 0.7(1.0) + 0.1 + 0.1 + 0.1 = **1.0 reward** on step 1 with a garbage response

The reward function measures **keyword density**, not **conversational quality**. An agent will learn to keyword-stuff, not to help customers.

---

## PHASE 11: EDGE CASE & CHAOS SIMULATION

| Input | `inference.py` Behavior | `server/app.py` + `env.py` Behavior |
|-------|------------------------|--------------------------------------|
| Empty string `""` | Returns generic "Hello. I can help..." | Accepted, graded, gets 0 keyword score |
| 10MB string | Processed. Memory spike. No limit. | Processed. Graded by scanning entire string. |
| `"use_tool: "` (no tool name) | Returns generic response | **`IndexError` crash** at `env.py:104` |
| `"use_tool: ; rm -rf /"` | Returns generic response | Tool not found, no crash (lucky, not by design) |
| 1000 rapid `/step` calls | History grows to 2000 entries. Memory leak. | Environment terminates after `max_steps` but `envs` dict retains dead env objects |
| `/step` after done (env.py) | N/A (never done) | `RuntimeError` → HTTP 500 |
| Unicode/emoji input `"🔥💀"` | Returns generic response | Graded normally (no keyword match, low score) |
| `null` / missing `message` field | FastAPI 422 (pydantic validation) | FastAPI 422 (pydantic validation) |

---

## PHASE 12: PRODUCTION READINESS VERDICT

### Classification: 🏷️ **DEMO-LEVEL / HACKATHON PROTOTYPE**

This is not pre-production. This is not even a solid prototype. This is a **hackathon submission** that was uploaded to Hugging Face Spaces with temporary functionality bolted on.

---

### Final Questions Answered

#### 1. What will break first in real-world usage?
**Multi-user access.** The moment two people use this simultaneously, their sessions collide, state corrupts, and both get nonsensical responses. This happens immediately, on the very first concurrent request.

#### 2. What will fail silently?
**The reward system.** `inference.py` returns `reward: 1.0` for everything. No error, no warning, no indication. Any downstream training pipeline will receive perfect scores for garbage responses and learn nothing. The failure is invisible and the damage is maximum.

#### 3. What will cause the most damage?
**The disconnect between `env.py` and `inference.py`.** Someone will read `env.py`, believe the grading works, train an agent against `inference.py`, get perfect scores, deploy to production, and discover the agent learned nothing because it was never actually graded.

#### 4. What is the most dangerous hidden flaw?
**The logs lie.** `reward=1.00 done=false error=null` is printed regardless of actual state. When debugging, an engineer will read the logs, conclude everything is working, and never find the real problem. **The observability layer actively obstructs debugging.**

---

## 🧨 NO FILTER CRITIQUE

### Harshest Summary

This codebase is two contradictory systems duct-taped into one repository. `env.py` is a competent-but-fragile RL environment that nobody calls. `inference.py` is a 5-branch if-statement chatbot wearing an RL environment's clothes. The Docker deployment ignores the only file with actual logic. The API returns fake rewards, fake completion signals, and logs that lie. There are zero security controls, zero user isolation, zero monitoring, and zero tests. The system has the architectural coherence of a dorm room built by two roommates who never spoke to each other.

### Most Critical Design Mistake

**Building two separate servers (`inference.py` and `server/app.py`) that don't share any code, any schema, any state model, or any deployment pathway.** The result is a system that simultaneously has too much code (290 lines of unused grading logic) and too little code (5 if-statements as the actual production logic).

### Biggest Misconception

The author believes that having `env.py` with proper Pydantic models, reward shaping, and environment classes means the system "works." **It doesn't.** The production entrypoint (`inference.py`) bypasses all of it. The sophistication of `env.py` is decoration on an unused wall.

### Skill-Level Assessment

**Junior developer (3–12 months experience), likely during a hackathon or course project.**

Evidence:
- Understands Pydantic and FastAPI basics
- Knows RL environment structure conceptually
- Cannot integrate components into a coherent system
- Uses global mutable state without understanding concurrency
- Mixes languages in comments (indicates informal/personal project)
- No tests, no error handling, no authentication
- Copy-paste architecture (two servers with overlapping purpose)
- `sys.path.insert` hack indicates unfamiliarity with Python packaging

---

## SUMMARY TABLE

| Category | Score (0–10) | Notes |
|----------|:---:|-------|
| Correctness | 2 | Two servers, one unused. Rewards always 1.0. |
| Security | 0 | No auth, no input validation, log injection, DoS-vulnerable |
| Scalability | 0 | Global state. Cannot handle >1 user. |
| Observability | 1 | Logs exist but actively lie. No metrics. |
| Architecture | 2 | Two contradictory systems. No shared contracts. |
| Resilience | 1 | No retries, no timeouts, no graceful degradation. |
| RL Validity | 2 | Reward function exists but is unused and gameable. |
| Test Coverage | 0 | Zero tests. |
| Documentation | 4 | README is decent. Only redeeming quality. |
| **OVERALL** | **1.3/10** | **Not deployable. Not trainable. Not production-ready.** |

---

*End of Audit. No appeals accepted.*
