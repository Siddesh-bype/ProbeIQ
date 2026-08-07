"""
ProgressTracker — enforces stop condition in code, not via LLM prompting.

This guarantees the spec's minimum requirements (≥8 questions, ≥4 distinct days)
regardless of model behavior or prompt drift.
"""
from __future__ import annotations
from models import InterviewState, PlanEntry

MIN_QUESTIONS = 8
MIN_DAYS = 4
SOFT_CAP = 14  # hard ceiling regardless of plan state


def is_done(state: InterviewState) -> bool:
    """Return True when the interview should end."""
    plan_exhausted = len(state["covered_days"]) >= len(state["plan"])
    return (
        state["question_count"] >= MIN_QUESTIONS
        and len(state["covered_days"]) >= MIN_DAYS
        and (plan_exhausted or state["question_count"] >= SOFT_CAP)
    )


def get_current_plan_entry(state: InterviewState) -> PlanEntry | None:
    """
    Return the next plan entry that hasn't been covered yet.
    Falls back to the first entry if all days are covered but
    stop condition hasn't fired (edge case with very short plans).
    """
    for entry in state["plan"]:
        if entry["day"] not in state["covered_days"]:
            return entry
    # All covered but still going — cycle from top (shouldn't happen normally)
    return state["plan"][0] if state["plan"] else None
