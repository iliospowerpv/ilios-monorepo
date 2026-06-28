"""Pluggable credential storage for telemetry v2 provider accounts.

Backends:

* :class:`InMemoryCredentialStore` — process-local; for unit tests and
  Replit dev shells where GCP isn't reachable.
* :class:`PlaceholderCredentialStore` — no-op; used only by the demo
  seed so existing rows keep their ``demo_token_placeholder`` reference.
* :class:`GCPSecretManagerCredentialStore` — durable backend backed by
  Google Cloud Secret Manager. Each provider account owns one secret
  resource; credential rotation adds a new *version* to the same secret
  rather than creating a new resource.

The selected backend is decided once at process start by
:func:`_build_default_store` and reused by every request through
:func:`get_credential_store`. Selection rules (in order):

1. If env var ``TELEMETRY_V2_CREDENTIAL_BACKEND`` is set, honour it
   (``gcp`` or ``in-memory``).
2. Otherwise, prefer GCP if ``gcp_project_id`` is set AND any of:
   - ``GOOGLE_APPLICATION_CREDENTIALS_JSON`` env var is set, OR
   - ``service_account_key_file_path`` setting points at an existing file.
3. Otherwise, fall back to in-memory and emit a startup warning.

Use :func:`is_credential_store_durable` to ask whether the active
backend persists credentials across process restarts. Production
startup and the credential write/test routes use this to refuse unsafe
operation.

The credential payload format on disk (GCP) is a JSON object of
``{field_name: value}`` pairs. Nothing else is ever written to a
secret payload, and no value is ever logged.
"""
from __future__ import annotations

import json
import logging
import os
import secrets
from threading import Lock
from typing import Optional, Protocol, runtime_checkable

from fastapi import HTTPException

logger = logging.getLogger(__name__)

# Prefix used for every v2-managed GCP secret resource. Keeping a stable
# prefix makes audits / IAM filters / cleanup scripts trivial and clearly
# distinguishes v2 secrets from the legacy ``ilios-das-c{cid}-...`` set.
V2_SECRET_PREFIX = "ilios-telemetry-v2"


@runtime_checkable
class CredentialStore(Protocol):
    def store(
        self,
        account_label: str,
        fields: dict[str, str],
        *,
        company_id: int,
        name_prefix: Optional[str] = None,
    ) -> str:
        """Persist ``fields`` and return an opaque secret reference name.

        ``name_prefix`` lets a caller (e.g. the weather provider framework)
        namespace its secrets (``ilios-weather-c{company}-…``) so they are
        distinguishable from telemetry secrets for audit / IAM / cleanup.
        When omitted the existing telemetry prefix is used unchanged.
        """

    def retrieve(self, secret_name: str) -> dict[str, str]:
        """Fetch the latest credential payload for ``secret_name``."""

    def rotate(self, secret_name: str, fields: dict[str, str]) -> None:
        """Replace the credential payload for ``secret_name`` (new version)."""

    def delete(self, secret_name: str) -> None:
        """Permanently remove ``secret_name`` (best-effort)."""


# ---------------------------------------------------------------------------
# In-memory backend
# ---------------------------------------------------------------------------


