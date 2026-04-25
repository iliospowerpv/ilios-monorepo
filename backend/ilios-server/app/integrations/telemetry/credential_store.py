"""Pluggable credential storage for provider accounts.

Phase 1 ships only an :class:`InMemoryCredentialStore` and a thin
:class:`PlaceholderCredentialStore` used by the demo seed. A future
``GCPSecretManagerCredentialStore`` will slot in here without touching
callers.
"""
from __future__ import annotations

import secrets
from threading import Lock
from typing import Protocol, runtime_checkable


@runtime_checkable
class CredentialStore(Protocol):
    def store(self, account_label: str, fields: dict[str, str]) -> str: ...

    def retrieve(self, secret_name: str) -> dict[str, str]: ...

    def delete(self, secret_name: str) -> None: ...


class InMemoryCredentialStore:
    """Process-local credential store. Suitable for local dev and tests."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._data: dict[str, dict[str, str]] = {}

    def _new_name(self, account_label: str) -> str:
        suffix = secrets.token_hex(6)
        return f"telemetry::{account_label or 'account'}::{suffix}"

    def store(self, account_label: str, fields: dict[str, str]) -> str:
        with self._lock:
            name = self._new_name(account_label)
            self._data[name] = dict(fields)
        return name

    def retrieve(self, secret_name: str) -> dict[str, str]:
        with self._lock:
            return dict(self._data.get(secret_name, {}))

    def delete(self, secret_name: str) -> None:
        with self._lock:
            self._data.pop(secret_name, None)


class PlaceholderCredentialStore:
    """No-op store that returns the literal account label as the secret name.

    Used by the demo seed so existing rows keep their ``demo_token_placeholder``
    secret reference without mutation.
    """

    def store(self, account_label: str, fields: dict[str, str]) -> str:
        return account_label or "telemetry::placeholder"

    def retrieve(self, secret_name: str) -> dict[str, str]:
        return {}

    def delete(self, secret_name: str) -> None:
        return None


_default_store: CredentialStore = InMemoryCredentialStore()


def get_credential_store() -> CredentialStore:
    """FastAPI dependency-friendly accessor for the configured store."""
    return _default_store


def set_credential_store(store: CredentialStore) -> None:
    """Override the process-wide store (tests only)."""
    global _default_store
    _default_store = store
