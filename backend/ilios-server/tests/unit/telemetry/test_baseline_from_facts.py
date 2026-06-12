"""DD V2 Phase 2 — promoted ``project_facts`` -> draft baseline bridge.

These guard the honesty + safety contract of
``app.services.telemetry.baseline_from_facts_service`` and its two endpoints:

* a draft is built from ACTIVE/promoted ``project_facts`` (module/inverter) plus
  reviewer-supplied datasheet constants — never from ``SiteAdditionalFieldList``;
* nothing is ever fabricated (a missing/non-numeric required field blocks the
  create and is reported honestly, never defaulted);
* the bridge only ever creates a ``draft`` — it never approves/activates and
  never overwrites an existing active baseline;
* full provenance (per-field source, fact ids, document id, AI confidence) is
  recorded, and re-creating with identical inputs is idempotent while changed
  inputs cut a new version.

The service-level tests use real DB fixtures (``company_id``/``site_id`` cascade
on teardown, so created facts/baselines clean up automatically). The endpoint
tests drive the FastAPI app via the shared ``client`` + system-user auth.
"""
from __future__ import annotations

from datetime import date

import pytest

from app.crud.site_additional_fields_list import SiteAdditionalFieldListCRUD
from app.crud.telemetry_expected import TelemetryExpectedBaselineCRUD
from app.models.project_facts import CanonicalField, FactStatus, ProjectFact
from app.models.telemetry_expected import (
    TelemetryBaselineSource,
    TelemetryBaselineStatus,
    TelemetryBaselineType,
    TelemetryExpectedBaseline,
)
from app.services.telemetry import baseline_from_facts_service as svc
from app.services.telemetry.expected_service import REQUIRED_PHYSICS_FIELDS

WAM = TelemetryBaselineType.weather_adjusted_model

# Reviewer-supplied datasheet constants (no fact source exists today).
REVIEWER_CONSTANTS = {
    "thermal_coefficient_pct": -0.35,
    "power_tolerance_min_pct": 0.0,
    "year_1_degradation_pct": 2.0,
    "annual_degradation_pct": 0.5,
    "cec_efficiency_pct": 98.5,
}

# Unit-plausible fact values (modules in W, inverters in kW).
FACT_VALUES = {
    "module_wattage": 400.0,
    "module_quantity": 1000.0,
    "inverter_wattage": 50.0,
    "inverter_quantity": 4.0,
}

FACT_COLUMNS = set(FACT_VALUES)


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


def _seed_physics_facts(
    db, site_id, *, source_file_id=None, ai_confidence=None, values=None
):
    values = FACT_VALUES if values is None else values
    return {
        name: _add_fact(
            db,
            site_id,
            name,
            val,
            source_file_id=source_file_id,
            ai_confidence=ai_confidence,
        )
        for name, val in values.items()
    }


def _baselines_for(db, site_id):
    return (
        db.query(TelemetryExpectedBaseline)
        .filter(TelemetryExpectedBaseline.site_id == site_id)
        .all()
    )


# ===========================================================================
# Readiness (facts only — reviewer constants are always "missing" here)
# ===========================================================================
def test_readiness_no_facts_reports_all_required_missing(db_session, site_id):
    res = svc.evaluate_readiness(db_session, site_id, WAM)

    assert res.ready is False
    assert res.fields_used == []
    assert res.source_fact_ids == []
    # Every required physics field is outstanding (4 fact cols + 5 constants).
    assert set(res.missing_fields) == set(REQUIRED_PHYSICS_FIELDS)


def test_readiness_with_facts_only_constants_missing(db_session, site_id):
    facts = _seed_physics_facts(db_session, site_id)

    res = svc.evaluate_readiness(db_session, site_id, WAM)

    assert res.ready is False  # the 5 datasheet constants are supplied on create
    assert set(res.missing_fields) == set(REVIEWER_CONSTANTS)
    used = {f.field: f for f in res.fields_used}
    assert set(used) == FACT_COLUMNS
    assert all(f.source == "project_fact" for f in used.values())
    assert used["module_wattage"].value == 400.0
    assert set(res.source_fact_ids) == {f.id for f in facts.values()}


# ===========================================================================
# Create — block path (honest, no row)
# ===========================================================================
def test_create_without_constants_is_not_ready_and_writes_nothing(
    db_session, company_id, site_id
):
    _seed_physics_facts(db_session, site_id)

    result = svc.create_draft_from_facts(
        db_session,
        company_id=company_id,
        site_id=site_id,
        site_timezone="UTC",
        baseline_type=WAM,
        reviewer_values={},  # constants missing
    )

    assert result.readiness.ready is False
    assert result.baseline is None
    assert result.created is False
    assert set(result.readiness.missing_fields) == set(REVIEWER_CONSTANTS)
    assert _baselines_for(db_session, site_id) == []


