"""
Unit tests for planner.py — pure data logic, no LLM, no real curriculum file needed.

Run: python test_planner.py
"""
import json
import pathlib
import sys

# ── Patch curriculum path before importing planner ───────────────────────────

MOCK_CURRICULUM = {
    "days": [
        {"day": 1,  "title": "Environment Setup",    "type": "SETUP",    "tools": ["git"],              "objectives": ["set up env"]},
        {"day": 5,  "title": "Prompt Engineering",   "type": "AI_CORE",  "tools": ["openai", "langchain"], "objectives": ["write prompts", "chain calls"]},
        {"day": 10, "title": "Build a Chatbot",      "type": "BUILD",    "tools": ["fastapi", "redis"], "objectives": ["build api", "manage state"]},
        {"day": 15, "title": "Fine-tuning",          "type": "AI_CORE",  "tools": ["huggingface"],      "objectives": ["fine tune a model"]},
        {"day": 20, "title": "Optimization",         "type": "OPTIMIZE", "tools": ["profiler"],         "objectives": ["reduce latency"]},
        {"day": 25, "title": "Capstone Project",     "type": "CAPSTONE", "tools": ["all"],              "objectives": ["ship a product"]},
        {"day": 30, "title": "Another Setup Day",    "type": "SETUP",    "tools": [],                   "objectives": []},
    ]
}

_tmp = pathlib.Path("_test_curriculum.json")
_tmp.write_text(json.dumps(MOCK_CURRICULUM))

import planner
planner.CURRICULUM_PATH = _tmp
planner._days_by_number = {}  # reset cache so it re-reads our mock file


def _reload():
    """Reset planner cache so each test starts fresh."""
    planner._days_by_number = {}


# ── Helpers ───────────────────────────────────────────────────────────────────

def make_candidate(missions: list[dict]) -> dict:
    return {
        "member": {"id": "1", "name": "Test User", "jobRole": "Dev", "yearsExperience": 2},
        "missions": missions,
        "signals": {"commitDays": 10, "missionsCompleted": len(missions), "missionsFirstTry": 1},
    }


# ── Tests ─────────────────────────────────────────────────────────────────────

def test_high_attempts_scores_highest():
    _reload()
    candidate = make_candidate([
        {"day": 5,  "attempts": 4, "passed": True,  "skipped": False},
        {"day": 10, "attempts": 1, "passed": True,  "skipped": False},
    ])
    plan = planner.build_plan(candidate)
    assert plan[0]["day"] == 5, "High-attempt day should be first"
    assert plan[0]["priority"] == "high"
    print("PASS test_high_attempts_scores_highest")


def test_setup_days_excluded_when_plan_is_fat():
    _reload()
    candidate = make_candidate([
        {"day": 1,  "attempts": 1, "passed": True,  "skipped": False},  # SETUP
        {"day": 5,  "attempts": 1, "passed": True,  "skipped": False},  # AI_CORE
        {"day": 10, "attempts": 1, "passed": True,  "skipped": False},  # BUILD
        {"day": 15, "attempts": 1, "passed": True,  "skipped": False},  # AI_CORE
        {"day": 25, "attempts": 1, "passed": True,  "skipped": False},  # CAPSTONE
    ])
    plan = planner.build_plan(candidate)
    days = [e["day"] for e in plan]
    assert 1 not in days, "SETUP day should be excluded when plan is not thin"
    print("PASS test_setup_days_excluded_when_plan_is_fat")


def test_fallback_pads_to_4_entries():
    _reload()
    # 2 scoreable + 2 SETUP missions — fallback should pad with SETUP days to reach 4
    candidate = make_candidate([
        {"day": 5,  "attempts": 1, "passed": True, "skipped": False},   # AI_CORE
        {"day": 10, "attempts": 1, "passed": True, "skipped": False},   # BUILD
        {"day": 1,  "attempts": 1, "passed": True, "skipped": False},   # SETUP, excluded first pass
        {"day": 30, "attempts": 1, "passed": True, "skipped": False},   # SETUP, excluded first pass
    ])
    plan = planner.build_plan(candidate)
    assert len(plan) >= 4, f"Plan should have >=4 entries, got {len(plan)}"
    setup_days = {e["day"] for e in plan if e["priority"] == "low"}
    assert setup_days, "Fallback should include SETUP days when plan is thin"
    print("PASS test_fallback_pads_to_4_entries")


def test_plan_capped_at_10():
    _reload()
    # Give candidate missions on all 7 mock days
    missions = [{"day": d["day"], "attempts": 2, "passed": True, "skipped": False}
                for d in MOCK_CURRICULUM["days"]]
    candidate = make_candidate(missions)
    plan = planner.build_plan(candidate)
    assert len(plan) <= 10, f"Plan should be capped at 10, got {len(plan)}"
    print("PASS test_plan_capped_at_10")


def test_skipped_mission_gets_medium_priority():
    _reload()
    candidate = make_candidate([
        {"day": 5, "attempts": 0, "passed": False, "skipped": True},
    ])
    plan = planner.build_plan(candidate)
    assert len(plan) >= 1
    assert plan[0]["priority"] == "medium"
    assert "skipped" in plan[0]["reason"]
    print("PASS test_skipped_mission_gets_medium_priority")


def test_unknown_day_skipped_gracefully():
    _reload()
    candidate = make_candidate([
        {"day": 999, "attempts": 1, "passed": True, "skipped": False},  # not in curriculum
        {"day": 5,   "attempts": 1, "passed": True, "skipped": False},
    ])
    plan = planner.build_plan(candidate)
    days = [e["day"] for e in plan]
    assert 999 not in days, "Unknown day should be silently skipped"
    assert 5 in days
    print("PASS test_unknown_day_skipped_gracefully")


def test_plan_entries_have_required_keys():
    _reload()
    candidate = make_candidate([
        {"day": 5,  "attempts": 3, "passed": True, "skipped": False},
        {"day": 10, "attempts": 1, "passed": True, "skipped": False},
    ])
    plan = planner.build_plan(candidate)
    required = {"day", "title", "objectives", "tools", "reason", "priority"}
    for entry in plan:
        missing = required - entry.keys()
        assert not missing, f"Plan entry missing keys: {missing}"
    print("PASS test_plan_entries_have_required_keys")


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_high_attempts_scores_highest,
        test_setup_days_excluded_when_plan_is_fat,
        test_fallback_pads_to_4_entries,
        test_plan_capped_at_10,
        test_skipped_mission_gets_medium_priority,
        test_unknown_day_skipped_gracefully,
        test_plan_entries_have_required_keys,
    ]
    failed = []
    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"FAIL {t.__name__}: {e}")
            failed.append(t.__name__)

    _tmp.unlink(missing_ok=True)  # clean up mock file

    if failed:
        print(f"\n{len(failed)} test(s) failed: {failed}")
        sys.exit(1)
    else:
        print(f"\nAll {len(tests)} tests passed.")
