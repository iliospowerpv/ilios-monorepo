"""Additive, read-only PHYSICS VALIDATION for weather-adjusted baselines.

This module judges whether a :class:`TelemetryExpectedBaseline` carries
physically plausible assumptions BEFORE it is allowed to drive an expected
curve. It never mutates, converts, auto-corrects, or persists anything; callers
decide what to do with the structured verdict:

* the activation gate blocks a ``hard_invalid`` baseline and requires explicit
  acknowledgement for ``warning`` baselines (see ``crud.telemetry_expected``);
* the O&M read path suppresses the expected/comparison curve for an active but
  ``hard_invalid`` baseline (``baseline_invalid`` state), keeping actuals.

Two design rules anchor everything here:

1. **One canonical temperature-unit contract.** ``thermal_coefficient_pct`` is
   stored as ``% per °C``. The temperature delta it multiplies must be in ``°C``,
   measured from the 25 °C STC reference. Production converts any Fahrenheit cell
   temperature to Celsius exactly once
   (``expected_service._expected_power_breakdown``:
   ``cell_temperature_c = (cell_temperature_f - 32) / 1.8``) before applying the
   coefficient. The smoke test below calls THAT SAME path so a Fahrenheit-vs-
   Celsius defect cannot silently produce a valid-looking but wrong curve.

2. **Never guess or convert.** A value whose unit is ambiguous (e.g. a thermal
   coefficient near ``-0.63`` that looks like ``%/°F`` copied into a ``%/°C``
   field, or an inverter rating that looks like Watts in a kW field) is flagged
   ``warning`` requiring explicit human confirmation — it is NEVER silently
   reinterpreted or auto-converted.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field as dc_field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from app.services.telemetry.expected_service import (
    BaselineParams,
    CELL_TEMPERATURE_BASELINE_C,
    IRRADIANCE_BASELINE_WM2,
    REQUIRED_PHYSICS_FIELDS,
    _expected_power_breakdown,
)

# ---------------------------------------------------------------------------
# Policy identity + temperature-unit contract (persisted with every verdict)
# ---------------------------------------------------------------------------

POLICY_VERSION = "baseline-physics-v1"

# Version of the temperature-unit contract the smoke test exercises. Bump this
# (and POLICY_VERSION) if the canonical conversion path ever changes so a stored
# verdict is never silently reinterpreted under a different contract.
TEMPERATURE_UNIT_CONTRACT_VERSION = "tc-contract-v1"
TEMPERATURE_UNIT_CONTRACT = (
    "thermal_coefficient_pct is % per °C; the temperature delta is in °C measured "
    "from the 25 °C STC reference; Fahrenheit cell temperature is converted exactly "
    "once via (F-32)/1.8 in expected_service before the coefficient is applied."
)

# Numeric tolerance for float equality assertions (factors, power).
_ABS_TOL = 1e-9
_REL_TOL = 1e-9


class Classification(str, Enum):
    """Per-field / per-check verdict. ``hard_invalid`` is the only blocking one."""

    plausible = "plausible"
    warning = "warning"
    hard_invalid = "hard_invalid"


# ---------------------------------------------------------------------------
# Result dataclasses
# ---------------------------------------------------------------------------


@dataclass
class FieldValidationResult:
    field: str
    entered_value: Optional[float]
    expected_unit: str
    classification: Classification
    reason: str
    source: str
    required_action: Optional[str]
    policy_version: str = POLICY_VERSION

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["classification"] = self.classification.value
        return d


@dataclass
class SmokeProbe:
    """One evaluated point of the canonical breakdown, fully introspected."""

    label: str
    input_temperature: float
    input_unit: str  # "C" or "F"
    canonical_temperature_c: float
    reference_temperature_c: float
    delta_c: float
    thermal_coefficient_unit: str
    thermal_coefficient_per_c: float
    temperature_factor: float
    irradiance_wm2: float
    irradiance_factor: float
    expected_power_kw: float
    preclip_kw: float
    is_clipped: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class SmokeCheck:
    """A named pass/fail assertion of the smoke test."""

    name: str
    passed: bool
    classification: Classification
    detail: str

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["classification"] = self.classification.value
        return d


@dataclass
class SmokeTestReport:
    ran: bool
    reason_not_run: Optional[str]
    celsius_fahrenheit_equivalence_verified: bool
    temperature_input_modes_exercised: list[str] = dc_field(default_factory=list)
    probes: list[SmokeProbe] = dc_field(default_factory=list)
    checks: list[SmokeCheck] = dc_field(default_factory=list)
    unit_mismatch_demonstration: Optional[dict[str, Any]] = None

    @property
    def has_blocking(self) -> bool:
        return any(
            c.classification == Classification.hard_invalid and not c.passed
            for c in self.checks
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "ran": self.ran,
            "reason_not_run": self.reason_not_run,
            "celsius_fahrenheit_equivalence_verified": (
                self.celsius_fahrenheit_equivalence_verified
            ),
            "temperature_input_modes_exercised": self.temperature_input_modes_exercised,
            "probes": [p.to_dict() for p in self.probes],
            "checks": [c.to_dict() for c in self.checks],
            "unit_mismatch_demonstration": self.unit_mismatch_demonstration,
        }


@dataclass
class BaselineValidationReport:
    baseline_id: Optional[int]
    is_blocking: bool
    summary: str
    policy_version: str
    temperature_unit_contract: str
    temperature_unit_contract_version: str
    validation_timestamp: str
    validation_source_mode: str
    celsius_fahrenheit_equivalence_verified: bool
    fields: list[FieldValidationResult]
    cross_field_checks: list[FieldValidationResult]
    smoke_test: SmokeTestReport
    provenance: dict[str, Any]

    @property
    def blocking_fields(self) -> list[FieldValidationResult]:
        return [
            f
            for f in (self.fields + self.cross_field_checks)
            if f.classification == Classification.hard_invalid
        ]

    @property
    def warning_fields(self) -> list[FieldValidationResult]:
        return [
            f
            for f in (self.fields + self.cross_field_checks)
            if f.classification == Classification.warning
        ]

    @property
    def has_warnings(self) -> bool:
        return bool(self.warning_fields)

    def to_dict(self) -> dict[str, Any]:
        return {
            "baseline_id": self.baseline_id,
            "is_blocking": self.is_blocking,
            "summary": self.summary,
            "policy_version": self.policy_version,
            "temperature_unit_contract": self.temperature_unit_contract,
            "temperature_unit_contract_version": self.temperature_unit_contract_version,
            "validation_timestamp": self.validation_timestamp,
            "validation_source_mode": self.validation_source_mode,
            "celsius_fahrenheit_equivalence_verified": (
                self.celsius_fahrenheit_equivalence_verified
            ),
            "blocking_field_count": len(self.blocking_fields),
            "warning_field_count": len(self.warning_fields),
            "fields": [f.to_dict() for f in self.fields],
            "cross_field_checks": [c.to_dict() for c in self.cross_field_checks],
            "smoke_test": self.smoke_test.to_dict(),
            "provenance": self.provenance,
        }


# ---------------------------------------------------------------------------
# Field bounds (single source of truth) + units
# ---------------------------------------------------------------------------

EXPECTED_UNITS: dict[str, str] = {
    "module_wattage": "W (per module)",
    "module_quantity": "count",
    "inverter_wattage": "kW AC (per inverter)",
    "inverter_quantity": "count",
    "thermal_coefficient_pct": "% per °C",
    "power_tolerance_min_pct": "% (minimum tolerance, ≤ 0)",
    "year_1_degradation_pct": "% (year 1)",
    "annual_degradation_pct": "% per year",
    "cec_efficiency_pct": "% (CEC inverter efficiency)",
    "soiling_factor": "fraction (1.0 = no soiling)",
    "dc_loss_pct": "% (positive loss)",
    "ac_loss_pct": "% (positive loss)",
    "medium_voltage_loss_pct": "% (positive loss)",
    "mv_line_loss_pct": "% (positive loss)",
}

_LOSS_FIELDS = (
    "dc_loss_pct",
    "ac_loss_pct",
    "medium_voltage_loss_pct",
    "mv_line_loss_pct",
)


def _action_for(classification: Classification, what: str) -> Optional[str]:
    if classification == Classification.plausible:
        return None
    if classification == Classification.warning:
        return (
            f"Confirm {what} against source documentation and acknowledge at "
            "activation (with a source note)."
        )
    return (
        f"Correct {what} via a new source-backed replacement baseline; this "
        "value cannot be activated."
    )


def _classify_thermal_coefficient(v: float) -> tuple[Classification, str]:
    """``%/°C`` coefficient. Negative for c-Si; magnitude ~0.3–0.45 is typical."""
    if v >= 0:
        return (
            Classification.hard_invalid,
            "A zero or positive thermal coefficient is non-physical for a "
            "crystalline-silicon baseline (expected ~ -0.35 %/°C).",
        )
    av = abs(v)
    if av < 0.01:
        return (
            Classification.warning,
            f"Magnitude {av:g} is near a decimal fraction per °C (e.g. -0.0035); "
            "confirm the value is %/°C, not a fraction.",
        )
    if av < 0.20:
        return (
            Classification.warning,
            f"Magnitude {av:g} %/°C is unusually small for crystalline silicon; "
            "confirm against the module datasheet.",
        )
    if 0.20 <= av <= 0.50:
        return (
            Classification.plausible,
            f"{v:g} %/°C is within the typical crystalline-silicon range "
            "(~ -0.20 to -0.50 %/°C).",
        )
    if 0.50 < av <= 0.80:
        return (
            Classification.warning,
            f"Magnitude {av:g} %/°C resembles a %/°F coefficient copied into a "
            "%/°C field; confirm the unit (no automatic conversion is applied).",
        )
    return (
        Classification.hard_invalid,
        f"Magnitude {av:g} %/°C is implausibly large for a thermal coefficient.",
    )


def _classify_power_tolerance_min(v: float) -> tuple[Classification, str]:
    """Minimum power tolerance — should be ≤ 0 (a downward deviation)."""
    if v > 0:
        return (
            Classification.hard_invalid,
            "Minimum power tolerance must be ≤ 0; a positive value likely belongs "
            "in power_tolerance_max_pct, not the minimum-tolerance field.",
        )
    if -5.0 <= v <= 0.0:
        return (Classification.plausible, f"{v:g}% is a normal minimum tolerance.")
    if -10.0 <= v < -5.0:
        return (
            Classification.warning,
            f"{v:g}% is a large negative minimum tolerance; confirm with the "
            "module datasheet.",
        )
    return (
        Classification.hard_invalid,
        f"{v:g}% is below -10%, an implausible minimum power tolerance.",
    )


def _classify_loss(v: float) -> tuple[Classification, str]:
    if v < 0:
        return (
            Classification.hard_invalid,
            f"A negative loss ({v:g}%) is invalid; losses are stored as positive "
            "percentages.",
        )
    if v <= 15.0:
        return (Classification.plausible, f"{v:g}% is a normal loss assumption.")
    if v <= 30.0:
        return (
            Classification.warning,
            f"{v:g}% is a high single-stage loss; confirm with the source.",
        )
    return (
        Classification.hard_invalid,
        f"{v:g}% exceeds 30%, an implausibly large single-stage loss.",
    )


def _classify_soiling(v: float) -> tuple[Classification, str]:
    if v <= 0 or v > 1.05:
        return (
            Classification.hard_invalid,
            f"Soiling factor {v:g} is outside the valid (0, 1.05] range.",
        )
    if v > 1.00:
        return (
            Classification.warning,
            f"Soiling factor {v:g} is above 1.0 (a gain, not a loss); allowed only "
            "with an explicit source acknowledgement.",
        )
    if 0.90 <= v <= 1.00:
        return (Classification.plausible, f"{v:g} is a normal soiling assumption.")
    if 0.80 <= v < 0.90:
        return (
            Classification.warning,
            f"{v:g} implies 10–20% soiling loss; confirm with the source.",
        )
    return (
        Classification.warning,
        f"{v:g} implies >20% soiling loss; confirm with the source.",
    )


def _classify_module_wattage(v: float) -> tuple[Classification, str]:
    if v <= 0:
        return (Classification.hard_invalid, "Module wattage must be positive.")
    if v < 50:
        return (
            Classification.hard_invalid,
            f"{v:g} W is below 50 W and likely a kW-vs-W entry error.",
        )
    if v <= 250:
        return (
            Classification.warning,
            f"{v:g} W is low for a modern module; confirm the value/unit.",
        )
    if v <= 1000:
        return (Classification.plausible, f"{v:g} W is a normal module wattage.")
    return (
        Classification.hard_invalid,
        f"{v:g} W exceeds 1000 W, implausible for a single module.",
    )


def _classify_inverter_wattage(v: float) -> tuple[Classification, str]:
    """Canonical unit: kW AC per inverter. Never auto-convert a W-looking value."""
    if v <= 0:
        return (Classification.hard_invalid, "Inverter rating must be positive.")
    if v < 1.0:
        return (
            Classification.warning,
            f"{v:g} kW is sub-kW; confirm a micro-inverter or the unit.",
        )
    if v <= 6000:
        return (
            Classification.plausible,
            f"{v:g} kW AC is a normal per-inverter rating.",
        )
    return (
        Classification.warning,
        f"{v:g} looks like Watts rather than kW AC per inverter; confirm the unit "
        "(no automatic conversion is applied).",
    )


def _classify_quantity(v: float, what: str) -> tuple[Classification, str]:
    if v <= 0:
        return (Classification.hard_invalid, f"{what} must be a positive count.")
    return (Classification.plausible, f"{v:g} is a valid count.")


def _classify_cec_efficiency(v: float) -> tuple[Classification, str]:
    if v <= 0:
        return (Classification.hard_invalid, "CEC efficiency must be positive.")
    if v < 50:
        return (
            Classification.hard_invalid,
            f"{v:g}% is below 50% (a non-functional inverter, or a fraction entered "
            "as a percent).",
        )
    if v < 90:
        return (
            Classification.warning,
            f"{v:g}% is low for CEC inverter efficiency; confirm the value.",
        )
    if v <= 100:
        return (Classification.plausible, f"{v:g}% is a normal CEC efficiency.")
    if v <= 105:
        return (
            Classification.warning,
            f"{v:g}% is slightly above 100%; confirm the value.",
        )
    return (
        Classification.hard_invalid,
        f"{v:g}% exceeds 105%, an impossible inverter efficiency.",
    )


def _classify_year1_degradation(v: float) -> tuple[Classification, str]:
    if v < 0:
        return (Classification.hard_invalid, "Year-1 degradation cannot be negative.")
    if v <= 3.0:
        return (Classification.plausible, f"{v:g}% is a normal year-1 degradation.")
    if v <= 5.0:
        return (
            Classification.warning,
            f"{v:g}% is a high year-1 degradation; confirm with the source.",
        )
    return (
        Classification.hard_invalid,
        f"{v:g}% exceeds 5%, implausible for year-1 degradation.",
    )


def _classify_annual_degradation(v: float) -> tuple[Classification, str]:
    if v < 0:
        return (Classification.hard_invalid, "Annual degradation cannot be negative.")
    if v <= 1.0:
        return (Classification.plausible, f"{v:g}% is a normal annual degradation.")
    if v <= 3.0:
        return (
            Classification.warning,
            f"{v:g}% is a high annual degradation; confirm with the source.",
        )
    return (
        Classification.hard_invalid,
        f"{v:g}% exceeds 3%, implausible for annual degradation.",
    )


_FIELD_CLASSIFIERS = {
    "thermal_coefficient_pct": _classify_thermal_coefficient,
    "power_tolerance_min_pct": _classify_power_tolerance_min,
    "soiling_factor": _classify_soiling,
    "module_wattage": _classify_module_wattage,
    "inverter_wattage": _classify_inverter_wattage,
    "cec_efficiency_pct": _classify_cec_efficiency,
    "year_1_degradation_pct": _classify_year1_degradation,
    "annual_degradation_pct": _classify_annual_degradation,
}


def _coerce_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------------------
# Field-level validation
# ---------------------------------------------------------------------------


def validate_fields(baseline) -> list[FieldValidationResult]:
    """Classify every typed physics column of a baseline row.

    Required physics fields that are absent are ``hard_invalid`` (the baseline
    cannot compute). Optional loss/soiling columns that are absent are reported
    as ``plausible`` defaults (matching ``BaselineParams.from_baseline``).
    """
    source = _value_source(baseline)
    results: list[FieldValidationResult] = []

    def _add(field_name: str, classifier) -> None:
        raw = getattr(baseline, field_name, None)
        v = _coerce_float(raw)
        unit = EXPECTED_UNITS[field_name]
        if v is None:
            if field_name in REQUIRED_PHYSICS_FIELDS:
                results.append(
                    FieldValidationResult(
                        field=field_name,
                        entered_value=None,
                        expected_unit=unit,
                        classification=Classification.hard_invalid,
                        reason="Required physics field is absent; baseline cannot "
                        "compute an expected curve.",
                        source=source,
                        required_action=_action_for(
                            Classification.hard_invalid, field_name
                        ),
                    )
                )
            else:
                default = "1.0" if field_name == "soiling_factor" else "0.0"
                results.append(
                    FieldValidationResult(
                        field=field_name,
                        entered_value=None,
                        expected_unit=unit,
                        classification=Classification.plausible,
                        reason=f"Not set; the calc uses the default ({default}).",
                        source=source,
                        required_action=None,
                    )
                )
            return
        classification, reason = classifier(v)
        results.append(
            FieldValidationResult(
                field=field_name,
                entered_value=v,
                expected_unit=unit,
                classification=classification,
                reason=reason,
                source=source,
                required_action=_action_for(classification, field_name),
            )
        )

    _add("module_wattage", _classify_module_wattage)
    _add("module_quantity", lambda v: _classify_quantity(v, "Module quantity"))
    _add("inverter_wattage", _classify_inverter_wattage)
    _add("inverter_quantity", lambda v: _classify_quantity(v, "Inverter quantity"))
    _add("thermal_coefficient_pct", _classify_thermal_coefficient)
    _add("power_tolerance_min_pct", _classify_power_tolerance_min)
    _add("year_1_degradation_pct", _classify_year1_degradation)
    _add("annual_degradation_pct", _classify_annual_degradation)
    _add("cec_efficiency_pct", _classify_cec_efficiency)
    _add("soiling_factor", _classify_soiling)
    for loss in _LOSS_FIELDS:
        _add(loss, _classify_loss)
    return results


def validate_cross_fields(baseline) -> list[FieldValidationResult]:
    """Relationships between fields (DC/AC ratio, aggregate AC-side loss)."""
    source = _value_source(baseline)
    results: list[FieldValidationResult] = []

    mw = _coerce_float(getattr(baseline, "module_wattage", None))
    mq = _coerce_float(getattr(baseline, "module_quantity", None))
    iw = _coerce_float(getattr(baseline, "inverter_wattage", None))
    iq = _coerce_float(getattr(baseline, "inverter_quantity", None))
    if None not in (mw, mq, iw, iq) and iw > 0 and iq > 0:
        dc_kw = mw * mq / 1000.0
        ac_kw = iw * iq
        ratio = dc_kw / ac_kw if ac_kw else None
        if ratio is not None:
            if 0.9 <= ratio <= 1.6:
                cls, reason = (
                    Classification.plausible,
                    f"DC/AC ratio {ratio:.2f} is within the normal 0.9–1.6 range.",
                )
            elif 0.7 <= ratio < 0.9 or 1.6 < ratio <= 2.0:
                cls, reason = (
                    Classification.warning,
                    f"DC/AC ratio {ratio:.2f} is outside the typical 0.9–1.6 band; "
                    "confirm module/inverter counts and units.",
                )
            else:
                cls, reason = (
                    Classification.hard_invalid,
                    f"DC/AC ratio {ratio:.2f} is implausible; check for a "
                    "kW-vs-W or quantity error in module/inverter sizing.",
                )
            results.append(
                FieldValidationResult(
                    field="dc_ac_ratio",
                    entered_value=round(ratio, 4),
                    expected_unit="ratio (DC kW / AC kW)",
                    classification=cls,
                    reason=reason,
                    source=source,
                    required_action=_action_for(cls, "the DC/AC sizing"),
                )
            )

    ac_side = sum(
        _coerce_float(getattr(baseline, f, None)) or 0.0
        for f in ("ac_loss_pct", "medium_voltage_loss_pct", "mv_line_loss_pct")
    )
    if ac_side <= 25.0:
        cls, reason = (
            Classification.plausible,
            f"Aggregate AC-side loss {ac_side:g}% is within 25%.",
        )
    elif ac_side < 50.0:
        cls, reason = (
            Classification.warning,
            f"Aggregate AC-side loss {ac_side:g}% is high; confirm the components.",
        )
    else:
        cls, reason = (
            Classification.hard_invalid,
            f"Aggregate AC-side loss {ac_side:g}% is implausibly large (≥50%).",
        )
    results.append(
        FieldValidationResult(
            field="ac_side_loss_total",
            entered_value=round(ac_side, 4),
            expected_unit="% (ac + mv + mv_line)",
            classification=cls,
            reason=reason,
            source=source,
            required_action=_action_for(cls, "the aggregate AC-side loss"),
        )
    )
    return results


# ---------------------------------------------------------------------------
# Smoke test — exercises the CANONICAL breakdown path (incl. F->C conversion)
# ---------------------------------------------------------------------------

# Physical temperatures probed in BOTH Celsius-origin and Fahrenheit-origin form.
# (°C, °F) pairs are exact: 0/32, 25/77, 45/113, 65/149.
_TEMP_PROBES_C = (0.0, 25.0, 45.0, 65.0)


def _c_to_f(c: float) -> float:
    return c * 1.8 + 32.0


def _build_probe(
    params: BaselineParams,
    *,
    label: str,
    input_temperature: float,
    input_unit: str,
    cell_temperature_f: float,
    irradiance_wm2: float,
    age: int = 1,
) -> SmokeProbe:
    bd = _expected_power_breakdown(params, irradiance_wm2, cell_temperature_f, age)
    return SmokeProbe(
        label=label,
        input_temperature=input_temperature,
        input_unit=input_unit,
        canonical_temperature_c=bd.cell_temperature_c,
        reference_temperature_c=bd.reference_temperature_c,
        delta_c=bd.delta_c,
        thermal_coefficient_unit="% per °C",
        thermal_coefficient_per_c=bd.thermal_coefficient_per_c,
        temperature_factor=bd.temperature_factor,
        irradiance_wm2=irradiance_wm2,
        irradiance_factor=bd.irradiance_factor,
        expected_power_kw=bd.clipped_kw,
        preclip_kw=bd.preclip_kw,
        is_clipped=bd.is_clipped,
    )


def run_smoke_test(baseline) -> SmokeTestReport:
    """Evaluate the canonical breakdown over a temperature/irradiance probe grid.

    Proves Fahrenheit/Celsius equivalence (same physical temperature → identical
    factor/output regardless of origin unit), temperature-factor monotonicity for
    a negative coefficient, and physical plausibility of the temperature factor.
    Returns ``ran=False`` (non-blocking here; the field checks already flag the
    absent required field) when the baseline lacks required physics inputs.
    """
    try:
        params = BaselineParams.from_baseline(baseline)
    except ValueError as exc:
        return SmokeTestReport(
            ran=False,
            reason_not_run=str(exc),
            celsius_fahrenheit_equivalence_verified=False,
        )

    probes: list[SmokeProbe] = []
    checks: list[SmokeCheck] = []

    # Temperature probes at STC irradiance (irradiance_factor == 1.0) in both
    # origins, plus two irradiance probes at 25 °C.
    c_probes: dict[float, SmokeProbe] = {}
    f_probes: dict[float, SmokeProbe] = {}
    for c in _TEMP_PROBES_C:
        f = _c_to_f(c)
        cp = _build_probe(
            params,
            label=f"{c:g}°C origin",
            input_temperature=c,
            input_unit="C",
            cell_temperature_f=f,  # canonical path converts back to °C
            irradiance_wm2=IRRADIANCE_BASELINE_WM2,
        )
        fp = _build_probe(
            params,
            label=f"{f:g}°F origin",
            input_temperature=f,
            input_unit="F",
            cell_temperature_f=f,
            irradiance_wm2=IRRADIANCE_BASELINE_WM2,
        )
        c_probes[c] = cp
        f_probes[c] = fp
        probes.append(cp)
        probes.append(fp)
    for irr in (200.0, 1000.0):
        probes.append(
            _build_probe(
                params,
                label=f"irradiance {irr:g} W/m² @ 25°C",
                input_temperature=25.0,
                input_unit="C",
                cell_temperature_f=_c_to_f(25.0),
                irradiance_wm2=irr,
            )
        )

    # Check 1: 25 °C / 77 °F → temperature factor == 1.0 (the STC reference).
    f25 = c_probes[25.0].temperature_factor
    f25_f = f_probes[25.0].temperature_factor
    ref_ok = math.isclose(f25, 1.0, abs_tol=_ABS_TOL) and math.isclose(
        f25_f, 1.0, abs_tol=_ABS_TOL
    )
    checks.append(
        SmokeCheck(
            name="reference_factor_unity_25c_77f",
            passed=ref_ok,
            classification=Classification.hard_invalid,
            detail=(
                f"temperature_factor at 25°C={f25:.9f}, at 77°F={f25_f:.9f}; "
                "both must equal 1.0."
            ),
        )
    )

    # Check 2: Celsius/Fahrenheit equivalence at every probed temperature.
    equivalence_ok = True
    for c in _TEMP_PROBES_C:
        cp, fp = c_probes[c], f_probes[c]
        same_factor = math.isclose(
            cp.temperature_factor, fp.temperature_factor, abs_tol=_ABS_TOL
        )
        same_power = math.isclose(
            cp.expected_power_kw, fp.expected_power_kw, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
        )
        same_canon = math.isclose(
            cp.canonical_temperature_c, fp.canonical_temperature_c, abs_tol=_ABS_TOL
        )
        ok = same_factor and same_power and same_canon
        equivalence_ok = equivalence_ok and ok
        checks.append(
            SmokeCheck(
                name=f"cf_equivalence_{c:g}c_{_c_to_f(c):g}f",
                passed=ok,
                classification=Classification.hard_invalid,
                detail=(
                    f"{c:g}°C → factor {cp.temperature_factor:.9f}, power "
                    f"{cp.expected_power_kw:.9f}; {_c_to_f(c):g}°F → factor "
                    f"{fp.temperature_factor:.9f}, power {fp.expected_power_kw:.9f}."
                ),
            )
        )

    # Check 3: monotonicity + positivity for a negative thermal coefficient.
    coeff = c_probes[25.0].thermal_coefficient_per_c
    factors = [c_probes[c].temperature_factor for c in _TEMP_PROBES_C]
    all_positive = all(f > 0 for f in factors)
    if coeff < 0:
        mono_ok = (
            c_probes[0.0].temperature_factor > c_probes[25.0].temperature_factor
            > c_probes[45.0].temperature_factor
            > c_probes[65.0].temperature_factor
        )
        checks.append(
            SmokeCheck(
                name="temperature_factor_monotonic_decreasing",
                passed=mono_ok and all_positive,
                classification=Classification.warning,
                detail=(
                    "For a negative coefficient the factor must strictly decrease "
                    f"with temperature and stay positive: factors={[round(f,6) for f in factors]}."
                ),
            )
        )

    # Check 4: physical plausibility of the temperature factor over 0–65 °C.
    in_range = all(0.5 <= f <= 1.5 for f in factors)
    checks.append(
        SmokeCheck(
            name="temperature_factor_physical_range",
            passed=in_range,
            classification=Classification.hard_invalid,
            detail=(
                "Across 0–65 °C every temperature factor must stay within "
                f"[0.5, 1.5]; factors={[round(f,6) for f in factors]} "
                "(a value far outside this band indicates a wrong-unit or "
                "absurd thermal coefficient)."
            ),
        )
    )

    # Demonstration (non-blocking): applying the %/°C coefficient against a raw
    # Fahrenheit delta (the classic unit-mismatch bug) yields a DIFFERENT factor,
    # confirming the canonical conversion path is what keeps the curve correct.
    f_for_45 = _c_to_f(45.0)
    canonical_factor_45 = c_probes[45.0].temperature_factor
    mismatch_factor_45 = 1.0 + coeff * (f_for_45 - CELL_TEMPERATURE_BASELINE_C)
    mismatch_detected = not math.isclose(
        canonical_factor_45, mismatch_factor_45, abs_tol=1e-6
    )
    unit_mismatch_demo = {
        "temperature_c": 45.0,
        "temperature_f": f_for_45,
        "thermal_coefficient_per_c": coeff,
        "canonical_factor_celsius_delta": canonical_factor_45,
        "mismatch_factor_fahrenheit_delta": mismatch_factor_45,
        "mismatch_detected": mismatch_detected,
        "note": (
            "A %/°C coefficient applied to a Fahrenheit delta produces a different "
            "(wrong) factor; production converts to °C first, so this mismatch "
            "cannot occur on the canonical path."
        ),
    }

    return SmokeTestReport(
        ran=True,
        reason_not_run=None,
        celsius_fahrenheit_equivalence_verified=equivalence_ok and ref_ok,
        temperature_input_modes_exercised=["celsius_native", "fahrenheit_converted"],
        probes=probes,
        checks=checks,
        unit_mismatch_demonstration=unit_mismatch_demo,
    )


# ---------------------------------------------------------------------------
# Aggregate
# ---------------------------------------------------------------------------


def _value_source(baseline) -> str:
    st = getattr(baseline, "source_type", None)
    if st is None:
        return "baseline_snapshot"
    return getattr(st, "value", str(st))


def _provenance(baseline) -> dict[str, Any]:
    status = getattr(baseline, "status", None)
    return {
        "baseline_id": getattr(baseline, "id", None),
        "baseline_status": getattr(status, "value", str(status) if status else None),
        "source_type": _value_source(baseline),
        "source_document_id": getattr(baseline, "source_document_id", None),
        "source_project_fact_id": getattr(baseline, "source_project_fact_id", None),
    }


def validate_baseline(
    baseline, *, validation_source_mode: str = "activation_gate"
) -> BaselineValidationReport:
    """Full physics verdict for one baseline. Pure: no DB writes, no mutation."""
    fields = validate_fields(baseline)
    cross = validate_cross_fields(baseline)
    smoke = run_smoke_test(baseline)

    blocking_fields = [
        f for f in (fields + cross) if f.classification == Classification.hard_invalid
    ]
    is_blocking = bool(blocking_fields) or smoke.has_blocking

    warning_count = sum(
        1 for f in (fields + cross) if f.classification == Classification.warning
    )
    if is_blocking:
        summary = (
            f"Baseline is physically invalid: {len(blocking_fields)} hard-invalid "
            f"field(s)"
            + (" + failed smoke checks" if smoke.has_blocking else "")
            + ". A source-backed replacement baseline is required."
        )
    elif warning_count:
        summary = (
            f"Baseline is plausible with {warning_count} field(s) requiring source "
            "confirmation before activation."
        )
    else:
        summary = "Baseline passes all physics-plausibility checks."

    return BaselineValidationReport(
        baseline_id=getattr(baseline, "id", None),
        is_blocking=is_blocking,
        summary=summary,
        policy_version=POLICY_VERSION,
        temperature_unit_contract=TEMPERATURE_UNIT_CONTRACT,
        temperature_unit_contract_version=TEMPERATURE_UNIT_CONTRACT_VERSION,
        validation_timestamp=datetime.now(timezone.utc).isoformat(),
        validation_source_mode=validation_source_mode,
        celsius_fahrenheit_equivalence_verified=(
            smoke.celsius_fahrenheit_equivalence_verified
        ),
        fields=fields,
        cross_field_checks=cross,
        smoke_test=smoke,
        provenance=_provenance(baseline),
    )


def is_active_baseline_blocking(baseline) -> bool:
    """Cheap read-path gate: True when an active baseline must NOT drive a curve.

    Used by the O&M read path to surface ``baseline_invalid`` (suppressing the
    expected/comparison curve while keeping actuals) WITHOUT mutating the row.
    """
    if baseline is None:
        return False
    return validate_baseline(
        baseline, validation_source_mode="read_time"
    ).is_blocking
