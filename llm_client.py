"""
LLM client wrapper — single swap point for changing providers or models.
All LLM calls in the project go through chat() here.
"""
from __future__ import annotations
import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

_client: OpenAI | None = None


def _get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY not set. Copy .env.example → .env and add your key.")
        _client = OpenAI(api_key=api_key)
    return _client


def chat(messages: list[dict], temperature: float = 0.7) -> str:
    """
    Send a list of {role, content} messages to the LLM and return the reply text.

    messages format:
        [
            {"role": "system",    "content": "..."},
            {"role": "user",      "content": "..."},
            {"role": "assistant", "content": "..."},  # optional history
        ]
    """
    model = os.environ.get("LLM_MODEL", "gpt-4o-mini")
    response = _get_client().chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
    )
    return response.choices[0].message.content.strip()
