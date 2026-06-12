"""DD V2 Phase 4 — READ-ONLY assumptions reconciliation aggregator.

These guard the honesty + safety contract of
``app.services.due_diligence.reconciliation_service`` and its single endpoint
(``GET /api/due-diligence/sites/{site_id}/reconciliation``):

* the service is STRICTLY READ-ONLY — it performs zero writes/commits, never
  recomputes a baseline value (point values are read verbatim), and never
  creates/approves/activates anything;
* every catalog field renders a row even on an empty site (honest ``missing``,
  never a 500), plus catch-all rows for any other promoted/candidate fact;
* the per-field status ladder is most-advanced-wins (missing -> candidate_only
  -> active_fact -> in_draft_baseline -> in_active_baseline) and ``superseded``
  is a history pointer, never a row status;
* warnings are orthogonal to status: missing_required_for_baseline,
  fact_differs_from_legacy (losses compared via magnitude), draft_differs_from_active,
  active_baseline_outdated, design_points_missing, needs_review;
* the two "expected" notions stay separate — physics nameplate reconciles
  against the weather-adjusted header columns, design-estimate production
  against the design-estimate baseline POINTS;
* legacy ``SiteAdditionalFieldList`` values are display/comparison only and are
  never used to build a baseline.

Service-level tests use real DB fixtures (``company_id``/``site_id`` cascade on
teardown). Endpoint tests drive the FastAPI app via the shared ``client`` +
system-user auth.
"""
from __future__ import annotations

from datetime import date, datetime

import pytest

from app.models.project_facts import CanonicalField, FactStatus, ProjectFact
from app.models.site import SiteAdditionalFieldList
from app.models.telemetry_expected import (
    TelemetryBaselineGranularity,
    TelemetryBaselineStatus,
    TelemetryBaselineType,
    TelemetryExpectedBaseline,
    TelemetryExpectedBaselinePoint,
)
from app.services.due_diligence import reconciliation_service as svc
from app.static.reconciliation_catalog import (
    CATALOG_BY_NAME,
    RECONCILIATION_CATALOG,
)

DESIGN = TelemetryBaselineType.design_estimate
WAM = TelemetryBaselineType.weather_adjusted_model
MONTHLY = TelemetryBaselineGranularity.monthly
ANNUAL = TelemetryBaselineGranularity.annual

# Warning tokens (kept in lock-step with the service constants).
W_MISSING_REQUIRED = svc.W_MISSING_REQUIRED
W_FACT_VS_LEGACY = svc.W_FACT_VS_LEGACY
W_DRAFT_VS_ACTIVE = svc.W_DRAFT_VS_ACTIVE
W_ACTIVE_OUTDATED = svc.W_ACTIVE_OUTDATED
W_DESIGN_POINTS_MISSING = svc.W_DESIGN_POINTS_MISSING
W_NEEDS_REVIEW = svc.W_NEEDS_REVIEW


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
    status=FactStatus.active.value,
    source_file_id=None,
    ai_confidence=None,
    ai_extracted_value=None,
    evidence=None,
    source_document_type=None,
    overridden_at=None,
    override_notes=None,
    promoted_at=None,
    supersedes_fact_id=None,
    effective_from=None,
):
    field = _canonical(db, name)
    fact = ProjectFact(
        site_id=site_id,
        canonical_field_id=field.id,
        value={"v": value},
        status=status,
        source_file_id=source_file_id,
        ai_confidence=ai_confidence,
        ai_extracted_value=(
            {"v": ai_extracted_value} if ai_extracted_value is not None else None
        ),
        evidence=evidence,
        source_document_type=source_document_type,
        overridden_at=overridden_at,
        override_notes=override_notes,
        promoted_at=promoted_at,
        supersedes_fact_id=supersedes_fact_id,
        effective_from=effective_from,
    )
    db.add(fact)
    db.commit()
    db.refresh(fact)
    return fact


