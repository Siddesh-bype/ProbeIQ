"""
End-to-end integration test for the /api/interview route.
No real LLM needed — patches interviewer_agent and feedback_generator with stubs.

Run: python test_api.py
"""
import sys
import importlib
import types

# ── Stub friend's modules before importing main ───────────────────────────────

def _stub_interviewer(state):
    entry = state["plan"][0] if state["plan"] else None
    if not state["transcript"]:
        return f"Hi {state['candidate']['member']['name']}! Let's start. Tell me about Day {entry['day'] if entry else '?'}."
    return f"Follow-up on Day {entry['day'] if entry else '?'}: can you go deeper?"

def _stub_feedback(state):
    return {"summary": "Good effort.", "strengths": ["clear answers"], "gaps": ["depth"], "next": ["practice more"]}

# Inject stubs so main.py import doesn't need real OpenAI
interviewer_mod = types.ModuleType("interviewer")
interviewer_mod.interviewer_agent = _stub_interviewer
sys.modules["interviewer"] = interviewer_mod

feedback_mod = types.ModuleType("feedback")
feedback_mod.feedback_generator = _stub_feedback
sys.modules["feedback"] = feedback_mod

# Also stub llm_client so planner/progress imports don't fail
llm_mod = types.ModuleType("llm_client")
llm_mod.chat = lambda messages, **kw: "stubbed"
sys.modules["llm_client"] = llm_mod

# ── Now import the app ────────────────────────────────────────────────────────

import json, pathlib

MOCK_CURRICULUM = {
    "days": [
        {"day": d, "title": f"Day {d}", "type": t, "tools": ["tool"], "objectives": ["obj"]}
        for d, t in [(1,"SETUP"),(2,"AI_CORE"),(3,"BUILD"),(4,"CAPSTONE"),(5,"AI_CORE"),(6,"BUILD"),(7,"AI_CORE"),(8,"BUILD")]
    ]
}
_tmp = pathlib.Path("_test_curriculum.json")
_tmp.write_text(json.dumps(MOCK_CURRICULUM))

import planner
planner.CURRICULUM_PATH = _tmp
planner._days_by_number = {}

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

CANDIDATE = {
    "member": {"id": "c1", "name": "Alice", "jobRole": "AI Eng", "yearsExperience": 2, "education": "BS", "status": "active"},
    "missions": [
        {"day": 2, "attempts": 3, "passed": True,  "skipped": False},
        {"day": 3, "attempts": 1, "passed": True,  "skipped": False},
        {"day": 4, "attempts": 1, "passed": True,  "skipped": False},
        {"day": 5, "attempts": 2, "passed": True,  "skipped": False},
        {"day": 6, "attempts": 1, "passed": True,  "skipped": False},
        {"day": 7, "attempts": 1, "passed": False, "skipped": True},
        {"day": 8, "attempts": 1, "passed": True,  "skipped": False},
    ],
    "signals": {"commitDays": 10, "missionsCompleted": 6, "missionsFirstTry": 3},
}

SESSION = "test-session-001"

# ── Tests ─────────────────────────────────────────────────────────────────────

def test_turn1_creates_session():
    r = client.post("/api/interview", json={"sessionId": SESSION, "candidate": CANDIDATE})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["done"] is False
    assert isinstance(body["reply"], str) and len(body["reply"]) > 0
    assert body["feedback"] is None
    print("PASS test_turn1_creates_session")


def test_turn2_continues_interview():
    r = client.post("/api/interview", json={"sessionId": SESSION, "message": "I used LangChain for chaining."})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["done"] is False
    assert body["reply"]
    print("PASS test_turn2_continues_interview")


def test_unknown_session_returns_404():
    r = client.post("/api/interview", json={"sessionId": "no-such-session", "message": "hello"})
    assert r.status_code == 404, f"Expected 404, got {r.status_code}"
    print("PASS test_unknown_session_returns_404")


def test_missing_body_returns_400():
    r = client.post("/api/interview", json={"sessionId": SESSION})
    assert r.status_code == 400, f"Expected 400, got {r.status_code}"
    print("PASS test_missing_body_returns_400")


def test_full_interview_reaches_done():
    sid = "test-full-run"
    # Turn 1
    r = client.post("/api/interview", json={"sessionId": sid, "candidate": CANDIDATE})
    assert r.status_code == 200

    # Drive through enough turns to hit stop condition (>=8 questions, >=4 days)
    done = False
    for i in range(20):
        r = client.post("/api/interview", json={"sessionId": sid, "message": f"Answer {i}: I worked on this using the tools provided."})
        assert r.status_code == 200, r.text
        body = r.json()
        if body["done"]:
            done = True
            assert body["feedback"] is not None
            fb = body["feedback"]
            assert "summary" in fb
            assert "strengths" in fb
            assert "gaps" in fb
            assert "next" in fb
            break

    assert done, "Interview never reached done=true within 20 turns"
    print("PASS test_full_interview_reaches_done")


def test_completed_session_returns_400():
    # Session from previous test is DONE
    r = client.post("/api/interview", json={"sessionId": "test-full-run", "message": "more answers"})
    assert r.status_code == 400
    print("PASS test_completed_session_returns_400")


def test_health_endpoint():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
    print("PASS test_health_endpoint")


# ── Run ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    tests = [
        test_turn1_creates_session,
        test_turn2_continues_interview,
        test_unknown_session_returns_404,
        test_missing_body_returns_400,
        test_full_interview_reaches_done,
        test_completed_session_returns_400,
        test_health_endpoint,
    ]
    failed = []
    for t in tests:
        try:
            t()
        except Exception as e:
            print(f"FAIL {t.__name__}: {e}")
            failed.append(t.__name__)

    _tmp.unlink(missing_ok=True)

    if failed:
        print(f"\n{len(failed)} test(s) failed: {failed}")
        sys.exit(1)
    else:
        print(f"\nAll {len(tests)} tests passed.")
