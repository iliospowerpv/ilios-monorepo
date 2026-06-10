"""Value objects exchanged between adapters and the rest of the app."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(frozen=True)
class ExternalSiteRecord:
    """A single external site as reported by a provider."""

    external_site_id: str
    external_site_name: str | None = None
    raw_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExternalDeviceRecord:
    """A single external device (hardware) as reported by a provider.

    Devices are always scoped to a parent external site; the provider returns
    them per-site, so this value object intentionally carries only the device's
    own identity plus any extra provider metadata. The owning
    ``external_site_id`` is tracked by the caller, not duplicated here.
    """

    external_device_id: str
    external_device_name: str | None = None
    raw_metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TestResult:
    """Outcome of an adapter ``test_credentials`` call."""

    success: bool
    message: str
    available_sites_count: int | None = None


# ---------------------------------------------------------------------------
# Readings capability value objects
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MetricFieldSpec:
    """A normalized metric and the provider field candidates that produce it.

    ``candidates`` is a tuple of ``(provider_field_name, provider_query_field)``
    pairs, where:

    * ``provider_field_name`` is the legacy/short field name as it appears in a
      device's ``fieldsArchived`` list. It is matched against the device's
      available fields and is echoed back in the BinData response
      ``info[0].name``.
    * ``provider_query_field`` is the canonical field name sent as the BinData
      request ``fieldName``.

    Multiple candidates exist when a normalized metric can come from more than
    one provider field (e.g. AlsoEnergy ``Sun``/POA and ``Sun2``/GHI both map to
    ``irradiance_wm2``). If a single device exposes more than one candidate the
    metric is *ambiguous* for that device and is skipped — matching the legacy
    pipeline.
    """

    normalized_metric: str
    unit: str
    candidates: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class ReadingRecord:
    """A single normalized reading returned by a :class:`ReadingsAdapter`.

    ``metric_ts`` is UTC and timezone-naive (to match the storage schema).
    ``provider_field`` is the legacy field name actually pulled (one of the
    candidate ``provider_field_name`` values), preserved as provenance.
    """

    external_device_id: str
    normalized_metric: str
    unit: str
    provider_field: str
    metric_ts: datetime
    value: float


@dataclass(frozen=True)
class ReadingsPullResult:
    """Best-effort outcome of a :meth:`ReadingsAdapter.get_readings` call.

    The adapter is partial-failure tolerant: per-target provider errors are
    recorded here rather than aborting the whole pull, so the ingestion service
    can persist whatever was retrieved and surface an accurate status. Only
    session-fatal failures (token mint / site discovery) raise.

    Counters are at *target* granularity, where a target is one
    ``(device, normalized_metric)`` pull:

    * ``targets_attempted`` — pulls issued (exactly one candidate field matched).
    * ``targets_with_data`` — pulls that returned at least one reading.
    * ``targets_failed`` — pulls that errored after retries (transport/5xx/
      unexpected) or whose response failed verification.
    * ``targets_ambiguous`` — skipped because >1 candidate field matched.
    * ``rate_limited`` — True if the pull stopped early due to a 429.

    ``errors`` holds human-readable messages that never contain secrets.
    """

    readings: tuple[ReadingRecord, ...]
    devices_seen: int = 0
    targets_attempted: int = 0
    targets_with_data: int = 0
    targets_failed: int = 0
    targets_ambiguous: int = 0
    rate_limited: bool = False
    errors: tuple[str, ...] = field(default_factory=tuple)