def _make_baseline(
    db,
    company_id,
    site_id,
    baseline_type,
    *,
    status,
    timezone="UTC",
    source_facts=None,
    created_at=None,
    pto_date=None,
    **cols,
):
    baseline = TelemetryExpectedBaseline(
        company_id=company_id,
        site_id=site_id,
        baseline_name="recon test baseline",
        baseline_type=baseline_type,
        status=status,
        version=1,
        timezone=timezone,
        pto_date=pto_date,
        model_parameters_json=(
            {"source_facts": source_facts} if source_facts is not None else None
        ),
        **cols,
    )
    if created_at is not None:
        baseline.created_at = created_at
    db.add(baseline)
    db.commit()
    db.refresh(baseline)
    return baseline


def _add_point(db, baseline_id, site_id, granularity, point_ts, energy):
    point = TelemetryExpectedBaselinePoint(
        baseline_id=baseline_id,
        site_id=site_id,
        source_granularity=granularity,
        point_ts=point_ts,
        expected_energy_kwh=energy,
    )
    db.add(point)
    db.commit()
    db.refresh(point)
    return point


def _add_safl(db, site_id, **cols):
    safl = SiteAdditionalFieldList(site_id=site_id, **cols)
    db.add(safl)
    db.commit()
    db.refresh(safl)
    return safl


def _row(resp, canonical_name):
    return next(r for r in resp.rows if r.canonical_field == canonical_name)


def _url(site_id):
    return f"/api/due-diligence/sites/{site_id}/reconciliation"


# ===========================================================================
# H1 — empty site: every catalog field renders honestly, never a 500
# ===========================================================================
def test_h1_empty_site_renders_full_catalog(db_session, site):
    resp = svc.build_site_reconciliation(db_session, site)

    # Exactly one row per catalog entry (no catch-all rows on an empty site).
    assert len(resp.rows) == len(RECONCILIATION_CATALOG)
    assert all(r.status == "missing" for r in resp.rows)

    mw = _row(resp, "module_wattage")
    assert mw.required_for_baseline is True
    assert W_MISSING_REQUIRED in mw.warnings
    assert mw.active_fact_value is None
    assert mw.draft_baseline_value is None
    assert mw.active_baseline_value is None

    # Block scaffolding is always present and honest.
    assert resp.telemetry_reality.available is False
    assert resp.telemetry_reality.last_reading_at is None
    assert resp.help_targets  # tooltip hooks present
    assert resp.schema_expansion_recommended is False
    assert resp.readiness.active_baseline_available is False
    assert resp.readiness.design_points_ready is None


# ===========================================================================
# H2 — candidate-only fact: candidate_only status + needs_review + required gap
# ===========================================================================
def test_h2_candidate_only_status(db_session, site, site_id):
    _add_fact(
        db_session,
        site_id,
        "module_wattage",
        400.0,
        status=FactStatus.candidate.value,
    )

    resp = svc.build_site_reconciliation(db_session, site)
    row = _row(resp, "module_wattage")

    assert row.status == "candidate_only"
    assert row.accepted_value == 400.0
    assert row.active_fact_value is None
    assert row.candidate_count == 1
    assert W_MISSING_REQUIRED in row.warnings  # no ACTIVE fact yet
    assert W_NEEDS_REVIEW in row.warnings  # unresolved candidate on a driver


# ===========================================================================
# H3 — active fact, no baseline: active_fact, clean warnings
# ===========================================================================
def test_h3_active_fact_no_baseline(db_session, site, site_id):
    _add_fact(db_session, site_id, "module_wattage", 400.0)

    resp = svc.build_site_reconciliation(db_session, site)
    row = _row(resp, "module_wattage")

    assert row.status == "active_fact"
    assert row.active_fact_value == 400.0
    assert row.draft_baseline_value is None
    assert row.active_baseline_value is None
    assert row.warnings == []


