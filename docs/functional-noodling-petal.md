# Customer Support RL Environment — Implementation Plan

## Context
Building a complete OpenEnv-compliant RL training environment for the Meta × PyTorch × Scaler OpenEnv Hackathon (Team X-Force). Deadline: April 8, 11:59 PM IST (TODAY). The repo is a blank slate — only guide.md, development.md, and AgentOS.md exist. Zero implementation code. Must build everything from scratch in the correct order to avoid the failure patterns documented in development.md.

LLM API: NVIDIA NIM (nvidia/nemotron-3-super-120b-a12b) via OpenAI-compatible client with streaming + reasoning support. API key stored in `.env`.

## Critical Architecture Rules (from development.md anti-patterns)
- **One server**: Dockerfile runs `server.app:app`. `inference.py` is HTTP client only.
- **Session isolation**: Every `/reset` returns `session_id`. No global mutable dicts.
- **Real rewards**: VADER for tone, cosine similarity for loop detection, NOT keyword counting.
- **Non-sparse rewards**: Partial signals every step.
- **Proper HTTP status codes**: 404 for missing session, 422 for bad input, never 200 on error.

## Files to Create (in build order)

### 1. `.env` — API keys and config
```
NVIDIA_API_KEY=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
API_BASE_URL=https://integrate.api.nvidia.com/v1
MODEL_NAME=nvidia/nemotron-3-super-120b-a12b
ENV_URL=http://localhost:7860
```

### 2. `env/models.py` — Pydantic models
- `ActionType` enum: respond, escalate, close, request_info
- `Action(BaseModel)`: action_type, message, reason
- `Message(BaseModel)`: role (customer|agent), content
- `Observation(BaseModel)`: ticket_id, category, priority, subject, conversation_history, step, max_steps, customer_sentiment, unresolved_issues, is_done, session_id
- `Reward(BaseModel)`: value (0.0–1.0), resolution_score, tone_score, efficiency_score, accuracy_score, breakdown dict
- `Ticket(BaseModel)`: full ticket schema including required_info_before_close, expected_resolution_type, customer_persona, task

### 3. `env/ticket_store.py` — 30 mock tickets
- 10 easy (billing, low/medium priority): double charges, refund status, invoice errors
- 10 medium (technical/account, medium priority): broken product, account access, multi-step complaints  
- 10 hard (critical priority, SLA-breach scenarios): service outages, data issues, enterprise customers
- Each ticket has: id, category, priority, subject, opening_message, follow_up_info, required_info_before_close, expected_resolution_type, ideal_max_steps, customer_persona, task
- `TicketStore` class with `get_random_by_task(task)` method

### 4. `env/reward_engine.py` — Real reward signals
- `compute_tone_score(message)`: VADER SentimentIntensityAnalyzer, normalize compound score
- `compute_loop_penalty(history)`: TF-IDF cosine similarity between last 2 agent messages, -0.1 if >0.85
- `compute_resolution_score(action, ticket)`: Compare action's implied solution to `expected_resolution_type` — NOT keyword match
- `compute_efficiency_score(steps_used, max_steps)`: `1.0 - (steps_used / max_steps)`
- `compute_accuracy_score(history, ticket)`: Did agent gather `required_info_before_close`? Check conversation for account emails, order IDs
- `compute_escalation_penalty(action, ticket)`: -0.3 if escalating low/medium priority
- `compute_step_reward(...)`: Combines signals, clamps to [0.0, 1.0]

### 5. `env/environment.py` — Core CustomerSupportEnv class
```python
class CustomerSupportEnv:
    def reset(self, task) -> Observation
    def step(self, action: Action) -> tuple[Observation, Reward, bool, dict]
    def state(self) -> dict
```
- Picks random ticket from task pool on reset
- Tracks conversation_history, step count, customer_sentiment
- Applies customer persona to generate follow-up responses
- Calls reward_engine on every step
- Sets `is_done=True` on CLOSE/ESCALATE or max_steps reached

### 6. `env/graders/task_easy.py`
- `grade(session_state) -> float`
- Checks: CLOSE was called + solution matches "billing_clarification" or "refund_initiated" + no unnecessary escalation + completed in ≤5 steps
- Returns 0.0–1.0

### 7. `env/graders/task_medium.py`
- `grade(session_state) -> float`
- Checks: REQUEST_INFO or ID-gathering detected + resolution attempted + sentiment didn't drop below -0.5
- Returns 0.0–1.0

