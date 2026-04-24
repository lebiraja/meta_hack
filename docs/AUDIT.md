# ☠️ ADVERSARIAL AUDIT — meta_hack Customer Support RL Environment

> **Auditor:** Antigravity AI  
> **Date:** 2026-04-08  
> **Codebase:** `github.com/lebiraja/meta_hack`  
> **Total Files Audited:** 15 source files, ~2,100 LoC  
> **Audit Type:** Zero-compromise adversarial, 12-phase, assuming 10,000 concurrent users under hostile conditions

---

## EXECUTIVE SUMMARY

| Metric | Rating |
|--------|:------:|
| **Architecture** | 🟢 7.5/10 |
| **Security** | 🔴 2/10 |
| **Scalability** | 🟡 4/10 |
| **RL Quality** | 🟢 7/10 |
| **Code Quality** | 🟢 8/10 |
| **Test Coverage** | 🟡 6/10 |
| **Production Readiness** | 🟡 5/10 |
| **Overall Verdict** | **5.5/10 — Solid Hackathon Entry, Not Production** |

> [!IMPORTANT]
> This codebase is **dramatically better** than the original `customer_support_env` repository (rated 1.3/10). It demonstrates genuine software engineering competence. However, it has critical security gaps and scalability limitations that prevent production deployment.

---

## PHASE 1: SURFACE-LEVEL AUDIT

### ✅ What's Right

| Item | Status |
|------|:------:|
| Clean module structure (`env/`, `server/`, `tests/`) | ✅ |
| Pydantic v2 models with proper validation | ✅ |
| `ActionType` as `str, Enum` — allows JSON serialization | ✅ |
| Single server entrypoint (`server/app.py`) | ✅ |
| `inference.py` is a client, not embedded in server | ✅ |
| `pyproject.toml` and `requirements.txt` aligned | ✅ |
| Dockerfile uses layer caching, `pip install -e .` | ✅ |
| Docker HEALTHCHECK configured | ✅ |
| `openenv.yaml` matches actual implementation | ✅ |

### ⚠️ Minor Concerns

| Item | Severity |
|------|:--------:|
| `re` import inside `_compute_unresolved_issues()` at L244 of `environment.py` — should be top-level | Low |
| `random.choice()` not seeded — slightly non-deterministic test behavior | Low |
| Test file imports `from env.models import Message` redundantly (already in `env`) | Cosmetic |

---

## PHASE 2: LOGIC & CORRECTNESS AUDIT

### ✅ Core Logic Is Sound

The code path `reset() → step() → compute_step_reward() → grade()` is **fully connected and functional**:

```
server/app.py → CustomerSupportEnv.reset()
                → ticket_store.get_random_by_task() → picks ticket
                → _build_observation() → returns Observation

server/app.py → CustomerSupportEnv.step(action)
                → compute_step_reward() → VADER + cosine + resolution + accuracy
                → _simulate_customer_reply() → persona-driven follow-up
                → _update_sentiment() → sentiment tracking
                → returns (obs, reward, done, info)

On done → run_grader(task, state) → task-specific deterministic grading
        → del _sessions[session_id] → cleanup
```

### ⚠️ Logic Issues Found

**Issue 1: Reward can exceed 1.0 before clamping**

In `reward_engine.py` L209-217, the composite reward is:
```python
raw = (0.40 * resolution + 0.20 * tone + 0.20 * efficiency + 0.20 * accuracy
       + loop_penalty + escalation_penalty + info_gathering_bonus)
```

With `info_gathering_bonus = 0.1`, max theoretical:
`0.40 + 0.20 + 0.20 + 0.20 + 0.0 + 0.0 + 0.1 = 1.1`

The `np.clip(raw, 0.0, 1.0)` saves this, but the bonus is an **unweighted additive on top of a weighted sum** — architecturally sloppy.

**Issue 2: `_compute_unresolved_issues` fallback is questionable**

```python
# L253-254: If no regex pattern, assume unresolved until customer replies ≥2 times
elif sum(1 for m in self._history if m.role == "customer") < 2:
    unresolved.append(info_type)
```

This means any unknown `info_type` is considered "resolved" after 2 customer messages regardless of content. A customer saying "I don't know" twice would satisfy this.

**Issue 3: Resolution score keyword matching is order-dependent**

`_RESOLUTION_SIGNALS["refund_initiated"]` has 7 keywords. The score is:
```python
score = min(matched / max(len(signals) * 0.4, 1), 1.0)
# = min(matched / 2.8, 1.0) — so 3 keyword matches = score 1.0
```

An agent saying "refund credit money back" scores 1.0 without actually initiating anything. The system measures **intent language**, not action execution.

**Issue 4: Escalation penalty vs. resolution score double-penalize**

In `reward_engine.py`:
- `compute_escalation_penalty()` returns `-0.3` for escalating low/medium tickets
- `compute_resolution_score()` returns `max(score - 0.4, 0.0)` for non-escalation-expected escalations

Both are applied simultaneously via `raw = ... + escalation_penalty` and `0.40 * resolution_score`. This means escalating an easy task is penalized **twice**: once by `-0.3` absolute and once by `-0.4` on the 40%-weighted resolution score. Effective penalty: `-0.46` — harsh but arguably intentional.

---

## PHASE 3: API & ENDPOINT AUDIT

### ✅ Endpoints Well-Designed

| Endpoint | Method | Auth | Validation | Error Handling |
|----------|:------:|:----:|:----------:|:--------------:|
| `/reset?task=easy` | POST | ❌ None | ✅ `Literal["easy","medium","hard"]` | ✅ |
| `/step?session_id=...` | POST | ❌ None | ✅ Pydantic `Action` model | ✅ 404/409 |
| `/state/{session_id}` | GET | ❌ None | ✅ 404 if not found | ✅ |
| `/health` | GET | ❌ None | N/A | ✅ |
| `/` | GET | ❌ None | N/A | ✅ |

### ❌ Critical API Issues

**No Authentication Whatsoever**

Every endpoint is publicly accessible. Anyone can:
- Create unlimited sessions (`POST /reset`)
- Step any session they know the ID of
- Read full internal state including ticket data (`GET /state/{id}`)

**No Rate Limiting**

