"""Period-Effective Baseline Selection for historical expected values.

These guard the read-only, additive sprint that makes a HISTORICAL V2 expected
bucket use the baseline that was ACTIVE during that bucket's period (via
``active_from``/``active_to``/``supersedes_baseline_id``), not always the current
active baseline. Coverage:

* the CRUD window selector (real DB): overlap math, status/type exclusions, NULL
  ``active_from`` legacy open-start, and ascending order;
* the pure ``_effective_baseline_at`` ownership rule (boundary -> new baseline);
* the stitching orchestrator (monkeypatched calc seam): none/single/spanning,
  no boundary double-count, per-bucket ``baseline_id``, honest null vs genuine 0,
  and a pre-baseline gap left absent (never fabricated);
* the chart builders keeping actuals visible across an uncovered gap while the
  expected stays ``None`` and the state honestly downgrades to ``partial``.

The calc core itself (``compute_site_expected``) is monkeypatched so these stay
fast and deterministic — the physics is exercised by ``expected_calc_test`` and
``test_v2_expected_wiring``; here we only verify SELECTION + STITCHING.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

import app.helpers.telemetry.v2_chart_data as v2
import app.services.telemetry.expected_service as svc
from app.models.telemetry_expected import (
    TelemetryBaselineStatus,
    TelemetryBaselineType,
    TelemetryExpectedBaseline,
)
from app.services.telemetry.expected_service import (
    BucketStatus,
    ExpectedBucket,
    ExpectedResult,
    ExpectedState,
    OverallStatus,
    _effective_baseline_at,
    compute_site_expected_period_effective,
)

WAM = TelemetryBaselineType.weather_adjusted_model
DESIGN = TelemetryBaselineType.design_estimate


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------
def _fake_baseline(baseline_id, active_from, active_to):
    """A stand-in baseline the orchestrator reads (id/active_from/active_to)."""
    return SimpleNamespace(
        id=baseline_id, active_from=active_from, active_to=active_to
    )


def _make_fake_compute(specs):
    """Build a ``compute_site_expected`` replacement.

    ``specs`` maps ``baseline_id -> {ts: (status, exp_p, exp_e, act)}``. The fake
    emits one bucket per hour in the (inclusive) clipped window for which a spec
    exists, stamping ``baseline_id`` exactly as the real DB wrapper does — so the
    inclusive ``get_series`` boundary bucket is produced by BOTH neighbouring
    segments and the orchestrator's dedupe is genuinely exercised.
    """

    def _fake(db, *, site, baseline, start, end, bucket_size="1h", weather_resolver=None):
        buckets = []
        ts = start
        per_baseline = specs.get(baseline.id, {})
        while ts <= end:
            spec = per_baseline.get(ts)
            if spec is not None:
                status, exp_p, exp_e, act = spec
                buckets.append(
                    ExpectedBucket(
                        bucket_start=ts,
                        status=status,
                        expected_power_kw=exp_p,
                        expected_energy_kwh=exp_e,
                        actual_power_kw=act,
                        irradiance_wm2=None,
                        cell_temperature_f=None,
                        age_years=None,
                        baseline_id=baseline.id,
                    )
                )
            ts += timedelta(hours=1)
        ok = [b for b in buckets if b.status == BucketStatus.ok]
        return ExpectedResult(
            overall_status=OverallStatus.ok,
            baseline_id=baseline.id,
            baseline_type="weather_adjusted_model",
            bucket_size=bucket_size,
            window_start=start,
            window_end=end,
            buckets=buckets,
            expected_energy_kwh=(sum(b.expected_energy_kwh for b in ok) if ok else None),
            actual_energy_kwh=None,
            ok_bucket_count=len(ok),
            missing_inputs_bucket_count=sum(
                1 for b in buckets if b.status == BucketStatus.missing_inputs
            ),
            pre_pto_bucket_count=sum(
                1 for b in buckets if b.status == BucketStatus.pre_pto
            ),
        )

    return _fake


def _patch_orchestrator(monkeypatch, baselines, specs):
    """Patch the CRUD selector + calc seam the orchestrator depends on."""

    class _FakeCRUD:
        def __init__(self, _db):
            pass

        def get_baselines_effective_in_window(self, *_a, **_k):
            return baselines

    monkeypatch.setattr(svc, "TelemetryExpectedBaselineCRUD", _FakeCRUD)
    monkeypatch.setattr(svc, "compute_site_expected", _make_fake_compute(specs))


def _run(start, end):
    return compute_site_expected_period_effective(
        None, site=SimpleNamespace(id=1, timezone="UTC"), start=start, end=end
    )


# ===========================================================================
# _effective_baseline_at — ownership rule
# ===========================================================================
class TestEffectiveBaselineAt:
    def test_boundary_belongs_to_new_baseline(self):
        t2 = datetime(2026, 6, 10)
        old = _fake_baseline(1, datetime(2026, 6, 1), t2)  # [Jun1, Jun10)
        new = _fake_baseline(2, t2, None)  # [Jun10, inf)
        baselines = [old, new]
        # Just before the boundary -> old; exactly at / after -> new.
        assert _effective_baseline_at(baselines, t2 - timedelta(hours=1)).id == 1
        assert _effective_baseline_at(baselines, t2).id == 2
        assert _effective_baseline_at(baselines, t2 + timedelta(hours=1)).id == 2

    def test_before_earliest_active_from_is_none(self):
        b = _fake_baseline(1, datetime(2026, 6, 5), None)
        assert _effective_baseline_at([b], datetime(2026, 6, 4)) is None

    def test_null_active_from_is_open_start_but_loses_to_stamped(self):
        legacy = _fake_baseline(1, None, None)  # open-start legacy
        stamped = _fake_baseline(2, datetime(2026, 6, 5), None)
        baselines = [legacy, stamped]
        # Before the stamped row only legacy covers it.
        assert _effective_baseline_at(baselines, datetime(2026, 6, 1)).id == 1
        # Where both cover, the precisely-stamped row wins (latest active_from).
        assert _effective_baseline_at(baselines, datetime(2026, 6, 10)).id == 2


# ===========================================================================
# CRUD get_baselines_effective_in_window — real DB
# ===========================================================================
class TestWindowSelector:
    def _mk(
        self,
        db_session,
        company_id,
        site_id,
        *,
        status,
        active_from,
        active_to,
        baseline_type=WAM,
        name="b",
    ):
        row = TelemetryExpectedBaseline(
            company_id=company_id,
            site_id=site_id,
            baseline_name=name,
            baseline_type=baseline_type,
            status=status,
            active_from=active_from,
            active_to=active_to,
        )
        db_session.add(row)
        db_session.commit()
        db_session.refresh(row)
        self._created.append(row.id)
        return row

    @pytest.fixture(autouse=True)
    def _cleanup(self, db_session):
        self._created: list[int] = []
        yield
        if self._created:
            db_session.query(TelemetryExpectedBaseline).filter(
                TelemetryExpectedBaseline.id.in_(self._created)
            ).delete(synchronize_session=False)
            db_session.commit()

    def test_overlap_and_ordering(self, db_session, company_id, site_id):
        from app.crud.telemetry_expected import TelemetryExpectedBaselineCRUD

        # Superseded [Jun1, Jun10), active [Jun10, inf).
        old = self._mk(
            db_session,
            company_id,
            site_id,
            status=TelemetryBaselineStatus.superseded,
            active_from=datetime(2026, 6, 1),
            active_to=datetime(2026, 6, 10),
        )
        new = self._mk(
            db_session,
            company_id,
            site_id,
            status=TelemetryBaselineStatus.active,
            active_from=datetime(2026, 6, 10),
            active_to=None,
        )
        crud = TelemetryExpectedBaselineCRUD(db_session)
        # Window spanning both -> both, ascending by active_from.
        rows = crud.get_baselines_effective_in_window(
            site_id, datetime(2026, 6, 5), datetime(2026, 6, 15)
        )
        assert [r.id for r in rows] == [old.id, new.id]

    def test_excludes_non_overlapping(self, db_session, company_id, site_id):
        from app.crud.telemetry_expected import TelemetryExpectedBaselineCRUD

        old = self._mk(
            db_session,
            company_id,
            site_id,
            status=TelemetryBaselineStatus.superseded,
            active_from=datetime(2026, 6, 1),
            active_to=datetime(2026, 6, 10),
        )
        crud = TelemetryExpectedBaselineCRUD(db_session)
        # Window entirely AFTER the superseded period (active_to <= start) -> excluded.
        rows = crud.get_baselines_effective_in_window(
            site_id, datetime(2026, 6, 10), datetime(2026, 6, 15)
        )
        assert old.id not in [r.id for r in rows]

    def test_excludes_draft_and_other_types(self, db_session, company_id, site_id):
        from app.crud.telemetry_expected import TelemetryExpectedBaselineCRUD

        draft = self._mk(
            db_session,
            company_id,
            site_id,
            status=TelemetryBaselineStatus.draft,
            active_from=None,
            active_to=None,
        )
        design = self._mk(
            db_session,
            company_id,
            site_id,
            status=TelemetryBaselineStatus.active,
            active_from=datetime(2026, 6, 1),
            active_to=None,
            baseline_type=DESIGN,
            name="design",
        )
        crud = TelemetryExpectedBaselineCRUD(db_session)
        rows = crud.get_baselines_effective_in_window(
            site_id, datetime(2026, 6, 1), datetime(2026, 6, 15)
        )
        got = {r.id for r in rows}
        assert draft.id not in got  # draft never drives expected
        assert design.id not in got  # other baseline_type filtered out

    def test_null_active_from_is_included(self, db_session, company_id, site_id):
        from app.crud.telemetry_expected import TelemetryExpectedBaselineCRUD

        legacy = self._mk(
            db_session,
            company_id,
            site_id,
            status=TelemetryBaselineStatus.active,
            active_from=None,
            active_to=None,
        )
        crud = TelemetryExpectedBaselineCRUD(db_session)
        rows = crud.get_baselines_effective_in_window(
            site_id, datetime(2026, 6, 1), datetime(2026, 6, 15)
        )
        assert legacy.id in [r.id for r in rows]

    def test_null_active_from_sorts_first(self, db_session, company_id, site_id):
        from app.crud.telemetry_expected import TelemetryExpectedBaselineCRUD

        # A legacy open-start row (NULL active_from) and a stamped one; the open
        # start must order first so the caller walks the chain from -inf forward.
        legacy = self._mk(
            db_session,
            company_id,
            site_id,
            status=TelemetryBaselineStatus.superseded,
            active_from=None,
            active_to=datetime(2026, 6, 5),
            name="legacy",
        )
        stamped = self._mk(
            db_session,
            company_id,
            site_id,
            status=TelemetryBaselineStatus.active,
            active_from=datetime(2026, 6, 5),
            active_to=None,
            name="stamped",
        )
        crud = TelemetryExpectedBaselineCRUD(db_session)
        rows = crud.get_baselines_effective_in_window(
            site_id, datetime(2026, 6, 1), datetime(2026, 6, 15)
        )
        assert [r.id for r in rows] == [legacy.id, stamped.id]


# ===========================================================================
# Orchestrator — stitching, dedupe, honesty
# ===========================================================================
class TestOrchestrator:
    def test_no_baseline_is_baseline_not_available(self, monkeypatch):
        _patch_orchestrator(monkeypatch, [], {})
        out = _run(datetime(2026, 6, 1), datetime(2026, 6, 2))
        assert out.overall_status == OverallStatus.baseline_not_available
        assert out.buckets == []
        assert out.baseline_selection_mode == "period_effective"
        assert out.baseline_segments == []
        assert out.baseline_id is None

    def test_single_baseline_window(self, monkeypatch):
        b = _fake_baseline(7, datetime(2026, 6, 1), None)
        specs = {
            7: {
                datetime(2026, 6, 10, 10): (BucketStatus.ok, 8.0, 8.0, 7.0),
                datetime(2026, 6, 10, 11): (BucketStatus.ok, 9.0, 9.0, 8.0),
            }
        }
        _patch_orchestrator(monkeypatch, [b], specs)
        out = _run(datetime(2026, 6, 10, 10), datetime(2026, 6, 10, 11))
        assert [bk.baseline_id for bk in out.buckets] == [7, 7]
        assert out.baseline_id == 7  # single distinct baseline
        assert out.baseline_selection_mode == "period_effective"
        assert len(out.baseline_segments) == 1
        assert out.expected_energy_kwh == 17.0

    def test_spanning_two_baselines_no_boundary_double_count(self, monkeypatch):
        t0 = datetime(2026, 6, 10, 9)
        t1 = datetime(2026, 6, 10, 10)
        t2 = datetime(2026, 6, 10, 11)  # supersede boundary
        t3 = datetime(2026, 6, 10, 12)
        old = _fake_baseline(1, datetime(2026, 6, 1), t2)  # [.., t2)
        new = _fake_baseline(2, t2, None)  # [t2, ..)
        # BOTH segments can emit the boundary bucket t2 (inclusive get_series).
        specs = {
            1: {
                t0: (BucketStatus.ok, 5.0, 5.0, 4.0),
                t1: (BucketStatus.ok, 6.0, 6.0, 5.0),
                t2: (BucketStatus.ok, 7.0, 7.0, 6.0),  # boundary from OLD
            },
            2: {
                t2: (BucketStatus.ok, 70.0, 70.0, 6.0),  # boundary from NEW
                t3: (BucketStatus.ok, 8.0, 8.0, 7.0),
            },
        }
        _patch_orchestrator(monkeypatch, [old, new], specs)
        out = _run(t0, t3)
        by_ts = {bk.bucket_start: bk for bk in out.buckets}
        # t2 appears exactly once, owned by the NEW baseline.
        assert list(by_ts) == [t0, t1, t2, t3]
        assert by_ts[t2].baseline_id == 2
        assert by_ts[t2].expected_power_kw == 70.0  # new baseline's value, not old's
        assert by_ts[t0].baseline_id == 1
        assert by_ts[t3].baseline_id == 2
        assert out.baseline_id is None  # multiple distinct baselines
        assert {s.baseline_id for s in out.baseline_segments} == {1, 2}

    def test_gap_before_earliest_baseline_is_absent(self, monkeypatch):
        # Baseline only active from t1; t0 (before it) has no covering baseline.
        t0 = datetime(2026, 6, 10, 9)
        t1 = datetime(2026, 6, 10, 10)
        b = _fake_baseline(3, t1, None)
        specs = {3: {t1: (BucketStatus.ok, 6.0, 6.0, 5.0)}}
        _patch_orchestrator(monkeypatch, [b], specs)
        out = _run(t0, t1)
        # Only the covered bucket is present; the pre-baseline hour is absent
        # (the chart layer renders it as an honest gap, never fabricated here).
        assert [bk.bucket_start for bk in out.buckets] == [t1]

    def test_genuine_zero_preserved(self, monkeypatch):
        b = _fake_baseline(9, datetime(2026, 6, 1), None)
        ts = datetime(2026, 6, 10, 10)
        # ok bucket with real expected but zero actual -> genuine 0, not null.
        specs = {9: {ts: (BucketStatus.ok, 8.0, 8.0, 0.0)}}
        _patch_orchestrator(monkeypatch, [b], specs)
        out = _run(ts, ts)
        assert out.buckets[0].actual_power_kw == 0.0
        assert out.buckets[0].expected_power_kw == 8.0
        assert out.ok_bucket_count == 1


# ===========================================================================
# Chart builders — actuals stay visible across an uncovered gap
# ===========================================================================
class TestChartGapHandling:
    def test_actual_vs_expected_keeps_actuals_across_gap(self, monkeypatch):
        covered = datetime(2026, 6, 10, 10)
        gap = datetime(2026, 6, 10, 9)  # has actual power but no covering baseline
        result = ExpectedResult(
            overall_status=OverallStatus.ok,
            baseline_id=5,
            baseline_type="weather_adjusted_model",
            bucket_size="1h",
            window_start=gap,
            window_end=covered,
            buckets=[
                ExpectedBucket(
                    bucket_start=covered,
                    status=BucketStatus.ok,
                    expected_power_kw=8.0,
                    expected_energy_kwh=8.0,
                    actual_power_kw=7.0,
                    irradiance_wm2=600.0,
                    cell_temperature_f=None,
                    age_years=None,
                    baseline_id=5,
                )
            ],
            expected_energy_kwh=8.0,
            actual_energy_kwh=None,
            ok_bucket_count=1,
            missing_inputs_bucket_count=0,
            pre_pto_bucket_count=0,
            baseline_selection_mode="period_effective",
        )
        monkeypatch.setattr(
            v2, "compute_site_expected_period_effective", lambda *a, **k: result
        )
        # No active-baseline lookup hits the DB here (db_session is None); the
        # gap/coverage behavior is under test, not the read-time gate.
        monkeypatch.setattr(v2, "_active_baseline", lambda *a, **k: None)
        # The gap hour HAS real power (and irradiance) but no covering baseline.
        monkeypatch.setattr(
            v2,
            "_power_irradiance_maps",
            lambda *a, **k: ({gap: 4.0, covered: 7.0}, {gap: 300.0, covered: 600.0}),
        )
        out = v2.build_actual_vs_expected_section(
            None, SimpleNamespace(id=1, timezone="UTC")
        )
        by_ts = {p["period"]: p for p in out["data"]}
        # Covered point: real expected + baseline_id.
        assert by_ts[covered]["expected"] == 8.0
        assert by_ts[covered]["baseline_id"] == 5
        # Gap point: actual stays visible, expected honestly None, no baseline.
        assert by_ts[gap]["actual"] == 4.0
        assert by_ts[gap]["expected"] is None
        assert by_ts[gap]["baseline_id"] is None
        # Real production in an uncovered period -> the section is partial.
        assert out["expected_state"] == ExpectedState.partial.value

    def test_past_performance_pre_baseline_day_is_honest_none(self, monkeypatch):
        covered_day_ts = datetime(2026, 6, 10, 10)
        gap_day_ts = datetime(2026, 6, 9, 10)  # earlier day, no covering baseline
        result = ExpectedResult(
            overall_status=OverallStatus.ok,
            baseline_id=5,
            baseline_type="weather_adjusted_model",
            bucket_size="1h",
            window_start=gap_day_ts,
            window_end=covered_day_ts,
            buckets=[
                ExpectedBucket(
                    bucket_start=covered_day_ts,
                    status=BucketStatus.ok,
                    expected_power_kw=10.0,
                    expected_energy_kwh=10.0,
                    actual_power_kw=10.0,
                    irradiance_wm2=600.0,
                    cell_temperature_f=None,
                    age_years=None,
                    baseline_id=5,
                )
            ],
            expected_energy_kwh=10.0,
            actual_energy_kwh=None,
            ok_bucket_count=1,
            missing_inputs_bucket_count=0,
            pre_pto_bucket_count=0,
            baseline_selection_mode="period_effective",
        )
        monkeypatch.setattr(
            v2, "compute_site_expected_period_effective", lambda *a, **k: result
        )
        # No active-baseline lookup hits the DB here (db_session is None); the
        # gap/coverage behavior is under test, not the read-time gate.
        monkeypatch.setattr(v2, "_active_baseline", lambda *a, **k: None)
        # The earlier day has production but fell in an uncovered period.
        monkeypatch.setattr(
            v2,
            "_power_irradiance_maps",
            lambda *a, **k: (
                {gap_day_ts: 5.0, covered_day_ts: 10.0},
                {gap_day_ts: 300.0, covered_day_ts: 600.0},
            ),
        )
        out = v2.build_past_performance_section(
            None, SimpleNamespace(id=1, timezone="UTC")
        )
        # The covered day has a real percent; the pre-baseline day still appears
        # but as an honest None (never a fabricated 0%).
        assert out["data"][datetime(2026, 6, 10)] == 100
        assert out["data"][datetime(2026, 6, 9)] is None
        assert out["expected_state"] == ExpectedState.partial.value
