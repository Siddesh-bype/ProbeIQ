# AI Interview Agent — Project Plan

## 1. Goal

Build an HTTP service that conducts a realistic, multi-turn technical interview with a candidate from the AI Cohort, grounded in what they *actually* did (from `candidates.json`) and what the curriculum *actually* covers (from `curriculum.json`), and ends with structured feedback. Single endpoint, no auth, session state keyed by `sessionId`.

**Non-goals (explicitly out of scope):** voice, user auth, persistent accounts, long-term history across sessions, mobile.

---

## 2. Data we're working with

**`curriculum.json`**
- `cohort`: string metadata ("AI Cohort · 31 days · 8 modules")
- `modules`: 8 modules, each `{ n, title, days: [startDay, endDay] }`
- `days`: 31 entries, each `{ day, title, type, tools[], objectives[] }`
- `type` ∈ `SETUP, LEARN, BUILD, AI_CORE, OPTIMIZE, SHIP_IT, CAPSTONE`

**`candidates.json`**
- 20 candidates, each `{ member: {id, name, jobRole, yearsExperience, education, status}, missions: [{day, title, passed?, attempts?, skipped?}], signals: {commitDays, missionsCompleted, missionsFirstTry} }`

**Key design implication:** a candidate's `missions` list is already the interview scope. We don't need retrieval or embeddings — it's a direct join: `missions[].day` → `curriculum.days[].objectives/tools`. Skipped/failed missions are *interesting* to probe gently, not to grill on.

---

## 3. Architecture

```
Client
  │  POST /api/interview  { sessionId, candidate }        (turn 1)
  │  POST /api/interview  { sessionId, message }           (turn 2+)
  ▼
FastAPI app
  ├── SessionStore (in-memory dict, sessionId → InterviewState)
  ├── InterviewPlanner   (builds question plan from candidate + curriculum on turn 1)
  ├── InterviewerAgent   (LLM call: next question / follow-up, given state)
  ├── ProgressTracker    (enforces ≥8 questions, ≥4 distinct days, decides `done`)
  └── FeedbackGenerator  (LLM call: final structured feedback from full transcript)
```

