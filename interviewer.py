"""
InterviewerAgent — generates the next interview question or follow-up via LLM.

Single LLM call per turn. Decides follow-up vs. advance based on answer length
(simple heuristic — fast, zero latency overhead vs. a second classifier call).
"""
from __future__ import annotations
from models import InterviewState, PlanEntry
from progress import get_current_plan_entry
from llm_client import chat

_SYSTEM = (
    "You are a skilled technical interviewer for an AI engineering program. "
    "Be professional, curious, and encouraging — never adversarial. "
    "Ask ONE focused question at a time. Keep questions concise."
)

# Minimum word count to consider an answer substantive
_THIN_ANSWER_WORDS = 20
# Max follow-ups per day before moving on regardless of answer quality
_MAX_FOLLOWUPS_PER_DAY = 2


def _last_candidate_answer(state: InterviewState) -> str:
    for turn in reversed(state["transcript"]):
        if turn["role"] == "candidate":
            return turn["text"]
    return ""


def _recent_transcript_text(state: InterviewState, n: int = 6) -> str:
    lines = []
    for t in state["transcript"][-n:]:
        speaker = "Interviewer" if t["role"] == "interviewer" else "Candidate"
        lines.append(f"{speaker}: {t['text']}")
    return "\n".join(lines)


def _followups_on_current_day(state: InterviewState, day: int) -> int:
    """Count how many consecutive interviewer turns targeted this day."""
    count = 0
    for t in reversed(state["transcript"]):
        if t["role"] == "interviewer" and t.get("day") == day:
            count += 1
        elif t["role"] == "interviewer":
            break
    return count


def _is_thin(text: str) -> bool:
    return len(text.split()) < _THIN_ANSWER_WORDS


def interviewer_agent(state: InterviewState) -> str:
    """Return the next interviewer message (opening or question/follow-up)."""
    entry = get_current_plan_entry(state)
    if not entry:
        return "Thank you — we've covered all the topics. Let me put together your feedback."

    candidate = state["candidate"]["member"]
    is_opening = len(state["transcript"]) == 0

    if is_opening:
        prompt = _opening_prompt(candidate, entry)
    else:
        last_answer = _last_candidate_answer(state)
        followups_done = _followups_on_current_day(state, entry["day"])
        do_followup = _is_thin(last_answer) and followups_done < _MAX_FOLLOWUPS_PER_DAY
        prompt = _question_prompt(candidate, entry, state, do_followup)

    return chat([{"role": "system", "content": _SYSTEM}, {"role": "user", "content": prompt}])


def _opening_prompt(candidate: dict, entry: PlanEntry) -> str:
    return f"""Candidate: {candidate['name']}, {candidate['yearsExperience']} years experience, role: {candidate['jobRole']}

Open the interview with a warm, personalized greeting (1–2 sentences), then ask your first question.

First topic — Day {entry['day']}: {entry['title']}
Objectives: {', '.join(entry['objectives'][:3])}
Tools: {', '.join(entry['tools'][:4])}
Context: {entry['reason']}

Return only the greeting + first question. No preamble."""


def _question_prompt(candidate: dict, entry: PlanEntry, state: InterviewState, follow_up: bool) -> str:
    action = (
        "The candidate's last answer was brief. Ask a follow-up that probes deeper on the SAME topic."
        if follow_up
        else f"Move naturally to the next topic — Day {entry['day']}: {entry['title']}"
    )
    return f"""Candidate: {candidate['name']}, {candidate['jobRole']}

Current topic — Day {entry['day']}: {entry['title']}
Objectives: {', '.join(entry['objectives'][:3])}
Tools: {', '.join(entry['tools'][:4])}
Context: {entry['reason']}

Recent conversation:
{_recent_transcript_text(state)}

Task: {action}
Return only the question text. No preamble."""
