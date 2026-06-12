"""DD V2 Phase 3 — design-estimate baseline POINTS producer.

These guard the honesty + safety contract of
``app.services.telemetry.baseline_points_service`` and its two endpoints
(``points-readiness`` GET + ``generate-design-points`` POST):

* points are built from a site's ACTIVE/promoted PVsyst ``project_facts`` and
  attached to an EXISTING ``draft`` / ``in_review`` ``design_estimate`` baseline;
* only ``monthly`` + ``annual`` design points are produced — the weather-adjusted
  model (computed on read) is NEVER touched;
* nothing is ever fabricated: an absent month is "partial" (a warning), a
  present-but-malformed value is an itemized parse error that blocks the write,
  and an annual total is NEVER distributed into months;
* units are stored as-extracted into ``expected_energy_kwh`` (never converted);
  GHI + P50/P90 live in the header ``design_points`` block, never in a point;
* a rebuild is idempotent — delete + re-insert yields an identical set — and an
  ``approved`` / ``active`` baseline (or a non-design type) is never mutated.

Service-level tests use real DB fixtures (``company_id``/``site_id`` cascade on
teardown). Endpoint tests drive the FastAPI app via the shared ``client`` +
system-user auth.
"""
from __future__ import annotations

import inspect
from datetime import date, datetime

import pytest

from app.crud.telemetry_expected import (
    DESIGN_POINT_GRANULARITIES,
    TelemetryExpectedBaselinePointCRUD,
)
from app.models.project_facts import CanonicalField, FactStatus, ProjectFact
from app.models.telemetry_expected import (
    TelemetryBaselineGranularity,
    TelemetryBaselineStatus,
    TelemetryBaselineType,
    TelemetryExpectedBaseline,
)
from app.services.telemetry import baseline_points_service as svc
from app.services.telemetry.baseline_points_service import (
    ANNUAL_GHI_FIELD,
    ANNUAL_PRODUCTION_FIELD,
    CALCULATION_METHOD,
    MONTHLY_PRODUCTION_FIELDS,
    P50_FIELD,
    P90_FIELD,
    STATISTICAL_STANDARD_FIELD,
)

DESIGN = TelemetryBaselineType.design_estimate
WAM = TelemetryBaselineType.weather_adjusted_model

MONTH_TO_FIELD = {month: name for name, month in MONTHLY_PRODUCTION_FIELDS.items()}

# Distinct per-month production (kWh) so individual points are identifiable.
MONTHLY_KWH = {month: 100000.0 + month * 1000.0 for month in range(1, 13)}
ANNUAL_KWH = 1_400_000.0


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _canonical(db, name):
    field = (
        db.query(CanonicalField).filter(CanonicalField.name == name).one_or_none()
    )
    if field is None:
        field = CanonicalField(name=name, display_name=name, field_type="number")
        db.add(field)
        db.commit()
        db.refresh(field)
    return field


def _add_fact(
    db,
    site_id,
    name,
    value,
    *,
    source_file_id=None,
    ai_confidence=None,
    status=FactStatus.active.value,
):
    field = _canonical(db, name)
    fact = ProjectFact(
        site_id=site_id,
        canonical_field_id=field.id,
        value={"v": value},
        status=status,
        source_file_id=source_file_id,
        ai_confidence=ai_confidence,
    )
    db.add(fact)
    db.commit()
    db.refresh(fact)
    return fact


def _seed_monthly(db, site_id, values=None, **kw):
    values = MONTHLY_KWH if values is None else values
    return {
        month: _add_fact(db, site_id, MONTH_TO_FIELD[month], val, **kw)
        for month, val in values.items()
    }


def _make_design_baseline(
    db,
    company_id,
    site_id,
    *,
    status=TelemetryBaselineStatus.draft,
    timezone=None,
    pto_date=None,
    system_size_dc_kw=None,
    baseline_type=DESIGN,
):
    baseline = TelemetryExpectedBaseline(
        company_id=company_id,
        site_id=site_id,
        baseline_name="design draft",
        baseline_type=baseline_type,
        status=status,
        version=1,
        timezone=timezone,
        pto_date=pto_date,
        system_size_dc_kw=system_size_dc_kw,
    )
    db.add(baseline)
    db.commit()
    db.refresh(baseline)
    return baseline


def _points(db, baseline_id, granularities=None):
    return TelemetryExpectedBaselinePointCRUD(db).list_for_baseline(
        baseline_id, granularities
    )