def test_non_numeric_fact_is_missing_not_guessed(db_session, company_id, site_id):
    # module_wattage arrives as a non-numeric string -> treated as missing
    # (never coerced to a fabricated default), so the create is blocked.
    values = dict(FACT_VALUES)
    values["module_wattage"] = "N/A"
    _seed_physics_facts(db_session, site_id, values=values)

    res = svc.evaluate_readiness(db_session, site_id, WAM)
    assert res.ready is False
    assert "module_wattage" in res.missing_fields
    assert any("not numeric" in w for w in res.warnings)

    result = svc.create_draft_from_facts(
        db_session,
        company_id=company_id,
        site_id=site_id,
        site_timezone="UTC",
        reviewer_values=dict(REVIEWER_CONSTANTS),
    )
    assert result.created is False
    assert result.baseline is None
    assert _baselines_for(db_session, site_id) == []


# ===========================================================================
# Create — ready path (provenance, draft-only)
# ===========================================================================
def test_create_ready_builds_draft_with_full_provenance(
    db_session, company_id, site_id, file, system_user_id
):
    facts = _seed_physics_facts(
        db_session, site_id, source_file_id=file.id, ai_confidence=0.9
    )

    result = svc.create_draft_from_facts(
        db_session,
        company_id=company_id,
        site_id=site_id,
        site_timezone="UTC",
        baseline_type=WAM,
        reviewer_values=dict(REVIEWER_CONSTANTS),
        created_by_user_id=system_user_id,
    )

    assert result.created is True
    assert result.idempotent_existing is False
    b = result.baseline
    assert b is not None

    # DRAFT ONLY — never approved/activated.
    assert b.status == TelemetryBaselineStatus.draft
    assert b.approved_at is None and b.approved_by is None
    assert b.reviewed_at is None and b.reviewed_by is None
    assert b.version == 1
    assert b.created_by_user_id == system_user_id

    # Header provenance.
    assert b.source_type == TelemetryBaselineSource.diligence_ai_parse
    assert b.source_project_fact_id == facts["module_wattage"].id
    assert b.source_document_id == file.document_id  # all facts share one doc

    # Physics columns came from the facts.
    assert b.module_wattage == 400.0
    assert b.inverter_wattage == 50.0
    assert b.cec_efficiency_pct == 98.5  # reviewer-supplied

    # Per-field source map.
    sources = b.model_parameters_json["field_sources"]
    assert sources["module_wattage"]["source"] == "project_fact"
    assert sources["module_wattage"]["fact_id"] == facts["module_wattage"].id
    assert sources["module_wattage"]["document_id"] == file.document_id
    assert sources["cec_efficiency_pct"]["source"] == "reviewer_supplied"
    assert b.model_parameters_json["source_fact_signature"]

    # AI confidence captured only for fact-backed fields.
    assert b.ai_confidence_json["module_wattage"] == 0.9


def test_create_without_source_file_has_null_document(
    db_session, company_id, site_id
):
    # No facts carry a source file -> the header document id is honestly null
    # (the "not exactly one contributing document" branch).
    _seed_physics_facts(db_session, site_id, source_file_id=None)

    result = svc.create_draft_from_facts(
        db_session,
        company_id=company_id,
        site_id=site_id,
        site_timezone="UTC",
        reviewer_values=dict(REVIEWER_CONSTANTS),
    )

    assert result.created is True
    assert result.baseline.source_document_id is None
    assert result.readiness.source_document_ids == []


# ===========================================================================
# Uses project_facts, NOT SiteAdditionalFieldList
# ===========================================================================
def test_site_additional_field_losses_are_ignored(
    db_session, company_id, site_id
):
    # A SiteAdditionalFieldList row with a loss value MUST NOT leak into the
    # draft: the bridge calls create_draft(site_additional=None), so the legacy
    # snapshot never fires and an unsupplied loss stays None.
    SiteAdditionalFieldListCRUD(db_session).create_item(
        {"site_id": site_id, "dc_wiring_loss": 99}
    )
    _seed_physics_facts(db_session, site_id)

    result = svc.create_draft_from_facts(
        db_session,
        company_id=company_id,
        site_id=site_id,
        site_timezone="UTC",
        reviewer_values=dict(REVIEWER_CONSTANTS),  # no dc_loss_pct supplied
    )

    assert result.created is True
    assert result.baseline.dc_loss_pct is None  # NOT 99 from the SAFL snapshot


