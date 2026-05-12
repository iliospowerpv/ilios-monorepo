"""Adapter that delegates to the legacy GCP Cloud Function gateway.

The real network call lives in the existing ``BaseCloudFuncHTTPClient``
implementation under ``app.helpers.telemetry``. This adapter is a thin
translation layer: it owns the request payload format, performs the call
in a way that does not log credentials, and converts provider-specific
HTTP status codes / error bodies into our structured exceptions.

Concrete vendor adapters subclass this class and override
:py:attr:`provider_key` plus the credential-encoding hook.
"""
from __future__ import annotations

import logging
from typing import Any, Sequence

from app.security.redaction import fingerprint, redact_mapping

from .base import (
    CredentialError,
    NoData,
    ProviderError,
    ProviderUnavailable,
    RateLimited,
)
from .models import ExternalSiteRecord, TestResult

logger = logging.getLogger(__name__)


class CloudFunctionAdapter:
    """Base adapter that issues HTTP requests via the legacy CF gateway."""

    provider_key: str = ""
    cloud_function_url_setting: str = ""

    # Subclasses override the keys their provider expects in ``credentials``.
    required_credential_fields: tuple[str, ...] = ()

    def __init__(self, http_client: Any | None = None) -> None:
        self._http_client = http_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def test_credentials(self, credentials: dict[str, str]) -> TestResult:
        self._require_fields(credentials)
        # Use a dedicated ``validate`` action rather than ``list_sites`` so the
        # cloud-function client can route credential verification through a
        # cheap auth check (the legacy ``validate_token`` endpoint) without
        # triggering full site enumeration. Site enumeration may require
        # provider state (secret-manager-backed token references) that is not
        # available during credential entry.
        try:
            self._invoke(self._build_payload("validate", credentials, {}))
        except CredentialError as exc:
            return TestResult(success=False, message=str(exc) or "Invalid credentials")
        except RateLimited as exc:
            return TestResult(success=False, message=str(exc) or "Rate limited")
        except (NoData, ProviderUnavailable) as exc:
            return TestResult(success=False, message=str(exc) or "Provider unavailable")
        return TestResult(
            success=True,
            message="Credentials verified",
            available_sites_count=None,
        )

    def list_sites(self, credentials: dict[str, str]) -> Sequence[ExternalSiteRecord]:
        self._require_fields(credentials)
        payload = self._build_payload("list_sites", credentials, {})
        response = self._invoke(payload)
        return tuple(
            ExternalSiteRecord(
                external_site_id=str(item["external_site_id"]),
                external_site_name=item.get("external_site_name"),
                raw_metadata=item.get("raw_metadata") or {},
            )
            for item in self._extract_sites(response)
        )

    # ------------------------------------------------------------------
    # Hooks for subclasses
    # ------------------------------------------------------------------

    def encode_credentials(self, credentials: dict[str, str]) -> dict[str, str]:
        """Return the credential payload expected by the cloud function.

        Default implementation returns the dict as-is. Vendor adapters that
        need base64 / token shaping override this.
        """
        return dict(credentials)

    def _build_payload(
        self,
        action: str,
        credentials: dict[str, str],
        extra: dict[str, Any],
    ) -> dict[str, Any]:
        return {
            "provider": self.provider_key,
            "action": action,
            "credentials": self.encode_credentials(credentials),
            **extra,
        }

    def _extract_sites(self, response: Any) -> list[dict[str, Any]]:
        if response is None:
            return []
        if isinstance(response, list):
            return [self._normalise_site(item) for item in response]
        if isinstance(response, dict):
            sites = response.get("sites") or response.get("items") or []
            return [self._normalise_site(item) for item in sites]
        return []

    @staticmethod
    def _normalise_site(item: dict[str, Any]) -> dict[str, Any]:
        return {
            "external_site_id": item.get("external_site_id")
            or item.get("id")
            or item.get("site_id"),
            "external_site_name": item.get("external_site_name")
            or item.get("name")
            or item.get("site_name"),
            "raw_metadata": item.get("raw_metadata") or item.get("metadata") or {},
        }

    # ------------------------------------------------------------------
    # Internal HTTP plumbing
    # ------------------------------------------------------------------

    def _require_fields(self, credentials: dict[str, str]) -> None:
        missing = [k for k in self.required_credential_fields if not credentials.get(k)]
        if not missing:
            return
        # Distinguish "nothing stored at all" from "partial config". The
        # former is the normal state after an in-memory store wipe and
        # deserves an actionable message that points operators at the
        # Rotate Credentials flow.
        if not any(credentials.values()):
            raise CredentialError(
                "No credentials are stored for this account. "
                "Use Rotate Credentials to enter them.",
                provider_key=self.provider_key,
            )
        raise CredentialError(
            f"Missing credential fields: {', '.join(missing)}. "
            "Use Rotate Credentials to update them.",
            provider_key=self.provider_key,
        )

    def _invoke(self, payload: dict[str, Any]) -> Any:
        client = self._get_client()
        safe_payload = redact_mapping(payload)
        cred_fp = fingerprint((payload.get("credentials") or {}).get("token") or "")
        logger.info(
            "Invoking telemetry provider adapter provider=%s action=%s payload=%s cred_fp=%s",
            self.provider_key,
            payload.get("action"),
            safe_payload,
            cred_fp,
        )
        try:
            return client.invoke(payload)
        except CredentialError:
            raise
        except ProviderError:
            raise
        except Exception as exc:  # noqa: BLE001
            return self._translate_error(exc)

    def _translate_error(self, exc: Exception) -> Any:
        """Convert raw HTTP errors into structured ProviderError subclasses."""
        status_code = getattr(exc, "status_code", None) or getattr(
            getattr(exc, "response", None), "status_code", None
        )
        body_text = ""
        response = getattr(exc, "response", None)
        if response is not None:
            try:
                body_text = response.text or ""
            except Exception:  # pragma: no cover - defensive
                body_text = ""

        if status_code in (401, 403):
            raise CredentialError(
                f"Provider rejected credentials (HTTP {status_code})",
                provider_key=self.provider_key,
            ) from exc
        if status_code == 429:
            retry_after = None
            if response is not None:
                try:
                    retry_after = int(response.headers.get("Retry-After", "0")) or None
                except (TypeError, ValueError):
                    retry_after = None
            raise RateLimited(
                "Provider rate-limited the request",
                retry_after=retry_after,
                provider_key=self.provider_key,
            ) from exc
        if status_code == 404 and "BinData" in body_text:
            # Legacy convention: CF returns 404 with BinData payload when the
            # external account has no telemetry rows yet.
            raise NoData(
                "Provider returned no data",
                provider_key=self.provider_key,
            ) from exc
        if status_code and 500 <= status_code < 600:
            raise ProviderUnavailable(
                f"Provider responded with HTTP {status_code}",
                provider_key=self.provider_key,
            ) from exc
        raise ProviderUnavailable(
            f"Provider call failed: {type(exc).__name__}",
            provider_key=self.provider_key,
        ) from exc

    def _get_client(self) -> Any:
        if self._http_client is not None:
            return self._http_client

        # Lazy import + lazy default client construction so unit tests can
        # inject a fake without forcing GCS credentials to load.
        try:
            from app.helpers.telemetry.cloud_function_telemetry_client import (  # type: ignore
                CloudFunctionTelemetryClient,
            )
        except ImportError as exc:
            # The v2 cloud-function client glue is not wired up in this
            # environment. Surface a clean ProviderUnavailable so callers
            # (e.g. test_credentials) return a meaningful message instead
            # of crashing the request with a 500.
            logger.warning(
                "CloudFunctionTelemetryClient unavailable for provider %s: %s",
                self.provider_key,
                exc,
            )
            raise ProviderUnavailable(
                "Live credential testing is not available in this environment. "
                "Contact a telemetry administrator to enable the provider integration.",
                provider_key=self.provider_key,
            ) from exc

        self._http_client = CloudFunctionTelemetryClient()
        return self._http_client
