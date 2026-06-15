"""Weather Data Architecture W2 — historical weather import / backfill.

These guard the W2 service contract on top of the W0 schema and the W1 resolver:

* import is **all-or-nothing** (one invalid row ⇒ nothing is written) and
  **idempotent** (re-importing the same window inserts nothing);
* GHI/DNI/DHI irradiance and ambient temperature are STORED but disclosed as
  not physics-usable — never converted to POA / cell;
* modeled rows are flagged, never hidden;
* readiness reports honest coverage / gaps / unknown-semantics and blocks replay
  unless an active historical policy governs the full window with usable inputs;
* the profile lifecycle creates DRAFT policies and only ``approve`` activates
  them (so the UNCHANGED resolver ``_select_active_profile`` picks them up);
* every emitted W2 indicator/blocking key has a glossary entry;
* no external-provider / BigQuery / Firestore dependency is introduced and the
  app imports cleanly with the weather router registered.

DB-backed cases create their own company/site directly via CRUD (overriding the
shared HTTP-app-backed fixtures) so no FastAPI lifespan is spun up. Each test that
writes uses its OWN site + source so cases never contaminate each other.
"""
from __future__ import annotations

import ast
import copy
import inspect
import itertools
from datetime import datetime

import pytest

from app.crud import weather as weather_crud
from app.helpers.telemetry.expected_glossary import EXPECTED_GLOSSARY
from app.models.weather import (
    WeatherApprovalAction,
    WeatherConfidence,
    WeatherIrradiancePlane,
    WeatherObservationBatchKind,
    WeatherSourceProfileRole,
    WeatherSourceProfileStatus,
    WeatherSourceType,
    WeatherTemperatureType,
)
from app.schema.weather import (
    HistoricalImportRequest,
    HistoricalProfileCreateRequest,
    WeatherImportRow,
)
from app.services.weather import bucketing as bucketing_mod
from app.services.weather import historical_weather_import_service as import_svc
from app.services.weather import weather_profile_service as profile_svc
from app.services.weather import weather_readiness_service as readiness_svc
from app.services.weather import weather_resolver as wr
from app.services.weather.historical_weather_import_service import (
    NormalizedObservation,
    WeatherImportValidationError,
    build_dedupe_key,
    preview_import,
    run_historical_import,
    validate_rows,
)
from app.services.weather.weather_profile_service import (
    WeatherProfileActionError,
    apply_profile_action,
    create_historical_profile,
)
from app.services.weather.weather_readiness_service import (
    CELL_TEMPERATURE_METRIC,
    IRRADIANCE_METRIC,
    compute_weather_readiness,
)

_NAME_SEQ = itertools.count(1)


# ---------------------------------------------------------------------------
# Local FK fixtures (created via CRUD — no FastAPI lifespan).
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def company_id(db_session):
    from app.crud.company import CompanyCRUD
    from tests.unit import samples

    # Unique name/email so this module never collides with other test modules
    # that also create the shared sample company in the same DB session.
    payload = copy.deepcopy(samples.SETUP_COMPANIES[0])
    suffix = next(_NAME_SEQ)
    payload["name"] = f"{payload['name']} W2Co-{suffix}"
    if payload.get("email"):
        local, _, domain = payload["email"].partition("@")
        payload["email"] = f"{local}+w2co{suffix}@{domain or 'example.com'}"
    company = CompanyCRUD(db_session).create_item(payload)
    return company.id


def _make_site(db_session, company_id) -> int:
    """Create a FRESH site (unique name) so writing tests stay isolated."""
    from app.crud.site import SiteCRUD
    from tests.unit import samples

    payload = copy.deepcopy(samples.TEST_SITE_BODY)
    payload["company_id"] = company_id
    payload["name"] = f"{payload['name']} W2-{next(_NAME_SEQ)}"
    return SiteCRUD(db_session).create_item(payload).id


@pytest.fixture()
def site_id(db_session, company_id) -> int:
    return _make_site(db_session, company_id)


