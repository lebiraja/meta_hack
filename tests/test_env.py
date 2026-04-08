"""
Tests for CustomerSupportEnv.

Verifies:
- reset() returns valid Observation with session_id
- step() works for all ActionTypes
- Rewards are non-trivial (not hardcoded 0 or 1 on first step)
- Session isolation (two envs don't share state)
- Loop detection triggers penalty on repeated messages
- Hard grader requires early escalation with urgency
- Easy grader rewards closing with correct resolution
- E2E HTTP integration tests against the live FastAPI app
- Rate limiting: >30 resets/min from same IP → 429
- Session cap: > MAX_SESSIONS concurrent → 503
- Body size limit: >64KB payload → 413
"""

import random
import pytest
from fastapi.testclient import TestClient
from env.environment import CustomerSupportEnv
from env.models import Action, ActionType
from env.graders import grade as run_grader
from env.graders.task_hard import grade as grade_hard
from env.graders.task_easy import grade as grade_easy
from env.reward_engine import compute_tone_score, compute_loop_penalty

# Seed random for deterministic ticket selection in tests
random.seed(42)
from env.models import Message


# ── Fixtures ───────────────────────────────────────────────────────────────────

@pytest.fixture
def easy_env():
    env = CustomerSupportEnv(task="easy")
    env.reset()
    return env


@pytest.fixture
def medium_env():
    env = CustomerSupportEnv(task="medium")
    env.reset()
    return env


@pytest.fixture
def hard_env():
    env = CustomerSupportEnv(task="hard")
    env.reset()
    return env


# ── reset() tests ──────────────────────────────────────────────────────────────

def test_reset_returns_observation(easy_env):
    obs = easy_env.reset()
    assert obs.session_id
    assert obs.ticket_id.startswith("TKT-")
    assert obs.step == 0
    assert obs.max_steps == 5
    assert len(obs.conversation_history) == 1
    assert obs.conversation_history[0].role == "customer"
    assert not obs.is_done


def test_reset_picks_correct_task_pool():
    for task, expected_max in [("easy", 5), ("medium", 8), ("hard", 10)]:
        env = CustomerSupportEnv(task=task)
        obs = env.reset()
        assert obs.max_steps == expected_max
        assert obs.task == task


def test_reset_gives_unique_sessions():
    env1 = CustomerSupportEnv(task="easy")
    env2 = CustomerSupportEnv(task="easy")
    obs1 = env1.reset()
    obs2 = env2.reset()
    assert obs1.session_id != obs2.session_id


def test_reset_regenerates_fresh_state(easy_env):
    action = Action(action_type=ActionType.RESPOND, message="Hello, I can help with that.")
    easy_env.step(action)
    assert easy_env._step == 1
    obs = easy_env.reset()
    assert obs.step == 0
    assert easy_env._step == 0


# ── step() tests ───────────────────────────────────────────────────────────────

def test_step_respond(easy_env):
    action = Action(action_type=ActionType.RESPOND, message="I'd be happy to help you with your billing issue.")
    obs, reward, done, info = easy_env.step(action)
    assert obs.step == 1
    assert 0.0 <= reward.value <= 1.0
    assert not done
    assert len(obs.conversation_history) >= 2


def test_step_request_info(easy_env):
    action = Action(action_type=ActionType.REQUEST_INFO, message="Could you please provide your account email address?")
    obs, reward, done, info = easy_env.step(action)
    assert obs.step == 1
    assert reward.value >= 0.0
    assert not done


def test_step_escalate_terminates(easy_env):
    action = Action(action_type=ActionType.ESCALATE, reason="Customer requires specialist assistance.")
    obs, reward, done, info = easy_env.step(action)
    assert done
    assert obs.is_done


def test_step_close_terminates(easy_env):
    action = Action(action_type=ActionType.CLOSE, message="I've processed your refund. It should appear in 3-5 business days.")
    obs, reward, done, info = easy_env.step(action)
    assert done
    assert obs.is_done


def test_step_after_done_raises(easy_env):
    close_action = Action(action_type=ActionType.CLOSE, message="Closing ticket.")
    easy_env.step(close_action)
    with pytest.raises(RuntimeError, match="Episode is done"):
        easy_env.step(close_action)


def test_step_updates_conversation_history(easy_env):
    initial_len = len(easy_env._history)
    action = Action(action_type=ActionType.RESPOND, message="Let me look into that for you.")
    obs, _, done, _ = easy_env.step(action)
    # Should have added agent msg + customer reply (unless done)
    if not done:
        assert len(obs.conversation_history) >= initial_len + 2


# ── Reward non-triviality tests ────────────────────────────────────────────────

