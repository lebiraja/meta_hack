"""
Tests for CustomerSupportEnv (single-agent + hierarchical).
"""
import random
import pytest
from fastapi.testclient import TestClient
from env.environment import CustomerSupportEnv, HierarchicalCustomerSupportEnv
from env.models import Action, ActionType, Message
from env.graders import grade as run_grader
from env.graders.task_hard import grade as grade_hard
from env.graders.task_easy import grade as grade_easy
from env.reward_engine import compute_tone_score, compute_loop_penalty

random.seed(42)

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

@pytest.fixture
def hierarchy_env():
    env = HierarchicalCustomerSupportEnv(task="hierarchy_medium")
    env.reset()
    return env

# ── reset() tests ──────────────────────────────────────────────────────────────

def test_reset_returns_observation(easy_env):
    obs = easy_env.reset()
    assert obs.session_id
    assert obs.ticket_id.startswith("TKT-") or obs.ticket_id.startswith("HTKT-")
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
    if not done:
        assert len(obs.conversation_history) >= initial_len + 2

# ── Reward tests ───────────────────────────────────────────────────────────────

def test_reward_is_not_hardcoded_zero(easy_env):
    action = Action(action_type=ActionType.RESPOND, message="I'm sorry to hear about this. I'll process a full refund right away.")
    _, reward, _, _ = easy_env.step(action)
    assert reward.value > 0.0

def test_reward_is_not_hardcoded_one(easy_env):
    action = Action(action_type=ActionType.RESPOND, message="x")
    _, reward, _, _ = easy_env.step(action)
    assert reward.value < 1.0

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
    assert env2._step == 0

# ── Tone score tests ───────────────────────────────────────────────────────────

def test_tone_score_positive_message():
    score = compute_tone_score("Thank you so much! I'm happy to help you resolve this quickly.")
    assert score > 0.6

def test_tone_score_negative_message():
    score = compute_tone_score("This is terrible and unacceptable.")
    assert score < 0.5

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

# ── Grader tests ───────────────────────────────────────────────────────────────

def test_hard_grader_requires_escalation():
    state = {
        "action_log": [
            {"step": 1, "action_type": "respond", "message": "I'll look into this.", "reason": None, "reward": 0.5},
            {"step": 2, "action_type": "close", "message": "Closing.", "reason": None, "reward": 0.3},
        ],
        "ticket": {"priority": "critical", "expected_resolution_type": "escalated_to_engineering",
                   "required_info_before_close": [], "subject": "Production down"},
        "history": [
            {"role": "customer", "content": "CRITICAL: Production is down!"},
            {"role": "agent", "content": "I'll look into this."},
        ],
        "step": 2, "sentiment": 0.0,
    }
    score = grade_hard(state)
    assert score < 0.3

def test_hard_grader_rewards_early_escalation():
    state = {
        "action_log": [{"step": 1, "action_type": "escalate", "message": None,
                        "reason": "SLA breach imminent — production outage requires immediate senior engineering escalation.",
                        "reward": 0.8}],
        "ticket": {"priority": "critical", "expected_resolution_type": "escalated_to_engineering",
                   "required_info_before_close": [], "subject": "Production outage SLA"},
        "history": [
            {"role": "customer", "content": "CRITICAL: Production is down! SLA breach in 30 min!"},
            {"role": "agent", "content": "SLA breach imminent — escalating immediately."},
        ],
        "step": 1, "sentiment": 0.2,
    }
    score = grade_hard(state)
    assert score >= 0.7

def test_easy_grader_rewards_close_with_refund():
    state = {
        "action_log": [
            {"step": 1, "action_type": "respond", "message": "I see the double charge.", "reason": None, "reward": 0.5},
            {"step": 2, "action_type": "close", "message": "I've processed a full refund.", "reason": None, "reward": 0.7},
        ],
        "ticket": {"priority": "medium", "expected_resolution_type": "refund_initiated",
                   "required_info_before_close": ["account_email"]},
        "history": [
            {"role": "customer", "content": "I was charged twice. Account: john@example.com"},
            {"role": "agent", "content": "I see the double charge."},
            {"role": "customer", "content": "Please hurry!"},
            {"role": "agent", "content": "I've processed a full refund for the duplicate charge."},
        ],
        "step": 2, "sentiment": 0.1,
    }
    score = grade_easy(state)
    assert score >= 0.6

# ── Hierarchy env tests ────────────────────────────────────────────────────────

def test_hierarchy_reset(hierarchy_env):
    obs = hierarchy_env.reset()
    assert obs.active_role == "support_agent"
    assert obs.hierarchy_state is not None
    assert obs.hierarchy_state.current_phase == "support_handling"
    assert obs.policy_context  # non-empty policy

def test_hierarchy_l1_step_switches_to_supervisor(hierarchy_env):
    action = Action(action_type=ActionType.RESPOND, message="Hello, I can help with your technical issue.")
    obs, reward, done, info = hierarchy_env.step(action)
    assert not done
    assert obs.active_role == "supervisor"
    assert obs.hierarchy_state.current_phase == "supervisor_review"

