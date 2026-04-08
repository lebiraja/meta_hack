"""
FastAPI server — CustomerSupportEnv.

One server. Used by Docker deployment AND by inference.py (HTTP client).
Session isolation via session_id — NO global mutable state per-request.
"""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import JSONResponse

from env.environment import CustomerSupportEnv
from env.graders import grade as run_grader
from env.models import Action, Observation

app = FastAPI(
    title="CustomerSupportEnv",
    version="1.0.0",
    description="OpenEnv-compliant RL environment for customer support agent training.",
)

# Per-session environment storage — key: session_id string
# This dict is the ONLY mutable global. It stores env objects, not state dicts.
_sessions: dict[str, CustomerSupportEnv] = {}


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.post("/reset")
def reset(task: Literal["easy", "medium", "hard"] = Query(default="easy")):
    """
    Start a new episode. Returns a session_id and the initial observation.
    Each call creates an isolated environment instance.
    """
    env = CustomerSupportEnv(task=task)
    obs = env.reset()
    _sessions[env.session_id] = env

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
    env = _sessions.get(session_id)
    if env is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found. Call /reset to start a new episode.",
        )

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
        # Run task grader for final score
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
    env = _sessions.get(session_id)
    if env is None:
        raise HTTPException(
            status_code=404,
            detail=f"Session '{session_id}' not found.",
        )
    return env.state()


@app.get("/health")
def health():
    """Health check — used by Docker HEALTHCHECK and hackathon validator."""
    return {"status": "ok", "active_sessions": len(_sessions)}


@app.get("/")
def root():
    return {
        "name": "CustomerSupportEnv",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
        "endpoints": ["/reset", "/step", "/state/{session_id}", "/health"],
    }
