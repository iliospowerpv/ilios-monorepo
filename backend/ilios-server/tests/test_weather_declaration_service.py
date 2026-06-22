"""WS.2 — tests for the governed weather-declaration lifecycle SERVICE.

These exercise :mod:`app.services.weather.declaration_service` against the real
test database WITH the WS.1 append-only trigger installed, so every write the
service emits must satisfy both the governance policy (this layer) and the
append-only shape guard (WS.1). The harness builds the schema with
``Base.metadata.create_all`` (not migrations), so the ``weather_guard`` fixture
applies the canonical trigger SQL exactly as the migration does, then removes it.

Covered behaviors:

* ``create_declaration`` always INSERTs a ``draft`` (never auto-active) and writes
  the ``declare_draft`` ledger event; ``reviewer_assumption`` needs confirm + note.
* Cross-tenant evidence fails closed.
* ``activate_declaration`` enforces draft-only, full basis completeness,
  single-active, and explicit supersession — superseding leaves the prior row's
  semantic value columns byte-identical and back-links it.
* Activation captures an eligibility snapshot but never gates on eligibility.
* ``mark_needs_re_review`` is active-only, monotonic, and reason-required.
* ``get_current_for_device`` prefers the ACTIVE governed row.

The service commits on the shared session, so expected-failure tests roll back to
release row locks / discard the uncommitted draft; successful rows are cleaned up
by the function-scoped ``site`` fixture (``weather_device_mappings.site_id`` and
``weather_source_approvals.site_id`` are ``ON DELETE CASCADE``).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.db.weather_declaration_guard import APPLY_GUARD_SQL, REMOVE_GUARD_SQL
from app.models.weather import (
    WeatherApprovalAction,
    WeatherCalibrationStatus,
    WeatherDeclarationBasis,
    WeatherDeclarationStatus,
    WeatherDeviceMapping,
    WeatherIrradiancePlane,
    WeatherSourceApproval,
    WeatherTemperatureType,
)
from app.schema.weather import WeatherDeviceMappingDeclareRequest
from app.services.weather import declaration_service as decl_svc
from app.services.weather.declaration_service import (
    DeclarationServiceError,
    _validate_evidence_in_tenant,
    activate_declaration,
    create_declaration,
    mark_needs_re_review,
)
from tests.conftest import engine

METRIC = "irradiance_wm2"


# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------
def _run_guard_ddl(statements) -> None:
    """Run trigger DDL on its own connection with a bounded lock wait.

    ``CREATE``/``DROP TRIGGER`` needs ACCESS EXCLUSIVE on ``weather_device_mappings``.
    The service calls ``db.refresh()`` after each commit, which leaves the
    session-scoped ``db_session`` connection idle-in-transaction holding an
    ACCESS SHARE lock on that table. Without a bound, the DDL would wait forever
    behind it; ``lock_timeout`` turns a regression into a fast, clear error rather
    than a hung suite. The ``db_session.rollback()`` in :func:`weather_guard`
    releases that lock before we get here, so this normally never waits.
    """
    with engine.begin() as conn:
        conn.execute(text("SET LOCAL lock_timeout = '15s'"))
        for stmt in statements:
            conn.execute(text(stmt))


@pytest.fixture()
def weather_guard(db_session):
    """Install the WS.1 append-only trigger on the test DB, then remove it.

    Rolls back ``db_session`` immediately before each DDL so any ACCESS SHARE lock
    it is holding on ``weather_device_mappings`` (e.g. from a prior test's
    ``db.refresh``) is released and the ACCESS EXCLUSIVE ``CREATE``/``DROP TRIGGER``
    does not block. The rollback is safe: every CRUD delete in the fixture chain
    commits, so there is never uncommitted data to lose at these boundaries.
    """
    db_session.rollback()
    _run_guard_ddl(APPLY_GUARD_SQL)
    yield
    db_session.rollback()
    _run_guard_ddl(REMOVE_GUARD_SQL)


@pytest.fixture(autouse=True)
def _cleanup_weather_rows(db_session, site, device):
    """Remove governed weather rows BEFORE the ``device`` fixture tears down.

    ``device_id`` is a guard-protected column, so the ``device`` fixture's delete
    fires ``ON DELETE SET NULL`` on a governed mapping and trips the WS.1
    append-only trigger — aborting the teardown transaction (which then cascades to
    every later test on the shared session). DELETE itself is NOT constrained by the
    BEFORE UPDATE trigger, and a single bulk delete drops a superseded row and its
    back-link together so the self-FK SET NULL never fires either. Depending on
    ``device`` guarantees this tears down BEFORE it. The declaration actor is the
    session-scoped system user (never torn down mid-session), so there is no
    ``declared_by``/``activated_by`` user-delete cascade to beat. A leading rollback
    also clears any aborted state left by expected-error tests.
    """
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
    """Build a declare request for an eligible POA + calibrated source_document.

    Defaults describe a declaration that is both activatable (evidence complete)
    AND ``expected_model_eligible`` (POA plane, calibrated with a cert, sensor
    role set). Individual tests override fields to probe each rule.
    """
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


def _status(mapping) -> str:
    return getattr(
        mapping.declaration_status, "value", mapping.declaration_status
    )


# ---------------------------------------------------------------------------
# create_declaration
# ---------------------------------------------------------------------------
class TestCreateDeclaration:
    def test_create_always_drafts_and_writes_ledger(
        self, weather_guard, db_session, site, device, document, system_user_id
    ):
        mapping = create_declaration(
            db_session,
            site=site,
            device=device,
            payload=_payload(device, source_document_id=document.id),
            actor_id=system_user_id,
        )
        assert _status(mapping) == WeatherDeclarationStatus.draft.value
        assert mapping.declared_by == system_user_id
        assert mapping.declared_at is not None
        assert mapping.needs_re_review is False
        assert mapping.activated_at is None
        # The basis + declared semantics are persisted verbatim (never inferred).
        assert (
            getattr(mapping.declaration_basis, "value", mapping.declaration_basis)
            == WeatherDeclarationBasis.source_document.value
        )
        assert _ledger_actions(db_session, mapping.id) == [
            WeatherApprovalAction.declare_draft.value
        ]

    def test_defaults_stay_unknown_when_not_declared(
        self, weather_guard, db_session, site, device, document, system_user_id
    ):
        """The service never fills a non-``unknown`` semantic value on its own."""
        mapping = create_declaration(
            db_session,
            site=site,
            device=device,
            payload=_payload(
                device,
                source_document_id=document.id,
                irradiance_plane=WeatherIrradiancePlane.unknown,
                temperature_type=WeatherTemperatureType.unknown,
                calibration_status=WeatherCalibrationStatus.unknown,
                calibrated_at=None,
                calibration_reference=None,
            ),
            actor_id=system_user_id,
        )
        assert (
            getattr(mapping.irradiance_plane, "value", mapping.irradiance_plane)
            == WeatherIrradiancePlane.unknown.value
        )
        assert (
            getattr(mapping.temperature_type, "value", mapping.temperature_type)
            == WeatherTemperatureType.unknown.value
        )

    def test_reviewer_assumption_requires_confirmation(
        self, weather_guard, db_session, site, device, system_user_id
    ):
        with pytest.raises(DeclarationServiceError) as exc:
            create_declaration(
                db_session,
                site=site,
                device=device,
                payload=_payload(
                    device,
                    declaration_basis=WeatherDeclarationBasis.reviewer_assumption,
                    reviewer_note="I think it's POA.",
                    assumption_confirmed=False,
                ),
                actor_id=system_user_id,
            )
        assert exc.value.status_code == 422
        db_session.rollback()

    def test_reviewer_assumption_requires_note(
        self, weather_guard, db_session, site, device, system_user_id
    ):
        with pytest.raises(DeclarationServiceError) as exc:
            create_declaration(
                db_session,
                site=site,
                device=device,
                payload=_payload(
                    device,
                    declaration_basis=WeatherDeclarationBasis.reviewer_assumption,
                    reviewer_note="   ",
                    assumption_confirmed=True,
                ),
                actor_id=system_user_id,
            )
        assert exc.value.status_code == 422
        db_session.rollback()

    def test_reviewer_assumption_with_confirm_and_note_drafts(
        self, weather_guard, db_session, site, device, system_user_id
    ):
        mapping = create_declaration(
            db_session,
            site=site,
            device=device,
            payload=_payload(
                device,
                declaration_basis=WeatherDeclarationBasis.reviewer_assumption,
                reviewer_note="Operator confirms POA per site walk.",
                assumption_confirmed=True,
            ),
            actor_id=system_user_id,
        )
        assert _status(mapping) == WeatherDeclarationStatus.draft.value

    def test_cross_tenant_evidence_fails_closed_on_create(
        self, weather_guard, db_session, site, device, system_user_id
    ):
        with pytest.raises(DeclarationServiceError) as exc:
            create_declaration(
                db_session,
                site=site,
                device=device,
                payload=_payload(device, source_document_id=999_999_99),
                actor_id=system_user_id,
            )
        assert exc.value.status_code == 422
        db_session.rollback()


class TestEvidenceInTenant:
    def test_document_in_own_site_passes_other_site_fails(
        self, weather_guard, db_session, site, document
    ):
        # The document belongs to ``site``; validating it for that site is fine.
        _validate_evidence_in_tenant(
            db_session,
            site_id=site.id,
            source_document_id=document.id,
            source_file_id=None,
        )
        # Validating the SAME document against a different site fails closed —
        # a site-A admin can never borrow a site-B document as evidence.
        with pytest.raises(DeclarationServiceError) as exc:
            _validate_evidence_in_tenant(
                db_session,
                site_id=site.id + 999_999,
                source_document_id=document.id,
                source_file_id=None,
            )
        assert exc.value.status_code == 422

    def test_file_evidence_in_tenant_passes(
        self, weather_guard, db_session, site, file
    ):
        # ``file`` -> document -> site resolves within the tenant.
        _validate_evidence_in_tenant(
            db_session,
            site_id=site.id,
            source_document_id=None,
            source_file_id=file.id,
        )


# ---------------------------------------------------------------------------
# activate_declaration
# ---------------------------------------------------------------------------
class TestActivateDeclaration:
    def _draft(self, db_session, site, device, document, actor, **overrides):
        return create_declaration(
            db_session,
            site=site,
            device=device,
            payload=_payload(device, source_document_id=document.id, **overrides),
            actor_id=actor,
        )

    def test_activate_draft_to_active_with_snapshot(
        self, weather_guard, db_session, site, device, document, system_user_id
    ):
        draft = self._draft(
            db_session, site, device, document, system_user_id
        )
        active = activate_declaration(
            db_session,
            site=site,
            mapping_id=draft.id,
            actor_id=system_user_id,
            rationale="Reviewed and confirmed.",
        )
        assert _status(active) == WeatherDeclarationStatus.active.value
        assert active.activated_by == system_user_id
        assert active.activated_at is not None
        # An audit snapshot is captured; for POA + calibrated + source_document
        # + sensor role the derived verdict is eligible.
        assert isinstance(active.eligibility_snapshot_json, dict)
        assert active.eligibility_snapshot_json.get("expected_model_eligible") is True
        assert _ledger_actions(db_session, active.id) == [
            WeatherApprovalAction.declare_draft.value,
            WeatherApprovalAction.activate.value,
        ]

    def test_recorded_only_basis_can_activate_but_not_eligible(
        self, weather_guard, db_session, site, device, system_user_id
    ):
        """Activation validates evidence, NOT eligibility (separation of concerns)."""
        draft = create_declaration(
            db_session,
            site=site,
            device=device,
            payload=_payload(
                device,
                declaration_basis=WeatherDeclarationBasis.reviewer_assumption,
                reviewer_note="Operator assumption pending document.",
                assumption_confirmed=True,
            ),
            actor_id=system_user_id,
        )
        active = activate_declaration(
            db_session, site=site, mapping_id=draft.id, actor_id=system_user_id
        )
        assert _status(active) == WeatherDeclarationStatus.active.value
        # reviewer_assumption basis can never be expected_model_eligible.
        assert (
            active.eligibility_snapshot_json.get("expected_model_eligible") is False
        )

    def test_activate_non_draft_rejected(
        self, weather_guard, db_session, site, device, document, system_user_id
    ):
        draft = self._draft(
            db_session, site, device, document, system_user_id
        )
        activate_declaration(
            db_session, site=site, mapping_id=draft.id, actor_id=system_user_id
        )
        with pytest.raises(DeclarationServiceError) as exc:
            activate_declaration(
                db_session,
                site=site,
                mapping_id=draft.id,
                actor_id=system_user_id,
            )
        assert exc.value.status_code == 409
        db_session.rollback()

    def test_activate_incomplete_basis_rejected(
        self, weather_guard, db_session, site, device, system_user_id
    ):
        """source_document basis with no attached evidence cannot activate (422)."""
        draft = create_declaration(
            db_session,
            site=site,
            device=device,
            payload=_payload(device),  # source_document basis, no doc/file attached
            actor_id=system_user_id,
        )
        assert _status(draft) == WeatherDeclarationStatus.draft.value
        with pytest.raises(DeclarationServiceError) as exc:
            activate_declaration(
                db_session,
                site=site,
                mapping_id=draft.id,
                actor_id=system_user_id,
            )
        assert exc.value.status_code == 422
        db_session.rollback()

    def test_single_active_conflict_without_supersede(
        self, weather_guard, db_session, site, device, document, system_user_id
    ):
        first = self._draft(
            db_session, site, device, document, system_user_id
        )
        activate_declaration(
            db_session, site=site, mapping_id=first.id, actor_id=system_user_id
        )
        second = self._draft(
            db_session, site, device, document, system_user_id
        )
        with pytest.raises(DeclarationServiceError) as exc:
            activate_declaration(
                db_session,
                site=site,
                mapping_id=second.id,
                actor_id=system_user_id,
            )
        assert exc.value.status_code == 409
        db_session.rollback()

    def test_activate_with_supersede_preserves_prior_values(
        self, weather_guard, db_session, site, device, document, system_user_id
    ):
        first = self._draft(
            db_session, site, device, document, system_user_id
        )
        activate_declaration(
            db_session, site=site, mapping_id=first.id, actor_id=system_user_id
        )
        # Snapshot the prior's semantic value columns before supersession.
        prior_values = (
            _status_value(first.irradiance_plane),
            _status_value(first.temperature_type),
            _status_value(first.calibration_status),
            _status_value(first.declaration_basis),
        )

        second = self._draft(
            db_session,
            site,
            device,
            document,
            system_user_id,
            supersedes_mapping_id=first.id,
        )
        active = activate_declaration(
            db_session,
            site=site,
            mapping_id=second.id,
            actor_id=system_user_id,
            rationale="Recalibrated sensor.",
        )
        db_session.refresh(first)

        assert _status(active) == WeatherDeclarationStatus.active.value
        assert _status(first) == WeatherDeclarationStatus.superseded.value
        assert first.superseded_by_mapping_id == second.id
        # Supersession is a NEW row + back-link; the prior's value columns are
        # byte-identical (never edited in place).
        assert (
            _status_value(first.irradiance_plane),
            _status_value(first.temperature_type),
            _status_value(first.calibration_status),
            _status_value(first.declaration_basis),
        ) == prior_values
        # Ledger: prior carries declare_draft+activate+supersede; new carries
        # declare_draft+activate.
        assert _ledger_actions(db_session, first.id) == [
            WeatherApprovalAction.declare_draft.value,
            WeatherApprovalAction.activate.value,
            WeatherApprovalAction.supersede.value,
        ]
        assert _ledger_actions(db_session, second.id) == [
            WeatherApprovalAction.declare_draft.value,
            WeatherApprovalAction.activate.value,
        ]

    def test_supersede_target_must_be_active(
        self, weather_guard, db_session, site, device, document, system_user_id
    ):
        """A supersedes_mapping_id that isn't the current active row is 409."""
        first = self._draft(
            db_session, site, device, document, system_user_id
        )  # left as draft (never activated)
        second = self._draft(
            db_session,
            site,
            device,
            document,
            system_user_id,
            supersedes_mapping_id=first.id,
        )
        with pytest.raises(DeclarationServiceError) as exc:
            activate_declaration(
                db_session,
                site=site,
                mapping_id=second.id,
                actor_id=system_user_id,
            )
        assert exc.value.status_code == 409
        db_session.rollback()

    def test_activation_revalidates_evidence_in_tenant(
        self,
        weather_guard,
        db_session,
        site,
        device,
        document,
        system_user_id,
        monkeypatch,
    ):
        """Activation re-runs the cross-tenant evidence check, not only create.

        A draft can be recorded while its document is in-tenant and later activated
        after that document has been re-parented or removed; activation must fail
        closed exactly as create did. We prove activation calls
        ``_validate_evidence_in_tenant`` with the mapping's OWN evidence + site by
        swapping in a spy that fails closed. A real re-parent cannot be staged here
        because ``source_document_id`` is guard-immutable and ``documents.site_id``
        is an FK, so the spy is the deterministic probe.
        """
        draft = self._draft(db_session, site, device, document, system_user_id)

        captured: dict = {}

        def _spy(db, *, site_id, source_document_id, source_file_id):  # noqa: U100
            captured.update(
                site_id=site_id,
                source_document_id=source_document_id,
                source_file_id=source_file_id,
            )
            raise DeclarationServiceError(
                422, "evidence no longer resolves within this project/site."
            )

        monkeypatch.setattr(decl_svc, "_validate_evidence_in_tenant", _spy)

        with pytest.raises(DeclarationServiceError) as exc:
            activate_declaration(
                db_session,
                site=site,
                mapping_id=draft.id,
                actor_id=system_user_id,
            )
        assert exc.value.status_code == 422
        # It re-validated THIS mapping's evidence against THIS site.
        assert captured == {
            "site_id": site.id,
            "source_document_id": document.id,
            "source_file_id": None,
        }
        db_session.rollback()