def _by_month(points):
    return {p.point_ts.month: p for p in points}


# ===========================================================================
# F1 — readiness: no production facts -> honest "no_design_data" (never ready)
# ===========================================================================
def test_f1_readiness_no_production_facts_is_no_design_data(
    db_session, company_id, site, site_id
):
    baseline = _make_design_baseline(
        db_session, company_id, site_id, pto_date=date(2025, 1, 1)
    )

    res = svc.evaluate_points_readiness(db_session, site, baseline)

    assert res.ready is False
    assert res.has_design_data is False
    assert res.parsed_months == []
    assert res.annual_value is None
    assert res.parse_errors == []
    # Every production field is reported outstanding (not fabricated).
    assert ANNUAL_PRODUCTION_FIELD in res.missing_fields
    assert set(MONTHLY_PRODUCTION_FIELDS).issubset(set(res.missing_fields))


# ===========================================================================
# F2 — readiness: full 12 months + annual -> ready, anchored, nothing written
# ===========================================================================
def test_f2_readiness_full_facts_ready_and_does_not_write(
    db_session, company_id, site, site_id
):
    _seed_monthly(db_session, site_id)
    _add_fact(db_session, site_id, ANNUAL_PRODUCTION_FIELD, ANNUAL_KWH)
    baseline = _make_design_baseline(
        db_session, company_id, site_id, timezone="UTC", pto_date=date(2025, 1, 1)
    )

    res = svc.evaluate_points_readiness(db_session, site, baseline)

    assert res.ready is True
    assert res.has_design_data is True
    assert res.parsed_months == list(range(1, 13))
    assert len(res.parsed_months) == 12
    assert res.annual_value == pytest.approx(ANNUAL_KWH)
    assert res.reference_year == 2025
    assert res.reference_year_source == "pto_date"
    assert res.parse_errors == []
    # Readiness NEVER writes.
    assert _points(db_session, baseline.id) == []


# ===========================================================================
# F3 — generate full curve: 12 monthly + 1 annual point, correct columns + header
# ===========================================================================
def test_f3_generate_full_curve_writes_points_and_header(
    db_session, company_id, site, site_id, file
):
    _seed_monthly(db_session, site_id, source_file_id=file.id, ai_confidence=0.8)
    _add_fact(
        db_session,
        site_id,
        ANNUAL_PRODUCTION_FIELD,
        ANNUAL_KWH,
        source_file_id=file.id,
        ai_confidence=0.8,
    )
    baseline = _make_design_baseline(
        db_session, company_id, site_id, timezone="UTC", pto_date=date(2025, 1, 1)
    )

    result = svc.generate_design_points(db_session, site, baseline)

    assert result.wrote is True
    assert result.points_created == 13
    assert result.points_deleted == 0
    assert result.monthly_points == 12
    assert result.annual_points == 1

    monthly = _points(db_session, baseline.id, (TelemetryBaselineGranularity.monthly,))
    annual = _points(db_session, baseline.id, (TelemetryBaselineGranularity.annual,))
    assert len(monthly) == 12
    assert len(annual) == 1

    # Monthly points: all in the ref year, value as-extracted, never converted.
    by_month = _by_month(monthly)
    for month, point in by_month.items():
        assert point.point_ts == datetime(2025, month, 1, 0, 0)
        assert float(point.expected_energy_kwh) == pytest.approx(MONTHLY_KWH[month])
        assert point.calculation_method == CALCULATION_METHOD
        assert point.source_granularity == TelemetryBaselineGranularity.monthly
        assert point.irradiance_wm2 is None  # GHI is NEVER written to a point
        assert point.expected_power_kw is None
        assert point.device_id is None  # site-level only

    # Annual point anchored at Jan 1 of the same ref year.
    assert annual[0].point_ts == datetime(2025, 1, 1, 0, 0)
    assert float(annual[0].expected_energy_kwh) == pytest.approx(ANNUAL_KWH)

    # Header design_points provenance block.
    block = baseline.model_parameters_json["design_points"]
    assert block["calculation_method"] == CALCULATION_METHOD
    assert block["assumed_unit"] == "kwh"
    assert block["unit_verified"] is False
    assert block["reference_year"] == 2025
    assert block["reference_year_source"] == "pto_date"
    assert block["monthly_points"] == 12
    assert block["annual_points"] == 1
    assert block["monthly"]["1"]["fact_id"]
    assert block["monthly"]["1"]["document_id"] == file.document_id
    assert block["monthly"]["1"]["ai_confidence"] == pytest.approx(0.8)
    assert file.document_id in block["source_document_ids"]


