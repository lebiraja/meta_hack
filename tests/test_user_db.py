"""
tests/test_user_db.py — Unit tests for DB-backed query actions.

Tests:
  - DB lookup (hit / miss)
  - query action updates observation.retrieved_data
  - not_found handling
  - query does NOT trigger supervisor review (active_role stays support_agent)
  - hallucination_penalty fires on fabricated facts
  - grounded_response_bonus fires on verbatim cited data
"""

import pytest
from env.user_db import get_user, get_order
from env.models import Action, ActionType
from env.environment import HierarchicalCustomerSupportEnv


# ── DB lookup ──────────────────────────────────────────────────────────────────

def test_get_user_hit():
    result = get_user("sarah.jones@email.com")
    assert isinstance(result, dict)
    assert result["name"] == "Sarah Jones"
    assert result["domain"] == "food_delivery"


def test_get_user_miss():
    result = get_user("nobody@notexist.com")
    assert result == "not_found"


def test_get_order_hit():
    result = get_order("ORD-FD-8821")
    assert isinstance(result, dict)
    assert result["amount"] == 499
    assert result["restaurant"] == "Biryani House"


def test_get_order_miss():
    result = get_order("ORD-FAKE-0000")
    assert result == "not_found"


def test_get_order_case_insensitive():
    result = get_order("ord-fd-8821")
    assert isinstance(result, dict)
    assert result["amount"] == 499


# ── Query action updates observation ──────────────────────────────────────────

def test_query_action_updates_user_observation():
    env = HierarchicalCustomerSupportEnv(task="multi_domain")
    env.reset()

    action = Action(action_type="query_user_profile", email="sarah.jones@email.com")
    obs, reward, done, info = env.step(action)

    assert "sarah.jones@email.com" in obs.retrieved_data["users"]
    user_result = obs.retrieved_data["users"]["sarah.jones@email.com"]
    assert isinstance(user_result, dict)
    assert user_result["name"] == "Sarah Jones"


def test_query_action_updates_order_observation():
    env = HierarchicalCustomerSupportEnv(task="multi_domain")
    env.reset()

    action = Action(action_type="query_order_details", order_id="ORD-FD-8821")
    obs, reward, done, info = env.step(action)

    assert "ORD-FD-8821" in obs.retrieved_data["orders"]
    order_result = obs.retrieved_data["orders"]["ORD-FD-8821"]
    assert isinstance(order_result, dict)
    assert order_result["amount"] == 499


def test_query_action_not_found_handling():
    env = HierarchicalCustomerSupportEnv(task="multi_domain")
    env.reset()

    action = Action(action_type="query_user_profile", email="ghost@notreal.com")
    obs, reward, done, info = env.step(action)

    assert obs.retrieved_data["users"]["ghost@notreal.com"] == "not_found"
    # Episode should still be alive (agent can continue)
    assert not done


def test_query_does_not_trigger_supervisor():
    env = HierarchicalCustomerSupportEnv(task="multi_domain")
    env.reset()

    # multi_domain uses active_levels=[1] so supervisor never activates,
    # but verify active_role stays support_agent after a query
    action = Action(action_type="query_order_details", order_id="ORD-FD-8821")
    obs, reward, done, info = env.step(action)

    assert obs.active_role == "support_agent"


def test_query_data_accumulates_across_steps():
    env = HierarchicalCustomerSupportEnv(task="multi_domain")
    env.reset()

    env.step(Action(action_type="query_user_profile", email="sarah.jones@email.com"))
    obs, _, _, _ = env.step(Action(action_type="query_order_details", order_id="ORD-FD-8821"))

    assert "sarah.jones@email.com" in obs.retrieved_data["users"]
    assert "ORD-FD-8821" in obs.retrieved_data["orders"]


# ── Reward signals ─────────────────────────────────────────────────────────────

def test_hallucination_penalty():
    from env.reward_engine import compute_db_signals
    from env.models import Message

    ticket = {
        "customer_email": "sarah.jones@email.com",
        "related_order_ids": ["ORD-FD-8821"],
        "required_info_before_close": [],
    }
    retrieved_data = {
        "users": {"sarah.jones@email.com": {"name": "Sarah Jones", "amount": None}},
        "orders": {},
    }
    history = [
        Message(role="customer", content="I need help with my order"),
    ]
    # Agent claims a ₹999 amount that was never in DB or customer message
    action = Action(
        action_type="respond",
        message="I can see your ₹999 order is being processed.",
    )

    signals = compute_db_signals(action, ticket, history, retrieved_data)
    assert signals["hallucination_penalty"] < 0, "Expected hallucination penalty for fabricated amount"


def test_grounded_response_bonus():
    from env.reward_engine import compute_db_signals
    from env.models import Message

    ticket = {
        "customer_email": "sarah.jones@email.com",
        "related_order_ids": ["ORD-FD-8821"],
        "required_info_before_close": [],
    }
    retrieved_data = {
        "users": {},
        "orders": {
            "ORD-FD-8821": {
                "amount": 499,
                "restaurant": "Biryani House",
                "status": "delivered",
            }
        },
    }
    history = [
        Message(role="customer", content="My order from Biryani House was not delivered"),
    ]
    # Agent cites exact data from retrieved_data
    action = Action(
        action_type="respond",
        message="I can see your order from Biryani House for ₹499 is marked as delivered. Let me initiate a refund.",
    )

    signals = compute_db_signals(action, ticket, history, retrieved_data)
    assert signals["grounded_response_bonus"] > 0, "Expected grounded response bonus for citing DB data"


def test_query_match_bonus():
    from env.reward_engine import compute_db_signals
    from env.models import Message

    ticket = {
        "customer_email": "sarah.jones@email.com",
        "related_order_ids": ["ORD-FD-8821"],
        "required_info_before_close": [],
    }
    retrieved_data = {"users": {}, "orders": {}}
    history = [
        Message(role="customer", content="My email is sarah.jones@email.com"),
    ]
    action = Action(action_type="query_user_profile", email="sarah.jones@email.com")

    signals = compute_db_signals(action, ticket, history, retrieved_data)
    assert signals["query_match_bonus"] > 0, "Expected query match bonus for correct email query"


def test_no_signals_without_queries():
    from env.reward_engine import compute_db_signals
    from env.models import Message

    ticket = {"customer_email": "", "related_order_ids": [], "required_info_before_close": []}
    retrieved_data = {"users": {}, "orders": {}}
    history = [Message(role="customer", content="Hello")]
    action = Action(action_type="respond", message="How can I help you today?")

    signals = compute_db_signals(action, ticket, history, retrieved_data)
    # With no DB data and no fabricated facts, all signals should be zero
    assert signals["query_match_bonus"] == 0.0
    assert signals["grounded_response_bonus"] == 0.0
    assert signals["hallucination_penalty"] == 0.0
