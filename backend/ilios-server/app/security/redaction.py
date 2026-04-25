"""Redaction utilities for telemetry credentials and other secrets.

Any value passing through these helpers is shortened to a fingerprint that
is safe to log. The :class:`RedactingFilter` is attached to the root
logger by ``configure_redaction()`` so that no credential value emitted by
log statements (deliberately or accidentally) survives to a log sink.
"""
from __future__ import annotations

import logging
import re
from typing import Any, Iterable, Mapping

# Field names whose values should always be redacted regardless of context.
SECRET_FIELDS: frozenset[str] = frozenset(
    {
        "password",
        "passwd",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "api_key",
        "api-key",
        "apikey",
        "authorization",
        "credential",
        "credentials",
        "secret_token",
        "secret_token_name",
    }
)

# Keys that look "sensitive" by name fragment.
_SENSITIVE_PATTERN = re.compile(r"(?i)(secret|token|password|api[_-]?key|authorization|credential)")

REDACTED = "[REDACTED]"


def fingerprint(value: str | None, *, keep: int = 4) -> str:
    """Return a short fingerprint for a secret string, never the secret itself.

    The fingerprint preserves the trailing ``keep`` characters so operators can
    correlate a token across log lines without exposing it.
    """
    if not value:
        return REDACTED
    sval = str(value)
    if len(sval) <= keep:
        return f"***(len={len(sval)})"
    return f"***{sval[-keep:]}(len={len(sval)})"


def is_secret_key(key: str) -> bool:
    if not key:
        return False
    if key.lower() in SECRET_FIELDS:
        return True
    return bool(_SENSITIVE_PATTERN.search(key))


def redact_mapping(data: Mapping[str, Any]) -> dict[str, Any]:
    """Return a shallow copy of ``data`` with secret values replaced."""
    if not isinstance(data, Mapping):
        return data  # type: ignore[return-value]
    out: dict[str, Any] = {}
    for key, value in data.items():
        if is_secret_key(str(key)):
            out[key] = REDACTED
        elif isinstance(value, Mapping):
            out[key] = redact_mapping(value)
        elif isinstance(value, (list, tuple)):
            out[key] = [redact_mapping(v) if isinstance(v, Mapping) else v for v in value]
        else:
            out[key] = value
    return out


# Patterns recognised inside formatted log messages.
_KV_PATTERN = re.compile(
    r"(?i)\b(password|passwd|secret(?:_token(?:_name)?)?|token|access[_-]?token|"
    r"refresh[_-]?token|api[_-]?key|authorization|credentials?)"
    r"\s*[:=]\s*"
    r"(?:\"([^\"]+)\"|'([^']+)'|([^\s,;}\)\]]+))",
)
_BEARER_PATTERN = re.compile(r"(?i)bearer\s+([A-Za-z0-9._\-+/=]{8,})")
_BASIC_PATTERN = re.compile(r"(?i)basic\s+([A-Za-z0-9+/=]{8,})")


def redact_text(message: str) -> str:
    """Best-effort scrub of inline credential patterns inside a log message."""
    if not message:
        return message

    def _kv_repl(match: re.Match[str]) -> str:
        key = match.group(1)
        return f"{key}={REDACTED}"

    scrubbed = _KV_PATTERN.sub(_kv_repl, message)
    scrubbed = _BEARER_PATTERN.sub("Bearer " + REDACTED, scrubbed)
    scrubbed = _BASIC_PATTERN.sub("Basic " + REDACTED, scrubbed)
    return scrubbed


class RedactingFilter(logging.Filter):
    """Logging filter that scrubs secret-looking content from log records."""

    def filter(self, record: logging.LogRecord) -> bool:  # noqa: D401
        try:
            if isinstance(record.msg, str):
                record.msg = redact_text(record.msg)
            elif isinstance(record.msg, Mapping):
                record.msg = redact_mapping(record.msg)

            if record.args:
                record.args = self._scrub_args(record.args)
        except Exception:  # pragma: no cover - logging must never raise
            pass
        return True

    def _scrub_args(self, args: Any) -> Any:
        if isinstance(args, Mapping):
            return redact_mapping(args)
        if isinstance(args, tuple):
            return tuple(self._scrub_one(a) for a in args)
        if isinstance(args, list):
            return [self._scrub_one(a) for a in args]
        return self._scrub_one(args)

    def _scrub_one(self, value: Any) -> Any:
        if isinstance(value, Mapping):
            return redact_mapping(value)
        if isinstance(value, str):
            return redact_text(value)
        return value


_INSTALLED = False


def configure_redaction(loggers: Iterable[str] | None = None) -> None:
    """Attach :class:`RedactingFilter` to the root logger (idempotent).

    Optionally also attach to named loggers — useful for libraries that
    create their own logger and bypass the root filter chain.
    """
    global _INSTALLED
    flt = RedactingFilter()
    if not _INSTALLED:
        root = logging.getLogger()
        if not any(isinstance(f, RedactingFilter) for f in root.filters):
            root.addFilter(flt)
        for handler in root.handlers:
            if not any(isinstance(f, RedactingFilter) for f in handler.filters):
                handler.addFilter(RedactingFilter())
        _INSTALLED = True
    for name in loggers or ():
        logger = logging.getLogger(name)
        if not any(isinstance(f, RedactingFilter) for f in logger.filters):
            logger.addFilter(RedactingFilter())
