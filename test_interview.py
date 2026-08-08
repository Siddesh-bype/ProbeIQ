"""
End-to-end test script for ProbeIQ.

Usage:
    1. Start the server:  python main.py
    2. In another terminal: python test_interview.py

Tests a full interview flow with a real candidate from candidates.json:
  - Turn 1: personalized opening
  - Turns 2–N: simulated candidate responses
  - Final: structured feedback with all required keys
"""
import json
import sys
import requests

BASE_URL = "http://localhost:8000"
ENDPOINT = f"{BASE_URL}/api/interview"

# Simulated candidate responses — mix of thin and substantive answers
SIMULATED_RESPONSES = [
    "I used embeddings to convert text into vector representations for semantic search.",
    "Yeah, I did that one.",  # deliberately thin — should trigger follow-up
    "I built a retrieval pipeline using FAISS as the vector store. The main challenge was tuning "
    "the similarity threshold — too low gave irrelevant results, too high missed valid matches. "
    "I ended up using cosine similarity with a 0.75 threshold after testing on our validation set.",
    "I'm not sure, I think we used some prompting techniques.",  # somewhat thin
    "For function calling I defined JSON schemas for each tool the model could invoke, then parsed "
    "the structured output to route to the right handler. The tricky part was handling edge cases "
    "where the model hallucinated function names that didn't exist in our schema.",
    "I worked with LangChain agents and set up a ReAct loop that could reason through multi-step "
    "tasks. We used tool-calling with a custom calculator and a web search tool.",
    "We deployed using Docker containers orchestrated with Kubernetes. I wrote the Dockerfile, "
    "set up health checks, and configured horizontal pod autoscaling based on request latency.",
    "Not really.",  # deliberately thin
    "I implemented monitoring using Prometheus for metrics collection and Grafana for dashboards. "
    "We tracked p95 latency, token usage per request, and error rates by endpoint.",
    "The capstone was a RAG-based Q&A system for internal documentation. I handled the embedding "
    "pipeline, retrieval layer, and prompt engineering. We got 85% accuracy on our eval set.",
    "I think it went well overall.",
    "We used structured outputs with JSON mode to ensure the model returned parseable responses. "
    "This was critical for our workflow automation pipeline.",
    "I haven't explored that area much yet.",
    "For the chatbot, I integrated the OpenAI API with a FastAPI backend, added streaming responses "
    "using Server-Sent Events, and built a simple React frontend to display the conversation.",
]


def test_health():
    """Check the server is running."""
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        r.raise_for_status()
        print(f"✓ Health check passed: {r.json()}")
        return True
    except requests.ConnectionError:
        print("✗ Server not reachable at", BASE_URL)
        print("  → Start it first: python main.py")
        return False


def load_candidate(index: int = 0) -> dict:
    """Load a candidate from candidates.json."""
    with open("candidates.json", encoding="utf-8") as f:
        data = json.load(f)
    candidate = data["candidates"][index]
    print(f"\n── Candidate: {candidate['member']['name']} ({candidate['member']['jobRole']}) ──")
    print(f"   Experience: {candidate['member']['yearsExperience']} years")
    print(f"   Missions: {len(candidate['missions'])}")
    print(f"   Signals: {candidate['signals']}")
    return candidate


def run_interview(candidate: dict):
    """Run a full interview and validate each step."""
    session_id = "test-e2e-001"
    errors = []
    turn_count = 0

    # ── Turn 1: Start ────────────────────────────────────────────────────────
    print("\n── Turn 1: Start Interview ──")
    r = requests.post(ENDPOINT, json={"sessionId": session_id, "candidate": candidate}, timeout=60)
    r.raise_for_status()
    body = r.json()
    turn_count += 1

    print(f"  Reply ({len(body['reply'])} chars): {body['reply'][:150]}...")
    print(f"  Done: {body['done']}")

    # Validate: personalized opening
    name = candidate["member"]["name"].split()[0]  # first name
    if name.lower() in body["reply"].lower():
        print(f"  ✓ Opening mentions candidate name '{name}'")
    else:
        errors.append(f"Opening doesn't mention candidate name '{name}'")
        print(f"  ✗ Opening doesn't mention candidate name '{name}'")

    if body["done"]:
        errors.append("Interview ended on turn 1")
        print("  ✗ Interview ended on turn 1!")
        return errors

    # ── Turns 2..N ────────────────────────────────────────────────────────────
    for i, response_text in enumerate(SIMULATED_RESPONSES):
        turn_count += 1
        print(f"\n── Turn {turn_count}: Candidate responds ──")
        print(f"  Candidate: {response_text[:80]}...")

        r = requests.post(ENDPOINT, json={"sessionId": session_id, "message": response_text}, timeout=60)
        r.raise_for_status()
        body = r.json()

        print(f"  Reply ({len(body['reply'])} chars): {body['reply'][:150]}...")
        print(f"  Done: {body['done']}")

        if body["done"]:
            print(f"\n══ Interview completed at turn {turn_count} ══")

            # Validate: done fires within 8–14 turns
            if 8 <= turn_count <= 15:
                print(f"  ✓ Done fired at turn {turn_count} (within 8–15 range)")
            else:
                errors.append(f"Done fired at turn {turn_count} (expected 8–15)")
                print(f"  ✗ Done fired at turn {turn_count} (expected 8–15)")

            # Validate: feedback structure
            fb = body.get("feedback")
            if fb is None:
                errors.append("No feedback in final response")
                print("  ✗ No feedback in final response")
            else:
                print(f"\n── Feedback ──")
                print(f"  Summary: {fb.get('summary', '(missing)')[:120]}...")

                for key in ("summary", "strengths", "gaps", "next"):
                    if key not in fb:
                        errors.append(f"Feedback missing key: {key}")
                        print(f"  ✗ Missing key: {key}")
                    elif key == "summary" and not fb[key]:
                        errors.append("Feedback summary is empty")
                        print("  ✗ Summary is empty")
                    elif key != "summary" and not fb[key]:
                        errors.append(f"Feedback {key} is empty list")
                        print(f"  ✗ {key} is empty list")
                    else:
                        if isinstance(fb[key], list):
                            print(f"  ✓ {key}: {len(fb[key])} items")
                            for item in fb[key]:
                                print(f"      • {item[:100]}")
                        else:
                            print(f"  ✓ {key}: present")

            return errors

    # If we ran out of simulated responses
    print(f"\n  ⚠ Ran out of simulated responses at turn {turn_count} — interview didn't end")
    errors.append(f"Interview didn't end within {turn_count} turns")
    return errors


def main():
    print("╔══════════════════════════════════════════╗")
    print("║   ProbeIQ — End-to-End Interview Test    ║")
    print("╚══════════════════════════════════════════╝")

    if not test_health():
        sys.exit(1)

    candidate = load_candidate(index=0)  # Sarah Johnson
    errors = run_interview(candidate)

    print("\n" + "═" * 50)
    if errors:
        print(f"RESULT: {len(errors)} issue(s) found:")
        for e in errors:
            print(f"  ✗ {e}")
        sys.exit(1)
    else:
        print("RESULT: ✓ All checks passed!")
        sys.exit(0)


if __name__ == "__main__":
    main()
