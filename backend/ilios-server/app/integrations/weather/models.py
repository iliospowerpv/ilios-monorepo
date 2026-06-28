"""Value objects exchanged between weather provider adapters and the app.

These intentionally use plain ``str`` for measurement semantics (irradiance
plane / temperature type / confidence) so the adapter layer never imports the
ORM enums and stays cycle-free. The import service validates the strings against
``app.models.weather`` enums at the service boundary (mirroring the file-import
path), which is also where any "never guess / never convert" invariants live.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class TestResult:
    """Outcome of an adapter ``test_credentials`` call.

    For keyless providers (e.g. Open-Meteo) this reports reachability/"no
    credentials required" rather than an authentication result.
    """

    success: bool
    message: str
    detail: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RateLimitSpec:
    """Declared rate/quota limits for a provider (advisory, enforced by callers)."""

    requests_per_minute: int | None = None
    requests_per_day: int | None = None
    max_concurrent: int | None = None


@dataclass(frozen=True)
class WeatherProviderCapabilities:
    """A provider adapter's self-declared capabilities.

    ``native_plane`` / ``native_temperature_type`` are honest descriptions of
    what the provider's irradiance/temperature actually MEAN (e.g. ``"ghi"`` /
    ``"ambient"``); the adapter must never label GHI as POA or ambient as cell.

    ``expected_eligible_capable`` is a derived, read-only flag that is ALWAYS
    ``False`` for every provider in Phases A–D. Only a future, separately
    approved governed physics model (transposition + temperature) could ever
    flip it — never a provider adapter on its own.
    """

    supports_historical: bool
    supports_forecast: bool
    metrics: frozenset[str]
    native_plane: str = "unknown"
    native_temperature_type: str = "unknown"
    is_modeled: bool = True
    min_granularity_minutes: int = 60
    max_history_days: int | None = None
    rate_limit: RateLimitSpec = field(default_factory=RateLimitSpec)
    licensing_class: str = "unknown"

    @property
    def expected_eligible_capable(self) -> bool:
        """FROZEN to False in Phases A–D. External weather is context-only."""
        return False

    def to_json(self) -> dict[str, Any]:
        """A JSON-safe snapshot for the catalog ``capabilities_json`` column."""
        return {
            "supports_historical": self.supports_historical,
            "supports_forecast": self.supports_forecast,
            "metrics": sorted(self.metrics),
            "native_plane": self.native_plane,
            "native_temperature_type": self.native_temperature_type,
            "is_modeled": self.is_modeled,
            "min_granularity_minutes": self.min_granularity_minutes,
            "max_history_days": self.max_history_days,
            "rate_limit": {
                "requests_per_minute": self.rate_limit.requests_per_minute,
                "requests_per_day": self.rate_limit.requests_per_day,
                "max_concurrent": self.rate_limit.max_concurrent,
            },
            "licensing_class": self.licensing_class,
            "expected_eligible_capable": self.expected_eligible_capable,
        }


@dataclass(frozen=True)
class NormalizedWeatherRow:
    """One normalized observation produced by an adapter.

    ``obs_ts`` is naive-UTC (the existing storage convention). Semantics are
    plain strings validated downstream; nothing here is ever converted.
    """

    obs_ts: datetime
    metric: str
    value: float
    unit: str | None = None
    irradiance_plane: str = "unknown"
    temperature_type: str = "unknown"
    is_modeled: bool = True
    confidence: str = "unknown"
    source_row_id: str | None = None


@dataclass(frozen=True)
class WeatherPullResult:
    """Best-effort outcome of a :meth:`WeatherProviderAdapter.get_observations`.

    Partial-failure tolerant: a per-metric/per-window failure is recorded on
    ``warnings``/``errors`` and ``partial=True`` rather than aborting the whole
    pull, so the import service can persist whatever was retrieved and report an
    honest status. ``errors`` strings never contain secrets. A genuinely missing
    reading is the ABSENCE of a row — never a fabricated/zero value.
    """

    rows: tuple[NormalizedWeatherRow, ...] = ()
    partial: bool = False
    warnings: tuple[str, ...] = ()
    errors: tuple[str, ...] = ()
    request_hash: str | None = None
    response_hash: str | None = None
    api_version: str | None = None