# ===========================================================================
# F4 — idempotent rebuild: re-run replaces the set, no duplicates
# ===========================================================================
def test_f4_generate_is_idempotent_delete_rebuild(
    db_session, company_id, site, site_id
):
    _seed_monthly(db_session, site_id)
    _add_fact(db_session, site_id, ANNUAL_PRODUCTION_FIELD, ANNUAL_KWH)
    baseline = _make_design_baseline(
        db_session, company_id, site_id, timezone="UTC", pto_date=date(2025, 1, 1)
    )

    first = svc.generate_design_points(db_session, site, baseline)
    assert first.points_created == 13
    assert first.points_deleted == 0

    second = svc.generate_design_points(db_session, site, baseline)
    assert second.points_created == 13
    assert second.points_deleted == 13  # prior monthly+annual removed first

    # Exactly one set survives — no duplicate accumulation.
    assert len(_points(db_session, baseline.id)) == 13


# ===========================================================================
# F5 — partial months: only present months produced, absent never fabricated
# ===========================================================================
def test_f5_partial_months_are_not_fabricated(
    db_session, company_id, site, site_id
):
    present = {1: MONTHLY_KWH[1], 2: MONTHLY_KWH[2], 6: MONTHLY_KWH[6]}
    _seed_monthly(db_session, site_id, values=present)
    baseline = _make_design_baseline(
        db_session, company_id, site_id, timezone="UTC", pto_date=date(2025, 1, 1)
    )

    res = svc.evaluate_points_readiness(db_session, site, baseline)
    assert res.ready is True  # partial coverage is still buildable
    assert res.parsed_months == [1, 2, 6]
    assert any("absent months are not fabricated" in w for w in res.warnings)

    result = svc.generate_design_points(db_session, site, baseline)
    assert result.monthly_points == 3
    assert result.annual_points == 0
    monthly = _points(db_session, baseline.id, (TelemetryBaselineGranularity.monthly,))
    assert sorted(_by_month(monthly)) == [1, 2, 6]


# ===========================================================================
# F6 — malformed PRESENT production fact -> parse error, 422, writes nothing
# ===========================================================================
def test_f6_malformed_present_fact_blocks_write(
    db_session, company_id, site, site_id
):
    values = dict(MONTHLY_KWH)
    values[3] = "N/A"  # present but non-numeric
    _seed_monthly(db_session, site_id, values=values)
    baseline = _make_design_baseline(
        db_session, company_id, site_id, timezone="UTC", pto_date=date(2025, 1, 1)
    )

    res = svc.evaluate_points_readiness(db_session, site, baseline)
    assert res.ready is False
    assert any(e["month"] == 3 for e in res.parse_errors)

    result = svc.generate_design_points(db_session, site, baseline)
    assert result.wrote is False
    assert result.points_created == 0
    # NOTHING was written despite 11 valid months.
    assert _points(db_session, baseline.id) == []


def test_f6_negative_production_value_is_a_parse_error(
    db_session, company_id, site, site_id
):
    _add_fact(db_session, site_id, ANNUAL_PRODUCTION_FIELD, -5.0)
    baseline = _make_design_baseline(
        db_session, company_id, site_id, timezone="UTC", pto_date=date(2025, 1, 1)
    )

    res = svc.evaluate_points_readiness(db_session, site, baseline)
    assert res.ready is False
    assert any("negative" in e["error"] for e in res.parse_errors)


# ===========================================================================
# F7 — annual only (no monthly facts) -> single annual point, never split
# ===========================================================================
def test_f7_annual_only_produces_single_annual_point(
    db_session, company_id, site, site_id
):
    _add_fact(db_session, site_id, ANNUAL_PRODUCTION_FIELD, ANNUAL_KWH)
    baseline = _make_design_baseline(
        db_session, company_id, site_id, timezone="UTC", pto_date=date(2025, 1, 1)
    )

    result = svc.generate_design_points(db_session, site, baseline)
    assert result.monthly_points == 0  # annual is NEVER distributed into months
    assert result.annual_points == 1
    annual = _points(db_session, baseline.id, (TelemetryBaselineGranularity.annual,))
    assert len(annual) == 1
    assert float(annual[0].expected_energy_kwh) == pytest.approx(ANNUAL_KWH)


