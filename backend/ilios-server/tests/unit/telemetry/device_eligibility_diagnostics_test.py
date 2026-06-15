"""Phase 4 — read-only Path-B device eligibility diagnostics.

Guards that the diagnostics service correctly DISCLOSES where each device sits in
the eligibility → mapping → weather-semantics chain without ever changing it:

* an unmapped *expected driver* (inverter) is a ``blocks_calculation`` gap;
* a mappable-but-not-expected device (meter) is inspection-only / informational;
* a weather-source device with no declared semantics lowers confidence (never
  assumed POA/cell);
* an explicit POA/cell declaration clears the unknown-semantics gap and is
  disclosed as physics-usable;
* an ineligible device is reported as such;
* the site rollup dedupes indicators keeping the most-severe blocking level;
* the service performs ZERO writes (read-only).

DB-backed: builds its own company/site/devices via CRUD (mirrors the W2 suite).
"""
from __future__ import annotations

import copy
import itertools

import pytest

from app.crud.device import DeviceCRUD
from app.crud.weather import WeatherDeviceMappingCRUD
from app.models.device import DeviceCategories
from app.models.site import Site
from app.models.telemetry import TelemetryDeviceMapping
from app.models.weather import (
    WeatherCalibrationStatus,
    WeatherIrradiancePlane,
    WeatherTemperatureType,
)
from app.schema.device_eligibility import DiagnosticBlockingLevel
from app.services.telemetry import device_eligibility_diagnostics_service as svc

_NAME_SEQ = itertools.count(1)


@pytest.fixture(scope="module")
def company_id(db_session):
    from app.crud.company import CompanyCRUD
    from tests.unit import samples

    payload = copy.deepcopy(samples.SETUP_COMPANIES[0])
    suffix = next(_NAME_SEQ)
    payload["name"] = f"{payload['name']} DiagCo-{suffix}"
    if payload.get("email"):
        local, _, domain = payload["email"].partition("@")
        payload["email"] = f"{local}+diagco{suffix}@{domain or 'example.com'}"
    return CompanyCRUD(db_session).create_item(payload).id


@pytest.fixture()
def site_id(db_session, company_id) -> int:
    from app.crud.site import SiteCRUD
    from tests.unit import samples

    payload = copy.deepcopy(samples.TEST_SITE_BODY)
    payload["company_id"] = company_id
    payload["name"] = f"{payload['name']} Diag-{next(_NAME_SEQ)}"
    return SiteCRUD(db_session).create_item(payload).id


def _device(db_session, site_id, category: DeviceCategories, **overrides):
    payload = {
        "name": f"Diag {category.name} {next(_NAME_SEQ)}",
        "category": category.name,
        "site_id": site_id,
    }
    payload.update(overrides)
    return DeviceCRUD(db_session).create_item(payload)


def _map_device(db_session, device):
    mapping = TelemetryDeviceMapping(
        device_id=device.id,
        telemetry_device_id=f"ext-{device.id}",
        telemetry_device_name=f"External {device.id}",
    )
    db_session.add(mapping)
    db_session.commit()


def _site(db_session, site_id) -> Site:
    db_session.expire_all()
    return db_session.query(Site).filter(Site.id == site_id).one()


def _by_id(resp, device_id):
    return next(d for d in resp.devices if d.device_id == device_id)


