# Plan: Unified `/chat` Endpoint — Single-Port User-Facing API

## Context

Currently the system has 3 ports: env (7860), model (8001), frontend (3000). To test the full RL loop (customer → model → env → reward), a curl user has to make 2 separate requests to 2 different services:

1. `POST http://localhost:7860/reset` → get session + observation
2. `POST http://localhost:8001/agent-action` → get model action
3. `POST http://localhost:7860/step` → apply action, get reward

This is awkward for testing, confusing for judges, and duplicates the frontend's orchestration logic on the client side.

**The fix:** Add a `/chat` endpoint to the env server (port 7860) that internally calls the model server (port 8001) so the user only needs to talk to one port.

**Why on port 7860 (not 8001):** The env is the stateful source of truth. The model is a stateless text generator. Coupling "apply-an-action-and-return-reward" to the env side is the correct direction — the env already has the session, observation, graders, and reward engine. Adding an HTTP-out call to reach the model is a tiny addition. Doing it the other way (model server owns the chat loop) would force the model server to duplicate session lookup and reward surfacing.

**Why this matters for training:**
- Training loop (`train/env_client.py`) **does not need `/chat`** — it uses `/reset` + `/step` directly and drives the model locally for speed. `/chat` is purely a testing/demo convenience layer.
- **Swap-in trained models:** Set `AGENT_MODEL_URL=https://yourspace.hf.space` to point `/chat` at a trained model deployed anywhere. One env var, no code changes.
- **OpenEnv purity preserved:** `/reset` and `/step` remain untouched. `/chat` is an optional extension that returns 503 if `AGENT_MODEL_URL` isn't set, so the env still validates with `openenv validate .`.

---

## Design

### New endpoint: `POST /chat` (in `server/app.py`)

**Request body:**
```json
{
  "session_id": "uuid",
  "message": "I was double charged on my credit card"
}
```

**Response body (flat, chat-friendly):**
```json
{
  "agent_reply": "I'm sorry to hear that. Let me process your refund right away.",
  "action_type": "respond",
  "active_role": "support_agent",
  "reward": 0.45,
  "step": 1,
  "max_steps": 5,
  "done": false,
  "customer_sentiment": 0.2,
  "unresolved_issues": ["account_email"],
  "final_score": null
}
```

### Internal flow

```
1. Validate session_id via _get_env() (existing helper, server/app.py:163)
2. Read AGENT_MODEL_URL env var (default http://host.docker.internal:8001)
3. Build current observation via env._build_observation()
4. POST observation to {AGENT_MODEL_URL}/agent-action via httpx
5. Receive action back, validate via Action pydantic model
6. Call env.step(action, human_customer_message=body.message)
7. For HIERARCHICAL tasks: loop steps 3-6 internally while active_role ≠ "support_agent" and not done,
   passing human_customer_message ONLY on the first iteration. This way the customer doesn't see
   intermediate supervisor/manager turns. Cap at 8 internal iterations for safety.
8. Return flat chat response (see above)
9. If done: call run_grader() for final_score (existing logic from /step handler at line 266-271)
```

### Key constants
- `AGENT_MODEL_URL` env var — default `http://host.docker.internal:8001`
- HTTP timeout to model: 60s (matches existing NIM call timeout patterns)
- Max internal hierarchy iterations: 8 (safety bound)

### Error handling
- No `AGENT_MODEL_URL` set AND model unreachable → `503` with clear message "Start serve_inference.py or set AGENT_MODEL_URL"
- Model returns malformed action → `502` with model error surfaced
- Session expired → `404` (existing _get_env behavior)
- Episode already done → `409` (existing env.step behavior)

---

## Files to modify