def test_hierarchy_supervisor_approve_returns_to_l1(hierarchy_env):
    # L1 acts
    a1 = Action(action_type=ActionType.RESPOND, message="Hello, I can help with your issue.")
    hierarchy_env.step(a1)
    # L2 approves
    a2 = Action(action_type=ActionType.SUPERVISOR_APPROVE, message="Approved: good response.")
    obs, reward, done, info = hierarchy_env.step(a2)
    assert obs.active_role == "support_agent"

def test_hierarchy_supervisor_feedback_returns_to_l1(hierarchy_env):
    a1 = Action(action_type=ActionType.RESPOND, message="Hello.")
    hierarchy_env.step(a1)
    a2 = Action(action_type=ActionType.SUPERVISOR_FEEDBACK, feedback_to_agent="Add more empathy and reference the specific issue.")
    obs, reward, done, info = hierarchy_env.step(a2)
    assert obs.active_role == "support_agent"
    assert obs.supervisor_feedback == "Add more empathy and reference the specific issue."

def test_hierarchy_supervisor_escalate_to_manager(hierarchy_env):
    a1 = Action(action_type=ActionType.RESPOND, message="I see this is urgent.")
    hierarchy_env.step(a1)
    a2 = Action(action_type=ActionType.SUPERVISOR_ESCALATE, reason="Critical SLA breach needs manager.")
    obs, reward, done, info = hierarchy_env.step(a2)
    assert obs.active_role == "manager"
    assert obs.hierarchy_state.current_phase == "manager_override"

def test_hierarchy_manager_resolve_ends_episode(hierarchy_env):
    a1 = Action(action_type=ActionType.RESPOND, message="I see this is urgent.")
    hierarchy_env.step(a1)
    a2 = Action(action_type=ActionType.SUPERVISOR_ESCALATE, reason="Complex case needs manager.")
    hierarchy_env.step(a2)
    a3 = Action(action_type=ActionType.MANAGER_RESOLVE, message="I am escalating to engineering team immediately.")
    obs, reward, done, info = hierarchy_env.step(a3)
    assert done
    assert obs.is_done

def test_hierarchy_manager_send_back(hierarchy_env):
    a1 = Action(action_type=ActionType.RESPOND, message="I see this issue.")
    hierarchy_env.step(a1)
    a2 = Action(action_type=ActionType.SUPERVISOR_ESCALATE, reason="Needs manager review.")
    hierarchy_env.step(a2)
    a3 = Action(action_type=ActionType.MANAGER_SEND_BACK, feedback_to_agent="Offer refund and close.")
    obs, reward, done, info = hierarchy_env.step(a3)
    assert not done
    assert obs.active_role == "support_agent"
    assert obs.manager_directive == "Offer refund and close."

def test_hierarchy_reward_has_role_rewards(hierarchy_env):
    a1 = Action(action_type=ActionType.RESPOND, message="I understand your concern and will help resolve this.")
    _, reward, _, _ = hierarchy_env.step(a1)
    assert "support_agent" in reward.role_rewards
    assert "supervisor" in reward.role_rewards
    assert "manager" in reward.role_rewards

# ── Policy engine tests ────────────────────────────────────────────────────────

def test_policy_engine_drift():
    from env.policy_engine import PolicyEngine
    pe = PolicyEngine(task="hierarchy_hard", category="billing", drift_probability=1.0)
    # Force a specific step
    if pe._scheduled_step:
        event = pe.check_drift(pe._scheduled_step)
        assert event is not None
        assert pe.get_active_changes()  # should have changes

def test_policy_engine_no_drift():
    from env.policy_engine import PolicyEngine
    pe = PolicyEngine(task="easy", category="billing", drift_probability=0.0)
    for s in range(1, 10):
        assert pe.check_drift(s) is None

# ── Action validation tests ────────────────────────────────────────────────────

def test_action_auto_role_assignment():
    a = Action(action_type="supervisor_approve", message="OK")
    assert a.role == "supervisor"
    a2 = Action(action_type="manager_resolve", message="Done.")
    assert a2.role == "manager"
    a3 = Action(action_type="respond", message="Hi")
    assert a3.role == "support_agent"

def test_action_validation_supervisor_feedback():
    with pytest.raises(Exception):
        Action(action_type="supervisor_feedback")  # missing feedback_to_agent

def test_action_validation_manager_resolve():
    with pytest.raises(Exception):
        Action(action_type="manager_resolve")  # missing message

# ── state() tests ──────────────────────────────────────────────────────────────

def test_state_returns_correct_structure(easy_env):
    state = easy_env.state()
    assert "session_id" in state
    assert "task" in state
    assert "ticket" in state
    assert state["task"] == "easy"

def test_hierarchy_state_includes_hierarchy(hierarchy_env):
    state = hierarchy_env.state()
    assert "hierarchy_state" in state
    assert "active_role" in state

# ── E2E Integration tests ─────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def client():
    from server.app import app, _sessions
    _sessions.clear()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    _sessions.clear()

def test_e2e_root(client):
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["name"] == "CustomerSupportEnv"
    assert r.json()["version"] == "2.0.0"

def test_e2e_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"

