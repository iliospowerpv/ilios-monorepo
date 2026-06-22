"""WS.1 — pure verdict + calibration-policy helpers for governed weather declarations.

This module is intentionally **pure**: it imports NO database/session, NO resolver,
and NO expected/baseline math. Every function is a deterministic function of its
inputs so it can be unit-tested directly and reused verbatim by the read-only
diagnostics and reconciliation surfaces (WS.3/WS.4).

It answers two separate questions, kept distinct on purpose:

* the value-level disclosures ``physics_usable_irradiance`` / ``physics_usable_temperature``
  (is the declared plane/temperature something the cell-temperature physics path could
  use at all — POA irradiance, or cell/module/modeled_cell temperature), and
* the production-grade verdict ``expected_model_eligible`` — whether an *active,
  non-stale* declaration with a *qualifying basis*, *declared sensor role*, and
  *sensor-type-specific calibration* is complete enough to clear the Layer-1
  semantics-readiness block.

Reaching ``expected_model_eligible`` is **Layer-1 only**: it never writes
``expected_weather_provenance``, never triggers baseline revalidation, and never
asserts WAM revalidation. The reconciliation/diagnostics consumers may *escalate*
the intrinsic ``blocking_level`` to ``blocks_calculation`` when an active
weather-adjusted model actually requires the input; the policy itself reports the
declaration-intrinsic severity only.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

from app.models.weather import (
    WeatherCalibrationStatus,
    WeatherDeclarationBasis,
    WeatherDeclarationStatus,
    WeatherIrradiancePlane,
    WeatherTemperatureType,
)
from app.schema.weather import (
    _PHYSICS_USABLE_PLANES,
    _PHYSICS_USABLE_TEMPERATURES,
)

# Exact Layer-1 wording (kept verbatim — the frontend asserts this string).
LAYER1_ELIGIBLE_MESSAGE = (
    "Weather semantics declaration is complete and eligible for expected-model "
    "integration. Expected-model integration has not yet been applied."
)

# --- Stable reason codes ----------------------------------------------------
REASON_MISSING_DECLARATION = "missing_declaration"
REASON_DRAFT_NOT_ACTIVATED = "draft_not_activated"
REASON_SUPERSEDED = "superseded"
REASON_STALE_NEEDS_RE_REVIEW = "stale_needs_re_review"
REASON_BASIS_NOT_QUALIFYING = "basis_not_qualifying"
REASON_IRRADIANCE_NOT_POA = "irradiance_not_poa"
REASON_TEMPERATURE_NOT_CELL_USABLE = "temperature_not_cell_usable"
REASON_NO_USABLE_MEASUREMENT = "no_usable_measurement"
REASON_SENSOR_ROLE_MISSING = "sensor_role_missing"
REASON_CALIBRATION_REQUIRED_MISSING = "calibration_required_missing"
REASON_CALIBRATION_VALIDITY_UNKNOWN = "calibration_validity_unknown"
REASON_EFFECTIVE_WINDOW_GAP = "effective_window_gap"
REASON_ELIGIBLE_INTEGRATION_PENDING = "eligible_integration_pending"

# --- Blocking levels (shared vocabulary with eligibility diagnostics) -------
BLOCKING_BLOCKS_CALCULATION = "blocks_calculation"
BLOCKING_LOWERS_CONFIDENCE = "lowers_confidence"
BLOCKING_INFORMATIONAL = "informational"

# --- Declaration-centric reconciliation states (taxonomy states 1-5) --------
# States 6-8 (weather_source_missing / weather_source_stale /
# source_coverage_incomplete) are source/profile-level and are overlaid by the
# reconciliation consumer; this pure helper only decides the declaration axis.
STATE_SOURCE_EXISTS_SEMANTICS_UNKNOWN = "source_exists_semantics_unknown"
STATE_DECLARATION_DRAFT = "declaration_draft"
STATE_DECLARED_NOT_PHYSICS_USABLE = "declared_not_physics_usable"
STATE_DECLARED_ELIGIBLE_INTEGRATION_PENDING = "declared_eligible_integration_pending"
STATE_DECLARATION_STALE_NEEDS_RE_REVIEW = "declaration_stale_needs_re_review"

# Human-readable next action per reason (most-actionable-first ordering below).
_REASON_ACTIONS: dict[str, str] = {
    REASON_MISSING_DECLARATION: (
        "Declare the weather semantics (e.g. POA plane / cell temperature) with "
        "qualifying evidence, then activate."
    ),
    REASON_DRAFT_NOT_ACTIVATED: (
        "Complete the required evidence and calibration, then activate the draft "
        "declaration."
    ),
    REASON_SUPERSEDED: (
        "Create and activate a new declaration; this one has been superseded."
    ),
    REASON_STALE_NEEDS_RE_REVIEW: (
        "Re-declare and activate a new declaration to clear the stale flag."
    ),
    REASON_BASIS_NOT_QUALIFYING: (
        "Attach provider-confirmed or source-document evidence (reviewer notes / "
        "assumptions stay recorded-only)."
    ),
    REASON_IRRADIANCE_NOT_POA: (
        "Declare the irradiance plane as POA with calibrated reference evidence."
    ),
    REASON_TEMPERATURE_NOT_CELL_USABLE: (
        "Declare a usable temperature type (cell, module, or modeled_cell) with "
        "qualifying evidence."
    ),
    REASON_NO_USABLE_MEASUREMENT: (
        "Declare a physics-usable plane (POA) or temperature type "
        "(cell / module / modeled_cell)."
    ),
    REASON_SENSOR_ROLE_MISSING: "Declare the sensor role for this measurement.",
    REASON_CALIBRATION_REQUIRED_MISSING: (
        "Attach a calibration certificate (reference + date) and mark the sensor "
        "calibrated."
    ),
    REASON_CALIBRATION_VALIDITY_UNKNOWN: (
        "Provide current calibration — the existing calibration is expired or its "
        "validity is unknown."
    ),
    REASON_EFFECTIVE_WINDOW_GAP: (
        "Extend the declaration's effective period to fully cover the required window."
    ),
}

# Priority order for choosing the single surfaced ``required_action``.
_REASON_PRIORITY: tuple[str, ...] = (
    REASON_MISSING_DECLARATION,
    REASON_SUPERSEDED,
    REASON_DRAFT_NOT_ACTIVATED,
    REASON_STALE_NEEDS_RE_REVIEW,
    REASON_BASIS_NOT_QUALIFYING,
    REASON_NO_USABLE_MEASUREMENT,
    REASON_IRRADIANCE_NOT_POA,
    REASON_TEMPERATURE_NOT_CELL_USABLE,
    REASON_SENSOR_ROLE_MISSING,
    REASON_CALIBRATION_REQUIRED_MISSING,
    REASON_CALIBRATION_VALIDITY_UNKNOWN,
    REASON_EFFECTIVE_WINDOW_GAP,
)

_USABLE_PLANE_VALUES = frozenset(p.value for p in _PHYSICS_USABLE_PLANES)
_USABLE_TEMPERATURE_VALUES = frozenset(t.value for t in _PHYSICS_USABLE_TEMPERATURES)
_QUALIFYING_BASES = frozenset(
    {
        WeatherDeclarationBasis.provider_confirmed.value,
        WeatherDeclarationBasis.source_document.value,
    }
)


def _v(value: Any) -> Any:
    """Normalize an enum/scalar to its comparable ``.value`` (None stays None)."""
    return getattr(value, "value", value)


@dataclass(frozen=True)
class DeclarationVerdict:
    """Read-only verdict for a single (resolved current) weather declaration."""

    expected_model_eligible: bool
    physics_usable_irradiance: bool
    physics_usable_temperature: bool
    calibration_ok: bool
    reason_codes: tuple[str, ...]
    blocking_level: str
    required_action: Optional[str]
    layer1_message: Optional[str]
    declaration_state: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "expected_model_eligible": self.expected_model_eligible,
            "physics_usable_irradiance": self.physics_usable_irradiance,
            "physics_usable_temperature": self.physics_usable_temperature,
            "calibration_ok": self.calibration_ok,
            "reason_codes": list(self.reason_codes),
            "blocking_level": self.blocking_level,
            "required_action": self.required_action,
            "layer1_message": self.layer1_message,
            "declaration_state": self.declaration_state,
        }


def physics_usable_irradiance(plane: Any) -> bool:
    """True only for true plane-of-array; GHI/DNI/DHI/unknown are never usable."""
    return _v(plane) in _USABLE_PLANE_VALUES


def physics_usable_temperature(temperature_type: Any) -> bool:
    """True for cell / module / modeled_cell; ambient/unknown are never usable."""
    return _v(temperature_type) in _USABLE_TEMPERATURE_VALUES


def calibration_required(*, plane: Any, temperature_type: Any) -> bool:
    """Whether the calibration policy applies to this sensor type.

    Mandatory for POA irradiance, cell temperature, and module-back temperature
    (the stricter default). N/A for modeled_cell (no physical sensor) and for any
    non-physics-usable plane/temperature (those are never eligible regardless).
    """
    if _v(plane) == WeatherIrradiancePlane.poa.value:
        return True
    if _v(temperature_type) in (
        WeatherTemperatureType.cell.value,
        WeatherTemperatureType.module.value,
    ):
        return True
    return False


def evaluate_calibration(
    *,
    plane: Any,
    temperature_type: Any,
    calibration_status: Any,
    calibrated_at: Any,
    calibration_reference: Any,
) -> tuple[bool, Optional[str]]:
    """Sensor-type-specific calibration gate. Returns ``(ok, reason_code)``.

    When calibration is not required for the sensor type (modeled_cell or a
    non-usable plane/temperature), this returns ``(True, None)`` — eligibility is
    then decided by the other rules (basis, usability, role, coverage).
    """
    if not calibration_required(plane=plane, temperature_type=temperature_type):
        return True, None

    status = _v(calibration_status)
    if status == WeatherCalibrationStatus.calibrated.value:
        if calibrated_at is not None and calibration_reference:
            return True, None
        return False, REASON_CALIBRATION_REQUIRED_MISSING
    if status == WeatherCalibrationStatus.expired.value:
        return False, REASON_CALIBRATION_VALIDITY_UNKNOWN
    # uncalibrated / unknown / missing
    return False, REASON_CALIBRATION_REQUIRED_MISSING


def _required_action(reason_codes: tuple[str, ...]) -> Optional[str]:
    for reason in _REASON_PRIORITY:
        if reason in reason_codes:
            return _REASON_ACTIONS.get(reason)
    return None


def evaluate_declaration(
    *,
    declaration_status: Any,
    declaration_basis: Any,
    irradiance_plane: Any,
    temperature_type: Any,
    calibration_status: Any,
    calibrated_at: Any = None,
    calibration_reference: Any = None,
    sensor_role: Any = None,
    needs_re_review: Any = None,
    window_coverage_ok: Optional[bool] = None,
) -> DeclarationVerdict:
    """Compute the full read-only verdict for one resolved current declaration.

    ``window_coverage_ok`` is the effective-period coverage check (taxonomy rule 6),
    which is a W1/consumer computation. ``None`` means "not evaluated here" and is
    NOT treated as a failure; pass ``False`` to fail eligibility on a coverage gap.
    A NULL ``declaration_status`` is treated as "no governed declaration".
    """
    usable_irr = physics_usable_irradiance(irradiance_plane)
    usable_temp = physics_usable_temperature(temperature_type)
    status = _v(declaration_status)

    # No governed declaration (legacy NULL / absent) -> semantics unknown.
    if status is None:
        return DeclarationVerdict(
            expected_model_eligible=False,
            physics_usable_irradiance=usable_irr,
            physics_usable_temperature=usable_temp,
            calibration_ok=False,
            reason_codes=(REASON_MISSING_DECLARATION,),
            blocking_level=BLOCKING_LOWERS_CONFIDENCE,
            required_action=_REASON_ACTIONS[REASON_MISSING_DECLARATION],
            layer1_message=None,
            declaration_state=STATE_SOURCE_EXISTS_SEMANTICS_UNKNOWN,
        )

    # A superseded row is never the production-grade current declaration.
    if status == WeatherDeclarationStatus.superseded.value:
        return DeclarationVerdict(
            expected_model_eligible=False,
            physics_usable_irradiance=usable_irr,
            physics_usable_temperature=usable_temp,
            calibration_ok=False,
            reason_codes=(REASON_SUPERSEDED,),
            blocking_level=BLOCKING_LOWERS_CONFIDENCE,
            required_action=_REASON_ACTIONS[REASON_SUPERSEDED],
            layer1_message=None,
            declaration_state=STATE_SOURCE_EXISTS_SEMANTICS_UNKNOWN,
        )

    # Draft is recorded-only; it can never be physics-usable until activated.
    if status == WeatherDeclarationStatus.draft.value:
        return DeclarationVerdict(
            expected_model_eligible=False,
            physics_usable_irradiance=usable_irr,
            physics_usable_temperature=usable_temp,
            calibration_ok=False,
            reason_codes=(REASON_DRAFT_NOT_ACTIVATED,),
            blocking_level=BLOCKING_LOWERS_CONFIDENCE,
            required_action=_REASON_ACTIONS[REASON_DRAFT_NOT_ACTIVATED],
            layer1_message=None,
            declaration_state=STATE_DECLARATION_DRAFT,
        )

    # status == active. The stale sub-state is its own taxonomy state.
    if bool(needs_re_review):
        return DeclarationVerdict(
            expected_model_eligible=False,
            physics_usable_irradiance=usable_irr,
            physics_usable_temperature=usable_temp,
            calibration_ok=False,
            reason_codes=(REASON_STALE_NEEDS_RE_REVIEW,),
            blocking_level=BLOCKING_LOWERS_CONFIDENCE,
            required_action=_REASON_ACTIONS[REASON_STALE_NEEDS_RE_REVIEW],
            layer1_message=None,
            declaration_state=STATE_DECLARATION_STALE_NEEDS_RE_REVIEW,
        )

    # Active + not stale: run the full eligibility policy.
    reasons: list[str] = []

    if _v(declaration_basis) not in _QUALIFYING_BASES:
        reasons.append(REASON_BASIS_NOT_QUALIFYING)

    # A mapping is per-metric, so at most one of plane/temperature is the declared
    # axis. Eligibility needs at least one physics-usable dimension; when neither
    # qualifies, surface the precise reason for whatever WAS declared.
    if not (usable_irr or usable_temp):
        plane_declared = _v(irradiance_plane) != WeatherIrradiancePlane.unknown.value
        temp_declared = _v(temperature_type) != WeatherTemperatureType.unknown.value
        if plane_declared:
            reasons.append(REASON_IRRADIANCE_NOT_POA)
        if temp_declared:
            reasons.append(REASON_TEMPERATURE_NOT_CELL_USABLE)
        if not plane_declared and not temp_declared:
            reasons.append(REASON_NO_USABLE_MEASUREMENT)

    if not (sensor_role and str(sensor_role).strip()):
        reasons.append(REASON_SENSOR_ROLE_MISSING)

    calibration_ok, calibration_reason = evaluate_calibration(
        plane=irradiance_plane,
        temperature_type=temperature_type,
        calibration_status=calibration_status,
        calibrated_at=calibrated_at,
        calibration_reference=calibration_reference,
    )
    if calibration_reason is not None:
        reasons.append(calibration_reason)

    if window_coverage_ok is False:
        reasons.append(REASON_EFFECTIVE_WINDOW_GAP)

    if not reasons:
        return DeclarationVerdict(
            expected_model_eligible=True,
            physics_usable_irradiance=usable_irr,
            physics_usable_temperature=usable_temp,
            calibration_ok=calibration_ok,
            reason_codes=(REASON_ELIGIBLE_INTEGRATION_PENDING,),
            blocking_level=BLOCKING_INFORMATIONAL,
            required_action=None,
            layer1_message=LAYER1_ELIGIBLE_MESSAGE,
            declaration_state=STATE_DECLARED_ELIGIBLE_INTEGRATION_PENDING,
        )

    reason_tuple = tuple(reasons)
    return DeclarationVerdict(
        expected_model_eligible=False,
        physics_usable_irradiance=usable_irr,
        physics_usable_temperature=usable_temp,
        calibration_ok=calibration_ok,
        reason_codes=reason_tuple,
        blocking_level=BLOCKING_LOWERS_CONFIDENCE,
        required_action=_required_action(reason_tuple),
        layer1_message=None,
        declaration_state=STATE_DECLARED_NOT_PHYSICS_USABLE,
    )


def evaluate_mapping(
    mapping: Any, *, window_coverage_ok: Optional[bool] = None
) -> DeclarationVerdict:
    """Convenience wrapper that reads attributes off a ``WeatherDeviceMapping``.

    Reads only already-loaded attributes (no DB access). Pass ``None`` for a
    missing mapping to get the ``source_exists_semantics_unknown`` verdict.
    """
    if mapping is None:
        return verdict_for_no_declaration()
    return evaluate_declaration(
        declaration_status=getattr(mapping, "declaration_status", None),
        declaration_basis=getattr(mapping, "declaration_basis", None),
        irradiance_plane=getattr(mapping, "irradiance_plane", None),
        temperature_type=getattr(mapping, "temperature_type", None),
        calibration_status=getattr(mapping, "calibration_status", None),
        calibrated_at=getattr(mapping, "calibrated_at", None),
        calibration_reference=getattr(mapping, "calibration_reference", None),
        sensor_role=getattr(mapping, "sensor_role", None),
        needs_re_review=getattr(mapping, "needs_re_review", None),
        window_coverage_ok=window_coverage_ok,
    )


def verdict_for_no_declaration() -> DeclarationVerdict:
    """Verdict for a weather-capable device with no governed declaration (Site 4)."""
    return evaluate_declaration(
        declaration_status=None,
        declaration_basis=None,
        irradiance_plane=WeatherIrradiancePlane.unknown,
        temperature_type=WeatherTemperatureType.unknown,
        calibration_status=WeatherCalibrationStatus.unknown,
    )
