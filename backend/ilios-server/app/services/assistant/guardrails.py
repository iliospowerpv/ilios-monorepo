"""Hard guardrails for the AI Assistant tool layer.

Defense-in-depth around the read-only contract. Two independent checks must BOTH pass before any
tool runs:

1. Allowlist — the requested tool name must be in the explicit read-only catalog (``allowed``).
2. Prohibited-keyword screen — the name must not look like a mutating/executing/governed action,
   independent of the allowlist, so a future catalog mistake can't smuggle a write through.

The screened keywords are derived from the engine's machine-readable ``PROHIBITED_ACTIONS`` contract
plus generic mutation verbs. Any rejection raises ``AssistantGuardrailError`` and is logged.
"""
from __future__ import annotations

import logging
from typing import Iterable

logger = logging.getLogger(__name__)


class AssistantGuardrailError(Exception):
    """Raised when a tool invocation violates the read-only contract."""


# Substrings that indicate a non-read-only action. Matched case-insensitively against the tool name.
# Sourced from orchestration_context_service.PROHIBITED_ACTIONS + common write/execute verbs.
PROHIBITED_KEYWORDS: tuple[str, ...] = (
    "start",
    "advance",
    "resume",
    "execute",
    "run_step",
    "launch",
    "preview",
    "promote",
    "approve",
    "activate",
    "map_",
    "unmap",
    "declare",
    "bypass",
    "write",
    "mutate",
    "create",
    "update",
    "delete",
    "remove",
    "set_",
    "accept",
    "override",
    "submit",
    "complete_run",
    "abandon",
)


def is_prohibited(name: str) -> bool:
    """True if ``name`` matches any prohibited-action keyword (mutation/execution/governed)."""
    lowered = (name or "").lower()
    return any(kw in lowered for kw in PROHIBITED_KEYWORDS)


def assert_tool_allowed(name: str, allowed: Iterable[str]) -> None:
    """Enforce both guardrail checks. Raise ``AssistantGuardrailError`` on any violation."""
    allowed_set = set(allowed)
    if is_prohibited(name):
        logger.warning("AI Assistant blocked a prohibited tool request: %r", name)
        raise AssistantGuardrailError(
            f"Tool {name!r} is not permitted: the assistant is read-only and cannot perform "
            f"actions that start, execute, or mutate anything."
        )
    if name not in allowed_set:
        logger.warning("AI Assistant blocked a non-allowlisted tool request: %r", name)
        raise AssistantGuardrailError(
            f"Tool {name!r} is not in the read-only assistant catalog."
        )
