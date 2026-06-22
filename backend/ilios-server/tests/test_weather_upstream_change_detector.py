"""WS.3 — tests for the upstream-change / stale re-review detector.

Two layers:

* **Pure fingerprint** (no DB): :mod:`app.services.weather.upstream_fingerprint`
  builds a deterministic upstream-identity snapshot and compares two snapshots. A
  missing baseline never diverges; ``schema_version`` is ignored; blank/whitespace
  normalizes to absent; ``changed_keys`` is sorted.
* **Detector against the real DB** (with the WS.1 append-only trigger installed):
  :func:`detect_site` is strictly read-only; :func:`apply_re_review` raises the
  monotonic ``needs_re_review`` flag (+ reason + ledger) on diverged, not-already
  flagged ACTIVE declarations, is idempotent, ignores drafts, and NEVER writes
  ``expected_weather_provenance``.

The DB layer reuses the WS.2 fixtures (``weather_guard``, ``db_session``, ``site``,
``device``, ``document``, ``system_user_id``) and the same teardown shape, so a
governed UPDATE always satisfies both the policy and the append-only guard.
Divergence is simulated by mutating ``device.source_provider`` (a fingerprint
input that is NOT guard-protected — it lives on ``devices``, not on the governed
mapping) after the declaration's fingerprint was captured at draft creation.
"""
from __future__ import annotations

from types import SimpleNamespace

import pytest
from sqlalchemy import text

from app.db.weather_declaration_guard import APPLY_GUARD_SQL, REMOVE_GUARD_SQL
from app.models.weather import (
    ExpectedWeatherProvenance,
    WeatherApprovalAction,
    WeatherDeclarationBasis,
    WeatherCalibrationStatus,
    WeatherDeclarationStatus,
    WeatherIrradiancePlane,
    WeatherSourceApproval,
    WeatherTemperatureType,
)
from app.schema.weather import WeatherDeviceMappingDeclareRequest
from app.services.weather.declaration_service import (
    activate_declaration,
    create_declaration,
)
from app.services.weather.upstream_change_detector import (
    apply_re_review,
    detect_site,
)
from app.services.weather.upstream_fingerprint import (
    FINGERPRINT_SCHEMA_VERSION,
    compare_fingerprint,
    compute_upstream_fingerprint,
)
from tests.conftest import engine

METRIC = "irradiance_wm2"


# ---------------------------------------------------------------------------
# Pure fingerprint tests (no DB)
# ---------------------------------------------------------------------------
class TestComputeFingerprint:
    def _device(self, **overrides):
        base = dict(
            category="weather_station",
            type="irradiance_sensor",
            device_role=None,
            source_provider="acme",
            external_device_type="poa_cell",
            telemetry_mapping=SimpleNamespace(
                provider_account_id=7, telemetry_device_id="dev-1"
            ),
        )
        base.update(overrides)
        return SimpleNamespace(**base)

    def _mapping(self, **overrides):
        base = dict(
            metric=METRIC,
            provider_key="prov",
            external_device_id="ext-1",
            weather_source_id=3,
            sensor_model="LI-200",
        )
        base.update(overrides)
        return SimpleNamespace(**base)

    def test_includes_schema_version_and_identity_keys(self):
        fp = compute_upstream_fingerprint(self._device(), self._mapping())
        assert fp["schema_version"] == FINGERPRINT_SCHEMA_VERSION
        assert fp["metric"] == METRIC
        assert fp["source_provider"] == "acme"
        assert fp["device_category"] == "weather_station"
        assert fp["link_provider_account_id"] == 7
        assert fp["link_telemetry_device_id"] == "dev-1"

    def test_none_device_yields_none_descriptors_not_error(self):
        fp = compute_upstream_fingerprint(None, self._mapping())
        assert fp["device_category"] is None
        assert fp["link_provider_account_id"] is None
        # Governed stream identity still comes from the mapping.
        assert fp["metric"] == METRIC

    def test_blank_strings_normalize_to_none(self):
        fp = compute_upstream_fingerprint(
            self._device(source_provider="   "), self._mapping()
        )
        assert fp["source_provider"] is None


