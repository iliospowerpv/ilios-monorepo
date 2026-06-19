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

from datetime import date, datetime

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

# Reviewer-supplied inputs that have no project_fact source today: the five
# module/inverter datasheet constants PLUS the PTO date, which is now REQUIRED for
# the weather-adjusted model (without it the expected curve is NULL for every
# bucket). Service-path tests pass these straight through (the ``date`` object is
# fine); endpoint tests must JSON-encode ``pto_date`` (see ``_json_payload``).
REVIEWER_CONSTANTS = {
    "thermal_coefficient_pct": -0.35,
    "power_tolerance_min_pct": 0.0,
    "year_1_degradation_pct": 2.0,
    "annual_degradation_pct": 0.5,
    "cec_efficiency_pct": 98.5,
    "pto_date": date(2025, 1, 1),
}


def _json_payload(**overrides):
    """``REVIEWER_CONSTANTS`` as a JSON-safe POST body (``pto_date`` as ISO str)."""
    payload = {k: v for k, v in REVIEWER_CONSTANTS.items() if k != "pto_date"}
    payload["pto_date"] = REVIEWER_CONSTANTS["pto_date"].isoformat()
    payload.update(overrides)
    return payload


def _constants_without_pto():
    """The datasheet constants only — used to assert the PTO requirement."""
    return {k: v for k, v in REVIEWER_CONSTANTS.items() if k != "pto_date"}


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
    # Every required physics field is outstanding (4 fact cols + 5 constants),
    # plus the now-required PTO date for the weather-adjusted model.
    assert set(res.missing_fields) == set(REQUIRED_PHYSICS_FIELDS) | {"pto_date"}


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
    payload = _json_payload()

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


# ===========================================================================
# Structured field blockers (Scope A) — descriptive, never change `ready`
# ===========================================================================
def _blockers_by_field(res):
    return {b.field: b for b in res.field_blockers}


def test_readiness_field_blockers_cover_every_input(db_session, site_id):
    _seed_physics_facts(db_session, site_id)

    res = svc.evaluate_readiness(db_session, site_id, WAM)
    blockers = _blockers_by_field(res)

    # All 4 facts + 5 reviewer constants + 4 losses + soiling + pto = 15 inputs.
    assert len(res.field_blockers) == 15

    # Fact-backed numeric inputs are satisfied + informational.
    assert blockers["module_wattage"].source_status == svc.SourceStatus.ACTIVE_FACT
    assert blockers["module_wattage"].blocking_level == svc.BlockingLevel.INFORMATIONAL
    assert blockers["module_wattage"].current_normalized_value == 400.0

    # Reviewer constants are needed (not yet supplied here) and block the draft.
    assert (
        blockers["cec_efficiency_pct"].source_status
        == svc.SourceStatus.REVIEWER_SUPPLIED_NEEDED
    )
    assert (
        blockers["cec_efficiency_pct"].blocking_level
        == svc.BlockingLevel.BLOCKS_DRAFT
    )

    # Optional losses carry their default, never blocking.
    assert (
        blockers["dc_loss_pct"].source_status
        == svc.SourceStatus.OPTIONAL_DEFAULT_APPLIED
    )
    assert blockers["dc_loss_pct"].blocking_level == svc.BlockingLevel.INFORMATIONAL
    assert blockers["dc_loss_pct"].default_value == 0.0
    assert blockers["soiling_factor"].default_value == 1.0

    # PTO is REQUIRED for the weather-adjusted model: a missing PTO blocks the
    # draft itself (the expected curve would be NULL for every bucket without it).
    assert (
        blockers["pto_date"].source_status
        == svc.SourceStatus.REVIEWER_SUPPLIED_NEEDED
    )
    assert blockers["pto_date"].blocking_level == svc.BlockingLevel.BLOCKS_DRAFT