def _make_source(db_session, site_id, **kw):
    defaults = dict(
        site_id=site_id,
        company_id=None,
        source_type=WeatherSourceType.imported_historical_provider_file,
        display_name="W2 historical source",
        default_confidence=WeatherConfidence.high,
    )
    defaults.update(kw)
    return weather_crud.WeatherSourceCRUD(db_session).create(**defaults)


def _row(ts, metric, value, *, plane=WeatherIrradiancePlane.unknown,
         temp=WeatherTemperatureType.unknown, is_modeled=False,
         confidence=WeatherConfidence.high):
    return WeatherImportRow(
        timestamp=ts,
        metric=metric,
        value=value,
        irradiance_plane=plane,
        temperature_type=temp,
        is_modeled=is_modeled,
        confidence=confidence,
    )


def _poa(ts, value=600.0, **kw):
    return _row(ts, IRRADIANCE_METRIC, value, plane=WeatherIrradiancePlane.poa, **kw)


def _cell(ts, value=100.0, **kw):
    return _row(ts, CELL_TEMPERATURE_METRIC, value,
                temp=WeatherTemperatureType.cell, **kw)


def _count_obs(db_session, site_id, source_id) -> int:
    obs = weather_crud.WeatherObservationCRUD(db_session).get_window(
        site_id,
        start=datetime(2000, 1, 1),
        end=datetime(2100, 1, 1),
        metrics=[IRRADIANCE_METRIC, CELL_TEMPERATURE_METRIC],
        weather_source_id=source_id,
    )
    return len(obs)


# ===========================================================================
# Import — idempotency + all-or-nothing
# ===========================================================================
def test_run_historical_import_is_idempotent(db_session, site_id):
    source = _make_source(db_session, site_id)
    ts = datetime(2031, 3, 1, 12, 0)
    req = HistoricalImportRequest(
        weather_source_id=source.id,
        rows=[_poa(ts, 600.0), _cell(ts, 100.0)],
    )

    first = run_historical_import(db_session, site_id=site_id, request=req)
    assert first.rows_inserted == 2
    assert first.rows_duplicate == 0

    # Same window, same source, same semantics → deterministic dedupe keys → no-op.
    second = run_historical_import(db_session, site_id=site_id, request=req)
    assert second.rows_inserted == 0
    assert second.rows_duplicate == 2
    assert "idempotent_duplicates_skipped" in second.warnings

    assert _count_obs(db_session, site_id, source.id) == 2


def test_run_historical_import_all_or_nothing_writes_nothing(db_session, site_id):
    source = _make_source(db_session, site_id)
    before = _count_obs(db_session, site_id, source.id)

    # One valid row + one row with an INVALID plane enum. Use a request-like
    # object so the bad row reaches the service (the typed schema would reject it
    # at the boundary); the service must validate BEFORE writing anything.
    bad_request = SimpleNamespaceRequest(
        weather_source_id=source.id,
        rows=[
            {"timestamp": datetime(2031, 4, 1, 9, 0), "metric": "irradiance",
             "value": 500.0, "irradiance_plane": "poa"},
            {"timestamp": datetime(2031, 4, 1, 10, 0), "metric": "irradiance",
             "value": 500.0, "irradiance_plane": "banana"},
        ],
    )
    with pytest.raises(WeatherImportValidationError) as exc:
        run_historical_import(db_session, site_id=site_id, request=bad_request)
    assert exc.value.errors  # structured, row-addressable errors
    # Nothing persisted — not even the valid row.
    assert _count_obs(db_session, site_id, source.id) == before


# ===========================================================================
# Source site-scoping — never attach another tenant's weather source
# ===========================================================================
def _make_other_company(db_session) -> int:
    from app.crud.company import CompanyCRUD
    from tests.unit import samples

    payload = copy.deepcopy(samples.SETUP_COMPANIES[0])
    suffix = next(_NAME_SEQ)
    payload["name"] = f"{payload['name']} W2Other-{suffix}"
    if payload.get("email"):
        local, _, domain = payload["email"].partition("@")
        payload["email"] = f"{local}+w2other{suffix}@{domain or 'example.com'}"
    return CompanyCRUD(db_session).create_item(payload).id


