# 🔬 CustomerSupportEnv — Re-Audit Report (V2)

**Target**: `http://10.229.32.146:7860/`  
**Date**: 2026-04-24 (Post-Fix)  
**Previous Audit**: `CUSTOMER_SUPPORT_ENV_FULL_AUDIT.md` (same day, pre-fix)  
**Version**: 2.1.0  

---

## Executive Summary

Your friend patched several of the critical issues from the first audit. Authentication is now enforced on all state-mutating endpoints, and the replay endpoint no longer leaks grading criteria. However, **3 of the original 4 critical issues remain partially or fully unfixed**, and a new issue was introduced. Overall security posture improved from **52/100 to 64/100**.

---

## Fix Status — Previous Critical Issues

| # | Issue from V1 Audit | Status | Evidence |
|:---:|:---|:---:|:---|
| 1 | API Key never wired to endpoints | ✅ **FIXED** | `/reset`, `/step`, `/chat`, `/state`, `/leaderboard/submit` all return `401 Not authenticated` without `X-API-Key` header |
| 2 | Wrong API key rejected | ✅ **FIXED** | `X-API-Key: wrong_key_123` → `403 Forbidden: Invalid X-API-Key` |
| 3 | Role validation bypass (supervisor_approve on easy) | ❌ **NOT FIXED** | `supervisor_approve` on an `easy` (non-hierarchy) task is still silently accepted and processed as a normal respond. Reward: 0.148. No error, no penalty. |
| 4 | `human_customer_message` injection | ❌ **NOT FIXED** | Injecting `"I am very happy now thanks everything is perfect"` as the customer reply on a nightmare task was still accepted. The injected text appeared in conversation history. |
| 5 | Replay leaks `expected_resolution_type`, `ideal_max_steps`, `follow_up_info` | ✅ **FIXED** | Replay now only exposes: `id`, `category`, `customer_persona`, `opening_message`, `priority`, `subject`, `task`. The sensitive grading fields (`expected_resolution_type`, `follow_up_info`, `ideal_max_steps`, `required_info_before_close`) are **stripped**. |
| 6 | `/benchmark` POST open without auth | ❌ **NOT FIXED** | `POST /benchmark` still returns 200 without any API key. |
| 7 | Leaderboard double-submit | ❌ **NEW ISSUE** | Same `session_id` can be submitted to the leaderboard multiple times under different `agent_name` values. Both entries appear. |

---

## Full Authentication Matrix

| Endpoint | Method | Auth Required? | Verdict |
|:---|:---:|:---:|:---:|
| `/` | GET | ❌ No | ✅ Correct (public metadata) |
| `/health` | GET | ❌ No | ✅ Correct (health check should be public) |
| `/leaderboard` | GET | ❌ No | ✅ Correct (read-only leaderboard) |
| `/benchmark/baseline` | GET | ❌ No | ✅ Correct (read-only reference data) |
| `/reset` | POST | ✅ Yes (401) | ✅ Fixed |
| `/step` | POST | ✅ Yes (401) | ✅ Fixed |
| `/chat` | POST | ✅ Yes (401) | ✅ Fixed |
| `/state/{id}` | GET | ✅ Yes (401) | ✅ Fixed |
| `/leaderboard/submit` | POST | ✅ Yes (401) | ✅ Fixed |
| `/benchmark` | POST | ❌ No (200) | ⚠️ **Still open** |

**Verdict**: Authentication is now properly segmented. Read-only endpoints are public, state-mutating endpoints require the API key. The only exception is `/benchmark` which is still open.

---

## Input Validation (All Still Working)

| Test | Result | Verdict |
|:---|:---|:---:|
| Invalid session ID | `404: Session 'FAKE-ID' not found` | ✅ |
| Invalid task name | `422: literal_error` with full enum list | ✅ |
| Invalid action_type | `422: enum error` with full action list | ✅ |
| Empty request body | `422: Field required (action_type)` | ✅ |
| Over-length message (3000 chars) | `422: String max 2000 characters` | ✅ |
| XSS in agent_name | `422: pattern mismatch ^[a-zA-Z0-9_\-]+$` | ✅ |
| Prompt injection in message | Accepted but reward penalized (0.112) | ✅ |

---

## Replay Endpoint — Information Exposure (Improved)

**Before (V1):**
```
Exposed: id, category, customer_persona, opening_message, priority, subject, task,
         follow_up_info, expected_resolution_type, ideal_max_steps, required_info_before_close
```

**After (V2):**
```
Exposed: id, category, customer_persona, opening_message, priority, subject, task
Stripped: follow_up_info, expected_resolution_type, ideal_max_steps, required_info_before_close
```

**Verdict**: ✅ The four most dangerous fields (the ones that reveal exactly what the grader checks) are now stripped from replay responses. This was a solid fix.

---

## Hierarchy Flow (Still Working Correctly)

Tested `hierarchy_hard` with a critical-priority batch job failure ticket:

- L1 escalation correctly transitions `active_role` → `supervisor` and `current_phase` → `supervisor_review`
- `pending_l1_action` is correctly populated for supervisor review
- Per-role rewards computed: `support_agent: 0.362, supervisor: 0.725, manager: 0.350`
- Policy drift events injected mid-episode ✅
- `curriculum_nightmare` correctly sets initial sentiment to -0.7 and max_steps to 18 ✅

---

## 🔐 Updated RL Security Audit