def test_missing_fact_blocker_recommends_promotion(db_session, site_id):
    res = svc.evaluate_readiness(db_session, site_id, WAM)
    blockers = _blockers_by_field(res)

    mw = blockers["module_wattage"]
    assert mw.source_status == svc.SourceStatus.MISSING
    assert mw.blocking_level == svc.BlockingLevel.BLOCKS_DRAFT
    assert mw.recommended_action and "Promote" in mw.recommended_action


def test_non_numeric_wattage_blocker_carries_normalization_proposal(
    db_session, site_id
):
    values = dict(FACT_VALUES)
    values["module_wattage"] = "340 Wp"
    _seed_physics_facts(db_session, site_id, values=values)

    res = svc.evaluate_readiness(db_session, site_id, WAM)
    mw = _blockers_by_field(res)["module_wattage"]

    assert mw.source_status == svc.SourceStatus.ACTIVE_FACT_NON_NUMERIC
    assert mw.blocking_level == svc.BlockingLevel.BLOCKS_DRAFT
    assert mw.current_raw_value == "340 Wp"
    # A non-blocked proposal is surfaced so the reviewer can confirm it.
    assert mw.normalization is not None
    assert mw.normalization.blocked is False
    assert mw.normalization.proposed_value == 400.0 or mw.normalization.proposed_value == 340.0


def test_non_numeric_quantity_is_never_normalizable(db_session, site_id):
    values = dict(FACT_VALUES)
    values["module_quantity"] = "lots"
    _seed_physics_facts(db_session, site_id, values=values)

    res = svc.evaluate_readiness(db_session, site_id, WAM)
    mq = _blockers_by_field(res)["module_quantity"]

    assert mq.source_status == svc.SourceStatus.ACTIVE_FACT_NON_NUMERIC
    assert mq.blocking_level == svc.BlockingLevel.BLOCKS_DRAFT
    assert mq.normalization is None  # counts are unitless — never normalized
    assert "module_quantity" in res.missing_fields


# ===========================================================================
# Reviewer-confirmed unit normalization (Scope B/C) — never silent, facts intact
# ===========================================================================
def _norm_payload(fact, raw, confirmed, *, allow_conversion=False):
    return {
        "module_wattage": {
            "confirmed_value": confirmed,
            "raw_value": raw,
            "source_fact_id": fact.id,
            "allow_conversion": allow_conversion,
        }
    }


def test_confirmed_strip_creates_draft_and_leaves_fact_untouched(
    db_session, company_id, site_id, file, system_user_id
):
    values = dict(FACT_VALUES)
    values["module_wattage"] = "340 Wp"
    facts = _seed_physics_facts(db_session, site_id, source_file_id=file.id, values=values)
    mw_fact = facts["module_wattage"]

    reviewer = dict(REVIEWER_CONSTANTS)
    reviewer["normalizations"] = _norm_payload(mw_fact, "340 Wp", 340.0)

    result = svc.create_draft_from_facts(
        db_session,
        company_id=company_id,
        site_id=site_id,
        site_timezone="UTC",
        reviewer_values=reviewer,
        created_by_user_id=system_user_id,
    )

    assert result.created is True
    b = result.baseline
    assert float(b.module_wattage) == pytest.approx(340.0)

    # Provenance records the normalized source explicitly.
    src = b.model_parameters_json["field_sources"]["module_wattage"]
    assert src["source"] == "project_fact_normalized"
    assert src["normalization"]["from_unit"] == "wp"
    assert src["normalization"]["to_unit"] == "W"
    assert src["normalization"]["method"] == "unit_strip"
    assert src["normalization"]["normalized_value"] == pytest.approx(340.0)
    assert src["normalization"]["confirmed_by_user_id"] == system_user_id

    # The project_fact row itself is NEVER mutated.
    db_session.refresh(mw_fact)
    assert mw_fact.value == {"v": "340 Wp"}