# ===========================================================================
# Optional loss / soiling / PTO assumptions
# ===========================================================================
def test_losses_soiling_and_pto_are_stored_and_normalized(
    db_session, company_id, site_id
):
    _seed_physics_facts(db_session, site_id)
    reviewer = dict(REVIEWER_CONSTANTS)
    reviewer.update(
        {
            "dc_loss_pct": -2.0,  # sign-normalized to +2
            "soiling_factor": 0.98,
            "pto_date": date(2025, 1, 1),
        }
    )

    result = svc.create_draft_from_facts(
        db_session,
        company_id=company_id,
        site_id=site_id,
        site_timezone="UTC",
        reviewer_values=reviewer,
    )

    b = result.baseline
    assert float(b.dc_loss_pct) == pytest.approx(2.0)  # abs() normalized
    assert float(b.soiling_factor) == pytest.approx(0.98)
    assert b.pto_date == date(2025, 1, 1)
    losses = b.loss_assumptions_json
    assert losses["dc_loss_pct"] == pytest.approx(2.0)
    assert losses["soiling_factor"] == pytest.approx(0.98)


# ===========================================================================
# Idempotency + versioning
# ===========================================================================
def test_identical_inputs_are_idempotent(db_session, company_id, site_id):
    _seed_physics_facts(db_session, site_id)
    kwargs = dict(
        company_id=company_id,
        site_id=site_id,
        site_timezone="UTC",
        reviewer_values=dict(REVIEWER_CONSTANTS),
    )

    first = svc.create_draft_from_facts(db_session, **kwargs)
    second = svc.create_draft_from_facts(db_session, **kwargs)

    assert first.created is True
    assert second.created is False
    assert second.idempotent_existing is True
    assert second.baseline.id == first.baseline.id
    assert len(_baselines_for(db_session, site_id)) == 1


def test_changed_constant_cuts_a_new_version(db_session, company_id, site_id):
    _seed_physics_facts(db_session, site_id)
    first = svc.create_draft_from_facts(
        db_session,
        company_id=company_id,
        site_id=site_id,
        site_timezone="UTC",
        reviewer_values=dict(REVIEWER_CONSTANTS),
    )

    changed = dict(REVIEWER_CONSTANTS)
    changed["cec_efficiency_pct"] = 97.0  # different datasheet value
    second = svc.create_draft_from_facts(
        db_session,
        company_id=company_id,
        site_id=site_id,
        site_timezone="UTC",
        reviewer_values=changed,
    )

    assert second.created is True
    assert second.baseline.id != first.baseline.id
    assert first.baseline.version == 1
    assert second.baseline.version == 2
    assert len(_baselines_for(db_session, site_id)) == 2


def test_active_baseline_is_never_overwritten(db_session, company_id, site_id):
    # An already-active baseline must survive untouched, and its signature must
    # NOT short-circuit the create (idempotency is scoped to drafts only).
    active = TelemetryExpectedBaseline(
        company_id=company_id,
        site_id=site_id,
        baseline_name="active baseline",
        baseline_type=WAM,
        status=TelemetryBaselineStatus.active,
        version=1,
    )
    db_session.add(active)
    db_session.commit()
    db_session.refresh(active)
    active_id = active.id

    _seed_physics_facts(db_session, site_id)
    result = svc.create_draft_from_facts(
        db_session,
        company_id=company_id,
        site_id=site_id,
        site_timezone="UTC",
        reviewer_values=dict(REVIEWER_CONSTANTS),
    )

    assert result.created is True
    assert result.baseline.status == TelemetryBaselineStatus.draft
    assert result.baseline.id != active_id

    db_session.refresh(active)
    assert active.status == TelemetryBaselineStatus.active  # untouched
    still_active = TelemetryExpectedBaselineCRUD(db_session).get_active(site_id, WAM)
    assert still_active.id == active_id


def test_idempotency_does_not_match_a_non_draft(db_session, company_id, site_id):
    # A draft promoted out of `draft` must not be reused: the same inputs cut a
    # brand-new draft (approved/active baselines are never short-circuited).
    _seed_physics_facts(db_session, site_id)
    kwargs = dict(
        company_id=company_id,
        site_id=site_id,
        site_timezone="UTC",
        reviewer_values=dict(REVIEWER_CONSTANTS),
    )
    first = svc.create_draft_from_facts(db_session, **kwargs)

    # Promote the first draft out of `draft`.
    first.baseline.status = TelemetryBaselineStatus.approved
    db_session.commit()

    second = svc.create_draft_from_facts(db_session, **kwargs)
    assert second.created is True
    assert second.idempotent_existing is False
    assert second.baseline.id != first.baseline.id