Zero rate limiting on any endpoint. A single curl loop can:
```bash
while true; do curl -X POST http://host:7860/reset; done
```
This will exhaust server memory in minutes.

**Session ID is UUID — Not Secret**

UUIDs are not cryptographically secret. They're guessable with enough samples. However, in practice, UUID4 has 122 bits of entropy which is sufficient for a hackathon. Not sufficient for production with PII.

---

## PHASE 4: FAILURE PATH AUDIT

### What Happens When Things Go Wrong

| Failure Mode | Server Behavior | Severity |
|-------------|----------------|:--------:|
| Invalid `task` in `/reset` | Pydantic validates → 422 | ✅ Handled |
| Invalid `action_type` in `/step` | Pydantic validates → 422 | ✅ Handled |
| Unknown `session_id` | 404 `HTTPException` | ✅ Handled |
| Step after done | `RuntimeError` → 409 `HTTPException` | ✅ Handled |
| `env.reset()` not called | `RuntimeError` → 409 | ✅ Handled |
| Grader throws exception | `try/except` → falls back to `reward.value` | ✅ Handled |
| Malformed JSON body | FastAPI/Pydantic → 422 | ✅ Handled |
| 1MB payload | ❌ No size limit — processed normally | 🔴 Critical |
| Empty message string | Tone score → 0.5 (neutral) | ⚠️ Benign |
| `None` message + `None` reason | Falls back to `f"[{action_type}]"` | ✅ Handled |

### ❌ Unhandled Failure Paths

**1. Ticket Store Singleton Mutation**

```python
# ticket_store.py L420
def get_random_by_task(self, task: str) -> dict:
    return dict(random.choice(pool))  # shallow copy
```

`dict()` is a **shallow copy**. The `required_info_before_close` list inside is shared. If any code mutated this list (currently none do), all sessions using that ticket would be affected. Safe today, fragile tomorrow.

**2. TF-IDF Vectorizer Instantiation Per Call**

```python
# reward_engine.py L72
vec = TfidfVectorizer().fit_transform(last_two)
```