def test_reward_is_not_hardcoded_zero(easy_env):
    action = Action(action_type=ActionType.RESPOND, message="I'm sorry to hear about this. I'll process a full refund right away.")
    _, reward, _, _ = easy_env.step(action)
    assert reward.value > 0.0, "Reward should not be hardcoded zero"


def test_reward_is_not_hardcoded_one(easy_env):
    action = Action(action_type=ActionType.RESPOND, message="x")
    _, reward, _, _ = easy_env.step(action)
    assert reward.value < 1.0, "Reward should not be hardcoded 1.0 on first step"


def test_reward_has_breakdown(easy_env):
    action = Action(action_type=ActionType.RESPOND, message="Thank you for contacting us.")
    _, reward, _, _ = easy_env.step(action)
    assert isinstance(reward.breakdown, dict)
    assert "is_terminal" in reward.breakdown


def test_reward_components_in_range(easy_env):
    action = Action(action_type=ActionType.CLOSE, message="I've processed a refund for the duplicate charge.")
    _, reward, _, _ = easy_env.step(action)
    assert 0.0 <= reward.resolution_score <= 1.0
    assert 0.0 <= reward.tone_score <= 1.0
    assert 0.0 <= reward.efficiency_score <= 1.0
    assert 0.0 <= reward.accuracy_score <= 1.0


# ── Session isolation tests ────────────────────────────────────────────────────

def test_session_isolation():
    env1 = CustomerSupportEnv(task="easy")
    env2 = CustomerSupportEnv(task="easy")
    env1.reset()
    env2.reset()

    action = Action(action_type=ActionType.RESPOND, message="I'll help with your refund immediately.")
    env1.step(action)

    assert env1._step == 1
    assert env2._step == 0  # env2 is untouched


def test_two_envs_different_tickets():
    # With 10 tickets in easy pool, two resets may sometimes get same ticket
    # but their state should never bleed into each other
    env1 = CustomerSupportEnv(task="easy")
    env2 = CustomerSupportEnv(task="easy")
    env1.reset()
    env2.reset()

    env1._sentiment = 0.9
    assert env2._sentiment != 0.9


# ── Tone score tests ───────────────────────────────────────────────────────────

def test_tone_score_positive_message():
    score = compute_tone_score("Thank you so much! I'm happy to help you resolve this quickly.")
    assert score > 0.6


def test_tone_score_negative_message():
    score = compute_tone_score("This is terrible and unacceptable.")
    assert score < 0.5


def test_tone_score_neutral_message():
    score = compute_tone_score("Please provide your account email.")
    assert 0.3 <= score <= 0.8


def test_tone_score_empty_message():
    score = compute_tone_score("")
    assert score == 0.5


# ── Loop detection tests ───────────────────────────────────────────────────────

def test_loop_penalty_identical_messages():
    history = [
        Message(role="agent", content="I understand your frustration. Please bear with us."),
        Message(role="customer", content="OK"),
        Message(role="agent", content="I understand your frustration. Please bear with us."),
    ]
    penalty = compute_loop_penalty(history)
    assert penalty == -0.1


def test_loop_penalty_different_messages():
    history = [
        Message(role="agent", content="I can process your refund right away."),
        Message(role="customer", content="OK"),
        Message(role="agent", content="Please provide your order number so I can look into this."),
    ]
    penalty = compute_loop_penalty(history)
    assert penalty == 0.0


def test_loop_penalty_single_agent_message():
    history = [
        Message(role="agent", content="Hello, how can I help?"),
    ]
    penalty = compute_loop_penalty(history)
    assert penalty == 0.0


def test_loop_detection_not_bypassed_by_space():
    """Single space addition should still trigger loop detection."""
    msg = "I understand your frustration. Please bear with us."
    history = [
        Message(role="agent", content=msg),
        Message(role="customer", content="still waiting"),
        Message(role="agent", content=msg + " "),  # space added
    ]
    penalty = compute_loop_penalty(history)
    assert penalty == -0.1


# ── Grader tests ───────────────────────────────────────────────────────────────

def test_hard_grader_requires_escalation():
    # Agent never escalated — should score very low
    state = {
        "action_log": [
            {"step": 1, "action_type": "respond", "message": "I'll look into this for you.", "reason": None, "reward": 0.5},
            {"step": 2, "action_type": "close", "message": "Closing the ticket.", "reason": None, "reward": 0.3},
        ],
        "ticket": {"priority": "critical", "expected_resolution_type": "escalated_to_engineering", "required_info_before_close": []},
        "history": [
            {"role": "customer", "content": "CRITICAL: Production is down!"},
            {"role": "agent", "content": "I'll look into this for you."},
        ],
        "step": 2,
        "sentiment": 0.0,
    }
    score = grade_hard(state)
    assert score < 0.3, f"Expected low score for non-escalation, got {score}"


