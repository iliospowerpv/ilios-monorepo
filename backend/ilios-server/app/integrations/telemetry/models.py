"""Value objects exchanged between adapters and the rest of the app."""
from __future__ import annotations

from dataclasses import dataclass, field
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
