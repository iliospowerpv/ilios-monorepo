"""Promotion Freshness Guard — fail-closed coverage.

A candidate fact may only be promoted to an active assumption when its accepted
*source basis* can be proven current against the file version's CURRENT parse
run (the latest run by ``extraction_run_number`` — the same anchor
``bulk_accept_ai_values`` uses). When freshness cannot be proven, promotion must
FAIL CLOSED: nothing is promoted, no fact is retired, no ``AssumptionPromotion``
audit record is written, and the version's ``is_actual`` flag is untouched. One
stale candidate blocks the whole (file-version-scoped, all-or-nothing) promotion.

These tests are DB-backed (mirroring ``bulk_accept_guardrail_test``): the
session-scoped ``db_session`` plus function-scoped ``document``/``file`` fixtures
give each test a fresh site/document/file, while canonical fields (UNIQUE name)
are get-or-created. The matrix is exercised through the real
``PromotionService.validate_promotion_freshness`` (real CRUD + ``_find_field_in_run``);
the HTTP contract (409 + structured body, no writes / 200 happy path) is
exercised through the ``POST .../assumptions/promote`` route.
"""

from app.crud.assumption_promotion import AssumptionPromotionCRUD
from app.crud.project_fact import ProjectFactCRUD
from app.models.file import AIParsingResult, FileParsingStatuses
from app.models.project_facts import AssumptionPromotion, CanonicalField, FactStatus, ProjectFact
from app.services.promotion_service import (
    PROMOTION_SOURCE_STALE_CODE,
    PromotionError,
    PromotionService,
)

# Baseline-driving canonical names (feed expected/baseline math).
MODULE_WATTAGE = "module_wattage"
INVERTER_WATTAGE = "inverter_wattage"
# A non-baseline canonical name (never feeds baseline math).
QUIET_ENJOYMENT = "quiet_enjoyment"


def _promote_endpoint(site_id_):
    return f"/api/projects/{site_id_}/assumptions/promote"


def _make_canonical_field(db_session, name, display):
    """Session-scoped DB + UNIQUE canonical name -> get-or-create."""
    field = db_session.query(CanonicalField).filter_by(name=name).first()
    if field is not None:
        return field
    field = CanonicalField(name=name, display_name=display, field_type="text", is_active=True)
    db_session.add(field)
    db_session.commit()
    db_session.refresh(field)
    return field


def _make_run(db_session, file_id, parsed_result, run_number=1, status=FileParsingStatuses.completed):
    run = AIParsingResult(
        file_id=file_id,
        status=status,
        parsed_result=parsed_result,
        extraction_run_number=run_number,
    )
    db_session.add(run)
    db_session.commit()
    db_session.refresh(run)
    return run


def _make_candidate_fact(db_session, site_id, canonical_field_id, file_id, value, source_run_id=None):
    fact = ProjectFact(
        site_id=site_id,
        canonical_field_id=canonical_field_id,
        value={"v": value} if value is not None else None,
        status=FactStatus.candidate.value,
        source_file_id=file_id,
        source_run_id=source_run_id,
    )
    db_session.add(fact)
    db_session.commit()
    db_session.refresh(fact)
    return fact


