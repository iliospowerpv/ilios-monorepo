"""Integration tests for /api/telemetry/v2/companies/{id}/provider-accounts.

Verifies CRUD, write-only credential redaction, and cross-tenant 404.
"""
from unittest.mock import Mock

import pytest

from app.crud.company import CompanyCRUD
from app.helpers.authentication import get_current_user
from app.schema.user import CurrentUserSchema
from tests.conftest import get_test_session, test_app


def _admin_user(limited_companies=None):
    user = Mock(spec=CurrentUserSchema)
    user.id = 1
    user.is_system_user = False
    user.role = Mock()
    user.role.permissions = {
        "Telemetry": {"admin": True},
        "Settings Page": {"edit": True},
    }
    user.get_limited_companies_ids = lambda: list(limited_companies or [])
    user.get_limited_sites_ids = lambda: []
    return user


def _system_user():
    user = _admin_user()
    user.is_system_user = True
    return user


@pytest.fixture(scope="function")
def two_companies():
    db = next(get_test_session())
    crud = CompanyCRUD(db)
    a = crud.create_item({"name": "Tel V2 Acct Co A", "company_type": "Portfolio Management"})
    b = crud.create_item({"name": "Tel V2 Acct Co B", "company_type": "Portfolio Management"})
    db.commit()
    yield a, b


def _grant_license(client, cid, provider_key="also_energy"):
    r = client.post(
        f"/api/telemetry/v2/companies/{cid}/licensed-providers",
        json={"provider_key": provider_key},
    )
    assert r.status_code in (200, 201), r.text


class TestProviderAccountCRUD:
    def setup_method(self):
        test_app.dependency_overrides[get_current_user] = _system_user

    def teardown_method(self):
        test_app.dependency_overrides.pop(get_current_user, None)

    def test_create_response_never_contains_credential_value(self, client, two_companies):
        company, _ = two_companies
        cid = company.id
        _grant_license(client, cid)

        secret_token = "ZZSECRET_NEVER_LEAKS_42"
        r = client.post(
            f"/api/telemetry/v2/companies/{cid}/provider-accounts",
            json={
                "name": "Primary AlsoEnergy",
                "provider_key": "also_energy",
                "external_account_label": "primary",
                "credentials": {"fields": {"token": secret_token}},
            },
        )
        assert r.status_code == 201, r.text
        body = r.json()

        # Credential value MUST NOT appear anywhere in the response.
        assert secret_token not in r.text
        assert "credentials" not in body  # write-only field
        # Three-state model exposed.
        for key in ("status", "credential_status", "last_sync_status"):
            assert key in body, key
        # Optional fingerprint may be present but must not contain raw token.
        if body.get("credentials_fingerprint"):
            assert secret_token not in body["credentials_fingerprint"]

    def test_create_requires_credentials(self, client, two_companies):
        company, _ = two_companies
        _grant_license(client, company.id)
        r = client.post(
            f"/api/telemetry/v2/companies/{company.id}/provider-accounts",
            json={
                "name": "No-Creds Account",
                "provider_key": "also_energy",
                "credentials": {"fields": {}},
            },
        )
        assert r.status_code == 422

    def test_list_excludes_archived_by_default(self, client, two_companies):
        company, _ = two_companies
        cid = company.id
        _grant_license(client, cid)

        r = client.post(
            f"/api/telemetry/v2/companies/{cid}/provider-accounts",
            json={
                "name": "To-Archive",
                "provider_key": "also_energy",
                "credentials": {"fields": {"token": "tok"}},
            },
        )
        assert r.status_code == 201
        account_id = r.json()["id"]

        # Archive
        r = client.delete(
            f"/api/telemetry/v2/companies/{cid}/provider-accounts/{account_id}"
        )
        assert r.status_code in (204, 200)

        # Default list excludes archived
        r = client.get(f"/api/telemetry/v2/companies/{cid}/provider-accounts")
        assert r.status_code == 200
        assert all(item["id"] != account_id for item in r.json()["items"])

        # include_archived returns it
        r = client.get(
            f"/api/telemetry/v2/companies/{cid}/provider-accounts?include_archived=true"
        )
        assert r.status_code == 200
        assert any(item["id"] == account_id for item in r.json()["items"])


class TestCrossTenantIsolation:
    def test_user_limited_to_company_a_gets_404_for_company_b(self, client, two_companies):
        company_a, company_b = two_companies

        # Use system user briefly to seed a license + account on company B.
        test_app.dependency_overrides[get_current_user] = _system_user
        try:
            _grant_license(client, company_b.id)
            r = client.post(
                f"/api/telemetry/v2/companies/{company_b.id}/provider-accounts",
                json={
                    "name": "On Company B",
                    "provider_key": "also_energy",
                    "credentials": {"fields": {"token": "tok"}},
                },
            )
            assert r.status_code == 201
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)

        # Switch to a user limited to company A only — must NOT see company B.
        test_app.dependency_overrides[get_current_user] = lambda: _admin_user(
            limited_companies=[company_a.id]
        )
        try:
            r = client.get(
                f"/api/telemetry/v2/companies/{company_b.id}/provider-accounts"
            )
            assert r.status_code == 404, (
                f"Cross-tenant must 404, got {r.status_code}: {r.text}"
            )
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)
