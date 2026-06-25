"""Phase 0 — baseline lifecycle authorization helpers (unit level).

These guard the backend source of truth for baseline lifecycle authority:
``approve``/``activate`` require BOTH telemetry-admin AND company-admin for the
baseline's owning company (or a platform-bypass user). Draft-authoring and
read-only review stay at telemetry-admin only. The structured 403 handler is
asserted directly so the machine-readable body shape is locked in.

Everything here is read-only against authorization state except a single seeded
``user_company_access`` membership (cleaned up on teardown). Nothing touches
baselines, expected math, ingestion, the resolver, or any telemetry write path.
"""
from __future__ import annotations

import asyncio
import json
from unittest.mock import Mock

import pytest

from app.helpers.authorization.module_based.telemetry import (
    BaselineLifecycleForbiddenError,
    baseline_lifecycle_forbidden_handler,
    can_author_draft,
    can_manage_baseline_lifecycle,
    enforce_baseline_lifecycle_authority,
    user_is_company_admin,
)
from app.crud.user_company_access import UserCompanyAccessCRUD
from app.models.user import CompanyRole, MembershipStatus
from app.schema.user import CurrentUserSchema


def _mk_user(user_id, *, telemetry_admin=False, bypass=False):
    """A CurrentUserSchema-shaped mock.

    ``has_platform_bypass`` is set explicitly (the helpers read it as a direct
    attribute; a ``spec``-ed Mock would otherwise raise ``AttributeError``).
    """
    user = Mock(spec=CurrentUserSchema)
    user.id = user_id
    user.has_platform_bypass = bypass
    user.is_system_user = bypass
    user.role = Mock()
    user.role.permissions = {"Telemetry": {"admin": True}} if telemetry_admin else {}
    return user


@pytest.fixture(scope="function")
def company_admin_user(db_session, create_non_system_user, company_id):
    """A real user seeded as an ACTIVE company-admin of the test company."""
    crud = UserCompanyAccessCRUD(db_session)
    membership = crud.add_membership(
        user_id=create_non_system_user.id,
        company_id=company_id,
        role=CompanyRole.company_admin,
        status=MembershipStatus.active,
    )
    yield create_non_system_user
    crud.delete_by_id(membership.id)


# ---------------------------------------------------------------------------
# enforce_baseline_lifecycle_authority
# ---------------------------------------------------------------------------
def test_platform_bypass_passes_enforcement(db_session, company_id):
    """A platform-bypass user is authorized regardless of company-admin state."""
    user = _mk_user(999_001, telemetry_admin=False, bypass=True)
    # Does not raise.
    enforce_baseline_lifecycle_authority(
        db_session, user, company_id=company_id, action_code="approve"
    )
    assert can_manage_baseline_lifecycle(db_session, user, company_id) is True
    assert user_is_company_admin(db_session, user, company_id) is True


def test_non_telemetry_admin_raises_telemetry_admin_required(db_session, company_id):
    """No telemetry-admin permission -> fails closed with the telemetry reason."""
    user = _mk_user(999_002, telemetry_admin=False, bypass=False)
    with pytest.raises(BaselineLifecycleForbiddenError) as exc_info:
        enforce_baseline_lifecycle_authority(
            db_session, user, company_id=company_id, action_code="activate"
        )
    err = exc_info.value
    assert err.action_code == "activate"
    assert err.reason_code == "telemetry_admin_required"
    assert err.company_id == company_id
    assert can_manage_baseline_lifecycle(db_session, user, company_id) is False


def test_telemetry_admin_without_company_admin_raises_company_admin_required(
    db_session, company_id
):
    """Telemetry-admin but NOT company-admin -> fails closed with the company reason.

    This is the central Phase 0 tightening: telemetry-admin alone is no longer
    sufficient to mutate the lifecycle. Draft-authoring, however, stays allowed.
    """
    # An id with no user_company_access membership -> not a company admin.
    user = _mk_user(999_003, telemetry_admin=True, bypass=False)
    with pytest.raises(BaselineLifecycleForbiddenError) as exc_info:
        enforce_baseline_lifecycle_authority(
            db_session, user, company_id=company_id, action_code="approve"
        )
    assert exc_info.value.reason_code == "company_admin_required"
    assert can_manage_baseline_lifecycle(db_session, user, company_id) is False
    # Draft-authoring is telemetry-admin only, so it remains True.
    assert can_author_draft(user) is True


def test_telemetry_admin_with_company_admin_passes(
    db_session, company_id, company_admin_user
):
    """Telemetry-admin AND company-admin -> authorized (no raise)."""
    user = _mk_user(company_admin_user.id, telemetry_admin=True, bypass=False)
    enforce_baseline_lifecycle_authority(
        db_session, user, company_id=company_id, action_code="activate"
    )
    assert can_manage_baseline_lifecycle(db_session, user, company_id) is True
    assert user_is_company_admin(db_session, user, company_id) is True


def test_company_admin_is_scoped_to_the_owning_company(
    db_session, company_id, company_admin_user
):
    """Company-admin of company A is NOT company-admin of a different company."""
    user = _mk_user(company_admin_user.id, telemetry_admin=True, bypass=False)
    other_company_id = company_id + 10_000  # no membership exists for this company
    assert user_is_company_admin(db_session, user, other_company_id) is False
    assert (
        can_manage_baseline_lifecycle(db_session, user, other_company_id) is False
    )
    with pytest.raises(BaselineLifecycleForbiddenError) as exc_info:
        enforce_baseline_lifecycle_authority(
            db_session, user, company_id=other_company_id, action_code="approve"
        )
    assert exc_info.value.reason_code == "company_admin_required"


# ---------------------------------------------------------------------------
# Capability helpers
# ---------------------------------------------------------------------------
def test_can_author_draft_is_telemetry_admin_only():
    """Draft-authoring needs telemetry-admin; company-admin is irrelevant here."""
    assert can_author_draft(_mk_user(1, telemetry_admin=True, bypass=False)) is True
    assert can_author_draft(_mk_user(2, telemetry_admin=False, bypass=False)) is False
    assert can_author_draft(_mk_user(3, telemetry_admin=False, bypass=True)) is True


# ---------------------------------------------------------------------------
# Structured 403 handler
# ---------------------------------------------------------------------------
def test_forbidden_handler_renders_structured_body(company_id):
    """The handler renders a machine-readable 403 body (not a flattened string)."""
    exc = BaselineLifecycleForbiddenError(
        action_code="approve",
        reason_code="company_admin_required",
        company_id=company_id,
    )
    response = asyncio.run(baseline_lifecycle_forbidden_handler(None, exc))
    assert response.status_code == 403
    body = json.loads(response.body)
    assert body["error"] == "baseline_approve_forbidden"
    assert body["action"] == "approve"
    assert body["reason"] == "company_admin_required"
    assert isinstance(body["message"], str) and body["message"]
    assert body["required_roles"] == ["telemetry_admin", "company_admin"]
