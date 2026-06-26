"""Phase 0 + Phase 1 — baseline lifecycle endpoints (router smoke tests).

Exercises the FastAPI layer end-to-end via the TestClient:

* Phase 0 — approve/activate are gated (telemetry-admin AND company-admin, or
  platform bypass); a forbidden caller gets a structured 403 and mutates nothing
  (fail-closed, zero side effects). The list endpoint is telemetry-admin-only and
  carries viewer capability flags; the active endpoint is enveloped + flagged.
* Phase 1 — the telemetry-admin draft-preview endpoint renders a draft/approved
  baseline without activating it, 409s an active/superseded baseline, 404s a
  cross-site baseline, and the public expected-preview still 409s a draft.

These run against a fresh per-test throwaway site (the function-scoped ``site``
fixture), never a protected/live site. Writes are limited to the baselines each
test seeds (cleaned up on teardown). The deep authorization matrix lives in the
``baseline_lifecycle_authorization_test`` unit suite.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from unittest.mock import Mock

import pytest

import app.helpers.telemetry.audit as audit_mod
import app.routers.telemetry.v2 as v2_router
from app.crud.site import SiteCRUD
from app.helpers.authentication import get_current_user
from app.models.audit_log import AuditLog
from app.models.telemetry_expected import (
    TelemetryBaselineStatus,
    TelemetryBaselineType,
    TelemetryExpectedBaseline,
)
from app.schema.user import CurrentUserSchema
from tests.conftest import test_app
from tests.unit import samples

WAM = TelemetryBaselineType.weather_adjusted_model


def _system_user():
    """Telemetry-admin / platform-bypass user (mirrors the v2 integration tests)."""
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
    """No platform bypass, no telemetry-admin permission -> fails closed."""
    user = Mock(spec=CurrentUserSchema)
    user.id = 2
    user.is_system_user = False
    user.has_platform_bypass = False
    user.role = Mock()
    user.role.permissions = {}
    user.get_limited_companies_ids = lambda: []
    user.get_limited_sites_ids = lambda: []
    return user


def _telemetry_admin_no_company():
    """Telemetry-admin but NOT company-admin and NOT platform bypass.

    id ``987654`` has no ``user_company_access`` membership, so the lifecycle gate
    must deny with ``company_admin_required``.
    """
    user = Mock(spec=CurrentUserSchema)
    user.id = 987_654
    user.is_system_user = False
    user.has_platform_bypass = False
    user.role = Mock()
    user.role.permissions = {"Telemetry": {"admin": True}}
    user.get_limited_companies_ids = lambda: []
    user.get_limited_sites_ids = lambda: []
    return user


def _make_baseline(db_session, company_id, site_id, *, status, version=1, physics=True, **overrides):
    """Seed a baseline row directly. ``physics=True`` makes it activation-valid."""
    fields = dict(
        company_id=company_id,
        site_id=site_id,
        baseline_name=f"lifecycle-test-{status.value}-{version}",
        baseline_type=WAM,
        status=status,
        version=version,
    )
    if physics:
        fields.update(
            pto_date=date(2026, 5, 11),
            module_wattage=340.0,
            module_quantity=1900.0,
            inverter_wattage=66.0,
            inverter_quantity=7.0,
            thermal_coefficient_pct=-0.35,
            power_tolerance_min_pct=0.0,
            year_1_degradation_pct=2.5,
            annual_degradation_pct=0.73,
            cec_efficiency_pct=97.0,
            soiling_factor=1.0,
            dc_loss_pct=2.0,
            ac_loss_pct=1.0,
            medium_voltage_loss_pct=0.0,
            mv_line_loss_pct=0.0,
        )
    fields.update(overrides)
    baseline = TelemetryExpectedBaseline(**fields)
    db_session.add(baseline)
    db_session.commit()
    db_session.refresh(baseline)
    return baseline


@pytest.fixture(scope="function")
def draft_baseline(db_session, company_id, site_id):
    """A physics-incomplete (thin) DRAFT baseline.

    Thin so the draft-preview read-time validation is blocking -> the curve is
    suppressed deterministically (no dependence on seeded readings/weather).
    """
    baseline = _make_baseline(
        db_session, company_id, site_id, status=TelemetryBaselineStatus.draft, physics=False
    )
    yield baseline
    db_session.query(TelemetryExpectedBaseline).filter_by(id=baseline.id).delete()
    db_session.commit()


@pytest.fixture(scope="function")
def approved_baseline(db_session, company_id, site_id):
    """A physics-valid APPROVED baseline (activation-ready)."""
    baseline = _make_baseline(
        db_session, company_id, site_id, status=TelemetryBaselineStatus.approved
    )
    yield baseline
    db_session.query(TelemetryExpectedBaseline).filter_by(id=baseline.id).delete()
    db_session.commit()


@pytest.fixture(scope="function")
def active_baseline(db_session, company_id, site_id):
    """A physics-valid ACTIVE baseline (not draft-previewable)."""
    baseline = _make_baseline(
        db_session,
        company_id,
        site_id,
        status=TelemetryBaselineStatus.active,
        active_from=datetime(2026, 5, 11),
    )
    yield baseline
    db_session.query(TelemetryExpectedBaseline).filter_by(id=baseline.id).delete()
    db_session.commit()


@pytest.fixture(scope="function")
def other_site(db_session, company_id):
    """A second site (same company) for cross-site isolation checks."""
    crud = SiteCRUD(db_session)
    payload = dict(samples.TEST_SITE_BODY)
    payload["company_id"] = company_id
    site = crud.create_item(payload)
    yield site
    crud.delete_by_id(site.id)


class TestBaselineLifecycleEndpoints:
    def setup_method(self):
        test_app.dependency_overrides[get_current_user] = _system_user

    def teardown_method(self):
        test_app.dependency_overrides.pop(get_current_user, None)

    # -- Phase 0: approve/activate gating ----------------------------------
    def test_approve_forbidden_for_non_admin_no_side_effect(
        self, client, db_session, draft_baseline
    ):
        """A non-admin cannot approve; the baseline stays a draft (zero writes)."""
        test_app.dependency_overrides[get_current_user] = _non_admin_user
        r = client.post(f"/api/telemetry/v2/expected-baselines/{draft_baseline.id}/approve")
        assert r.status_code == 403, r.text
        db_session.refresh(draft_baseline)
        assert draft_baseline.status == TelemetryBaselineStatus.draft

    def test_approve_lifecycle_forbidden_structured_body_no_side_effect(
        self, client, db_session, site, draft_baseline, monkeypatch
    ):
        """Telemetry-admin without company-admin -> structured 403, nothing mutated.

        Site visibility is patched to a passthrough so the lifecycle gate (not the
        resolver) is the thing under test; the gate must still deny.
        """
        monkeypatch.setattr(
            v2_router, "get_authorized_site_with_company_admin", lambda *_a, **_k: site
        )
        test_app.dependency_overrides[get_current_user] = _telemetry_admin_no_company
        r = client.post(f"/api/telemetry/v2/expected-baselines/{draft_baseline.id}/approve")
        assert r.status_code == 403, r.text
        body = r.json()
        assert body["error"] == "baseline_approve_forbidden"
        assert body["reason"] == "company_admin_required"
        assert body["required_roles"] == ["telemetry_admin", "company_admin"]
        db_session.refresh(draft_baseline)
        assert draft_baseline.status == TelemetryBaselineStatus.draft

    def test_approve_succeeds_for_platform_bypass(self, client, db_session, draft_baseline):
        """A platform-bypass admin can approve a draft baseline."""
        r = client.post(f"/api/telemetry/v2/expected-baselines/{draft_baseline.id}/approve")
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "approved"
        db_session.refresh(draft_baseline)
        assert draft_baseline.status == TelemetryBaselineStatus.approved

    def test_activate_succeeds_for_platform_bypass(
        self, client, db_session, approved_baseline
    ):
        """A platform-bypass admin can activate a physics-valid approved baseline."""
        r = client.post(
            f"/api/telemetry/v2/expected-baselines/{approved_baseline.id}/activate"
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "active"
        db_session.refresh(approved_baseline)
        assert approved_baseline.status == TelemetryBaselineStatus.active

    # -- Phase 0: tightened reads ------------------------------------------
    def test_list_baselines_forbidden_for_non_admin(self, client, site_id, draft_baseline):
        """The lifecycle-history list is telemetry-admin only now."""
        test_app.dependency_overrides[get_current_user] = _non_admin_user
        r = client.get(f"/api/telemetry/v2/sites/{site_id}/expected-baselines")
        assert r.status_code == 403, r.text

    def test_list_baselines_flags_for_bypass(self, client, site_id, draft_baseline):
        """A bypass admin sees the list plus both capability flags as True."""
        r = client.get(f"/api/telemetry/v2/sites/{site_id}/expected-baselines")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["viewer_can_manage_lifecycle"] is True
        assert body["viewer_can_author_draft"] is True
        assert any(b["id"] == draft_baseline.id for b in body["baselines"])

    def test_active_endpoint_is_enveloped_with_flags(
        self, client, site_id, active_baseline
    ):
        """The active endpoint returns an envelope (baseline + viewer flags)."""
        r = client.get(f"/api/telemetry/v2/sites/{site_id}/expected-baselines/active")
        assert r.status_code == 200, r.text
        body = r.json()
        assert "baseline" in body
        assert body["baseline"] is not None
        assert body["baseline"]["id"] == active_baseline.id
        assert body["viewer_can_manage_lifecycle"] is True
        assert body["viewer_can_author_draft"] is True

    # -- Phase 1: draft-preview --------------------------------------------
    def test_draft_preview_renders_draft_baseline(self, client, site_id, draft_baseline):
        """A draft baseline is previewable; a blocking verdict suppresses the curve."""
        r = client.get(
            f"/api/telemetry/v2/sites/{site_id}/expected-baseline/"
            f"{draft_baseline.id}/draft-preview"
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["is_draft_preview"] is True
        assert body["baseline_status"] == "draft"
        assert body["validation_summary"] is not None
        assert isinstance(body["disclaimer"], str) and body["disclaimer"]
        # Thin (physics-incomplete) draft -> blocking -> curve suppressed, never 0.
        assert body["validation_summary"]["is_blocking"] is True
        assert body["overall_status"] == "baseline_invalid"
        assert body["buckets"] == []
        assert body["expected_energy_kwh"] is None

    def test_draft_preview_rejects_active_baseline_409(
        self, client, site_id, active_baseline
    ):
        """An active baseline is not draft-previewable (use the public preview)."""
        r = client.get(
            f"/api/telemetry/v2/sites/{site_id}/expected-baseline/"
            f"{active_baseline.id}/draft-preview"
        )
        assert r.status_code == 409, r.text

    def test_draft_preview_cross_site_returns_404(
        self, client, other_site, draft_baseline
    ):
        """A baseline from another site is invisible here (cross-site isolation)."""
        r = client.get(
            f"/api/telemetry/v2/sites/{other_site.id}/expected-baseline/"
            f"{draft_baseline.id}/draft-preview"
        )
        assert r.status_code == 404, r.text

    def test_draft_preview_forbidden_for_non_admin(
        self, client, site_id, draft_baseline
    ):
        """Draft-preview is telemetry-admin gated."""
        test_app.dependency_overrides[get_current_user] = _non_admin_user
        r = client.get(
            f"/api/telemetry/v2/sites/{site_id}/expected-baseline/"
            f"{draft_baseline.id}/draft-preview"
        )
        assert r.status_code == 403, r.text

    def test_public_preview_still_409s_a_draft(self, client, site_id, draft_baseline):
        """The public expected-preview must still refuse a never-approved draft."""
        r = client.get(
            f"/api/telemetry/v2/sites/{site_id}/expected-preview",
            params={"baseline_id": draft_baseline.id},
        )
        assert r.status_code == 409, r.text


class TestBaselineLifecycleAuditEvents:
    """Phase B3 Tier 1 — best-effort ``audit_logs`` events for lifecycle actions.

    Every event is ``source="telemetry_baseline"`` with a JSON-encoded ``details``
    string. The audit write is best-effort: it must never block, roll back, or
    otherwise alter the lifecycle outcome.
    """

    BASELINE_AUDIT_SOURCE = "telemetry_baseline"

    def setup_method(self):
        test_app.dependency_overrides[get_current_user] = _system_user

    def teardown_method(self):
        test_app.dependency_overrides.pop(get_current_user, None)

    def _audit_rows(self, db_session, baseline_id, action=None):
        # ``details`` is JSON with sort_keys -> ``"baseline_id": <id>,`` is always
        # followed by another key, so the trailing comma makes the match exact
        # (no 12 vs 120 prefix collision).
        query = db_session.query(AuditLog).filter(
            AuditLog.source == self.BASELINE_AUDIT_SOURCE,
            AuditLog.details.like(f'%"baseline_id": {baseline_id},%'),
        )
        if action is not None:
            query = query.filter(AuditLog.action == action)
        return query.all()

    def _cleanup_audit(self, db_session, baseline_id):
        db_session.query(AuditLog).filter(
            AuditLog.source == self.BASELINE_AUDIT_SOURCE,
            AuditLog.details.like(f'%"baseline_id": {baseline_id},%'),
        ).delete(synchronize_session=False)
        db_session.commit()

    def test_approve_writes_audit_event(self, client, db_session, draft_baseline):
        """A successful approve writes one ``baseline_approved`` audit row."""
        r = client.post(
            f"/api/telemetry/v2/expected-baselines/{draft_baseline.id}/approve"
        )
        assert r.status_code == 200, r.text
        try:
            rows = self._audit_rows(db_session, draft_baseline.id, "baseline_approved")
            assert len(rows) == 1
            row = rows[0]
            assert row.is_success is True
            assert row.user_id == 1
            payload = json.loads(row.details)
            assert payload["baseline_id"] == draft_baseline.id
            assert payload["site_id"] == draft_baseline.site_id
            assert payload["prior_status"] == "draft"
        finally:
            self._cleanup_audit(db_session, draft_baseline.id)

    def test_activate_writes_audit_event_with_supersession_folded(
        self, client, db_session, approved_baseline
    ):
        """A successful activate writes one ``baseline_activated`` row.

        Supersession is folded into this single event (no separate superseded
        event), and the details carry the activation context.
        """
        r = client.post(
            f"/api/telemetry/v2/expected-baselines/{approved_baseline.id}/activate"
        )
        assert r.status_code == 200, r.text
        try:
            rows = self._audit_rows(
                db_session, approved_baseline.id, "baseline_activated"
            )
            assert len(rows) == 1
            row = rows[0]
            assert row.is_success is True
            assert row.user_id == 1
            payload = json.loads(row.details)
            assert payload["baseline_id"] == approved_baseline.id
            assert payload["site_id"] == approved_baseline.site_id
            # Supersession folded in (None when nothing was replaced).
            assert "supersedes_baseline_id" in payload
            assert payload["active_from"]  # ISO-8601 string
            assert payload["acknowledged_warnings"] is False
            assert payload["source_note"] is None
            assert "policy_version" in payload
        finally:
            self._cleanup_audit(db_session, approved_baseline.id)

    def test_activation_blocked_invalid_status_audits_without_mutation(
        self, client, db_session, draft_baseline
    ):
        """A draft cannot be activated -> ``baseline_activation_blocked`` (no write)."""
        r = client.post(
            f"/api/telemetry/v2/expected-baselines/{draft_baseline.id}/activate"
        )
        assert r.status_code == 409, r.text
        try:
            rows = self._audit_rows(
                db_session, draft_baseline.id, "baseline_activation_blocked"
            )
            assert len(rows) == 1
            row = rows[0]
            assert row.is_success is False
            payload = json.loads(row.details)
            assert payload["reason"] == "invalid_status"
            # No mutation: the baseline is still a draft.
            db_session.refresh(draft_baseline)
            assert draft_baseline.status == TelemetryBaselineStatus.draft
        finally:
            self._cleanup_audit(db_session, draft_baseline.id)

    def test_activation_blocked_hard_invalid_audits_without_mutation(
        self, client, db_session, company_id, site_id
    ):
        """An approved-but-physics-incomplete baseline -> physics block + audit.

        The physics gate raises before any mutation, so the baseline stays
        ``approved`` and the blocked attempt is recorded (best-effort).
        """
        baseline = _make_baseline(
            db_session,
            company_id,
            site_id,
            status=TelemetryBaselineStatus.approved,
            physics=False,
        )
        try:
            r = client.post(
                f"/api/telemetry/v2/expected-baselines/{baseline.id}/activate"
            )
            assert r.status_code == 409, r.text
            assert r.json()["reason"] == "hard_invalid"
            rows = self._audit_rows(
                db_session, baseline.id, "baseline_activation_blocked"
            )
            assert len(rows) == 1
            assert rows[0].is_success is False
            assert json.loads(rows[0].details)["reason"] == "hard_invalid"
            db_session.refresh(baseline)
            assert baseline.status == TelemetryBaselineStatus.approved
        finally:
            self._cleanup_audit(db_session, baseline.id)
            db_session.query(TelemetryExpectedBaseline).filter_by(
                id=baseline.id
            ).delete()
            db_session.commit()

    def test_audit_write_failure_does_not_break_activation(
        self, client, db_session, approved_baseline, monkeypatch
    ):
        """If the audit backend fails, activation must still succeed (isolation).

        The helper swallows the write failure; the activation was already
        committed and the response is unaffected. No audit row is persisted.
        """

        class _BoomCRUD:
            def __init__(self, *_a, **_k):
                pass

            def create_item(self, *_a, **_k):
                raise RuntimeError("audit backend down")

        monkeypatch.setattr(audit_mod, "AuditLogCRUD", _BoomCRUD)
        r = client.post(
            f"/api/telemetry/v2/expected-baselines/{approved_baseline.id}/activate"
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "active"
        # Activation persisted despite the audit failure.
        db_session.refresh(approved_baseline)
        assert approved_baseline.status == TelemetryBaselineStatus.active
        # The failed audit write left no row behind.
        rows = self._audit_rows(
            db_session, approved_baseline.id, "baseline_activated"
        )
        assert rows == []
