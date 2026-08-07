from __future__ import annotations
from typing import TypedDict, Literal, Optional


class PlanEntry(TypedDict):
    day: int
    title: str
    objectives: list[str]
    tools: list[str]
    reason: str
    priority: Literal["high", "medium", "low"]


class TranscriptTurn(TypedDict):
    role: Literal["interviewer", "candidate"]
    text: str
    day: Optional[int]  # set for interviewer turns that open a new topic


class InterviewState(TypedDict):
    session_id: str
    candidate: dict
    plan: list[PlanEntry]
    covered_days: set  # set[int] — days already explored
    transcript: list[TranscriptTurn]
    question_count: int
    status: Literal["IN_PROGRESS", "DONE"]