def test_normalization_without_confirmation_stays_missing(
    db_session, company_id, site_id
):
    values = dict(FACT_VALUES)
    values["module_wattage"] = "340 Wp"
    _seed_physics_facts(db_session, site_id, values=values)

    result = svc.create_draft_from_facts(
        db_session,
        company_id=company_id,
        site_id=site_id,
        site_timezone="UTC",
        reviewer_values=dict(REVIEWER_CONSTANTS),  # no normalizations
    )

    assert result.created is False
    assert "module_wattage" in result.readiness.missing_fields
    assert _baselines_for(db_session, site_id) == []


def test_conversion_requires_explicit_allow_conversion(
    db_session, company_id, site_id
):
    values = dict(FACT_VALUES)
    values["module_wattage"] = "0.34 kW"  # needs W<-kW conversion
    facts = _seed_physics_facts(db_session, site_id, values=values)
    mw_fact = facts["module_wattage"]

    # Without allow_conversion the proposal is rejected -> stays missing.
    reviewer = dict(REVIEWER_CONSTANTS)
    reviewer["normalizations"] = _norm_payload(
        mw_fact, "0.34 kW", 340.0, allow_conversion=False
    )
    blocked = svc.create_draft_from_facts(
        db_session,
        company_id=company_id,
        site_id=site_id,
        site_timezone="UTC",
        reviewer_values=reviewer,
    )
    assert blocked.created is False
    assert "module_wattage" in blocked.readiness.missing_fields

    # With explicit conversion confirmation it applies.
    reviewer["normalizations"] = _norm_payload(
        mw_fact, "0.34 kW", 340.0, allow_conversion=True
    )
    ok = svc.create_draft_from_facts(
        db_session,
        company_id=company_id,
        site_id=site_id,
        site_timezone="UTC",
        reviewer_values=reviewer,
    )
    assert ok.created is True
    assert float(ok.baseline.module_wattage) == pytest.approx(340.0)


def test_stale_source_fact_id_confirmation_is_rejected(
    db_session, company_id, site_id
):
    values = dict(FACT_VALUES)
    values["module_wattage"] = "340 Wp"
    facts = _seed_physics_facts(db_session, site_id, values=values)

    reviewer = dict(REVIEWER_CONSTANTS)
    reviewer["normalizations"] = {
        "module_wattage": {
            "confirmed_value": 340.0,
            "raw_value": "340 Wp",
            "source_fact_id": facts["module_wattage"].id + 9999,  # stale
            "allow_conversion": False,
        }
    }

    result = svc.create_draft_from_facts(
        db_session,
        company_id=company_id,
        site_id=site_id,
        site_timezone="UTC",
        reviewer_values=reviewer,
    )
    assert result.created is False
    assert "module_wattage" in result.readiness.missing_fields


def test_stale_raw_value_confirmation_is_rejected(db_session, company_id, site_id):
    values = dict(FACT_VALUES)
    values["module_wattage"] = "340 Wp"
    facts = _seed_physics_facts(db_session, site_id, values=values)

    reviewer = dict(REVIEWER_CONSTANTS)
    reviewer["normalizations"] = _norm_payload(
        facts["module_wattage"], "999 Wp", 340.0  # raw drifted from the fact
    )

    result = svc.create_draft_from_facts(
        db_session,
        company_id=company_id,
        site_id=site_id,
        site_timezone="UTC",
        reviewer_values=reviewer,
    )
    assert result.created is False
    assert "module_wattage" in result.readiness.missing_fields


def test_missing_source_fact_id_confirmation_is_rejected(db_session, company_id, site_id):
    """A confirmation without its source-fact anchor can't be proven current → rejected."""
    values = dict(FACT_VALUES)
    values["module_wattage"] = "340 Wp"
    _seed_physics_facts(db_session, site_id, values=values)

    reviewer = dict(REVIEWER_CONSTANTS)
    reviewer["normalizations"] = {
        "module_wattage": {
            "confirmed_value": 340.0,
            "raw_value": "340 Wp",
            # source_fact_id intentionally omitted
            "allow_conversion": False,
        }
    }

    result = svc.create_draft_from_facts(
        db_session,
        company_id=company_id,
        site_id=site_id,
        site_timezone="UTC",
        reviewer_values=reviewer,
    )
    assert result.created is False
    assert "module_wattage" in result.readiness.missing_fields
    assert _baselines_for(db_session, site_id) == []


