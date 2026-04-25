"""Integration tests for POST /provider-accounts/{id}/sync-sites.

Verifies upsert provenance (new vs missing counts) and status transitions.
The provider adapter is replaced with a fake so no network call happens.
"""
from unittest.mock import Mock

import pytest

from app.crud.company import CompanyCRUD
from app.helpers.authentication import get_current_user
from app.integrations.telemetry import registry
from app.integrations.telemetry.models import ExternalSiteRecord, TestResult
from app.schema.user import CurrentUserSchema
from tests.conftest import get_test_session, test_app


class FakeAdapter:
    provider_key = "also_energy"

    def __init__(self, sites):
        self._sites = sites

    def test_credentials(self, credentials):  # noqa: ARG002
        return TestResult(success=True, message="ok", available_sites_count=len(self._sites))

    def list_sites(self, credentials):  # noqa: ARG002
        return [
            ExternalSiteRecord(external_site_id=str(s["id"]), external_site_name=s.get("name"))
            for s in self._sites
        ]


def _system_user():
    user = Mock(spec=CurrentUserSchema)
    user.id = 1
    user.is_system_user = True
    user.role = Mock()
    user.role.permissions = {"Telemetry": {"admin": True}}
    user.get_limited_companies_ids = lambda: []
    user.get_limited_sites_ids = lambda: []
    return user


@pytest.fixture(scope="function")
def company_with_account(client, monkeypatch):
    db = next(get_test_session())
    company = CompanyCRUD(db).create_item(
        {"name": "Tel V2 Sync Co", "company_type": "Portfolio Management"}
    )
    db.commit()
    cid = company.id

    test_app.dependency_overrides[get_current_user] = _system_user
    try:
        r = client.post(
            f"/api/telemetry/v2/companies/{cid}/licensed-providers",
            json={"provider_key": "also_energy"},
        )
        assert r.status_code in (200, 201), r.text

        r = client.post(
            f"/api/telemetry/v2/companies/{cid}/provider-accounts",
            json={
                "name": "Sync Account",
                "provider_key": "also_energy",
                "credentials": {"fields": {"token": "tok"}},
            },
        )
        assert r.status_code == 201, r.text
        account_id = r.json()["id"]
        yield cid, account_id
    finally:
        test_app.dependency_overrides.pop(get_current_user, None)


def _install_fake_adapter(monkeypatch, sites):
    fake = FakeAdapter(sites)
    monkeypatch.setattr(registry, "get_adapter", lambda *a, **kw: fake)


class TestSyncSitesProvenance:
    def setup_method(self):
        test_app.dependency_overrides[get_current_user] = _system_user

    def teardown_method(self):
        test_app.dependency_overrides.pop(get_current_user, None)

    def test_first_sync_marks_all_as_new(self, client, company_with_account, monkeypatch):
        cid, account_id = company_with_account
        _install_fake_adapter(monkeypatch, [{"id": "ext-1"}, {"id": "ext-2"}])

        r = client.post(f"/api/telemetry/v2/provider-accounts/{account_id}/sync-sites")
        assert r.status_code in (200, 202), r.text
        body = r.json()
        assert body["new_count"] == 2
        assert body["missing_count"] == 0
        assert body["seen_count"] == 2
        assert body["last_sync_status"] in ("ok", "success")
        assert body["sync_run_id"]

    def test_second_sync_with_same_sites_is_idempotent(
        self, client, company_with_account, monkeypatch
    ):
        cid, account_id = company_with_account
        _install_fake_adapter(monkeypatch, [{"id": "ext-1"}, {"id": "ext-2"}])

        r1 = client.post(f"/api/telemetry/v2/provider-accounts/{account_id}/sync-sites")
        assert r1.status_code in (200, 202)

        r2 = client.post(f"/api/telemetry/v2/provider-accounts/{account_id}/sync-sites")
        assert r2.status_code in (200, 202)
        body = r2.json()
        assert body["new_count"] == 0
        assert body["missing_count"] == 0
        assert body["seen_count"] == 2

    def test_dropped_site_marked_missing(
        self, client, company_with_account, monkeypatch
    ):
        cid, account_id = company_with_account
        _install_fake_adapter(monkeypatch, [{"id": "ext-1"}, {"id": "ext-2"}])
        client.post(f"/api/telemetry/v2/provider-accounts/{account_id}/sync-sites")

        # Provider now omits ext-2
        _install_fake_adapter(monkeypatch, [{"id": "ext-1"}])
        r = client.post(f"/api/telemetry/v2/provider-accounts/{account_id}/sync-sites")
        body = r.json()
        assert body["seen_count"] == 1
        assert body["missing_count"] >= 1

    def test_external_sites_listing_after_sync(
        self, client, company_with_account, monkeypatch
    ):
        cid, account_id = company_with_account
        _install_fake_adapter(monkeypatch, [{"id": "ext-1", "name": "Site One"}])
        client.post(f"/api/telemetry/v2/provider-accounts/{account_id}/sync-sites")

        r = client.get(f"/api/telemetry/v2/provider-accounts/{account_id}/external-sites")
        assert r.status_code == 200, r.text
        body = r.json()
        ids = {item["external_site_id"] for item in body["items"]}
        assert "ext-1" in ids
