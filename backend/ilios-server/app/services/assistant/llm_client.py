"""OpenAI client for the AI Assistant, via the Replit AI gateway.

Mirrors the lazy-client + tenacity-retry pattern already used by ``InAppParsingService`` (no API
key managed by us — billed to Replit credits). Kept as a tiny seam so tests can monkeypatch
``get_client`` and never hit a live model. This module performs NO business logic and NO writes.
"""
from __future__ import annotations

import logging
import os
from typing import Any, Optional

from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

# The newest supported model on the Replit AI gateway (same default InAppParsingService uses).
ASSISTANT_MODEL = "gpt-5.2"

_client: Any = None


class AssistantLLMError(Exception):
    """The assistant's language-model call failed for a non-rate-limit reason.

    The router maps this to a friendly 503 so the FE can show a transient-failure message instead of
    leaking a raw provider/SDK error.
    """


class AssistantRateLimitError(AssistantLLMError):
    """The model is rate-limited/over capacity (HTTP 429 from the gateway, retries exhausted).

    Carries an optional ``retry_after`` (seconds) so the router can echo a ``Retry-After`` header
    (already in CORS ``expose_headers``) and the FE can show a calibrated "try again" hint.
    """

    def __init__(self, message: str = "rate_limited", retry_after: Optional[int] = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after


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


def _extract_retry_after(exc: BaseException) -> Optional[int]:
    """Best-effort parse of a ``Retry-After`` (seconds) hint off a provider/SDK error. None if absent."""
    response = getattr(exc, "response", None)
    headers = getattr(response, "headers", None)
    if headers:
        for key in ("retry-after", "Retry-After", "x-ratelimit-reset", "retry-after-ms"):
            try:
                raw = headers.get(key)  # type: ignore[union-attr]
            except Exception:  # noqa: BLE001 - headers may be a non-Mapping
                raw = None
            if raw:
                try:
                    value = int(float(raw))
                except (TypeError, ValueError):
                    continue
                if key == "retry-after-ms":
                    value = max(1, round(value / 1000))
                if value > 0:
                    return value
    return None


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
def _create_chat_completion_raw(
    *, messages: list[dict], tools: list[dict], model: str = ASSISTANT_MODEL
):
    """Single chat-completion call with tool schemas. Retries only on rate limits (reraises raw)."""
    client = get_client()
    return client.chat.completions.create(
        model=model,
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )


def create_chat_completion(*, messages: list[dict], tools: list[dict], model: str = ASSISTANT_MODEL):
    """Public seam: run the retrying call and normalize any failure into a typed assistant error.

    ``tenacity`` is configured with ``reraise=True``, so an exhausted retry surfaces the original
    exception here (not a ``RetryError``); we convert a rate-limit to ``AssistantRateLimitError``
    (with any ``Retry-After``) and every other failure to ``AssistantLLMError`` so the router can
    map them to friendly 429/503 responses without leaking raw SDK errors.
    """
    try:
        return _create_chat_completion_raw(messages=messages, tools=tools, model=model)
    except (AssistantLLMError, AssistantRateLimitError):
        raise
    except Exception as exc:  # noqa: BLE001 - normalize provider/SDK failures into typed errors
        if _is_rate_limit_error(exc):
            logger.warning("AI Assistant LLM rate-limited after retries: %s", exc)
            raise AssistantRateLimitError(retry_after=_extract_retry_after(exc)) from exc
        logger.exception("AI Assistant LLM call failed")
        raise AssistantLLMError(str(exc)) from exc