# ---------------------------------------------------------------------------
# single-active DB invariant (partial unique index backstop)
# ---------------------------------------------------------------------------
class TestSingleActiveDbInvariant:
    """The WS.2 partial unique indexes are the durable single-active guarantee the
    activation service relies on under concurrency (two activations of an empty
    lineage cannot both win). They constrain ONLY ``active`` rows per lineage.
    """

    def _row(self, site, device, status, system_user_id) -> WeatherDeviceMapping:
        return WeatherDeviceMapping(
            site_id=site.id,
            device_id=device.id,
            metric=METRIC,
            declaration_status=status,
            declaration_basis=WeatherDeclarationBasis.source_document,
            irradiance_plane=WeatherIrradiancePlane.poa,
            temperature_type=WeatherTemperatureType.unknown,
            calibration_status=WeatherCalibrationStatus.calibrated,
            declared_by=system_user_id,
            needs_re_review=False,
        )

    def test_partial_unique_index_blocks_second_active_same_lineage(
        self, weather_guard, db_session, site, device, system_user_id
    ):
        """Two ACTIVE rows in one lineage violate the partial unique index. INSERT
        is not constrained by the WS.1 append-only trigger, so it is the index (not
        the trigger) that rejects the second active row.
        """
        db_session.add(
            self._row(site, device, WeatherDeclarationStatus.active, system_user_id)
        )
        db_session.flush()
        db_session.add(
            self._row(site, device, WeatherDeclarationStatus.active, system_user_id)
        )
        with pytest.raises(IntegrityError):
            db_session.flush()
        db_session.rollback()

    def test_multiple_drafts_same_lineage_allowed(
        self, weather_guard, db_session, site, device, system_user_id
    ):
        """The index constrains only ACTIVE rows: multiple drafts in one lineage
        coexist freely (a fresh draft alongside the live active row is the normal
        pre-supersession state).
        """
        db_session.add(
            self._row(site, device, WeatherDeclarationStatus.draft, system_user_id)
        )
        db_session.add(
            self._row(site, device, WeatherDeclarationStatus.draft, system_user_id)
        )
        db_session.flush()  # no IntegrityError — drafts are unconstrained
        db_session.rollback()