class TestCompareFingerprint:
    def _fp(self, **overrides):
        base = dict(
            schema_version=FINGERPRINT_SCHEMA_VERSION,
            metric=METRIC,
            source_provider="acme",
            device_category="weather_station",
        )
        base.update(overrides)
        return base

    def test_missing_baseline_never_diverges(self):
        assert compare_fingerprint(None, self._fp()) == {
            "diverged": False,
            "changed_keys": [],
            "summary": None,
        }
        assert compare_fingerprint({}, self._fp())["diverged"] is False

    def test_identical_does_not_diverge(self):
        assert compare_fingerprint(self._fp(), self._fp())["diverged"] is False

    def test_schema_version_change_alone_is_ignored(self):
        stored = self._fp(schema_version=99)
        assert compare_fingerprint(stored, self._fp())["diverged"] is False

    def test_changed_field_diverges_with_sorted_keys(self):
        stored = self._fp()
        current = self._fp(source_provider="other", device_category="meter")
        result = compare_fingerprint(stored, current)
        assert result["diverged"] is True
        assert result["changed_keys"] == ["device_category", "source_provider"]
        assert result["summary"]
        assert "source_provider" in result["summary"]


# ---------------------------------------------------------------------------
# Detector against the real DB (mirrors the WS.2 harness)
# ---------------------------------------------------------------------------
def _run_guard_ddl(statements) -> None:
    with engine.begin() as conn:
        conn.execute(text("SET LOCAL lock_timeout = '15s'"))
        for stmt in statements:
            conn.execute(text(stmt))


@pytest.fixture()
def weather_guard(db_session):
    """Install the WS.1 append-only trigger, then remove it (WS.2 pattern)."""
    db_session.rollback()
    _run_guard_ddl(APPLY_GUARD_SQL)
    yield
    db_session.rollback()
    _run_guard_ddl(REMOVE_GUARD_SQL)


@pytest.fixture(autouse=True)
def _cleanup_weather_rows(db_session, site, device):
    """Drop governed weather rows BEFORE the ``device`` fixture tears down."""
    yield
    db_session.rollback()
    db_session.execute(
        text("DELETE FROM weather_source_approvals WHERE site_id = :sid"),
        {"sid": site.id},
    )
    db_session.execute(
        text("DELETE FROM weather_device_mappings WHERE site_id = :sid"),
        {"sid": site.id},
    )
    db_session.commit()


def _payload(device, **overrides) -> WeatherDeviceMappingDeclareRequest:
    base = dict(
        device_id=device.id,
        metric=METRIC,
        declaration_basis=WeatherDeclarationBasis.source_document,
        irradiance_plane=WeatherIrradiancePlane.poa,
        temperature_type=WeatherTemperatureType.unknown,
        calibration_status=WeatherCalibrationStatus.calibrated,
        calibrated_at="2026-01-01T00:00:00",
        calibration_reference="cert-123",
        sensor_role="poa_reference",
    )
    base.update(overrides)
    return WeatherDeviceMappingDeclareRequest(**base)


def _ledger_actions(db, target_id: int) -> list[str]:
    rows = (
        db.query(WeatherSourceApproval)
        .filter(WeatherSourceApproval.target_id == target_id)
        .order_by(WeatherSourceApproval.id)
        .all()
    )
    return [getattr(r.action, "value", r.action) for r in rows]


def _draft(db, site, device, document, actor, **overrides):
    return create_declaration(
        db,
        site=site,
        device=device,
        payload=_payload(device, source_document_id=document.id, **overrides),
        actor_id=actor,
    )


def _active(db, site, device, document, actor, **overrides):
    draft = _draft(db, site, device, document, actor, **overrides)
    return activate_declaration(
        db,
        site=site,
        mapping_id=draft.id,
        actor_id=actor,
        rationale="Reviewed and confirmed.",
    )


def _diverge_device(db, device) -> None:
    """Mutate a fingerprint input on the device so the stored snapshot diverges."""
    device.source_provider = "REPOINTED-PROVIDER"
    db.add(device)
    db.commit()


def _provenance_count(db) -> int:
    return db.query(ExpectedWeatherProvenance).count()


