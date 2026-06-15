"""Weather Data Architecture W0 — native weather provenance foundation.

These guard the W0 schema/CRUD contract WITHOUT asserting any new runtime
behavior (W0 is additive only — ``expected_service``, telemetry ingestion, O&M
charts, the scheduler, DD, baselines, and reconciliation are untouched):

* every weather table accepts rows and applies honest defaults;
* measurement semantics default to ``unknown`` and are never guessed — unmapped
  DAS weather is not assumed to be POA/cell;
* weather observations are append/idempotent on ``dedupe_key`` (a re-import is a
  no-op, and existing rows are never mutated);
* the approval ledger is append-only;
* all seven models are registered on ``Base.metadata``;
* no external-provider / BigQuery / Firestore dependency is reintroduced.

Runs against a real test DB; ``company_id`` / ``site_id`` are created directly via
CRUD (overriding the shared HTTP-app-backed fixtures) so no FastAPI lifespan is
spun up.
"""
from __future__ import annotations

import ast
import inspect
from datetime import datetime

import pytest

from app.crud import weather as weather_crud
from app.db.base import Base
from app.models import weather as weather_models
from app.models.weather import (
    ExpectedWeatherProvenance,
    WeatherApprovalAction,
    WeatherApprovalTargetType,
    WeatherCalibrationStatus,
    WeatherConfidence,
    WeatherDeviceMapping,
    WeatherIrradiancePlane,
    WeatherObservation,
    WeatherObservationBatch,
    WeatherObservationBatchKind,
    WeatherSource,
    WeatherSourceApproval,
    WeatherSourceProfile,
    WeatherSourceProfileRole,
    WeatherSourceProfileStatus,
    WeatherSourceType,
    WeatherTemperatureType,
)

TS = datetime(2026, 6, 1, 12, 0)


# ---------------------------------------------------------------------------
# Local FK fixtures
# ---------------------------------------------------------------------------
# The shared ``company_id`` / ``site_id`` fixtures transitively require the
# session-scoped ``client`` fixture, which spins up the full FastAPI lifespan
# (telemetry scheduler, startup tasks) against the live dev DB. We only need a
# valid company/site row to satisfy FKs, so we create them directly via CRUD on
# ``db_session`` — overriding the shared fixtures by name for this module.
@pytest.fixture(scope="module")
def company_id(db_session):
    from app.crud.company import CompanyCRUD
    from tests.unit import samples

    company = CompanyCRUD(db_session).create_item(samples.SETUP_COMPANIES[0])
    return company.id


@pytest.fixture(scope="module")
def site_id(db_session, company_id):
    import copy

    from app.crud.site import SiteCRUD
    from tests.unit import samples

    payload = copy.deepcopy(samples.TEST_SITE_BODY)
    payload["company_id"] = company_id
    site = SiteCRUD(db_session).create_item(payload)
    return site.id


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _make_source(db, company_id, site_id, **kw):
    defaults = dict(
        company_id=company_id,
        site_id=site_id,
        source_type=WeatherSourceType.imported_historical_provider_file,
        display_name="Test weather source",
    )
    defaults.update(kw)
    return weather_crud.WeatherSourceCRUD(db).create(**defaults)


def _make_batch(db, site_id, source_id, **kw):
    defaults = dict(
        site_id=site_id,
        weather_source_id=source_id,
        batch_kind=WeatherObservationBatchKind.file_import,
    )
    defaults.update(kw)
    return weather_crud.WeatherObservationBatchCRUD(db).create(**defaults)


def _obs_row(site_id, batch_id, source_id, *, dedupe_key, metric="irradiance", value=500.0, **kw):
    row = dict(
        site_id=site_id,
        batch_id=batch_id,
        weather_source_id=source_id,
        metric=metric,
        value=value,
        obs_ts=TS,
        dedupe_key=dedupe_key,
    )
    row.update(kw)
    return row


# ===========================================================================
# Sources
# ===========================================================================
def test_create_weather_source_applies_honest_defaults(db_session, company_id, site_id):
    source = _make_source(db_session, company_id, site_id)

    assert source.id is not None
    # No fabricated confidence / modeling claims.
    assert source.is_modeled is False
    assert source.active is True
    assert source.default_confidence == WeatherConfidence.unknown
    assert source.created_at is not None

    listed = weather_crud.WeatherSourceCRUD(db_session).list_for_site(site_id)
    assert source.id in {s.id for s in listed}


# ===========================================================================
# Profiles — versioned by new row, never auto-activated, overlap allowed
# ===========================================================================
def test_profile_defaults_to_draft_no_auto_activation(db_session, company_id, site_id):
    source = _make_source(db_session, company_id, site_id)
    profile = weather_crud.WeatherSourceProfileCRUD(db_session).create(
        site_id=site_id,
        role=WeatherSourceProfileRole.live,
        weather_source_id=source.id,
    )
    assert profile.status == WeatherSourceProfileStatus.draft
    assert profile.priority == 0
    assert profile.fallback_allowed is False
    assert profile.external_modeled_allowed is False
    assert profile.approved_at is None


