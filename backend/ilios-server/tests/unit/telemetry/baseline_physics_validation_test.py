"""Pure-logic tests for weather-adjusted baseline PHYSICS validation.

These exercise the additive, read-only validation seam end-to-end WITHOUT a
database: the per-field classifiers, the cross-field checks, the canonical
breakdown smoke test, the aggregate ``validate_baseline`` verdict (what the
fail-closed activation gate and the read-time ``baseline_invalid`` state both
consume), and the reference-condition diff helper.

The first-class requirement under test is the ONE canonical temperature-unit
contract: ``thermal_coefficient_pct`` is ``%/°C`` applied to a Celsius delta
from the 25 °C STC reference, and any Fahrenheit cell temperature is converted
exactly once via ``(F-32)/1.8`` on the SAME path production uses. The smoke
test probes the same physical temperature in both Celsius-origin and
Fahrenheit-origin form and asserts identical output — a Fahrenheit-vs-Celsius
defect cannot pass.

No formula math is asserted by re-derivation here; instead the breakdown is
pinned BYTE-IDENTICAL to the production ``_expected_power_kw`` so the
behavior-preserving extraction stays provably equivalent.
"""
from __future__ import annotations

import math
from datetime import date
from types import SimpleNamespace

import pytest

from app.services.telemetry import baseline_physics_validation as bpv
from app.services.telemetry.baseline_physics_validation import (
    Classification,
    is_active_baseline_blocking,
    run_smoke_test,
    validate_baseline,
    validate_cross_fields,
    validate_fields,
)
from app.services.telemetry.expected_service import (
    BaselineParams,
    _expected_power_breakdown,
    _expected_power_kw,
    reference_expected_power_kw,
)