# ===========================================================================
# H4 — header value present on DRAFT weather-adjusted baseline only
# ===========================================================================
def test_h4_in_draft_baseline_header(db_session, company_id, site, site_id):
    _add_fact(db_session, site_id, "module_wattage", 400.0)
    _make_baseline(
        db_session,
        company_id,
        site_id,
        WAM,
        status=TelemetryBaselineStatus.draft,
        module_wattage=400,
    )

    resp = svc.build_site_reconciliation(db_session, site)
    row = _row(resp, "module_wattage")

    assert row.status == "in_draft_baseline"
    assert row.draft_baseline_value == 400
    assert row.active_baseline_value is None
    assert W_ACTIVE_OUTDATED not in row.warnings  # no active baseline to be stale


# ===========================================================================
# H5 — header value on ACTIVE baseline, fact in source + older: not outdated
# ===========================================================================
def test_h5_in_active_baseline_not_outdated(db_session, company_id, site, site_id):
    fact = _add_fact(
        db_session,
        site_id,
        "module_wattage",
        400.0,
        promoted_at=datetime(2025, 1, 1),
    )
    _make_baseline(
        db_session,
        company_id,
        site_id,
        WAM,
        status=TelemetryBaselineStatus.active,
        module_wattage=400,
        created_at=datetime(2025, 1, 2),
        source_facts=[{"fact_id": fact.id}],
    )

    resp = svc.build_site_reconciliation(db_session, site)
    row = _row(resp, "module_wattage")

    assert row.status == "in_active_baseline"
    assert row.active_baseline_value == 400
    assert W_ACTIVE_OUTDATED not in row.warnings


# ===========================================================================
# H6 — active baseline outdated: active fact absent from baseline source_facts
# ===========================================================================
def test_h6_active_baseline_outdated_missing_source(
    db_session, company_id, site, site_id
):
    _add_fact(
        db_session,
        site_id,
        "module_wattage",
        400.0,
        promoted_at=datetime(2025, 1, 1),
    )
    _make_baseline(
        db_session,
        company_id,
        site_id,
        WAM,
        status=TelemetryBaselineStatus.active,
        module_wattage=400,
        created_at=datetime(2025, 2, 1),
        source_facts=[],  # fact not recorded as a source
    )

    resp = svc.build_site_reconciliation(db_session, site)
    row = _row(resp, "module_wattage")

    assert row.status == "in_active_baseline"
    assert W_ACTIVE_OUTDATED in row.warnings


# ===========================================================================
# H6b — active baseline outdated: fact promoted AFTER baseline creation
# ===========================================================================
def test_h6b_active_baseline_outdated_newer_fact(
    db_session, company_id, site, site_id
):
    fact = _add_fact(
        db_session,
        site_id,
        "module_wattage",
        400.0,
        promoted_at=datetime(2025, 2, 1),
    )
    _make_baseline(
        db_session,
        company_id,
        site_id,
        WAM,
        status=TelemetryBaselineStatus.active,
        module_wattage=400,
        created_at=datetime(2025, 1, 1),
        source_facts=[{"fact_id": fact.id}],
    )

    resp = svc.build_site_reconciliation(db_session, site)
    row = _row(resp, "module_wattage")

    assert W_ACTIVE_OUTDATED in row.warnings


# ===========================================================================
# H7 — override without notes on a driver flags needs_review; AI vs accepted
# ===========================================================================
def test_h7_override_without_notes_needs_review(db_session, site, site_id):
    _add_fact(
        db_session,
        site_id,
        "module_wattage",
        400.0,
        ai_extracted_value=300.0,
        overridden_at=datetime(2025, 1, 1),
        override_notes=None,
    )

    resp = svc.build_site_reconciliation(db_session, site)
    row = _row(resp, "module_wattage")

    assert row.ai_extracted_value == 300.0
    assert row.accepted_value == 400.0
    assert row.active_fact_value == 400.0
    assert W_NEEDS_REVIEW in row.warnings


