"""Bridge between the v2 telemetry adapter and the legacy Cloud Function client.

The v2 :class:`~app.integrations.telemetry.cloud_function_adapter.CloudFunctionAdapter`
expects an HTTP client object that exposes a single ``invoke(payload)`` method
returning the parsed response body. The actual network plumbing for our
GCP cloud-function gateway lives in
:class:`~app.helpers.telemetry.telemetry_cloud_function_client.TelemetryFuncHTTPClient`,
which exposes one method per action (``validate_token``,
``get_telemetry_sites``, etc.) and a different payload shape per endpoint.

This module is a thin translation layer that adapts those legacy methods to the
single ``invoke`` entry point the v2 adapter calls. It is intentionally small
and stateless so that unit tests can inject a fake client without going
through this shim at all.
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import HTTPException

from .telemetry_cloud_function_client import TelemetryFuncHTTPClient

logger = logging.getLogger(__name__)


class _CloudFunctionInvokeError(Exception):
    """Raised by :meth:`CloudFunctionTelemetryClient.invoke` so that
    :py:meth:`CloudFunctionAdapter._translate_error` can map it onto a
    structured ProviderError. The adapter inspects ``status_code`` to decide
    between :class:`CredentialError`, :class:`RateLimited`, etc.
    """

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class CloudFunctionTelemetryClient:
    """Shim that lets the v2 adapter speak to the legacy CF gateway.

    Currently dispatches the ``validate`` action (used by
    :py:meth:`CloudFunctionAdapter.test_credentials`) to the legacy
    ``validate_token`` endpoint, which is the production-tested path for
    verifying AlsoEnergy / KMC credentials.

    The ``list_sites`` action is intentionally rejected with
    :class:`_CloudFunctionInvokeError` (mapped to
    :class:`ProviderUnavailable` by the adapter) so that the v2 sync-sites
    endpoint surfaces a clear error rather than silently treating the
    account as having zero sites — which would mark every existing
    external-site mapping as missing. Site enumeration for syncing remains
    handled by the existing ``/connections/{id}/remote-sites`` flow that
    requires a Secret-Manager-backed token reference.
    """

    def __init__(self, legacy_client: TelemetryFuncHTTPClient | None = None) -> None:
        self._legacy = legacy_client

    def _client(self) -> TelemetryFuncHTTPClient:
        if self._legacy is None:
            self._legacy = TelemetryFuncHTTPClient()
        return self._legacy

    def invoke(self, payload: dict[str, Any]) -> Any:
        action = payload.get("action")
        provider_key = payload.get("provider") or ""
        credentials = payload.get("credentials") or {}
        token = credentials.get("token") or ""

        if action == "validate":
            self._validate_credentials(provider_key, token)
            return {"valid": True}

        if action == "list_sites":
            # See class docstring: silent empty-list would corrupt sync state.
            raise _CloudFunctionInvokeError(
                "Site enumeration via the v2 cloud-function client is not "
                "wired up yet. Use the per-site Add Connection flow to map "
                "external sites for now.",
                status_code=501,
            )

        raise _CloudFunctionInvokeError(
            f"Unsupported telemetry action: {action!r}",
            status_code=501,
        )

    def _validate_credentials(self, provider_key: str, token: str) -> None:
        if not token:
            # Adapter should have caught this earlier via _require_fields, but
            # guard defensively so we never POST an empty token to the gateway.
            raise _CloudFunctionInvokeError(
                "Missing credentials token",
                status_code=401,
            )
        try:
            self._client().validate_token(provider_key, token)
        except HTTPException as exc:
            # The legacy client raises HTTP 400 on either an invalid token or
            # an unreachable cloud function. We can't tell which from here,
            # but for the user-facing Test Credentials flow the most useful
            # interpretation is "credentials rejected" — a transient gateway
            # outage will still re-test cleanly on the next click.
            logger.info(
                "Telemetry validate_token rejected provider=%s detail=%s",
                provider_key,
                getattr(exc, "detail", ""),
            )
            raise _CloudFunctionInvokeError(
                str(getattr(exc, "detail", "")) or "Provider rejected credentials",
                status_code=401,
            ) from exc