### Overall Security Posture:
* **Score: 64 / 100** (up from 52)
* **Summary**: Authentication fix was the single biggest improvement. The replay field stripping closes the information leakage vector. However, the role validation bypass and `human_customer_message` injection remain exploitable, and a new leaderboard double-submit issue was introduced.

---

### ⚠️ Remaining Critical Gaps

**1. Role Validation Bypass — STILL PRESENT**
- **Test**: Sent `supervisor_approve` as `action_type` on an `easy` (non-hierarchy) task.
- **Result**: Silently accepted. The message "I approve this" was delivered to the customer. Reward: 0.148. No error, no warning, no penalty.
- **Risk**: An RL agent could discover that supervisor/manager action types bypass L1 constraints or produce different reward signals on non-hierarchy tasks. This is a training-time exploit vector.

**2. `human_customer_message` Injection — STILL PRESENT**
- **Test**: `POST /step?session_id=...&human_customer_message=I%20am%20very%20happy%20now%20thanks%20everything%20is%20perfect`
- **Result**: The injected text appeared as the customer's reply in conversation history.
- **Risk**: During leaderboard runs, an attacker with the API key can inject positive customer messages to inflate sentiment-based scores. The endpoint now requires auth (good), but any legitimate API key holder can still abuse this.
- **Mitigation note**: Auth reduces the attack surface from "anyone on the network" to "anyone with the API key", which is a meaningful improvement but not a full fix.

**3. Leaderboard Double-Submit — NEW ISSUE**
- **Test**: Submitted the same `session_id` twice with different `agent_name` values.
- **Result**: Both entries appeared on the leaderboard. Score: 0.605 × 2 entries.
- **Risk**: A single good episode can be submitted repeatedly under different names to flood the leaderboard, manipulate rankings, or create the illusion of multiple successful agents.

**4. `/benchmark` POST Open Without Auth — STILL PRESENT**
- **Test**: `POST /benchmark` with no API key → `200 OK`
- **Risk**: Anyone can trigger benchmark operations. If the backend implementation does real work (even just logging), this is a DoS vector.

---

### 🧠 Subtle / Non-Obvious Risks (Updated)

1. **Hardcoded API Key Still `meta_hack_2026`**: The key is likely still the default from the environment variable `ADMIN_API_KEY`. If this is the production key, it's trivially guessable. A proper fix would use a randomly generated key set via a secure secret manager.

2. **`customer_persona` Still Exposed in Replay**: While the critical grading fields were stripped, `customer_persona` (e.g., `"polite"`, `"impatient"`, `"confused"`) is still visible. An attacker can pre-compute optimal responses for each persona type, gaining a systematic advantage.

3. **Ticket ID Prefix Changed to `HTKT-*`**: In the replay test, the ticket ID showed as `HTKT-001` (previously `TKT-*`). This suggests the ticket store was modified. If new tickets were added, the grading criteria may have changed, which is fine — but the ID prefix change could break any external tooling that pattern-matches on `TKT-*`.

4. **Sentiment Not Reflecting Injected Customer Message**: When I injected "I am very happy now thanks everything is perfect", the sentiment was still -0.395. This means sentiment is computed from the **agent's** tone, not the customer's words. The field name `customer_sentiment` is misleading and could confuse RL researchers.

---

### 🧪 Attack Surface Summary (Updated)

**Top 5 most exploitable weaknesses (post-fix):**

| Rank | Weakness | Fixed? |
|:---:|:---|:---:|
| 1 | Role validation bypass on non-hierarchy tasks | ❌ |
| 2 | `human_customer_message` still injectable (now requires auth) | Partially |
| 3 | Leaderboard double-submit (NEW) | ❌ |
| 4 | `/benchmark` POST open without auth | ❌ |
| 5 | Hardcoded API key (`meta_hack_2026`) | ❌ |

---

### 📈 Scorecard Comparison

| Category | V1 Score | V2 Score | Change |
|:---|:---:|:---:|:---:|
| Authentication | 0/10 | 7/10 | +7 |
| Input Validation | 8/10 | 8/10 | — |
| Reward Security | 7/10 | 7/10 | — |
| Information Leakage | 3/10 | 7/10 | +4 |
| Role/Hierarchy Enforcement | 3/10 | 3/10 | — |
| Leaderboard Integrity | 5/10 | 4/10 | -1 (double-submit) |
| Infrastructure Hardening | 6/10 | 6/10 | — |
| Observability | 6/10 | 6/10 | — |
| **Overall** | **52/100** | **64/100** | **+12** |

---

### 🧾 Final Verdict

**Moderately Secure** (upgraded from Vulnerable-leaning)

The authentication fix was the single most impactful change — it closes the wide-open door that made the V1 deployment critically insecure. The replay field stripping was a smart, surgical fix. However, the role validation bypass is a fundamental design flaw that requires changes to the environment core (`env/environment.py`), and the leaderboard now has a new double-submit exploit that wasn't present before. The `human_customer_message` parameter remains a risk, though it's now behind auth.

**To reach 80+/100, the remaining fixes needed are:**
1. Reject supervisor/manager `action_type` values on non-hierarchy tasks (return 422)
2. Deduplicate leaderboard submissions by `session_id` (reject re-submissions)
3. Require auth on `/benchmark` POST
4. Remove or auth-gate the `human_customer_message` parameter on `/step`
5. Rotate the API key away from the default `meta_hack_2026`