# ===========================================================================
# F8 — GHI + P50/P90 are header metadata only (never points, never irradiance)
# ===========================================================================
def test_f8_ghi_and_scenarios_are_header_metadata_only(
    db_session, company_id, site, site_id
):
    _seed_monthly(db_session, site_id)
    _add_fact(db_session, site_id, ANNUAL_GHI_FIELD, 1850.0)
    _add_fact(db_session, site_id, P50_FIELD, 1380.0)
    _add_fact(db_session, site_id, P90_FIELD, 1300.0)
    _add_fact(db_session, site_id, STATISTICAL_STANDARD_FIELD, "P50")
    baseline = _make_design_baseline(
        db_session, company_id, site_id, timezone="UTC", pto_date=date(2025, 1, 1)
    )

    res = svc.evaluate_points_readiness(db_session, site, baseline)
    assert res.schema_expansion_recommended is True
    assert res.scenarios is not None
    assert res.scenarios["p50_mwh"]["value"] == pytest.approx(1380.0)
    assert res.scenarios["statistical_standard"]["value"] == "P50"

    svc.generate_design_points(db_session, site, baseline)

    # No GHI/scenario value ever leaks into a point row.
    for point in _points(db_session, baseline.id):
        assert point.irradiance_wm2 is None
    block = baseline.model_parameters_json["design_points"]
    assert block["ghi"]["annual"]["value"] == pytest.approx(1850.0)
    assert block["scenarios"]["p90_mwh"]["value"] == pytest.approx(1300.0)
    assert block["schema_expansion_recommended"] is True


# ===========================================================================
# F9 — reference year precedence: pto_date.year wins
# ===========================================================================
def test_f9_reference_year_prefers_pto_date(
    db_session, company_id, site, site_id
):
    _seed_monthly(db_session, site_id, values={1: MONTHLY_KWH[1]})
    baseline = _make_design_baseline(
        db_session, company_id, site_id, timezone="UTC", pto_date=date(2027, 9, 9)
    )

    res = svc.evaluate_points_readiness(db_session, site, baseline)
    assert res.reference_year == 2027
    assert res.reference_year_source == "pto_date"

    svc.generate_design_points(db_session, site, baseline)
    monthly = _points(db_session, baseline.id, (TelemetryBaselineGranularity.monthly,))
    assert monthly[0].point_ts == datetime(2027, 1, 1, 0, 0)


# ===========================================================================
# F10 — reference year falls back to created_at when no pto_date
# ===========================================================================
def test_f10_reference_year_falls_back_to_created_at(
    db_session, company_id, site, site_id
):
    _seed_monthly(db_session, site_id, values={1: MONTHLY_KWH[1]})
    baseline = _make_design_baseline(
        db_session, company_id, site_id, timezone="UTC", pto_date=None
    )

    res = svc.evaluate_points_readiness(db_session, site, baseline)
    assert res.reference_year == baseline.created_at.year
    assert res.reference_year_source == "created_at"


# ===========================================================================
# F11 — site-local midnight: tz converts first-of-month to naive-UTC
# ===========================================================================
def test_f11_timezone_anchors_site_local_midnight_to_naive_utc(
    db_session, company_id, site, site_id
):
    _seed_monthly(db_session, site_id, values={1: MONTHLY_KWH[1]})
    _add_fact(db_session, site_id, ANNUAL_PRODUCTION_FIELD, ANNUAL_KWH)
    baseline = _make_design_baseline(
        db_session,
        company_id,
        site_id,
        timezone="America/New_York",
        pto_date=date(2024, 6, 1),
    )

    svc.generate_design_points(db_session, site, baseline)

    monthly = _points(db_session, baseline.id, (TelemetryBaselineGranularity.monthly,))
    annual = _points(db_session, baseline.id, (TelemetryBaselineGranularity.annual,))
    # Jan 1 2024 00:00 America/New_York (EST, UTC-5) == 05:00 naive-UTC.
    assert monthly[0].point_ts == datetime(2024, 1, 1, 5, 0)
    assert annual[0].point_ts == datetime(2024, 1, 1, 5, 0)