def test_profiles_overlap_is_allowed_no_single_active_constraint(
    db_session, company_id, site_id
):
    # Two ACTIVE profiles for the same (site, role) must coexist — precedence is
    # expressed by priority, resolution is a future W1 concern.
    crud = weather_crud.WeatherSourceProfileCRUD(db_session)
    src_a = _make_source(db_session, company_id, site_id, display_name="A")
    src_b = _make_source(db_session, company_id, site_id, display_name="B")
    p1 = crud.create(
        site_id=site_id,
        role=WeatherSourceProfileRole.live,
        weather_source_id=src_a.id,
        status=WeatherSourceProfileStatus.active,
        priority=10,
    )
    p2 = crud.create(
        site_id=site_id,
        role=WeatherSourceProfileRole.live,
        weather_source_id=src_b.id,
        status=WeatherSourceProfileStatus.active,
        priority=5,
    )
    assert p1.id != p2.id
    listed = crud.list_for_site(site_id)
    actives = [
        p
        for p in listed
        if p.role == WeatherSourceProfileRole.live
        and p.status == WeatherSourceProfileStatus.active
    ]
    assert {p1.id, p2.id}.issubset({p.id for p in actives})
    # Ordered by priority desc.
    assert listed[0].priority >= listed[-1].priority


# ===========================================================================
# Observations — append/idempotent on dedupe_key
# ===========================================================================
def test_observation_upsert_is_idempotent_on_dedupe_key(
    db_session, company_id, site_id
):
    source = _make_source(db_session, company_id, site_id)
    batch = _make_batch(db_session, site_id, source.id)
    crud = weather_crud.WeatherObservationCRUD(db_session)

    rows = [
        _obs_row(site_id, batch.id, source.id, dedupe_key=f"w0-test-{i}", value=float(i))
        for i in range(3)
    ]
    inserted_first = crud.upsert(rows)
    assert inserted_first == 3

    # Re-importing the SAME keys writes nothing and mutates nothing.
    inserted_second = crud.upsert(rows)
    assert inserted_second == 0

    stored = crud.list_for_site(site_id, metric="irradiance")
    assert len([s for s in stored if s.dedupe_key.startswith("w0-test-")]) == 3


def test_observation_dedupe_unique_constraint_enforced(db_session, company_id, site_id):
    from sqlalchemy.exc import IntegrityError

    source = _make_source(db_session, company_id, site_id)
    batch = _make_batch(db_session, site_id, source.id)

    db_session.add(
        WeatherObservation(**_obs_row(site_id, batch.id, source.id, dedupe_key="w0-dupe"))
    )
    db_session.commit()
    db_session.add(
        WeatherObservation(**_obs_row(site_id, batch.id, source.id, dedupe_key="w0-dupe"))
    )
    with pytest.raises(IntegrityError):
        db_session.commit()
    db_session.rollback()


# ===========================================================================
# Unknown semantics — never guessed
# ===========================================================================
def test_observation_semantics_default_to_unknown(db_session, company_id, site_id):
    source = _make_source(db_session, company_id, site_id)
    batch = _make_batch(db_session, site_id, source.id)
    crud = weather_crud.WeatherObservationCRUD(db_session)
    crud.upsert([_obs_row(site_id, batch.id, source.id, dedupe_key="w0-unknown")])

    obs = next(
        o
        for o in crud.list_for_site(site_id)
        if o.dedupe_key == "w0-unknown"
    )
    # irradiance is NOT assumed to be POA; temperature is NOT assumed cell/ambient.
    assert obs.irradiance_plane == WeatherIrradiancePlane.unknown
    assert obs.temperature_type == WeatherTemperatureType.unknown
    assert obs.confidence == WeatherConfidence.unknown
    assert obs.is_modeled is False


def test_device_mapping_defaults_to_unknown_semantics(db_session, company_id, site_id):
    source = _make_source(
        db_session, company_id, site_id, source_type=WeatherSourceType.das_provider_stream
    )
    mapping = weather_crud.WeatherDeviceMappingCRUD(db_session).create(
        site_id=site_id,
        device_id=None,
        external_device_id="inv-001",
        weather_source_id=source.id,
        metric="irradiance",
        provider_key="poa_irradiance_raw",
    )
    # Existing DAS weather defaults to unknown semantics until explicitly mapped.
    assert mapping.irradiance_plane == WeatherIrradiancePlane.unknown
    assert mapping.temperature_type == WeatherTemperatureType.unknown
    assert mapping.calibration_status == WeatherCalibrationStatus.unknown


