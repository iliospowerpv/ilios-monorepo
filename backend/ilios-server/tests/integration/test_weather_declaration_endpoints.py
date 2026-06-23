"""WS.4 — router smoke tests for the governed weather-semantics endpoints.

These are the deferred WS.2 router-level checks (auth / site-scoping /
``DeclarationServiceError`` -> HTTP translation) plus WS.4 read-only
reconciliation-endpoint coverage. They exercise the FastAPI layer end-to-end via
the TestClient; the deep lifecycle/policy behavior is covered by the WS.1/WS.2/WS.3
service-level suites.

Everything here is additive and read-mostly: the only writes are a draft
declaration created through the public endpoint. Nothing touches the
WeatherResolver, expected math, ingestion, rollups, the scheduler, baselines,
``expected_weather_provenance``, or O&M.
"""
from __future__ import annotations

from unittest.mock import Mock

import pytest

from app.crud.device import DeviceCRUD
from app.helpers.authentication import get_current_user
from app.models.telemetry import TelemetryDeviceMapping
from app.schema.user import CurrentUserSchema
from tests.conftest import test_app


def _system_user():
    """Telemetry-admin / platform-bypass user (mirrors the v2 integration tests).

    ``has_platform_bypass`` is set explicitly: the project-access resolver reads it
    as a direct attribute (no ``getattr`` default), and a ``spec``-ed Mock raises
    ``AttributeError`` for attributes that are never assigned.
    """
    user = Mock(spec=CurrentUserSchema)
    user.id = 1
    user.is_system_user = True
    user.has_platform_bypass = True
    user.role = Mock()
    user.role.permissions = {"Telemetry": {"admin": True}}
    user.get_limited_companies_ids = lambda: []
    user.get_limited_sites_ids = lambda: []
    return user


def _non_admin_user():
    """A non-privileged user: no platform bypass, no telemetry-admin permission.

    The effective-access resolver denies a user with no real grants, so any
    admin-gated declaration endpoint must fail closed with a 403.
    """
    user = Mock(spec=CurrentUserSchema)
    user.id = 2
    user.is_system_user = False
    user.has_platform_bypass = False
    user.role = Mock()
    user.role.permissions = {}
    user.get_limited_companies_ids = lambda: []
    user.get_limited_sites_ids = lambda: []
    return user


@pytest.fixture(scope="function")
def weather_device(db_session, site_id):
    """A weather-source-capable device (Weather Station) on the test site."""
    crud = DeviceCRUD(db_session)
    device = crud.create_item(
        {
            "status": "available_inventory",
            "asset_id": "WX-SEMANTICS-0001",
            "name": "Test Weather Station",
            "category": "weather_station",
            "site_id": site_id,
        }
    )
    yield device
    crud.delete_by_id(device.id)


@pytest.fixture(scope="function")
def observed_weather_device(db_session, weather_device):
    """A weather-source-capable device that is OBSERVED (telemetry-mapped).

    Adding a ``TelemetryDeviceMapping`` makes the device "observed" so the
    reconciliation reports state 1
    (``observed_weather_device_no_governed_declaration``) rather than the generic
    ``weather_source_missing`` source-axis state. Teardown runs before the
    ``weather_device`` teardown, so the mapping is removed before its device.
    """
    mapping = TelemetryDeviceMapping(
        device_id=weather_device.id,
        telemetry_device_id="WX-TELE-0001",
        telemetry_device_name="Test Weather Telemetry",
    )
    db_session.add(mapping)
    db_session.commit()
    yield weather_device
    db_session.delete(mapping)
    db_session.commit()


