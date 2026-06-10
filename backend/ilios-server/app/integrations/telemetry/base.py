"""Abstract provider adapter interface and structured exceptions.

Adapters wrap third-party DAS vendors. The interface is intentionally tiny —
test credentials and list external sites — so it is easy to add new vendors.
Richer telemetry queries (BigQuery, etc.) remain in their existing modules
and are out of scope for Phase 1.
"""
from __future__ import annotations

from datetime import datetime
from typing import Mapping, Protocol, Sequence, runtime_checkable

from .models import (
    ExternalDeviceRecord,
    ExternalSiteRecord,
    MetricFieldSpec,
    ReadingsPullResult,
    TestResult,
)


# ---------------------------------------------------------------------------
# Structured exceptions
# ---------------------------------------------------------------------------


class ProviderError(Exception):
    """Base class for all telemetry provider errors."""

    def __init__(self, message: str = "", *, provider_key: str | None = None) -> None:
        super().__init__(message)
        self.provider_key = provider_key


class CredentialError(ProviderError):
    """Provider rejected the supplied credentials (HTTP 401/403 typically)."""


class NoData(ProviderError):
    """Provider responded successfully but returned no data for the request."""


class ProviderUnavailable(ProviderError):
    """Transport-level failure or 5xx response — the provider is unreachable."""


class RateLimited(ProviderError):
    """Provider returned a rate-limit response (HTTP 429)."""

    def __init__(self, message: str = "", *, retry_after: int | None = None, provider_key: str | None = None) -> None:
        super().__init__(message, provider_key=provider_key)
        self.retry_after = retry_after


class MappingError(ProviderError):
    """A configured mapping refers to an external entity the provider does not recognise."""


# ---------------------------------------------------------------------------
# Adapter Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class ProviderAdapter(Protocol):
    """Interface implemented by every telemetry vendor adapter."""

    provider_key: str

    def test_credentials(self, credentials: dict[str, str]) -> TestResult:
        """Verify credentials. Should raise :class:`CredentialError` on auth failure."""

    def list_sites(self, credentials: dict[str, str]) -> Sequence[ExternalSiteRecord]:
        """Return all external sites the credentialed account can see.

        Implementations should map provider-specific HTTP errors onto the
        structured exceptions in this module so callers never need to inspect
        provider-specific status codes.
        """


@runtime_checkable
class DeviceListingAdapter(Protocol):
    """Optional capability: enumerate the devices under one external site.

    This is intentionally a *separate* Protocol from :class:`ProviderAdapter`.
    Not every vendor adapter exposes per-site device listing, and adding the
    method to the base Protocol would silently break ``isinstance`` checks for
    adapters that only implement credential/site listing. Callers should guard
    with ``isinstance(adapter, DeviceListingAdapter)`` before invoking.
    """

    provider_key: str

    def list_devices(
        self, credentials: dict[str, str], external_site_id: str
    ) -> Sequence[ExternalDeviceRecord]:
        """Return the devices the provider reports for ``external_site_id``.

        Implementations should map provider-specific HTTP errors onto the
        structured exceptions in this module:

        - the site is unknown to the provider -> :class:`MappingError`,
        - the provider returns an empty body -> an empty sequence,
        - auth failure -> :class:`CredentialError`,
        - rate limiting -> :class:`RateLimited`,
        - 5xx / transport failure -> :class:`ProviderUnavailable`.
        """


@runtime_checkable
class ReadingsAdapter(Protocol):
    """Optional capability: pull normalized time-series readings for one site.

    Kept as a *separate* Protocol from :class:`ProviderAdapter` for the same
    reason as :class:`DeviceListingAdapter`: not every vendor adapter can pull
    readings, and folding it into the base Protocol would silently break
    ``isinstance`` checks. Callers must guard with
    ``isinstance(adapter, ReadingsAdapter)`` before invoking.

    The method is *best-effort and partial-failure tolerant*: per-target
    provider errors are accumulated on the returned
    :class:`~app.integrations.telemetry.models.ReadingsPullResult` rather than
    aborting the whole pull, so an ingestion run can persist whatever was
    retrieved. Only session-fatal failures (token mint, site/device discovery)
    raise a structured exception:

    - auth failure -> :class:`CredentialError`,
    - the site is unknown to the provider -> :class:`MappingError`,
    - rate limiting on the *initial* requests -> :class:`RateLimited`,
    - 5xx / transport failure on discovery -> :class:`ProviderUnavailable`.
    """

    provider_key: str

    def get_readings(
        self,
        credentials: Mapping[str, str],
        *,
        external_site_id: str,
        metric_specs: Sequence[MetricFieldSpec],
        window_start: datetime,
        window_end: datetime,
        external_device_ids: Sequence[str] | None = None,
        bin_size: str = "BinRaw",
    ) -> ReadingsPullResult:
        """Pull readings for ``metric_specs`` across the site's devices.

        ``external_device_ids`` restricts the pull to those provider device
        ids; ``None`` means "every device the provider reports for the site".
        ``bin_size`` is passed through to the provider's binning parameter;
        ``BinRaw`` is the only value verified against the live API, other bin
        sizes are provider-dependent pass-throughs.
        """