# ---------------------------------------------------------------------------
# Stub baselines (ORM-shaped: validate_* and from_baseline read by getattr)
# ---------------------------------------------------------------------------
def _baseline(**overrides):
    """A clean, fully-plausible weather-adjusted baseline row.

    DC = 340 W * 1900 = 646 kW; AC = 66 kW * 7 = 462 kW; DC/AC ≈ 1.40.
    Every physics field is in a plausible band so the default fixture passes
    with no warnings; overrides inject the defect under test.
    """
    base = dict(
        id=999,
        status=SimpleNamespace(value="draft"),
        source_type=SimpleNamespace(value="reviewer_constant"),
        source_document_id=None,
        source_project_fact_id=None,
        module_wattage=340.0,
        module_quantity=1900.0,
        inverter_wattage=66.0,
        inverter_quantity=7.0,
        thermal_coefficient_pct=-0.35,
        power_tolerance_min_pct=0.0,
        year_1_degradation_pct=2.5,
        annual_degradation_pct=0.73,
        cec_efficiency_pct=97.0,
        soiling_factor=1.0,
        dc_loss_pct=2.0,
        ac_loss_pct=1.0,
        medium_voltage_loss_pct=0.0,
        mv_line_loss_pct=0.0,
        pto_date=date(2026, 5, 11),
        timezone="America/New_York",
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _field(results, name):
    return next(f for f in results if f.field == name)


def _check(report, name):
    return next(c for c in report.smoke_test.checks if c.name == name)


# ===========================================================================
# Behavior-preserving breakdown extraction (T002): byte-identical to prod calc
# ===========================================================================
class TestBreakdownByteIdentity:
    def _params(self, **o):
        base = dict(
            module_wattage=340.0,
            module_quantity=1900.0,
            inverter_wattage=66.0,
            inverter_quantity=7.0,
            thermal_coefficient_pct=-0.35,
            power_tolerance_min_pct=0.0,
            year_1_degradation_pct=2.5,
            annual_degradation_pct=0.73,
            cec_efficiency_pct=97.0,
            soiling_factor=1.0,
            dc_loss_pct=2.0,
            ac_loss_pct=1.0,
            medium_voltage_loss_pct=0.0,
            mv_line_loss_pct=0.0,
            pto_date=date(2026, 1, 1),
            timezone="UTC",
        )
        base.update(o)
        return BaselineParams(**base)

    @pytest.mark.parametrize("irr", [0.0, 200.0, 500.0, 800.0, 1000.0, 1200.0])
    @pytest.mark.parametrize("temp_f", [32.0, 77.0, 113.0, 149.0])
    @pytest.mark.parametrize("age", [0, 1, 5, 20])
    def test_clipped_kw_equals_expected_power_kw(self, irr, temp_f, age):
        p = self._params()
        bd = _expected_power_breakdown(p, irr, temp_f, age)
        # The extraction's clipped_kw must be EXACTLY what production returns.
        assert bd.clipped_kw == _expected_power_kw(p, irr, temp_f, age)
        # Pre-clip is never below the clipped value; clip flag is consistent.
        assert bd.preclip_kw >= bd.clipped_kw - 1e-12
        assert bd.is_clipped == (bd.preclip_kw > bd.clipped_kw + 1e-12) or not bd.is_clipped

    def test_canonical_f_to_c_conversion_single_site(self):
        # The breakdown converts F->C exactly once: 113F -> 45C.
        bd = _expected_power_breakdown(self._params(), 1000.0, 113.0, 0)
        assert bd.cell_temperature_c == pytest.approx(45.0)
        assert bd.reference_temperature_c == 25.0
        assert bd.delta_c == pytest.approx(20.0)


# ===========================================================================
# Fahrenheit / Celsius equivalence (first-class) via the smoke test
# ===========================================================================
class TestCelsiusFahrenheitEquivalence:
    def test_reference_factor_is_unity_at_25c_and_77f(self):
        report = validate_baseline(_baseline())
        chk = _check(report, "reference_factor_unity_25c_77f")
        assert chk.passed
        # Every 25C / 77F probe returns temperature_factor == 1.0.
        for p in report.smoke_test.probes:
            if p.canonical_temperature_c == pytest.approx(25.0):
                assert p.temperature_factor == pytest.approx(1.0, abs=1e-9)

    @pytest.mark.parametrize("c,f", [(0.0, 32.0), (25.0, 77.0), (45.0, 113.0), (65.0, 149.0)])
    def test_same_physical_temp_identical_output_both_origins(self, c, f):
        report = run_smoke_test(_baseline())
        c_probe = next(
            p for p in report.probes if p.input_unit == "C" and p.input_temperature == c
        )
        f_probe = next(
            p for p in report.probes if p.input_unit == "F" and p.input_temperature == f
        )
        # Same physical temperature -> identical canonical C, factor, and power
        # regardless of the origin unit (the F->C contract holds).
        assert c_probe.canonical_temperature_c == pytest.approx(f_probe.canonical_temperature_c)
        assert c_probe.temperature_factor == pytest.approx(f_probe.temperature_factor)
        assert c_probe.expected_power_kw == pytest.approx(f_probe.expected_power_kw)
        # And the matching per-temperature equivalence check passes.
        assert _check(validate_baseline(_baseline()), f"cf_equivalence_{c:g}c_{f:g}f").passed

    def test_minus_0_35_c_origin_equals_f_origin_end_to_end(self):
        report = validate_baseline(_baseline(thermal_coefficient_pct=-0.35))
        assert report.celsius_fahrenheit_equivalence_verified is True
        assert report.smoke_test.celsius_fahrenheit_equivalence_verified is True

    def test_unit_mismatch_fahrenheit_delta_is_demonstrably_different(self):
        # Applying the %/°C coefficient to a RAW Fahrenheit delta (the classic
        # bug) yields a different factor; the canonical path avoids it.
        demo = run_smoke_test(_baseline()).unit_mismatch_demonstration
        assert demo["mismatch_detected"] is True
        assert not math.isclose(
            demo["canonical_factor_celsius_delta"],
            demo["mismatch_factor_fahrenheit_delta"],
            abs_tol=1e-6,
        )

    def test_temperature_factor_monotonic_and_physical_for_negative_coeff(self):
        report = validate_baseline(_baseline())
        assert _check(report, "temperature_factor_monotonic_decreasing").passed
        assert _check(report, "temperature_factor_physical_range").passed


# ===========================================================================
# Coefficient-unit sanity (never auto-convert; flag ambiguous units)
# ===========================================================================
class TestThermalCoefficientUnitSanity:
    @pytest.mark.parametrize(
        "value,expected",
        [
            (-0.35, Classification.plausible),  # typical c-Si %/°C
            (-0.45, Classification.plausible),
            (-0.0035, Classification.warning),  # looks like a fraction per °C
            (-0.10, Classification.warning),  # unusually small magnitude
            (-0.63, Classification.warning),  # looks like a %/°F value copied in
            (0.0, Classification.hard_invalid),  # zero/positive is non-physical
            (350.0, Classification.hard_invalid),  # absurd magnitude (Site 4 #3)
        ],
    )
    def test_classification_bands(self, value, expected):
        res = _field(validate_fields(_baseline(thermal_coefficient_pct=value)), "thermal_coefficient_pct")
        assert res.classification == expected
        assert res.expected_unit == "% per °C"
        # Ambiguous-unit values are flagged, never silently reinterpreted.
        if expected is Classification.warning:
            assert "confirm" in res.reason.lower() or "unit" in res.reason.lower()
            assert res.required_action is not None


# ===========================================================================
# Per-field classifiers (representative bands)
# ===========================================================================
class TestFieldClassifiers:
    @pytest.mark.parametrize(
        "value,expected",
        [
            (0.0, Classification.plausible),
            (-3.0, Classification.plausible),
            (-7.0, Classification.warning),
            (-12.0, Classification.hard_invalid),
            (5.0, Classification.hard_invalid),  # positive min tolerance (Site 4 #3)
        ],
    )
    def test_power_tolerance_min(self, value, expected):
        res = _field(validate_fields(_baseline(power_tolerance_min_pct=value)), "power_tolerance_min_pct")
        assert res.classification == expected

    @pytest.mark.parametrize(
        "value,expected",
        [
            (97.0, Classification.plausible),
            (85.0, Classification.warning),
            (40.0, Classification.hard_invalid),
            (110.0, Classification.hard_invalid),
        ],
    )
    def test_cec_efficiency(self, value, expected):
        res = _field(validate_fields(_baseline(cec_efficiency_pct=value)), "cec_efficiency_pct")
        assert res.classification == expected

    @pytest.mark.parametrize(
        "value,expected",
        [
            (2.0, Classification.plausible),
            (20.0, Classification.warning),
            (40.0, Classification.hard_invalid),
            (-1.0, Classification.hard_invalid),
        ],
    )
    def test_loss_field(self, value, expected):
        res = _field(validate_fields(_baseline(dc_loss_pct=value)), "dc_loss_pct")
        assert res.classification == expected

    def test_missing_required_field_is_hard_invalid(self):
        res = _field(validate_fields(_baseline(module_wattage=None)), "module_wattage")
        assert res.classification == Classification.hard_invalid
        assert res.entered_value is None

    def test_missing_optional_loss_defaults_plausible(self):
        res = _field(validate_fields(_baseline(mv_line_loss_pct=None)), "mv_line_loss_pct")
        assert res.classification == Classification.plausible
        assert "default" in res.reason.lower()

    def test_inverter_wattage_watts_looking_value_is_warning_not_converted(self):
        # 66000 in a kW field looks like Watts -> warning, never auto-divided.
        res = _field(validate_fields(_baseline(inverter_wattage=66000.0)), "inverter_wattage")
        assert res.classification == Classification.warning
        assert res.entered_value == 66000.0


# ===========================================================================
# Cross-field checks (DC/AC ratio, aggregate AC-side loss)
# ===========================================================================
class TestCrossFieldChecks:
    def test_dc_ac_ratio_plausible(self):
        res = _field(validate_cross_fields(_baseline()), "dc_ac_ratio")
        assert res.classification == Classification.plausible
        assert res.entered_value == pytest.approx(1.40, abs=0.01)

    def test_dc_ac_ratio_implausible_is_hard_invalid(self):
        # AC tiny vs DC -> implausible ratio (kW-vs-W style error).
        res = _field(
            validate_cross_fields(_baseline(inverter_wattage=2.0, inverter_quantity=1.0)),
            "dc_ac_ratio",
        )
        assert res.classification == Classification.hard_invalid

    def test_ac_side_loss_total_aggregates(self):
        res = _field(
            validate_cross_fields(
                _baseline(ac_loss_pct=20.0, medium_voltage_loss_pct=20.0, mv_line_loss_pct=20.0)
            ),
            "ac_side_loss_total",
        )
        assert res.entered_value == pytest.approx(60.0)
        assert res.classification == Classification.hard_invalid


# ===========================================================================
# Aggregate verdict — what the gate + read-time state consume
# ===========================================================================
class TestAggregateVerdict:
    def test_clean_baseline_passes_no_block_no_warning(self):
        report = validate_baseline(_baseline())
        assert report.is_blocking is False
        assert report.has_warnings is False
        assert report.policy_version == bpv.POLICY_VERSION
        assert report.temperature_unit_contract_version == bpv.TEMPERATURE_UNIT_CONTRACT_VERSION
        assert report.celsius_fahrenheit_equivalence_verified is True

    def test_site4_baseline3_like_is_blocking(self):
        # thermal 350 + positive min tolerance -> two hard-invalid fields.
        report = validate_baseline(
            _baseline(thermal_coefficient_pct=350.0, power_tolerance_min_pct=5.0)
        )
        assert report.is_blocking is True
        blocking = {f.field for f in report.blocking_fields}
        assert "thermal_coefficient_pct" in blocking
        assert "power_tolerance_min_pct" in blocking

    def test_warning_only_baseline_is_not_blocking_but_has_warnings(self):
        report = validate_baseline(_baseline(thermal_coefficient_pct=-0.63))
        assert report.is_blocking is False
        assert report.has_warnings is True

    def test_validation_source_mode_is_recorded(self):
        report = validate_baseline(_baseline(), validation_source_mode="read_time")
        assert report.validation_source_mode == "read_time"
        d = report.to_dict()
        assert d["validation_source_mode"] == "read_time"
        assert d["policy_version"] == bpv.POLICY_VERSION

    def test_smoke_not_run_when_required_fields_absent(self):
        report = validate_baseline(_baseline(thermal_coefficient_pct=None))
        assert report.smoke_test.ran is False
        assert report.smoke_test.celsius_fahrenheit_equivalence_verified is False
        # The absent required field still drives the block.
        assert report.is_blocking is True


# ===========================================================================
# Read-path gate (validate-on-read, no mutation)
# ===========================================================================
class TestReadPathGate:
    def test_none_baseline_is_not_blocking(self):
        assert is_active_baseline_blocking(None) is False

    def test_clean_active_baseline_not_blocking(self):
        assert is_active_baseline_blocking(_baseline()) is False

    def test_invalid_active_baseline_blocks(self):
        assert (
            is_active_baseline_blocking(
                _baseline(thermal_coefficient_pct=350.0, power_tolerance_min_pct=5.0)
            )
            is True
        )

    def test_validation_does_not_mutate_baseline(self):
        b = _baseline(thermal_coefficient_pct=350.0)
        before = (b.thermal_coefficient_pct, b.power_tolerance_min_pct)
        is_active_baseline_blocking(b)
        validate_baseline(b)
        assert (b.thermal_coefficient_pct, b.power_tolerance_min_pct) == before


# ===========================================================================
# Reference-condition diff helper (never fabricate; canonical path)
# ===========================================================================
class TestReferenceExpectedPower:
    def test_returns_none_when_required_fields_absent(self):
        assert (
            reference_expected_power_kw(
                _baseline(module_wattage=None),
                irradiance_wm2=500.0,
                cell_temperature_f=113.0,
                age=0,
            )
            is None
        )

    def test_matches_canonical_breakdown(self):
        b = _baseline()
        params = BaselineParams.from_baseline(b)
        expected = _expected_power_breakdown(params, 500.0, 113.0, 0).clipped_kw
        assert (
            reference_expected_power_kw(
                b, irradiance_wm2=500.0, cell_temperature_f=113.0, age=0
            )
            == expected
        )

    def test_invalid_baseline_pins_to_ac_rating_at_partial_load(self):
        # The Site 4 #3-like thermal coefficient blows the temperature factor up,
        # pinning the reference power to the AC nameplate (462 kW) even at partial
        # load, which the corrected baseline does NOT.
        invalid = reference_expected_power_kw(
            _baseline(thermal_coefficient_pct=350.0),
            irradiance_wm2=500.0,
            cell_temperature_f=113.0,
            age=0,
        )
        corrected = reference_expected_power_kw(
            _baseline(thermal_coefficient_pct=-0.35),
            irradiance_wm2=500.0,
            cell_temperature_f=113.0,
            age=0,
        )
        assert invalid == pytest.approx(462.0)
        assert corrected < invalid