def test_get_source_visible_to_site_enforces_scope(db_session, company_id):
    """A source is visible to a site only when it is site-scoped to that exact
    site, company-scoped to the site's company, or global. A source bound to a
    different site or company is invisible so it can never be attached."""
    crud = weather_crud.WeatherSourceCRUD(db_session)
    site_a = _make_site(db_session, company_id)
    site_b = _make_site(db_session, company_id)  # same company, different site
    other_company_id = _make_other_company(db_session)

    def _src(**kw):
        return crud.create(
            source_type=WeatherSourceType.imported_historical_provider_file,
            display_name="scope-test source",
            default_confidence=WeatherConfidence.high,
            **kw,
        )

    site_scoped_here = _make_source(db_session, site_a)
    site_scoped_other = _make_source(db_session, site_b)
    company_scoped_here = _src(site_id=None, company_id=company_id)
    company_scoped_other = _src(site_id=None, company_id=other_company_id)
    global_source = _src(site_id=None, company_id=None)

    # Same site → visible.
    assert crud.get_visible_to_site(
        site_id=site_a, source_id=site_scoped_here.id
    ) is not None
    # Different site (even within the same company) → hidden.
    assert crud.get_visible_to_site(
        site_id=site_a, source_id=site_scoped_other.id
    ) is None
    # Company-scoped to this site's company → visible.
    assert crud.get_visible_to_site(
        site_id=site_a, source_id=company_scoped_here.id
    ) is not None
    # Company-scoped to a DIFFERENT company → hidden.
    assert crud.get_visible_to_site(
        site_id=site_a, source_id=company_scoped_other.id
    ) is None
    # Global (no site/company) → visible.
    assert crud.get_visible_to_site(
        site_id=site_a, source_id=global_source.id
    ) is not None
    # Unknown id → None.
    assert crud.get_visible_to_site(site_id=site_a, source_id=999_999) is None


def test_run_historical_import_rejects_cross_site_source(db_session, company_id):
    """Importing on site A with a source that belongs to site B is rejected
    before any write — closing the cross-site source-attachment hole."""
    site_a = _make_site(db_session, company_id)
    site_b = _make_site(db_session, company_id)
    foreign_source = _make_source(db_session, site_b)  # belongs to site B
    req = HistoricalImportRequest(
        weather_source_id=foreign_source.id,
        rows=[_poa(datetime(2032, 5, 1, 12, 0), 600.0)],
    )
    with pytest.raises(ValueError):
        run_historical_import(db_session, site_id=site_a, request=req)
    # Nothing written under site A for that foreign source.
    assert _count_obs(db_session, site_a, foreign_source.id) == 0


def test_create_historical_profile_rejects_cross_site_source(db_session, company_id):
    """Defense-in-depth: creating a profile against a source that belongs to
    another site is rejected at the service layer (not only the router)."""
    site_a = _make_site(db_session, company_id)
    site_b = _make_site(db_session, company_id)
    foreign_source = _make_source(db_session, site_b)  # belongs to site B
    with pytest.raises(ValueError):
        create_historical_profile(
            db_session,
            site_id=site_a,
            request=HistoricalProfileCreateRequest(
                weather_source_id=foreign_source.id
            ),
        )


# ===========================================================================
# Import — disclosure (validate / preview), no fixtures needed
# ===========================================================================
def test_validate_rows_rejects_nonfinite_and_bad_enum():
    rows = [
        {"timestamp": datetime(2031, 1, 1, 0, 0), "metric": "irradiance",
         "value": 600.0, "irradiance_plane": "poa"},  # valid
        {"timestamp": datetime(2031, 1, 1, 1, 0), "metric": "irradiance",
         "value": float("nan"), "irradiance_plane": "poa"},  # non-finite
        {"timestamp": datetime(2031, 1, 1, 2, 0), "metric": "irradiance",
         "value": 700.0, "irradiance_plane": "banana"},  # bad enum
    ]
    normalized, errors = validate_rows(rows)
    assert len(normalized) == 1  # only the valid row survives
    assert {e.index for e in errors} == {1, 2}
    assert {e.field for e in errors} == {"value", "irradiance_plane"}


