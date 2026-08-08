"""
InterviewerAgent — generates next interview question or follow-up via LLM.

Features:
  1. Persona & Depth Adaptation based on candidate seniority (Junior, Mid, Senior)
  2. Keyword-aware Thin-answer Heuristic
  3. Soft Framing for Skipped Missions
  4. Real-time Rubric & Turn Scoring (1-5 scale)
  5. Memory Compression for long transcripts (>6 turns)
"""
from __future__ import annotations
import re
from models import InterviewState, PlanEntry, TopicScore
from progress import get_current_plan_entry
from llm_client import chat

_SYSTEM = (
    "You are a skilled technical interviewer conducting an interview for an AI engineering program. "
    "Be professional, curious, and encouraging — never adversarial. "
    "Ask ONE focused question at a time. Keep questions concise."
)

_THIN_ANSWER_WORDS = 25
_MAX_FOLLOWUPS_PER_DAY = 2


def _get_candidate_info(candidate_obj: dict) -> tuple[str, str, str | int]:
    """Extract name, jobRole, and yearsExperience safely from raw candidate object."""
    member = candidate_obj.get("member", candidate_obj)
    name = member.get("name", "Candidate")
    role = member.get("jobRole", member.get("role", "Engineer"))
    exp = member.get("yearsExperience", "N/A")
    return name, role, exp


def _get_persona_guidance(candidate_info: tuple[str, str, str | int]) -> str:
    """Return persona and question depth instructions based on candidate experience level."""
    _, role, exp = candidate_info
    try:
        years = int(exp)
    except (ValueError, TypeError):
        years = 3

    if years >= 6:
        return (
            f"Persona Mode: Senior Expert Interviewer. Target Role: {role} ({years} yrs exp). "
            "Probe for system design trade-offs, architecture scalability, failure modes, and production edge cases."
        )
    elif years >= 3:
        return (
            f"Persona Mode: Mid-level Practitioner Interviewer. Target Role: {role} ({years} yrs exp). "
            "Probe for implementation details, framework/API choices, design patterns, and debugging experience."
        )
    else:
        return (
            f"Persona Mode: Encouraging Mentor Interviewer. Target Role: {role} ({years} yrs exp). "
            "Focus on core conceptual clarity, foundational tool usage, step-by-step reasoning, and supportive tone."
        )


def score_turn_response(entry: PlanEntry, candidate_text: str) -> TopicScore:
    """Evaluate candidate response quality on a 1-5 rubric scale for real-time tracking."""
    words = candidate_text.split()
    word_count = len(words)
    keywords = _extract_keywords(entry)
    hits = sum(1 for kw in keywords if kw in candidate_text.lower()) if keywords else 0

    if word_count < 8:
        score = 1
        rating = "shallow"
    elif (hits >= 2 and word_count >= 10) or word_count >= 40:
        score = 5
        rating = "deep"
    elif hits >= 1 or word_count >= 25:
        score = 4
        rating = "adequate"
    elif word_count >= 15:
        score = 3
        rating = "adequate"
    else:
        score = 2
        rating = "shallow"

    return {
        "day": entry["day"],
        "title": entry["title"],
        "score": score,
        "depth_rating": rating,
    }


def _last_candidate_answer(state: InterviewState) -> str:
    """Return the most recent candidate message text."""
    for turn in reversed(state["transcript"]):
        if turn["role"] == "candidate":
            return turn["text"]
    return ""


def _recent_transcript_text(state: InterviewState, max_turns: int = 5) -> str:
    """
    Format transcript history with memory compression.
    If transcript is long (> 6 turns), compresses older turns into a summary header.
    """
    transcript = state["transcript"]
    if not transcript:
        return ""

    if len(transcript) <= max_turns + 2:
        lines = []
        for t in transcript[-max_turns:]:
            speaker = "Interviewer" if t["role"] == "interviewer" else "Candidate"
            day_tag = f" [Day {t['day']}]" if t.get("day") else ""
            lines.append(f"{speaker}{day_tag}: {t['text']}")
        return "\n".join(lines)

    older_turns = transcript[:-max_turns]
    recent_turns = transcript[-max_turns:]

    covered_topics = set()
    for t in older_turns:
        if t.get("day"):
            covered_topics.add(str(t["day"]))

    compressed_header = (
        f"[Memory Summary of Turns 1..{len(older_turns)}: "
        f"Already covered Days {', '.join(sorted(covered_topics)) if covered_topics else 'initial topics'}]"
    )

    lines = [compressed_header]
    for t in recent_turns:
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
            break
    return max(0, count - 1)


def _extract_keywords(entry: PlanEntry) -> set[str]:
    """Extract keywords from a plan entry's objectives and tools."""
    keywords: set[str] = set()
    for tool in entry.get("tools", []):
        keywords.add(tool.lower())
        for word in tool.lower().split():
            if len(word) > 3:
                keywords.add(word)
    for obj in entry.get("objectives", []):
        for word in re.findall(r'[a-zA-Z]+', obj.lower()):
            if len(word) >= 4:
                keywords.add(word)
    return keywords


def _is_thin(text: str, entry: PlanEntry) -> bool:
    """Determine if candidate answer is too thin to move on."""
    words = text.split()
    word_count = len(words)

    if word_count < 8:
        return True
    if word_count >= 50:
        return False

    keywords = _extract_keywords(entry)
    if keywords:
        answer_lower = text.lower()
        hits = sum(1 for kw in keywords if kw in answer_lower)
        if hits >= 1 and word_count >= 15:
            return False
        if hits == 0 and word_count < 35:
            return True

    return word_count < _THIN_ANSWER_WORDS


def _is_skipped_topic(entry: PlanEntry) -> bool:
    """Check if this plan entry is for a mission the candidate skipped."""
    reason = entry.get("reason", "").lower()
    return "skipped" in reason


def should_followup(
    state: InterviewState, last_message: str
) -> tuple[bool, PlanEntry | None, int | None]:
    """
    Decide whether to ask a follow-up on current active topic or advance.
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
    """Return next interviewer message (opening or question/follow-up)."""
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
    """Build prompt for the opening turn with persona guidance."""
    name, role, exp = candidate_info
    persona = _get_persona_guidance(candidate_info)
    skipped_note = ""
    if _is_skipped_topic(entry):
        skipped_note = (
            "\nNote: The candidate skipped this mission. Frame your question gently — "
            "ask if they got a chance to explore the topic, don't assume they completed it."
        )

    return f"""Candidate: {name}, {exp} years experience, role: {role}
{persona}

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
    """Build prompt for turn 2+ with persona guidance and memory compression."""
    name, role, _ = candidate_info
    persona = _get_persona_guidance(candidate_info)

    if follow_up:
        action = (
            "The candidate's last answer was brief or didn't engage with topic specifics. "
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
{persona}

Current topic — Day {entry['day']}: {entry['title']}
Objectives: {', '.join(entry['objectives'][:3])}
Tools: {', '.join(entry['tools'][:4])}
Context: {entry['reason']}

Recent conversation:
{_recent_transcript_text(state)}

Task: {action}
Return only the question text. No preamble."""
