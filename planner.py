"""
InterviewPlanner — pure data logic, no LLM.

Joins a candidate's missions against curriculum.json days,
scores each by interview value, and returns a prioritized plan
of 8–10 days for the InterviewerAgent to work through.
"""
from __future__ import annotations
import json
from pathlib import Path
from models import PlanEntry

CURRICULUM_PATH = Path("curriculum.json")

# Cached once at startup
_days_by_number: dict[int, dict] = {}

HIGH_VALUE_TYPES = {"AI_CORE", "BUILD", "CAPSTONE"}
LOW_VALUE_TYPES  = {"SETUP"}


def _load_curriculum() -> None:
    global _days_by_number
    if _days_by_number:
        return
    with open(CURRICULUM_PATH, encoding="utf-8") as f:
        data = json.load(f)
    _days_by_number = {d["day"]: d for d in data["days"]}


def _score_mission(mission: dict, day_data: dict) -> tuple[int, str]:
    """
    Return (score, reason) for a mission.
    Higher score = higher interview value = earlier in the plan.
    """
    attempts  = mission.get("attempts", 1) or 1
    skipped   = mission.get("skipped", False)
    passed    = mission.get("passed", True)
    day_type  = day_data.get("type", "")

    if skipped:
        return 2, f"skipped — soft diagnostic question"
    if attempts >= 3:
        return 3, f"attempts={attempts} — struggled, good depth probe"
    if day_type in HIGH_VALUE_TYPES:
        if attempts == 1 and passed:
            return 2, f"first try ({day_type}) — ask for tradeoffs"
        return 2, f"core content ({day_type})"
    if day_type in LOW_VALUE_TYPES:
        return 0, "setup day — low interview value"
    return 1, "completed"


def build_plan(candidate: dict) -> list[PlanEntry]:
    """
    Build and return a prioritized list of PlanEntry dicts for a candidate.
    Always returns at least 4 entries (fallback pads with lower-value days).
    """
    _load_curriculum()

    scored: list[tuple[int, PlanEntry]] = []

    for mission in candidate.get("missions", []):
        day_num  = mission.get("day")
        day_data = _days_by_number.get(day_num)
        if not day_data:
            continue

        score, reason = _score_mission(mission, day_data)
        if score == 0:
            continue  # skip SETUP days in first pass

        entry: PlanEntry = {
            "day":        day_num,
            "title":      day_data["title"],
            "objectives": day_data.get("objectives", []),
            "tools":      day_data.get("tools", []),
            "reason":     reason,
            "priority":   "high" if score == 3 else ("medium" if score == 2 else "low"),
        }
        scored.append((score, entry))

    scored.sort(key=lambda x: x[0], reverse=True)
    plan: list[PlanEntry] = [e for _, e in scored]

    # Fallback: pad with any remaining days so plan always has ≥4 entries
    if len(plan) < 4:
        existing_days = {e["day"] for e in plan}
        for mission in candidate.get("missions", []):
            day_num  = mission.get("day")
            day_data = _days_by_number.get(day_num)
            if not day_data or day_num in existing_days:
                continue
            plan.append({
                "day":        day_num,
                "title":      day_data["title"],
                "objectives": day_data.get("objectives", []),
                "tools":      day_data.get("tools", []),
                "reason":     "fallback (thin plan)",
                "priority":   "low",
            })
            existing_days.add(day_num)
            if len(plan) >= 4:
                break

    return plan[:10]  # cap at 10 days (gives follow-up room without going too long)
