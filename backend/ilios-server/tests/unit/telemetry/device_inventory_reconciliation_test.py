"""Read-only Device Inventory Reconciliation — zero-mutation + the G1→G8 ladder.

Guards the two load-bearing contracts of
``app.services.telemetry.device_inventory_reconciliation_service`` (Phase A):

1. **ZERO MUTATION.** Calling ``build_site_inventory_reconciliation`` (and the
   ``build_inventory_reconciliation_summary`` projection consumed by the DD
   ``telemetry_reality`` block) must never write or commit. We fingerprint every
   table the service reads — ``devices``, ``telemetry_devices_mapping``,
   ``telemetry_sites_mapping``, ``project_facts``, ``telemetry_external_sites``,
   ``telemetry_external_devices``, ``telemetry_sync_jobs``,
   ``weather_device_mappings`` and ``telemetry_expected_baselines`` — before and
   after the call and assert byte-for-byte identity, and additionally assert the
   ORM session carries no pending ``new``/``dirty``/``deleted`` objects.

2. **THE G1→G8 LADDER (first gate wins, top-down).** One synthetic site per gate
   exercises the deterministic headline ladder, plus a Site-4-shaped site that
   must land on ``needs_reconciliation`` (a blocking, unresolved weather-measurement
   dependency while a weather-adjusted expected baseline is active).

A dedicated regression test also pins the ``{"v": ...}`` fact-envelope unwrap:
``project_facts.value`` is always stored wrapped (e.g. ``{"v": "7"}``), so the
documented inverter/module counts must be read through the same unwrap the DD
reconciliation service uses — otherwise a real documented count silently reads as
missing.

DB-backed: the module builds its own company / site / devices / mappings via CRUD
and ORM (mirroring the eligibility-diagnostics and DD reconciliation suites).
No ``pytest-mock``; the service is pure-read so nothing needs mocking.
"""
from __future__ import annotations

import copy
import itertools
from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException

from app.crud.das_connection import DASConnectionCRUD
from app.crud.device import DeviceCRUD
from app.crud.weather import WeatherDeviceMappingCRUD
from app.models.device import Device, DeviceCategories
from app.models.project_facts import CanonicalField, FactStatus, ProjectFact
from app.models.site import Site
from app.models.telemetry import (
    DASProvidersEnum,
    ExternalSiteSyncStatus,
    TelemetryDeviceMapping,
    TelemetryExternalDevice,
    TelemetryExternalSite,
    TelemetrySiteMapping,
    TelemetrySyncJob,
    TelemetrySyncStatus,
)
from app.models.telemetry_expected import (
    TelemetryBaselineStatus,
    TelemetryBaselineType,
    TelemetryExpectedBaseline,
)
from app.models.weather import (
    WeatherCalibrationStatus,
    WeatherDeviceMapping,
    WeatherIrradiancePlane,
    WeatherTemperatureType,
)
from app.schema.inventory_acknowledgement import (
    InventoryAckCreateRequest,
    InventoryAckRevokeRequest,
)
from app.schema.inventory_reconciliation import (
    CoverageMode,
    DocumentedInventoryState,
    EquipmentClass,
    InventoryAckPolicy,
    InventoryReconciliationStatus,
    WeatherDependencySubtype,
)
from app.services.telemetry import device_inventory_reconciliation_service as svc
from app.services.telemetry import inventory_acknowledgement_service as ack_svc

_SEQ = itertools.count(1)

S = InventoryReconciliationStatus


# ---------------------------------------------------------------------------
# Fixtures — self-contained company + per-test site (mirrors the W2 suite)
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def company_id(db_session):
    from app.crud.company import CompanyCRUD
    from tests.unit import samples

    payload = copy.deepcopy(samples.SETUP_COMPANIES[0])
    suffix = next(_SEQ)
    payload["name"] = f"{payload['name']} InvReconCo-{suffix}"
    if payload.get("email"):
        local, _, domain = payload["email"].partition("@")
        payload["email"] = f"{local}+invrecon{suffix}@{domain or 'example.com'}"
    return CompanyCRUD(db_session).create_item(payload).id


@pytest.fixture()
def site_id(db_session, company_id) -> int:
    from app.crud.site import SiteCRUD
    from tests.unit import samples

    payload = copy.deepcopy(samples.TEST_SITE_BODY)
    payload["company_id"] = company_id
    payload["name"] = f"{payload['name']} InvRecon-{next(_SEQ)}"
    return SiteCRUD(db_session).create_item(payload).id