No database, no external memory service, no vector store. This is intentionally boring: the spec's state requirement is "remember this one interview," not "remember across interviews" — a dict keyed by `sessionId` covers it completely. If the process restarts mid-interview, that's an acceptable hackathon tradeoff (spec doesn't require durability).

**Stack (adjust to team's fluency):** FastAPI (Python) + one LLM provider via a single `llm_client.py` wrapper, so swapping models later touches one file. Any HTTP framework works equally well — this doesn't need to be Python.

---

## 4. Session state shape

```python
InterviewState = {
  "sessionId": str,
  "candidate": {...},                # raw candidate.json object, stored once
  "plan": [                          # built once, on turn 1
      {"day": 12, "title": "Prompt Engineering Fundamentals",
       "reason": "attempts=4, struggled here", "priority": "high"},
      ...
  ],
  "covered_days": set(),             # updated as interview proceeds
  "transcript": [                    # every turn, both sides
      {"role": "interviewer", "text": "...", "day": 12},
      {"role": "candidate", "text": "..."},
  ],
  "question_count": int,
  "status": "IN_PROGRESS" | "DONE",
}
```

---

## 5. Turn-by-turn logic

### Turn 1 — Start Interview
1. Receive `{sessionId, candidate}`.
2. **Build the plan**: join candidate's `missions` against `curriculum.days`.
   - Sort candidates for questioning by a simple score, e.g.:
     - `high attempts` (≥3) → likely struggled → good for probing depth
     - `AI_CORE` / `BUILD` / `CAPSTONE` day types → weighted over `SETUP`
     - 1–2 `skipped` days → include as a soft "did you get to X?" check-in, not a hard question
   - Pick ~8–10 candidate days from the plan (spec needs ≥8 questions across ≥4 distinct days; padding to 8–10 days gives room for follow-ups to eat into the count without falling short).
3. Store `InterviewState`, return a warm opening `reply`, `done: false`.

### Turn 2..N — Conversation
1. Receive `{sessionId, message}`; look up state (404/error if missing).
2. Append candidate's message to `transcript`.
3. **Decide next move** (single LLM call, given: current day's objectives, candidate's last answer, plan, covered_days so far):
   - If the answer was thin/vague → generate a follow-up on the *same* day (doesn't count as a new "day covered" but does count toward question total).
   - If the answer was solid, or two follow-ups have already happened on this day → move to the next day in the plan.
   - Prompt should quote the specific `objectives`/`tools` for that day so questions stay grounded, not generic.
4. Update `covered_days`, `question_count`, append interviewer's question to `transcript`.
5. Check stop condition (see §6). If not done → return `{reply, done: false}`.

### Final Turn — End Interview
1. Once stop condition is met, make one LLM call over the **full transcript** to produce:
   ```json
   { "summary": "...", "strengths": [...], "gaps": [...], "next": [...] }
   ```
2. Ground `gaps`/`next` in real signals where possible — e.g. reference `missionsFirstTry` vs `missionsCompleted`, or a day the candidate was shaky on live, not just generic advice.
3. Return `{reply: "Interview completed.", done: true, feedback: {...}}`.

---

## 6. Stop condition (server-enforced, not left to the LLM's discretion)

```
done = (question_count >= 8) AND (len(covered_days) >= 4) AND
       (plan mostly exhausted OR question_count >= soft_cap e.g. 14)
```

Enforcing this in code (not just prompting the LLM to "ask 8 questions") guarantees the minimum requirement is always met regardless of model behavior — important since this is graded against a hard spec.

---

## 7. Question selection heuristic (concrete, no ML needed)

For each mission in a candidate's list:

| Signal | Interpretation | Weight |
|---|---|---|
| `attempts >= 3` | struggled, good depth-probe target | high |
| `skipped: true` | gap — ask a lighter, diagnostic question | medium, capped at 1–2 per interview |
| `day type` = AI_CORE/BUILD/CAPSTONE | core engineering content | high |
| `day type` = SETUP | low interview value | low, skip unless plan is thin |
| `attempts == 1`, passed | confident area, good for "explain the tradeoffs" style depth | medium |

This alone satisfies "ask a minimum of 8 questions covering at least 4 different curriculum days" and "adapt naturally" without needing embeddings/RAG — it's a deterministic prioritization over structured data the hackathon already gave us.

---

## 8. API contract (mirrors technical-spec.md exactly)

```
POST /api/interview

# Turn 1
→ { "sessionId": "abc-123", "candidate": { ...candidate.json shape... } }
← { "reply": "...", "done": false }

# Turn 2..N
→ { "sessionId": "abc-123", "message": "..." }
← { "reply": "...", "done": false }

# Final
← { "reply": "Interview completed.", "done": true,
    "feedback": { "summary": "", "strengths": [], "gaps": [], "next": [] } }
```

No auth. Single endpoint. State entirely server-side, addressed by `sessionId`.

---

## 9. Build order (suggested for a time-boxed hackathon)

1. **Skeleton first**: FastAPI app, `/api/interview` route, in-memory session dict, hardcoded reply — confirm the contract works end-to-end before any LLM logic (curl/Postman test).
2. **Plug in the plan builder**: load `curriculum.json` + incoming `candidate`, produce the prioritized day list. Unit-test this in isolation — it's pure data logic, no LLM needed, fastest thing to get right.
3. **Wire the LLM for question/follow-up generation**: one well-structured prompt template that takes `{day objectives, tools, last answer, transcript so far}`.
4. **Stop condition + progress tracking** in code (not prompt-only).
5. **Feedback generation** call at the end.
6. **Polish**: opening message tone, error handling for missing/unknown `sessionId`, restart-safety notes in README.
7. **If time remains**: nicer follow-up logic (e.g. explicit "shallow answer" classifier step before deciding to follow up), a small CLI or React client to demo the flow live for Live Steer.

---

## 10. Risks / things to test before demo day

- **Unknown `sessionId` on a non-turn-1 request** → decide a graceful response (don't crash).
- **Candidate with very few passed missions** (e.g. mostly skipped) → plan builder needs a fallback so it never has fewer than 4 days to draw from.
- **LLM rambling past `done`** → the code-enforced stop condition (§6) protects against this; test it doesn't get bypassed by prompt drift.
- **Latency**: keep each turn to a single LLM call where possible — a multi-agent chain per turn will feel slow live.
- **Determinism for demo**: do one full run-through with a real candidate from `candidates.json` before presenting, not just synthetic testing.

---

## 11. What we deliberately did *not* include, and why

- **No vector DB / RAG**: the candidate's missions already scope the interview precisely; retrieval adds complexity with no accuracy benefit here.
- **No external memory/MCP service for session state**: spec explicitly excludes long-term history; a dict keyed by `sessionId` fully satisfies "maintain context across the interview" for a single session's lifetime. Introducing a third-party dependency here is added risk for a requirement that's already solved for free.
- **No persistent DB**: acceptable per "no persistent user accounts" being out of scope; can be added trivially later (swap dict for Redis/SQLite) if durability across restarts becomes a demo requirement.