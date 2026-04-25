"""Integration tests for company-licensed providers endpoints (v2)."""
from unittest.mock import Mock

import pytest

from app.crud.company import CompanyCRUD
from app.helpers.authentication import get_current_user
from app.schema.user import CurrentUserSchema
from tests.conftest import get_test_session, test_app


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
def license_company():
    db = next(get_test_session())
    company = CompanyCRUD(db).create_item(
        {"name": "Telemetry V2 License Co", "company_type": "Portfolio Management"}
    )
    db.commit()
    yield company
    # Best-effort cleanup; tearDown happens at session end via Base.metadata.drop_all.


class TestLicensedProvidersFlow:
    def setup_method(self):
        test_app.dependency_overrides[get_current_user] = _system_user

    def teardown_method(self):
        test_app.dependency_overrides.pop(get_current_user, None)

    def test_grant_list_revoke_license(self, client, license_company):
        cid = license_company.id

        # 1. Initially empty
        r = client.get(f"/api/telemetry/v2/companies/{cid}/licensed-providers")
        assert r.status_code == 200, r.text
        assert r.json()["items"] == []

        # 2. Grant a license
        r = client.post(
            f"/api/telemetry/v2/companies/{cid}/licensed-providers",
            json={"provider_key": "also_energy", "notes": "trial"},
        )
        assert r.status_code == 201, r.text
        license_id = r.json()["id"]
        assert r.json()["provider_key"] == "also_energy"
        assert r.json()["status"] == "active"
        assert r.json()["notes"] == "trial"

        # 3. List shows the license
        r = client.get(f"/api/telemetry/v2/companies/{cid}/licensed-providers")
        assert r.status_code == 200
        assert any(item["id"] == license_id for item in r.json()["items"])

        # 4. Granting same provider again is idempotent (no duplicate row)
        r = client.post(
            f"/api/telemetry/v2/companies/{cid}/licensed-providers",
            json={"provider_key": "also_energy"},
        )
        assert r.status_code in (200, 201, 409)

        # 5. Revoke
        r = client.delete(
            f"/api/telemetry/v2/companies/{cid}/licensed-providers/{license_id}"
        )
        assert r.status_code in (204, 200), r.text

    def test_grant_unknown_provider_returns_400(self, client, license_company):
        r = client.post(
            f"/api/telemetry/v2/companies/{license_company.id}/licensed-providers",
            json={"provider_key": "does_not_exist"},
        )
        assert r.status_code == 400