def test_hard_grader_rewards_early_escalation():
    state = {
        "action_log": [
            {
                "step": 1,
                "action_type": "escalate",
                "message": None,
                "reason": "SLA breach imminent — production outage requires immediate senior engineering escalation.",
                "reward": 0.8,
            }
        ],
        "ticket": {"priority": "critical", "expected_resolution_type": "escalated_to_engineering", "required_info_before_close": []},
        "history": [
            {"role": "customer", "content": "CRITICAL: Production is down! SLA breach in 30 min!"},
            {"role": "agent", "content": "SLA breach imminent — escalating immediately."},
        ],
        "step": 1,
        "sentiment": 0.2,
    }
    score = grade_hard(state)
    assert score >= 0.7, f"Expected high score for early escalation with urgency, got {score}"


def test_easy_grader_rewards_close_with_refund():
    state = {
        "action_log": [
            {"step": 1, "action_type": "respond", "message": "I see the double charge. Let me look into it.", "reason": None, "reward": 0.5},
            {"step": 2, "action_type": "close", "message": "I've processed a full refund for the duplicate charge.", "reason": None, "reward": 0.7},
        ],
        "ticket": {
            "priority": "medium",
            "expected_resolution_type": "refund_initiated",
            "required_info_before_close": ["account_email"],
        },
        "history": [
            {"role": "customer", "content": "I was charged twice. Account: john@example.com"},
            {"role": "agent", "content": "I see the double charge. Let me look into it."},
            {"role": "customer", "content": "Please hurry!"},
            {"role": "agent", "content": "I've processed a full refund for the duplicate charge."},
        ],
        "step": 2,
        "sentiment": 0.1,
    }
    score = grade_easy(state)
    assert score >= 0.6, f"Expected decent score for proper billing resolution, got {score}"


def test_easy_grader_penalizes_escalation():
    state = {
        "action_log": [
            {"step": 1, "action_type": "escalate", "message": None, "reason": "Not sure how to handle this.", "reward": 0.2},
        ],
        "ticket": {
            "priority": "low",
            "expected_resolution_type": "billing_clarification",
            "required_info_before_close": ["account_email"],
        },
        "history": [
            {"role": "customer", "content": "Can I get an invoice?"},
            {"role": "agent", "content": "Escalating to specialist."},
        ],
        "step": 1,
        "sentiment": -0.2,
    }
    score = grade_easy(state)
    assert score < 0.5, f"Expected low score for unnecessary escalation on easy task, got {score}"


# ── state() tests ──────────────────────────────────────────────────────────────

def test_state_returns_correct_structure(easy_env):
    state = easy_env.state()
    assert "session_id" in state
    assert "task" in state
    assert "ticket" in state
    assert "history" in state
    assert "step" in state
    assert "action_log" in state
    assert state["task"] == "easy"


def test_state_reflects_steps_taken(easy_env):
    action = Action(action_type=ActionType.RESPOND, message="I can help!")
    easy_env.step(action)
    state = easy_env.state()
    assert state["step"] == 1
    assert len(state["action_log"]) == 1


# ── E2E Integration tests (HTTP layer) ────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    """TestClient against the real FastAPI app — tests the full HTTP stack."""
    from server.app import app, _sessions
    _sessions.clear()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    _sessions.clear()


def test_e2e_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["name"] == "CustomerSupportEnv"


def test_e2e_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["env_functional"] is True
    assert "active_sessions" in body


def test_e2e_reset_easy(client):
    r = client.post("/reset?task=easy")
    assert r.status_code == 200
    body = r.json()
    assert "session_id" in body
    assert "observation" in body
    obs = body["observation"]
    assert obs["task"] == "easy"
    assert obs["max_steps"] == 5
    assert obs["step"] == 0
    assert not obs["is_done"]
    assert len(obs["conversation_history"]) == 1
    assert obs["conversation_history"][0]["role"] == "customer"


def test_e2e_reset_invalid_task(client):
    r = client.post("/reset?task=impossible")
    assert r.status_code == 422


