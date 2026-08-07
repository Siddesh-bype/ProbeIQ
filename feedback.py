"""
FeedbackGenerator — produces structured end-of-interview feedback via LLM.

Called once after the stop condition fires. Grounds feedback in real signals
(missionsCompleted, missionsFirstTry, commitDays) and transcript evidence.
"""
from __future__ import annotations
import json
from models import InterviewState
from llm_client import chat

_SYSTEM = (
    "You are a program mentor reviewing a technical interview for an AI engineering cohort. "
    "Be honest, specific, and constructive. Ground every observation in evidence from "
    "the interview transcript. Return only valid JSON — no markdown fences, no explanation."
)

_SAFE_FALLBACK: dict = {
    "summary":   "Interview completed successfully.",
    "strengths": [],
    "gaps":      [],
    "next":      [],
}


def _transcript_text(state: InterviewState) -> str:
    lines = []
    for t in state["transcript"]:
        speaker = "Interviewer" if t["role"] == "interviewer" else "Candidate"
        lines.append(f"{speaker}: {t['text']}")
    return "\n".join(lines)


def _plan_summary(state: InterviewState) -> str:
    lines = []
    for e in state["plan"]:
        covered = "✓" if e["day"] in state["covered_days"] else "–"
        lines.append(f"  {covered} Day {e['day']}: {e['title']} ({e['priority']} priority — {e['reason']})")
    return "\n".join(lines)


def feedback_generator(state: InterviewState) -> dict:
    """Return {summary, strengths, gaps, next} grounded in transcript + signals."""
    member  = state["candidate"]["member"]
    signals = state["candidate"].get("signals", {})

    prompt = f"""Candidate: {member['name']}, {member['jobRole']}, {member['yearsExperience']} years experience
Cohort signals: {signals.get('missionsCompleted', '?')} missions completed, \
{signals.get('missionsFirstTry', '?')} on first try, \
{signals.get('commitDays', '?')} active commit days

Topics covered in this interview:
{_plan_summary(state)}

Full transcript:
{_transcript_text(state)}

Return a JSON object with exactly these keys:
{{
  "summary":   "2–3 sentence overall assessment",
  "strengths": ["specific strength backed by a transcript moment", ...],
  "gaps":      ["specific gap backed by evidence", ...],
  "next":      ["concrete, actionable recommendation", ...]
}}

Rules:
- strengths: 2–4 items
- gaps: 1–3 items
- next: 2–3 items
- Reference specific days, tools, or candidate quotes where possible.
- Avoid generic advice like "practice more" — be specific to this candidate."""

    raw = chat(
        [{"role": "system", "content": _SYSTEM}, {"role": "user", "content": prompt}],
        temperature=0.4,
    )

    # Parse — strip markdown fences if the model ignores instructions
    for candidate_text in (raw, raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()):
        try:
            return json.loads(candidate_text)
        except json.JSONDecodeError:
            continue

    return _SAFE_FALLBACK