# ---------------------------------------------------------------------------
# create + activate atomic
# ---------------------------------------------------------------------------
class TestCreateAndActivateAtomic:
    def test_activate_flag_creates_active_in_one_call(
        self, weather_guard, db_session, site, device, document, system_user_id
    ):
        mapping = create_declaration(
            db_session,
            site=site,
            device=device,
            payload=_payload(device, source_document_id=document.id, activate=True),
            actor_id=system_user_id,
        )
        assert _status(mapping) == WeatherDeclarationStatus.active.value
        assert _ledger_actions(db_session, mapping.id) == [
            WeatherApprovalAction.declare_draft.value,
            WeatherApprovalAction.activate.value,
        ]

    def test_atomic_conflict_rolls_back_the_draft(
        self, weather_guard, db_session, site, device, document, system_user_id
    ):
        existing = create_declaration(
            db_session,
            site=site,
            device=device,
            payload=_payload(device, source_document_id=document.id, activate=True),
            actor_id=system_user_id,
        )
        before = (
            db_session.query(WeatherDeviceMapping)
            .filter(WeatherDeviceMapping.device_id == device.id)
            .count()
        )
        with pytest.raises(DeclarationServiceError) as exc:
            create_declaration(
                db_session,
                site=site,
                device=device,
                payload=_payload(
                    device, source_document_id=document.id, activate=True
                ),
                actor_id=system_user_id,
            )
        assert exc.value.status_code == 409
        db_session.rollback()
        after = (
            db_session.query(WeatherDeviceMapping)
            .filter(WeatherDeviceMapping.device_id == device.id)
            .count()
        )
        # The conflicting create+activate left nothing behind (atomic rollback).
        assert after == before
        assert _status(existing) == WeatherDeclarationStatus.active.value