def test_missing_raw_value_confirmation_is_rejected(db_session, company_id, site_id):
    """A confirmation without the original raw value it was based on → rejected."""
    values = dict(FACT_VALUES)
    values["module_wattage"] = "340 Wp"
    facts = _seed_physics_facts(db_session, site_id, values=values)

    reviewer = dict(REVIEWER_CONSTANTS)
    reviewer["normalizations"] = {
        "module_wattage": {
            "confirmed_value": 340.0,
            # raw_value intentionally omitted
            "source_fact_id": facts["module_wattage"].id,
            "allow_conversion": False,
        }
    }

    result = svc.create_draft_from_facts(
        db_session,
        company_id=company_id,
        site_id=site_id,
        site_timezone="UTC",
        reviewer_values=reviewer,
    )
    assert result.created is False
    assert "module_wattage" in result.readiness.missing_fields
    assert _baselines_for(db_session, site_id) == []


def test_confirmed_value_mismatch_is_rejected(db_session, company_id, site_id):
    values = dict(FACT_VALUES)
    values["module_wattage"] = "340 Wp"
    facts = _seed_physics_facts(db_session, site_id, values=values)

    reviewer = dict(REVIEWER_CONSTANTS)
    reviewer["normalizations"] = _norm_payload(
        facts["module_wattage"], "340 Wp", 999.0  # disagrees with server recompute
    )

    result = svc.create_draft_from_facts(
        db_session,
        company_id=company_id,
        site_id=site_id,
        site_timezone="UTC",
        reviewer_values=reviewer,
    )
    assert result.created is False
    assert "module_wattage" in result.readiness.missing_fields


def test_identical_normalized_inputs_are_idempotent(
    db_session, company_id, site_id
):
    values = dict(FACT_VALUES)
    values["module_wattage"] = "340 Wp"
    facts = _seed_physics_facts(db_session, site_id, values=values)
    reviewer = dict(REVIEWER_CONSTANTS)
    reviewer["normalizations"] = _norm_payload(facts["module_wattage"], "340 Wp", 340.0)
    kwargs = dict(
        company_id=company_id,
        site_id=site_id,
        site_timezone="UTC",
        reviewer_values=reviewer,
    )

    first = svc.create_draft_from_facts(db_session, **kwargs)
    second = svc.create_draft_from_facts(db_session, **kwargs)

    assert first.created is True
    assert second.created is False
    assert second.idempotent_existing is True
    assert len(_baselines_for(db_session, site_id)) == 1


# ===========================================================================
# Endpoints — field_blockers + normalization payload
# ===========================================================================
def test_endpoint_readiness_includes_field_blockers(
    client, system_user_auth_header, db_session, site_id
):
    _seed_physics_facts(db_session, site_id)

    resp = client.get(_readiness_url(site_id), headers=system_user_auth_header)

    assert resp.status_code == 200
    body = resp.json()
    blockers = {b["field"]: b for b in body["field_blockers"]}
    assert len(blockers) == 15
    assert blockers["module_wattage"]["source_status"] == "active_fact"
    assert blockers["cec_efficiency_pct"]["blocking_level"] == "blocks_draft_baseline"
    assert blockers["pto_date"]["source_status"] == "reviewer_supplied_needed"
    assert blockers["pto_date"]["blocking_level"] == "blocks_draft_baseline"


def test_endpoint_create_with_normalization(
    client, system_user_auth_header, db_session, site_id
):
    values = dict(FACT_VALUES)
    values["module_wattage"] = "340 Wp"
    facts = _seed_physics_facts(db_session, site_id, values=values)

    payload = _json_payload(
        normalizations={
            "module_wattage": {
                "confirmed_value": 340.0,
                "raw_value": "340 Wp",
                "source_fact_id": facts["module_wattage"].id,
                "allow_conversion": False,
            }
        }
    )

    resp = client.post(
        _create_url(site_id), json=payload, headers=system_user_auth_header
    )

    assert resp.status_code == 201
    body = resp.json()
    assert body["status"] == "draft"
    assert body["ready"] is True
    mw = next(f for f in body["fields_used"] if f["field"] == "module_wattage")
    assert mw["source"] == "project_fact_normalized"
    assert mw["value"] == pytest.approx(340.0)