def test_h7b_override_with_notes_no_needs_review(db_session, site, site_id):
    _add_fact(
        db_session,
        site_id,
        "module_wattage",
        400.0,
        ai_extracted_value=300.0,
        overridden_at=datetime(2025, 1, 1),
        override_notes="Datasheet confirmed by reviewer.",
    )

    resp = svc.build_site_reconciliation(db_session, site)
    row = _row(resp, "module_wattage")

    assert W_NEEDS_REVIEW not in row.warnings


# ===========================================================================
# H8 — legacy loss comparison is magnitude-only (sign convention differs)
# ===========================================================================
def test_h8_loss_matches_legacy_via_abs_no_warning(db_session, site, site_id):
    # dc_loss_pct is a catch-all (not in catalog) but SAFL-mapped + abs-compared.
    _add_fact(db_session, site_id, "dc_loss_pct", -2.0)
    _add_safl(db_session, site_id, dc_wiring_loss=2.0)

    resp = svc.build_site_reconciliation(db_session, site)
    row = _row(resp, "dc_loss_pct")

    assert row.legacy_value == 2.0
    assert row.active_fact_value == -2.0
    assert W_FACT_VS_LEGACY not in row.warnings


def test_h8b_loss_differs_from_legacy(db_session, site, site_id):
    _add_fact(db_session, site_id, "dc_loss_pct", -3.0)
    _add_safl(db_session, site_id, dc_wiring_loss=2.0)

    resp = svc.build_site_reconciliation(db_session, site)
    row = _row(resp, "dc_loss_pct")

    assert W_FACT_VS_LEGACY in row.warnings


# ===========================================================================
# H8c — legacy DATE comparison is exact after parse (str fact vs date column)
# ===========================================================================
def test_h8c_legacy_date_exact_match_no_warning(db_session, site, site_id):
    _add_fact(db_session, site_id, "placed_in_service_date", "2025-01-15")
    _add_safl(db_session, site_id, placed_in_service_date=date(2025, 1, 15))

    resp = svc.build_site_reconciliation(db_session, site)
    row = _row(resp, "placed_in_service_date")

    assert W_FACT_VS_LEGACY not in row.warnings


# ===========================================================================
# H9 — draft header value differs from active header value -> warning
# ===========================================================================
def test_h9_draft_differs_from_active_header(db_session, company_id, site, site_id):
    fact = _add_fact(
        db_session,
        site_id,
        "module_wattage",
        410.0,
        promoted_at=datetime(2025, 1, 1),
    )
    _make_baseline(
        db_session,
        company_id,
        site_id,
        WAM,
        status=TelemetryBaselineStatus.active,
        module_wattage=410,
        created_at=datetime(2025, 1, 2),
        source_facts=[{"fact_id": fact.id}],
    )
    _make_baseline(
        db_session,
        company_id,
        site_id,
        WAM,
        status=TelemetryBaselineStatus.draft,
        module_wattage=400,
    )

    resp = svc.build_site_reconciliation(db_session, site)
    row = _row(resp, "module_wattage")

    assert row.status == "in_active_baseline"  # most-advanced wins
    assert row.draft_baseline_value == 400
    assert row.active_baseline_value == 410
    assert W_DRAFT_VS_ACTIVE in row.warnings


# ===========================================================================
# H10 — design monthly point present on DRAFT design-estimate baseline (read)
# ===========================================================================
def test_h10_monthly_point_in_draft_design(db_session, company_id, site, site_id):
    _add_fact(db_session, site_id, "january_estimated_production_year_1", 100000.0)
    baseline = _make_baseline(
        db_session,
        company_id,
        site_id,
        DESIGN,
        status=TelemetryBaselineStatus.draft,
        pto_date=date(2025, 1, 1),
    )
    _add_point(db_session, baseline.id, site_id, MONTHLY, datetime(2025, 1, 1), 100000.0)

    resp = svc.build_site_reconciliation(db_session, site)
    row = _row(resp, "january_estimated_production_year_1")

    assert row.status == "in_draft_baseline"
    assert row.draft_baseline_value == pytest.approx(100000.0)
    assert W_DESIGN_POINTS_MISSING not in row.warnings


