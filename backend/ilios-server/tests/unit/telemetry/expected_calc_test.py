"""Golden tests for the native weather-adjusted expected calc (Phase P3.2).

These exercise the PURE calc core only (no DB): the legacy BigQuery physics
port, the honesty states (pre_pto / missing_inputs), the AC-nameplate clip,
site-local age boundaries, and loss-sign normalization. Expected numbers are
computed by hand from the documented formula so a regression in the port is
caught, not merely re-derived.
"""
from datetime import date, datetime

import pytest

from app.crud.telemetry_expected import _abs_or_none
from app.services.telemetry.expected_service import (
    BaselineParams,
    BucketInput,
    BucketStatus,
    _expected_power_kw,
    compute_expected_buckets,
)


def _params(**overrides) -> BaselineParams:
    """A fully-specified baseline; dc=400kW nameplate, ac=300kW.

    system_derate (age 0) = ptol(1) * soiling(1) * age_factor(1)
                          * dc_vd(0.98) * inv_eff(0.98) * ac_vd(0.99)
                          = 0.950796
    """
    base = dict(
        module_wattage=400.0,
        module_quantity=1000.0,  # dc_nameplate = 400 kW
        inverter_wattage=100.0,
        inverter_quantity=3.0,  # ac_nameplate = 300 kW
        thermal_coefficient_pct=-0.4,  # -0.004 /°C
        power_tolerance_min_pct=0.0,
        year_1_degradation_pct=2.0,
        annual_degradation_pct=0.5,
        cec_efficiency_pct=98.0,
        soiling_factor=1.0,
        dc_loss_pct=2.0,  # dc_vd = 0.98
        ac_loss_pct=1.0,  # ac_vd = 0.99
        medium_voltage_loss_pct=0.0,
        mv_line_loss_pct=0.0,
        pto_date=date(2024, 1, 1),
        timezone="UTC",
    )
    base.update(overrides)
    return BaselineParams(**base)


# Hand-computed reference value used across several cases.
_SYSTEM_DERATE_AGE0 = 0.98 * 0.98 * 0.99  # 0.950796


class TestExpectedPowerCore:
    def test_unclipped_age0_stc_half_irradiance(self):
        # irr 500 -> factor 0.5; temp 77F -> 25C -> temp_factor 1.
        power = _expected_power_kw(_params(), irradiance_wm2=500.0, cell_temperature_f=77.0, age=0)
        assert power == pytest.approx(400.0 * _SYSTEM_DERATE_AGE0 * 0.5)  # 190.1592

    def test_ac_nameplate_clip(self):
        # irr 1000 -> raw expected 380.3 kW, clipped to AC nameplate 300 kW.
        power = _expected_power_kw(_params(), irradiance_wm2=1000.0, cell_temperature_f=77.0, age=0)
        assert power == pytest.approx(300.0)

    def test_age1_applies_year1_degradation_only(self):
        # age_factor = 1 - 0.02 = 0.98
        power = _expected_power_kw(_params(), irradiance_wm2=500.0, cell_temperature_f=77.0, age=1)
        assert power == pytest.approx(400.0 * _SYSTEM_DERATE_AGE0 * 0.98 * 0.5)

    def test_age3_applies_year1_plus_annual(self):
        # age_factor = 1 - (0.02 + 0.005*(3-1)) = 1 - 0.03 = 0.97
        power = _expected_power_kw(_params(), irradiance_wm2=500.0, cell_temperature_f=77.0, age=3)
        assert power == pytest.approx(400.0 * _SYSTEM_DERATE_AGE0 * 0.97 * 0.5)

    def test_temperature_factor_above_stc(self):
        # 95F -> 35C -> temp_factor = 1 + (-0.004)*(35-25) = 0.96
        power = _expected_power_kw(_params(), irradiance_wm2=500.0, cell_temperature_f=95.0, age=0)
        assert power == pytest.approx(400.0 * _SYSTEM_DERATE_AGE0 * 0.5 * 0.96)

    def test_zero_irradiance_is_zero_not_missing(self):
        # 0 irradiance is a real (night) reading -> expected exactly 0, not NULL.
        power = _expected_power_kw(_params(), irradiance_wm2=0.0, cell_temperature_f=77.0, age=0)
        assert power == pytest.approx(0.0)