class InMemoryCredentialStore:
    """Process-local credential store. Suitable for local dev and tests."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._data: dict[str, dict[str, str]] = {}

    def _new_name(self, company_id: int, name_prefix: Optional[str] = None) -> str:
        return f"{name_prefix or V2_SECRET_PREFIX}-c{company_id}-{secrets.token_hex(6)}"

    def store(
        self,
        account_label: str,
        fields: dict[str, str],
        *,
        company_id: int,
        name_prefix: Optional[str] = None,
    ) -> str:
        with self._lock:
            name = self._new_name(company_id, name_prefix)
            self._data[name] = dict(fields)
        return name

    def retrieve(self, secret_name: str) -> dict[str, str]:
        with self._lock:
            return dict(self._data.get(secret_name, {}))

    def rotate(self, secret_name: str, fields: dict[str, str]) -> None:
        with self._lock:
            if secret_name in self._data:
                self._data[secret_name] = dict(fields)
            else:
                # Tolerant: a rotate on a vanished name re-creates it so
                # callers that pre-bind a secret name still work.
                self._data[secret_name] = dict(fields)

    def delete(self, secret_name: str) -> None:
        with self._lock:
            self._data.pop(secret_name, None)


# ---------------------------------------------------------------------------
# Demo placeholder backend
# ---------------------------------------------------------------------------


class PlaceholderCredentialStore:
    """No-op store that returns the literal account label as the secret name.

    Used by the demo seed so existing rows keep their
    ``demo_token_placeholder`` secret reference without mutation.
    """

    def store(
        self,
        account_label: str,
        fields: dict[str, str],
        *,
        company_id: int,
        name_prefix: Optional[str] = None,
    ) -> str:
        return account_label or "telemetry::placeholder"

    def retrieve(self, secret_name: str) -> dict[str, str]:
        return {}

    def rotate(self, secret_name: str, fields: dict[str, str]) -> None:
        return None

    def delete(self, secret_name: str) -> None:
        return None


# ---------------------------------------------------------------------------
# GCP Secret Manager backend (durable)
# ---------------------------------------------------------------------------


class GCPSecretManagerCredentialStore:
    """Durable credential store backed by Google Cloud Secret Manager.

    Secret naming: ``ilios-telemetry-v2-c{company_id}-{token_hex(6)}``.

    Payload format: JSON-encoded ``{field_name: value}`` dict.

    Rotation strategy: ``add_secret_version`` against the existing
    secret resource. The previous version remains for audit / rollback;
    callers always read ``versions/latest``.
    """

    def __init__(self, *, manager: Optional["object"] = None) -> None:
        # `manager` is typed `object` so this module can be imported even
        # when google-cloud-secret-manager isn't installed (e.g. in some
        # test contexts). The real type is GCPSecretsManager.
        self._manager = manager

    @property
    def manager(self):
        if self._manager is None:
            from app.helpers.telemetry.secrets_manager import GCPSecretsManager

            self._manager = GCPSecretsManager()
        return self._manager

    def _new_name(self, company_id: int, name_prefix: Optional[str] = None) -> str:
        return f"{name_prefix or V2_SECRET_PREFIX}-c{company_id}-{secrets.token_hex(6)}"

    def store(
        self,
        account_label: str,
        fields: dict[str, str],
        *,
        company_id: int,
        name_prefix: Optional[str] = None,
    ) -> str:
        name = self._new_name(company_id, name_prefix)
        payload = json.dumps(fields, separators=(",", ":"))
        self.manager.create_secret(name)
        self.manager.add_secret_version(name, payload)
        # Audit log — value is never included; only the resource name.
        logger.info(
            "telemetry_v2_credential_stored secret_name=%s company_id=%s account_label=%s",
            name,
            company_id,
            account_label,
        )
        return name

    def retrieve(self, secret_name: str) -> dict[str, str]:
        if not secret_name:
            return {}
        try:
            raw = self.manager.access_secret_value(secret_name)
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "telemetry_v2_credential_fetch_failed secret_name=%s error=%s",
                secret_name,
                type(exc).__name__,
            )
            return {}
        if not raw:
            return {}
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning(
                "telemetry_v2_credential_payload_corrupt secret_name=%s",
                secret_name,
            )
            return {}
        if not isinstance(data, dict):
            return {}
        return {str(k): str(v) for k, v in data.items()}

    def rotate(self, secret_name: str, fields: dict[str, str]) -> None:
        payload = json.dumps(fields, separators=(",", ":"))
        try:
            self.manager.add_secret_version(secret_name, payload)
        except HTTPException as exc:
            # Self-heal a dangling pointer. The DB row may reference a
            # V2-prefixed secret that no longer exists in GCP: e.g. the
            # account was created under the pre-durable in-memory backend
            # (which minted V2-style names but never wrote them to GCP), or
            # the secret was deleted out of band. ``add_secret_version`` on a
            # missing resource surfaces as a 404 via
            # ``GCPSecretsManager.handle_response_error``. Recreate the
            # resource and write the first version so the operator's
            # rotation succeeds instead of dead-ending on a 404. This mirrors
            # the tolerant ``InMemoryCredentialStore.rotate`` behaviour and
            # keeps ``secret_token_name`` stable (no DB churn). Any non-404
            # failure is a real error and is re-raised unchanged.
            if exc.status_code != 404:
                raise
            logger.warning(
                "telemetry_v2_credential_rotate_missing_secret secret_name=%s "
                "(recreating resource and writing first version)",
                secret_name,
            )
            try:
                self.manager.create_secret(secret_name)
            except HTTPException as create_exc:
                # A concurrent rotation (or a prior heal that created the
                # resource but failed before writing a version) may have
                # already recreated it -> AlreadyExists surfaces as 409.
                # That's fine: fall through and add our version to it. Any
                # other failure is real and is re-raised unchanged.
                if create_exc.status_code != 409:
                    raise
            self.manager.add_secret_version(secret_name, payload)
        logger.info(
            "telemetry_v2_credential_rotated secret_name=%s field_count=%s",
            secret_name,
            len(fields),
        )

    def delete(self, secret_name: str) -> None:
        try:
            self.manager.delete_secret(secret_name)
            logger.info(
                "telemetry_v2_credential_deleted secret_name=%s", secret_name
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "telemetry_v2_credential_delete_failed secret_name=%s error=%s",
                secret_name,
                type(exc).__name__,
            )


# ---------------------------------------------------------------------------
# Default store selection
# ---------------------------------------------------------------------------


def _gcp_config_available() -> bool:
    """Return True if we can construct a working GCPSecretsManager.

    Two supported credential sources (matches secrets_manager._build_credentials):

    1. ``GOOGLE_APPLICATION_CREDENTIALS_JSON`` env var (preferred on Replit;
       inline service-account JSON, never written to disk in the repo).
    2. ``service_account_key_file_path`` setting pointing at an existing file
       (legacy file-mounted key).

    In both cases ``gcp_project_id`` setting must also be present.
    """
    try:
        from app.settings import settings  # local import to avoid cycles
    except Exception:  # noqa: BLE001
        return False
    project_id = getattr(settings, "gcp_project_id", None)
    if not project_id:
        return False
    if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON"):
        return True
    key_path = getattr(settings, "service_account_key_file_path", None)
    if key_path and os.path.isfile(key_path):
        return True
    return False


def _build_default_store() -> CredentialStore:
    """Choose the best credential backend at process start."""
    backend = (os.getenv("TELEMETRY_V2_CREDENTIAL_BACKEND") or "").strip().lower()
    if backend == "in-memory":
        logger.warning(
            "telemetry_v2_credential_backend=in-memory (forced via env). "
            "Credentials WILL NOT survive process restart."
        )
        return InMemoryCredentialStore()
    if backend == "gcp":
        # Forced GCP — instantiate eagerly so misconfiguration surfaces now.
        store = GCPSecretManagerCredentialStore()
        _ = store.manager  # may raise; surfacing the error here is intentional
        logger.info("telemetry_v2_credential_backend=gcp (forced via env)")
        return store
    # Auto: pick GCP when configured, otherwise in-memory + warning.
    if _gcp_config_available():
        try:
            store = GCPSecretManagerCredentialStore()
            _ = store.manager
            logger.info("telemetry_v2_credential_backend=gcp (auto-selected)")
            return store
        except Exception as exc:  # noqa: BLE001
            logger.warning(
                "telemetry_v2_credential_backend=in-memory (GCP init failed: %s). "
                "Credentials WILL NOT survive process restart.",
                type(exc).__name__,
            )
            return InMemoryCredentialStore()
    logger.warning(
        "telemetry_v2_credential_backend=in-memory (no GCP credentials in environment). "
        "Credentials WILL NOT survive process restart."
    )
    return InMemoryCredentialStore()


_default_store: CredentialStore = _build_default_store()


def get_credential_store() -> CredentialStore:
    """FastAPI dependency-friendly accessor for the configured store."""
    return _default_store


def set_credential_store(store: CredentialStore) -> None:
    """Override the process-wide store (tests only)."""
    global _default_store
    _default_store = store


def reset_credential_store() -> CredentialStore:
    """Reconstruct the default store (used by restart-durability tests)."""
    global _default_store
    _default_store = _build_default_store()
    return _default_store


def is_credential_store_durable(
    store: Optional[CredentialStore] = None,
) -> bool:
    """Whether the active store persists credentials across restarts.

    ``InMemoryCredentialStore`` and ``PlaceholderCredentialStore`` are
    non-durable. Anything else (currently only
    ``GCPSecretManagerCredentialStore``) is treated as durable.
    """
    target = store if store is not None else _default_store
    return not isinstance(
        target, (InMemoryCredentialStore, PlaceholderCredentialStore)
    )
