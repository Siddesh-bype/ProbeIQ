"""
InterviewerAgent — generates the next interview question or follow-up via LLM.

Single LLM call per turn. Decides follow-up vs. advance based on:
  1. Answer word count (< 25 words = thin)
  2. Whether the candidate mentioned any of the day's objectives or tools
  3. Max 2 follow-ups per day before auto-advancing

For skipped missions, uses softer framing ("Did you get a chance to…")
rather than grilling.
"""
from __future__ import annotations
import re
from models import InterviewState, PlanEntry
from progress import get_current_plan_entry
from llm_client import chat

_SYSTEM = (
    "You are a skilled technical interviewer conducting an interview for an AI engineering program. "
    "Be professional, curious, and encouraging — never adversarial. "
    "Ask ONE focused question at a time. Keep questions concise."
)

# ── Thin-answer detection ────────────────────────────────────────────────────

# Minimum word count to consider an answer substantive
_THIN_ANSWER_WORDS = 25
# Max follow-ups per day before moving on regardless of answer quality
_MAX_FOLLOWUPS_PER_DAY = 2


def _get_candidate_info(candidate_obj: dict) -> tuple[str, str, str | int]:
    """Extract name, jobRole, and yearsExperience safely from raw candidate object."""
    member = candidate_obj.get("member", candidate_obj)
    name = member.get("name", "Candidate")
    role = member.get("jobRole", member.get("role", "Engineer"))
    exp = member.get("yearsExperience", "N/A")
    return name, role, exp


def _last_candidate_answer(state: InterviewState) -> str:
    """Return the most recent candidate message text."""
    for turn in reversed(state["transcript"]):
        if turn["role"] == "candidate":
            return turn["text"]
    return ""


def _recent_transcript_text(state: InterviewState, n: int = 5) -> str:
    """Format the last n transcript turns for inclusion in the prompt."""
    lines = []
    for t in state["transcript"][-n:]:
        speaker = "Interviewer" if t["role"] == "interviewer" else "Candidate"
        day_tag = f" [Day {t['day']}]" if t.get("day") else ""
        lines.append(f"{speaker}{day_tag}: {t['text']}")
    return "\n".join(lines)


def _followups_on_current_day(state: InterviewState, day: int | None) -> int:
    """Count how many follow-ups have been asked on this day so far."""
    if day is None:
        return 0
    count = 0
    for t in reversed(state["transcript"]):
        if t["role"] == "interviewer" and t.get("day") == day:
            count += 1
        elif t["role"] == "interviewer":
            break  # hit a different day's question — stop counting
    return max(0, count - 1)


def _extract_keywords(entry: PlanEntry) -> set[str]:
    """
    Extract meaningful keywords from a plan entry's objectives and tools.
    Used to check if the candidate's answer actually engages with the topic.
    """
    keywords: set[str] = set()
    for tool in entry.get("tools", []):
        keywords.add(tool.lower())
        for word in tool.lower().split():
            if len(word) > 3:
                keywords.add(word)
    for obj in entry.get("objectives", []):
        for word in re.findall(r'[a-zA-Z]+', obj.lower()):
            if len(word) > 4:
                keywords.add(word)
    return keywords


def _is_thin(text: str, entry: PlanEntry) -> bool:
    """
    Determine if a candidate answer is too thin to move on.
    Checks word count and topic keyword coverage.
    """
    words = text.split()
    word_count = len(words)

    # Answers with < 8 words are always thin (e.g. "yeah", "I did that")
    if word_count < 8:
        return True

    # Answers with >= 50 words are detailed enough
    if word_count >= 50:
        return False

    # Check keyword hits from objectives/tools
    keywords = _extract_keywords(entry)
    if keywords:
        answer_lower = text.lower()
        hits = sum(1 for kw in keywords if kw in answer_lower)
        # If the answer has 1+ keyword hits and is at least 15 words, it's substantive!
        if hits >= 1 and word_count >= 15:
            return False
        # If no keyword hits, answers under 35 words are thin
        if hits == 0 and word_count < 35:
            return True

    # Default fallback based on word count limit
    return word_count < _THIN_ANSWER_WORDS


def _is_skipped_topic(entry: PlanEntry) -> bool:
    """Check if this plan entry is for a mission the candidate skipped."""
    reason = entry.get("reason", "").lower()
    return "skipped" in reason