class TestValidatePromotionFreshnessMatrix:
    """Per-candidate fail-closed decision matrix (service-level)."""

    def _service(self, db_session):
        return PromotionService(db_session)

    def _validate(self, db_session, site_id, file):
        return self._service(db_session).validate_promotion_freshness(site_id, file.id, promoted_by_id=1)

    # ------------------------------------------------------------------ fresh / allowed

    def test_lineage_match_is_fresh(self, document, file, db_session):
        """source_run_id == current run id -> FRESH (no raise, no warnings)."""
        field = _make_canonical_field(db_session, MODULE_WATTAGE, "Module Wattage")
        run = _make_run(db_session, file.id, {MODULE_WATTAGE: {"value": "400"}})
        _make_candidate_fact(db_session, document.site_id, field.id, file.id, "400", source_run_id=run.id)

        assert self._validate(db_session, document.site_id, file) == []

    def test_lineage_match_is_fresh_even_for_override_value(self, document, file, db_session):
        """An override (candidate value differs from AI) accepted from the current run is still FRESH:
        lineage identity proves freshness and no value-vs-AI comparison is made."""
        field = _make_canonical_field(db_session, INVERTER_WATTAGE, "Inverter Wattage")
        run = _make_run(db_session, file.id, {INVERTER_WATTAGE: {"value": "100"}})
        # Candidate value 999 != AI 100, but it was accepted from the current run.
        _make_candidate_fact(db_session, document.site_id, field.id, file.id, "999", source_run_id=run.id)

        assert self._validate(db_session, document.site_id, file) == []

    def test_no_candidate_facts_is_a_noop(self, document, file, db_session):
        """No candidate facts -> nothing to prove (no run required, no raise)."""
        assert self._validate(db_session, document.site_id, file) == []

    def test_no_lineage_non_baseline_value_match_allowed_with_warning(self, document, file, db_session):
        """NULL lineage, non-baseline field, value matches current extracted -> ALLOWED (warning)."""
        field = _make_canonical_field(db_session, QUIET_ENJOYMENT, "Quiet Enjoyment")
        _make_run(db_session, file.id, {QUIET_ENJOYMENT: {"value": "granted"}})
        _make_candidate_fact(db_session, document.site_id, field.id, file.id, "granted", source_run_id=None)

        warnings = self._validate(db_session, document.site_id, file)
        assert len(warnings) == 1
        assert warnings[0]["reason"] == "no_lineage_value_match"
        assert warnings[0]["canonical_field"] == QUIET_ENJOYMENT

    # ------------------------------------------------------------------ stale / blocked

    def _assert_blocks(self, db_session, site_id, file, expected_reason):
        try:
            self._validate(db_session, site_id, file)
        except PromotionError as exc:
            assert exc.error_code == PROMOTION_SOURCE_STALE_CODE
            reasons = [s["reason"] for s in exc.details["stale_fields"]]
            assert expected_reason in reasons, f"expected {expected_reason}, got {reasons}"
            return exc
        raise AssertionError(f"expected PromotionError ({expected_reason}) but none was raised")

    def test_source_run_outdated_blocks(self, document, file, db_session):
        """Candidate points to a parse run that is not the current run -> STALE."""
        field = _make_canonical_field(db_session, MODULE_WATTAGE, "Module Wattage")
        old_run = _make_run(db_session, file.id, {MODULE_WATTAGE: {"value": "400"}}, run_number=1)
        _make_run(db_session, file.id, {MODULE_WATTAGE: {"value": "410"}}, run_number=2)  # newer = current
        _make_candidate_fact(db_session, document.site_id, field.id, file.id, "400", source_run_id=old_run.id)

        self._assert_blocks(db_session, document.site_id, file, "source_run_outdated")

    def test_no_lineage_baseline_field_blocks_even_when_value_matches(self, document, file, db_session):
        """NULL lineage on a baseline-driving field -> STALE even when the value matches the parse."""
        field = _make_canonical_field(db_session, MODULE_WATTAGE, "Module Wattage")
        _make_run(db_session, file.id, {MODULE_WATTAGE: {"value": "400"}})
        _make_candidate_fact(db_session, document.site_id, field.id, file.id, "400", source_run_id=None)

        self._assert_blocks(db_session, document.site_id, file, "no_lineage_baseline_field")

    def test_no_lineage_non_baseline_value_diverged_blocks(self, document, file, db_session):
        """NULL lineage, non-baseline field, value differs from current extracted -> STALE."""
        field = _make_canonical_field(db_session, QUIET_ENJOYMENT, "Quiet Enjoyment")
        _make_run(db_session, file.id, {QUIET_ENJOYMENT: {"value": "granted"}})
        _make_candidate_fact(db_session, document.site_id, field.id, file.id, "revoked", source_run_id=None)

        self._assert_blocks(db_session, document.site_id, file, "value_diverged_no_lineage")

    def test_field_removed_blocks(self, document, file, db_session):
        """NULL lineage, field absent from the current parse -> STALE (field_removed)."""
        field = _make_canonical_field(db_session, QUIET_ENJOYMENT, "Quiet Enjoyment")
        _make_run(db_session, file.id, {"some_other_field": {"value": "x"}})
        _make_candidate_fact(db_session, document.site_id, field.id, file.id, "granted", source_run_id=None)

        self._assert_blocks(db_session, document.site_id, file, "field_removed")

    def test_no_current_parse_blocks(self, document, file, db_session):
        """Candidate exists but the version has no parse run at all -> STALE (no_current_parse)."""
        field = _make_canonical_field(db_session, MODULE_WATTAGE, "Module Wattage")
        _make_candidate_fact(db_session, document.site_id, field.id, file.id, "400", source_run_id=None)

        self._assert_blocks(db_session, document.site_id, file, "no_current_parse")

    def test_latest_parse_not_completed_blocks(self, document, file, db_session):
        """Latest run is not completed (reparse in flight) -> STALE (latest_parse_not_completed)."""
        field = _make_canonical_field(db_session, MODULE_WATTAGE, "Module Wattage")
        run = _make_run(db_session, file.id, {MODULE_WATTAGE: {"value": "400"}})
        # A newer, still-processing run becomes the latest -> blocks promotion.
        _make_run(db_session, file.id, None, run_number=2, status=FileParsingStatuses.processing)
        _make_candidate_fact(db_session, document.site_id, field.id, file.id, "400", source_run_id=run.id)

        self._assert_blocks(db_session, document.site_id, file, "latest_parse_not_completed")

    def test_latest_parse_unusable_blocks(self, document, file, db_session):
        """Latest run completed but has no parseable result -> STALE (latest_parse_unusable)."""
        field = _make_canonical_field(db_session, MODULE_WATTAGE, "Module Wattage")
        run = _make_run(db_session, file.id, {})  # completed, empty parsed_result
        _make_candidate_fact(db_session, document.site_id, field.id, file.id, "400", source_run_id=run.id)

        self._assert_blocks(db_session, document.site_id, file, "latest_parse_unusable")

    def test_lineage_match_but_field_unreadable_blocks(self, document, file, db_session):
        """Corruption guard: lineage matches but the field is no longer readable in the run -> STALE."""
        field = _make_canonical_field(db_session, MODULE_WATTAGE, "Module Wattage")
        run = _make_run(db_session, file.id, {"some_other_field": {"value": "x"}})
        _make_candidate_fact(db_session, document.site_id, field.id, file.id, "400", source_run_id=run.id)

        self._assert_blocks(db_session, document.site_id, file, "source_basis_unreadable")

    def test_one_stale_candidate_blocks_all(self, document, file, db_session):
        """A fresh candidate alongside a stale one -> the WHOLE promotion is blocked."""
        fresh_field = _make_canonical_field(db_session, INVERTER_WATTAGE, "Inverter Wattage")
        stale_field = _make_canonical_field(db_session, MODULE_WATTAGE, "Module Wattage")
        run = _make_run(
            db_session,
            file.id,
            {INVERTER_WATTAGE: {"value": "100"}, MODULE_WATTAGE: {"value": "400"}},
        )
        # Fresh: lineage to current run. Stale: baseline field with NULL lineage.
        _make_candidate_fact(db_session, document.site_id, fresh_field.id, file.id, "100", source_run_id=run.id)
        _make_candidate_fact(db_session, document.site_id, stale_field.id, file.id, "400", source_run_id=None)

        exc = self._assert_blocks(db_session, document.site_id, file, "no_lineage_baseline_field")
        # Only the genuinely stale field is reported; the fresh one is not flagged.
        stale = exc.details["stale_fields"]
        assert len(stale) == 1
        assert stale[0]["canonical_field"] == MODULE_WATTAGE

    def test_structured_error_carries_per_field_details(self, document, file, db_session):
        """The structured error exposes canonical_field, reason, required_action and fact_id."""
        field = _make_canonical_field(db_session, MODULE_WATTAGE, "Module Wattage")
        _make_run(db_session, file.id, {MODULE_WATTAGE: {"value": "400"}})
        fact = _make_candidate_fact(db_session, document.site_id, field.id, file.id, "400", source_run_id=None)

        exc = self._assert_blocks(db_session, document.site_id, file, "no_lineage_baseline_field")
        item = exc.details["stale_fields"][0]
        assert item["canonical_field"] == MODULE_WATTAGE
        assert item["field_display_name"] == "Module Wattage"
        assert item["fact_id"] == fact.id
        assert item["required_action"]


