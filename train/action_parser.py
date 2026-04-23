"""
train/action_parser.py — Parse model output text into a validated Action dict.

Returns None (with a reason string) when the output is invalid so the rollout
collector can assign the invalid_penalty without calling the environment.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional, Tuple

# Valid action types per role
_L1_ACTIONS = {"respond", "escalate", "close", "request_info"}
_L2_ACTIONS = {"supervisor_approve", "supervisor_reject", "supervisor_feedback", "supervisor_escalate"}
_L3_ACTIONS = {"manager_override", "manager_resolve", "manager_send_back"}

_ROLE_ACTIONS: Dict[str, set] = {
    "support_agent": _L1_ACTIONS,
    "supervisor":    _L2_ACTIONS,
    "manager":       _L3_ACTIONS,
}

# Fields required per action_type
_REQUIRED_FIELDS: Dict[str, str] = {
    "respond":              "message",
    "request_info":         "message",
    "close":                "message",
    "escalate":             "reason",
    "supervisor_approve":   "message",
    "supervisor_reject":    "feedback_to_agent",
    "supervisor_feedback":  "feedback_to_agent",
    "supervisor_escalate":  "reason",
    "manager_override":     "message",
    "manager_resolve":      "message",
    "manager_send_back":    "feedback_to_agent",
}

# Fallback actions per role (used when parsing fails)
FALLBACK_ACTIONS: Dict[str, Dict[str, str]] = {
    "support_agent": {
        "action_type": "respond",
        "message": "I apologize for the inconvenience. Let me look into this for you right away.",
    },
    "supervisor": {
        "action_type": "supervisor_approve",
        "message": "Approved.",
    },
    "manager": {
        "action_type": "manager_resolve",
        "message": "I am resolving this escalation directly. Our team will follow up shortly.",
    },
}


def parse_action(
    text: str,
    active_role: str = "support_agent",
) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    """
    Parse model output text into an action dict.

    Returns:
        (action_dict, None)         — valid action
        (None, reason_string)       — invalid, reason explains why
    """
    if not text or not text.strip():
        return None, "empty output"

    # Strip Qwen3 <think>...</think> reasoning blocks BEFORE any other processing.
    # Qwen3 outputs chain-of-thought inside <think> tags that may themselves contain
    # JSON-like fragments — we must remove the entire block or we'll parse the wrong JSON.
    cleaned = re.sub(r"<think>[\s\S]*?</think>", "", text, flags=re.IGNORECASE).strip()

    # Strip markdown code fences
    if cleaned.startswith("```"):
        cleaned = "\n".join(
            line for line in cleaned.split("\n")
            if not line.startswith("```")
        ).strip()

    # Extract first JSON object
    match = re.search(r"\{[\s\S]*?\}", cleaned)
    if not match:
        return None, f"no JSON object found in output: {text[:100]!r}"

    try:
        action = json.loads(match.group(0))
    except json.JSONDecodeError as e:
        return None, f"JSON parse error: {e} — text: {text[:100]!r}"

    if not isinstance(action, dict):
        return None, "parsed value is not a dict"

    action_type = action.get("action_type", "")
    if not action_type:
        return None, "missing action_type field"

    # Check role compatibility
    allowed = _ROLE_ACTIONS.get(active_role, _L1_ACTIONS)
    if action_type not in allowed:
        return None, (
            f"action_type '{action_type}' not valid for role '{active_role}'. "
            f"Allowed: {sorted(allowed)}"
        )

    # Check required field is present and non-empty
    required_field = _REQUIRED_FIELDS.get(action_type)
    if required_field and not (action.get(required_field) or "").strip():
        return None, f"action_type '{action_type}' requires non-empty '{required_field}'"

    return action, None


def get_fallback_action(active_role: str) -> Dict[str, Any]:
    """Return a safe fallback action for a given role."""
    return dict(FALLBACK_ACTIONS.get(active_role, FALLBACK_ACTIONS["support_agent"]))
