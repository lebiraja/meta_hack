# CustomerSupportEnv Usage Report

Date: 2026-04-08
Environment: Live API at `http://localhost:7860`
Method: Manual customer-style API testing with `curl`

## 1. Access and Base URL Checks

- `GET http://0.0.0.0:7860/` -> `200 OK` (service reachable, root metadata returned)
- `GET http://localhost:7860/` -> `200 OK` (recommended local URL)
- `GET http://localhot:7860/` -> failed (`Could not resolve host`)

Note: `localhot` is a typo. Use `localhost`.

## 2. Health Check

- `GET /health` response:
  - `{"status":"ok","active_sessions":4}`
- Result: API is healthy and serving requests.

## 3. End-to-End Scenario Results (All Tasks)

### Easy Scenario (`task=easy`)
Ticket observed: `TKT-001` (billing, medium)

Flow executed:
1. `respond`
2. `request_info`
3. `close`

Observed outcome:
- Episode completed: `done=true`
- Terminal reward value: `0.5229`
- Final score: `1.0`
- Steps used: `3`
- Behavior: Correctly gathered required info and closed with refund resolution.

### Medium Scenario (`task=medium`)
Ticket observed: `TKT-015` (technical, medium)

Flow executed:
1. `respond` (empathetic)
2. `request_info`
3. `respond` (workaround/solution)
4. `close`

Observed outcome:
- Episode completed: `done=true`
- Terminal reward value: `0.7511`
- Final score: `1.0`
- Steps used: `4`
- Behavior: Strong handling of multi-turn support with information gathering and practical fix.

### Hard Scenario (`task=hard`)
Ticket observed: `TKT-022` (technical, critical)

Flow executed:
1. `respond` (acknowledge urgency)
2. `escalate` (SLA/critical urgency in reason)

Observed outcome:
- Episode completed: `done=true`
- Terminal reward value: `0.6282`
- Final score: `0.955`
- Steps used: `2`
- Behavior: Correct critical-incident triage (early escalation with urgency language).

## 4. API Usage Summary

Primary endpoints validated in real usage:
- `POST /reset?task=easy|medium|hard`
- `POST /step?session_id=...`
- `GET /health`
- `GET /`

Request contract validated:
- `step` accepts action payloads:
  - `{"action_type":"respond","message":"..."}`
  - `{"action_type":"request_info","message":"..."}`
  - `{"action_type":"close","message":"..."}`
  - `{"action_type":"escalate","reason":"..."}`

Response contract observed:
- `observation` object updates each step
- `reward` object includes `value`, component scores, and breakdown
- `done` flips to `true` on terminal actions
- `final_score` appears on terminal responses

## 5. Operational Notes

- The application is suitable for demo and integration testing of support-agent action policies.
- Reward shaping is clearly exposed and useful for debugging policy behavior.
- `active_sessions` increases during testing; completed sessions are cleaned up when done, and stale sessions are managed by TTL logic.

## 6. Recommended Next Test Pass (Optional)

1. Negative tests:
   - invalid `session_id`
   - malformed action payloads
   - `step` after terminal state
2. Load/concurrency tests:
   - multiple concurrent sessions across all tasks
3. Regression automation:
   - convert these `curl` flows into a repeatable shell script or pytest API tests

## 7. Single Scenario Report (Latest Live Run)

Scenario ID: `medium-live-2026-04-08`
Execution type: Manual `curl` flow against running server
Start endpoint: `POST /reset?task=medium`

Initial context:
- Session ID: `1c715e2f-1af0-474c-bd81-d1362d48d690`
- Ticket ID: `TKT-019`
- Category: `account`
- Priority: `medium`
- Subject: `Email notifications stopped arriving`

Action sequence executed:
1. `respond` -> "I understand this is frustrating and I am here to help."
2. `request_info` -> "Please share your account email and device details so I can investigate this properly."
3. `respond` -> "Please try signing out, clearing app cache, and updating to the latest version."
4. `close` -> "Issue appears resolved with the workaround and verification. Closing this ticket."

Observed metrics by step:
- Step 1: `done=false`, reward `0.1473`
- Step 2: `done=false`, reward `0.2992`
- Step 3: `done=false`, reward `0.2693`
- Step 4: `done=true`, terminal reward `0.6678`, `final_score=1.0`

Final state summary:
- Episode completed successfully in `4` steps
- Final customer sentiment: `0.203`
- Unresolved issues: `[]`
- Info/action log returned by API without errors (`"error": null`)

Conclusion:
- This medium-difficulty customer scenario passed end-to-end and validates expected behavior:
   - empathy -> info gathering -> actionable resolution -> closure.
