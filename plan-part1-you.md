# ProbeIQ — Part 1: Backend & Data Layer (YOUR TASKS)

> **Your focus:** The skeleton, session state, plan builder, stop condition, and API contract.
> Your friend handles the LLM calls once you wire the endpoints they can plug into.

---

## Context (read once, shared with your friend)

**Goal:** HTTP service, single endpoint `POST /api/interview`, no auth, session state keyed by `sessionId`.

**Data:**
- `curriculum.json` — 8 modules, 31 days, each day has `type`, `tools[]`, `objectives[]`
- `candidates.json` — 20 candidates, each has `missions[{day, passed?, attempts?, skipped?}]` and `signals`
- A candidate's `missions[].day` joins directly to `curriculum.days[]` — no RAG, no embeddings needed.

---

## Architecture (your half highlighted)

```
Client
  │  POST /api/interview  { sessionId, candidate }        (turn 1)
  │  POST /api/interview  { sessionId, message }           (turn 2+)
  ▼
FastAPI app
  ├── ★ SessionStore       (in-memory dict, sessionId → InterviewState)
  ├── ★ InterviewPlanner   (builds question plan from candidate + curriculum)
  ├──   InterviewerAgent   (LLM — your friend's code)
  ├── ★ ProgressTracker    (enforces ≥8 questions, ≥4 distinct days, decides `done`)
  └──   FeedbackGenerator  (LLM — your friend's code)
```

---

## Session State Shape (you own this)

```python
InterviewState = {
  "sessionId": str,
  "candidate": {...},          # raw candidate object, stored once on turn 1
  "plan": [                    # built once by InterviewPlanner
      {"day": 12, "title": "Prompt Engineering Fundamentals",
       "reason": "attempts=4, struggled here", "priority": "high"},
      ...
  ],
  "covered_days": set(),       # you update this each turn
  "transcript": [              # every turn, both sides — your friend appends to this too
      {"role": "interviewer", "text": "...", "day": 12},
      {"role": "candidate", "text": "..."},
  ],
  "question_count": int,
  "status": "IN_PROGRESS" | "DONE",
}
```

---

## API Contract (you wire this up)

```
POST /api/interview

# Turn 1 — you receive this, build state, call friend's InterviewerAgent for the opener
→ { "sessionId": "abc-123", "candidate": { ...candidate.json shape... } }
← { "reply": "...", "done": false }

# Turn 2..N — you look up state, append message, call friend's InterviewerAgent
→ { "sessionId": "abc-123", "message": "..." }
← { "reply": "...", "done": false }

# Final — stop condition fires, you call friend's FeedbackGenerator
← { "reply": "Interview completed.", "done": true,
    "feedback": { "summary": "", "strengths": [], "gaps": [], "next": [] } }
```

---

## Your Build Steps

### Step 1 — Skeleton (do this first, before any LLM logic)
- FastAPI app with `POST /api/interview`
- In-memory `sessions: dict[str, InterviewState]`
- Hardcoded `reply = "Hello, let's start!"` — just confirm the contract works end-to-end
- Test with curl: turn 1 with `{sessionId, candidate}`, turn 2 with `{sessionId, message}`

### Step 2 — InterviewPlanner
Pure data logic, no LLM — fastest to unit-test in isolation.

**Priority scoring per mission:**

| Signal | Interpretation | Priority |
|---|---|---|
| `attempts >= 3` | struggled → probe depth | `high` |
| `skipped: true` | gap → soft check-in | `medium`, max 1–2 per interview |
| day `type` = `AI_CORE` / `BUILD` / `CAPSTONE` | core content | `high` |
| day `type` = `SETUP` | low value | `low`, skip unless plan is thin |
| `attempts == 1`, passed | confident → ask for tradeoffs | `medium` |

- Join `missions[].day` → `curriculum.days[day]` to get `objectives`, `tools`, `type`
- Sort by priority, pick top 8–10 days (gives room for follow-ups)
- Fallback: if candidate has very few passed missions, pad with any available days so plan always has ≥ 4 days
- Return list of `{day, title, objectives, tools, reason, priority}`

### Step 3 — ProgressTracker & Stop Condition
Enforce in code — never rely on the LLM to count questions correctly.

```python
def is_done(state: InterviewState) -> bool:
    SOFT_CAP = 14
    return (
        state["question_count"] >= 8
        and len(state["covered_days"]) >= 4
        and (plan_mostly_exhausted(state) or state["question_count"] >= SOFT_CAP)
    )
```

Update `covered_days` and `question_count` every turn in the route handler.

### Step 4 — Route Handler (glue layer)
Turn 1:
1. Parse `{sessionId, candidate}`
2. Call `InterviewPlanner` → store plan in `InterviewState`
3. Call friend's `InterviewerAgent(state)` → get opening message
4. Return `{reply, done: false}`

Turn 2+:
1. Look up `sessionId` → 404 if missing (don't crash)
2. Append candidate message to `transcript`
3. Call `is_done(state)` — if true, call friend's `FeedbackGenerator` and return `{done: true, feedback}`
4. Otherwise call friend's `InterviewerAgent(state)` → get next question
5. Update `covered_days`, `question_count`
6. Return `{reply, done: false}`

---

## Risks You Own

- **Unknown sessionId on turn 2+** → return a clear 404/error, don't crash
- **Candidate with very few missions** → plan builder fallback so ≥ 4 days always available
- **Stop condition bypassed by prompt drift** → your code-enforced check prevents this; don't skip it

---

## Interface Contract with Your Friend

Tell your friend their two functions need this signature:

```python
# question/follow-up — returns a string (the interviewer's next message)
def interviewer_agent(state: InterviewState) -> str: ...

# final feedback — returns a dict
def feedback_generator(state: InterviewState) -> dict: ...
# returns: { "summary": str, "strengths": list, "gaps": list, "next": list }
```

They read from `state["transcript"]`, `state["plan"]`, `state["covered_days"]` — you keep those up to date.