def test_preview_discloses_stored_not_usable_and_modeled_without_converting():
    rows = [
        {"timestamp": datetime(2031, 1, 1, 0, 0), "metric": "irradiance",
         "value": 600.0, "irradiance_plane": "poa"},                 # usable
        {"timestamp": datetime(2031, 1, 1, 1, 0), "metric": "irradiance",
         "value": 700.0, "irradiance_plane": "ghi"},                 # stored, not usable
        {"timestamp": datetime(2031, 1, 1, 2, 0), "metric": "ambient_temperature",
         "value": 75.0, "temperature_type": "ambient"},              # stored, not usable
        {"timestamp": datetime(2031, 1, 1, 3, 0), "metric": "irradiance",
         "value": 650.0, "irradiance_plane": "poa", "is_modeled": True},  # modeled
    ]
    preview = preview_import(rows)
    assert preview.valid_rows == 4
    assert preview.invalid_rows == 0
    assert preview.physics_usable_rows == 2  # two POA rows
    assert preview.stored_not_usable_rows == 2  # GHI + ambient
    assert preview.modeled_rows == 1
    assert "stored_not_usable_rows_present" in preview.warnings
    assert "modeled_rows_present" in preview.warnings


def test_build_dedupe_key_is_deterministic_and_semantics_sensitive():
    ts = datetime(2031, 1, 1, 12, 0, 30)
    poa = NormalizedObservation(
        metric="irradiance", value=600.0, unit=None, obs_ts=ts,
        irradiance_plane="poa", temperature_type="unknown",
        is_modeled=False, confidence="high", source_row_id=None,
    )
    poa_again = NormalizedObservation(
        metric="irradiance", value=999.0, unit=None, obs_ts=ts,
        irradiance_plane="poa", temperature_type="unknown",
        is_modeled=False, confidence="low", source_row_id=None,
    )
    ghi = NormalizedObservation(
        metric="irradiance", value=600.0, unit=None, obs_ts=ts,
        irradiance_plane="ghi", temperature_type="unknown",
        is_modeled=False, confidence="high", source_row_id=None,
    )
    k_poa = build_dedupe_key(site_id=1, source_id=2, obs=poa)
    # Same identity (value/confidence excluded) → identical key (idempotent).
    assert k_poa == build_dedupe_key(site_id=1, source_id=2, obs=poa_again)
    # Different SEMANTICS → distinct key (we never silently overwrite semantics).
    assert k_poa != build_dedupe_key(site_id=1, source_id=2, obs=ghi)


# ===========================================================================
# Readiness — honest coverage / blocking
# ===========================================================================
def test_readiness_blocks_when_no_active_profile(db_session, site_id):
    # Empty window, no profile, no observations → not replay-ready.
    out = compute_weather_readiness(
        db_session,
        site_id=site_id,
        start=datetime(2031, 6, 1, 0, 0),
        end=datetime(2031, 6, 1, 2, 0),
        bucket_size="1h",
    )
    assert out.ready_for_expected_replay is False
    assert readiness_svc.REASON_PROFILE_MISSING in out.blocking_reasons
    assert readiness_svc.REASON_NO_USABLE_IRRADIANCE in out.blocking_reasons
    assert readiness_svc.REASON_NO_USABLE_CELL_TEMPERATURE in out.blocking_reasons


def test_readiness_ready_when_active_profile_and_full_coverage(db_session, site_id):
    source = _make_source(db_session, site_id)
    start = datetime(2031, 7, 1, 0, 0)
    end = datetime(2031, 7, 1, 1, 0)  # buckets: 00:00, 01:00
    req = HistoricalImportRequest(
        weather_source_id=source.id,
        rows=[
            _poa(start), _cell(start),
            _poa(datetime(2031, 7, 1, 1, 0)), _cell(datetime(2031, 7, 1, 1, 0)),
        ],
    )
    run_historical_import(db_session, site_id=site_id, request=req)

    profile = create_historical_profile(
        db_session,
        site_id=site_id,
        request=HistoricalProfileCreateRequest(weather_source_id=source.id),
    )
    apply_profile_action(
        db_session, site_id=site_id, profile_id=profile.id, action="approve",
    )

    out = compute_weather_readiness(
        db_session, site_id=site_id, start=start, end=end, bucket_size="1h",
    )
    assert out.has_active_historical_profile is True
    assert out.total_expected_buckets == 2
    assert out.both_usable_buckets == 2
    assert out.coverage_pct == 1.0
    assert out.ready_for_expected_replay is True
    assert readiness_svc.IND_READY_FOR_REPLAY in out.indicators


