"""Read-only device eligibility / Path-B diagnostics schemas (additive).

These power a strictly read-only "why can't this device drive expected yet?" view.
They DISCLOSE the position of each device in the eligibility → mapping → weather-
semantics chain; they never change eligibility, mapping, weather semantics, the
resolver, or the expected math. Mirrors the weather-readiness diagnostics shape
(``blocking_level`` + indicator glossary keys the FE renders as "why" tips).
"""
from __future__ import annotations

import enum
from typing import Optional

from pydantic import BaseModel


class DiagnosticBlockingLevel(str, enum.Enum):
    """How severely an indicator limits the device's telemetry usefulness.

    Ordered most→least severe. ``blocks_calculation`` means a value the expected/
    O&M path needs cannot be produced; ``lowers_confidence`` means data flows but a
    semantic/quality gap weakens it; ``informational`` is a benign disclosure.
    """

    blocks_calculation = "blocks_calculation"
    lowers_confidence = "lowers_confidence"
    informational = "informational"


_SEVERITY_ORDER = {
    DiagnosticBlockingLevel.blocks_calculation: 0,
    DiagnosticBlockingLevel.lowers_confidence: 1,
    DiagnosticBlockingLevel.informational: 2,
}


class DiagnosticIndicator(BaseModel):
    """A single Path-B "why" item for a device (or site-level rollup)."""

    key: str
    label: str
    explanation: str
    blocking_level: DiagnosticBlockingLevel
    recommended_action: Optional[str] = None


class DeviceWeatherSemantics(BaseModel):
    """Disclosed weather measurement semantics for a weather-source device.

    Reflects the latest ``weather_device_mappings`` declaration verbatim. Never
    inferred or converted: ``physics_usable_*`` only report whether the *declared*
    plane/temperature is usable by the physics today (POA / cell-usable)."""

    has_declaration: bool
    metric: Optional[str] = None
    irradiance_plane: str
    temperature_type: str
    calibration_status: str
    physics_usable_irradiance: bool
    physics_usable_temperature: bool
    # WS.3 — read-only stale / upstream-change disclosure. Never a status, never a
    # gate: ``needs_re_review`` is the persisted monotonic flag;
    # ``upstream_change_detected`` is a live (uncommitted) fingerprint comparison.
    needs_re_review: bool = False
    re_review_reason: Optional[str] = None
    upstream_change_detected: bool = False
    upstream_changed_keys: list[str] = []


class DeviceEligibilityDiagnostic(BaseModel):
    """Per-device eligibility/mapping/semantics position + Path-B indicators."""

    device_id: int
    name: Optional[str] = None
    category: Optional[str] = None
    device_role: Optional[str] = None
    mappable: bool
    can_drive_expected: bool
    telemetry_capable: bool
    weather_source_capable: bool
    production_meter_capable: bool
    gateway_capable: bool
    virtual_device: bool
    mapped_status: str
    is_mapped: bool
    source_provider: Optional[str] = None
    external_device_type: Optional[str] = None
    eligibility_reason: Optional[str] = None
    ineligibility_reason: Optional[str] = None
    weather_semantics: Optional[DeviceWeatherSemantics] = None
    indicators: list[DiagnosticIndicator] = []


class DeviceEligibilityDiagnosticsResponse(BaseModel):
    """Site-level eligibility diagnostics (read-only).

    ``indicators`` is a deduped site-level rollup of the distinct Path-B items
    across the site's devices (most-severe ``blocking_level`` per key)."""

    site_id: int
    total_devices: int
    mappable_count: int
    mapped_count: int
    unmapped_eligible_count: int
    expected_driving_count: int
    weather_source_count: int
    meter_count: int
    gateway_count: int
    virtual_count: int
    ineligible_count: int
    weather_unknown_semantics_count: int
    devices: list[DeviceEligibilityDiagnostic] = []
    indicators: list[DiagnosticIndicator] = []


def severity_rank(level: DiagnosticBlockingLevel) -> int:
    """Lower rank == more severe (for picking the most-severe rollup level)."""
    return _SEVERITY_ORDER[level]
