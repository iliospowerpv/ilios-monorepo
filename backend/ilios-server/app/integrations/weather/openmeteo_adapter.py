"""Open-Meteo weather provider adapter (keyless, free tier).

Open-Meteo (https://open-meteo.com) needs NO API key for its historical archive
endpoint, which is why it is the reference adapter for the framework: it lets us
exercise the full pull/normalize/persist path with zero secrets and zero paid
commitment. It is seeded ``is_enabled=false`` so it stays dark until an operator
explicitly turns it on.

Context-only mapping — this adapter is deliberately conservative about meaning:

* ``shortwave_radiation`` is GLOBAL HORIZONTAL irradiance (GHI). It is emitted
  with ``irradiance_plane="ghi"`` and is NEVER labelled POA. No transposition is
  performed here or anywhere downstream.
* ``temperature_2m`` is AMBIENT air temperature. It is emitted with
  ``temperature_type="ambient"`` and is NEVER labelled cell/module.
* Everything is ``is_modeled=True`` (Open-Meteo reanalysis/forecast is a model,
  not a calibrated on-site sensor) and ``confidence="unknown"`` — we never
  overstate confidence in external data.

Network access is isolated behind an injectable ``fetcher`` so unit tests run
against recorded fixtures with no live HTTP.
"""
from __future__ import annotations

import hashlib
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Callable, Mapping, Sequence

from .base import (
    WeatherCredentialError,
    WeatherMappingError,
    WeatherProviderUnavailable,
    WeatherRateLimited,
)
from .models import (
    NormalizedWeatherRow,
    RateLimitSpec,
    TestResult,
    WeatherProviderCapabilities,
    WeatherPullResult,
)

# Fetcher returns (status_code, raw_body_bytes). Injected in tests.
Fetcher = Callable[[str], "tuple[int, bytes]"]

_API_VERSION = "open-meteo-archive-v1"
_REQUEST_TIMEOUT_SECONDS = 30