class TestWeatherDeclarationEndpoints:
    def setup_method(self):
        test_app.dependency_overrides[get_current_user] = _system_user

    def teardown_method(self):
        test_app.dependency_overrides.pop(get_current_user, None)

    # -- auth / scoping -----------------------------------------------------
    def test_declare_requires_telemetry_admin(self, client, site_id):
        """A non-admin caller cannot declare weather semantics (fails closed)."""
        test_app.dependency_overrides[get_current_user] = _non_admin_user
        r = client.post(
            f"/api/weather/sites/{site_id}/device-mappings",
            json={
                "device_id": 1,
                "metric": "irradiance_wm2",
                "declaration_basis": "source_document",
            },
        )
        assert r.status_code == 403, r.text

    def test_declare_missing_device_returns_404(self, client, site_id):
        """Declaring against a device that is not on the site is a clean 404."""
        r = client.post(
            f"/api/weather/sites/{site_id}/device-mappings",
            json={
                "device_id": 99_999_999,
                "metric": "irradiance_wm2",
                "declaration_basis": "source_document",
            },
        )
        assert r.status_code == 404, r.text

    def test_declare_non_weather_device_returns_422(self, client, site_id, device):
        """A non-weather device (inverter) is not weather-source capable -> 422.

        Semantics are never inferred from a non-weather device.
        """
        r = client.post(
            f"/api/weather/sites/{site_id}/device-mappings",
            json={
                "device_id": device.id,
                "metric": "irradiance_wm2",
                "declaration_basis": "source_document",
            },
        )
        assert r.status_code == 422, r.text

    def test_activate_missing_mapping_translates_to_404(self, client, site_id):
        """``DeclarationServiceError`` (mapping not found) is translated to HTTP 404."""
        r = client.post(
            f"/api/weather/sites/{site_id}/device-mappings/99_999_999/activate",
            json={},
        )
        assert r.status_code == 404, r.text

    # -- reconciliation (read-only) ----------------------------------------
    def test_reconciliation_reports_weather_source_missing(
        self, client, site_id, weather_device
    ):
        """An UNOBSERVED weather device (no telemetry mapping, no readings) with no
        weather source is the source-missing state."""
        r = client.get(f"/api/weather/sites/{site_id}/semantics-reconciliation")
        assert r.status_code == 200, r.text
        body = r.json()

        assert body["site_id"] == site_id
        assert body["has_weather_source"] is False
        assert body["has_active_weather_profile"] is False
        assert body["total_weather_capable_devices"] >= 1

        row = next(d for d in body["devices"] if d["device_id"] == weather_device.id)
        # Undeclared semantics + not observed + no usable source => source-axis wins.
        assert row["reconciliation_state"] == "weather_source_missing"
        assert row["declaration_state"] == "source_exists_semantics_unknown"
        assert row["source_state"] == "weather_source_missing"
        assert row["expected_model_eligible"] is False
        assert row["needs_re_review"] is False
        # Layer-1 never blocks calculation.
        assert row["blocking_level"] in ("lowers_confidence", "informational")
        # Semantics are never inferred — nothing declared stays unknown.
        assert row["irradiance_plane"] in (None, "unknown")

    def test_reconciliation_observed_device_no_declaration(
        self, client, site_id, observed_weather_device
    ):
        """An OBSERVED weather device with no declaration is taxonomy state 1
        (observed_weather_device_no_governed_declaration), never the generic
        weather_source_missing source-axis state — even though the site still has
        no registered weather source."""
        r = client.get(f"/api/weather/sites/{site_id}/semantics-reconciliation")
        assert r.status_code == 200, r.text
        body = r.json()

        row = next(
            d
            for d in body["devices"]
            if d["device_id"] == observed_weather_device.id
        )
        assert (
            row["reconciliation_state"]
            == "observed_weather_device_no_governed_declaration"
        )
        # The declaration axis is still "no governed value"...
        assert row["declaration_state"] == "source_exists_semantics_unknown"
        # ...and the source axis still honestly discloses the missing source.
        assert row["source_state"] == "weather_source_missing"
        assert row["expected_model_eligible"] is False
        assert row["needs_re_review"] is False
        # Layer-1 never blocks calculation; the gap only lowers confidence.
        assert row["blocking_level"] in ("lowers_confidence", "informational")
        # Semantics are never inferred — observation is not a declaration.
        assert row["irradiance_plane"] in (None, "unknown")

    def test_declare_draft_then_reconciliation_shows_draft(
        self, client, site_id, weather_device
    ):
        """A recorded draft keeps its declaration state as the headline (not overlaid).

        A ``reviewer_assumption`` draft only needs the confirmation flag + note at
        create time; no document evidence is required to record the draft.
        """
        r = client.post(
            f"/api/weather/sites/{site_id}/device-mappings",
            json={
                "device_id": weather_device.id,
                "metric": "irradiance_wm2",
                "declaration_basis": "reviewer_assumption",
                "assumption_confirmed": True,
                "reviewer_note": "Test assumption: POA reference per site survey.",
            },
        )
        assert r.status_code == 201, r.text
        created = r.json()
        assert created["declaration_status"] == "draft"
        assert created["declaration_basis"] == "reviewer_assumption"

        recon = client.get(
            f"/api/weather/sites/{site_id}/semantics-reconciliation"
        )
        assert recon.status_code == 200, recon.text
        row = next(
            d
            for d in recon.json()["devices"]
            if d["device_id"] == weather_device.id
        )
        # Draft is not state 1, so the source gap never hides it.
        assert row["reconciliation_state"] == "declaration_draft"
        assert row["declaration_state"] == "declaration_draft"
        assert row["declaration_status"] == "draft"
        assert row["expected_model_eligible"] is False

    def test_declare_assumption_requires_confirmation_returns_422(
        self, client, site_id, weather_device
    ):
        """A ``reviewer_assumption`` draft without confirmation is rejected (422)."""
        r = client.post(
            f"/api/weather/sites/{site_id}/device-mappings",
            json={
                "device_id": weather_device.id,
                "metric": "irradiance_wm2",
                "declaration_basis": "reviewer_assumption",
                "reviewer_note": "Missing the confirmation flag.",
            },
        )
        assert r.status_code == 422, r.text