def test_readiness_discloses_gaps_and_unknown_semantics(db_session, site_id):
    source = _make_source(db_session, site_id)
    start = datetime(2031, 8, 1, 0, 0)
    end = datetime(2031, 8, 1, 2, 0)  # buckets: 00:00, 01:00, 02:00
    req = HistoricalImportRequest(
        weather_source_id=source.id,
        rows=[
            _poa(start), _cell(start),                       # bucket 0 fully usable
            _row(datetime(2031, 8, 1, 1, 0), IRRADIANCE_METRIC, 700.0,
                 plane=WeatherIrradiancePlane.ghi),          # bucket 1: stored, NOT usable
        ],
    )
    run_historical_import(db_session, site_id=site_id, request=req)
    profile = create_historical_profile(
        db_session,
        site_id=site_id,
        request=HistoricalProfileCreateRequest(weather_source_id=source.id),
    )
    apply_profile_action(
        db_session, site_id=site_id, profile_id=profile.id, action="approve",
    )

    out = compute_weather_readiness(
        db_session, site_id=site_id, start=start, end=end, bucket_size="1h",
    )
    assert out.both_usable_buckets == 1
    assert out.coverage_pct < 1.0
    assert out.ready_for_expected_replay is False
    assert readiness_svc.REASON_INSUFFICIENT_COVERAGE in out.blocking_reasons
    assert readiness_svc.IND_COVERAGE_GAPS_PRESENT in out.indicators
    assert readiness_svc.IND_UNKNOWN_SEMANTICS_PRESENT in out.indicators


# ===========================================================================
# Profile lifecycle — draft → approve activates; reject/revoke; errors
# ===========================================================================
def test_create_historical_profile_is_draft(db_session, site_id):
    source = _make_source(db_session, site_id)
    profile = create_historical_profile(
        db_session,
        site_id=site_id,
        request=HistoricalProfileCreateRequest(weather_source_id=source.id),
    )
    assert profile.status == WeatherSourceProfileStatus.draft
    assert profile.role == WeatherSourceProfileRole.historical
    assert profile.approved_at is None


def test_approve_activates_profile_and_records_ledger(db_session, site_id):
    source = _make_source(db_session, site_id)
    profile = create_historical_profile(
        db_session,
        site_id=site_id,
        request=HistoricalProfileCreateRequest(weather_source_id=source.id),
    )
    updated, approval = apply_profile_action(
        db_session, site_id=site_id, profile_id=profile.id, action="approve",
        rationale="looks good",
    )
    assert updated.status == WeatherSourceProfileStatus.active
    assert updated.approved_at is not None
    assert approval.action == WeatherApprovalAction.approve


def test_reject_then_revoke_set_expected_statuses(db_session, site_id):
    source = _make_source(db_session, site_id)
    rejected = create_historical_profile(
        db_session, site_id=site_id,
        request=HistoricalProfileCreateRequest(weather_source_id=source.id),
    )
    upd_rej, _ = apply_profile_action(
        db_session, site_id=site_id, profile_id=rejected.id, action="reject",
    )
    assert upd_rej.status == WeatherSourceProfileStatus.rejected
    assert upd_rej.approved_at is None  # reject is not an approval stamp

    revoked = create_historical_profile(
        db_session, site_id=site_id,
        request=HistoricalProfileCreateRequest(weather_source_id=source.id),
    )
    upd_rev, _ = apply_profile_action(
        db_session, site_id=site_id, profile_id=revoked.id, action="revoke",
    )
    assert upd_rev.status == WeatherSourceProfileStatus.superseded


