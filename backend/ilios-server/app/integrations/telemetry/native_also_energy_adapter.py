"""Native AlsoEnergy provider adapter.

Replaces the legacy ``CloudFunctionAdapter`` path for ``also_energy``. Calls
the AlsoEnergy REST API directly so credential validation no longer depends
on the GCP Cloud Function gateway.

Implements the :class:`~app.integrations.telemetry.base.ProviderAdapter`
Protocol. Concretely:

* ``test_credentials`` issues a single ``POST /Auth/token`` (OAuth password
  grant) and maps the response to a structured :class:`TestResult`.
* ``list_sites`` reuses the access token from the same token endpoint and
  performs ``GET /Sites``. ``list_sites`` is implemented and unit-testable
  but the V2 ``sync-sites`` HTTP route remains gated until durable
  storage + operator approval are in place company-wide.

Credential and token values are *never* logged. Provider URLs and field
names are inherited from the legacy ``backend/rea-telemetry/`` reference
implementation; no API behaviour is invented.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from http import HTTPStatus
from typing import Any, Mapping, Sequence

import requests

from app.security.redaction import fingerprint

from .base import (
    CredentialError,
    MappingError,
    ProviderUnavailable,
    RateLimited,
)
from .models import (
    ExternalDeviceRecord,
    ExternalSiteRecord,
    MetricFieldSpec,
    ReadingRecord,
    ReadingsPullResult,
    TestResult,
)

logger = logging.getLogger(__name__)

ALSO_ENERGY_API_BASE = "https://api.alsoenergy.com"
TOKEN_PATH = "/Auth/token"
SITES_PATH = "/Sites"
HARDWARE_PATH_TEMPLATE = "/Sites/{site_id}/Hardware"
BINDATA_PATH = "/v2/Data/BinData"

# Only verified bin size against the live API (matches the legacy pipeline).
DEFAULT_BIN_SIZE = "BinRaw"

DEFAULT_TIMEOUT_SECONDS = 15
DEFAULT_RETRIES = 2


class NativeAlsoEnergyAdapter:
    """AlsoEnergy adapter that talks to the provider REST API directly."""

    provider_key = "also_energy"
    required_credential_fields: tuple[str, ...] = ("username", "password")

    def __init__(
        self,
        *,
        http_session: Any | None = None,
        timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
        max_retries: int = DEFAULT_RETRIES,
        base_url: str = ALSO_ENERGY_API_BASE,
    ) -> None:
        # ``http_session`` is duck-typed: any object with ``.post`` and
        # ``.get`` matching ``requests`` semantics works. Tests inject
        # a fake; production uses ``requests``.
        self._session = http_session
        self._timeout = timeout_seconds
        self._retries = max_retries
        self._base_url = base_url.rstrip("/")

    # ------------------------------------------------------------------
    # ProviderAdapter API
    # ------------------------------------------------------------------

    def test_credentials(self, credentials: Mapping[str, str]) -> TestResult:
        try:
            creds = self._validate_required_fields(credentials)
            self._fetch_access_token(creds["username"], creds["password"])
        except CredentialError as exc:
            return TestResult(success=False, message=str(exc) or "Credentials rejected")
        except RateLimited as exc:
            return TestResult(success=False, message=str(exc) or "Provider rate-limited")
        except ProviderUnavailable as exc:
            return TestResult(success=False, message=str(exc) or "Provider unavailable")
        return TestResult(
            success=True,
            message="Credentials verified",
            available_sites_count=None,
        )

    def list_sites(self, credentials: Mapping[str, str]) -> Sequence[ExternalSiteRecord]:
        creds = self._validate_required_fields(credentials)
        access_token = self._fetch_access_token(creds["username"], creds["password"])
        response = self._sites_request(access_token)
        status_code = response.status_code

        if status_code == HTTPStatus.NO_CONTENT:
            return ()
        if status_code in (
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.UNAUTHORIZED,
            HTTPStatus.FORBIDDEN,
        ):
            # Token was minted moments ago, so a 4xx here usually means the
            # account lost provider-side authorization to enumerate sites.
            # Surface as CredentialError so the UI prompts re-entry.
            raise CredentialError(
                f"Provider rejected the site listing request (HTTP {status_code})",
                provider_key=self.provider_key,
            )
        if status_code == HTTPStatus.TOO_MANY_REQUESTS:
            retry_after = self._parse_retry_after(response.headers)
            raise RateLimited(
                "Provider rate-limited the site listing request",
                retry_after=retry_after,
                provider_key=self.provider_key,
            )
        if 500 <= status_code < 600:
            raise ProviderUnavailable(
                f"Provider responded with HTTP {status_code} on site listing",
                provider_key=self.provider_key,
            )
        if not (200 <= status_code < 300):
            raise ProviderUnavailable(
                f"Unexpected provider response (HTTP {status_code}) on site listing",
                provider_key=self.provider_key,
            )

        try:
            payload = response.json() or {}
        except ValueError as exc:
            raise ProviderUnavailable(
                "Provider returned an unparseable site list",
                provider_key=self.provider_key,
            ) from exc
        items = payload.get("items") or []
        return tuple(
            ExternalSiteRecord(
                external_site_id=str(item.get("siteId")),
                external_site_name=item.get("siteName"),
                raw_metadata={
                    k: v for k, v in item.items() if k not in {"siteId", "siteName"}
                },
            )
            for item in items
            if item.get("siteId") is not None
        )

    def list_devices(
        self, credentials: Mapping[str, str], external_site_id: str
    ) -> Sequence[ExternalDeviceRecord]:
        """Return the hardware devices AlsoEnergy reports for one site.

        Mirrors :meth:`list_sites`: it mints a fresh token then performs
        ``GET /Sites/{site_id}/Hardware``. Per the legacy ``rea-telemetry``
        reference, devices are returned under the ``hardware`` key with ``id``
        and ``name`` fields. An unknown site yields HTTP 404 which is surfaced
        as :class:`MappingError` (the configured site no longer resolves);
        HTTP 204 means the site simply has no hardware yet.
        """
        site_ref = str(external_site_id).strip()
        if not site_ref:
            raise MappingError(
                "No external site id supplied for device listing",
                provider_key=self.provider_key,
            )
        creds = self._validate_required_fields(credentials)
        access_token = self._fetch_access_token(creds["username"], creds["password"])
        response = self._hardware_request(access_token, site_ref)
        status_code = response.status_code

        if status_code == HTTPStatus.NO_CONTENT:
            return ()
        if status_code == HTTPStatus.NOT_FOUND:
            raise MappingError(
                "Provider does not recognise the configured site for this account",
                provider_key=self.provider_key,
            )
        if status_code in (
            HTTPStatus.BAD_REQUEST,
            HTTPStatus.UNAUTHORIZED,
            HTTPStatus.FORBIDDEN,
        ):
            # Token was minted moments ago, so a 4xx here usually means the
            # account lost provider-side authorization to enumerate hardware.
            raise CredentialError(
                f"Provider rejected the device listing request (HTTP {status_code})",
                provider_key=self.provider_key,
            )
        if status_code == HTTPStatus.TOO_MANY_REQUESTS:
            retry_after = self._parse_retry_after(response.headers)
            raise RateLimited(
                "Provider rate-limited the device listing request",
                retry_after=retry_after,
                provider_key=self.provider_key,
            )
        if 500 <= status_code < 600:
            raise ProviderUnavailable(
                f"Provider responded with HTTP {status_code} on device listing",
                provider_key=self.provider_key,
            )
        if not (200 <= status_code < 300):
            raise ProviderUnavailable(
                f"Unexpected provider response (HTTP {status_code}) on device listing",
                provider_key=self.provider_key,
            )

        try:
            payload = response.json() or {}
        except ValueError as exc:
            raise ProviderUnavailable(
                "Provider returned an unparseable device list",
                provider_key=self.provider_key,
            ) from exc
        items = payload.get("hardware") or []
        return tuple(
            ExternalDeviceRecord(
                external_device_id=str(item.get("id")),
                external_device_name=item.get("name"),
                raw_metadata={
                    k: v for k, v in item.items() if k not in {"id", "name"}
                },
            )
            for item in items
            if item.get("id") is not None
        )

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _validate_required_fields(self, credentials: Mapping[str, str]) -> dict[str, str]:
        if not isinstance(credentials, Mapping) or not any(
            (credentials or {}).get(field) for field in self.required_credential_fields
        ):
            raise CredentialError(
                "No credentials are stored for this account. "
                "Use Update Credentials to enter them.",
                provider_key=self.provider_key,
            )
        missing = [
            field for field in self.required_credential_fields if not credentials.get(field)
        ]
        if missing:
            raise CredentialError(
                f"Missing credential fields: {', '.join(missing)}. "
                "Use Update Credentials to update them.",
                provider_key=self.provider_key,
            )
        return {field: str(credentials[field]) for field in self.required_credential_fields}

    def _fetch_access_token(self, username: str, password: str) -> str:
        response = self._token_request(username, password)
        status_code = response.status_code

        # Provider convention (confirmed by the legacy native impl): the
        # OAuth token endpoint returns HTTP 400 when username/password is
        # wrong, never 401/403. Any other 4xx is treated as a credential
        # error too — we never want to surface "OK" on a bad password.
        if status_code == HTTPStatus.BAD_REQUEST:
            raise CredentialError(
                "Provider rejected credentials (HTTP 400)",
                provider_key=self.provider_key,
            )
        if status_code == HTTPStatus.TOO_MANY_REQUESTS:
            retry_after = self._parse_retry_after(response.headers)
            raise RateLimited(
                "Provider rate-limited the token request",
                retry_after=retry_after,
                provider_key=self.provider_key,
            )
        if status_code in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
            raise CredentialError(
                f"Provider rejected credentials (HTTP {status_code})",
                provider_key=self.provider_key,
            )
        if 500 <= status_code < 600:
            raise ProviderUnavailable(
                f"Provider responded with HTTP {status_code}",
                provider_key=self.provider_key,
            )
        if not (200 <= status_code < 300):
            raise ProviderUnavailable(
                f"Unexpected provider response (HTTP {status_code})",
                provider_key=self.provider_key,
            )

        try:
            payload = response.json() or {}
        except ValueError as exc:
            raise ProviderUnavailable(
                "Provider returned an unparseable token payload",
                provider_key=self.provider_key,
            ) from exc

        access_token = payload.get("access_token")
        if not access_token:
            raise ProviderUnavailable(
                "Provider response missing access_token",
                provider_key=self.provider_key,
            )
        # Log only the *fingerprint* of the token — never the value.
        logger.info(
            "telemetry_native_also_energy_token_obtained provider=%s token_fp=%s",
            self.provider_key,
            fingerprint(access_token),
        )
        return str(access_token)

    def _token_request(self, username: str, password: str) -> requests.Response:
        url = f"{self._base_url}{TOKEN_PATH}"
        # NOTE: ``data=`` is a form-encoded body. The username/password are
        # sent in the request body, not the URL. Never include them in any
        # log statement.
        return self._post_with_retry(
            url,
            data={
                "grant_type": "password",
                "username": username,
                "password": password,
            },
        )

    def _sites_request(self, access_token: str) -> requests.Response:
        url = f"{self._base_url}{SITES_PATH}"
        return self._get_with_retry(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    def _hardware_request(
        self,
        access_token: str,
        site_id: str,
        *,
        include_archived_fields: bool = False,
    ) -> requests.Response:
        url = f"{self._base_url}{HARDWARE_PATH_TEMPLATE.format(site_id=site_id)}"
        params = (
            {"includeArchivedFields": "true"} if include_archived_fields else None
        )
        return self._get_with_retry(
            url,
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
        )

    def _post_with_retry(self, url: str, *, data: Mapping[str, str]) -> requests.Response:
        return self._with_retry(lambda s: s.post(url, data=dict(data), timeout=self._timeout))

    def _get_with_retry(
        self,
        url: str,
        *,
        headers: Mapping[str, str],
        params: Mapping[str, str] | None = None,
    ) -> requests.Response:
        return self._with_retry(
            lambda s: s.get(
                url,
                headers=dict(headers),
                params=dict(params) if params else None,
                timeout=self._timeout,
            )
        )

    def _post_json_with_retry(
        self,
        url: str,
        *,
        params: Mapping[str, str],
        json_body: Any,
        headers: Mapping[str, str],
    ) -> requests.Response:
        return self._with_retry(
            lambda s: s.post(
                url,
                params=dict(params),
                json=json_body,
                headers=dict(headers),
                timeout=self._timeout,
            )
        )

    def _with_retry(self, call):
        session = self._get_session()
        last_exc: Exception | None = None
        attempts = max(1, self._retries + 1)
        for attempt in range(attempts):
            try:
                return call(session)
            except requests.RequestException as exc:
                last_exc = exc
                # Network-level failure. Don't log exception args (could
                # contain URL with a token in pathological cases).
                logger.warning(
                    "telemetry_native_also_energy_request_failed provider=%s attempt=%s exc=%s",
                    self.provider_key,
                    attempt + 1,
                    type(exc).__name__,
                )
        raise ProviderUnavailable(
            f"Provider call failed after {attempts} attempts: "
            f"{type(last_exc).__name__ if last_exc else 'RequestException'}",
            provider_key=self.provider_key,
        ) from last_exc

    def _get_session(self):
        if self._session is not None:
            return self._session
        # ``requests`` is already a transitive dep (used by helpers/cloud_function_client).
        self._session = requests.Session()
        return self._session

    @staticmethod
    def _parse_retry_after(headers: Mapping[str, str]) -> int | None:
        raw = headers.get("Retry-After") if headers else None
        if not raw:
            return None
        try:
            return int(raw)
        except (TypeError, ValueError):
            return None

    # ------------------------------------------------------------------
    # Readings capability (ReadingsAdapter)
    # ------------------------------------------------------------------

    def get_readings(
        self,
        credentials: Mapping[str, str],
        *,
        external_site_id: str,
        metric_specs: Sequence[MetricFieldSpec],
        window_start: datetime,
        window_end: datetime,
        external_device_ids: Sequence[str] | None = None,
        bin_size: str = DEFAULT_BIN_SIZE,
    ) -> ReadingsPullResult:
        """Pull normalized readings for one site. See ``ReadingsAdapter``.

        Session-fatal failures (token mint, site/device discovery) raise a
        structured exception. Per-target provider errors are accumulated on the
        result so the caller can persist partial data without wiping anything.
        """
        creds = self._validate_required_fields(credentials)
        site_ref = str(external_site_id).strip()
        if not site_ref:
            raise MappingError(
                "No external site id supplied for the readings pull",
                provider_key=self.provider_key,
            )

        if not metric_specs:
            return ReadingsPullResult(readings=tuple())

        # Token mint and device-field discovery are session-fatal: if either
        # fails we have nothing to persist, so we raise instead of returning a
        # partial result (the caller records a cleanly-failed job, no wipe).
        access_token = self._fetch_access_token(creds["username"], creds["password"])
        device_fields = self._discover_site_device_fields(access_token, site_ref)

        requested: set[str] | None = None
        if external_device_ids is not None:
            requested = {
                str(d).strip() for d in external_device_ids if str(d).strip()
            }

        target_device_ids = [
            device_id
            for device_id in device_fields
            if requested is None or device_id in requested
        ]

        readings: list[ReadingRecord] = []
        errors: list[str] = []
        targets_attempted = 0
        targets_with_data = 0
        targets_failed = 0
        targets_ambiguous = 0
        rate_limited = False
        stop = False

        for device_id in target_device_ids:
            if stop:
                break
            available = device_fields.get(device_id) or set()
            for spec in metric_specs:
                matching = [
                    (legacy, query)
                    for (legacy, query) in spec.candidates
                    if legacy in available
                ]
                if not matching:
                    # Device simply doesn't expose this metric — normal.
                    continue
                if len(matching) > 1:
                    targets_ambiguous += 1
                    logger.info(
                        "telemetry_readings_ambiguous provider=%s device=%s metric=%s candidates=%s",
                        self.provider_key,
                        device_id,
                        spec.normalized_metric,
                        len(matching),
                    )
                    continue

                legacy_field, query_field = matching[0]
                targets_attempted += 1
                try:
                    pulled = self._pull_target(
                        access_token,
                        device_id=device_id,
                        legacy_field=legacy_field,
                        query_field=query_field,
                        spec=spec,
                        window_start=window_start,
                        window_end=window_end,
                        bin_size=bin_size or DEFAULT_BIN_SIZE,
                    )
                except RateLimited:
                    rate_limited = True
                    targets_failed += 1
                    errors.append(
                        f"rate limited pulling {spec.normalized_metric} for device {device_id}"
                    )
                    stop = True
                    break
                except CredentialError:
                    # Token died mid-run. Stop and keep whatever we have.
                    targets_failed += 1
                    errors.append(
                        f"authentication lost pulling {spec.normalized_metric} for device {device_id}"
                    )
                    stop = True
                    break
                except ProviderUnavailable as exc:
                    targets_failed += 1
                    errors.append(
                        f"provider error pulling {spec.normalized_metric} for device {device_id}: {exc}"
                    )
                    continue

                if pulled:
                    readings.extend(pulled)
                    targets_with_data += 1

        return ReadingsPullResult(
            readings=tuple(readings),
            devices_seen=len(device_fields),
            targets_attempted=targets_attempted,
            targets_with_data=targets_with_data,
            targets_failed=targets_failed,
            targets_ambiguous=targets_ambiguous,
            rate_limited=rate_limited,
            errors=tuple(errors),
        )

    def _discover_site_device_fields(
        self, access_token: str, external_site_id: str
    ) -> dict[str, set[str]]:
        """Return ``{external_device_id: {legacy field names}}`` for the site.

        Uses ``includeArchivedFields=true`` so the response carries each
        device's ``fieldsArchived`` legacy names, which are what metric-spec
        candidates are matched against.
        """
        response = self._hardware_request(
            access_token, external_site_id, include_archived_fields=True
        )
        status = response.status_code

        if status == HTTPStatus.NO_CONTENT:
            return {}
        if status == HTTPStatus.NOT_FOUND:
            raise MappingError(
                "Provider does not recognise the configured site for this account",
                provider_key=self.provider_key,
            )
        if status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
            raise CredentialError(
                f"Provider rejected hardware discovery (HTTP {int(status)})",
                provider_key=self.provider_key,
            )
        if status == HTTPStatus.TOO_MANY_REQUESTS:
            raise RateLimited(
                "Provider rate-limited hardware discovery",
                retry_after=self._parse_retry_after(response.headers),
                provider_key=self.provider_key,
            )
        if 500 <= int(status) < 600:
            raise ProviderUnavailable(
                f"Provider responded with HTTP {int(status)} on hardware discovery",
                provider_key=self.provider_key,
            )
        if not (200 <= int(status) < 300):
            raise ProviderUnavailable(
                f"Unexpected provider response (HTTP {int(status)}) on hardware discovery",
                provider_key=self.provider_key,
            )

        try:
            payload = response.json() or {}
        except ValueError as exc:
            raise ProviderUnavailable(
                "Provider returned an unparseable hardware payload",
                provider_key=self.provider_key,
            ) from exc

        result: dict[str, set[str]] = {}
        for item in payload.get("hardware") or []:
            if not isinstance(item, dict):
                continue
            raw_id = item.get("id")
            if raw_id is None:
                continue
            device_id = str(raw_id).strip()
            if not device_id:
                continue
            fields = item.get("fieldsArchived") or []
            result[device_id] = {str(f) for f in fields if f is not None}
        return result

    def _pull_target(
        self,
        access_token: str,
        *,
        device_id: str,
        legacy_field: str,
        query_field: str,
        spec: MetricFieldSpec,
        window_start: datetime,
        window_end: datetime,
        bin_size: str,
    ) -> list[ReadingRecord]:
        """Pull one ``(device, metric)`` target. Returns [] for no-data.

        Raises :class:`RateLimited` / :class:`CredentialError` /
        :class:`ProviderUnavailable` for the corresponding provider responses so
        the caller can decide whether to stop or continue.
        """
        response = self._bindata_request(
            access_token,
            hardware_id=device_id,
            query_field=query_field,
            window_start=window_start,
            window_end=window_end,
            bin_size=bin_size,
        )
        status = response.status_code

        if status in (HTTPStatus.BAD_REQUEST, HTTPStatus.NO_CONTENT):
            # Provider rejected/has no data for this field+window — treat as
            # no-data (the legacy pipeline skips these silently).
            return []
        if status == HTTPStatus.TOO_MANY_REQUESTS:
            raise RateLimited(
                "Provider rate-limited the readings request",
                retry_after=self._parse_retry_after(response.headers),
                provider_key=self.provider_key,
            )
        if status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
            raise CredentialError(
                f"Provider rejected the readings request (HTTP {int(status)})",
                provider_key=self.provider_key,
            )
        if 500 <= int(status) < 600:
            raise ProviderUnavailable(
                f"Provider responded with HTTP {int(status)} on readings",
                provider_key=self.provider_key,
            )
        if not (200 <= int(status) < 300):
            raise ProviderUnavailable(
                f"Unexpected provider response (HTTP {int(status)}) on readings",
                provider_key=self.provider_key,
            )

        try:
            payload = response.json() or {}
        except ValueError as exc:
            raise ProviderUnavailable(
                "Provider returned an unparseable readings payload",
                provider_key=self.provider_key,
            ) from exc

        # Verify the response describes the field we asked for. The BinData
        # response echoes the *legacy* field name in ``info[0].name``; if it
        # doesn't match we skip rather than risk mislabelling values.
        info = payload.get("info") or []
        if len(info) != 1 or not isinstance(info[0], dict) or info[0].get("name") != legacy_field:
            logger.info(
                "telemetry_readings_field_mismatch provider=%s device=%s expected_field=%s",
                self.provider_key,
                device_id,
                legacy_field,
            )
            return []

        out: list[ReadingRecord] = []
        for item in payload.get("items") or []:
            if not isinstance(item, dict):
                continue
            data = item.get("data")
            if not isinstance(data, list) or len(data) != 1:
                continue
            metric_ts = self._parse_reading_timestamp(item.get("timestamp"))
            if metric_ts is None:
                continue
            out.append(
                ReadingRecord(
                    external_device_id=device_id,
                    normalized_metric=spec.normalized_metric,
                    unit=spec.unit,
                    provider_field=legacy_field,
                    metric_ts=metric_ts,
                    value=self._coerce_reading_value(data[0]),
                )
            )
        return out

    def _bindata_request(
        self,
        access_token: str,
        *,
        hardware_id: str,
        query_field: str,
        window_start: datetime,
        window_end: datetime,
        bin_size: str,
    ) -> requests.Response:
        url = f"{self._base_url}{BINDATA_PATH}"
        params = {
            "from": self._format_window(window_start),
            "to": self._format_window(window_end),
            "binSizes": bin_size,
        }
        body = [{"hardwareId": hardware_id, "fieldName": query_field}]
        return self._post_json_with_retry(
            url,
            params=params,
            json_body=body,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    @staticmethod
    def _format_window(value: datetime) -> str:
        """Format a window bound as the provider expects (UTC, naive wall-clock)."""
        if value.tzinfo is not None:
            value = value.astimezone(timezone.utc).replace(tzinfo=None)
        return value.strftime("%Y-%m-%dT%H:%M:%S")

    @staticmethod
    def _parse_reading_timestamp(raw: Any) -> datetime | None:
        """Parse a provider timestamp into a UTC-naive datetime, or None."""
        if not raw:
            return None
        try:
            parsed = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def _coerce_reading_value(raw: Any) -> float:
        """Coerce a provider data point to float; NaN/None/blank -> 0.0.

        Matches the legacy pipeline: missing or ``"NaN"`` samples become 0.0.
        """
        if raw is None:
            return 0.0
        if isinstance(raw, str):
            stripped = raw.strip()
            if not stripped or stripped.lower() == "nan":
                return 0.0
            try:
                raw = float(stripped)
            except ValueError:
                return 0.0
        try:
            value = float(raw)
        except (TypeError, ValueError):
            return 0.0
        if value != value:  # float('nan')
            return 0.0
        return round(value, 9)