class TestEligibilityDiagnostics:
    def test_unmapped_inverter_blocks_calculation(self, db_session, site_id):
        inv = _device(db_session, site_id, DeviceCategories.inverter)
        resp = svc.compute_site_eligibility_diagnostics(
            db_session, site=_site(db_session, site_id)
        )
        row = _by_id(resp, inv.id)
        assert row.can_drive_expected is True
        assert row.is_mapped is False
        keys = {i.key for i in row.indicators}
        assert svc.IND_EXPECTED_DRIVER_UNMAPPED in keys
        ind = next(
            i for i in row.indicators if i.key == svc.IND_EXPECTED_DRIVER_UNMAPPED
        )
        assert ind.blocking_level == DiagnosticBlockingLevel.blocks_calculation
        assert ind.recommended_action

    def test_mapped_inverter_has_no_unmapped_gap(self, db_session, site_id):
        inv = _device(db_session, site_id, DeviceCategories.inverter)
        _map_device(db_session, inv)
        resp = svc.compute_site_eligibility_diagnostics(
            db_session, site=_site(db_session, site_id)
        )
        row = _by_id(resp, inv.id)
        assert row.is_mapped is True
        keys = {i.key for i in row.indicators}
        assert svc.IND_EXPECTED_DRIVER_UNMAPPED not in keys

    def test_meter_is_inspection_only_not_expected(self, db_session, site_id):
        meter = _device(db_session, site_id, DeviceCategories.meter)
        resp = svc.compute_site_eligibility_diagnostics(
            db_session, site=_site(db_session, site_id)
        )
        row = _by_id(resp, meter.id)
        assert row.mappable is True
        assert row.can_drive_expected is False
        assert row.production_meter_capable is True
        keys = {i.key for i in row.indicators}
        assert svc.IND_METER_INSPECTION_ONLY in keys
        # An unmapped meter is informational, never a calculation blocker.
        levels = {i.blocking_level for i in row.indicators}
        assert DiagnosticBlockingLevel.blocks_calculation not in levels

    def test_weather_device_without_declaration_lowers_confidence(
        self, db_session, site_id
    ):
        ws = _device(db_session, site_id, DeviceCategories.weather_station)
        resp = svc.compute_site_eligibility_diagnostics(
            db_session, site=_site(db_session, site_id)
        )
        row = _by_id(resp, ws.id)
        assert row.weather_source_capable is True
        assert row.weather_semantics is not None
        assert row.weather_semantics.has_declaration is False
        keys = {i.key for i in row.indicators}
        assert svc.IND_WEATHER_SEMANTICS_UNDECLARED in keys
        ind = next(
            i for i in row.indicators if i.key == svc.IND_WEATHER_SEMANTICS_UNDECLARED
        )
        assert ind.blocking_level == DiagnosticBlockingLevel.lowers_confidence

    def test_weather_device_with_poa_cell_declaration_is_physics_usable(
        self, db_session, site_id
    ):
        ws = _device(db_session, site_id, DeviceCategories.weather_station)
        WeatherDeviceMappingCRUD(db_session).create(
            site_id=site_id,
            device_id=ws.id,
            metric="poa_irradiance",
            irradiance_plane=WeatherIrradiancePlane.poa,
            temperature_type=WeatherTemperatureType.cell,
            calibration_status=WeatherCalibrationStatus.calibrated,
        )
        resp = svc.compute_site_eligibility_diagnostics(
            db_session, site=_site(db_session, site_id)
        )
        row = _by_id(resp, ws.id)
        assert row.weather_semantics.has_declaration is True
        assert row.weather_semantics.physics_usable_irradiance is True
        assert row.weather_semantics.physics_usable_temperature is True
        keys = {i.key for i in row.indicators}
        assert svc.IND_WEATHER_SEMANTICS_UNDECLARED not in keys
        assert svc.IND_WEATHER_SEMANTICS_UNKNOWN not in keys
        assert svc.IND_WEATHER_NOT_PHYSICS_USABLE not in keys

    def test_ineligible_device_reported(self, db_session, site_id):
        modem = _device(db_session, site_id, DeviceCategories.modem)
        resp = svc.compute_site_eligibility_diagnostics(
            db_session, site=_site(db_session, site_id)
        )
        row = _by_id(resp, modem.id)
        assert row.mappable is False
        keys = {i.key for i in row.indicators}
        assert svc.IND_DEVICE_INELIGIBLE in keys

    def test_site_rollup_dedupes_and_counts(self, db_session, site_id):
        _device(db_session, site_id, DeviceCategories.inverter)
        _device(db_session, site_id, DeviceCategories.inverter)
        _device(db_session, site_id, DeviceCategories.meter)
        resp = svc.compute_site_eligibility_diagnostics(
            db_session, site=_site(db_session, site_id)
        )
        # Two unmapped inverters collapse to a single rollup indicator key.
        rollup_keys = [i.key for i in resp.indicators]
        assert rollup_keys.count(svc.IND_EXPECTED_DRIVER_UNMAPPED) == 1
        assert resp.expected_driving_count == 2
        assert resp.meter_count == 1
        assert resp.total_devices == 3

    def test_service_is_read_only(self, db_session, site_id):
        _device(db_session, site_id, DeviceCategories.inverter)
        db_session.commit()
        # A clean session must report no pending writes after diagnostics run.
        svc.compute_site_eligibility_diagnostics(
            db_session, site=_site(db_session, site_id)
        )
        assert not db_session.new
        assert not db_session.dirty
        assert not db_session.deleted
