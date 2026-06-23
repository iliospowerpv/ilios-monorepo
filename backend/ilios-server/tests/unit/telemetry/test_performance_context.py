"""Unit tests for the read-only V2 performance-context aggregator.

These exercise the *composition + data-display integrity contract* of
``build_performance_context`` at its pure-logic seams. Every DB/composition
dependency is monkeypatched (``_active_baseline``, ``_evaluate_active_baseline``,
``compute_site_expected_period_effective``, ``build_site_semantics_reconciliation``,
``compute_site_eligibility_diagnostics``, ``TelemetrySiteRollupCRUD``,
``TelemetryReadingCRUD``) so no database or rollup fixtures are required.

The honesty contract under test (data contract §2.2 / §3):

* ``0`` is a genuine measured zero (``no_production_during_interval``) — the only
  state allowed to render a 0;
* a negative tare is a real reading (``available``), preserved verbatim;
* a missing actual is ``telemetry_unavailable`` (fresh) or ``telemetry_stale``
  (site latest reading stale) or ``pre_pto`` (aligned expected bucket is pre-PTO);
* an expected value / variance is NEVER fabricated when an input is missing;
* weather semantics are projected VERBATIM and ``used_by_active_model`` is always
  ``False``.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

import app.services.telemetry.performance_context_service as svc
from app.schema.telemetry import TelemetryHealthStatus
from app.schema.weather import (
    WeatherSemanticsReconciliationResponse,
    WeatherSemanticsReconciliationRow,
)
from app.services.telemetry.expected_service import (
    BucketStatus,
    ExpectedBucket,
    ExpectedResult,
    ExpectedState,
    OverallStatus,
)

_T0 = datetime(2026, 6, 20, 0, 0, 0)


def _ts(hour: int) -> datetime:
    return _T0 + timedelta(hours=hour)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------
def _bucket(ts, status, *, exp_p=None, exp_e=None, irr=None, temp_f=None, baseline_id=7):
    return ExpectedBucket(
        bucket_start=ts,
        status=status,
        expected_power_kw=exp_p,
        expected_energy_kwh=exp_e,
        actual_power_kw=None,
        irradiance_wm2=irr,
        cell_temperature_f=temp_f,
        age_years=None,
        baseline_id=baseline_id,
    )


def _result(buckets, *, overall=OverallStatus.ok, baseline_id=7, selection_mode="active"):
    return ExpectedResult(
        overall_status=overall,
        baseline_id=baseline_id,
        baseline_type="weather_adjusted_model",
        bucket_size="1h",
        window_start=buckets[0].bucket_start if buckets else _T0,
        window_end=_T0 + timedelta(days=1),
        buckets=buckets,
        expected_energy_kwh=None,
        actual_energy_kwh=None,
        ok_bucket_count=sum(1 for b in buckets if b.status == BucketStatus.ok),
        missing_inputs_bucket_count=sum(
            1 for b in buckets if b.status == BucketStatus.missing_inputs
        ),
        pre_pto_bucket_count=sum(
            1 for b in buckets if b.status == BucketStatus.pre_pto
        ),
        baseline_selection_mode=selection_mode,
    )


class _RollupRow:
    def __init__(
        self, bucket_start, value, *, unit="kW", agg="avg", sample_count=12, completeness=1.0
    ):
        self.bucket_start = bucket_start
        self.value = value
        self.unit = unit
        self.agg = agg
        self.sample_count = sample_count
        self.completeness = completeness


def _fake_rollup_crud(rows_by_metric, latest_bucket=None):
    class _Fake:
        def __init__(self, _db):
            pass

        def get_series(self, *, site_id, normalized_metric, bucket_size, start, end):
            return rows_by_metric.get(normalized_metric, [])

        def latest_bucket_start(self, _site_id):
            return latest_bucket

    return _Fake


def _fake_reading_crud(latest_ts):
    class _Fake:
        def __init__(self, _db):
            pass

        def latest_metric_ts(self, _site_id):
            return latest_ts

    return _Fake


def _fake_health(latest_ts):
    """Build a fake telemetry-health verdict mirroring the real thresholds.

    Freshness in the aggregator is a verbatim PROJECTION of
    ``compute_site_telemetry_health``; tests patch that seam directly so the
    ``latest_reading`` they pass maps to the same fresh/stale/no_data outcome
    the real health computation would yield (<=120m → fresh, else stale, no
    reading → no_data).
    """
    if latest_ts is None:
        return SimpleNamespace(
            status=TelemetryHealthStatus.no_data,
            last_data_at=None,
            data_delay_minutes=None,
        )
    lt = latest_ts if latest_ts.tzinfo else latest_ts.replace(tzinfo=timezone.utc)
    delay = int((datetime.now(timezone.utc) - lt).total_seconds() / 60)
    if delay <= 30:
        status = TelemetryHealthStatus.healthy
    elif delay <= 120:
        status = TelemetryHealthStatus.warn
    else:
        status = TelemetryHealthStatus.error
    return SimpleNamespace(
        status=status, last_data_at=latest_ts, data_delay_minutes=delay
    )


def _fake_diagnostics(**overrides):
    base = dict(
        total_devices=5,
        mappable_count=4,
        mapped_count=3,
        unmapped_eligible_count=1,
        expected_driving_count=2,
        weather_source_count=1,
        weather_unknown_semantics_count=1,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def _wrow(
    device_id,
    *,
    state="observed_weather_device_no_governed_declaration",
    label="Observed weather device — no governed declaration",
    blocking="lowers_confidence",
    basis=None,
    eligible=False,
    plane=None,
    temp_type=None,
    mapping_id=None,
):
    return WeatherSemanticsReconciliationRow(
        device_id=device_id,
        reconciliation_state=state,
        state_label=label,
        state_explanation="explanation",
        blocking_level=blocking,
        source_state=state,
        declaration_basis=basis,
        expected_model_eligible=eligible,
        irradiance_plane=plane,
        temperature_type=temp_type,
        mapping_id=mapping_id,
    )


def _fake_recon(rows):
    return WeatherSemanticsReconciliationResponse(
        site_id=1,
        generated_at=_T0,
        total_weather_capable_devices=len(rows),
        has_weather_source=bool(rows),
        has_active_weather_profile=False,
        eligible_count=sum(1 for r in rows if r.expected_model_eligible),
        needs_re_review_count=0,
        devices=rows,
    )


def _site(timezone="UTC"):
    return SimpleNamespace(id=1, timezone=timezone)


def _patch(
    monkeypatch,
    *,
    active=None,
    is_blocking=False,
    report=None,
    result=None,
    power_rows=None,
    irr_rows=None,
    temp_rows=None,
    latest_reading=None,
    latest_bucket=None,
    recon_rows=None,
    diagnostics=None,
):
    monkeypatch.setattr(svc, "_active_baseline", lambda *_a, **_k: active)
    monkeypatch.setattr(
        svc, "_evaluate_active_baseline", lambda *_a, **_k: (is_blocking, report)
    )
    monkeypatch.setattr(
        svc, "compute_site_expected_period_effective", lambda *_a, **_k: result
    )
    monkeypatch.setattr(
        svc,
        "compute_site_eligibility_diagnostics",
        lambda *_a, **_k: diagnostics if diagnostics is not None else _fake_diagnostics(),
    )
    monkeypatch.setattr(
        svc,
        "build_site_semantics_reconciliation",
        lambda *_a, **_k: _fake_recon(recon_rows if recon_rows is not None else []),
    )
    monkeypatch.setattr(
        svc,
        "TelemetrySiteRollupCRUD",
        _fake_rollup_crud(
            {
                svc.SITE_POWER_METRIC: power_rows or [],
                svc.IRRADIANCE_METRIC: irr_rows or [],
                svc.CELL_TEMPERATURE_METRIC: temp_rows or [],
            },
            latest_bucket=latest_bucket,
        ),
    )
    monkeypatch.setattr(
        svc, "TelemetryReadingCRUD", _fake_reading_crud(latest_reading)
    )
    monkeypatch.setattr(
        svc, "compute_site_telemetry_health", lambda *_a, **_k: _fake_health(latest_reading)
    )


def _build(site=None, *, window_end=None, **kwargs):
    """Build the context over a window. Defaults to a SINGLE bucket [_T0, _T0].

    ``expected_bucket_starts`` is end-INCLUSIVE, so the canonical per-bucket
    axis spans every epoch-anchored bucket in ``[window_start, window_end]``.
    Multi-bucket tests pass ``window_end`` explicitly (e.g. ``_ts(1)`` → two
    buckets) so the axis matches their fixtures exactly.
    """
    return svc.build_performance_context(
        db=None,
        site=site or _site(),
        window_start=_T0,
        window_end=window_end if window_end is not None else _T0,
        bucket_size="1h",
        temp_unit=kwargs.pop("temp_unit", "F"),
    )


# ---------------------------------------------------------------------------
# 0-vs-null integrity
# ---------------------------------------------------------------------------
def test_measured_zero_is_no_production_not_unavailable(monkeypatch):
    buckets = [_bucket(_ts(0), BucketStatus.ok, exp_p=10.0, exp_e=10.0)]
    _patch(
        monkeypatch,
        active=SimpleNamespace(id=7, baseline_type="weather_adjusted_model"),
        result=_result(buckets),
        power_rows=[_RollupRow(_ts(0), 0.0)],
        latest_reading=datetime.utcnow(),
    )
    resp = _build()
    pt = resp.series[0]
    assert pt.actual_kw == 0.0
    assert pt.actual_kwh == 0.0
    assert pt.actual_state == "no_production_during_interval"


def test_missing_actual_is_unavailable_never_zero(monkeypatch):
    buckets = [_bucket(_ts(0), BucketStatus.ok, exp_p=10.0, exp_e=10.0)]
    _patch(
        monkeypatch,
        active=SimpleNamespace(id=7, baseline_type="weather_adjusted_model"),
        result=_result(buckets),
        power_rows=[],  # no actual row for this bucket
        latest_reading=datetime.utcnow(),
    )
    resp = _build()
    pt = resp.series[0]
    assert pt.actual_kw is None
    assert pt.actual_kwh is None
    assert pt.actual_state == "telemetry_unavailable"
    # expected is real, never coerced to 0
    assert pt.expected_kw == 10.0
    assert pt.expected_kwh == 10.0
    # variance only when BOTH present -> here actual missing -> null, not 0
    assert pt.variance_kwh is None
    assert pt.variance_pct is None


def test_negative_tare_preserved_as_available(monkeypatch):
    buckets = [_bucket(_ts(0), BucketStatus.ok, exp_p=10.0, exp_e=10.0)]
    _patch(
        monkeypatch,
        active=SimpleNamespace(id=7, baseline_type="weather_adjusted_model"),
        result=_result(buckets),
        power_rows=[_RollupRow(_ts(0), -2.5)],
        latest_reading=datetime.utcnow(),
    )
    resp = _build()
    pt = resp.series[0]
    assert pt.actual_kw == -2.5
    assert pt.actual_kwh == -2.5
    assert pt.actual_state == "available"
    assert pt.variance_kwh == pytest.approx(-12.5)


def test_stale_freshness_makes_missing_actual_stale(monkeypatch):
    buckets = [_bucket(_ts(0), BucketStatus.ok, exp_p=10.0, exp_e=10.0)]
    _patch(
        monkeypatch,
        active=SimpleNamespace(id=7, baseline_type="weather_adjusted_model"),
        result=_result(buckets),
        power_rows=[],
        latest_reading=datetime.utcnow() - timedelta(hours=5),
    )
    resp = _build()
    assert resp.series[0].actual_state == "telemetry_stale"
    assert resp.telemetry_quality.freshness_state == "stale"


# ---------------------------------------------------------------------------
# Expected / baseline states (never fabricated)
# ---------------------------------------------------------------------------
def test_missing_inputs_bucket_keeps_expected_null(monkeypatch):
    buckets = [_bucket(_ts(0), BucketStatus.missing_inputs)]
    _patch(
        monkeypatch,
        active=SimpleNamespace(id=7, baseline_type="weather_adjusted_model"),
        result=_result(buckets, overall=OverallStatus.ok),
        power_rows=[_RollupRow(_ts(0), 5.0)],
        latest_reading=datetime.utcnow(),
    )
    resp = _build()
    pt = resp.series[0]
    assert pt.expected_kw is None
    assert pt.expected_kwh is None
    assert pt.expected_state == "missing_inputs"
    assert pt.variance_kwh is None  # no expected -> no fabricated variance


def test_pre_pto_bucket_marks_actual_pre_pto_when_missing(monkeypatch):
    buckets = [_bucket(_ts(0), BucketStatus.pre_pto)]
    _patch(
        monkeypatch,
        active=SimpleNamespace(id=7, baseline_type="weather_adjusted_model"),
        result=_result(buckets, overall=OverallStatus.ok),
        power_rows=[],
        latest_reading=datetime.utcnow(),
    )
    resp = _build()
    pt = resp.series[0]
    assert pt.expected_state == "pre_pto"
    assert pt.actual_state == "pre_pto"


def test_invalid_active_baseline_suppresses_expected(monkeypatch):
    active = SimpleNamespace(id=3, baseline_type="weather_adjusted_model")
    report = SimpleNamespace(
        is_blocking=True, summary={"reason": "bad"}, policy_version="v1"
    )
    _patch(
        monkeypatch,
        active=active,
        is_blocking=True,
        report=report,
        result=None,  # period-effective never called when invalid
        power_rows=[_RollupRow(_ts(0), 5.0)],
        latest_reading=datetime.utcnow(),
    )
    resp = _build()
    assert resp.baseline_status.baseline_invalid is True
    assert resp.baseline_status.invalid_baseline_id == 3
    assert resp.baseline_status.expected_state == "baseline_invalid"
    assert resp.baseline_status.expected_baseline_available is False
    pt = resp.series[0]
    assert pt.actual_kw == 5.0  # actuals stay visible
    assert pt.expected_kw is None  # expected suppressed, never fabricated
    assert pt.expected_state == "baseline_invalid"


def test_no_active_baseline_is_not_available(monkeypatch):
    _patch(
        monkeypatch,
        active=None,
        result=None,
        power_rows=[_RollupRow(_ts(0), 5.0)],
        latest_reading=datetime.utcnow(),
    )
    resp = _build()
    assert resp.baseline_status.expected_baseline_available is False
    assert resp.baseline_status.expected_state == "baseline_not_available"
    assert resp.series[0].expected_state == "baseline_not_available"


# ---------------------------------------------------------------------------
# Weather semantics (verbatim, never re-derived)
# ---------------------------------------------------------------------------
def test_weather_semantics_projected_verbatim(monkeypatch):
    rows = [
        _wrow(20, blocking="lowers_confidence"),
        _wrow(
            10,
            state="declared_poa_irradiance",
            label="POA declared",
            blocking="informational",
            basis="manufacturer_spec",
            eligible=True,
            plane="poa",
            temp_type="cell",
            mapping_id=88,
        ),
    ]
    _patch(
        monkeypatch,
        active=SimpleNamespace(id=7, baseline_type="weather_adjusted_model"),
        result=_result([_bucket(_ts(0), BucketStatus.ok, exp_p=1.0, exp_e=1.0)]),
        power_rows=[_RollupRow(_ts(0), 1.0)],
        irr_rows=[_RollupRow(_ts(0), 600.0, unit="W/m2")],
        latest_reading=datetime.utcnow(),
        recon_rows=rows,
    )
    resp = _build()
    ws = resp.weather_semantics
    # headline = most severe (lowers_confidence) then lowest device_id
    assert ws.headline_state == "observed_weather_device_no_governed_declaration"
    assert ws.blocking_level == "lowers_confidence"
    # irradiance/temperature blocks pick the row that actually declares them
    assert ws.irradiance.plane == "poa"
    assert ws.temperature.type == "cell"
    assert ws.irradiance.expected_model_eligible is True
    # never claims to drive the model
    assert ws.irradiance.used_by_active_model is False
    assert ws.temperature.used_by_active_model is False
    # full reconciliation embedded verbatim
    assert resp.weather_semantics.reconciliation is not None
    assert len(resp.weather_semantics.reconciliation.devices) == 2
    # the governed mapping id backing the weather labels is carried verbatim into
    # the per-bucket provenance ONLY for a bucket that has an observed value
    assert resp.series[0].source_provenance.weather_declaration_mapping_id == 88
    # there is no per-bucket weather-source linkage in telemetry rollups -> null
    assert resp.series[0].source_provenance.irradiance_source_id is None
    assert resp.series[0].source_provenance.temperature_source_id is None


def test_window_object_and_site_timezone_in_envelope(monkeypatch):
    """The canonical envelope carries a top-level ``site_timezone`` (IANA) and a
    ``window`` object {start,end,tz_note}; the flat bounds stay additively."""
    _patch(
        monkeypatch,
        active=SimpleNamespace(id=7, baseline_type="weather_adjusted_model"),
        result=_result([_bucket(_ts(0), BucketStatus.ok, exp_p=1.0, exp_e=1.0)]),
        power_rows=[_RollupRow(_ts(0), 1.0)],
        latest_reading=datetime.utcnow(),
    )
    resp = _build(site=_site(timezone="America/New_York"), window_end=_ts(1))
    assert resp.site_timezone == "America/New_York"
    assert resp.window.start == _T0
    assert resp.window.end == _ts(1)
    assert "naive-UTC" in resp.window.tz_note
    # flat bounds retained additively and must agree with the window object
    assert resp.window_start == resp.window.start
    assert resp.window_end == resp.window.end


def test_site_timezone_falls_back_to_utc(monkeypatch):
    """A site with no timezone falls back to UTC (never null/blank)."""
    _patch(
        monkeypatch,
        active=SimpleNamespace(id=7, baseline_type="weather_adjusted_model"),
        result=_result([_bucket(_ts(0), BucketStatus.ok, exp_p=1.0, exp_e=1.0)]),
        power_rows=[_RollupRow(_ts(0), 1.0)],
        latest_reading=datetime.utcnow(),
    )
    resp = _build(site=SimpleNamespace(id=1, timezone=None))
    assert resp.site_timezone == "UTC"


def test_weather_mapping_id_null_when_no_observed_weather(monkeypatch):
    """The governed mapping id is attached per-bucket ONLY when that bucket has an
    observed weather value; a bucket with no irradiance/temperature stays null."""
    _patch(
        monkeypatch,
        active=SimpleNamespace(id=7, baseline_type="weather_adjusted_model"),
        result=_result([_bucket(_ts(0), BucketStatus.ok, exp_p=1.0, exp_e=1.0)]),
        power_rows=[_RollupRow(_ts(0), 1.0)],
        latest_reading=datetime.utcnow(),
        recon_rows=[_wrow(10, plane="poa", mapping_id=88)],
    )
    resp = _build()
    assert resp.series[0].source_provenance.weather_declaration_mapping_id is None


def test_observed_weather_no_declaration_headline(monkeypatch):
    """Mirrors the protected Site-4 shape: an observed weather device with no
    governed declaration surfaces that state verbatim."""
    _patch(
        monkeypatch,
        active=SimpleNamespace(id=7, baseline_type="weather_adjusted_model"),
        result=_result([_bucket(_ts(0), BucketStatus.ok, exp_p=1.0, exp_e=1.0)]),
        power_rows=[_RollupRow(_ts(0), 1.0)],
        latest_reading=datetime.utcnow(),
        recon_rows=[_wrow(42)],
    )
    resp = _build()
    assert (
        resp.weather_semantics.headline_state
        == "observed_weather_device_no_governed_declaration"
    )


# ---------------------------------------------------------------------------
# Temperature conversion (display only, null-safe)
# ---------------------------------------------------------------------------
def test_temperature_celsius_conversion(monkeypatch):
    _patch(
        monkeypatch,
        active=SimpleNamespace(id=7, baseline_type="weather_adjusted_model"),
        result=_result([_bucket(_ts(0), BucketStatus.ok, exp_p=1.0, exp_e=1.0)]),
        power_rows=[_RollupRow(_ts(0), 1.0)],
        temp_rows=[_RollupRow(_ts(0), 50.0, unit="F")],  # 50F == 10C
        latest_reading=datetime.utcnow(),
    )
    resp = _build(temp_unit="C")
    assert resp.series[0].temperature == pytest.approx(10.0)
    assert resp.temp_unit == "C"


def test_temperature_default_fahrenheit_passthrough(monkeypatch):
    _patch(
        monkeypatch,
        active=SimpleNamespace(id=7, baseline_type="weather_adjusted_model"),
        result=_result([_bucket(_ts(0), BucketStatus.ok, exp_p=1.0, exp_e=1.0)]),
        power_rows=[_RollupRow(_ts(0), 1.0)],
        temp_rows=[_RollupRow(_ts(0), 68.0, unit="F")],
        latest_reading=datetime.utcnow(),
    )
    resp = _build(temp_unit="F")
    assert resp.series[0].temperature == pytest.approx(68.0)


def test_missing_temperature_stays_null(monkeypatch):
    _patch(
        monkeypatch,
        active=SimpleNamespace(id=7, baseline_type="weather_adjusted_model"),
        result=_result([_bucket(_ts(0), BucketStatus.ok, exp_p=1.0, exp_e=1.0)]),
        power_rows=[_RollupRow(_ts(0), 1.0)],
        temp_rows=[],
        latest_reading=datetime.utcnow(),
    )
    resp = _build(temp_unit="C")
    assert resp.series[0].temperature is None


# ---------------------------------------------------------------------------
# Summary + telemetry-quality composition
# ---------------------------------------------------------------------------
def test_summary_variance_over_comparable_subset(monkeypatch):
    buckets = [
        _bucket(_ts(0), BucketStatus.ok, exp_p=10.0, exp_e=10.0),
        _bucket(_ts(1), BucketStatus.ok, exp_p=20.0, exp_e=20.0),
    ]
    _patch(
        monkeypatch,
        active=SimpleNamespace(id=7, baseline_type="weather_adjusted_model"),
        result=_result(buckets),
        power_rows=[_RollupRow(_ts(0), 8.0), _RollupRow(_ts(1), 18.0)],
        latest_reading=datetime.utcnow(),
    )
    resp = _build(window_end=_ts(1))
    assert resp.summary.bucket_count == 2
    assert resp.summary.total_actual_kwh == pytest.approx(26.0)
    assert resp.summary.total_expected_kwh == pytest.approx(30.0)
    assert resp.summary.variance_kwh == pytest.approx(-4.0)
    assert resp.summary.actual_state == "available"
    assert resp.summary.expected_state == "available"


def test_summary_partial_actual_state(monkeypatch):
    buckets = [
        _bucket(_ts(0), BucketStatus.ok, exp_p=10.0, exp_e=10.0),
        _bucket(_ts(1), BucketStatus.ok, exp_p=20.0, exp_e=20.0),
    ]
    _patch(
        monkeypatch,
        active=SimpleNamespace(id=7, baseline_type="weather_adjusted_model"),
        result=_result(buckets),
        power_rows=[_RollupRow(_ts(0), 8.0)],  # only one of two buckets
        latest_reading=datetime.utcnow(),
    )
    resp = _build(window_end=_ts(1))
    assert resp.summary.actual_state == "partial"


def test_telemetry_quality_counts_verbatim(monkeypatch):
    _patch(
        monkeypatch,
        active=SimpleNamespace(id=7, baseline_type="weather_adjusted_model"),
        result=_result([_bucket(_ts(0), BucketStatus.ok, exp_p=1.0, exp_e=1.0)]),
        power_rows=[_RollupRow(_ts(0), 1.0)],
        latest_reading=datetime.utcnow(),
        latest_bucket=_ts(0),
        diagnostics=_fake_diagnostics(total_devices=9, expected_driving_count=4),
    )
    resp = _build()
    tq = resp.telemetry_quality
    assert tq.total_devices == 9
    assert tq.expected_driving_count == 4
    assert tq.freshness_state == "fresh"
    assert tq.latest_bucket_start == _ts(0)


def test_no_data_freshness_when_no_reading(monkeypatch):
    _patch(
        monkeypatch,
        active=None,
        result=None,
        power_rows=[],
        latest_reading=None,
    )
    resp = _build()
    assert resp.telemetry_quality.freshness_state == "no_data"
    assert resp.telemetry_quality.data_delay_minutes is None
    assert resp.summary.actual_state == "telemetry_unavailable"


def test_full_axis_emits_point_for_every_bucket(monkeypatch):
    """The per-bucket axis is the full epoch-anchored grid over the window, not
    the union of present timestamps: a bucket with no row still gets a point
    (null actual + honest state), never silently dropped."""
    buckets = [_bucket(_ts(0), BucketStatus.ok, exp_p=10.0, exp_e=10.0)]
    _patch(
        monkeypatch,
        active=SimpleNamespace(id=7, baseline_type="weather_adjusted_model"),
        result=_result(buckets),
        power_rows=[_RollupRow(_ts(0), 5.0)],  # only the first of 3 buckets
        latest_reading=datetime.utcnow(),
    )
    resp = _build(window_end=_ts(2))  # buckets ts0, ts1, ts2
    assert [p.bucket_start for p in resp.series] == [_ts(0), _ts(1), _ts(2)]
    # present bucket
    assert resp.series[0].actual_kw == 5.0
    # missing buckets surface as null + unavailable, never 0
    assert resp.series[1].actual_kw is None
    assert resp.series[1].actual_state == "telemetry_unavailable"
    assert resp.series[2].actual_kw is None


def test_provenance_is_null_when_no_producing_row(monkeypatch):
    """Provenance is copied verbatim from the rows that produced each value; a
    field stays null when no producing row exists (never fabricated)."""
    buckets = [_bucket(_ts(0), BucketStatus.ok, exp_p=10.0, exp_e=10.0)]
    _patch(
        monkeypatch,
        active=SimpleNamespace(id=7, baseline_type="weather_adjusted_model"),
        result=_result(buckets),
        power_rows=[_RollupRow(_ts(0), 5.0)],
        latest_reading=datetime.utcnow(),
    )
    resp = _build(window_end=_ts(1))  # ts0 has power, ts1 has nothing
    prov0 = resp.series[0].source_provenance
    assert prov0.actual_metric == svc.SITE_POWER_METRIC
    assert prov0.actual_unit == "kW"
    # no observed irradiance/temperature row -> metric provenance is null
    assert prov0.irradiance_metric is None
    assert prov0.temperature_metric is None
    prov1 = resp.series[1].source_provenance
    assert prov1.actual_metric is None
    assert prov1.actual_unit is None
    assert prov1.actual_agg is None


def test_zero_writes_no_commit_on_session(monkeypatch):
    """The aggregator must never write/commit. We pass a session spy and assert
    no mutating method is ever touched."""

    class _SessionSpy:
        def __init__(self):
            self.touched = []

        def __getattr__(self, name):
            if name in {"add", "commit", "flush", "delete", "execute", "merge"}:
                self.touched.append(name)
            raise AttributeError(name)

    spy = _SessionSpy()
    _patch(
        monkeypatch,
        active=SimpleNamespace(id=7, baseline_type="weather_adjusted_model"),
        result=_result([_bucket(_ts(0), BucketStatus.ok, exp_p=1.0, exp_e=1.0)]),
        power_rows=[_RollupRow(_ts(0), 1.0)],
        latest_reading=datetime.utcnow(),
    )
    svc.build_performance_context(
        db=spy,
        site=_site(),
        window_start=_T0,
        window_end=_T0 + timedelta(hours=4),
        bucket_size="1h",
        temp_unit="F",
    )
    assert spy.touched == []
