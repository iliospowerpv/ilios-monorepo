"""Path-B device eligibility diagnostics — read-only, additive.

Answers, for every device on a site, "where does this device sit in the
eligibility → mapping → weather-semantics chain, and what (if anything) keeps it
from driving expected performance?" It mirrors the weather-readiness diagnostics
shape: each gap is surfaced as a glossary-keyed :class:`DiagnosticIndicator` with a
``blocking_level`` and a ``recommended_action``.

It is strictly READ-ONLY: it performs no writes/commits, never mutates eligibility,
mapping, or weather semantics, never converts weather readings, and never changes
the resolver or expected math. It only DISCLOSES the current position so the UI can
explain it. ``can_drive_expected`` stays the frozen stable-three predicate; a
mappable meter/logger/gateway is reported as inspection-only, never as a driver.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.crud.weather import WeatherDeviceMappingCRUD
from app.schema.device_eligibility import (
    DeviceEligibilityDiagnostic,
    DeviceEligibilityDiagnosticsResponse,
    DeviceWeatherSemantics,
    DiagnosticBlockingLevel,
    DiagnosticIndicator,
    severity_rank,
)
from app.schema.weather import (
    _PHYSICS_USABLE_PLANES,
    _PHYSICS_USABLE_TEMPERATURES,
)
from app.services.telemetry.device_classification import classify_device
from app.services.weather.upstream_fingerprint import (
    compare_fingerprint,
    compute_upstream_fingerprint,
)

# --- Indicator glossary keys (FE renders these as "why" tips) ---------------
IND_EXPECTED_DRIVER_UNMAPPED = "expected_driver_unmapped"
IND_MAPPABLE_UNMAPPED = "mappable_unmapped"
IND_WEATHER_SEMANTICS_UNDECLARED = "weather_semantics_undeclared"
IND_WEATHER_SEMANTICS_UNKNOWN = "weather_semantics_unknown"
IND_WEATHER_NOT_PHYSICS_USABLE = "weather_not_physics_usable"
IND_WEATHER_CALIBRATION_UNKNOWN = "weather_calibration_unknown"
IND_WEATHER_SEMANTICS_STALE = "weather_semantics_stale"
IND_METER_INSPECTION_ONLY = "meter_inspection_only"
IND_GATEWAY_INSPECTION_ONLY = "gateway_inspection_only"
IND_VIRTUAL_AGGREGATION = "virtual_aggregation_device"
IND_DEVICE_INELIGIBLE = "device_ineligible"


def _ind(
    key: str,
    label: str,
    explanation: str,
    level: DiagnosticBlockingLevel,
    action: Optional[str] = None,
) -> DiagnosticIndicator:
    return DiagnosticIndicator(
        key=key,
        label=label,
        explanation=explanation,
        blocking_level=level,
        recommended_action=action,
    )


def _current_weather_semantics(
    db: Session, device
) -> Optional[DeviceWeatherSemantics]:
    """Latest declared weather mapping for the device, disclosed verbatim.

    Also surfaces the WS.3 stale signal (read-only): the persisted
    ``needs_re_review`` flag plus a LIVE upstream-fingerprint comparison
    (``upstream_change_detected``) so the UI can show "this declaration may be out
    of date" without any write or inference. The comparison is pure — a missing
    stored fingerprint never diverges (no baseline to compare against).
    """
    mapping = WeatherDeviceMappingCRUD(db).get_current_for_device(device.id)
    if mapping is None:
        return DeviceWeatherSemantics(
            has_declaration=False,
            metric=None,
            irradiance_plane="unknown",
            temperature_type="unknown",
            calibration_status="unknown",
            physics_usable_irradiance=False,
            physics_usable_temperature=False,
        )
    plane = mapping.irradiance_plane
    temp = mapping.temperature_type

    def _ev(v):
        return v.value if hasattr(v, "value") else v

    comparison = compare_fingerprint(
        getattr(mapping, "upstream_fingerprint_json", None),
        compute_upstream_fingerprint(device, mapping),
    )

    return DeviceWeatherSemantics(
        has_declaration=True,
        metric=mapping.metric,
        irradiance_plane=_ev(plane),
        temperature_type=_ev(temp),
        calibration_status=_ev(mapping.calibration_status),
        physics_usable_irradiance=plane in _PHYSICS_USABLE_PLANES,
        physics_usable_temperature=temp in _PHYSICS_USABLE_TEMPERATURES,
        needs_re_review=bool(getattr(mapping, "needs_re_review", False)),
        re_review_reason=getattr(mapping, "re_review_reason", None),
        upstream_change_detected=bool(comparison["diverged"]),
        upstream_changed_keys=list(comparison["changed_keys"]),
    )


def _device_indicators(
    cls, is_mapped: bool, semantics: Optional[DeviceWeatherSemantics]
) -> list[DiagnosticIndicator]:
    """Build the Path-B indicator list for one classified device."""
    indicators: list[DiagnosticIndicator] = []

    if not cls.mappable:
        indicators.append(
            _ind(
                IND_DEVICE_INELIGIBLE,
                "Not telemetry-eligible",
                cls.ineligibility_reason
                or "This device category cannot be mapped to a DAS/provider device.",
                DiagnosticBlockingLevel.informational,
            )
        )
        return indicators

    # Mapping gaps.
    if not is_mapped:
        if cls.can_drive_expected:
            indicators.append(
                _ind(
                    IND_EXPECTED_DRIVER_UNMAPPED,
                    "Unmapped expected driver",
                    "This device drives expected performance but is not mapped to a "
                    "provider device, so no readings can flow.",
                    DiagnosticBlockingLevel.blocks_calculation,
                    "Map this device to its provider/DAS device.",
                )
            )
        else:
            indicators.append(
                _ind(
                    IND_MAPPABLE_UNMAPPED,
                    "Mappable but unmapped",
                    "This device is eligible for telemetry inspection but is not "
                    "mapped yet, so no data is collected for it.",
                    DiagnosticBlockingLevel.informational,
                    "Map this device if you want to inspect its readings.",
                )
            )

    # Weather-source semantics gaps (never guessed/converted — only disclosed).
    if cls.weather_source_capable and semantics is not None:
        if not semantics.has_declaration:
            indicators.append(
                _ind(
                    IND_WEATHER_SEMANTICS_UNDECLARED,
                    "Weather semantics not declared",
                    "This weather-source device has no declared measurement "
                    "semantics, so its readings cannot be treated as plane-of-array "
                    "or cell temperature.",
                    DiagnosticBlockingLevel.lowers_confidence,
                    "Declare the irradiance plane / temperature type for this device.",
                )
            )
        else:
            if (
                semantics.irradiance_plane == "unknown"
                and semantics.temperature_type == "unknown"
            ):
                indicators.append(
                    _ind(
                        IND_WEATHER_SEMANTICS_UNKNOWN,
                        "Weather semantics unknown",
                        "The declared plane and temperature type are both unknown, "
                        "so the readings are stored verbatim and never assumed to be "
                        "POA / cell.",
                        DiagnosticBlockingLevel.lowers_confidence,
                        "Set the irradiance plane (e.g. POA) and/or temperature type "
                        "(e.g. cell) if known.",
                    )
                )
            elif not (
                semantics.physics_usable_irradiance
                or semantics.physics_usable_temperature
            ):
                indicators.append(
                    _ind(
                        IND_WEATHER_NOT_PHYSICS_USABLE,
                        "Weather not physics-usable",
                        "The declared semantics (e.g. GHI / ambient) are not "
                        "transposable to POA / cell by the current physics, so they "
                        "are not used by expected — and never auto-converted.",
                        DiagnosticBlockingLevel.lowers_confidence,
                        "Provide a POA irradiance and/or cell/module temperature "
                        "source if available.",
                    )
                )
            if semantics.calibration_status == "unknown":
                indicators.append(
                    _ind(
                        IND_WEATHER_CALIBRATION_UNKNOWN,
                        "Calibration unknown",
                        "The calibration status of this weather sensor is unknown, "
                        "which lowers confidence in its readings.",
                        DiagnosticBlockingLevel.informational,
                        "Record the calibration status / reference for this sensor.",
                    )
                )
            # WS.3 — read-only stale disclosure. Surface when the declaration was
            # flagged for re-review (persisted) OR the device's live upstream
            # identity diverges from the snapshot taken at declaration time. This is
            # a confidence signal only: it never blocks, never converts, and never
            # mutates anything from this read path.
            if semantics.needs_re_review or semantics.upstream_change_detected:
                changed = (
                    f" Changed: {', '.join(semantics.upstream_changed_keys)}."
                    if semantics.upstream_changed_keys
                    else ""
                )
                reason = (
                    f" {semantics.re_review_reason}"
                    if semantics.needs_re_review and semantics.re_review_reason
                    else ""
                )
                indicators.append(
                    _ind(
                        IND_WEATHER_SEMANTICS_STALE,
                        "Weather semantics may be out of date",
                        "The upstream device this declaration was authored against "
                        "appears to have changed, so the declared semantics should be "
                        "re-reviewed before they are trusted." + reason + changed,
                        DiagnosticBlockingLevel.lowers_confidence,
                        "Re-review the declared semantics; supersede with a new "
                        "declaration if the device's identity changed.",
                    )
                )

    # Inspection-only descriptors (mappable but deliberately not expected drivers).
    if cls.production_meter_capable and not cls.can_drive_expected:
        indicators.append(
            _ind(
                IND_METER_INSPECTION_ONLY,
                "Meter (inspection-only)",
                "Meters are mappable for inspection but do not drive expected "
                "performance, so their readings never change the expected math.",
                DiagnosticBlockingLevel.informational,
            )
        )
    if cls.gateway_capable and not cls.can_drive_expected:
        indicators.append(
            _ind(
                IND_GATEWAY_INSPECTION_ONLY,
                "Gateway / logger (inspection-only)",
                "Gateways and data loggers are mappable for inspection but do not "
                "drive expected performance.",
                DiagnosticBlockingLevel.informational,
            )
        )
    if cls.virtual_device:
        indicators.append(
            _ind(
                IND_VIRTUAL_AGGREGATION,
                "Virtual aggregation device",
                "This is a virtual site-performance device used for aggregation; it "
                "does not ingest its own provider readings.",
                DiagnosticBlockingLevel.informational,
            )
        )

    return indicators


def compute_site_eligibility_diagnostics(
    db: Session, *, site
) -> DeviceEligibilityDiagnosticsResponse:
    """Compute read-only Path-B eligibility diagnostics for every device on a site.

    ``site`` is an authorized ``Site`` whose ``devices`` relationship is loaded. No
    writes/commits occur; weather semantics are read verbatim and never converted.
    """
    devices_out: list[DeviceEligibilityDiagnostic] = []
    mappable_count = 0
    mapped_count = 0
    unmapped_eligible_count = 0
    expected_driving_count = 0
    weather_source_count = 0
    meter_count = 0
    gateway_count = 0
    virtual_count = 0
    ineligible_count = 0
    weather_unknown_count = 0

    # Most-severe blocking level seen per indicator key, for the site rollup.
    rollup: dict[str, DiagnosticIndicator] = {}

    for device in site.devices:
        cls = classify_device(device)
        is_mapped = getattr(device, "telemetry_mapping", None) is not None

        semantics = (
            _current_weather_semantics(db, device)
            if cls.weather_source_capable
            else None
        )

        if cls.mappable:
            mappable_count += 1
        else:
            ineligible_count += 1
        if is_mapped:
            mapped_count += 1
        elif cls.mappable:
            unmapped_eligible_count += 1
        if cls.can_drive_expected:
            expected_driving_count += 1
        if cls.weather_source_capable:
            weather_source_count += 1
        if cls.production_meter_capable:
            meter_count += 1
        if cls.gateway_capable:
            gateway_count += 1
        if cls.virtual_device:
            virtual_count += 1
        if semantics is not None and (
            not semantics.has_declaration
            or (
                semantics.irradiance_plane == "unknown"
                and semantics.temperature_type == "unknown"
            )
        ):
            weather_unknown_count += 1

        indicators = _device_indicators(cls, is_mapped, semantics)
        for ind in indicators:
            existing = rollup.get(ind.key)
            if existing is None or severity_rank(ind.blocking_level) < severity_rank(
                existing.blocking_level
            ):
                rollup[ind.key] = ind

        devices_out.append(
            DeviceEligibilityDiagnostic(
                device_id=device.id,
                name=device.name,
                category=cls.category,
                device_role=cls.device_role,
                mappable=cls.mappable,
                can_drive_expected=cls.can_drive_expected,
                telemetry_capable=cls.telemetry_capable,
                weather_source_capable=cls.weather_source_capable,
                production_meter_capable=cls.production_meter_capable,
                gateway_capable=cls.gateway_capable,
                virtual_device=cls.virtual_device,
                mapped_status=cls.mapped_status,
                is_mapped=is_mapped,
                source_provider=cls.source_provider,
                external_device_type=cls.external_device_type,
                eligibility_reason=cls.eligibility_reason,
                ineligibility_reason=cls.ineligibility_reason,
                weather_semantics=semantics,
                indicators=indicators,
            )
        )

    site_indicators = sorted(
        rollup.values(), key=lambda i: (severity_rank(i.blocking_level), i.key)
    )

    return DeviceEligibilityDiagnosticsResponse(
        site_id=site.id,
        total_devices=len(devices_out),
        mappable_count=mappable_count,
        mapped_count=mapped_count,
        unmapped_eligible_count=unmapped_eligible_count,
        expected_driving_count=expected_driving_count,
        weather_source_count=weather_source_count,
        meter_count=meter_count,
        gateway_count=gateway_count,
        virtual_count=virtual_count,
        ineligible_count=ineligible_count,
        weather_unknown_semantics_count=weather_unknown_count,
        devices=devices_out,
        indicators=site_indicators,
    )
