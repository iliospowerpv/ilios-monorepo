"""Phase 3 — weather device measurement semantics (additive W0 wiring).

Guards the contract that a device's weather *meaning* is DECLARED, never guessed:

* a device must be weather-source capable before semantics can attach;
* irradiance / temperature / reference-cell devices ARE weather-source capable;
* declarations default to ``unknown`` and stay ``unknown`` until explicitly set;
* an explicit POA / cell declaration persists and is disclosed as physics-usable;
* GHI / ambient are stored verbatim and NEVER upgraded to POA / cell (no
  conversion); the disclosure flags only report, they never promote;
* declarations are append-only (versioned by new row) — the latest row wins and
  earlier history is preserved.

DB-backed cases create their own company/site/device via CRUD (mirroring the W2
suite) so no FastAPI lifespan is spun up.
"""
from __future__ import annotations

import copy
import itertools
import types

import pytest

from app.crud import weather as weather_crud
from app.crud.device import DeviceCRUD
from app.models.device import DeviceCategories, DeviceTypes
from app.models.weather import (
    WeatherCalibrationStatus,
    WeatherIrradiancePlane,
    WeatherTemperatureType,
)
from app.schema.weather import WeatherDeviceMappingResponse
from app.services.telemetry.device_classification import DeviceRole, classify_device

_NAME_SEQ = itertools.count(1)


# ---------------------------------------------------------------------------
# Local FK fixtures (created via CRUD — no FastAPI lifespan).
# ---------------------------------------------------------------------------
@pytest.fixture(scope="module")
def company_id(db_session):
    from app.crud.company import CompanyCRUD
    from tests.unit import samples

    payload = copy.deepcopy(samples.SETUP_COMPANIES[0])
    suffix = next(_NAME_SEQ)
    payload["name"] = f"{payload['name']} WDMCo-{suffix}"
    if payload.get("email"):
        local, _, domain = payload["email"].partition("@")
        payload["email"] = f"{local}+wdmco{suffix}@{domain or 'example.com'}"
    return CompanyCRUD(db_session).create_item(payload).id


@pytest.fixture()
def site_id(db_session, company_id) -> int:
    from app.crud.site import SiteCRUD
    from tests.unit import samples

    payload = copy.deepcopy(samples.TEST_SITE_BODY)
    payload["company_id"] = company_id
    payload["name"] = f"{payload['name']} WDM-{next(_NAME_SEQ)}"
    return SiteCRUD(db_session).create_item(payload).id


def _make_weather_device(db_session, site_id, **overrides):
    payload = {
        "name": f"WDM Weather {next(_NAME_SEQ)}",
        "category": DeviceCategories.weather_station.name,
        "site_id": site_id,
    }
    payload.update(overrides)
    return DeviceCRUD(db_session).create_item(payload)


def _declare(db_session, site_id, device_id, **kw):
    defaults = dict(site_id=site_id, device_id=device_id, metric="irradiance")
    defaults.update(kw)
    return weather_crud.WeatherDeviceMappingCRUD(db_session).create(**defaults)


# ---------------------------------------------------------------------------
# Weather-source capability (gate for declaring semantics)
# ---------------------------------------------------------------------------
def _stub(category=None, **kw):
    return types.SimpleNamespace(category=category, **kw)


class TestWeatherSourceCapability:
    def test_weather_station_capable(self):
        assert classify_device(_stub(DeviceCategories.weather_station)).weather_source_capable

    def test_irradiance_sensor_capable(self):
        device = _stub(DeviceCategories.weather_station, type=DeviceTypes.irradiance)
        assert classify_device(device).weather_source_capable

    def test_temperature_sensor_capable(self):
        device = _stub(DeviceCategories.weather_station, type=DeviceTypes.temperature)
        assert classify_device(device).weather_source_capable

    def test_reference_cell_role_capable(self):
        device = _stub(category=None, device_role=DeviceRole.reference_cell.value)
        assert classify_device(device).weather_source_capable

    def test_meter_is_not_weather_source_capable(self):
        assert not classify_device(_stub(DeviceCategories.meter)).weather_source_capable


# ---------------------------------------------------------------------------
# Declaration persistence + "unknown stays unknown" + no conversion
# ---------------------------------------------------------------------------
class TestDeclarationSemantics:
    def test_unknown_stays_unknown_by_default(self, db_session, site_id):
        device = _make_weather_device(db_session, site_id)
        mapping = _declare(db_session, site_id, device.id)
        assert mapping.irradiance_plane == WeatherIrradiancePlane.unknown
        assert mapping.temperature_type == WeatherTemperatureType.unknown
        assert mapping.calibration_status == WeatherCalibrationStatus.unknown

        resp = WeatherDeviceMappingResponse.from_model(mapping)
        assert resp.irradiance_plane == "unknown"
        assert resp.physics_usable_irradiance is False
        assert resp.physics_usable_temperature is False

    def test_poa_cell_declaration_persists(self, db_session, site_id):
        device = _make_weather_device(db_session, site_id)
        mapping = _declare(
            db_session,
            site_id,
            device.id,
            metric="poa_irradiance",
            irradiance_plane=WeatherIrradiancePlane.poa,
            temperature_type=WeatherTemperatureType.cell,
            calibration_status=WeatherCalibrationStatus.calibrated,
        )
        # Re-read from the DB to prove it persisted, not just held in the instance.
        reloaded = weather_crud.WeatherDeviceMappingCRUD(db_session).get_current_for_device(
            device.id
        )
        assert reloaded.id == mapping.id
        assert reloaded.irradiance_plane == WeatherIrradiancePlane.poa
        assert reloaded.temperature_type == WeatherTemperatureType.cell

        resp = WeatherDeviceMappingResponse.from_model(reloaded)
        assert resp.physics_usable_irradiance is True
        assert resp.physics_usable_temperature is True

    def test_ghi_and_ambient_are_never_upgraded(self, db_session, site_id):
        device = _make_weather_device(db_session, site_id)
        mapping = _declare(
            db_session,
            site_id,
            device.id,
            metric="ghi_irradiance",
            irradiance_plane=WeatherIrradiancePlane.ghi,
            temperature_type=WeatherTemperatureType.ambient,
        )
        resp = WeatherDeviceMappingResponse.from_model(mapping)
        # Stored verbatim, disclosed as NOT physics-usable — never converted to POA/cell.
        assert resp.irradiance_plane == "ghi"
        assert resp.temperature_type == "ambient"
        assert resp.physics_usable_irradiance is False
        assert resp.physics_usable_temperature is False

    def test_declarations_are_append_only_latest_wins(self, db_session, site_id):
        device = _make_weather_device(db_session, site_id)
        first = _declare(
            db_session, site_id, device.id, irradiance_plane=WeatherIrradiancePlane.unknown
        )
        second = _declare(
            db_session, site_id, device.id, irradiance_plane=WeatherIrradiancePlane.poa
        )
        crud = weather_crud.WeatherDeviceMappingCRUD(db_session)
        history = crud.list_for_device(device.id)
        # Both rows preserved (history never rewritten); newest wins as "current".
        assert [m.id for m in history] == [first.id, second.id]
        assert crud.get_current_for_device(device.id).id == second.id
        assert crud.get_current_for_device(device.id).irradiance_plane == (
            WeatherIrradiancePlane.poa
        )