class TestBaselineParamsValidation:
    def test_from_baseline_raises_on_missing_required(self):
        class _Stub:
            id = 7
            # all required physics fields absent -> None via getattr default

        with pytest.raises(ValueError) as exc:
            BaselineParams.from_baseline(_Stub())
        assert "module_wattage" in str(exc.value)


class TestComputeExpectedBuckets:
    def _bucket(self, ts, irr=500.0, temp=77.0, actual=123.0):
        return BucketInput(
            bucket_start=ts, irradiance_wm2=irr, cell_temperature_f=temp, actual_power_kw=actual
        )

    def test_pre_pto_when_pto_is_none(self):
        params = _params(pto_date=None)
        out = compute_expected_buckets(params, [self._bucket(datetime(2025, 6, 15, 12))], 1.0)
        assert out[0].status == BucketStatus.pre_pto
        assert out[0].expected_power_kw is None
        assert out[0].expected_energy_kwh is None
        # actual is independent and still surfaced.
        assert out[0].actual_power_kw == 123.0

    def test_pre_pto_when_bucket_before_pto(self):
        out = compute_expected_buckets(_params(), [self._bucket(datetime(2023, 12, 31, 12))], 1.0)
        assert out[0].status == BucketStatus.pre_pto
        assert out[0].expected_power_kw is None

    def test_pto_boundary_day_is_ok(self):
        out = compute_expected_buckets(_params(), [self._bucket(datetime(2024, 1, 1, 12))], 1.0)
        assert out[0].status == BucketStatus.ok
        assert out[0].age_years == 0

    def test_missing_irradiance_is_missing_inputs(self):
        out = compute_expected_buckets(_params(), [self._bucket(datetime(2025, 6, 15, 12), irr=None)], 1.0)
        assert out[0].status == BucketStatus.missing_inputs
        assert out[0].expected_power_kw is None

    def test_missing_cell_temp_is_missing_inputs(self):
        out = compute_expected_buckets(_params(), [self._bucket(datetime(2025, 6, 15, 12), temp=None)], 1.0)
        assert out[0].status == BucketStatus.missing_inputs
        assert out[0].expected_power_kw is None

    def test_ok_energy_scales_with_bucket_hours(self):
        out = compute_expected_buckets(_params(), [self._bucket(datetime(2025, 6, 15, 12))], 0.25)
        b = out[0]
        assert b.status == BucketStatus.ok
        assert b.expected_energy_kwh == pytest.approx(b.expected_power_kw * 0.25)

    def test_site_local_timezone_shifts_pre_pto_boundary(self):
        # 2024-01-01 03:00 UTC is still 2023-12-31 in America/New_York (UTC-5),
        # so a NY site is pre_pto while a UTC site is ok.
        ts = datetime(2024, 1, 1, 3, 0)
        ny = compute_expected_buckets(_params(timezone="America/New_York"), [self._bucket(ts)], 1.0)
        utc = compute_expected_buckets(_params(timezone="UTC"), [self._bucket(ts)], 1.0)
        assert ny[0].status == BucketStatus.pre_pto
        assert utc[0].status == BucketStatus.ok

    def test_invalid_timezone_falls_back_to_utc(self):
        ts = datetime(2024, 1, 1, 3, 0)
        out = compute_expected_buckets(_params(timezone="Not/AZone"), [self._bucket(ts)], 1.0)
        # UTC fallback -> 2024-01-01 -> ok (not pre_pto).
        assert out[0].status == BucketStatus.ok


class TestLossSignNormalization:
    def test_abs_or_none(self):
        assert _abs_or_none(-2.5) == 2.5
        assert _abs_or_none(3.0) == 3.0
        assert _abs_or_none(0) == 0
        assert _abs_or_none(None) is None
