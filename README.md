# ProbeIQ — AI Interview Agent

Single-endpoint HTTP service that conducts a realistic multi-turn technical interview, grounded in what the candidate actually did (from `candidates.json`) and what the curriculum covers (`curriculum.json`), ending with structured feedback.

---

## Quickstart

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure environment
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 3. Add your data files
# Place candidates.json and curriculum.json in the project root

# 4. Run the server
python main.py
# or: uvicorn main:app --reload
```

Server runs at `http://localhost:8000`.

---

## File Structure

```
ProbeIQ/
├── main.py           # FastAPI app + /api/interview route
├── models.py         # InterviewState TypedDict + related types
├── session_store.py  # In-memory session dict
├── planner.py        # InterviewPlanner — pure data logic, no LLM
├── progress.py       # ProgressTracker + stop condition (code-enforced)
├── llm_client.py     # LLM wrapper — swap provider here
├── interviewer.py    # InterviewerAgent — question/follow-up generation
├── feedback.py       # FeedbackGenerator — end-of-interview feedback
├── curriculum.json   # (you provide)
├── candidates.json   # (you provide)
├── requirements.txt
└── .env.example
```

---

## API

**Single endpoint:** `POST /api/interview`

### Turn 1 — Start
```json
// Request
{ "sessionId": "abc-123", "candidate": { /* candidate object from candidates.json */ } }

// Response
{ "reply": "Hi Alex! Let's start...", "done": false }
```

### Turn 2..N — Conversation
```json
// Request
{ "sessionId": "abc-123", "message": "I used LangChain to chain prompts together..." }

// Response
{ "reply": "Interesting — can you walk me through...", "done": false }
```

### Final Turn
```json
// Response
{
  "reply": "Thank you — that's the end of our interview.",
  "done": true,
  "feedback": {
    "summary": "...",
    "strengths": ["..."],
    "gaps": ["..."],
    "next": ["..."]
  }
}
```

---

## Quick curl test

```bash
# Turn 1
curl -s -X POST http://localhost:8000/api/interview \
  -H "Content-Type: application/json" \
  -d '{"sessionId":"test-1","candidate":{...}}' | jq .

# Turn 2
curl -s -X POST http://localhost:8000/api/interview \
  -H "Content-Type: application/json" \
  -d '{"sessionId":"test-1","message":"I worked on prompt chaining using LangChain"}' | jq .

# Health check
curl http://localhost:8000/health
```

---

## Stop condition

Enforced in `progress.py`, not by the LLM:
```
done = (question_count ≥ 8) AND (covered_days ≥ 4) AND (plan exhausted OR question_count ≥ 14)
```

---

## Swapping the LLM provider

Edit `llm_client.py` only. Everything else is provider-agnostic.
Set `LLM_MODEL` in `.env` to change the model (default: `gpt-4o-mini`).