# ===========================================================================
# F12 — never mutate non-draft/non-design baselines (service writes regardless,
#       so the guard lives in the endpoint — verified below) + scoped delete
# ===========================================================================
def test_f12_delete_is_scoped_to_design_granularities(
    db_session, company_id, site, site_id
):
    # An hourly/interval point on the same baseline must survive a rebuild.
    _add_fact(db_session, site_id, ANNUAL_PRODUCTION_FIELD, ANNUAL_KWH)
    baseline = _make_design_baseline(
        db_session, company_id, site_id, timezone="UTC", pto_date=date(2025, 1, 1)
    )
    from app.models.telemetry_expected import TelemetryExpectedBaselinePoint

    hourly = TelemetryExpectedBaselinePoint(
        baseline_id=baseline.id,
        site_id=site_id,
        point_ts=datetime(2025, 6, 1, 12, 0),
        interval_minutes=60,
        expected_energy_kwh=10.0,
        source_granularity=TelemetryBaselineGranularity.hourly,
        calculation_method="other",
    )
    db_session.add(hourly)
    db_session.commit()

    svc.generate_design_points(db_session, site, baseline)
    svc.generate_design_points(db_session, site, baseline)  # rebuild again

    survivors = _points(db_session, baseline.id, (TelemetryBaselineGranularity.hourly,))
    assert len(survivors) == 1  # hourly never touched by the design rebuild
    assert set(DESIGN_POINT_GRANULARITIES) == {
        TelemetryBaselineGranularity.monthly,
        TelemetryBaselineGranularity.annual,
    }


def test_f12_service_refuses_immutable_baseline(
    db_session, company_id, site, site_id
):
    # Defense-in-depth: the service itself refuses an active baseline even if a
    # caller bypasses the endpoint guard. Nothing is written.
    _add_fact(db_session, site_id, ANNUAL_PRODUCTION_FIELD, ANNUAL_KWH)
    baseline = _make_design_baseline(
        db_session,
        company_id,
        site_id,
        status=TelemetryBaselineStatus.active,
        pto_date=date(2025, 1, 1),
    )

    with pytest.raises(ValueError):
        svc.generate_design_points(db_session, site, baseline)
    assert _points(db_session, baseline.id) == []


def test_f12_service_refuses_wrong_baseline_type(
    db_session, company_id, site, site_id
):
    _add_fact(db_session, site_id, ANNUAL_PRODUCTION_FIELD, ANNUAL_KWH)
    baseline = _make_design_baseline(
        db_session, company_id, site_id, baseline_type=WAM, pto_date=date(2025, 1, 1)
    )

    with pytest.raises(ValueError):
        svc.generate_design_points(db_session, site, baseline)
    assert _points(db_session, baseline.id) == []


# ===========================================================================
# F13 — guardrails: no legacy pipelines reintroduced; calc math untouched
# ===========================================================================
def test_f13_service_does_not_reintroduce_bigquery_firestore_or_docai():
    source = inspect.getsource(svc).lower()
    for forbidden in ("bigquery", "firestore", "google.cloud", "docai"):
        assert forbidden not in source


def test_f13_service_never_writes_irradiance_or_power_columns():
    # The producer must only ever populate expected_energy_kwh on a point.
    source = inspect.getsource(svc)
    assert "irradiance_wm2=None" in source
    assert "expected_power_kw=None" in source


# ===========================================================================
# Endpoints
# ===========================================================================
def _readiness_url(site_id, baseline_id):
    return (
        f"/api/telemetry/v2/sites/{site_id}/expected-baseline/"
        f"{baseline_id}/points-readiness"
    )


def _generate_url(site_id, baseline_id):
    return (
        f"/api/telemetry/v2/sites/{site_id}/expected-baseline/"
        f"{baseline_id}/generate-design-points"
    )


def test_endpoint_readiness_then_generate(
    client, system_user_auth_header, db_session, company_id, site_id
):
    _seed_monthly(db_session, site_id)
    _add_fact(db_session, site_id, ANNUAL_PRODUCTION_FIELD, ANNUAL_KWH)
    baseline = _make_design_baseline(
        db_session, company_id, site_id, timezone="UTC", pto_date=date(2025, 1, 1)
    )

    readiness = client.get(
        _readiness_url(site_id, baseline.id), headers=system_user_auth_header
    )
    assert readiness.status_code == 200
    rbody = readiness.json()
    assert rbody["ready"] is True
    assert rbody["parsed_months"] == list(range(1, 13))
    assert rbody["reference_year"] == 2025

    generate = client.post(
        _generate_url(site_id, baseline.id), headers=system_user_auth_header
    )
    assert generate.status_code == 200
    gbody = generate.json()
    assert gbody["status"] == "generated"
    assert gbody["monthly_points"] == 12
    assert gbody["annual_points"] == 1