# ===========================================================================
# Guardrails — calc math + legacy isolation untouched
# ===========================================================================
def test_required_physics_field_set_is_unchanged():
    # The bridge consumes the calc's required-field contract; it must not alter
    # it (changing the calc math is explicitly out of scope).
    assert set(REQUIRED_PHYSICS_FIELDS) == {
        "module_wattage",
        "module_quantity",
        "inverter_wattage",
        "inverter_quantity",
        "thermal_coefficient_pct",
        "power_tolerance_min_pct",
        "year_1_degradation_pct",
        "annual_degradation_pct",
        "cec_efficiency_pct",
    }


def test_service_does_not_reintroduce_bigquery_firestore_or_docai():
    import inspect

    source = inspect.getsource(svc).lower()
    for forbidden in ("bigquery", "firestore", "google.cloud", "docai"):
        assert forbidden not in source


# ===========================================================================
# Endpoints
# ===========================================================================
def _readiness_url(site_id):
    return f"/api/telemetry/v2/sites/{site_id}/expected-baseline/readiness-from-facts"


def _create_url(site_id):
    return (
        f"/api/telemetry/v2/sites/{site_id}/expected-baseline/create-draft-from-facts"
    )


def test_endpoint_readiness_from_facts(
    client, system_user_auth_header, db_session, site_id
):
    _seed_physics_facts(db_session, site_id)

    resp = client.get(_readiness_url(site_id), headers=system_user_auth_header)

    assert resp.status_code == 200
    body = resp.json()
    assert body["ready"] is False
    assert set(body["missing_fields"]) == set(REVIEWER_CONSTANTS)
    assert {f["field"] for f in body["fields_used"]} == FACT_COLUMNS


def test_endpoint_create_draft_success_then_idempotent(
    client, system_user_auth_header, db_session, site_id
):
    _seed_physics_facts(db_session, site_id)
    payload = dict(REVIEWER_CONSTANTS)

    first = client.post(
        _create_url(site_id), json=payload, headers=system_user_auth_header
    )
    assert first.status_code == 201
    body = first.json()
    assert body["status"] == "draft"
    assert body["ready"] is True
    assert body["created"] is True
    draft_id = body["draft_baseline_id"]
    assert draft_id is not None

    second = client.post(
        _create_url(site_id), json=payload, headers=system_user_auth_header
    )
    assert second.status_code == 200  # idempotent reuse
    second_body = second.json()
    assert second_body["idempotent_existing"] is True
    assert second_body["draft_baseline_id"] == draft_id


def test_endpoint_create_missing_constants_returns_422_review_required(
    client, system_user_auth_header, db_session, site_id
):
    _seed_physics_facts(db_session, site_id)

    resp = client.post(
        _create_url(site_id), json={}, headers=system_user_auth_header
    )

    assert resp.status_code == 422
    body = resp.json()
    assert body["status"] == "review_required"
    assert body["ready"] is False
    assert body["draft_baseline_id"] is None
    assert set(body["missing_fields"]) == set(REVIEWER_CONSTANTS)
    assert _baselines_for(db_session, site_id) == []


def test_endpoint_requires_telemetry_admin(
    client, non_system_user_auth_header, site_id
):
    resp = client.get(
        _readiness_url(site_id), headers=non_system_user_auth_header
    )
    assert resp.status_code in (401, 403, 404)


def test_legacy_create_baseline_endpoint_is_deprecated_and_warns(
    client, system_user_auth_header, db_session, site_id, caplog
):
    """DD V2 Phase 5B — the legacy SAFL-snapshot create endpoint still works (201) but is
    now marked deprecated and logs a warning steering callers to create-draft-from-facts.

    A ``draft`` row is created (the partial unique index only constrains ``active`` rows,
    so this never collides with other drafts on the shared site).
    """
    import logging

    url = f"/api/telemetry/v2/sites/{site_id}/expected-baselines"
    with caplog.at_level(logging.WARNING, logger="app.routers.telemetry.v2"):
        resp = client.post(
            url,
            json={"baseline_name": "Phase 5B legacy deprecation check"},
            headers=system_user_auth_header,
        )

    assert resp.status_code == 201
    assert any(
        "deprecated" in record.getMessage().lower()
        and "create-draft-from-facts" in record.getMessage()
        for record in caplog.records
    ), "expected a deprecation warning pointing to create-draft-from-facts"