# ---------------------------------------------------------------------------
# mark_needs_re_review
# ---------------------------------------------------------------------------
class TestMarkNeedsReReview:
    def _active(self, db_session, site, device, document, actor):
        return create_declaration(
            db_session,
            site=site,
            device=device,
            payload=_payload(device, source_document_id=document.id, activate=True),
            actor_id=actor,
        )

    def test_flag_active_declaration(
        self, weather_guard, db_session, site, device, document, system_user_id
    ):
        active = self._active(
            db_session, site, device, document, system_user_id
        )
        flagged = mark_needs_re_review(
            db_session,
            site=site,
            mapping_id=active.id,
            actor_id=system_user_id,
            reason="Upstream device classification changed.",
        )
        assert flagged.needs_re_review is True
        assert flagged.re_review_reason == "Upstream device classification changed."
        assert _ledger_actions(db_session, flagged.id)[-1] == (
            WeatherApprovalAction.needs_re_review.value
        )

    def test_reason_required(
        self, weather_guard, db_session, site, device, document, system_user_id
    ):
        active = self._active(
            db_session, site, device, document, system_user_id
        )
        with pytest.raises(DeclarationServiceError) as exc:
            mark_needs_re_review(
                db_session,
                site=site,
                mapping_id=active.id,
                actor_id=system_user_id,
                reason="   ",
            )
        assert exc.value.status_code == 422
        db_session.rollback()

    def test_non_active_rejected(
        self, weather_guard, db_session, site, device, document, system_user_id
    ):
        draft = create_declaration(
            db_session,
            site=site,
            device=device,
            payload=_payload(device, source_document_id=document.id),
            actor_id=system_user_id,
        )
        with pytest.raises(DeclarationServiceError) as exc:
            mark_needs_re_review(
                db_session,
                site=site,
                mapping_id=draft.id,
                actor_id=system_user_id,
                reason="stale",
            )
        assert exc.value.status_code == 409
        db_session.rollback()

    def test_already_flagged_rejected(
        self, weather_guard, db_session, site, device, document, system_user_id
    ):
        active = self._active(
            db_session, site, device, document, system_user_id
        )
        mark_needs_re_review(
            db_session,
            site=site,
            mapping_id=active.id,
            actor_id=system_user_id,
            reason="first flag",
        )
        with pytest.raises(DeclarationServiceError) as exc:
            mark_needs_re_review(
                db_session,
                site=site,
                mapping_id=active.id,
                actor_id=system_user_id,
                reason="second flag",
            )
        assert exc.value.status_code == 409
        db_session.rollback()


# ---------------------------------------------------------------------------
# get_current_for_device precedence
# ---------------------------------------------------------------------------
class TestGetCurrentForDevice:
    def test_prefers_active_over_draft(
        self, weather_guard, db_session, site, device, document, system_user_id
    ):
        from app.crud.weather import WeatherDeviceMappingCRUD

        # A bare draft first, then an activated declaration on the same device.
        create_declaration(
            db_session,
            site=site,
            device=device,
            payload=_payload(
                device,
                metric="ambient_temp_c",
                declaration_basis=WeatherDeclarationBasis.reviewer_assumption,
                reviewer_note="draft only",
                assumption_confirmed=True,
            ),
            actor_id=system_user_id,
        )
        active = create_declaration(
            db_session,
            site=site,
            device=device,
            payload=_payload(device, source_document_id=document.id, activate=True),
            actor_id=system_user_id,
        )
        current = WeatherDeviceMappingCRUD(db_session).get_current_for_device(
            device.id, metric=METRIC
        )
        assert current is not None
        assert current.id == active.id
        assert _status(current) == WeatherDeclarationStatus.active.value


def _status_value(value):
    return getattr(value, "value", value)