class TestDetectSite:
    def test_fingerprint_captured_at_creation(
        self, weather_guard, db_session, site, device, document, system_user_id
    ):
        draft = _draft(db_session, site, device, document, system_user_id)
        assert isinstance(draft.upstream_fingerprint_json, dict)
        assert draft.upstream_fingerprint_json["metric"] == METRIC

    def test_empty_site_reports_no_active(
        self, weather_guard, db_session, site
    ):
        report = detect_site(db_session, site=site)
        assert report.applied is False
        assert report.total_active == 0
        assert report.diverged_count == 0
        assert report.mappings == []

    def test_no_divergence_when_device_unchanged(
        self, weather_guard, db_session, site, device, document, system_user_id
    ):
        _active(db_session, site, device, document, system_user_id)
        report = detect_site(db_session, site=site)
        assert report.total_active == 1
        assert report.diverged_count == 0
        assert report.would_flag_count == 0
        assert report.mappings[0].has_stored_fingerprint is True

    def test_drafts_are_ignored(
        self, weather_guard, db_session, site, device, document, system_user_id
    ):
        _draft(db_session, site, device, document, system_user_id)
        report = detect_site(db_session, site=site)
        assert report.total_active == 0

    def test_divergence_is_detected_but_not_written(
        self, weather_guard, db_session, site, device, document, system_user_id
    ):
        active = _active(db_session, site, device, document, system_user_id)
        _diverge_device(db_session, device)

        report = detect_site(db_session, site=site)
        assert report.applied is False
        assert report.diverged_count == 1
        assert report.would_flag_count == 1
        row = report.mappings[0]
        assert row.diverged is True
        assert "source_provider" in row.changed_keys
        assert row.would_flag is True
        assert row.flagged is False

        # Strictly read-only: no flag raised, no ledger entry appended.
        db_session.refresh(active)
        assert active.needs_re_review is False
        assert active.re_review_reason is None
        assert _ledger_actions(db_session, active.id) == [
            WeatherApprovalAction.declare_draft.value,
            WeatherApprovalAction.activate.value,
        ]


class TestApplyReReview:
    def test_flags_diverged_row(
        self, weather_guard, db_session, site, device, document, system_user_id
    ):
        active = _active(db_session, site, device, document, system_user_id)
        prov_before = _provenance_count(db_session)
        _diverge_device(db_session, device)

        report = apply_re_review(
            db_session, site=site, actor_id=system_user_id
        )
        assert report.applied is True
        assert report.diverged_count == 1
        assert report.newly_flagged_count == 1
        assert report.mappings[0].flagged is True
        assert report.mappings[0].needs_re_review is True

        db_session.refresh(active)
        assert active.needs_re_review is True
        assert active.re_review_reason
        assert _ledger_actions(db_session, active.id) == [
            WeatherApprovalAction.declare_draft.value,
            WeatherApprovalAction.activate.value,
            WeatherApprovalAction.needs_re_review.value,
        ]
        # WS.3 boundary: expected_weather_provenance is NEVER written.
        assert _provenance_count(db_session) == prov_before

    def test_idempotent_skips_already_flagged(
        self, weather_guard, db_session, site, device, document, system_user_id
    ):
        active = _active(db_session, site, device, document, system_user_id)
        _diverge_device(db_session, device)

        first = apply_re_review(db_session, site=site, actor_id=system_user_id)
        assert first.newly_flagged_count == 1

        second = apply_re_review(db_session, site=site, actor_id=system_user_id)
        assert second.newly_flagged_count == 0
        assert second.already_flagged_count == 1
        assert second.diverged_count == 1
        assert second.mappings[0].flagged is False
        assert second.mappings[0].needs_re_review is True

        # The ledger was stamped exactly once (no double needs_re_review entry).
        db_session.refresh(active)
        assert _ledger_actions(db_session, active.id).count(
            WeatherApprovalAction.needs_re_review.value
        ) == 1

    def test_no_divergence_flags_nothing(
        self, weather_guard, db_session, site, device, document, system_user_id
    ):
        active = _active(db_session, site, device, document, system_user_id)
        report = apply_re_review(
            db_session, site=site, actor_id=system_user_id
        )
        assert report.applied is True
        assert report.diverged_count == 0
        assert report.newly_flagged_count == 0

        db_session.refresh(active)
        assert active.needs_re_review is False
        assert _ledger_actions(db_session, active.id) == [
            WeatherApprovalAction.declare_draft.value,
            WeatherApprovalAction.activate.value,
        ]