# ===========================================================================
# H10b — active production fact but design baseline lacks the point -> warning
# ===========================================================================
def test_h10b_design_points_missing_warning(db_session, company_id, site, site_id):
    _add_fact(db_session, site_id, "january_estimated_production_year_1", 100000.0)
    _make_baseline(
        db_session,
        company_id,
        site_id,
        DESIGN,
        status=TelemetryBaselineStatus.draft,
        pto_date=date(2025, 1, 1),
    )

    resp = svc.build_site_reconciliation(db_session, site)
    row = _row(resp, "january_estimated_production_year_1")

    assert row.status == "active_fact"
    assert W_DESIGN_POINTS_MISSING in row.warnings


# ===========================================================================
# H10c — annual point present on ACTIVE design-estimate baseline (read verbatim)
# ===========================================================================
def test_h10c_annual_point_in_active_design(db_session, company_id, site, site_id):
    _add_fact(db_session, site_id, "estimated_production_year_1", 1400000.0)
    baseline = _make_baseline(
        db_session,
        company_id,
        site_id,
        DESIGN,
        status=TelemetryBaselineStatus.active,
        pto_date=date(2025, 1, 1),
    )
    _add_point(db_session, baseline.id, site_id, ANNUAL, datetime(2025, 1, 1), 1400000.0)

    resp = svc.build_site_reconciliation(db_session, site)
    row = _row(resp, "estimated_production_year_1")

    assert row.status == "in_active_baseline"
    assert row.active_baseline_value == pytest.approx(1400000.0)


# ===========================================================================
# H11 — a metadata field (P50) sets the schema-expansion hint; never a baseline
# ===========================================================================
def test_h11_metadata_field_sets_schema_expansion(db_session, site, site_id):
    _add_fact(db_session, site_id, "p50_mwh", 1000.0)

    resp = svc.build_site_reconciliation(db_session, site)
    row = _row(resp, "p50_mwh")

    assert resp.schema_expansion_recommended is True
    assert row.baseline_target == "metadata"
    assert row.status == "active_fact"  # metadata is never "in baseline"
    assert row.draft_baseline_value is None
    assert row.active_baseline_value is None


# ===========================================================================
# H12 — an unknown fact gets a catch-all row (category other, target none)
# ===========================================================================
def test_h12_catch_all_row_for_unknown_fact(db_session, site, site_id):
    _add_fact(db_session, site_id, "interconnection_voltage", "12.47kV")

    resp = svc.build_site_reconciliation(db_session, site)

    assert len(resp.rows) == len(RECONCILIATION_CATALOG) + 1
    row = _row(resp, "interconnection_voltage")
    assert row.category == "other"
    assert row.baseline_target == "none"
    assert row.status == "active_fact"
    assert row.accepted_value == "12.47kV"


# ===========================================================================
# H13 — supersession is a history pointer, never a row status
# ===========================================================================
def test_h13_supersedes_pointer_exposed(db_session, site, site_id):
    prior = _add_fact(
        db_session,
        site_id,
        "module_wattage",
        390.0,
        status=FactStatus.retired.value,
    )
    _add_fact(
        db_session,
        site_id,
        "module_wattage",
        400.0,
        supersedes_fact_id=prior.id,
    )

    resp = svc.build_site_reconciliation(db_session, site)
    row = _row(resp, "module_wattage")

    assert row.status == "active_fact"
    assert row.supersedes_fact_id == prior.id
    assert row.candidate_count == 0


