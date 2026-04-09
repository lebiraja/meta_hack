"""
FastAPI server — CustomerSupportEnv.

Production hardening applied:
  - Rate limiting: 30 /reset calls per minute per IP (slowapi)
  - Max session cap: 500 concurrent sessions hard limit
  - Request body size limit: 64KB enforced at middleware level
  - Session TTL: abandoned sessions swept after 30 minutes
  - CORS: open for browser and HF Spaces clients
  - Structured JSON logging via standard logging module
  - Real health check: verifies ticket store is functional
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import asyncio
import logging
import time
import uuid
import structlog
from typing import Literal

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from env.environment import CustomerSupportEnv
from env.graders import grade as run_grader
from env.models import Action
from env.ticket_store import ticket_store

# ── Logging ────────────────────────────────────────────────────────────────────
structlog.configure(processors=[structlog.processors.JSONRenderer()])
logger = structlog.get_logger("customer_support_env")

async def _periodic_sweep():
    while True:
        await asyncio.sleep(300)
        n = _sweep_expired_sessions()
        if n: 
            logger.info("periodic_sweep", removed=n)

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(_periodic_sweep())
    yield
    task.cancel()

# ── Rate limiter ───────────────────────────────────────────────────────────────
limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])

# ── Config ─────────────────────────────────────────────────────────────────────
MAX_SESSIONS = 500          # hard cap on concurrent sessions
SESSION_TTL_SECONDS = 1800  # 30 minutes
MAX_BODY_BYTES = 64 * 1024  # 64KB per request

app = FastAPI(
    title="CustomerSupportEnv",
    version="1.0.0",
    description="OpenEnv-compliant RL environment for customer support agent training.",
    lifespan=lifespan,
)

# ── Middleware ─────────────────────────────────────────────────────────────────

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def enforce_body_size(request: Request, call_next):
    """Reject requests with body larger than MAX_BODY_BYTES."""
    content_length = request.headers.get("content-length")
    if content_length and int(content_length) > MAX_BODY_BYTES:
        logger.warning("body_too_large", content_length=content_length, ip=get_remote_address(request))
        return JSONResponse(
            status_code=413,
            content={"detail": f"Request body too large. Maximum allowed: {MAX_BODY_BYTES} bytes."},
        )
    return await call_next(request)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every request with method, path, status, and duration."""
    start = time.monotonic()
    response = await call_next(request)
    duration_ms = round((time.monotonic() - start) * 1000, 1)
    logger.info(
        "request", 
        method=request.method, 
        path=request.url.path, 
        status=response.status_code,
        duration_ms=duration_ms, 
        ip=get_remote_address(request)
    )
    return response


# ── Session storage ────────────────────────────────────────────────────────────
# Key: session_id → (CustomerSupportEnv, created_at monotonic timestamp)
_sessions: dict[str, tuple[CustomerSupportEnv, float]] = {}

# Storage for completed sessions (replays) and the leaderboard
_completed_sessions: dict[str, dict] = {}
_leaderboard: list[dict] = []

class BenchmarkSubmit(BaseModel):
    agent_name: str
    task_level: str
    total_score: float
    success_rate: float
    avg_steps: float
    sessions_run: int


def _sweep_expired_sessions() -> int:
    """Remove sessions older than SESSION_TTL_SECONDS. Returns count removed."""
    now = time.monotonic()
    expired = [
        sid for sid, (_, created_at) in _sessions.items()
        if now - created_at > SESSION_TTL_SECONDS
    ]
    for sid in expired:
        del _sessions[sid]
    if expired:
        logger.info("session_sweep", expired_count=len(expired), active_sessions=len(_sessions))
    return len(expired)


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
@limiter.limit("30/minute")
def reset(request: Request, task: Literal["easy", "medium", "hard", "nightmare"] = Query(default="easy")):
    """
    Start a new episode. Returns session_id + initial observation.
    Rate limited: 30 resets/minute per IP.
    Hard cap: 500 concurrent sessions.
    """
    _sweep_expired_sessions()

    if len(_sessions) >= MAX_SESSIONS:
        logger.warning("session_cap_hit", active_sessions=len(_sessions))
        raise HTTPException(
            status_code=503,
            detail=f"Server at capacity ({MAX_SESSIONS} concurrent sessions). Try again later.",
        )

    env = CustomerSupportEnv(task=task)
    obs = env.reset()
    _sessions[env.session_id] = (env, time.monotonic())

    logger.info("session_created", session_id=env.session_id, task=task, active_sessions=len(_sessions))

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
    Apply an action to the environment.
    Returns observation, reward, done, info (and final_score on done).
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
        
        # Save replay data
        state["final_score"] = final_score
        _completed_sessions[session_id] = state
        
        # Enforce memory cap on completed sessions (prevent HF Space OOM over thousands of episodes)
        if len(_completed_sessions) > 1000:
            oldest = next(iter(_completed_sessions))
            del _completed_sessions[oldest]
            
        del _sessions[session_id]
        logger.info("session_completed", session_id=session_id, task=env.task, final_score=final_score, steps=obs.step)

    return response


@app.get("/state/{session_id}")
def state(session_id: str):
    """
    Return full internal state of an active session.
    Note: contains conversation history. Do not expose publicly in production.
    """
    env = _get_env(session_id)
    return env.state()


@app.get("/replay/{session_id}")
def replay(session_id: str):
    """
    Return the full internal state and history of a completed session.
    """
    if session_id not in _completed_sessions:
        raise HTTPException(
            status_code=404,
            detail=f"Completed session '{session_id}' not found. Either it's still active, it expired, or it never existed."
        )
    return _completed_sessions[session_id]


@app.get("/leaderboard")
def get_leaderboard():
    """Return the global leaderboard, sorted by score descending."""
    return sorted(_leaderboard, key=lambda x: x["total_score"], reverse=True)


@app.post("/leaderboard/submit")
def submit_leaderboard(submission: BenchmarkSubmit):
    """Submit benchmark results to the public leaderboard."""
    _leaderboard.append(submission.model_dump())
    
    # Sort and cap to top 100 entries to prevent memory leaks
    _leaderboard.sort(key=lambda x: x["total_score"], reverse=True)
    if len(_leaderboard) > 100:
        _leaderboard[:] = _leaderboard[:100]
        
    return {"status": "success", "message": "Benchmark submitted to leaderboard."}


@app.post("/benchmark")
def run_benchmark():
    """
    Placeholder for triggering an automated benchmark run.
    """
    return {"status": "acknowledged", "message": "Benchmark started. Use /leaderboard to check results later."}


@app.get("/health")
def health():
    """
    Real health check — verifies ticket store is functional.
    Returns 503 if the environment cannot be instantiated.
    """
    try:
        ticket_store.get_random_by_task("easy")
        env_ok = True
    except Exception as exc:
        logger.error("health_check_failed", error=str(exc))
        env_ok = False

    if not env_ok:
        raise HTTPException(status_code=503, detail="Environment not functional")

    return {
        "status": "ok",
        "active_sessions": len(_sessions),
        "session_cap": MAX_SESSIONS,
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


def main():
    """Entry point for [project.scripts] and multi-mode deployment."""
    import uvicorn
    uvicorn.run(
        "server.app:app",
        host="0.0.0.0",
        port=7860,
        timeout_keep_alive=30,
    )


if __name__ == "__main__":
    main()