# ===========================================================================
# Approval ledger — append-only
# ===========================================================================
def test_approval_ledger_is_append_only(db_session, company_id, site_id):
    source = _make_source(db_session, company_id, site_id)
    profile = weather_crud.WeatherSourceProfileCRUD(db_session).create(
        site_id=site_id,
        role=WeatherSourceProfileRole.live,
        weather_source_id=source.id,
    )
    crud = weather_crud.WeatherSourceApprovalCRUD(db_session)
    crud.record(
        site_id=site_id,
        target_type=WeatherApprovalTargetType.profile,
        target_id=profile.id,
        action=WeatherApprovalAction.approve,
        rationale="looks good",
    )
    crud.record(
        site_id=site_id,
        target_type=WeatherApprovalTargetType.profile,
        target_id=profile.id,
        action=WeatherApprovalAction.revoke,
        rationale="superseded by new sensor",
    )
    ledger = crud.list_for_target(WeatherApprovalTargetType.profile, profile.id)
    assert [e.action for e in ledger] == [
        WeatherApprovalAction.approve,
        WeatherApprovalAction.revoke,
    ]


# ===========================================================================
# Expected-weather provenance — model exists, not written by runtime in W0
# ===========================================================================
def test_expected_weather_provenance_model_is_creatable(
    db_session, company_id, site_id
):
    source = _make_source(db_session, company_id, site_id)
    row = ExpectedWeatherProvenance(
        site_id=site_id,
        weather_source_id=source.id,
        bucket_size="1h",
    )
    db_session.add(row)
    db_session.commit()
    db_session.refresh(row)
    assert row.id is not None
    assert row.is_modeled is False
    assert row.confidence == WeatherConfidence.unknown


# ===========================================================================
# Enum contract — guard against accidental value drift
# ===========================================================================
def test_enum_values_match_spec():
    assert [e.value for e in WeatherSourceType] == [
        "on_site_calibrated_sensor",
        "on_site_weather_station",
        "das_provider_stream",
        "external_modeled_provider",
        "imported_historical_provider_file",
        "imported_weather_station_file",
        "pvsyst_design_weather",
        "manual_approved_weather_assumption",
        "unavailable",
    ]
    assert [e.value for e in WeatherSourceProfileRole] == [
        "live",
        "historical",
        "design",
        "fallback",
    ]
    assert [e.value for e in WeatherSourceProfileStatus] == [
        "draft",
        "in_review",
        "approved",
        "active",
        "superseded",
        "rejected",
    ]
    assert [e.value for e in WeatherObservationBatchKind] == [
        "file_import",
        "provider_pull",
        "manual",
        "telemetry_backfill",
    ]
    assert [e.value for e in WeatherIrradiancePlane] == [
        "poa",
        "ghi",
        "dni",
        "dhi",
        "unknown",
    ]
    assert [e.value for e in WeatherTemperatureType] == [
        "cell",
        "module",
        "ambient",
        "modeled_cell",
        "unknown",
    ]
    assert [e.value for e in WeatherConfidence] == ["high", "medium", "low", "unknown"]
    assert [e.value for e in WeatherCalibrationStatus] == [
        "calibrated",
        "uncalibrated",
        "expired",
        "unknown",
    ]
    assert [e.value for e in WeatherApprovalTargetType] == ["profile", "batch"]
    assert [e.value for e in WeatherApprovalAction] == [
        "approve",
        "reject",
        "revoke",
        "supersede",
    ]


# ===========================================================================
# Registration + guardrails
# ===========================================================================
def test_all_weather_models_registered_on_base():
    expected = {
        "weather_sources",
        "weather_source_profiles",
        "weather_observation_batches",
        "weather_observations",
        "weather_source_approvals",
        "weather_device_mappings",
        "expected_weather_provenance",
    }
    assert expected.issubset(set(Base.metadata.tables))


def _imported_module_names(module) -> set[str]:
    """Collect the dotted names of everything imported by ``module`` (ignores
    docstrings/comments — only real import statements)."""
    tree = ast.parse(inspect.getsource(module))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_weather_module_has_no_forbidden_dependencies():
    # W0 is native PostgreSQL only — no external provider / BigQuery / Firestore /
    # cloud-SDK imports. We inspect actual imports (not prose) so the modules may
    # still *document* what they deliberately avoid.
    forbidden_prefixes = (
        "google.cloud",
        "google.oauth2",
        "firebase_admin",
        "boto3",
        "requests",
    )
    forbidden_substrings = ("bigquery", "firestore")
    for module in (weather_models, weather_crud):
        for name in _imported_module_names(module):
            lname = name.lower()
            assert not any(
                lname == p or lname.startswith(p + ".") for p in forbidden_prefixes
            ), f"forbidden import {name!r} in {module.__name__}"
            assert not any(
                token in lname for token in forbidden_substrings
            ), f"forbidden import {name!r} in {module.__name__}"