class OpenMeteoAdapter:
    """Keyless adapter for the Open-Meteo historical archive API."""

    provider_key = "open_meteo"
    ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

    # Canonical metric name -> Open-Meteo hourly variable name.
    _METRIC_TO_VARIABLE: dict[str, str] = {
        "ghi_irradiance": "shortwave_radiation",
        "air_temperature": "temperature_2m",
    }
    # Open-Meteo hourly variable -> honest normalized semantics. GHI stays GHI;
    # ambient stays ambient. Nothing here is ever POA or cell.
    _VARIABLE_SEMANTICS: dict[str, dict[str, str]] = {
        "shortwave_radiation": {
            "metric": "ghi_irradiance",
            "irradiance_plane": "ghi",
            "temperature_type": "unknown",
            "unit": "W/m2",
        },
        "temperature_2m": {
            "metric": "air_temperature",
            "irradiance_plane": "unknown",
            "temperature_type": "ambient",
            "unit": "degC",
        },
    }

    def __init__(self, fetcher: Fetcher | None = None) -> None:
        self._fetcher = fetcher or self._default_fetch

    # -- capabilities -------------------------------------------------------
    def capabilities(self) -> WeatherProviderCapabilities:
        return WeatherProviderCapabilities(
            supports_historical=True,
            supports_forecast=False,
            metrics=frozenset(self._METRIC_TO_VARIABLE.keys()),
            native_plane="ghi",
            native_temperature_type="ambient",
            is_modeled=True,
            min_granularity_minutes=60,
            max_history_days=None,
            rate_limit=RateLimitSpec(
                requests_per_minute=60,
                requests_per_day=5000,
                max_concurrent=1,
            ),
            # Open-Meteo data is free for non-commercial use with attribution
            # (CC BY 4.0); commercial use requires their paid subscription.
            licensing_class="free_noncommercial",
        )

    # -- credentials --------------------------------------------------------
    def test_credentials(self, credentials: Mapping[str, str]) -> TestResult:
        # Keyless: there is nothing to authenticate. We deliberately do NOT make
        # a network call here so the "test" is deterministic and offline-safe.
        return TestResult(
            success=True,
            message="Open-Meteo is keyless; no API credentials are required.",
            detail={"keyless": True},
        )

    # -- pull ---------------------------------------------------------------
    def get_observations(
        self,
        credentials: Mapping[str, str],
        *,
        latitude: float,
        longitude: float,
        window_start: datetime,
        window_end: datetime,
        requested_metrics: Sequence[str],
        granularity: str = "hourly",
    ) -> WeatherPullResult:
        variables, warnings = self._resolve_variables(requested_metrics)
        if not variables:
            return WeatherPullResult(
                rows=(),
                partial=bool(warnings),
                warnings=tuple(warnings),
                api_version=_API_VERSION,
            )

        url = self._build_url(latitude, longitude, window_start, window_end, variables)
        request_hash = hashlib.sha256(url.encode("utf-8")).hexdigest()

        status_code, body = self._fetcher(url)
        self._raise_for_status(status_code, body)
        response_hash = hashlib.sha256(body or b"").hexdigest()

        try:
            payload = json.loads(body.decode("utf-8"))
        except (ValueError, UnicodeDecodeError) as exc:
            raise WeatherProviderUnavailable(
                f"Open-Meteo returned an unparseable response: {exc}",
                provider_key=self.provider_key,
            ) from exc

        rows = self.parse_response(
            payload,
            requested_variables=set(variables),
            window_start=window_start,
            window_end=window_end,
        )
        return WeatherPullResult(
            rows=tuple(rows),
            partial=bool(warnings),
            warnings=tuple(warnings),
            request_hash=request_hash,
            response_hash=response_hash,
            api_version=_API_VERSION,
        )

    # -- pure parsing (fixture-tested, no I/O) ------------------------------
    def parse_response(
        self,
        payload: Mapping[str, object],
        *,
        requested_variables: set[str],
        window_start: datetime | None = None,
        window_end: datetime | None = None,
    ) -> list[NormalizedWeatherRow]:
        """Normalize an Open-Meteo archive JSON payload into observations.

        ``None`` values (Open-Meteo's representation of a missing reading) are
        SKIPPED — a missing reading is the absence of a row, never a zero.
        """
        hourly = payload.get("hourly") or {}
        if not isinstance(hourly, Mapping):
            return []
        times = hourly.get("time") or []
        units = payload.get("hourly_units") or {}
        rows: list[NormalizedWeatherRow] = []

        for variable in requested_variables:
            semantics = self._VARIABLE_SEMANTICS.get(variable)
            if semantics is None:
                continue
            values = hourly.get(variable)
            if not isinstance(values, list):
                continue
            unit = (
                units.get(variable)
                if isinstance(units, Mapping)
                else None
            ) or semantics["unit"]
            for raw_ts, value in zip(times, values):
                if value is None:
                    continue
                ts = self._parse_ts(raw_ts)
                if ts is None:
                    continue
                if window_start is not None and ts < window_start:
                    continue
                if window_end is not None and ts > window_end:
                    continue
                try:
                    numeric = float(value)
                except (TypeError, ValueError):
                    continue
                rows.append(
                    NormalizedWeatherRow(
                        obs_ts=ts,
                        metric=semantics["metric"],
                        value=numeric,
                        unit=unit,
                        irradiance_plane=semantics["irradiance_plane"],
                        temperature_type=semantics["temperature_type"],
                        is_modeled=True,
                        confidence="unknown",
                        source_row_id=f"{variable}@{ts.isoformat()}",
                    )
                )
        return rows

    # -- helpers ------------------------------------------------------------
    def _resolve_variables(
        self, requested_metrics: Sequence[str]
    ) -> "tuple[list[str], list[str]]":
        variables: list[str] = []
        warnings: list[str] = []
        for metric in requested_metrics:
            if metric in self._METRIC_TO_VARIABLE:
                variables.append(self._METRIC_TO_VARIABLE[metric])
            elif metric in self._VARIABLE_SEMANTICS:
                variables.append(metric)
            else:
                warnings.append(f"Unsupported metric for Open-Meteo: {metric!r}")
        # Preserve order, drop duplicates.
        seen: set[str] = set()
        deduped = [v for v in variables if not (v in seen or seen.add(v))]
        return deduped, warnings

    def _build_url(
        self,
        latitude: float,
        longitude: float,
        window_start: datetime,
        window_end: datetime,
        variables: Sequence[str],
    ) -> str:
        params = {
            "latitude": f"{latitude:.6f}",
            "longitude": f"{longitude:.6f}",
            "start_date": window_start.date().isoformat(),
            "end_date": window_end.date().isoformat(),
            "hourly": ",".join(variables),
            "timezone": "UTC",
        }
        return f"{self.ARCHIVE_URL}?{urllib.parse.urlencode(params)}"

    @staticmethod
    def _parse_ts(raw_ts: object) -> datetime | None:
        if not isinstance(raw_ts, str):
            return None
        candidate = raw_ts.strip()
        if candidate.endswith("Z"):
            candidate = candidate[:-1]
        try:
            parsed = datetime.fromisoformat(candidate)
        except ValueError:
            return None
        # Store naive-UTC (drop any tzinfo) to match the storage convention.
        if parsed.tzinfo is not None:
            parsed = parsed.astimezone(tz=None).replace(tzinfo=None)
        return parsed.replace(tzinfo=None)

    def _raise_for_status(self, status_code: int, body: bytes) -> None:
        if status_code == 200:
            return
        reason = self._safe_reason(body)
        if status_code in (401, 403):
            raise WeatherCredentialError(
                f"Open-Meteo rejected the request ({status_code}): {reason}",
                provider_key=self.provider_key,
            )
        if status_code == 429:
            raise WeatherRateLimited(
                f"Open-Meteo rate limit reached: {reason}",
                provider_key=self.provider_key,
            )
        if status_code == 400:
            # Open-Meteo returns 400 for an out-of-range/invalid location window.
            raise WeatherMappingError(
                f"Open-Meteo could not service the request ({status_code}): {reason}",
                provider_key=self.provider_key,
            )
        raise WeatherProviderUnavailable(
            f"Open-Meteo is unavailable ({status_code}): {reason}",
            provider_key=self.provider_key,
        )

    @staticmethod
    def _safe_reason(body: bytes) -> str:
        try:
            data = json.loads((body or b"").decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            return "no detail"
        if isinstance(data, Mapping):
            return str(data.get("reason") or data.get("error") or "no detail")
        return "no detail"

    def _default_fetch(self, url: str) -> "tuple[int, bytes]":
        request = urllib.request.Request(url, headers={"Accept": "application/json"})
        try:
            with urllib.request.urlopen(
                request, timeout=_REQUEST_TIMEOUT_SECONDS
            ) as response:
                return response.status, response.read()
        except urllib.error.HTTPError as exc:  # pragma: no cover - network path
            return exc.code, exc.read()
        except urllib.error.URLError as exc:  # pragma: no cover - network path
            raise WeatherProviderUnavailable(
                f"Open-Meteo request failed: {exc.reason}",
                provider_key=self.provider_key,
            ) from exc