def test_apply_profile_action_unknown_action_and_cross_site_raise(db_session, site_id):
    source = _make_source(db_session, site_id)
    profile = create_historical_profile(
        db_session, site_id=site_id,
        request=HistoricalProfileCreateRequest(weather_source_id=source.id),
    )
    with pytest.raises(WeatherProfileActionError):
        apply_profile_action(
            db_session, site_id=site_id, profile_id=profile.id, action="frobnicate",
        )
    with pytest.raises(WeatherProfileActionError):
        # Same profile, wrong site → must refuse to act across sites.
        apply_profile_action(
            db_session, site_id=site_id + 987654, profile_id=profile.id,
            action="approve",
        )


# ===========================================================================
# Glossary coverage + static guarantees + clean startup
# ===========================================================================
def test_glossary_covers_every_emitted_w2_key():
    keys = {e["key"] for e in EXPECTED_GLOSSARY}
    readiness = {
        readiness_svc.REASON_PROFILE_MISSING,
        readiness_svc.REASON_PROFILE_UNAPPROVED,
        readiness_svc.REASON_PROFILE_PARTIAL,
        readiness_svc.REASON_NO_USABLE_IRRADIANCE,
        readiness_svc.REASON_NO_USABLE_CELL_TEMPERATURE,
        readiness_svc.REASON_INSUFFICIENT_COVERAGE,
        readiness_svc.REASON_NO_EXPECTED_BUCKETS,
        readiness_svc.IND_UNKNOWN_SEMANTICS_PRESENT,
        readiness_svc.IND_MODELED_WEATHER_PRESENT,
        readiness_svc.IND_COVERAGE_GAPS_PRESENT,
        readiness_svc.IND_READY_FOR_REPLAY,
    }
    resolver = {
        wr.IND_HISTORICAL_WEATHER_ACTIVE,
        wr.IND_MISSING_IRRADIANCE,
        wr.IND_MISSING_CELL_TEMPERATURE,
        wr.IND_MODELED_WEATHER_PRESENT,
        wr.IND_COVERAGE_GAPS_PRESENT,
        wr.IND_CONFIDENCE_UNKNOWN,
        wr.IND_BELOW_CONFIDENCE_THRESHOLD,
        wr.WARN_HISTORICAL_PARTIAL_WINDOW,
    }
    imports = {
        "stored_not_usable_rows_present",
        "modeled_rows_present",
        "idempotent_duplicates_skipped",
    }
    missing = (readiness | resolver | imports) - keys
    assert not missing, f"glossary missing W2 keys: {sorted(missing)}"


def _imported_module_names(module) -> set[str]:
    tree = ast.parse(inspect.getsource(module))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_w2_modules_have_no_forbidden_dependencies():
    from app.routers import weather as weather_router_mod

    forbidden_prefixes = (
        "google.cloud", "google.oauth2", "firebase_admin", "boto3", "requests",
    )
    forbidden_substrings = ("bigquery", "firestore")
    modules = (
        import_svc, readiness_svc, profile_svc, bucketing_mod, wr,
        weather_router_mod,
    )
    for module in modules:
        for name in _imported_module_names(module):
            lname = name.lower()
            assert not any(
                lname == p or lname.startswith(p + ".") for p in forbidden_prefixes
            ), f"forbidden import {name!r} in {module.__name__}"
            assert not any(
                token in lname for token in forbidden_substrings
            ), f"forbidden import {name!r} in {module.__name__}"


def test_app_imports_clean_with_weather_router_registered():
    from app.main import ilios_api

    app = ilios_api()
    paths = {getattr(r, "path", "") for r in app.routes}
    assert any(p.startswith("/api/weather/sites/") for p in paths), (
        "weather router not registered under /api/weather"
    )


class SimpleNamespaceRequest:
    """Minimal request-like holder used to drive an invalid row past the typed
    schema and into the service, proving service-level all-or-nothing safety."""

    def __init__(self, *, weather_source_id, rows):
        self.weather_source_id = weather_source_id
        self.source = None
        self.batch_kind = WeatherObservationBatchKind.file_import
        self.unit_system = None
        self.timezone_alignment_note = None
        self.source_file_id = None
        self.rows = rows