def test_endpoint_create_with_bad_normalization_returns_422(
    client, system_user_auth_header, db_session, site_id
):
    values = dict(FACT_VALUES)
    values["module_wattage"] = "340 Wp"
    facts = _seed_physics_facts(db_session, site_id, values=values)

    payload = _json_payload(
        normalizations={
            "module_wattage": {
                "confirmed_value": 999.0,  # mismatch -> rejected
                "raw_value": "340 Wp",
                "source_fact_id": facts["module_wattage"].id,
                "allow_conversion": False,
            }
        }
    )

    resp = client.post(
        _create_url(site_id), json=payload, headers=system_user_auth_header
    )

    assert resp.status_code == 422
    body = resp.json()
    assert body["status"] == "review_required"
    assert "module_wattage" in body["missing_fields"]
    assert _baselines_for(db_session, site_id) == []


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

    # Contract: the route itself is flagged deprecated in the OpenAPI schema
    # (not only logged), so generated clients/docs surface the deprecation.
    legacy_routes = [
        r
        for r in client.app.routes
        if getattr(r, "path", None)
        == "/api/telemetry/v2/sites/{site_id}/expected-baselines"
        and "POST" in (getattr(r, "methods", None) or set())
    ]
    assert legacy_routes, "legacy create-baseline POST route not found"
    assert all(
        getattr(r, "deprecated", False) for r in legacy_routes
    ), "legacy create-baseline route must be marked deprecated=True"


# ===========================================================================
# PTO is REQUIRED for the weather-adjusted model (DD V2 — Site 4 fix)
# ===========================================================================
# Background: without a PTO date the weather-adjusted expected curve is NULL for
# every bucket (production is suppressed before PTO), so the draft is useless.
# PTO is therefore a hard requirement for ``weather_adjusted_model`` — never a
# silent "optional adjustment". Other baseline types keep PTO informational.
def test_pto_required_blocks_create_for_weather_adjusted_model(
    db_session, company_id, site_id
):
    """All datasheet constants present but no PTO -> WAM draft is blocked, nothing
    is written, and ``pto_date`` is the sole outstanding field."""
    _seed_physics_facts(db_session, site_id)

    result = svc.create_draft_from_facts(
        db_session,
        company_id=company_id,
        site_id=site_id,
        site_timezone="UTC",
        baseline_type=WAM,
        reviewer_values=_constants_without_pto(),
    )

    assert result.created is False
    assert result.readiness.ready is False
    assert result.readiness.missing_fields == ["pto_date"]
    assert _baselines_for(db_session, site_id) == []


def test_pto_present_creates_draft_carrying_pto_date(
    db_session, company_id, site_id
):
    """Facts + datasheet constants + PTO -> a draft is created and it carries the
    reviewer-supplied PTO date verbatim."""
    _seed_physics_facts(db_session, site_id)

    result = svc.create_draft_from_facts(
        db_session,
        company_id=company_id,
        site_id=site_id,
        site_timezone="UTC",
        baseline_type=WAM,
        reviewer_values=dict(REVIEWER_CONSTANTS),  # includes the required pto_date
    )

    assert result.created is True
    assert result.readiness.ready is True
    assert result.baseline.status == TelemetryBaselineStatus.draft
    assert result.baseline.pto_date == REVIEWER_CONSTANTS["pto_date"]