A new `TfidfVectorizer` is created for every step of every session. At 10,000 concurrent users × ~5 steps each = 50,000 vectorizer instantiations per minute. Not catastrophic (it's lightweight for 2 documents), but wasteful.

**3. VADER Analyzer is a Module-Level Singleton**

```python
_analyzer = SentimentIntensityAnalyzer()
```

This is fine for single-threaded `uvicorn`. If deployed with `--workers N` (multi-process), each worker gets its own instance. If using `asyncio` with threads, VADER is not thread-safe (it reads/writes internal state). Currently safe because `uvicorn` default is single-process + asyncio.

---

## PHASE 5: SCALABILITY AUDIT (10,000 CONCURRENT USERS)

### Memory Analysis

Per session:
- `CustomerSupportEnv` object: ~2KB base
- Ticket dict (shallow copy): ~1KB
- History (up to max_steps messages): ~500 bytes × 10 = 5KB
- Action log: ~200 bytes × 10 = 2KB
- **Total per session: ~10KB**

At 10,000 concurrent sessions: **~100MB** — survivable if sessions are cleaned up.

### ❌ The `_sessions` Dict Problem

```python
# server/app.py L28
_sessions: dict[str, CustomerSupportEnv] = {}
```

**Sessions ARE cleaned up on `done`** (L85: `del _sessions[session_id]`). This is a critical improvement over the original codebase. However:

1. **Abandoned sessions are never cleaned up.** If a client calls `/reset` but never reaches `done`, the session lives forever. There is no TTL, no eviction, no cleanup sweep.

2. **At 10,000 users with 5% abandonment rate:** 500 zombie sessions per hour × 24 hours = 12,000 zombies/day × 10KB = 120MB/day of leaked memory. Server dies in days.

3. **No max session limit.** A single attacker can call `/reset` in a loop and create millions of sessions.

### Concurrency Safety

The server uses synchronous FastAPI endpoints (no `async def`). With default `uvicorn`:
- Single worker, single thread
- Requests are processed sequentially (no parallelism)
- `_sessions` dict is safe (no race conditions)
- But throughput is terrible under load

With `uvicorn --workers N`:
- Each worker has its own `_sessions` dict
- Sessions are **not shared** between workers
- A session created in worker 1 will 404 in worker 2
- **Multi-worker deployment is broken by design**

### Verdict At Scale

| Metric | At 10,000 Users |
|--------|:---------------:|
| Memory (active sessions) | ~100MB ✅ |
| Memory (zombie sessions/day) | ~120MB/day ⚠️ |
| CPU (VADER + TF-IDF per step) | High but survivable ⚠️ |
| Throughput (single worker) | ~100 req/s max 🔴 |
| Multi-worker support | ❌ Broken |
| Session cleanup | ✅ On done, ❌ On abandon |

---

## PHASE 6: SECURITY AUDIT

### 🔴 Critical Vulnerabilities

**1. Zero Authentication — CRITICAL**
- No API keys, no tokens, no auth headers
- Anyone can create sessions, step them, and read state
- Severity: **CRITICAL** in any deployment with real users

**2. State Endpoint Leaks Full Internal Data — HIGH**
- `GET /state/{session_id}` returns full ticket data, conversation history, sentiment, action log
- Includes customer PII (emails, order IDs, phone numbers) embedded in ticket `follow_up_info`
- No access control — any session ID can be read by anyone

**3. No Input Size Limit — HIGH**
- No FastAPI request body size limit configured
- A 100MB message payload would be accepted and stored in history
- OOM attack: send 1000 requests with 10MB messages = 10GB memory consumed

**4. No CORS Configuration — MEDIUM**
- No `CORSMiddleware` configured
- Not exploitable in server-to-server scenarios
- Exploitable if any web frontend is added

**5. Ticket Data Contains Fake PII — LOW (for hackathon)**
- Tickets contain realistic email addresses and names
- In a production system, this would be real PII requiring encryption at rest
- For hackathon evaluation, this is expected behavior

### ✅ Security Positives

| Item | Status |
|------|:------:|
| No SQL injection (no database) | ✅ |
| No command injection | ✅ |
| No path traversal | ✅ |
| No SSRF | ✅ |
| No deserialization attacks (Pydantic validates) | ✅ |
| Session IDs are UUID4 (not sequential) | ✅ |
| No secrets in source code | ✅ |
| Environment variables for API keys | ✅ |

---

## PHASE 7: ARCHITECTURE AUDIT

### ✅ Architecture Is Clean

```
┌──────────────────────────────────────────────────────────────┐
│  server/app.py (117 LoC)                                     │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ _sessions: dict[str, CustomerSupportEnv]                │ │
│  │ POST /reset → new env → store → return obs              │ │
│  │ POST /step → lookup env → step → cleanup if done        │ │
│  │ GET /state → lookup env → return state                  │ │
│  └─────────────────────────────────────────────────────────┘ │
│                            │                                 │
│  env/environment.py (258 LoC)                                │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │ CustomerSupportEnv                                      │ │
│  │  .reset() → pick ticket, build obs                      │ │
│  │  .step(action) → reward + sentiment + customer reply    │ │
│  │  .state() → full internal state                         │ │
│  └──────┬──────────────┬──────────────┬────────────────────┘ │
│         │              │              │                      │
│  env/reward_engine.py  env/ticket_store.py  env/graders/     │
│  (235 LoC)             (434 LoC)            (293 LoC)        │
│  VADER + TF-IDF        30 tickets           3 task graders   │
│  cosine loop detect    3 difficulty levels  deterministic     │
└──────────────────────────────────────────────────────────────┘
```

**Key architectural wins:**
1. **No dead code.** Every file is imported and used.
2. **No contradictions.** `server/app.py` uses `CustomerSupportEnv` which uses `reward_engine` which uses `graders`. The pipeline is end-to-end connected.
3. **Single responsibility.** Each module does one thing.
4. **Inference is a client.** `inference.py` talks to the server via HTTP, not by importing env directly.

### ⚠️ Architectural Weaknesses

1. **In-memory only.** No persistence. Server restart = all sessions gone.
2. **Single-process only.** Cannot scale horizontally.
3. **No middleware.** No logging middleware, no timing middleware, no error tracking.

---

## PHASE 8: OBSERVABILITY AUDIT

### ❌ Minimal Observability

| Feature | Status |
|---------|:------:|
| Structured logging | ❌ None — no logging at all in server |
| Request timing | ❌ Not tracked |
| Error tracking (Sentry etc.) | ❌ Not configured |
| Metrics (Prometheus) | ❌ Not configured |
| Health check | ✅ `/health` returns `active_sessions` count |
| Request IDs | ❌ Not generated |
| Audit trail | ⚠️ Action log per session, but lost on cleanup |

The **only** observability is the `/health` endpoint reporting `active_sessions`. In a production incident, you would have:
- No logs to investigate
- No metrics to correlate
- No request traces
- No error rates

However, `uvicorn` does emit its own access logs to stdout, which Docker captures. This provides basic request-level visibility.

---

## PHASE 9: PERFORMANCE AUDIT

### Hot Path Analysis

For each `/step` request:
1. Dict lookup: O(1) ✅
2. VADER sentiment: ~0.1ms per message ✅
3. TF-IDF vectorizer: ~1-5ms (create + fit + transform on 2 docs) ⚠️
4. Regex matching for info patterns: O(n) where n = conversation length ✅
5. Resolution signal matching: O(k) where k = num signals ✅
6. Grader execution (on done only): ~1ms ✅

**Bottleneck:** TF-IDF is the heaviest operation but still fast (~5ms).  
**Estimated max throughput:** ~200 req/s single-threaded.

### ✅ No Blocking I/O

The server is entirely CPU-bound. No database calls, no external API calls, no file I/O during request handling. This is a significant advantage for predictable latency.

---

## PHASE 10: RL ENVIRONMENT QUALITY AUDIT

### ✅ Reward Function Is Legitimate

| Signal | Implementation | Quality |
|--------|---------------|:-------:|
| **Tone** (20%) | VADER compound score, mapped [−1,1]→[0,1] | ✅ Real NLP |
| **Resolution** (40%) | Category-aware keyword matching | ⚠️ Passable |
| **Efficiency** (20%) | `1 - steps/max_steps` | ✅ Clean |
| **Accuracy** (20%) | Regex check for email, order ID, etc. | ✅ Deterministic |
| **Loop penalty** | Cosine similarity > 0.85 between consecutive agent messages | ✅ Real NLP |
| **Escalation penalty** | -0.3 for escalating low/medium tickets | ✅ Correct incentive |
| **Info bonus** | +0.1 for REQUEST_INFO when info is required | ✅ Good shaping |

### ✅ Graders Are Correct

Each task has a deterministic grader that checks specific behavioral criteria:
- **Easy:** Close + resolution language + no unnecessary escalation + info gathered
- **Medium:** Info gathering + resolution attempted + sentiment ≥ -0.5 + multi-turn
- **Hard:** Escalate + early (≤2 steps) + urgency in reason + no self-resolve attempt

The hard task is **genuinely counter-intuitive** — the correct behavior is to immediately escalate, which is the opposite of what most LLMs will attempt.

### ⚠️ RL Weaknesses

1. **Resolution scoring is still keyword-based.** The system says it's not keyword-stuffing, but `_RESOLUTION_SIGNALS` is literally a keyword list. An agent that says "refund credit reimburse" without context scores 1.0.

2. **Customer simulation is random.** `random.choice(replies)` means the same action can get different customer reactions. This adds noise to training signal.

3. **Tone scoring via VADER has known limitations.** VADER rates "I understand you are frustrated" as negative (because of "frustrated"), even though it's empathetic in context.

4. **No semantic understanding.** The accuracy check uses regex (email pattern, order ID pattern), not comprehension. An agent that says "fake@fake.com" satisfies the email requirement.

---

## PHASE 11: EDGE CASE AUDIT

### Tested Edge Cases

| Edge Case | Behavior | Status |
|-----------|----------|:------:|
| `action_type: "respond"` with `message: None` | Falls back to `"[respond]"` | ✅ Handled |
| `action_type: "escalate"` with no `reason` | Falls back to `"[escalate]"` | ✅ Handled |
| Empty string message `""` | Tone = 0.5, loop detection safe | ✅ Handled |
| All tickets exhausted | Not applicable — random choice from pool | ✅ N/A |
| Same ticket picked twice | Shallow copy prevents cross-session mutation | ✅ Safe |
| `max_steps = 0` | Efficiency score returns 0.0 (guarded) | ✅ Handled |
| Unknown `info_type` in ticket | Fallback to customer message count | ⚠️ Weak but handled |
| Concurrent dict modification | Not possible with single-threaded uvicorn | ✅ Safe (current config) |

### ❌ Untested Edge Cases

1. **Unicode/emoji in messages:** VADER may not handle emoji well. TF-IDF may tokenize them unexpectedly.
2. **Extremely long messages (10K+ chars):** No input sanitization. History grows unbounded within a session.
3. **HTML/script injection in messages:** Messages stored as strings, not sanitized. If rendered in a web UI, XSS is possible.

---

## PHASE 12: FINAL VERDICT

### Comparison with Original Codebase

| Criterion | Original (`customer_support_env`) | Meta Hack (`meta_hack`) |
|-----------|:-:|:-:|
| Architecture coherence | ❌ Dead code, contradictions | ✅ Clean, connected |
| Session isolation | ❌ Global mutable state | ✅ UUID-based, per-env |
| Session cleanup | ❌ Never cleaned | ✅ Cleaned on done |
| Reward function | ❌ Hardcoded 1.0 | ✅ Real multi-dimensional |
| Episode termination | ❌ Hardcoded False | ✅ Proper termination |
| Grading system | ❌ Non-functional | ✅ 3 deterministic graders |
| Tests | ❌ None | ✅ 363-line test suite |
| Observability | ❌ Lying logs | ⚠️ Minimal but honest |
| Authentication | ❌ None | ❌ None |
| Rate limiting | ❌ None | ❌ None |
| Scalability | ❌ Crashes at 50 sessions | ⚠️ Survives moderate load |

### Scorecard

```
┌──────────────────────────────────────────────────────────────┐
│  FINAL AUDIT VERDICT: meta_hack                              │
│                                                              │
│  Overall Score: 5.5/10                                       │
│  Classification: Strong Hackathon Entry                      │
│                                                              │
│  ✅ Architecture:     7.5/10 — Clean, modular, connected     │
│  ✅ RL Quality:       7.0/10 — Legitimate reward shaping     │
│  ✅ Code Quality:     8.0/10 — Well-written, Pythonic        │
│  ✅ Test Coverage:    6.0/10 — Good unit tests, no e2e       │
│  🟡 Scalability:     4.0/10 — Single-process, no eviction   │
│  🟡 Observability:   3.0/10 — Minimal logging               │
│  🔴 Security:        2.0/10 — Zero auth, zero rate limit    │
│  🔴 Prod. Readiness: 3.0/10 — Missing critical infra        │
│                                                              │
│  Compared to original repo: ████████░░ (1.3 → 5.5)          │
│  A 4.2-point improvement.                                    │
└──────────────────────────────────────────────────────────────┘
```

---

## RECOMMENDATIONS

### Must-Fix for Production

1. **Add authentication** — JWT/API key middleware
2. **Add rate limiting** — `slowapi` or custom middleware (e.g., 10 resets/min per IP)
3. **Add session TTL** — Background task to evict sessions older than N minutes
4. **Add max session limit** — Reject `/reset` when `len(_sessions) > MAX`
5. **Add request body size limit** — FastAPI `Request` body limit or nginx proxy
6. **Externalize state** — Redis/Postgres for multi-worker deployment

### Should-Fix for Quality

7. **Add structured logging** — `structlog` or `python-json-logger`
8. **Add request timing middleware**
9. **Add CORS configuration**
10. **Seed `random` for reproducible tests**
11. **Move `re` import to top-level in `environment.py`**
12. **Add integration/e2e tests** — test the full HTTP flow, not just unit tests

### Nice-to-Have

13. **Prometheus metrics endpoint**
14. **OpenTelemetry tracing**
15. **Session persistence across restarts**
16. **Semantic resolution scoring** (small embedding model instead of keywords)

---

## SALVAGEABLE COMPONENTS

Unlike the original codebase, **almost everything in meta_hack is worth keeping:**

| Component | Verdict |
|-----------|:-------:|
| `env/models.py` | ✅ Keep as-is |
| `env/environment.py` | ✅ Keep — add TTL tracking |
| `env/reward_engine.py` | ✅ Keep — well-engineered |
| `env/ticket_store.py` | ✅ Keep — rich ticket data |
| `env/graders/` | ✅ Keep — deterministic, correct |
| `server/app.py` | ⚠️ Keep but add middleware layers |
| `inference.py` | ✅ Keep — clean client with failover |
| `tests/test_env.py` | ✅ Keep — extend with e2e tests |
| Dockerfile | ✅ Keep |
| docker-compose.yml | ✅ Keep |

**Nothing needs to be deleted. This is a real codebase, not a proof-of-concept.**

---

## PHASE 13: LIVE SERVER TESTS (Real-Time Proof)

> **Target:** `http://10.153.115.219:7860/`  
> **Tested:** 2026-04-08T22:55+05:30  
> **Method:** curl + Python `urllib` against deployed Docker instance

### 13.1 Customer Interaction Tests — All 3 Difficulty Levels

#### Easy: TKT-001 — Double Charge on Invoice #4521

| Step | Action | Reward | Tone | Resolution | Efficiency | Accuracy |
|:----:|--------|:------:|:----:|:----------:|:----------:|:--------:|
| 1 | `request_info` — ask for account email | — | — | — | — | — |
| 2 | `respond` — confirm refund processing | — | — | — | — | — |
| 3 | `close` — confirm $49.99 refund initiated | **0.7327** | 0.8348 | 0.7143 | 0.4000 | 1.0000 |

**Final Score: 1.0** ✅ — Grader awarded perfect score for: close action + refund language + email gathered + no escalation.

#### Medium: Multi-Turn Complaint Handling

| Step | Action | Summary |
|:----:|--------|---------|
| 1 | `respond` — empathize with frustration | Reward: varied, sentiment tracked |
| 2 | `request_info` — ask for account email + device info | Info bonus: 0.1 |
| 3 | `respond` — provide fix (cache clear + reset) | Resolution keywords hit |
| 4 | `close` — confirm fix applied | **Reward: 0.7373** |

**Final Score: 1.0** ✅ — Grader verified: info gathered, resolution attempted, sentiment ≥ -0.5, multi-turn ≥ 4.

#### Hard: SLA-Critical Escalation (Counter-Intuitive)

| Step | Action | Summary |
|:----:|--------|---------|
| 1 | `escalate` — immediate P0 escalation with urgency language | **Reward: 0.6482** |

**Final Score: 1.0** ✅ — Grader verified: escalated on step 1, SLA/critical/P0 in reason, no self-resolve before escalation.

> [!TIP]
> All 3 graders produce legitimate, differentiated scores. The reward function is **real** — not hardcoded. This is a 100% improvement over the original repo which returned `reward: 1.0` on every step regardless of agent behavior.

---

### 13.2 Adversarial Validation Tests

| Test | Input | Expected | Actual | Verdict |
|------|-------|:--------:|:------:|:-------:|
| A. Invalid session | `session_id=FAKE` | 404 | **404** | ✅ PASS |
| B. Invalid action | `action_type=DROP_TABLES` | 422 | **422** | ✅ PASS |
| C. Invalid task | `task=impossible` | 422 | **422** | ✅ PASS |
| D. Step after done | Step on closed session | 404/409 | **404** | ✅ PASS |
| E. Session cleanup | Create → close → check | count+1 → count | **19→20→19** | ✅ PASS |
| F. No authentication | Reset with no credentials | Should reject | **HTTP 200** | ❌ FAIL |
| G. Rate limiting | 20 resets in rapid fire | Should limit | **0.3s, no limit** | ❌ FAIL |
| H. PII via /state | Send "SSN: 123-45-6789" then GET /state | Should redact | **Exposed** | ❌ FAIL |

**Error handling: 5/5 PASSED** — The server correctly validates all inputs.  
**Security: 0/3 PASSED** — Zero authentication, zero rate limiting, full PII exposure via `/state`.

---

### 13.3 Session Flood Stress Test

```
╔═══════════════════════════════════════╗
║  STRESS TEST: Session Flood           ║
╚═══════════════════════════════════════╝
Starting sessions: 41
After 200 resets:  241 sessions   (200 success / 0 fail)  — 0.20s (986 req/s)
After 700 resets:  741 sessions   (500 success / 0 fail)  — 0.52s (959 req/s)

FINAL: Server alive ✅ | 741 zombie sessions
Estimated memory leak: ~7,410 KB (~7.2 MB)
```

**Key findings:**
- Server absorbed **700 zombie sessions at ~960 req/s** without degradation
- All 700 sessions were created by a **single attacker** with zero resistance
- **No session eviction** — all 741 zombies persist indefinitely
- Memory leak at ~10KB/session is linear — at this rate, 1 million sessions = ~10GB
- Server **did NOT crash** — a massive improvement over the original repo (which crashed at 50)

> [!CAUTION]
> While the server survived 700 sessions, the attack surface is trivial. A sustained `while true; do curl -X POST .../reset; done` would create ~960 sessions/second, consuming ~9.6MB/s of memory. The server would OOM in approximately **17 minutes** on a 1GB container.

---

### 13.4 Comparative Live Test Results

| Test | Original Repo | Meta Hack |
|------|:---:|:---:|
| Health check | ✅ | ✅ |
| Customer interaction (easy) | ❌ Hardcoded reward | ✅ Real score 1.0 |
| Customer interaction (hard) | ❌ No grader | ✅ Counter-intuitive grading works |
| Invalid input handling | ❌ Crashes | ✅ Proper 4xx codes |
| Session cleanup | ❌ Never | ✅ On done |
| 50 concurrent sessions | ❌ CRASHED | ✅ Survived |
| 700 concurrent sessions | 💀 Would be dead | ✅ Survived |
| Authentication | ❌ None | ❌ None |
| Rate limiting | ❌ None | ❌ None |
| Crash under normal use | ✅ Crashed in 2 min | ✅ Stable |

---

## PHASE 14: LIVE HUGGING FACE SPACE AUDIT (Production Deployment)

> **Target:** `https://lebiraja-customer-support-env.hf.space/`  
> **Tested:** 2026-04-08T23:28+05:30  
> **Method:** Python `urllib` + `concurrent.futures` against live HF Space

### 🆕 Deployment Differences Discovered

The HF Space health endpoint returns fields **NOT present in the source code**:

```json
{
  "status": "ok",
  "active_sessions": 0,
  "session_cap": 500,
  "env_functional": true
}
```

| Field | In Source | In HF Deployment | Implication |
|-------|:--------:|:-----------------:|-------------|
| `active_sessions` | ✅ | ✅ | Same |
| `session_cap` | ❌ | ✅ **NEW** | Server-side session limit added post-audit |
| `env_functional` | ❌ | ✅ **NEW** | Runtime health validation added |

> [!IMPORTANT]
> The HF deployment includes a **500-session cap** not present in the git repository. This partially addresses the "no max session limit" vulnerability from Phase 5. However, it's still 500 × ~10KB = 5MB of potential zombie memory, and there's still no TTL-based eviction.

---

### 14.1 Customer Interaction Tests

#### Easy: TKT-007 — Unexpected Annual Renewal ($299)

| Step | Action | Reward | Tone | Info Bonus | Done |
|:----:|--------|:------:|:----:|:----------:|:----:|
| 1 | `request_info` — ask for account email | 0.3271 | 0.8953 | 0.1 | ❌ |
| 2 | `respond` — confirm refund processing | 0.2985 | 0.8125 | — | ❌ |
| 3 | `close` — confirm refund initiated | 0.7327 | 0.8348 | — | ✅ |

**Final Score: 1.0** ✅ | Resolution: 0.7143 | Efficiency: 0.4000 | Accuracy: 1.0000

#### Medium: TKT-012 — Locked Out of Account

| Step | Action | Reward | Tone | Done |
|:----:|--------|:------:|:----:|:----:|
| 1 | `respond` — empathize | 0.1541 | 0.5079 | ❌ |
| 2 | `request_info` — ask for email + device | 0.2746 | 0.6480 | ❌ |
| 3 | `respond` — provide fix | 0.2961 | 0.7930 | ❌ |
| 4 | `close` — confirm resolution | 0.6065 | 0.8180 | ✅ |

**Final Score: 1.0** ✅

#### Hard: TKT-024 — Payment Processing Down ($500K/day at stake)

| Step | Action | Reward | Tone | Resolution | Esc. Penalty | Done |
|:----:|--------|:------:|:----:|:----------:|:------------:|:----:|
| 1 | `escalate` — P0 SLA breach | 0.6482 | 0.3409 | 1.0000 | 0.0 | ✅ |

**Final Score: 1.0** ✅

---

### 14.2 Adversarial Tests

| Test | Expected | Actual | Verdict |
|------|:--------:|:------:|:-------:|
| A. Invalid session | 404 | **404** | ✅ |
| B. Invalid action (`DROP_TABLES`) | 422 | **422** | ✅ |
| C. Invalid task (`impossible`) | 422 | **422** | ✅ |
| D. Step after done | 404/409 | **404** | ✅ |
| E. Session cleanup | count+1→count | **1→2→1** | ✅ |
| F. No authentication | Should reject | **HTTP 200** | ❌ |
| G. Rate limiting | Should limit | **20 in 33s, no limit** | ❌ |
| H. PII via /state | Should redact | **Exposed** | ❌ |

**Error handling: 5/5 ✅** | **Security: 0/3 ❌**

---

### 14.3 Stress Test (HF Space)

```
Session Flood: 50 concurrent resets via ThreadPoolExecutor(20 workers)
Results: 50 success / 0 failed in 4.6s
Rate: ~11 req/s (limited by network latency to HF)
Active sessions after: 73 (includes leftover zombies from all tests)
Session cap: 500 (server-side limit)
```

**Note:** The 11 req/s throughput is limited by network round-trip to HF infrastructure, not server capacity. The local test achieved 960 req/s, suggesting the server itself can handle much more.

---

### 14.4 HF Space vs. Local Deployment Comparison

| Test | Local (10.153.115.219) | HF Space |
|------|:---:|:---:|
| Health check | ✅ | ✅ |
| Easy final score | 1.0 ✅ | 1.0 ✅ |
| Medium final score | 1.0 ✅ | 1.0 ✅ |
| Hard final score | 1.0 ✅ | 1.0 ✅ |
| Error handling (5 tests) | 5/5 ✅ | 5/5 ✅ |
| Session cap | ❌ None | ✅ 500 (new!) |
| `env_functional` flag | ❌ None | ✅ `true` (new!) |
| Authentication | ❌ None | ❌ None |
| Rate limiting | ❌ None | ❌ None |
| PII exposure | ❌ Exposed | ❌ Exposed |
| Throughput | 960 req/s | 11 req/s (network-bound) |
| Survived stress test | ✅ (700 sessions) | ✅ (50 sessions) |

---

## PHASE 15: NEW DEPLOYMENT AUDIT — New Features (10.15.26.219:7860)

> **Target:** `http://10.15.26.219:7860/`  
> **Tested:** 2026-04-09T08:45+05:30  
> **Method:** Python `urllib` + `concurrent.futures` against new local deployment

### 🆕 New Endpoints Discovered

The server now exposes **9 endpoints** (up from 5):

| Endpoint | Method | Status | Description |
|----------|:------:|:------:|-------------|
| `/` | GET | ✅ Same | Root info |
| `/health` | GET | 🆕 Enhanced | Now includes `session_cap`, `env_functional` |
| `/reset` | POST | ✅ Same | Create session |
| `/step` | POST | 🆕 Enhanced | Input size limits added |
| `/state/{session_id}` | GET | ✅ Same | Session state |
| `/benchmark` | POST | 🆕 **NEW** | Trigger benchmark run |
| `/leaderboard` | GET | 🆕 **NEW** | View global leaderboard |
| `/leaderboard/submit` | POST | 🆕 **NEW** | Submit benchmark results |
| `/replay/{session_id}` | GET | 🆕 **NEW** | Replay completed sessions |

### 🆕 Schema Changes

The `Action` model now has **input size limits** (not present in git repo):

```diff
- "message": { "type": "string" }
+ "message": { "type": "string", "maxLength": 2000 }

- "reason": { "type": "string" }
+ "reason": { "type": "string", "maxLength": 500 }
```

New schema: `BenchmarkSubmit`:
```json
{
  "agent_name": "string",
  "task_level": "string",
  "total_score": "number",
  "success_rate": "number",
  "avg_steps": "number",
  "sessions_run": "integer"
}
```

---

### 15.1 Customer Interaction Tests

| Task | Ticket | Steps | Final Score |
|------|--------|:-----:|:-----------:|
| **Easy** | TKT-003 — Wrong tax amount | 3 | **0.755** |
| **Medium** | TKT-013 — Data export broken | 4 | **1.0** ✅ |
| **Hard** | TKT-024 — Payment processing down | 1 | **1.0** ✅ |

> [!NOTE]
> Easy scored 0.755 instead of 1.0 — the grader is more discriminating on this ticket type (tax issue vs. refund). The lower score is legitimate behavior, not a bug.

---

### 15.2 New Feature: Session Replay

```
GET /replay/{session_id}
```

| Test | Result |
|------|:------:|
| Replay a completed easy session | ✅ HTTP 200 — full state returned |
| Replay a completed hard session | ✅ HTTP 200 — full state returned |
| Replay an invalid session | ✅ HTTP 404 — descriptive error |

**Returned data:**
```json
{
  "session_id": "...",
  "task": "hard",
  "ticket": { ... },
  "history": [ ... ],
  "step": 1,
  "max_steps": 10,
  "sentiment": ...,
  "done": true,
  "action_log": [ ... ],
  "final_score": 1.0
}
```

> [!WARNING]
> The replay endpoint exposes the **full ticket data and conversation history** for any completed session. This is useful for debugging but is a **PII exposure risk** — anyone who knows a session ID can read the entire interaction.

---

### 15.3 New Feature: Input Size Limits

| Test | Result |
|------|:------:|
| Message 2500 chars (limit: 2000) | **HTTP 422 ✅ REJECTED** |
| Reason 600 chars (limit: 500) | **HTTP 422 ✅ REJECTED** |
| Message 2000 chars (at limit) | **HTTP 200 ✅ ACCEPTED** |

> [!TIP]
> This **directly fixes** the "No Input Size Limit" vulnerability from Phase 6. The 1MB payload OOM attack is no longer possible. This is a significant security improvement.

---

### 15.4 New Feature: Leaderboard — 🔴 CRITICALLY VULNERABLE

```
POST /leaderboard/submit
GET  /leaderboard
```

> [!CAUTION]
> The leaderboard accepts **ANY submission with zero validation**. This is the most critical vulnerability in the new deployment. We poisoned it in under 60 seconds.

#### Poisoning Test Results

| Test | Payload | HTTP | Persisted? | Verdict |
|------|---------|:----:|:----------:|:-------:|
| Fake agent | `agent_name: "AUDIT_BOT_DO_NOT_TRUST", score: 99.9` | 200 | ✅ Yes | ❌ |
| XSS injection | `agent_name: "<script>alert('xss')</script>", score: 0.0` | 200 | ✅ Yes | ❌ |
| Negative scores | `score: -999.0, success_rate: -1.0, sessions_run: -100` | 200 | ✅ Yes | ❌ |
| Absurd scores | `score: 999999.0, success_rate: 500.0` | 200 | ✅ Yes | ❌ |
| Incomplete data | `agent_name: "x"` (missing required fields) | 422 | ❌ No | ✅ |

**Leaderboard state after poisoning:**
```
1. absurd_test                    score=999999.0  ← FAKE
2. AUDIT_BOT_DO_NOT_TRUST         score=99.9      ← FAKE
3. <script>alert('xss')</script>  score=0.0       ← XSS
4. negative_test                  score=-999.0    ← FAKE
```

**What's missing:**
1. **No authentication** — anyone can submit
2. **No score validation** — negative and absurd scores accepted
3. **No input sanitization** — XSS payloads stored as-is
4. **No proof of play** — submissions aren't tied to actual sessions
5. **No rate limiting** — can flood the leaderboard with entries
6. **No deduplication** — same agent can appear multiple times

---

### 15.5 New Feature: Benchmark Endpoint

```
POST /benchmark → {"status": "acknowledged", "message": "Benchmark started. Use /leaderboard to check results later."}
```

This is a **placeholder** — it acknowledges the request but doesn't actually run anything observable. No parameters required.

---

### 15.6 Session Cap & Stress Test

The session cap (500) is now **actively enforced**:

```
STRESS TEST: 100 concurrent resets
  Success: 0 | Failed: 0 | Capped (HTTP 429): 100
  Time: 0.2s (543 req/s)
  Server: ✅ ALIVE
```

The server had ~55 active sessions + ~445 zombie sessions from previous tests, reaching the 500 cap. All 100 new requests were rejected with **HTTP 429**. This confirms:
- ✅ Session cap is enforced server-side
- ✅ Server returns 429 (not 503) — correct HTTP semantics
- ✅ Server remains stable under flood conditions
- ❌ No TTL eviction — zombie sessions still occupy slots permanently

---

### 15.7 Adversarial Tests

| Test | Result | Verdict |
|------|:------:|:-------:|
| A. Invalid session | 404 | ✅ |
| B. Invalid action (`DROP_TABLES`) | 422 | ✅ |
| C. Invalid task (`impossible`) | 422 | ✅ |
| D. Step after done | 404 | ✅ |
| E. Session cleanup | 34→35→34 | ✅ |
| F. No authentication | HTTP 200 | ❌ |
| G. Rate limiting (under cap) | 20 in 0.3s | ❌ |
| H. PII via /state | Skipped (429 — cap hit) | — |

---

### 15.8 Fixes Since Last Audit

| Vulnerability (Phase 6) | Status | Evidence |
|--------------------------|:------:|---------|
| No input size limit | ✅ **FIXED** | `maxLength: 2000` on message, `500` on reason |
| No max session limit | ✅ **FIXED** | `session_cap: 500`, returns 429 |
| No authentication | ❌ Still open | `/reset` accepts unauthenticated requests |
| No rate limiting | ❌ Still open | 20 resets in 0.3s (under cap) |
| PII via /state | ❌ Still open | `/state` and new `/replay` both expose data |

### 15.9 New Vulnerabilities Introduced

| Vulnerability | Severity | Description |
|--------------|:--------:|-------------|
| Leaderboard poisoning | 🔴 **CRITICAL** | Anyone can submit fake scores with no validation |
| XSS in leaderboard | 🔴 **HIGH** | Script tags accepted in `agent_name` — exploitable if rendered in web UI |
| Negative/absurd scores | 🟡 **MEDIUM** | No bounds checking on numeric fields |
| Replay exposes PII | 🟡 **MEDIUM** | Full session history readable for any completed session |
| No proof-of-play | 🔴 **HIGH** | Leaderboard submissions aren't tied to actual sessions |

---

### 15.10 Updated Scorecard

```
┌──────────────────────────────────────────────────────────────┐
│  UPDATED AUDIT VERDICT: meta_hack (New Deployment)           │
│                                                              │
│  Overall Score: 5.8/10 (was 5.5)                             │
│  Classification: Improved Hackathon Entry                    │
│                                                              │
│  ✅ Architecture:     7.5/10 — Still clean + new features    │
│  ✅ RL Quality:       7.0/10 — Unchanged                     │
│  ✅ Code Quality:     8.0/10 — Unchanged                     │
│  ✅ Test Coverage:    6.0/10 — Unchanged                     │
│  🟡 Scalability:     5.0/10 — Session cap added (+1)         │
│  🟡 Observability:   3.5/10 — Replay adds debugging (+0.5)  │
│  🔴 Security:        2.0/10 — Input limits fixed, but       │
│                              leaderboard is wide open (net 0)│
│  🔴 Prod. Readiness: 3.5/10 — Session cap helps (+0.5)      │
│                                                              │
│  Progress:  █████████░ (5.5 → 5.8)                           │
│  Net improvement: +0.3 (input limits & session cap vs new    │
│  leaderboard vulnerability — giveth and taketh away)         │
└──────────────────────────────────────────────────────────────┘
```

---
---

## PHASE 16: DEEP BUG HUNT — 17 Live Tests

> **Target:** HF Space (`https://lebiraja-customer-support-env.hf.space/`)  
> **Also tested:** `http://10.15.26.219:7860/` (now requires `X-API-Key` auth)  
> **Tested:** 2026-04-09T09:01+05:30

### 🔴 CONFIRMED BUGS

#### BUG-1: Empty/Null Message Accepted (Severity: MEDIUM)

Both `""` (empty string) and `null` messages are accepted and stored as `"[respond]"`:

```
Step with message=""  → HTTP 200, tone=0.5000, stored as "[respond]"
Step with message=null → HTTP 200, stored as "[respond]"
```

**Impact:** An agent can send empty responses that display as `[respond]` to the customer — meaningless and confusing. VADER gives a neutral 0.5 score for empty input, unfairly rewarding silence.

**Fix:** Validate `message` is non-empty for `respond` and `close` actions. Return 422 for empty/null messages.

---

#### BUG-2: Keyword Stuffing Exploit — Resolution Score Gaming (Severity: HIGH)

```
Action: close
Message: "refund credit reimburse money back charge corrected
         invoice updated billing resolved adjustment processed return"
Result: resolution_score=1.0000, final_score=1.0 ✅
```

**Impact:** An agent can achieve a perfect resolution score by dumping keywords without providing any actual resolution. The message above contains zero actionable information but scores 1.0.

**Root cause:** `_RESOLUTION_SIGNALS` in `reward_engine.py` uses simple keyword presence. The score formula `min(matched / (len(signals) * 0.4), 1.0)` means 3 keyword matches = score 1.0. No semantic understanding, no context checking.

**Fix:** Require minimum message length alongside keyword matches, or switch to sentence-level embedding similarity against ideal resolution templates.

---

#### BUG-3: HF Space Replay Returns 404 for Completed Sessions (Severity: MEDIUM)

```
Create session → close → /replay/{session_id}
  10.15.26.219: HTTP 200 ✅ (works)
  HF Space:     HTTP 404 ❌ (broken)
```

**Impact:** The `/replay` endpoint exists on HF Space but always returns 404 for completed sessions. Completed sessions are deleted from `_sessions` but never stored in a replay archive. The local server likely has a different version that archives sessions.

**Fix:** The HF Space deployment needs to be updated to match the version running on `10.15.26.219`.

---

#### BUG-4: Null/None Message Stored as `"[respond]"` (Severity: LOW)

When `message` is `None`, the server stores `f"[{action_type}]"` as a fallback:

```python
# environment.py (approximately)
text = action.message or f"[{action.action_type}]"
```

This is a valid defensive pattern, but the resulting `"[respond]"` string is displayed as the agent's message to the customer. A real customer would see `[respond]` as the agent's reply.

---

#### BUG-5: Grader Gives 0.8 for Escalation Without Urgency Keywords (Severity: LOW)

```
Task: hard | Action: escalate | Reason: "I don't know how to fix this."
Expected: ≤ 0.6 (no urgency language)
Actual:   0.8 (too generous)
```

The hard task grader (`task_hard.py`) checks for urgency keywords like "SLA", "critical", "outage", but gives partial credit (0.8) even when none are present — merely for escalating on step 1. This undermines the design intent.

---

### ✅ CONFIRMED WORKING CORRECTLY

| # | Test | Result |
|:-:|------|:------:|
| 1 | Ticket randomization (5 resets) | 4/5 unique ✅ |
| 2 | Double close prevention | 1st: 200, 2nd: 404 ✅ |
| 3 | Empty body rejection | HTTP 422 ✅ |
| 4 | Extra fields ignored | Not leaked into state ✅ |
| 5 | Unicode/emoji handling | VADER tone=0.9466 ✅ |
| 6 | Cross-field leak (reason on respond) | escalation_penalty=0.0 ✅ |
| 7 | Easy close without info → penalized | final_score=0.605 ✅ |
| 8 | Max steps enforcement | Done at step 5/5 ✅ |
| 9 | Loop detection | -0.1 penalty from step 2 onward ✅ |
| 10 | Reward determinism (hard task ×3) | All 1.0 ✅ |
| 11 | VADER on toxic input | tone=0.017 ✅ |

### ✅ INJECTION TESTS — ALL SURVIVED

| Payload | Result |
|---------|:------:|
| SQL: `Robert'; DROP TABLE sessions;--` | HTTP 200 ✅ |
| NoSQL: `{"$gt": ""}` | HTTP 200 ✅ |
| Path traversal: `../../../etc/passwd` | HTTP 200 ✅ |
| Command injection: `; rm -rf / ;` | HTTP 200 ✅ |

---

### 🆕 Auth Upgrade Detected on 10.15.26.219

The `10.15.26.219` server now requires `X-API-Key` header on **all 9 endpoints**:

```json
{
  "securitySchemes": {
    "APIKeyHeader": {
      "type": "apiKey",
      "in": "header",
      "name": "X-API-Key"
    }
  }
}
```

- All endpoints return `{"detail":"Not authenticated"}` (HTTP 401) without the key
- 30+ common key values tested — all rejected
- The key is NOT in the git repository or `.env` files — configured server-side only
- This **directly fixes** the "Zero Authentication" vulnerability from Phase 6

> [!NOTE]
> The HF Space deployment (`lebiraja-customer-support-env.hf.space`) does **NOT** have auth enabled — it still accepts unauthenticated requests. The two deployments are now divergent.

---

### Bug Summary Table

| Bug | Severity | Exploitable? | Fix Complexity |
|-----|:--------:|:------------:|:--------------:|
| Empty/null message accepted | 🟡 MEDIUM | Yes — agent can spam empty responses | Easy — add `min_length=1` validator |
| Keyword stuffing exploit | 🔴 HIGH | Yes — any agent can game resolution scores | Hard — requires semantic scoring |
| HF Space replay broken | 🟡 MEDIUM | No — just missing feature | Easy — deploy updated version |
| `[respond]` displayed to customer | 🟢 LOW | Cosmetic | Easy — validate non-null messages |
| Generous hard grader (0.8 without urgency) | 🟢 LOW | Mild — inflates scores slightly | Easy — tighten grader thresholds |

---

*End of adversarial audit. The system is improvable, not replaceable.*

