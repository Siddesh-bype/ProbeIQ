"""
In-memory session store keyed by sessionId.

No persistence — if the process restarts mid-interview, sessions are lost.
Acceptable hackathon tradeoff; swap for Redis/SQLite later if needed.
"""
from __future__ import annotations
from models import InterviewState

_sessions: dict[str, InterviewState] = {}


def get(session_id: str) -> InterviewState | None:
    return _sessions.get(session_id)


def save(state: InterviewState) -> None:
    _sessions[state["session_id"]] = state


def exists(session_id: str) -> bool:
    return session_id in _sessions


def delete(session_id: str) -> None:
    _sessions.pop(session_id, None)


def count() -> int:
    return len(_sessions)