### 8. `env/graders/task_hard.py`
- `grade(session_state) -> float`  
- Checks: ESCALATE triggered in step ≤2 AND reason contains urgency reference ("SLA", "critical", "outage")
- High penalty for self-resolution attempts on critical tickets
- Returns 0.0–1.0

### 9. `server/app.py` — FastAPI server
- `POST /reset?task=easy` → returns `{session_id, observation}`
- `POST /step?session_id=...` with Action body → returns `{observation, reward, done, info}`
- `GET /state/{session_id}` → returns env state
- `GET /health` → `{"status": "ok"}`
- Per-session `_sessions: dict[str, CustomerSupportEnv]` — no global mutable state
- Cleanup completed sessions on done=True

### 10. `inference.py` — LLM client (root level)
- Loads `.env` via `python-dotenv`
- Uses NVIDIA NIM API with streaming + reasoning (reasoning_content from delta)
- Collects full streamed response before parsing JSON action
- Emits exact `[START]`, `[STEP]`, `[END]` stdout format
- HTTP client via `httpx` to `ENV_URL`
- Runs all 3 tasks sequentially

### 11. `tests/test_env.py`
- Test `reset()` returns valid Observation with session_id
- Test `step()` with each ActionType
- Test rewards are non-trivial (not 0.0 or 1.0 on first step)
- Test session isolation (two envs don't share state)
- Test loop detection triggers penalty
- Test hard task grader requires escalation in step ≤2

### 12. `docker-compose.yml` + `Dockerfile`
- `Dockerfile`: python:3.11-slim, copy requirements, copy code, expose 7860, CMD uvicorn server.app:app
- `docker-compose.yml`: service `env`, env_file: .env, ports 7860:7860, healthcheck
- `.env` referenced from docker-compose via `env_file`

### 13. `requirements.txt`
```
fastapi>=0.110.0
uvicorn[standard]>=0.29.0
pydantic>=2.0.0
openai>=1.0.0
httpx>=0.27.0
vaderSentiment>=3.3.2
numpy>=1.26.0
scikit-learn>=1.4.0
python-dotenv>=1.0.0
```

### 14. `pyproject.toml` — proper packaging (no sys.path hacks)
```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "customer-support-env"
version = "1.0.0"
```

### 15. `openenv.yaml` — metadata
Per spec: name, version, description, author, tasks, action_space, observation_space, reward_range, tags

### 16. `README.md` — documentation
- Overview, Action Space table, Observation Space table, Tasks (easy/medium/hard), Reward Function explanation, Setup & Usage (Docker + local), Baseline Scores table

## Key Implementation Details

### NVIDIA NIM Streaming in inference.py
```python
completion = client.chat.completions.create(
    model=MODEL_NAME,
    messages=[...],
    temperature=1,
    top_p=0.95,
    max_tokens=16384,
    extra_body={"chat_template_kwargs": {"enable_thinking": True}, "reasoning_budget": 16384},
    stream=True
)
full_content = ""
for chunk in completion:
    if not chunk.choices: continue
    reasoning = getattr(chunk.choices[0].delta, "reasoning_content", None)
    if reasoning: pass  # consume but don't print to avoid polluting stdout format
    if chunk.choices[0].delta.content:
        full_content += chunk.choices[0].delta.content
action = json.loads(full_content.strip())
```

### Session ID flow
- `/reset` creates UUID, stores env in `_sessions[uuid]`, returns `{session_id: uuid, observation: {...}}`
- `/step?session_id=uuid` looks up session, runs step, returns result
- Observation model includes `session_id` field

### Customer Sentiment Simulation
- Start at 0.0 (neutral)
- RESPOND with positive tone → +0.1 to +0.2
- RESPOND with negative/vague tone → -0.1 to -0.2
- REQUEST_INFO → neutral (slight +0.05 for showing effort)
- ESCALATE → depends on priority (critical: +0.3, low: -0.2)

### Loop Detection
- Keep last 2 agent messages in history
- Compute TF-IDF vectors, cosine similarity
- If similarity > 0.85 → apply -0.1 penalty
- Use sklearn's TfidfVectorizer + cosine_similarity

## Verification Steps
```bash
# 1. Local run
pip install -e .
uvicorn server.app:app --port 7860

# 2. Test reset
curl -X POST http://localhost:7860/reset?task=easy

# 3. Run inference
python inference.py

# 4. Docker compose
docker compose up --build

# 5. Test via Docker
curl -X POST http://localhost:7860/reset?task=hard

# 6. Run tests
pytest tests/test_env.py -v
```