# ---------------------------------------------------------------------------
# Construction helpers
# ---------------------------------------------------------------------------
def _site(db, site_id) -> Site:
    """Reload the Site with its telemetry mapping + devices freshly loaded."""
    db.expire_all()
    return db.query(Site).filter(Site.id == site_id).one()


def _canonical(db, name):
    field = db.query(CanonicalField).filter(CanonicalField.name == name).one_or_none()
    if field is None:
        field = CanonicalField(name=name, display_name=name, field_type="number")
        db.add(field)
        db.commit()
        db.refresh(field)
    return field


def _add_fact(db, site_id, name, value, *, status=FactStatus.active.value):
    """Add a ``project_fact`` using the production ``{"v": ...}`` envelope shape."""
    field = _canonical(db, name)
    fact = ProjectFact(
        site_id=site_id,
        canonical_field_id=field.id,
        value={"v": value},
        status=status,
    )
    db.add(fact)
    db.commit()
    db.refresh(fact)
    return fact


def _make_connection(db, company_id):
    from app.crud.company_das_provider import CompanyDASProviderCRUD

    provider_crud = CompanyDASProviderCRUD(db)
    if not provider_crud.has_provider(company_id, DASProvidersEnum.kmc):
        provider_crud.assign_provider(company_id, DASProvidersEnum.kmc)
        db.commit()
    return DASConnectionCRUD(db).create_item(
        {
            "company_id": company_id,
            "name": f"InvRecon DAS {next(_SEQ)}",
            "provider": DASProvidersEnum.kmc,
            "secret_token_name": f"tok-{next(_SEQ)}",
        }
    )


