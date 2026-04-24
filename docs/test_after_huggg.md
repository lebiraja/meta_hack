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

*End of adversarial audit. The system is improvable, not replaceable.*