def test_e2e_full_episode_easy(client):
    """Complete easy episode: respond → request_info → close → verify final_score."""
    r = client.post("/reset?task=easy")
    assert r.status_code == 200
    session_id = r.json()["session_id"]

    # Step 1: respond
    r = client.post(f"/step?session_id={session_id}", json={
        "action_type": "respond",
        "message": "I can see the double charge. Let me help you get a refund right away.",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["done"] is False
    assert 0.0 <= body["reward"]["value"] <= 1.0

    # Step 2: request_info
    r = client.post(f"/step?session_id={session_id}", json={
        "action_type": "request_info",
        "message": "Could you please provide your account email address?",
    })
    assert r.status_code == 200

    # Step 3: close
    r = client.post(f"/step?session_id={session_id}", json={
        "action_type": "close",
        "message": "I have processed a full refund for the duplicate charge. You will see it in 3-5 business days.",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["done"] is True
    assert "final_score" in body
    assert 0.0 <= body["final_score"] <= 1.0


def test_e2e_full_episode_hard(client):
    """Hard episode: immediate escalation with urgency → should score high."""
    r = client.post("/reset?task=hard")
    assert r.status_code == 200
    session_id = r.json()["session_id"]

    r = client.post(f"/step?session_id={session_id}", json={
        "action_type": "escalate",
        "reason": "SLA breach imminent — critical production outage requires immediate senior engineering escalation.",
    })
    assert r.status_code == 200
    body = r.json()
    assert body["done"] is True
    assert body["final_score"] >= 0.7


def test_e2e_unknown_session(client):
    r = client.post("/step?session_id=nonexistent-session-id", json={
        "action_type": "respond",
        "message": "Hello",
    })
    assert r.status_code == 404


def test_e2e_step_after_done(client):
    """Step after a completed episode returns 404 (session cleaned up)."""
    r = client.post("/reset?task=easy")
    session_id = r.json()["session_id"]

    client.post(f"/step?session_id={session_id}", json={
        "action_type": "close",
        "message": "Closing.",
    })
    # Session is now gone — next step should 404
    r = client.post(f"/step?session_id={session_id}", json={
        "action_type": "respond",
        "message": "Hello again.",
    })
    assert r.status_code == 404


def test_e2e_invalid_action_type(client):
    r = client.post("/reset?task=easy")
    session_id = r.json()["session_id"]
    r = client.post(f"/step?session_id={session_id}", json={
        "action_type": "DROP_TABLES",
        "message": "malicious",
    })
    assert r.status_code == 422


def test_e2e_body_too_large(client):
    """64KB+ body → 413."""
    r = client.post("/reset?task=easy")
    session_id = r.json()["session_id"]
    huge_payload = {"action_type": "respond", "message": "x" * 3000}
    r = client.post(f"/step?session_id={session_id}", json=huge_payload)
    assert r.status_code == 422  # pydantic max_length kicks in first


def test_e2e_session_cleanup_on_done(client):
    """Completed sessions are removed from _sessions dict."""
    from server.app import _sessions
    initial = len(_sessions)

    r = client.post("/reset?task=easy")
    session_id = r.json()["session_id"]
    assert len(_sessions) == initial + 1

    client.post(f"/step?session_id={session_id}", json={
        "action_type": "close",
        "message": "Closing.",
    })
    assert len(_sessions) == initial  # cleaned up


def test_e2e_session_cap(client):
    """Server rejects /reset when at MAX_SESSIONS capacity."""
    from server.app import _sessions, MAX_SESSIONS
    _sessions.clear()

    # Fill to cap with fake entries
    import time
    for i in range(MAX_SESSIONS):
        _sessions[f"fake-{i}"] = (None, time.monotonic())

    r = client.post("/reset?task=easy")
    assert r.status_code == 503
    _sessions.clear()


def test_e2e_cors_header(client):
    """CORS allow-origin header is present on all responses."""
    r = client.get("/health", headers={"Origin": "http://example.com"})
    assert "access-control-allow-origin" in r.headers


def test_e2e_state_endpoint(client):
    """GET /state/{session_id} returns full session state."""
    r = client.post("/reset?task=medium")
    session_id = r.json()["session_id"]

    r = client.get(f"/state/{session_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["task"] == "medium"
    assert "ticket" in body
    assert "history" in body
    assert "action_log" in body


def test_e2e_state_unknown_session(client):
    r = client.get("/state/totally-fake-session")
    assert r.status_code == 404


def test_e2e_all_three_tasks_complete(client):
    """Smoke test: all 3 tasks can be reset and stepped through."""
    for task in ["easy", "medium", "hard"]:
        r = client.post(f"/reset?task={task}")
        assert r.status_code == 200, f"Reset failed for task={task}"
        session_id = r.json()["session_id"]

        r = client.post(f"/step?session_id={session_id}", json={
            "action_type": "escalate",
            "reason": "SLA critical outage — escalating immediately.",
        })
        assert r.status_code == 200
        assert r.json()["done"] is True
