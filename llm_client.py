"""
LLM client wrapper — single swap point for changing providers or models.
All LLM calls in the project go through chat() here.
"""
from __future__ import annotations
import os
import time
import logging
from openai import OpenAI, APITimeoutError, APIConnectionError, RateLimitError
from dotenv import load_dotenv

load_dotenv()

log = logging.getLogger(__name__)

_client: OpenAI | None = None

# Default timeout for API calls (seconds)
_TIMEOUT = 30
# Number of retries on transient errors
_MAX_RETRIES = 1
# Delay between retries (seconds)
_RETRY_DELAY = 2


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set. Copy .env.example → .env and add your key.")
        _client = OpenAI(api_key=api_key, timeout=_TIMEOUT)
    return _client


def chat(
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 1024,
) -> str:
    """
    Send a list of {role, content} messages to the LLM and return the reply text.

    messages format:
        [
            {"role": "system",    "content": "..."},
            {"role": "user",      "content": "..."},
            {"role": "assistant", "content": "..."},  # optional history
        ]

    Includes retry logic for transient errors (timeout, connection, rate-limit).
    """
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
    client = _get_client()

    last_error: Exception | None = None
    for attempt in range(_MAX_RETRIES + 1):
        try:
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )
            content = response.choices[0].message.content
            return (content or "").strip()
        except (APITimeoutError, APIConnectionError, RateLimitError) as e:
            last_error = e
            if attempt < _MAX_RETRIES:
                wait = _RETRY_DELAY * (attempt + 1)
                log.warning("LLM call failed (attempt %d/%d): %s — retrying in %ds",
                            attempt + 1, _MAX_RETRIES + 1, e, wait)
                time.sleep(wait)
            else:
                log.error("LLM call failed after %d attempts: %s", _MAX_RETRIES + 1, e)

    raise RuntimeError(f"LLM call failed after {_MAX_RETRIES + 1} attempts: {last_error}")
