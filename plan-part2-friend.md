# ProbeIQ — Part 2: LLM & Intelligence Layer (FRIEND'S TASKS)

> **Your focus:** Question generation, follow-up logic, feedback generation, and prompt engineering.
> Your teammate handles the skeleton, session state, and plan builder — you plug your LLM functions in once the skeleton is up.

---

## Context (read once, shared with your teammate)

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
  ├──   SessionStore       (in-memory dict — your teammate's code)
  ├──   InterviewPlanner   (plan builder — your teammate's code)
  ├── ★ InterviewerAgent   (LLM: next question / follow-up, given state)
  ├──   ProgressTracker    (stop condition — your teammate's code)
  └── ★ FeedbackGenerator  (LLM: final structured feedback from full transcript)
```

---

## Session State Shape (your teammate builds this — you READ from it)

```python
InterviewState = {
  "sessionId": str,
  "candidate": {...},          # raw candidate object
  "plan": [                    # prioritized list built by InterviewPlanner
      {"day": 12, "title": "Prompt Engineering Fundamentals",
       "objectives": [...], "tools": [...],
       "reason": "attempts=4, struggled here", "priority": "high"},
      ...
  ],
  "covered_days": set(),       # days already asked about
  "transcript": [              # full conversation so far
      {"role": "interviewer", "text": "...", "day": 12},
      {"role": "candidate", "text": "..."},
  ],
  "question_count": int,
  "status": "IN_PROGRESS" | "DONE",
}
```

---

## Your Two Functions (the interface your teammate calls)

```python
# Called every turn — returns the interviewer's next message as a string
def interviewer_agent(state: InterviewState) -> str: ...

# Called once at the end — returns structured feedback dict
def feedback_generator(state: InterviewState) -> dict: ...
# must return: { "summary": str, "strengths": list[str], "gaps": list[str], "next": list[str] }
```

---

## Your Build Steps

### Step 1 — LLM wrapper (`llm_client.py`)
Single file, single function — so swapping providers later touches one place.

```python
# llm_client.py
def chat(messages: list[dict], model: str = "...", temperature: float = 0.7) -> str:
    # call your LLM provider (OpenAI, Anthropic, etc.)
    # messages format: [{"role": "system"|"user"|"assistant", "content": str}]
    ...
```

Pick one provider, hardcode the model for now, wrap the API call. Test it standalone before wiring into the agent.

### Step 2 — InterviewerAgent (question + follow-up generation)

**Decision logic (you implement this):**

At each turn, decide:
- **Follow-up** on the same day if the candidate's last answer was thin/vague (doesn't count as a new `covered_day`, does increment `question_count`)
- **Move to next day** in the plan if:
  - the answer was solid, OR
  - two follow-ups have already happened on this day

How to detect "thin answer": simplest approach — check word count / whether the candidate actually mentioned any of the day's `objectives` or `tools`. A second LLM call works too, but adds latency. Try a heuristic first.

**Prompt template (ground every question in real curriculum data):**

```
System:
You are a skilled technical interviewer conducting an interview for an AI engineering program.
Be professional, curious, and encouraging — not adversarial. Keep questions focused and concise.

User:
Candidate: {name}, {yearsExperience} years experience, role: {jobRole}

Current topic — Day {day}: {title}
Objectives: {objectives}
Tools covered: {tools}
Why this topic: {reason}  ← from the plan (e.g. "attempts=4, struggled here")

Transcript so far:
{last_3_to_5_turns_of_transcript}

Task: Ask ONE focused question about this topic based on the objectives and tools above.
If the candidate just gave a vague or short answer, ask a follow-up that probes deeper.
If moving to a new topic, briefly acknowledge the transition naturally.
Return only the question text, nothing else.
```

**Tips:**
- Pass only the last 3–5 transcript turns, not the full history (keeps latency down)
- Quote `objectives` and `tools` in the prompt so questions stay grounded, not generic
- For `skipped` missions: softer framing — "Did you get a chance to work on X?" rather than grilling

### Step 3 — FeedbackGenerator

Called once, after the stop condition fires. Gets the **full transcript** and **full plan**.

**Prompt template:**

```
System:
You are a program mentor reviewing a technical interview for an AI engineering cohort candidate.
Be honest, specific, and constructive. Ground every observation in evidence from the interview.

User:
Candidate: {name}, {jobRole}, {yearsExperience} years experience
Signals: {missionsCompleted} missions completed, {missionsFirstTry} on first try, {commitDays} commit days

Interview plan covered these topics:
{plan_summary}  ← list of days with priorities and reasons

Full transcript:
{full_transcript}

Produce a JSON object with exactly these keys:
{
  "summary": "2–3 sentence overall assessment",
  "strengths": ["specific strength with evidence from transcript", ...],  // 2–4 items
  "gaps": ["specific gap with evidence", ...],                             // 1–3 items
  "next": ["concrete actionable recommendation", ...]                      // 2–3 items
}

Ground gaps and next steps in real signals — reference specific days, tools, or moments from
the transcript. Avoid generic advice like "practice more."
Return only valid JSON, no markdown, no explanation.
```

Parse the response with `json.loads()` — add a try/except and return a safe fallback dict if the model returns malformed JSON.

---

## Turn-by-Turn Flow (your code path)

### Turn 1 — Opening message
Your teammate calls `interviewer_agent(state)` after building the plan.
- `state["transcript"]` is empty
- `state["plan"]` has the prioritized day list
- Return a warm, personalized opening that introduces the interview and asks the first question about `plan[0]`

### Turn 2..N — Conversation
Your teammate calls `interviewer_agent(state)` after appending the candidate's message.
- Check `covered_days` and `question_count` to decide which plan day you're on
- Decide follow-up vs. advance (see Step 2 logic above)
- Return the next question string

### Final Turn
Your teammate calls `feedback_generator(state)` when the stop condition fires.
- Read the full `transcript` and `plan`
- Return `{ "summary", "strengths", "gaps", "next" }`

---

## Risks You Own

- **LLM rambling past `done`**: your teammate's code-enforced stop condition protects against this — don't try to count questions in your prompt, let the code handle it
- **Latency per turn**: keep each turn to a single LLM call — avoid chaining two calls per turn, it'll feel slow live
- **Malformed feedback JSON**: wrap `json.loads()` in try/except with a safe fallback
- **Generic questions**: always pass `objectives` + `tools` from the plan entry in the prompt — questions that don't reference the curriculum data will feel off

---

## Demo Prep

Before demo day, run one full interview end-to-end with a real candidate from `candidates.json`:
- Confirm the opening message is personalized (not generic)
- Confirm questions reference actual day titles / tools
- Confirm feedback `gaps` cite something real from the transcript
- Confirm `done: true` fires correctly at turn 8–14