def test_endpoint_in_review_baseline_generates(
    client, system_user_auth_header, db_session, company_id, site_id
):
    # in_review is mutable just like draft.
    _add_fact(db_session, site_id, ANNUAL_PRODUCTION_FIELD, ANNUAL_KWH)
    baseline = _make_design_baseline(
        db_session,
        company_id,
        site_id,
        status=TelemetryBaselineStatus.in_review,
        timezone="UTC",
        pto_date=date(2025, 1, 1),
    )

    resp = client.post(
        _generate_url(site_id, baseline.id), headers=system_user_auth_header
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "generated"
    assert resp.json()["annual_points"] == 1


def test_endpoint_readiness_on_active_baseline_returns_200(
    client, system_user_auth_header, db_session, company_id, site_id
):
    # readiness is read-only (require_mutable=False) so an active baseline is fine.
    _add_fact(db_session, site_id, ANNUAL_PRODUCTION_FIELD, ANNUAL_KWH)
    baseline = _make_design_baseline(
        db_session,
        company_id,
        site_id,
        status=TelemetryBaselineStatus.active,
        pto_date=date(2025, 1, 1),
    )

    resp = client.get(
        _readiness_url(site_id, baseline.id), headers=system_user_auth_header
    )
    assert resp.status_code == 200
    assert resp.json()["ready"] is True


def test_endpoint_generate_no_design_data_returns_422(
    client, system_user_auth_header, db_session, company_id, site_id
):
    baseline = _make_design_baseline(
        db_session, company_id, site_id, pto_date=date(2025, 1, 1)
    )

    resp = client.post(
        _generate_url(site_id, baseline.id), headers=system_user_auth_header
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["status"] == "no_design_data"
    assert body["ready"] is False
    assert _points(db_session, baseline.id) == []


def test_endpoint_generate_malformed_returns_422(
    client, system_user_auth_header, db_session, company_id, site_id
):
    _add_fact(db_session, site_id, ANNUAL_PRODUCTION_FIELD, "garbage")
    baseline = _make_design_baseline(
        db_session, company_id, site_id, pto_date=date(2025, 1, 1)
    )

    resp = client.post(
        _generate_url(site_id, baseline.id), headers=system_user_auth_header
    )
    assert resp.status_code == 422
    body = resp.json()
    assert body["status"] == "malformed"
    assert body["parse_errors"]
    assert _points(db_session, baseline.id) == []


def test_endpoint_wrong_baseline_type_returns_409(
    client, system_user_auth_header, db_session, company_id, site_id
):
    baseline = _make_design_baseline(
        db_session, company_id, site_id, baseline_type=WAM, pto_date=date(2025, 1, 1)
    )

    resp = client.post(
        _generate_url(site_id, baseline.id), headers=system_user_auth_header
    )
    assert resp.status_code == 409


def test_endpoint_non_mutable_status_returns_409(
    client, system_user_auth_header, db_session, company_id, site_id
):
    _add_fact(db_session, site_id, ANNUAL_PRODUCTION_FIELD, ANNUAL_KWH)
    baseline = _make_design_baseline(
        db_session,
        company_id,
        site_id,
        status=TelemetryBaselineStatus.active,
        pto_date=date(2025, 1, 1),
    )

    resp = client.post(
        _generate_url(site_id, baseline.id), headers=system_user_auth_header
    )
    assert resp.status_code == 409
    # An active baseline is NEVER mutated.
    assert _points(db_session, baseline.id) == []


def test_endpoint_missing_baseline_returns_404(
    client, system_user_auth_header, site_id
):
    resp = client.get(
        _readiness_url(site_id, 99999999), headers=system_user_auth_header
    )
    assert resp.status_code == 404


def test_endpoint_requires_telemetry_admin(
    client, non_system_user_auth_header, db_session, company_id, site_id
):
    baseline = _make_design_baseline(
        db_session, company_id, site_id, pto_date=date(2025, 1, 1)
    )

    resp = client.get(
        _readiness_url(site_id, baseline.id), headers=non_system_user_auth_header
    )
    assert resp.status_code in (401, 403, 404)
