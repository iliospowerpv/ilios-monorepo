"""Phase 4 — non-destructive device classification backfill.

Guards the backfill's safety contract:

* it fills NULL classification columns from the shared classifier;
* it is idempotent — a second run makes no further changes and never overwrites an
  operator-set value;
* ``dry_run`` computes the plan but commits nothing;
* it NEVER mutates telemetry device mappings, and it ABORTS (rolls back) if a
  protected site's mapping count would change.
"""
from __future__ import annotations

import copy
import itertools

import pytest

from app.crud.device import DeviceCRUD
from app.models.device import Device, DeviceCategories
from app.models.telemetry import TelemetryDeviceMapping
from app.services.telemetry.device_classification import DeviceRole
from scripts import backfill_device_classification as bf

_NAME_SEQ = itertools.count(1)


@pytest.fixture(scope="module")
def company_id(db_session):
    from app.crud.company import CompanyCRUD
    from tests.unit import samples

    payload = copy.deepcopy(samples.SETUP_COMPANIES[0])
    suffix = next(_NAME_SEQ)
    payload["name"] = f"{payload['name']} BFCo-{suffix}"
    if payload.get("email"):
        local, _, domain = payload["email"].partition("@")
        payload["email"] = f"{local}+bfco{suffix}@{domain or 'example.com'}"
    return CompanyCRUD(db_session).create_item(payload).id


@pytest.fixture()
def site_id(db_session, company_id) -> int:
    from app.crud.site import SiteCRUD
    from tests.unit import samples

    payload = copy.deepcopy(samples.TEST_SITE_BODY)
    payload["company_id"] = company_id
    payload["name"] = f"{payload['name']} BF-{next(_NAME_SEQ)}"
    return SiteCRUD(db_session).create_item(payload).id


def _device(db_session, site_id, category: DeviceCategories, **overrides):
    payload = {
        "name": f"BF {category.name} {next(_NAME_SEQ)}",
        "category": category.name,
        "site_id": site_id,
    }
    payload.update(overrides)
    return DeviceCRUD(db_session).create_item(payload)


class TestBackfill:
    def test_fills_null_columns_from_classifier(self, db_session, site_id):
        inv = _device(db_session, site_id, DeviceCategories.inverter)
        meter = _device(db_session, site_id, DeviceCategories.meter)
        assert inv.device_role is None and meter.device_role is None

        summary = bf.backfill_device_classification(db_session, site_id=site_id)
        assert summary["devices_updated"] >= 2
        assert summary["dry_run"] is False

        db_session.refresh(inv)
        db_session.refresh(meter)
        assert inv.device_role == DeviceRole.inverter.value
        assert inv.telemetry_capable is True
        assert meter.device_role == DeviceRole.meter.value
        assert meter.production_meter_capable is True
        # The expected gate is NOT a backfilled column and stays derived-only.

    def test_is_idempotent(self, db_session, site_id):
        _device(db_session, site_id, DeviceCategories.inverter)
        first = bf.backfill_device_classification(db_session, site_id=site_id)
        assert first["fields_filled"] > 0
        second = bf.backfill_device_classification(db_session, site_id=site_id)
        assert second["devices_updated"] == 0
        assert second["fields_filled"] == 0

    def test_does_not_overwrite_operator_set_value(self, db_session, site_id):
        dev = _device(db_session, site_id, DeviceCategories.network_connection)
        dev.device_role = DeviceRole.power_logger.value
        db_session.commit()

        bf.backfill_device_classification(db_session, site_id=site_id)
        db_session.refresh(dev)
        # Operator's explicit role is preserved (NULL-only fill).
        assert dev.device_role == DeviceRole.power_logger.value

    def test_dry_run_commits_nothing(self, db_session, site_id):
        inv = _device(db_session, site_id, DeviceCategories.inverter)
        db_session.commit()
        summary = bf.backfill_device_classification(
            db_session, site_id=site_id, dry_run=True
        )
        assert summary["dry_run"] is True
        assert summary["devices_updated"] >= 1
        # Re-read from a fresh query: nothing persisted.
        db_session.expire_all()
        reloaded = db_session.query(Device).filter(Device.id == inv.id).one()
        assert reloaded.device_role is None

    def test_never_touches_mappings(self, db_session, site_id):
        dev = _device(db_session, site_id, DeviceCategories.inverter)
        db_session.add(
            TelemetryDeviceMapping(
                device_id=dev.id,
                telemetry_device_id=f"ext-{dev.id}",
                telemetry_device_name=f"External {dev.id}",
            )
        )
        db_session.commit()
        before = (
            db_session.query(TelemetryDeviceMapping)
            .filter(TelemetryDeviceMapping.device_id == dev.id)
            .count()
        )
        bf.backfill_device_classification(db_session, site_id=site_id)
        after = (
            db_session.query(TelemetryDeviceMapping)
            .filter(TelemetryDeviceMapping.device_id == dev.id)
            .count()
        )
        assert before == after == 1

    def test_aborts_when_protected_mapping_changes(
        self, db_session, site_id, monkeypatch
    ):
        _device(db_session, site_id, DeviceCategories.inverter)

        calls = {"n": 0}

        def _fake_fingerprint(db, site_ids):
            # Return a different "after" snapshot to simulate tampering.
            calls["n"] += 1
            return {4: [(calls["n"], "ext", "name", None, "primary", True)]}

        monkeypatch.setattr(bf, "_mapping_fingerprint", _fake_fingerprint)
        with pytest.raises(
            RuntimeError, match="Protected site telemetry mappings changed"
        ):
            bf.backfill_device_classification(db_session, site_id=site_id)