def _map_site(db, site_id, connection, *, telemetry_site_id, is_active=True):
    mapping = TelemetrySiteMapping(
        site_id=site_id,
        connection_id=connection.id,
        provider_account_id=connection.id,
        telemetry_site_id=telemetry_site_id,
        telemetry_site_name=f"Ext Site {telemetry_site_id}",
        is_active=is_active,
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


def _device(db, site_id, category, **overrides):
    payload = {
        "name": f"{category.name}-{next(_SEQ)}",
        "category": category.name,
        "site_id": site_id,
    }
    payload.update(overrides)
    return DeviceCRUD(db).create_item(payload)


def _map_device(db, device, telemetry_device_id):
    mapping = TelemetryDeviceMapping(
        device_id=device.id,
        telemetry_device_id=telemetry_device_id,
        telemetry_device_name=f"Ext {telemetry_device_id}",
    )
    db.add(mapping)
    db.commit()
    db.refresh(mapping)
    return mapping


def _external_device(
    db,
    connection,
    external_site_id,
    external_device_id,
    *,
    name=None,
    sync_status=ExternalSiteSyncStatus.seen,
):
    ext = TelemetryExternalDevice(
        provider_account_id=connection.id,
        external_site_id=external_site_id,
        external_device_id=external_device_id,
        external_device_name=name or external_device_id,
        sync_status=sync_status,
    )
    db.add(ext)
    db.commit()
    db.refresh(ext)
    return ext


def _external_site(db, connection, external_site_id, last_synced_at):
    ext = TelemetryExternalSite(
        provider_account_id=connection.id,
        external_site_id=external_site_id,
        external_site_name=f"Ext {external_site_id}",
        last_synced_at=last_synced_at,
    )
    db.add(ext)
    db.commit()
    db.refresh(ext)
    return ext


def _sync_job(db, company_id, site_id, *, status, ended_at):
    job = TelemetrySyncJob(
        company_id=company_id,
        site_id=site_id,
        status=status,
        correlation_id=f"corr-{next(_SEQ)}",
        ended_at=ended_at,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


def _wa_baseline(db, company_id, site_id):
    """An ACTIVE weather-adjusted expected baseline → weather input is required."""
    baseline = TelemetryExpectedBaseline(
        company_id=company_id,
        site_id=site_id,
        baseline_name="inv-recon WA",
        baseline_type=TelemetryBaselineType.weather_adjusted_model,
        status=TelemetryBaselineStatus.active,
        version=1,
        timezone="UTC",
    )
    db.add(baseline)
    db.commit()
    db.refresh(baseline)
    return baseline


def _weather_mapping(
    db,
    site_id,
    device,
    *,
    plane,
    temp,
    calib=WeatherCalibrationStatus.unknown,
    metric="irradiance_wm2",
):
    return WeatherDeviceMappingCRUD(db).create(
        site_id=site_id,
        device_id=device.id,
        metric=metric,
        irradiance_plane=plane,
        temperature_type=temp,
        calibration_status=calib,
    )


def _ext(site_id: int) -> str:
    return f"EXT-{site_id}"


def _class_count(resp, equipment_class: EquipmentClass):
    return next(
        (c for c in resp.class_counts if c.equipment_class == equipment_class), None
    )


# ---------------------------------------------------------------------------
# Scenario builder — a faithful, Site-4-shaped reconciliation site
# ---------------------------------------------------------------------------
def _build_site4_shaped(db, company_id, site_id):
    """Reproduce the validated Site-4 shape (13 documented / 13 discovered devices).

    * 7 inverters + Elkor meter + PowerLogger gateway + IMT weather cell — all
      mapped to provider devices (their external ids are "documented").
    * an AE-UPS gateway (mappable, unmapped) → ``missing_telemetry_counterpart``.
    * a cell modem (ineligible) and a null-ish "Site Performance" aggregate
      (``other``) — both unmapped and emit no mismatch.
    * the weather cell is mapped but its measurement semantics are UNKNOWN, while
      an active weather-adjusted baseline makes weather a hard dependency →
      the single blocking finding that pins ``needs_reconciliation``.
    * discovery is stale (12d) yet readings are fresh (a sync succeeded today) →
      a non-blocking ``telemetry_freshness`` note, NOT a G4 escalation.
    * three discovered provider devices have no documented counterpart →
      ``undocumented_telemetry_device`` ×3.
    """
    now = datetime.utcnow()
    ext_site = _ext(site_id)
    conn = _make_connection(db, company_id)
    _map_site(db, site_id, conn, telemetry_site_id=ext_site, is_active=True)

    _add_fact(db, site_id, "inverter_quantity", "7")
    _add_fact(db, site_id, "module_quantity", "1900")
    _add_fact(db, site_id, "inverter_model", "SG60KU-M")
    # Identical candidates are informational only; never change a documented count.
    _add_fact(db, site_id, "inverter_quantity", "7", status=FactStatus.candidate.value)

    mapped_ext_ids: list[str] = []
    for i in range(7):
        inv = _device(db, site_id, DeviceCategories.inverter)
        tid = f"INV{i + 1}"
        _map_device(db, inv, tid)
        mapped_ext_ids.append(tid)

    meter = _device(db, site_id, DeviceCategories.meter, name="Elkor Meter")
    _map_device(db, meter, "MTR1")
    mapped_ext_ids.append("MTR1")

    pl = _device(db, site_id, DeviceCategories.network_gateway, name="PowerLogger")
    _map_device(db, pl, "GW1")
    mapped_ext_ids.append("GW1")

    ws = _device(db, site_id, DeviceCategories.weather_station, name="IMT Reference Cell")
    _map_device(db, ws, "WS1")
    mapped_ext_ids.append("WS1")
    # Mapped weather source, but semantics are UNKNOWN (never assumed POA/cell).
    _weather_mapping(
        db,
        site_id,
        ws,
        plane=WeatherIrradiancePlane.unknown,
        temp=WeatherTemperatureType.unknown,
    )

    # Mappable-but-unmapped gateway → missing_telemetry_counterpart (non-blocking).
    _device(db, site_id, DeviceCategories.network_gateway, name="AE UPS")
    # Ineligible / non-mappable rows → no mismatch.
    _device(db, site_id, DeviceCategories.modem, name="Cell Modem")
    _device(db, site_id, DeviceCategories.rack_mount, name="Site Performance")

    # Discovered provider devices: documented counterparts + 3 undocumented extras.
    for tid in mapped_ext_ids:
        _external_device(db, conn, ext_site, tid)
    _external_device(db, conn, ext_site, "UPS-EXT", name="AE UPS")
    _external_device(db, conn, ext_site, "MODEM-EXT", name="Cell Modem")
    _external_device(db, conn, ext_site, "SITEPERF-EXT", name="Site Performance")

    # Stale discovery (12d) but fresh readings (sync today) → freshness note only.
    _external_site(db, conn, ext_site, last_synced_at=now - timedelta(days=12))
    _sync_job(db, company_id, site_id, status=TelemetrySyncStatus.succeeded, ended_at=now)
    _wa_baseline(db, company_id, site_id)
    return conn


# ---------------------------------------------------------------------------
# Zero-mutation fingerprint
# ---------------------------------------------------------------------------
_FINGERPRINT_MODELS = (
    Device,
    TelemetryDeviceMapping,
    TelemetrySiteMapping,
    ProjectFact,
    TelemetryExternalSite,
    TelemetryExternalDevice,
    TelemetrySyncJob,
    WeatherDeviceMapping,
    TelemetryExpectedBaseline,
)


def _fingerprint(db) -> dict:
    """Whole-table snapshot (every column of every row) keyed by table name.

    Read fresh from the DB (``expire_all``) so a committed mutation would surface
    as a diff. Equality of the two snapshots proves no insert/update/delete.
    """
    db.expire_all()
    snap: dict = {}
    for model in _FINGERPRINT_MODELS:
        rows = db.query(model).order_by(model.id).all()
        snap[model.__tablename__] = [
            tuple((c.name, getattr(row, c.name)) for c in model.__table__.columns)
            for row in rows
        ]
    return snap


class TestZeroMutation:
    def test_build_and_summary_never_mutate(self, db_session, company_id, site_id):
        _build_site4_shaped(db_session, company_id, site_id)

        before = _fingerprint(db_session)
        resp = svc.build_site_inventory_reconciliation(
            db_session, _site(db_session, site_id)
        )
        assert resp.status == S.needs_reconciliation
        assert not db_session.new
        assert not db_session.dirty
        assert not db_session.deleted

        summary = svc.build_inventory_reconciliation_summary(
            db_session, _site(db_session, site_id)
        )
        assert summary.status == resp.status
        assert summary.has_blocking_mismatch is True
        assert not db_session.new
        assert not db_session.dirty
        assert not db_session.deleted

        after = _fingerprint(db_session)
        assert before == after

    def test_build_on_empty_site_is_read_only(self, db_session, site_id):
        before = _fingerprint(db_session)
        resp = svc.build_site_inventory_reconciliation(
            db_session, _site(db_session, site_id)
        )
        assert resp.status == S.telemetry_not_connected
        assert not db_session.new
        assert not db_session.dirty
        assert not db_session.deleted
        assert before == _fingerprint(db_session)


# ---------------------------------------------------------------------------
# The G1 → G8 ladder
# ---------------------------------------------------------------------------
class TestLadder:
    def test_g1_telemetry_not_connected_no_mapping(self, db_session, site_id):
        resp = svc.build_site_inventory_reconciliation(
            db_session, _site(db_session, site_id)
        )
        assert resp.status == S.telemetry_not_connected
        assert resp.telemetry_connected is False
        assert resp.site_mapped is False

    def test_g1_telemetry_not_connected_inactive_mapping(
        self, db_session, company_id, site_id
    ):
        conn = _make_connection(db_session, company_id)
        _map_site(
            db_session, site_id, conn, telemetry_site_id=_ext(site_id), is_active=False
        )
        resp = svc.build_site_inventory_reconciliation(
            db_session, _site(db_session, site_id)
        )
        assert resp.status == S.telemetry_not_connected
        assert resp.site_mapped is False

    def test_g2_documented_inventory_incomplete(self, db_session, company_id, site_id):
        conn = _make_connection(db_session, company_id)
        _map_site(db_session, site_id, conn, telemetry_site_id=_ext(site_id))
        # Only one of the two anchor facts → partial documentation.
        _add_fact(db_session, site_id, "inverter_quantity", "7")
        resp = svc.build_site_inventory_reconciliation(
            db_session, _site(db_session, site_id)
        )
        assert resp.status == S.documented_inventory_incomplete
        assert resp.telemetry_connected is True
        assert resp.documented_inventory_state == DocumentedInventoryState.partial

    def test_g3_telemetry_connected_no_devices(self, db_session, company_id, site_id):
        conn = _make_connection(db_session, company_id)
        _map_site(db_session, site_id, conn, telemetry_site_id=_ext(site_id))
        _add_fact(db_session, site_id, "inverter_quantity", "7")
        _add_fact(db_session, site_id, "module_quantity", "1900")
        resp = svc.build_site_inventory_reconciliation(
            db_session, _site(db_session, site_id)
        )
        assert resp.status == S.telemetry_connected_no_devices
        assert resp.total_ilios_devices == 0
        assert resp.total_discovered_devices == 0

    def test_g4_expected_inverter_not_observed(self, db_session, company_id, site_id):
        conn = _make_connection(db_session, company_id)
        ext = _ext(site_id)
        _map_site(db_session, site_id, conn, telemetry_site_id=ext)
        _add_fact(db_session, site_id, "inverter_quantity", "7")
        _add_fact(db_session, site_id, "module_quantity", "1900")
        # A device is discovered (so not G3) but no inverter is observed/mapped.
        _external_device(db_session, conn, ext, "ORPHAN")
        _external_site(db_session, conn, ext, datetime.utcnow())
        resp = svc.build_site_inventory_reconciliation(
            db_session, _site(db_session, site_id)
        )
        assert resp.status == S.telemetry_inventory_incomplete_or_stale

    def test_g4_stale_discovery_without_fresh_readings(
        self, db_session, company_id, site_id
    ):
        conn = _make_connection(db_session, company_id)
        ext = _ext(site_id)
        _map_site(db_session, site_id, conn, telemetry_site_id=ext)
        _add_fact(db_session, site_id, "inverter_quantity", "1")
        _add_fact(db_session, site_id, "module_quantity", "1900")
        inv = _device(db_session, site_id, DeviceCategories.inverter)
        _map_device(db_session, inv, "INV1")  # observed → first G4 branch is False
        _external_device(db_session, conn, ext, "INV1")
        # Stale discovery (12d) and NO fresh readings (no sync job) → G4 stale branch.
        _external_site(
            db_session, conn, ext, last_synced_at=datetime.utcnow() - timedelta(days=12)
        )
        resp = svc.build_site_inventory_reconciliation(
            db_session, _site(db_session, site_id)
        )
        assert resp.status == S.telemetry_inventory_incomplete_or_stale
        assert resp.discovery_stale is True

    def test_g5_needs_reconciliation_blocking_weather(
        self, db_session, company_id, site_id
    ):
        conn = _make_connection(db_session, company_id)
        ext = _ext(site_id)
        _map_site(db_session, site_id, conn, telemetry_site_id=ext)
        _add_fact(db_session, site_id, "inverter_quantity", "1")
        _add_fact(db_session, site_id, "module_quantity", "1900")
        inv = _device(db_session, site_id, DeviceCategories.inverter)
        _map_device(db_session, inv, "INV1")
        ws = _device(db_session, site_id, DeviceCategories.weather_station)
        _map_device(db_session, ws, "WS1")  # mapped weather source, no semantics row
        _external_device(db_session, conn, ext, "INV1")
        _external_device(db_session, conn, ext, "WS1")
        _external_site(db_session, conn, ext, datetime.utcnow())
        _wa_baseline(db_session, company_id, site_id)  # weather now REQUIRED
        resp = svc.build_site_inventory_reconciliation(
            db_session, _site(db_session, site_id)
        )
        assert resp.status == S.needs_reconciliation
        assert resp.has_blocking_mismatch is True
        assert resp.weather_dependency_unsatisfied is True
        assert resp.weather_dependency_subtype == WeatherDependencySubtype.unknown_semantics

    def test_g7_partially_matched_non_blocking_followup(
        self, db_session, company_id, site_id
    ):
        conn = _make_connection(db_session, company_id)
        ext = _ext(site_id)
        _map_site(db_session, site_id, conn, telemetry_site_id=ext)
        _add_fact(db_session, site_id, "inverter_quantity", "1")
        _add_fact(db_session, site_id, "module_quantity", "1900")
        inv = _device(db_session, site_id, DeviceCategories.inverter)
        _map_device(db_session, inv, "INV1")
        # Mappable-but-unmapped gateway → non-blocking open follow-up.
        _device(db_session, site_id, DeviceCategories.network_gateway, name="AE UPS")
        _external_device(db_session, conn, ext, "INV1")
        _external_site(db_session, conn, ext, datetime.utcnow())
        resp = svc.build_site_inventory_reconciliation(
            db_session, _site(db_session, site_id)
        )
        assert resp.status == S.partially_matched
        assert resp.has_blocking_mismatch is False
        assert resp.open_actionable_mismatch_count >= 1

    def test_g8_matched(self, db_session, company_id, site_id):
        conn = _make_connection(db_session, company_id)
        ext = _ext(site_id)
        _map_site(db_session, site_id, conn, telemetry_site_id=ext)
        _add_fact(db_session, site_id, "inverter_quantity", "1")
        _add_fact(db_session, site_id, "module_quantity", "1900")
        inv = _device(db_session, site_id, DeviceCategories.inverter)
        _map_device(db_session, inv, "INV1")
        _external_device(db_session, conn, ext, "INV1")
        _external_site(db_session, conn, ext, datetime.utcnow())
        resp = svc.build_site_inventory_reconciliation(
            db_session, _site(db_session, site_id)
        )
        assert resp.status == S.matched
        assert resp.has_blocking_mismatch is False
        assert resp.open_actionable_mismatch_count == 0
        assert resp.coverage_mode == CoverageMode.device_level


# ---------------------------------------------------------------------------
# Site-4-shaped end-to-end + the fact-envelope unwrap regression
# ---------------------------------------------------------------------------
class TestSite4Shaped:
    def test_site4_shaped_needs_reconciliation(self, db_session, company_id, site_id):
        _build_site4_shaped(db_session, company_id, site_id)
        resp = svc.build_site_inventory_reconciliation(
            db_session, _site(db_session, site_id)
        )

        assert resp.status == S.needs_reconciliation
        assert resp.documented_inventory_state == DocumentedInventoryState.complete
        assert resp.coverage_mode == CoverageMode.device_level
        assert resp.has_blocking_mismatch is True
        assert resp.weather_dependency_unsatisfied is True
        assert resp.weather_dependency_subtype == WeatherDependencySubtype.unknown_semantics
        assert resp.discovery_stale is True

        assert resp.total_ilios_devices == 13
        assert resp.total_discovered_devices == 13
        assert resp.open_actionable_mismatch_count == 5
        assert resp.informational_mismatch_count == 0
        assert resp.mismatch_category_counts == {
            "weather_expected_dependency": 1,
            "missing_telemetry_counterpart": 1,
            "undocumented_telemetry_device": 3,
            "telemetry_freshness": 1,
        }

        inv = _class_count(resp, EquipmentClass.inverter)
        assert inv is not None
        assert inv.documented_count == 7
        assert inv.ilios_row_count == 7
        assert inv.mapped_count == 7

        mod = _class_count(resp, EquipmentClass.module)
        assert mod is not None
        assert mod.documented_count == 1900

    def test_documented_counts_unwrap_wrapped_fact_value(
        self, db_session, company_id, site_id
    ):
        """Regression: counts must be read through the ``{"v": ...}`` unwrap.

        Reading ``project_facts.value`` raw hands ``_coerce_int`` a ``dict`` and the
        documented count silently reads as ``None`` (the pre-fix behavior).
        """
        conn = _make_connection(db_session, company_id)
        ext = _ext(site_id)
        _map_site(db_session, site_id, conn, telemetry_site_id=ext)
        _add_fact(db_session, site_id, "inverter_quantity", "7")  # {"v": "7"}
        _add_fact(db_session, site_id, "module_quantity", "1900")  # {"v": "1900"}
        inv = _device(db_session, site_id, DeviceCategories.inverter)
        _map_device(db_session, inv, "INV1")
        _external_device(db_session, conn, ext, "INV1")
        _external_site(db_session, conn, ext, datetime.utcnow())

        resp = svc.build_site_inventory_reconciliation(
            db_session, _site(db_session, site_id)
        )
        assert _class_count(resp, EquipmentClass.inverter).documented_count == 7
        assert _class_count(resp, EquipmentClass.module).documented_count == 1900


# ---------------------------------------------------------------------------
# Phase B — reviewer acknowledgements + the G6 ladder state
# ---------------------------------------------------------------------------
def _build_single_actionable_site(db, company_id, site_id):
    """A clean device-level site whose ONLY finding is one acknowledgeable mismatch.

    One mapped inverter (documented qty 1) + a mappable-but-unmapped gateway →
    a single non-blocking ``missing_telemetry_counterpart`` follow-up. No weather
    dependency, no staleness → the site sits at ``partially_matched`` (G7) and
    becomes G6 once that one mismatch is acknowledged.
    """
    conn = _make_connection(db, company_id)
    ext = _ext(site_id)
    _map_site(db, site_id, conn, telemetry_site_id=ext)
    _add_fact(db, site_id, "inverter_quantity", "1")
    _add_fact(db, site_id, "module_quantity", "1900")
    inv = _device(db, site_id, DeviceCategories.inverter)
    _map_device(db, inv, "INV1")
    _device(db, site_id, DeviceCategories.network_gateway, name="AE UPS")
    _external_device(db, conn, ext, "INV1")
    _external_site(db, conn, ext, datetime.utcnow())
    return conn


def _actionable_signature(resp) -> str:
    return next(
        m.mismatch_signature
        for m in resp.mismatches
        if m.acknowledgement_policy
        in (
            InventoryAckPolicy.acknowledgeable_with_required_followup,
            InventoryAckPolicy.acknowledgeable_non_blocking,
        )
    )


class TestAcknowledgements:
    def test_acknowledge_reaches_g6(self, db_session, company_id, site_id):
        _build_single_actionable_site(db_session, company_id, site_id)
        resp = svc.build_site_inventory_reconciliation(
            db_session, _site(db_session, site_id)
        )
        assert resp.status == S.partially_matched
        assert resp.open_actionable_mismatch_count == 1
        assert resp.acknowledged_exception_count == 0

        sig = _actionable_signature(resp)
        out = ack_svc.create_acknowledgement(
            db_session,
            site=_site(db_session, site_id),
            payload=InventoryAckCreateRequest(
                mismatch_signature=sig,
                reconciliation_version=resp.reconciliation_version,
                acknowledgement_reason="Spare UPS, not a telemetry source — accepted.",
            ),
            user_id=None,
        )
        assert out.is_active is True
        assert out.is_expired is False

        after = svc.build_site_inventory_reconciliation(
            db_session, _site(db_session, site_id)
        )
        assert after.status == S.mapping_complete_with_acknowledged_exceptions
        assert after.open_actionable_mismatch_count == 0
        assert after.acknowledged_exception_count == 1
        assert after.has_blocking_mismatch is False
        acked = next(m for m in after.mismatches if m.mismatch_signature == sig)
        assert acked.is_acknowledged is True

    def test_blocking_mismatch_can_never_be_acknowledged(
        self, db_session, company_id, site_id
    ):
        _build_site4_shaped(db_session, company_id, site_id)
        resp = svc.build_site_inventory_reconciliation(
            db_session, _site(db_session, site_id)
        )
        assert resp.status == S.needs_reconciliation
        blocking_sig = next(
            m.mismatch_signature
            for m in resp.mismatches
            if m.acknowledgement_policy
            == InventoryAckPolicy.not_acknowledgeable_blocking
        )
        with pytest.raises(HTTPException) as exc:
            ack_svc.create_acknowledgement(
                db_session,
                site=_site(db_session, site_id),
                payload=InventoryAckCreateRequest(
                    mismatch_signature=blocking_sig,
                    reconciliation_version=resp.reconciliation_version,
                    acknowledgement_reason="Trying to wave away a blocking finding.",
                ),
                user_id=None,
            )
        assert exc.value.status_code == 422

        # The site is unchanged — still blocking.
        again = svc.build_site_inventory_reconciliation(
            db_session, _site(db_session, site_id)
        )
        assert again.status == S.needs_reconciliation
        assert again.has_blocking_mismatch is True

    def test_revoke_restores_open_actionable_count(
        self, db_session, company_id, site_id
    ):
        _build_single_actionable_site(db_session, company_id, site_id)
        resp = svc.build_site_inventory_reconciliation(
            db_session, _site(db_session, site_id)
        )
        sig = _actionable_signature(resp)
        created = ack_svc.create_acknowledgement(
            db_session,
            site=_site(db_session, site_id),
            payload=InventoryAckCreateRequest(
                mismatch_signature=sig,
                reconciliation_version=resp.reconciliation_version,
                acknowledgement_reason="Accepted as a known spare device.",
            ),
            user_id=None,
        )
        g6 = svc.build_site_inventory_reconciliation(
            db_session, _site(db_session, site_id)
        )
        assert g6.status == S.mapping_complete_with_acknowledged_exceptions

        revoked = ack_svc.revoke_acknowledgement(
            db_session,
            site=_site(db_session, site_id),
            ack_id=created.id,
            payload=InventoryAckRevokeRequest(
                revocation_reason="Re-opening: needs proper mapping after all.",
            ),
            user_id=None,
        )
        assert revoked.status == "revoked"
        assert revoked.is_active is False

        after = svc.build_site_inventory_reconciliation(
            db_session, _site(db_session, site_id)
        )
        assert after.status == S.partially_matched
        assert after.open_actionable_mismatch_count == 1
        assert after.acknowledged_exception_count == 0

    def test_stale_reconciliation_version_rejected(
        self, db_session, company_id, site_id
    ):
        _build_single_actionable_site(db_session, company_id, site_id)
        resp = svc.build_site_inventory_reconciliation(
            db_session, _site(db_session, site_id)
        )
        sig = _actionable_signature(resp)
        with pytest.raises(HTTPException) as exc:
            ack_svc.create_acknowledgement(
                db_session,
                site=_site(db_session, site_id),
                payload=InventoryAckCreateRequest(
                    mismatch_signature=sig,
                    reconciliation_version="inv-recon/ancient",
                    acknowledgement_reason="Stale client trying to acknowledge.",
                ),
                user_id=None,
            )
        assert exc.value.status_code == 409

    def test_unknown_signature_not_found(self, db_session, company_id, site_id):
        _build_single_actionable_site(db_session, company_id, site_id)
        resp = svc.build_site_inventory_reconciliation(
            db_session, _site(db_session, site_id)
        )
        with pytest.raises(HTTPException) as exc:
            ack_svc.create_acknowledgement(
                db_session,
                site=_site(db_session, site_id),
                payload=InventoryAckCreateRequest(
                    mismatch_signature="missing_telemetry_counterpart:does:not:exist",
                    reconciliation_version=resp.reconciliation_version,
                    acknowledgement_reason="Pointing at a signature that is not present.",
                ),
                user_id=None,
            )
        assert exc.value.status_code == 404

    def test_double_acknowledge_conflicts(self, db_session, company_id, site_id):
        _build_single_actionable_site(db_session, company_id, site_id)
        resp = svc.build_site_inventory_reconciliation(
            db_session, _site(db_session, site_id)
        )
        sig = _actionable_signature(resp)
        payload = InventoryAckCreateRequest(
            mismatch_signature=sig,
            reconciliation_version=resp.reconciliation_version,
            acknowledgement_reason="First acknowledgement of this mismatch.",
        )
        ack_svc.create_acknowledgement(
            db_session, site=_site(db_session, site_id), payload=payload, user_id=None
        )
        with pytest.raises(HTTPException) as exc:
            ack_svc.create_acknowledgement(
                db_session,
                site=_site(db_session, site_id),
                payload=payload,
                user_id=None,
            )
        assert exc.value.status_code == 409

    def test_acknowledgement_goes_inert_when_version_changes(
        self, db_session, company_id, site_id, monkeypatch
    ):
        """A version bump expires an ack at read time (DB enum still 'acknowledged')."""
        _build_single_actionable_site(db_session, company_id, site_id)
        resp = svc.build_site_inventory_reconciliation(
            db_session, _site(db_session, site_id)
        )
        sig = _actionable_signature(resp)
        ack_svc.create_acknowledgement(
            db_session,
            site=_site(db_session, site_id),
            payload=InventoryAckCreateRequest(
                mismatch_signature=sig,
                reconciliation_version=resp.reconciliation_version,
                acknowledgement_reason="Acknowledged under the current rule set.",
            ),
            user_id=None,
        )
        assert (
            svc.build_site_inventory_reconciliation(
                db_session, _site(db_session, site_id)
            ).status
            == S.mapping_complete_with_acknowledged_exceptions
        )

        # Simulate a reconciliation rule-set change that bumps the engine version.
        monkeypatch.setattr(svc, "RECONCILIATION_VERSION", "inv-recon/next")

        listing = ack_svc.list_acknowledgements(
            db_session, site=_site(db_session, site_id)
        )
        assert len(listing.acknowledgements) == 1
        assert listing.acknowledgements[0].is_active is False
        assert listing.acknowledgements[0].is_expired is True

        # The stale ack no longer applies → the mismatch is open again.
        reverted = svc.build_site_inventory_reconciliation(
            db_session, _site(db_session, site_id)
        )
        assert reverted.status == S.partially_matched
        assert reverted.open_actionable_mismatch_count == 1
        assert reverted.acknowledged_exception_count == 0

    def test_acknowledgement_writes_do_not_mutate_operational_tables(
        self, db_session, company_id, site_id
    ):
        """Acknowledging touches ONLY the ack table; the read path stays zero-mutation."""
        _build_single_actionable_site(db_session, company_id, site_id)
        resp = svc.build_site_inventory_reconciliation(
            db_session, _site(db_session, site_id)
        )
        sig = _actionable_signature(resp)
        ack_svc.create_acknowledgement(
            db_session,
            site=_site(db_session, site_id),
            payload=InventoryAckCreateRequest(
                mismatch_signature=sig,
                reconciliation_version=resp.reconciliation_version,
                acknowledgement_reason="Accepted; verifying read path stays read-only.",
            ),
            user_id=None,
        )
        before = _fingerprint(db_session)
        out = svc.build_site_inventory_reconciliation(
            db_session, _site(db_session, site_id)
        )
        assert out.status == S.mapping_complete_with_acknowledged_exceptions
        assert not db_session.new
        assert not db_session.dirty
        assert not db_session.deleted
        assert before == _fingerprint(db_session)