def test_pto_not_required_for_non_weather_adjusted_types(db_session, site_id):
    """The required-PTO rule is specific to the WAM. For ``design_estimate`` PTO
    stays informational (pre-PTO suppressed), never in ``missing_fields`` and
    never blocking the draft."""
    _seed_physics_facts(db_session, site_id)

    res = svc.evaluate_readiness(
        db_session, site_id, TelemetryBaselineType.design_estimate
    )

    blockers = {b.field: b for b in res.field_blockers}
    assert "pto_date" not in res.missing_fields
    assert (
        blockers["pto_date"].source_status
        == svc.SourceStatus.PRE_PTO_EXPECTED_SUPPRESSED
    )
    assert blockers["pto_date"].blocking_level == svc.BlockingLevel.BLOCKS_EXPECTED


def test_endpoint_create_missing_pto_returns_422_review_required(
    client, system_user_auth_header, db_session, site_id
):
    """The HTTP create endpoint rejects a WAM draft with no PTO: 422,
    ``review_required``, ``pto_date`` the only outstanding field, nothing written."""
    _seed_physics_facts(db_session, site_id)

    resp = client.post(
        _create_url(site_id),
        json=_constants_without_pto(),  # all numeric -> JSON-safe, no pto_date
        headers=system_user_auth_header,
    )

    assert resp.status_code == 422
    body = resp.json()
    assert body["status"] == "review_required"
    assert body["ready"] is False
    assert body.get("draft_baseline_id") is None
    assert body["missing_fields"] == ["pto_date"]
    assert _baselines_for(db_session, site_id) == []


# ===========================================================================
# Activation effective-from semantics (DD V2 — Site 4 fix)
# ===========================================================================
# First activation of a weather-adjusted baseline (no prior active) backdates
# ``active_from`` to the PTO date so the trailing O&M window is covered. A
# replacement activation instead takes effect at ``now`` and closes the prior
# row at ``now`` (history is never rewritten).
def _make_baseline(db_session, company_id, site_id, **overrides):
    fields = dict(
        company_id=company_id,
        site_id=site_id,
        baseline_name="wam-test",
        baseline_type=WAM,
        status=TelemetryBaselineStatus.approved,
        version=1,
        pto_date=date(2026, 5, 11),
    )
    fields.update(overrides)
    baseline = TelemetryExpectedBaseline(**fields)
    db_session.add(baseline)
    db_session.commit()
    db_session.refresh(baseline)
    return baseline


def test_first_activation_backdates_active_from_to_pto(
    db_session, company_id, site_id, system_user_id
):
    crud = TelemetryExpectedBaselineCRUD(db_session)
    baseline = _make_baseline(db_session, company_id, site_id)

    activated = crud.activate(baseline, user_id=system_user_id)

    assert activated.status == TelemetryBaselineStatus.active
    # date -> naive-UTC midnight; covers the whole post-PTO O&M window.
    assert activated.active_from == datetime(2026, 5, 11)
    assert activated.active_to is None
    assert activated.supersedes_baseline_id is None


def test_replacement_activation_uses_now_and_closes_prior(
    db_session, company_id, site_id, system_user_id
):
    crud = TelemetryExpectedBaselineCRUD(db_session)
    prior = _make_baseline(
        db_session,
        company_id,
        site_id,
        baseline_name="prior",
        status=TelemetryBaselineStatus.active,
        version=1,
        active_from=datetime(2026, 5, 11),
    )
    prior_id = prior.id
    replacement = _make_baseline(
        db_session,
        company_id,
        site_id,
        baseline_name="replacement",
        status=TelemetryBaselineStatus.approved,
        version=2,
    )

    before = datetime.utcnow()
    activated = crud.activate(replacement, user_id=system_user_id)
    after = datetime.utcnow()

    assert activated.status == TelemetryBaselineStatus.active
    # A replacement takes effect at *now*, never backdated to PTO.
    assert activated.active_from != datetime(2026, 5, 11)
    assert before <= activated.active_from <= after
    assert activated.supersedes_baseline_id == prior_id

    db_session.refresh(prior)
    assert prior.status == TelemetryBaselineStatus.superseded
    assert prior.active_to is not None
    assert before <= prior.active_to <= after