# ===========================================================================
# H14 — readiness: full 12 monthly + annual design facts on a draft -> ready
# ===========================================================================
def test_h14_readiness_design_points_full_ready(
    db_session, company_id, site, site_id
):
    for entry in RECONCILIATION_CATALOG:
        if entry.baseline_target == "points_monthly":
            _add_fact(db_session, site_id, entry.canonical_name, 100000.0)
    _add_fact(db_session, site_id, "estimated_production_year_1", 1400000.0)
    _make_baseline(
        db_session,
        company_id,
        site_id,
        DESIGN,
        status=TelemetryBaselineStatus.draft,
        timezone="UTC",
        pto_date=date(2025, 1, 1),
    )

    resp = svc.build_site_reconciliation(db_session, site)

    assert resp.readiness.design_estimate_baseline_status == "draft"
    assert resp.readiness.design_points_ready is True
    assert resp.readiness.design_points_present_months == list(range(1, 13))


# ===========================================================================
# H15 — readiness physics: present facts consumed, reviewer constants remain
# ===========================================================================
def test_h15_readiness_physics_consumes_present_facts(db_session, site, site_id):
    # Empty: required physics field is reported outstanding.
    empty = svc.build_site_reconciliation(db_session, site)
    assert empty.readiness.facts_to_draft_ready is False
    assert "module_wattage" in empty.readiness.missing_required_physics_fields

    # With all four physics facts present, those are no longer "missing"
    # (reviewer-only datasheet constants still keep it not-ready).
    for name in ("module_wattage", "module_quantity", "inverter_wattage", "inverter_quantity"):
        _add_fact(db_session, site_id, name, 100.0)

    filled = svc.build_site_reconciliation(db_session, site)
    assert "module_wattage" not in filled.readiness.missing_required_physics_fields


# ===========================================================================
# H16 — the service writes NOTHING (no inserts, no commits, no pending state)
# ===========================================================================
def test_h16_service_performs_zero_writes(db_session, company_id, site, site_id):
    _add_fact(db_session, site_id, "module_wattage", 400.0)
    _make_baseline(
        db_session,
        company_id,
        site_id,
        DESIGN,
        status=TelemetryBaselineStatus.draft,
        pto_date=date(2025, 1, 1),
    )

    before_facts = db_session.query(ProjectFact).count()
    before_baselines = db_session.query(TelemetryExpectedBaseline).count()
    before_points = db_session.query(TelemetryExpectedBaselinePoint).count()

    svc.build_site_reconciliation(db_session, site)

    # No pending writes were left on the session, and nothing was persisted.
    assert len(db_session.new) == 0
    assert len(db_session.dirty) == 0
    assert len(db_session.deleted) == 0
    assert db_session.query(ProjectFact).count() == before_facts
    assert db_session.query(TelemetryExpectedBaseline).count() == before_baselines
    assert db_session.query(TelemetryExpectedBaselinePoint).count() == before_points


# ===========================================================================
# H17 — catalog canonical names never drift from the live producer field maps
# ===========================================================================
def test_h17_catalog_names_match_points_producer():
    from app.services.telemetry.baseline_points_service import (
        ANNUAL_PRODUCTION_FIELD,
        MONTHLY_PRODUCTION_FIELDS,
    )

    monthly_catalog = {
        e.canonical_name
        for e in RECONCILIATION_CATALOG
        if e.baseline_target == "points_monthly"
    }
    assert monthly_catalog == set(MONTHLY_PRODUCTION_FIELDS)
    assert ANNUAL_PRODUCTION_FIELD in CATALOG_BY_NAME


# ===========================================================================
# Endpoint — auth + payload shape
# ===========================================================================
def test_endpoint_returns_200_payload(
    client, company_member_user_auth_header, db_session, site_id
):
    _add_fact(db_session, site_id, "module_wattage", 400.0)

    resp = client.get(_url(site_id), headers=company_member_user_auth_header)

    assert resp.status_code == 200
    body = resp.json()
    assert body["site_id"] == site_id
    assert len(body["rows"]) >= len(RECONCILIATION_CATALOG)
    assert body["telemetry_reality"]["available"] is False
    assert "readiness" in body
    assert body["help_targets"]


def test_endpoint_requires_permission(
    client, non_system_user_auth_header, db_session, site_id
):
    resp = client.get(_url(site_id), headers=non_system_user_auth_header)

    assert resp.status_code in (401, 403, 404)
