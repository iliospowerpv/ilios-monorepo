"""Unit tests for the V2 native-expected wiring into the O&M site charts.

These exercise the *honesty contract* (never fabricate an expected, never turn a
missing expected into 0, keep a genuine 0 distinguishable) at the pure-logic
seams: the ratio validator, the ``expected_state`` derivation, the None-safe
schema validators, and the three chart builders. The builders are tested by
monkeypatching their two DB seams (``_active_baseline`` and
``compute_site_expected``) so no database or rollup fixtures are required.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

import app.helpers.telemetry.v2_chart_data as v2
import app.helpers.telemetry.v2_company_data as vc
from app.schema.common import calculate_actual_vs_expected
from app.schema.om_site import SiteDashboardActualProductionSection
from app.services.telemetry.expected_service import (
    BucketStatus,
    ExpectedBucket,
    ExpectedResult,
    ExpectedState,
    OverallStatus,
    derive_expected_state,
)


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------
def _bucket(ts, status, *, exp_p=None, exp_e=None, act=None, irr=None):
    return ExpectedBucket(
        bucket_start=ts,
        status=status,
        expected_power_kw=exp_p,
        expected_energy_kwh=exp_e,
        actual_power_kw=act,
        irradiance_wm2=irr,
        cell_temperature_f=None,
        age_years=None,
    )


def _result(buckets, *, overall=OverallStatus.ok, baseline_id=7, exp_energy=None):
    return ExpectedResult(
        overall_status=overall,
        baseline_id=baseline_id,
        baseline_type="weather_adjusted_model",
        bucket_size="1h",
        window_start=buckets[0].bucket_start if buckets else datetime(2026, 6, 1),
        window_end=datetime(2026, 6, 11),
        buckets=buckets,
        expected_energy_kwh=exp_energy,
        actual_energy_kwh=None,
        ok_bucket_count=sum(1 for b in buckets if b.status == BucketStatus.ok),
        missing_inputs_bucket_count=sum(
            1 for b in buckets if b.status == BucketStatus.missing_inputs
        ),
        pre_pto_bucket_count=sum(1 for b in buckets if b.status == BucketStatus.pre_pto),
    )


class _Row:
    def __init__(self, bucket_start, value, normalized_metric=v2.SITE_POWER_METRIC):
        self.bucket_start = bucket_start
        self.value = value
        self.normalized_metric = normalized_metric


def _fake_site_rollup_crud(today_rows, latest_rows=None):
    """A drop-in for TelemetrySiteRollupCRUD returning canned rows."""

    class _FakeCRUD:
        def __init__(self, _db):
            pass

        def get_series(self, **_kwargs):
            return today_rows

        def get_latest_per_metric(self, _site_id, **_kwargs):
            return latest_rows or []

    return _FakeCRUD


# ---------------------------------------------------------------------------
# calculate_actual_vs_expected — the core "no fabricated 0%" contract
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "actual,expected,result",
    [
        (None, 5, None),  # no actual -> N/A, not 0%
        (5, None, None),  # no expected (missing/no baseline) -> N/A
        (5, 0, None),  # expected 0 -> undefined ratio, not 0%
        (0, 5, 0),  # genuine zero production vs real expected -> a real 0%
        (50, 100, 50),
        (75, 100, 75),
    ],
)
def test_calculate_actual_vs_expected_honesty(actual, expected, result):
    assert calculate_actual_vs_expected(actual, expected) == result


# ---------------------------------------------------------------------------
# derive_expected_state
# ---------------------------------------------------------------------------
def test_derive_state_no_baseline():
    res = _result([], overall=OverallStatus.baseline_not_available, baseline_id=None)
    assert derive_expected_state(res) == ExpectedState.baseline_not_available


def test_derive_state_baseline_but_no_buckets_is_missing_inputs():
    # Baseline present, but the window had no rollup buckets at all.
    res = _result([], overall=OverallStatus.ok)
    assert derive_expected_state(res) == ExpectedState.missing_inputs


def test_derive_state_all_ok_is_available():
    res = _result(
        [
            _bucket(datetime(2026, 6, 10, 10), BucketStatus.ok, exp_p=8, exp_e=8),
            _bucket(datetime(2026, 6, 10, 11), BucketStatus.ok, exp_p=9, exp_e=9),
        ]
    )
    assert derive_expected_state(res) == ExpectedState.available


def test_derive_state_mixed_is_partial():
    res = _result(
        [
            _bucket(datetime(2026, 6, 10, 10), BucketStatus.ok, exp_p=8, exp_e=8),
            _bucket(datetime(2026, 6, 10, 11), BucketStatus.missing_inputs),
        ]
    )
    assert derive_expected_state(res) == ExpectedState.partial


def test_derive_state_no_ok_dominant_reason():
    missing_heavy = _result(
        [
            _bucket(datetime(2026, 6, 10, 10), BucketStatus.missing_inputs),
            _bucket(datetime(2026, 6, 10, 11), BucketStatus.missing_inputs),
            _bucket(datetime(2026, 6, 10, 12), BucketStatus.pre_pto),
        ]
    )
    assert derive_expected_state(missing_heavy) == ExpectedState.missing_inputs

    pre_heavy = _result(
        [
            _bucket(datetime(2026, 6, 10, 10), BucketStatus.pre_pto),
            _bucket(datetime(2026, 6, 10, 11), BucketStatus.pre_pto),
            _bucket(datetime(2026, 6, 10, 12), BucketStatus.missing_inputs),
        ]
    )
    assert derive_expected_state(pre_heavy) == ExpectedState.pre_pto

    # Tie (and at least one of each) resolves to missing_inputs.
    tie = _result(
        [
            _bucket(datetime(2026, 6, 10, 10), BucketStatus.pre_pto),
            _bucket(datetime(2026, 6, 10, 11), BucketStatus.missing_inputs),
        ]
    )
    assert derive_expected_state(tie) == ExpectedState.missing_inputs


# ---------------------------------------------------------------------------
# Schema validators — None-safe, no fabricated 0
# ---------------------------------------------------------------------------
def _section(**overrides):
    base = dict(
        id=1,
        name="x",
        system_size_ac=10,
        system_size_dc=12,
        actual_kw=5.0,
        expected_kw=None,
        cumulative_actual_kw=3.0,
        cumulative_expected_kw=None,
        expected_baseline_available=False,
    )
    base.update(overrides)
    return SiteDashboardActualProductionSection(**base)


def test_section_no_expected_is_none_not_zero():
    s = _section(expected_state=ExpectedState.baseline_not_available.value)
    assert s.actual_vs_expected is None
    assert s.performance_index is None
    assert s.cumulative_actual_vs_expected is None
    assert s.cumulative_performance_index is None
    # Actual stays visible.
    assert s.actual_kw == 5.0
    assert s.cumulative_actual_kw == 3.0


def test_section_with_expected_computes_real_numbers():
    s = _section(
        expected_kw=10.0,
        cumulative_expected_kw=6.0,
        expected_baseline_available=True,
        expected_state=ExpectedState.available.value,
        baseline_id=7,
    )
    assert s.actual_vs_expected == 50
    assert s.performance_index == 0.5
    assert s.cumulative_actual_vs_expected == 50
    assert s.cumulative_performance_index == 0.5
    assert s.baseline_id == 7


def test_section_genuine_zero_is_zero_not_none():
    s = _section(
        actual_kw=0.0,
        expected_kw=10.0,
        cumulative_actual_kw=0.0,
        cumulative_expected_kw=6.0,
        expected_baseline_available=True,
        expected_state=ExpectedState.available.value,
    )
    assert s.actual_vs_expected == 0
    assert s.performance_index == 0.0
    assert s.cumulative_actual_vs_expected == 0


# ---------------------------------------------------------------------------
# _expected_power_for_bucket — strict alignment
# ---------------------------------------------------------------------------
def test_expected_power_for_bucket_strict_alignment():
    ts = datetime(2026, 6, 10, 14)
    ok = _result([_bucket(ts, BucketStatus.ok, exp_p=8.0, exp_e=8.0)])
    missing = _result([_bucket(ts, BucketStatus.missing_inputs)])

    assert v2._expected_power_for_bucket(ok, _Row(ts, 7.0)) == 8.0
    # Same timestamp but not ok -> None (never borrow a neighbour).
    assert v2._expected_power_for_bucket(missing, _Row(ts, 7.0)) is None
    # No actual bucket -> None.
    assert v2._expected_power_for_bucket(ok, None) is None
    # No matching bucket_start -> None.
    assert v2._expected_power_for_bucket(ok, _Row(datetime(2026, 6, 10, 15), 7.0)) is None


# ---------------------------------------------------------------------------
# apply_v2_actual_production
# ---------------------------------------------------------------------------
def test_apply_actual_production_no_baseline(monkeypatch):
    rows = [_Row(datetime(2026, 6, 10, 10), 4.0), _Row(datetime(2026, 6, 10, 11), 6.0)]
    monkeypatch.setattr(v2, "TelemetrySiteRollupCRUD", _fake_site_rollup_crud(rows))
    monkeypatch.setattr(v2, "_active_baseline", lambda _db, _sid: None)

    site = SimpleNamespace(id=1, timezone="UTC")
    v2.apply_v2_actual_production(None, site)

    assert site.actual_kw == 6.0  # latest today bucket
    assert site.cumulative_actual_kw == 10.0  # sum of today's buckets
    assert site.expected_kw is None
    assert site.cumulative_expected_kw is None
    assert site.expected_baseline_available is False
    assert site.expected_state == ExpectedState.baseline_not_available.value
    assert site.baseline_id is None


def test_apply_actual_production_baseline_latest_bucket_ok(monkeypatch):
    latest_ts = datetime(2026, 6, 10, 11)
    rows = [_Row(datetime(2026, 6, 10, 10), 4.0), _Row(latest_ts, 6.0)]
    monkeypatch.setattr(v2, "TelemetrySiteRollupCRUD", _fake_site_rollup_crud(rows))
    monkeypatch.setattr(v2, "_active_baseline", lambda _db, _sid: object())
    result = _result(
        [
            _bucket(datetime(2026, 6, 10, 10), BucketStatus.ok, exp_p=5.0, exp_e=5.0),
            _bucket(latest_ts, BucketStatus.ok, exp_p=8.0, exp_e=8.0),
        ],
        exp_energy=13.0,
    )
    monkeypatch.setattr(v2, "compute_site_expected", lambda *a, **k: result)

    site = SimpleNamespace(id=1, timezone="UTC")
    v2.apply_v2_actual_production(None, site)

    assert site.expected_kw == 8.0  # aligned to the latest (ok) bucket
    assert site.cumulative_expected_kw == 13.0
    assert site.expected_baseline_available is True
    assert site.expected_state == ExpectedState.available.value
    assert site.baseline_id == 7


def test_apply_actual_production_baseline_latest_bucket_missing(monkeypatch):
    latest_ts = datetime(2026, 6, 10, 11)
    rows = [_Row(datetime(2026, 6, 10, 10), 4.0), _Row(latest_ts, 6.0)]
    monkeypatch.setattr(v2, "TelemetrySiteRollupCRUD", _fake_site_rollup_crud(rows))
    monkeypatch.setattr(v2, "_active_baseline", lambda _db, _sid: object())
    result = _result(
        [
            _bucket(datetime(2026, 6, 10, 10), BucketStatus.ok, exp_p=5.0, exp_e=5.0),
            _bucket(latest_ts, BucketStatus.missing_inputs),
        ],
        exp_energy=5.0,
    )
    monkeypatch.setattr(v2, "compute_site_expected", lambda *a, **k: result)

    site = SimpleNamespace(id=1, timezone="UTC")
    v2.apply_v2_actual_production(None, site)

    # Latest bucket not ok -> instantaneous expected is N/A, but cumulative still
    # reflects the ok buckets and the state is partial.
    assert site.expected_kw is None
    assert site.cumulative_expected_kw == 5.0
    assert site.expected_state == ExpectedState.partial.value


# ---------------------------------------------------------------------------
# build_actual_vs_expected_section
# ---------------------------------------------------------------------------
def test_actual_vs_expected_section_no_baseline(monkeypatch):
    monkeypatch.setattr(v2, "_active_baseline", lambda _db, _sid: None)
    sentinel = [{"period": datetime(2026, 6, 10), "actual": 1.0, "expected": None, "irradiance": 2.0}]
    monkeypatch.setattr(v2, "_actual_irradiance_series", lambda *a, **k: sentinel)

    out = v2.build_actual_vs_expected_section(None, SimpleNamespace(id=1, timezone="UTC"))
    assert out["data"] is sentinel
    assert out["expected_baseline_available"] is False
    assert out["expected_state"] == ExpectedState.baseline_not_available.value


def test_actual_vs_expected_section_with_baseline_passthrough_and_fill(monkeypatch):
    monkeypatch.setattr(v2, "_active_baseline", lambda _db, _sid: object())
    result = _result(
        [
            # ok bucket: expected passes through, actual/irradiance present
            _bucket(datetime(2026, 6, 10, 10), BucketStatus.ok, exp_p=8.0, act=7.0, irr=600.0),
            # missing bucket: expected None, actual/irradiance None -> 0.0-filled
            _bucket(datetime(2026, 6, 10, 11), BucketStatus.missing_inputs),
        ]
    )
    monkeypatch.setattr(v2, "compute_site_expected", lambda *a, **k: result)

    out = v2.build_actual_vs_expected_section(None, SimpleNamespace(id=1, timezone="UTC"))
    assert out["expected_baseline_available"] is True
    assert out["expected_state"] == ExpectedState.partial.value
    p0, p1 = out["data"]
    assert p0 == {"period": datetime(2026, 6, 10, 10), "actual": 7.0, "expected": 8.0, "irradiance": 600.0}
    # missing-inputs bucket: expected stays None (never fabricated), others 0.0-filled
    assert p1 == {"period": datetime(2026, 6, 10, 11), "actual": 0.0, "expected": None, "irradiance": 0.0}


# ---------------------------------------------------------------------------
# build_past_performance_section
# ---------------------------------------------------------------------------
def test_past_performance_no_baseline(monkeypatch):
    monkeypatch.setattr(v2, "_active_baseline", lambda _db, _sid: None)
    out = v2.build_past_performance_section(None, SimpleNamespace(id=1, timezone="UTC"))
    assert out == {
        "data": {},
        "expected_baseline_available": False,
        "expected_state": ExpectedState.baseline_not_available.value,
    }


def test_past_performance_daily_aggregation(monkeypatch):
    monkeypatch.setattr(v2, "_active_baseline", lambda _db, _sid: object())
    result = _result(
        [
            # Day 2026-06-09: two ok buckets -> Σactual 20 / Σexpected 20 = 100%
            _bucket(datetime(2026, 6, 9, 10), BucketStatus.ok, exp_e=10.0, act=8.0),
            _bucket(datetime(2026, 6, 9, 11), BucketStatus.ok, exp_e=10.0, act=12.0),
            # Day 2026-06-10: only a missing bucket -> None (honest gap, not 0%)
            _bucket(datetime(2026, 6, 10, 10), BucketStatus.missing_inputs),
            # Day 2026-06-11: ok bucket, zero actual vs real expected -> genuine 0%
            _bucket(datetime(2026, 6, 11, 10), BucketStatus.ok, exp_e=10.0, act=0.0),
        ]
    )
    monkeypatch.setattr(v2, "compute_site_expected", lambda *a, **k: result)

    out = v2.build_past_performance_section(None, SimpleNamespace(id=1, timezone="UTC"))
    assert out["expected_baseline_available"] is True
    assert out["data"] == {
        datetime(2026, 6, 9): 100,
        datetime(2026, 6, 10): None,
        datetime(2026, 6, 11): 0,
    }


# ===========================================================================
# S6 — Company / investor / portfolio expected aggregation (v2_company_data)
#
# The company honesty contract: a company-level expected is a real number ONLY
# when EVERY telemetry-backed site (a site with V2 rollups) is fully computable
# (`available`). Otherwise expected is None and the additive metadata
# (`expected_state` + the three coverage counts) explains the gap. Never
# fabricate, never turn a missing expected into 0, and a genuine 0 (e.g. loss
# floored at zero) stays distinguishable from "unknown".
# ===========================================================================
def _site(site_id):
    return SimpleNamespace(id=site_id, timezone="UTC")


def _exp(state, energy=None, power=None):
    return vc.SiteExpectedToday(
        state=state, expected_energy_kwh=energy, expected_power_latest_kw=power
    )


# ---------------------------------------------------------------------------
# aggregate_company_expected — pure honest roll-up
# ---------------------------------------------------------------------------
def test_company_expected_no_telemetry_sites_is_baseline_not_available():
    # A company with sites but none V2-backed -> nothing to compare against.
    out = vc.aggregate_company_expected([_site(1)], set(), {}, {})
    assert out["total_expected_kw"] is None
    assert out["cumulative_expected_kw"] is None
    assert out["expected_baseline_available"] is False
    assert out["expected_state"] == ExpectedState.baseline_not_available.value
    assert out["sites_with_telemetry"] == 0
    assert out["sites_with_active_baseline"] == 0
    assert out["sites_missing_baseline"] == 0


def test_company_expected_all_sites_available_is_real_sum():
    sites = [_site(1), _site(2)]
    baselines = {1: object(), 2: object()}
    expected = {
        1: _exp(ExpectedState.available, energy=10.0, power=5.0),
        2: _exp(ExpectedState.available, energy=20.0, power=7.0),
    }
    out = vc.aggregate_company_expected(sites, {1, 2}, baselines, expected)
    assert out["cumulative_expected_kw"] == 30.0
    assert out["total_expected_kw"] == 12.0
    assert out["expected_baseline_available"] is True
    assert out["expected_state"] == ExpectedState.available.value
    assert out["sites_with_telemetry"] == 2
    assert out["sites_with_active_baseline"] == 2
    assert out["sites_missing_baseline"] == 0


def test_company_expected_one_telemetry_site_without_baseline_is_partial_null():
    # Site 2 has rollups but no active baseline -> the company sum would be
    # misleadingly low, so expected is None and the state is partial.
    sites = [_site(1), _site(2)]
    baselines = {1: object()}
    expected = {1: _exp(ExpectedState.available, energy=10.0, power=5.0)}
    out = vc.aggregate_company_expected(sites, {1, 2}, baselines, expected)
    assert out["total_expected_kw"] is None
    assert out["cumulative_expected_kw"] is None
    assert out["expected_baseline_available"] is False
    assert out["expected_state"] == ExpectedState.partial.value
    assert out["sites_with_telemetry"] == 2
    assert out["sites_with_active_baseline"] == 1
    assert out["sites_missing_baseline"] == 1


def test_company_expected_all_missing_baseline_is_baseline_not_available():
    sites = [_site(1), _site(2)]
    out = vc.aggregate_company_expected(sites, {1, 2}, {}, {})
    assert out["expected_state"] == ExpectedState.baseline_not_available.value
    assert out["expected_baseline_available"] is False
    assert out["sites_with_telemetry"] == 2
    assert out["sites_with_active_baseline"] == 0
    assert out["sites_missing_baseline"] == 2


def test_company_expected_available_plus_missing_inputs_is_partial():
    # Both sites have baselines, but site 2's inputs are missing today.
    sites = [_site(1), _site(2)]
    baselines = {1: object(), 2: object()}
    expected = {
        1: _exp(ExpectedState.available, energy=10.0, power=5.0),
        2: _exp(ExpectedState.missing_inputs, energy=None, power=None),
    }
    out = vc.aggregate_company_expected(sites, {1, 2}, baselines, expected)
    assert out["total_expected_kw"] is None
    assert out["cumulative_expected_kw"] is None
    assert out["expected_state"] == ExpectedState.partial.value
    assert out["sites_with_active_baseline"] == 2
    assert out["sites_missing_baseline"] == 0


def test_company_expected_available_but_incomplete_power_keeps_energy_only():
    # All available -> cumulative (energy) is a real sum, but if any site lacks a
    # latest-bucket expected power, the instantaneous total stays None.
    sites = [_site(1), _site(2)]
    baselines = {1: object(), 2: object()}
    expected = {
        1: _exp(ExpectedState.available, energy=10.0, power=5.0),
        2: _exp(ExpectedState.available, energy=20.0, power=None),
    }
    out = vc.aggregate_company_expected(sites, {1, 2}, baselines, expected)
    assert out["cumulative_expected_kw"] == 30.0
    assert out["total_expected_kw"] is None
    assert out["expected_baseline_available"] is True
    assert out["expected_state"] == ExpectedState.available.value


def test_company_expected_ignores_non_telemetry_company_sites():
    # Site 3 belongs to the company but has no V2 rollups -> it must not count as
    # a missing baseline nor block the available aggregate.
    sites = [_site(1), _site(2), _site(3)]
    baselines = {1: object(), 2: object()}
    expected = {
        1: _exp(ExpectedState.available, energy=10.0, power=5.0),
        2: _exp(ExpectedState.available, energy=20.0, power=7.0),
    }
    out = vc.aggregate_company_expected(sites, {1, 2}, baselines, expected)
    assert out["expected_state"] == ExpectedState.available.value
    assert out["sites_with_telemetry"] == 2
    assert out["sites_missing_baseline"] == 0
    assert out["cumulative_expected_kw"] == 30.0


# ---------------------------------------------------------------------------
# _summarize_site_expected — per-site honesty at the metric-map seam
# ---------------------------------------------------------------------------
def test_summarize_site_expected_no_metric_maps_is_missing_inputs():
    out = vc._summarize_site_expected(
        site_id=1,
        baseline=object(),
        metric_maps=None,
        bucket_hours=1.0,
        bucket_size="1h",
        window_start=datetime(2026, 6, 11),
        window_end=datetime(2026, 6, 11, 12),
    )
    assert out.state == ExpectedState.missing_inputs
    assert out.expected_energy_kwh is None
    assert out.expected_power_latest_kw is None


def test_summarize_site_expected_incomplete_baseline_is_missing_inputs(monkeypatch):
    # An active baseline whose physics cannot be parsed must surface
    # missing_inputs, never a fabricated expected.
    def _raise(_baseline):
        raise ValueError("incomplete")

    monkeypatch.setattr(vc.BaselineParams, "from_baseline", staticmethod(_raise))
    out = vc._summarize_site_expected(
        site_id=1,
        baseline=object(),
        metric_maps={
            vc.SITE_POWER_METRIC: {datetime(2026, 6, 11, 10): 5.0},
            vc.IRRADIANCE_METRIC: {},
            vc.CELL_TEMPERATURE_METRIC: {},
        },
        bucket_hours=1.0,
        bucket_size="1h",
        window_start=datetime(2026, 6, 11),
        window_end=datetime(2026, 6, 11, 12),
    )
    assert out.state == ExpectedState.missing_inputs
    assert out.expected_energy_kwh is None


def test_summarize_site_expected_aligns_to_latest_actual_and_comparable_set(monkeypatch):
    """Sites-table fields anchor to ACTUAL coverage, never the union's latest bucket.

    Two early ``ok`` buckets WITH actual power, then a later ``ok`` weather-only
    bucket (no actual power). The union-latest expected power anchors to the
    weather-only bucket (the company-aggregate field, unchanged), but the table
    fields must anchor to the latest ACTUAL power bucket and sum only over
    comparable (``ok`` + actual-present) buckets.
    """
    from app.services.telemetry.expected_service import BucketStatus, ExpectedBucket

    t1 = datetime(2026, 6, 11, 9)
    t2 = datetime(2026, 6, 11, 10)  # latest ACTUAL power bucket
    t3 = datetime(2026, 6, 11, 11)  # later, weather-only (no actual power)
    buckets = [
        ExpectedBucket(t1, BucketStatus.ok, 6.0, 6.0, 4.0, 600.0, 95.0, 1),
        ExpectedBucket(t2, BucketStatus.ok, 8.0, 8.0, 5.0, 600.0, 95.0, 1),
        ExpectedBucket(t3, BucketStatus.ok, 10.0, 10.0, None, 600.0, 95.0, 1),
    ]
    monkeypatch.setattr(vc.BaselineParams, "from_baseline", staticmethod(lambda _b: object()))
    monkeypatch.setattr(vc, "compute_expected_buckets", lambda _p, _i, _h: buckets)

    out = vc._summarize_site_expected(
        site_id=1,
        baseline=object(),
        metric_maps={
            vc.SITE_POWER_METRIC: {t1: 4.0, t2: 5.0},  # no t3 power
            vc.IRRADIANCE_METRIC: {t1: 600.0, t2: 600.0, t3: 600.0},
            vc.CELL_TEMPERATURE_METRIC: {t1: 95.0, t2: 95.0, t3: 95.0},
        },
        bucket_hours=1.0,
        bucket_size="1h",
        window_start=datetime(2026, 6, 11),
        window_end=datetime(2026, 6, 11, 12),
    )
    # Union-latest field (company aggregate) still anchors to the weather-only bucket.
    assert out.expected_power_latest_kw == 10.0
    # Table field anchors to the latest ACTUAL power bucket (t2), not t3.
    assert out.expected_power_at_latest_actual_kw == 8.0
    # Comparable sums cover ONLY the ok buckets WITH actual power (t1, t2).
    assert out.comparable_actual_energy_kwh == 9.0  # 4 + 5
    assert out.comparable_expected_energy_kwh == 14.0  # 6 + 8


def test_summarize_site_expected_latest_actual_bucket_not_ok_yields_none(monkeypatch):
    """When the latest ACTUAL power bucket is not ``ok``, the aligned expected power
    is None (no cross-bucket borrowing), and the comparable set excludes it."""
    from app.services.telemetry.expected_service import BucketStatus, ExpectedBucket

    t1 = datetime(2026, 6, 11, 9)
    t2 = datetime(2026, 6, 11, 10)  # latest actual power bucket, but missing_inputs
    buckets = [
        ExpectedBucket(t1, BucketStatus.ok, 6.0, 6.0, 4.0, 600.0, 95.0, 1),
        ExpectedBucket(t2, BucketStatus.missing_inputs, None, None, 5.0, None, None, 1),
    ]
    monkeypatch.setattr(vc.BaselineParams, "from_baseline", staticmethod(lambda _b: object()))
    monkeypatch.setattr(vc, "compute_expected_buckets", lambda _p, _i, _h: buckets)

    out = vc._summarize_site_expected(
        site_id=1,
        baseline=object(),
        metric_maps={
            vc.SITE_POWER_METRIC: {t1: 4.0, t2: 5.0},
            vc.IRRADIANCE_METRIC: {t1: 600.0},
            vc.CELL_TEMPERATURE_METRIC: {t1: 95.0},
        },
        bucket_hours=1.0,
        bucket_size="1h",
        window_start=datetime(2026, 6, 11),
        window_end=datetime(2026, 6, 11, 12),
    )
    assert out.expected_power_at_latest_actual_kw is None  # latest actual bucket not ok
    # Only t1 is ok AND has actual power.
    assert out.comparable_actual_energy_kwh == 4.0
    assert out.comparable_expected_energy_kwh == 6.0


# ---------------------------------------------------------------------------
# compute_sites_expected_today — windowed query, per-site local-day attribution
# ---------------------------------------------------------------------------
class _CRow:
    def __init__(self, site_id, normalized_metric, bucket_start, value):
        self.site_id = site_id
        self.normalized_metric = normalized_metric
        self.bucket_start = bucket_start
        self.value = value


class _FakeQuery:
    def __init__(self, rows):
        self._rows = rows

    def filter(self, *a, **k):
        return self

    def all(self):
        return self._rows


class _FakeDB:
    def __init__(self, rows):
        self._rows = rows

    def query(self, *a, **k):
        return _FakeQuery(self._rows)


def test_compute_sites_expected_today_attribution_and_baseline_filter(monkeypatch):
    now = datetime.utcnow()
    midnight = datetime(now.year, now.month, now.day)
    today_ts = midnight + timedelta(hours=10)
    yesterday_ts = midnight - timedelta(hours=2)
    rows = [
        _CRow(1, vc.SITE_POWER_METRIC, today_ts, 5.0),
        _CRow(1, vc.IRRADIANCE_METRIC, today_ts, 600.0),
        _CRow(1, vc.SITE_POWER_METRIC, yesterday_ts, 99.0),  # before today -> excluded
        _CRow(2, vc.SITE_POWER_METRIC, today_ts, 7.0),  # site 2 has no baseline
    ]

    captured = {}

    def fake_summarize(*, site_id, baseline, metric_maps, **_kw):
        captured[site_id] = metric_maps
        return _exp(ExpectedState.available, energy=1.0, power=1.0)

    monkeypatch.setattr(vc, "_summarize_site_expected", fake_summarize)

    out = vc.compute_sites_expected_today(
        _FakeDB(rows), [_site(1), _site(2)], {1: object()}
    )

    # Only the site with an active baseline is computed.
    assert set(out) == {1}
    assert set(captured) == {1}
    maps = captured[1]
    # Today's buckets attributed; yesterday's excluded; absent metric stays empty.
    assert maps[vc.SITE_POWER_METRIC] == {today_ts: 5.0}
    assert maps[vc.IRRADIANCE_METRIC] == {today_ts: 600.0}
    assert maps[vc.CELL_TEMPERATURE_METRIC] == {}


def test_compute_sites_expected_today_no_baselines_returns_empty():
    out = vc.compute_sites_expected_today(_FakeDB([]), [_site(1)], {})
    assert out == {}


# ---------------------------------------------------------------------------
# aggregate_company_actuals — full honest roll-up incl. loss
# ---------------------------------------------------------------------------
def _patch_actuals_seams(monkeypatch, *, latest_power, today_energy, baselines, expected):
    monkeypatch.setattr(vc, "get_sites_latest_power", lambda _db, _ids, **_k: latest_power)
    monkeypatch.setattr(vc, "get_sites_today_energy", lambda _db, _s, **_k: today_energy)
    monkeypatch.setattr(vc, "get_active_baselines", lambda _db, _ids: baselines)
    monkeypatch.setattr(
        vc, "compute_sites_expected_today", lambda _db, _s, _b, **_k: expected
    )


def test_aggregate_company_actuals_available_with_loss(monkeypatch):
    _patch_actuals_seams(
        monkeypatch,
        latest_power={1: 5.0, 2: 7.0},
        today_energy={1: 50.0, 2: 70.0},
        baselines={1: object(), 2: object()},
        expected={
            1: _exp(ExpectedState.available, energy=60.0, power=6.0),
            2: _exp(ExpectedState.available, energy=80.0, power=8.0),
        },
    )
    out = vc.aggregate_company_actuals(None, [_site(1), _site(2)])
    assert out["total_actual_kw"] == 12.0
    assert out["cumulative_actual_kw"] == 120.0
    assert out["total_expected_kw"] == 14.0
    assert out["cumulative_expected_kw"] == 140.0
    assert out["loss"] == 20.0  # 140 expected - 120 actual
    assert out["expected_baseline_available"] is True
    assert out["expected_state"] == ExpectedState.available.value
    assert out["sites_with_telemetry"] == 2
    assert out["per_site_actual_kw"] == {1: 5.0, 2: 7.0}


def test_aggregate_company_actuals_loss_floored_at_zero(monkeypatch):
    # Actual beats expected -> loss is a genuine 0.0 (not negative, not None).
    _patch_actuals_seams(
        monkeypatch,
        latest_power={1: 5.0},
        today_energy={1: 200.0},
        baselines={1: object()},
        expected={1: _exp(ExpectedState.available, energy=140.0, power=6.0)},
    )
    out = vc.aggregate_company_actuals(None, [_site(1)])
    assert out["loss"] == 0.0
    assert out["cumulative_expected_kw"] == 140.0


def test_aggregate_company_actuals_partial_nulls_expected_and_loss(monkeypatch):
    # Two telemetry sites, but site 2 has no baseline -> expected/loss are None
    # while actual stays fully visible.
    _patch_actuals_seams(
        monkeypatch,
        latest_power={1: 5.0, 2: 7.0},
        today_energy={1: 50.0, 2: 70.0},
        baselines={1: object()},
        expected={1: _exp(ExpectedState.available, energy=60.0, power=6.0)},
    )
    out = vc.aggregate_company_actuals(None, [_site(1), _site(2)])
    assert out["total_actual_kw"] == 12.0
    assert out["cumulative_actual_kw"] == 120.0
    assert out["total_expected_kw"] is None
    assert out["cumulative_expected_kw"] is None
    assert out["loss"] is None
    assert out["expected_baseline_available"] is False
    assert out["expected_state"] == ExpectedState.partial.value
    assert out["sites_with_telemetry"] == 2
    assert out["sites_with_active_baseline"] == 1
    assert out["sites_missing_baseline"] == 1