| File | Change |
|------|--------|
| `server/app.py` | Add `/chat` POST handler (~80 lines). Add one import: `httpx`. Add env var `AGENT_MODEL_URL`. |
| `docker-compose.yml` | Add `AGENT_MODEL_URL=http://host.docker.internal:8001` to env service `environment:` block (line 11-12). Add `extra_hosts: - "host.docker.internal:host-gateway"` so the env container can reach the host's port 8001. |
| `frontend/src/lib/api.ts` | Add `chat(sessionId, message)` method hitting `/chat` on port 7860. |
| `frontend/src/hooks/useHumanCustomer.ts` | Replace the 2-hop (fetchAIAction → /api/ai-action → 8001, then submitStep → /step) with single `api.chat()` call. Update `virtualMessages` from the response. |
| **NOT MODIFIED** | `serve_inference.py` (already exposes `/agent-action` correctly), `inference.py`, all `train/*.py` files, `env/environment.py`, `frontend/src/app/api/ai-action/route.ts` (kept for Auto-Play mode which doesn't need /chat) |

### Reused existing code (no rewrites)

- `server/app.py:163` `_get_env()` — session lookup with expiry sweep
- `server/app.py:266-276` — `run_grader()` + `_completed_sessions` saving on done
- `env/environment.py:154` `env.step(action, human_customer_message=...)` — already wired from last session
- `env/models.py:86-131` `Action` pydantic model — parse httpx response into this
- `env/environment.py:196` `env._build_observation()` — current obs for model
- `serve_inference.py:93-112` `/agent-action` — unchanged contract

---

## Exact new `/chat` handler (sketch for `server/app.py`, ~after line 290)

```python
import httpx

AGENT_MODEL_URL = os.environ.get("AGENT_MODEL_URL", "http://host.docker.internal:8001")
MAX_HIERARCHY_ITERATIONS = 8

class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(..., min_length=1, max_length=4000)

@app.post("/chat")
@limiter.limit("120/minute")
async def chat(request: Request, body: ChatRequest):
    env = _get_env(body.session_id)
    human_msg = body.message
    last_action = None
    last_reward = None
    last_done = False
    final_score = None

    async with httpx.AsyncClient(timeout=60.0) as client:
        for iteration in range(MAX_HIERARCHY_ITERATIONS):
            obs = env._build_observation().model_dump()
            try:
                r = await client.post(
                    f"{AGENT_MODEL_URL}/agent-action",
                    json={"observation": obs, "virtualMessages": []},
                )
                r.raise_for_status()
                action_dict = r.json()["action"]
            except httpx.RequestError as exc:
                raise HTTPException(503, f"Agent model unreachable at {AGENT_MODEL_URL}: {exc}")
            except (KeyError, ValueError) as exc:
                raise HTTPException(502, f"Model returned malformed response: {exc}")

            action = Action(**action_dict)
            try:
                obs_after, reward, done, info = env.step(
                    action,
                    human_customer_message=human_msg if iteration == 0 else None,
                )
            except RuntimeError as exc:
                raise HTTPException(409, str(exc))

            last_action = action
            last_reward = reward
            last_done = done

            if done:
                state = env.state()
                try:
                    final_score = run_grader(env.task, state)
                except Exception:
                    final_score = reward.value
                state["final_score"] = final_score
                _completed_sessions[body.session_id] = state
                if len(_completed_sessions) > 1000:
                    del _completed_sessions[next(iter(_completed_sessions))]
                del _sessions[body.session_id]
                break

            # If back at support_agent, return to the human for their next turn
            if obs_after.active_role == "support_agent":
                break
        else:
            raise HTTPException(500, f"Hierarchy did not resolve within {MAX_HIERARCHY_ITERATIONS} iterations")

    return {
        "agent_reply": last_action.message or last_action.reason or last_action.feedback_to_agent or "",
        "action_type": last_action.action_type,
        "active_role": last_action.role or "support_agent",
        "reward": last_reward.value,
        "step": obs_after.step,
        "max_steps": obs_after.max_steps,
        "done": last_done,
        "customer_sentiment": obs_after.customer_sentiment,
        "unresolved_issues": obs_after.unresolved_issues,
        "final_score": final_score,
    }
```

---

## Frontend simplification

**Before** (`useHumanCustomer.ts`): Human message → virtualMessages → fetchAIAction(/api/ai-action) → action → submitStep(/step) with humanCustomerMessage → 2 network round trips.

**After**: Human message → `api.chat(sessionId, message)` → single round trip. Store's `submitStep` logic is still used for Manual/Auto-Play; Chat mode uses the new path.

```typescript
// frontend/src/lib/api.ts
chat: (sessionId: string, message: string) =>
  apiFetch<ChatResponse>(`/chat`, {
    method: "POST",
    body: JSON.stringify({ session_id: sessionId, message }),
  }),
```

---

## Training compatibility

**No training code changes needed.** Confirmed by inspecting `train/env_client.py`:
- Lines 49–98 only call `/reset` and `/step`
- Training drives the model locally in-process, not over HTTP
- `/chat` is purely a test/demo interface

**After training, to test the trained model via curl:**
```bash
export AGENT_MODEL_URL=https://yourhfspace.hf.space   # or wherever trained model is served
docker compose restart env
# Now /chat uses the trained model
```

---

## Verification (end-to-end)

```bash
# 1. Services up
curl http://localhost:7860/health   # env
curl http://localhost:8001/health   # local model

# 2. Full chat loop via single port
SID=$(curl -s -X POST "http://localhost:7860/reset?task=easy" \
  -H "X-API-Key: meta_hack_2026" | jq -r '.session_id')

curl -s -X POST http://localhost:7860/chat \
  -H "Content-Type: application/json" -H "X-API-Key: meta_hack_2026" \
  -d "{\"session_id\": \"$SID\", \"message\": \"I was charged twice, email test@example.com\"}" | jq

# Keep chatting until done:true
curl -s -X POST http://localhost:7860/chat \
  -H "Content-Type: application/json" -H "X-API-Key: meta_hack_2026" \
  -d "{\"session_id\": \"$SID\", \"message\": \"Thanks, please close it\"}" | jq

# 3. Hierarchical task (internal L2/L3 loop handled transparently)
SID=$(curl -s -X POST "http://localhost:7860/reset?task=hierarchy_easy" \
  -H "X-API-Key: meta_hack_2026" | jq -r '.session_id')
curl -s -X POST http://localhost:7860/chat -H "X-API-Key: meta_hack_2026" \
  -d "{\"session_id\": \"$SID\", \"message\": \"I need a refund\"}" | jq

# 4. Frontend Chat as Customer still works (and is now 1 round trip instead of 2)

# 5. OpenEnv still validates
openenv validate .   # should still print [OK]

# 6. AGENT_MODEL_URL swap
AGENT_MODEL_URL=http://nonexistent:9999 docker compose restart env
# /chat should now 503 with clear error
# /reset and /step still work — proves /chat is optional, not required for OpenEnv compliance
```

---

## Out of scope (explicitly NOT doing)

- Auto-Play frontend rewrite (keeps existing 2-hop for now — it works)
- Removing the Manual Agent tab from frontend (user noted it's unnecessary — separate cleanup)
- Adding `/chat` to training pipeline (training has its own efficient in-process flow)
- Supporting non-text customer messages
- WebSocket streaming of agent tokens
