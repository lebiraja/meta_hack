"""
FastAPI server — CustomerSupportEnv.

One server. Used by Docker deployment AND by inference.py (HTTP client).
Session isolation via session_id — NO global mutable state per-request.

Fixes applied:
  - CORS middleware (Fix 4)
  - Session TTL: abandoned sessions expire after SESSION_TTL_SECONDS (Fix 3)
  - Real health check: verifies ticket store is functional (Fix 6)
"""

from __future__ import annotations

import time
import uuid
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from env.environment import CustomerSupportEnv
from env.graders import grade as run_grader
from env.models import Action
from env.ticket_store import ticket_store

# Sessions older than this (seconds) are swept on the next request
SESSION_TTL_SECONDS = 30 * 60  # 30 minutes

app = FastAPI(
    title="CustomerSupportEnv",
    version="1.0.0",
    description="OpenEnv-compliant RL environment for customer support agent training.",
)

# ── Fix 4: CORS ────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Session storage ────────────────────────────────────────────────────────────
# Key: session_id → (CustomerSupportEnv, created_at_timestamp)
_sessions: dict[str, tuple[CustomerSupportEnv, float]] = {}


def _sweep_expired_sessions() -> None:
    """Fix 3: Remove sessions that have been idle longer than SESSION_TTL_SECONDS."""
    now = time.monotonic()
    expired = [
        sid for sid, (_, created_at) in _sessions.items()
        if now - created_at > SESSION_TTL_SECONDS
    ]
    for sid in expired:
        del _sessions[sid]


def _get_env(session_id: str) -> CustomerSupportEnv:
    """Look up a session, sweeping expired ones first."""
    _sweep_expired_sessions()
    entry = _sessions.get(session_id)
    if entry is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found. Call /reset to start a new episode.",
        )
    return entry[0]


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.post("/reset")
def reset(task: Literal["easy", "medium", "hard"] = Query(default="easy")):
    """
    Start a new episode. Returns a session_id and the initial observation.
    Each call creates an isolated environment instance.
    """
    _sweep_expired_sessions()
    env = CustomerSupportEnv(task=task)
    obs = env.reset()
    _sessions[env.session_id] = (env, time.monotonic())

    return {
        "session_id": env.session_id,
        "observation": obs.model_dump(),
    }


@app.post("/step")
def step(
    session_id: str = Query(..., description="Session ID returned by /reset"),
    action: Action = ...,
):
    """
    Apply an action to the environment. Returns observation, reward, done, info.
    Cleans up session state when episode is done.
    """
    env = _get_env(session_id)

    try:
        obs, reward, done, info = env.step(action)
    except RuntimeError as exc:
        raise HTTPException(status_code=409, detail=str(exc))

    response = {
        "observation": obs.model_dump(),
        "reward": reward.model_dump(),
        "done": done,
        "info": info,
    }

    if done:
        state = env.state()
        try:
            final_score = run_grader(env.task, state)
        except Exception:
            final_score = reward.value
        response["final_score"] = final_score
        del _sessions[session_id]

    return response


@app.get("/state/{session_id}")
def state(session_id: str):
    """Return full internal state of an active session."""
    env = _get_env(session_id)
    return env.state()


@app.get("/health")
def health():
    """
    Fix 6: Real health check — verifies ticket store is functional.
    Returns 503 if the environment cannot be instantiated.
    """
    try:
        ticket_store.get_random_by_task("easy")
        env_ok = True
    except Exception:
        env_ok = False

    if not env_ok:
        raise HTTPException(status_code=503, detail="Environment not functional")

    return {
        "status": "ok",
        "active_sessions": len(_sessions),
        "env_functional": True,
    }


@app.get("/")
def root():
    return {
        "name": "CustomerSupportEnv",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": ["/reset", "/step", "/state/{session_id}", "/health"],
    }
