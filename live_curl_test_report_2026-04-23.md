# Live API Test Report (curl-only)

- Project: `customer-support-env`
- Environment Under Test: `http://localhost:7860`
- Date: `2026-04-23`
- Test Method: manual and scripted `curl` calls only
- Scope: customer flows, developer endpoints, tester negative and edge cases

## Executive Summary

The live API is operational and supports complete single-agent and hierarchical ticket flows with scoring, replay, and leaderboard integration. Validation and runtime protections (schema checks, body-size limit, rate limiting) are active. One critical security/design gap was confirmed: API key verification is implemented in code but not enforced on tested endpoints.

## Coverage Matrix

| Area | Status | Notes |
|---|---|---|
| Health and root metadata | PASS | `/health` and `/` returned `200` with expected payloads |
| Single-agent easy flow | PASS | `reset -> respond -> close`, terminal score returned |
| Single-agent medium flow | PASS | `reset -> request_info -> respond -> close`, terminal score returned |
| Single-agent hard flow | PASS | `reset -> respond -> escalate`, strong terminal score |
| Single-agent nightmare flow | PASS | multi-turn run completed with terminal score |
| Hierarchy easy flow | PASS | L1/L2 path completed and replay accessible |
| Hierarchy medium flow | PASS | feedback, escalation, manager resolution path validated |
| Hierarchy hard flow | PASS | all 3 roles engaged, policy drift event observed |
| Replay retrieval | PASS | completed sessions available, active/nonexistent return `404` |
| Leaderboard submit (valid proof-of-play) | PASS | accepted and listed in leaderboard |
| Leaderboard submit (invalid proof-of-play) | PASS | rejected with `404` |
| Invalid task validation | PASS | `/reset?task=impossible` returned `422` |
| Unknown session handling | PASS | `/step` with unknown session returned `404` |
| Invalid action schema | PASS | missing `reason` for `escalate` returned `422` |
| Request body-size guard | PASS | oversized payload rejected with `413` |
| Rate limiting | PASS | burst reset test returned both `200` and `429` as expected |
| PII masking on state/replay | PASS | email redacted as `[REDACTED_EMAIL]` in state output |
| API docs and OpenAPI | PASS | `/docs` and `/openapi.json` returned `200` |
| API key enforcement on endpoints | FAIL | requests succeeded (`200`) with no key and wrong key |

## Detailed Results

### 1. Baseline Service Checks

- `GET /health` -> `200`
- `GET /` -> `200`
- `GET /docs` -> `200`
- `GET /openapi.json` -> `200`

Observed health payload remained stable before and after full test cycle.

### 2. Customer Journey Tests

#### Easy

- Reset successful.
- Respond step successful.
- Close step successful.
- Episode terminated with `done=true` and `final_score` returned.
- Example observed final score: `0.85`.

#### Medium

- Reset successful.
- `request_info` step accepted and rewarded.
- Follow-up `respond` accepted.
- `close` ended episode and returned `final_score`.
- Example observed final score: `0.9`.

#### Hard

- Reset successful on critical-type ticket.
- Step 1 acknowledge/response accepted.
- Step 2 escalation accepted and episode terminated.
- Example observed final score: `1.0`.

#### Nightmare

- Multi-turn run completed after rate-limit cooldown.
- Terminal close returned `done=true` and `final_score`.
- Example observed final score: `0.7`.

### 3. Hierarchical Workflow Tests

#### Hierarchy Medium

Validated role-state transitions end-to-end:

- L1 `respond` -> `active_role=supervisor`
- L2 `supervisor_feedback` -> `active_role=support_agent` with feedback present
- L1 improved `respond` -> `active_role=supervisor`
- L2 `supervisor_escalate` -> `active_role=manager`
- L3 `manager_resolve` -> episode completed

Replay retrieval for completed session returned `200` and full action trace.

#### Hierarchy Hard

Validated all levels with policy drift context:

- L1 `respond`
- L2 `supervisor_escalate`
- L3 `manager_resolve`
- Episode completed with high score (`0.985` observed)
- Environment event/policy amendment was injected and surfaced in observation

### 4. Tester Negative and Edge Cases

- Invalid task:
  - `POST /reset?task=impossible` -> `422`
- Unknown session:
  - `POST /step?session_id=does-not-exist` -> `404`
- Invalid action payload:
  - `{"action_type":"escalate"}` -> `422` (missing reason)
- Replay for unknown/non-completed session:
  - `GET /replay/nonexistent-session-id` -> `404`
- Oversized request body:
  - ~70KB JSON to `/step` -> `413` (`Request body too large`)
- Rate limiter behavior:
  - 35 rapid resets produced `reset_200=28`, `reset_429=7`, `reset_other=0`

### 5. Data Privacy Check

- Session state included customer email in raw conversation before sanitization.
- `GET /state/{session_id}` output masked it as `[REDACTED_EMAIL]`.
- Result: sanitization mechanism is functioning for exposed state endpoint.

### 6. Leaderboard and Replay Validation

- Valid proof-of-play submit:
  - `POST /leaderboard/submit` with completed session -> `200`
- Invalid submit:
  - nonexistent session -> `404`
- `GET /leaderboard` reflected successful submissions and sorting by score.

## Findings

### Critical Finding

1. API key enforcement is not active on tested endpoints.
- Evidence:
  - `POST /reset?task=easy` with no `X-API-Key` -> `200`
  - `POST /reset?task=easy` with wrong `X-API-Key` -> `200`
- Impact:
  - Any client can run sessions and mutate server state without auth.

### Additional Notes

1. Rate limiting is correctly active and can interfere with bulk testing if not paced.
2. Active session count remained below cap during testing.
3. Benchmark endpoint responds as acknowledged placeholder (`200`).

## Conclusion

The system is functionally solid for benchmark-style operation and supports the expected customer, hierarchy, replay, leaderboard, and validation workflows in a live environment. The major issue to address before secure multi-tenant exposure is endpoint authentication enforcement.

## Recommended Next Fixes

1. Enforce `verify_api_key` via `Depends(...)` on mutation and sensitive endpoints (`/reset`, `/step`, `/state`, `/replay`, leaderboard writes).
2. Keep public read-only endpoints intentionally open only if required (`/health`, optionally `/docs`, `/openapi.json`) and document that policy.
3. Add a simple auth test case to CI ensuring wrong/missing API key returns `403` where expected.