def should_followup(
    state: InterviewState, last_message: str
) -> tuple[bool, PlanEntry | None, int | None]:
    """
    Decide whether to ask a follow-up on the current active topic or advance.
    Returns (do_followup, active_entry, active_day).
    """
    last_interviewer_turn = next(
        (t for t in reversed(state["transcript"]) if t["role"] == "interviewer"),
        None,
    )
    active_day = last_interviewer_turn.get("day") if last_interviewer_turn else None
    if active_day is None:
        return False, None, None

    active_entry = next((e for e in state["plan"] if e["day"] == active_day), None)
    if not active_entry:
        return False, None, active_day

    followups_done = _followups_on_current_day(state, active_day)
    is_thin_answer = _is_thin(last_message, active_entry)

    do_followup = is_thin_answer and followups_done < _MAX_FOLLOWUPS_PER_DAY
    return do_followup, active_entry, active_day


# ── Prompt builders ──────────────────────────────────────────────────────────

def interviewer_agent(
    state: InterviewState,
    target_entry: PlanEntry | None = None,
    is_followup: bool = False,
) -> str:
    """Return the next interviewer message (opening or question/follow-up)."""
    is_opening = len(state["transcript"]) == 0

    if is_opening:
        entry = target_entry or get_current_plan_entry(state)
        if not entry:
            return "Thank you — we've covered all the topics. Let me put together your feedback."
        candidate_info = _get_candidate_info(state["candidate"])
        prompt = _opening_prompt(candidate_info, entry)
    else:
        if target_entry is not None:
            entry = target_entry
            do_followup = is_followup
        else:
            last_answer = _last_candidate_answer(state)
            do_followup, active_entry, _ = should_followup(state, last_answer)
            entry = active_entry if do_followup else get_current_plan_entry(state)

        if not entry:
            return "Thank you — we've covered all the topics. Let me put together your feedback."

        candidate_info = _get_candidate_info(state["candidate"])
        prompt = _question_prompt(candidate_info, entry, state, do_followup)

    return chat([{"role": "system", "content": _SYSTEM}, {"role": "user", "content": prompt}])


def _opening_prompt(candidate_info: tuple[str, str, str | int], entry: PlanEntry) -> str:
    """Build the prompt for the very first turn — warm greeting + first question."""
    name, role, exp = candidate_info
    skipped_note = ""
    if _is_skipped_topic(entry):
        skipped_note = (
            "\nNote: The candidate skipped this mission. Frame your question gently — "
            "ask if they got a chance to explore the topic, don't assume they completed it."
        )

    return f"""Candidate: {name}, {exp} years experience, role: {role}

Open the interview with a warm, personalized greeting (1–2 sentences), then ask your first question.

First topic — Day {entry['day']}: {entry['title']}
Objectives: {', '.join(entry['objectives'][:3])}
Tools: {', '.join(entry['tools'][:4])}
Context: {entry['reason']}{skipped_note}

Return only the greeting + first question. No preamble."""


def _question_prompt(
    candidate_info: tuple[str, str, str | int],
    entry: PlanEntry,
    state: InterviewState,
    follow_up: bool,
) -> str:
    """Build the prompt for turn 2+ — either a follow-up or a new topic question."""
    name, role, _ = candidate_info
    if follow_up:
        action = (
            "The candidate's last answer was brief or didn't engage with the topic specifics. "
            "Ask a follow-up that probes deeper on the SAME topic. Reference a specific objective or tool."
        )
    else:
        transition = f"Move naturally to the next topic — Day {entry['day']}: {entry['title']}."
        if _is_skipped_topic(entry):
            transition += (
                " The candidate skipped this mission, so frame the question gently — "
                "ask if they got a chance to explore this area, rather than assuming completion."
            )
        else:
            transition += " Briefly acknowledge the transition."
        action = transition

    return f"""Candidate: {name}, {role}

Current topic — Day {entry['day']}: {entry['title']}
Objectives: {', '.join(entry['objectives'][:3])}
Tools: {', '.join(entry['tools'][:4])}
Context: {entry['reason']}

Recent conversation:
{_recent_transcript_text(state)}

Task: {action}
Return only the question text. No preamble."""