def test_e2e_reset_easy(client):
    r = client.post("/reset?task=easy")
    assert r.status_code == 200
    obs = r.json()["observation"]
    assert obs["task"] == "easy"
    assert obs["step"] == 0

def test_e2e_reset_hierarchy(client):
    r = client.post("/reset?task=hierarchy_medium")
    assert r.status_code == 200
    obs = r.json()["observation"]
    assert obs["task"] == "hierarchy_medium"
    assert obs["active_role"] == "support_agent"
    assert obs["hierarchy_state"] is not None

def test_e2e_reset_invalid_task(client):
    r = client.post("/reset?task=impossible")
    assert r.status_code == 422

def test_e2e_full_episode_easy(client):
    r = client.post("/reset?task=easy")
    session_id = r.json()["session_id"]

    r = client.post(f"/step?session_id={session_id}", json={
        "action_type": "respond",
        "message": "I can see the double charge. Let me help you get a refund right away.",
    })
    assert r.status_code == 200
    assert r.json()["done"] is False

    r = client.post(f"/step?session_id={session_id}", json={
        "action_type": "close",
        "message": "I have processed a full refund for the duplicate charge. You will see it in 3-5 business days.",
    })
    assert r.status_code == 200
    assert r.json()["done"] is True
    assert "final_score" in r.json()

def test_e2e_full_episode_hard(client):
    r = client.post("/reset?task=hard")
    session_id = r.json()["session_id"]
    r = client.post(f"/step?session_id={session_id}", json={
        "action_type": "escalate",
        "reason": "SLA breach imminent — critical production outage requires immediate senior engineering escalation.",
    })
    assert r.status_code == 200
    assert r.json()["done"] is True
    assert r.json()["final_score"] >= 0.7

def test_e2e_hierarchy_full_episode(client):
    """Full hierarchy episode: L1 → L2 approve → L1 close → L2 approve."""
    r = client.post("/reset?task=hierarchy_easy")
    assert r.status_code == 200
    session_id = r.json()["session_id"]
    obs = r.json()["observation"]
    assert obs["active_role"] == "support_agent"

    # L1 responds
    r = client.post(f"/step?session_id={session_id}", json={
        "action_type": "respond",
        "message": "I understand your billing concern. Let me look into the UPI payment for you right away.",
    })
    assert r.status_code == 200
    obs = r.json()["observation"]
    assert obs["active_role"] == "supervisor"

    # L2 approves
    r = client.post(f"/step?session_id={session_id}", json={
        "action_type": "supervisor_approve",
        "message": "Good empathy and correct approach.",
    })
    assert r.status_code == 200
    assert r.json()["done"] is False
    obs = r.json()["observation"]
    assert obs["active_role"] == "support_agent"

    # L1 closes
    r = client.post(f"/step?session_id={session_id}", json={
        "action_type": "close",
        "message": "I've confirmed your UPI payment was received. The billing has been updated.",
    })
    assert r.status_code == 200
    obs = r.json()["observation"]
    assert obs["active_role"] == "supervisor"

    # L2 approves close
    r = client.post(f"/step?session_id={session_id}", json={
        "action_type": "supervisor_approve",
        "message": "Resolution confirmed, good closure.",
    })
    assert r.status_code == 200
    assert r.json()["done"] is True
    assert "final_score" in r.json()

def test_e2e_hierarchy_escalation_to_manager(client):
    """Hierarchy: L1 → L2 escalates → L3 resolves."""
    r = client.post("/reset?task=hierarchy_hard")
    session_id = r.json()["session_id"]

    r = client.post(f"/step?session_id={session_id}", json={
        "action_type": "respond",
        "message": "I see this is a critical SLA issue. Let me flag this immediately.",
    })
    assert r.status_code == 200

    r = client.post(f"/step?session_id={session_id}", json={
        "action_type": "supervisor_escalate",
        "reason": "Critical SLA breach — needs manager authorization for immediate resolution.",
    })
    assert r.status_code == 200
    obs = r.json()["observation"]
    assert obs["active_role"] == "manager"

    r = client.post(f"/step?session_id={session_id}", json={
        "action_type": "manager_resolve",
        "message": "I am authorizing emergency escalation to engineering. Transaction frozen pending investigation.",
    })
    assert r.status_code == 200
    assert r.json()["done"] is True

def test_e2e_unknown_session(client):
    r = client.post("/step?session_id=nonexistent", json={"action_type": "respond", "message": "Hi"})
    assert r.status_code == 404

def test_e2e_session_cap(client):
    from server.app import _sessions, MAX_SESSIONS
    _sessions.clear()
    import time
    for i in range(MAX_SESSIONS):
        _sessions[f"fake-{i}"] = (None, time.monotonic())
    r = client.post("/reset?task=easy")
    assert r.status_code == 503
    _sessions.clear()

def test_e2e_all_tasks_smoke(client):
    for task in ["easy", "medium", "hard", "hierarchy_easy", "hierarchy_medium", "hierarchy_hard"]:
        r = client.post(f"/reset?task={task}")
        assert r.status_code == 200, f"Reset failed for {task}"