class TestPromoteVersionFailClosed:
    """End-to-end HTTP contract for the freshness guard on POST .../assumptions/promote."""

    def test_stale_promotion_returns_409_and_writes_nothing(
        self, client, site_id, document, file, db_session, company_member_user_auth_header
    ):
        """A stale candidate -> 409 structured body; no fact promoted/retired, no audit, is_actual untouched."""
        field = _make_canonical_field(db_session, MODULE_WATTAGE, "Module Wattage")
        old_run = _make_run(db_session, file.id, {MODULE_WATTAGE: {"value": "400"}}, run_number=1)
        _make_run(db_session, file.id, {MODULE_WATTAGE: {"value": "410"}}, run_number=2)
        fact = _make_candidate_fact(db_session, document.site_id, field.id, file.id, "400", source_run_id=old_run.id)

        response = client.post(
            _promote_endpoint(site_id),
            headers=company_member_user_auth_header,
            json={"document_id": document.id, "file_id": file.id},
        )

        assert response.status_code == 409
        # The structured body is returned verbatim (a JSONResponse, NOT a
        # str()-collapsed HTTPException detail), so the client can read it.
        body = response.json()
        assert body["error_code"] == PROMOTION_SOURCE_STALE_CODE
        assert body["message"]
        reasons = [s["reason"] for s in body["stale_fields"]]
        assert "source_run_outdated" in reasons

        # Fail-closed: no writes whatsoever.
        db_session.refresh(fact)
        assert fact.status == FactStatus.candidate.value
        assert fact.promoted_at is None
        db_session.refresh(file)
        assert file.is_actual is False
        assert AssumptionPromotionCRUD(db_session).get_promotions_for_file(file.id) == []

    def test_fresh_promotion_succeeds(
        self, client, site_id, document, file, db_session, company_member_user_auth_header
    ):
        """A fresh (lineage-backed) candidate promotes normally: 200, fact activated, version actual, audit written."""
        field = _make_canonical_field(db_session, MODULE_WATTAGE, "Module Wattage")
        run = _make_run(db_session, file.id, {MODULE_WATTAGE: {"value": "400"}})
        fact = _make_candidate_fact(db_session, document.site_id, field.id, file.id, "400", source_run_id=run.id)

        response = client.post(
            _promote_endpoint(site_id),
            headers=company_member_user_auth_header,
            json={"document_id": document.id, "file_id": file.id},
        )

        try:
            assert response.status_code == 200
            body = response.json()
            assert body["promoted"] is True
            assert body["facts_promoted"] == 1

            db_session.refresh(fact)
            assert fact.status == FactStatus.active.value
            assert fact.promoted_at is not None
            db_session.refresh(file)
            assert file.is_actual is True
            assert len(AssumptionPromotionCRUD(db_session).get_promotions_for_file(file.id)) == 1
        finally:
            # ``assumptions_promotions.promoted_by_id`` is NOT NULL but its user FK
            # is ``ON DELETE SET NULL``; leaving a promotion row behind makes the
            # auth-user fixture teardown fail with a NotNullViolation. Remove the
            # rows this test created so the shared session tears down cleanly.
            db_session.query(AssumptionPromotion).filter_by(file_id=file.id).delete()
            db_session.commit()
