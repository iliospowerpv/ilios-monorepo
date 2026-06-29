"""OpenAI client for the AI Assistant, via the Replit AI gateway.

Mirrors the lazy-client + tenacity-retry pattern already used by ``InAppParsingService`` (no API
key managed by us — billed to Replit credits). Kept as a tiny seam so tests can monkeypatch
``get_client`` and never hit a live model. This module performs NO business logic and NO writes.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# The newest supported model on the Replit AI gateway (same default InAppParsingService uses).
ASSISTANT_MODEL = "gpt-5.2"

_client: Any = None


def get_client() -> Any:
    """Lazily construct the OpenAI client against the Replit AI gateway.

    Tests monkeypatch this function, so the import and env lookup only happen in production.
    """
    global _client
    if _client is None:
        from openai import OpenAI

        api_key = os.environ.get("AI_INTEGRATIONS_OPENAI_API_KEY")
        base_url = os.environ.get("AI_INTEGRATIONS_OPENAI_BASE_URL")
        if not api_key or not base_url:
            raise RuntimeError(
                "AI_INTEGRATIONS_OPENAI_API_KEY and AI_INTEGRATIONS_OPENAI_BASE_URL must be set "
                "(install the OpenAI Replit integration) for the AI Assistant."
            )
        _client = OpenAI(api_key=api_key, base_url=base_url)
    return _client


def _is_rate_limit_error(exc: BaseException) -> bool:
    return "429" in str(exc) or "rate limit" in str(exc).lower()


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=20),
    retry=lambda state: bool(
        state.outcome
        and state.outcome.failed
        and _is_rate_limit_error(state.outcome.exception())
    ),
    reraise=True,
)
def create_chat_completion(*, messages: list[dict], tools: list[dict], model: str = ASSISTANT_MODEL):
    """Single chat-completion call with tool schemas. Retries only on rate limits."""
    client = get_client()
    return client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )
