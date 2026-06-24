"""Integration tests for the inventory-reconciliation acknowledgement endpoints.

Focus: CROSS-TENANT REJECTION. Every acknowledgement endpoint
(GET list / POST create / POST revoke) calls ``_enforce_company_visibility``
before touching the service, so a user limited to company A must never be able
to read, create, or revoke acknowledgements on a site that belongs to company B.

``get_authorized_site`` is overridden to hand the endpoint the company-B site
directly; this isolates the endpoint's OWN company-visibility guard (rather than
the generic site authorizer) and proves the cross-tenant 404 originates inside
the acknowledgement endpoints themselves. The body sent on the write paths is a
fully valid payload so the request reaches the endpoint function (a malformed
body would 422 during validation, before the guard runs).
"""
import copy
import itertools
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from app.crud.company import CompanyCRUD
from app.helpers.authentication import get_current_user
from app.helpers.authorization.project_access import get_authorized_site
from app.services.telemetry.device_inventory_reconciliation_service import (
    RECONCILIATION_VERSION,
)
from tests.conftest import get_test_session, test_app
from tests.unit import samples

_SEQ = itertools.count(1)


def _make_company(crud):
    payload = copy.deepcopy(samples.SETUP_COMPANIES[0])
    suffix = next(_SEQ)
    payload["name"] = f"InvAck Co {suffix}"
    if payload.get("email"):
        local, _, domain = payload["email"].partition("@")
        payload["email"] = f"{local}+invack{suffix}@{domain or 'example.com'}"
    return crud.create_item(payload)


def _asset_user(limited_companies):
    """A non-bypass user with Asset Management view+edit, limited to given companies."""
    user = Mock()
    user.id = 1
    user.is_system_user = False
    user.has_platform_bypass = False
    user.role = Mock()
    user.role.name = "Limited Asset Manager"
    user.role.permissions = {"Asset Management": {"view": True, "edit": True}}
    user.get_limited_companies_ids = lambda: list(limited_companies)
    user.get_limited_sites_ids = lambda: []
    return user


@pytest.fixture(scope="function")
def two_companies():
    db = next(get_test_session())
    crud = CompanyCRUD(db)
    a = _make_company(crud)
    b = _make_company(crud)
    db.commit()
    yield a, b


class TestInventoryAckCrossTenant:
    def teardown_method(self):
        test_app.dependency_overrides.pop(get_current_user, None)
        test_app.dependency_overrides.pop(get_authorized_site, None)

    def _bind(self, company_a_id, site_b):
        test_app.dependency_overrides[get_current_user] = lambda: _asset_user([company_a_id])
        test_app.dependency_overrides[get_authorized_site] = lambda: site_b

    def test_list_acks_cross_tenant_404(self, client, two_companies):
        company_a, company_b = two_companies
        site_b = SimpleNamespace(id=98765, company_id=company_b.id)
        self._bind(company_a.id, site_b)

        r = client.get(
            f"/api/telemetry/v2/sites/{site_b.id}/inventory-reconciliation/acknowledgements"
        )
        assert r.status_code == 404, f"cross-tenant list must 404, got {r.status_code}: {r.text}"

    def test_create_ack_cross_tenant_404(self, client, two_companies):
        company_a, company_b = two_companies
        site_b = SimpleNamespace(id=98765, company_id=company_b.id)
        self._bind(company_a.id, site_b)

        r = client.post(
            f"/api/telemetry/v2/sites/{site_b.id}/inventory-reconciliation/acknowledgements",
            json={
                "mismatch_signature": "any-signature",
                "reconciliation_version": RECONCILIATION_VERSION,
                "acknowledgement_reason": "Cross-tenant attempt that must be rejected.",
            },
        )
        assert r.status_code == 404, f"cross-tenant create must 404, got {r.status_code}: {r.text}"

    def test_revoke_ack_cross_tenant_404(self, client, two_companies):
        company_a, company_b = two_companies
        site_b = SimpleNamespace(id=98765, company_id=company_b.id)
        self._bind(company_a.id, site_b)

        r = client.post(
            f"/api/telemetry/v2/sites/{site_b.id}/inventory-reconciliation/acknowledgements/1/revoke",
            json={"revocation_reason": "Cross-tenant attempt that must be rejected."},
        )
        assert r.status_code == 404, f"cross-tenant revoke must 404, got {r.status_code}: {r.text}"
