"""Abstract weather provider adapter interface and structured exceptions.

Mirrors ``app/integrations/telemetry/base.py``. The interface is intentionally
small — declare capabilities, test reachability/credentials, and pull a bounded
window of observations. Adapters map provider-specific HTTP errors onto the
structured exceptions here so callers never inspect provider status codes.

Context-only contract: an adapter reports honest measurement semantics and
NEVER asserts an external source is physics-/expected-eligible. The framework
does not transpose GHI→POA or convert ambient→cell anywhere.
"""
from __future__ import annotations

from datetime import datetime
from typing import Mapping, Protocol, Sequence, runtime_checkable

from .models import TestResult, WeatherProviderCapabilities, WeatherPullResult


# ---------------------------------------------------------------------------
# Structured exceptions
# ---------------------------------------------------------------------------
class WeatherProviderError(Exception):
    """Base class for all weather provider errors."""

    def __init__(self, message: str = "", *, provider_key: str | None = None) -> None:
        super().__init__(message)
        self.provider_key = provider_key


class WeatherCredentialError(WeatherProviderError):
    """Provider rejected the supplied credentials (HTTP 401/403 typically)."""


class WeatherNoData(WeatherProviderError):
    """Provider responded successfully but returned no data for the request."""


class WeatherProviderUnavailable(WeatherProviderError):
    """Transport-level failure or 5xx response — the provider is unreachable."""


class WeatherRateLimited(WeatherProviderError):
    """Provider returned a rate-limit response (HTTP 429)."""

    def __init__(
        self,
        message: str = "",
        *,
        retry_after: int | None = None,
        provider_key: str | None = None,
    ) -> None:
        super().__init__(message, provider_key=provider_key)
        self.retry_after = retry_after


class WeatherMappingError(WeatherProviderError):
    """A request refers to a location/site the provider cannot resolve."""


# ---------------------------------------------------------------------------
# Adapter Protocol
# ---------------------------------------------------------------------------
@runtime_checkable
class WeatherProviderAdapter(Protocol):
    """Interface implemented by every third-party weather vendor adapter."""

    provider_key: str

    def capabilities(self) -> WeatherProviderCapabilities:
        """Return the adapter's self-declared capabilities (no I/O)."""

    def test_credentials(self, credentials: Mapping[str, str]) -> TestResult:
        """Verify reachability/credentials.

        Keyless providers report "no credentials required"; keyed providers
        should raise :class:`WeatherCredentialError` on auth failure.
        """

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
        """Pull a bounded window of observations for a lat/lon.

        ``window_start``/``window_end`` are naive-UTC. Implementations map
        provider HTTP errors onto the structured exceptions above:

        - auth failure -> :class:`WeatherCredentialError`,
        - unknown location -> :class:`WeatherMappingError`,
        - rate limiting -> :class:`WeatherRateLimited`,
        - 5xx / transport failure -> :class:`WeatherProviderUnavailable`,
        - empty body -> a :class:`WeatherPullResult` with no rows (or
          :class:`WeatherNoData` for a hard "no coverage" signal).
        """
