"""DD V2 Phase 1.6 — bulk-accept baseline override guardrail.

Mirrors the single-key set_key guardrail (see documents_test.TestSetKeyOverrideGuardrail) for the
``POST .../files/{file_id}/bulk-accept/`` endpoint: no baseline-driving assumption may be accepted
in bulk away from its AI-extracted original without an authenticated reviewer AND an override
rationale, and a baseline-driving audit failure rejects the ENTIRE batch (no silent partial accept).

Uses ``monkeypatch`` (pytest-mock is unavailable) and reuses the shared-session, function-scoped
``document``/``file`` fixtures, so each test gets a fresh site/document/file while canonical fields
(UNIQUE name) are get-or-created.
"""

from datetime import datetime, timezone

from app.crud.document_key import DocumentKeyCRUD
from app.crud.project_fact import ProjectFactCRUD
from app.models.file import AIParsingResult, FileParsingStatuses
from app.models.project_facts import CanonicalField, FactStatus, ProjectFact


class TestBulkAcceptOverrideGuardrail:
    BASELINE_KEY = "Module Wattage"
    CANONICAL_NAME = "module_wattage"
    NON_BASELINE_KEY = "Quiet Enjoyment"

    @staticmethod
    def _bulk_endpoint(site_id_, document_id_, file_id_):
        return f"/api/due-diligence/{site_id_}/documents/{document_id_}/files/{file_id_}/bulk-accept/"

    @staticmethod
    def _patch_allowed_keys(monkeypatch, allowed):
        # Registry is not seeded in the test DB (create_all, no Alembic) and config fallback is
        # off, so the allowed-keys set must be supplied explicitly. Patch the class method on the
        # files_parsing module's reference.
        monkeypatch.setattr(
            "app.routers.due_diligence.files_parsing.AIParsingHandler.get_keys_by_document_type",
            lambda self, document_type: list(allowed),
        )

    @staticmethod
    def _make_canonical_field(db_session, name, display):
        # Session-scoped db with no per-test rollback + canonical_fields.name UNIQUE -> get-or-create.
        field = db_session.query(CanonicalField).filter_by(name=name).first()
        if field is not None:
            return field
        field = CanonicalField(name=name, display_name=display, field_type="text", is_active=True)
        db_session.add(field)
        db_session.commit()
        db_session.refresh(field)
        return field

    @staticmethod
    def _make_run(db_session, file_id, parsed_result, run_number=1):
        run = AIParsingResult(
            file_id=file_id,
            status=FileParsingStatuses.completed,
            parsed_result=parsed_result,
            extraction_run_number=run_number,
        )
        db_session.add(run)
        db_session.commit()
        db_session.refresh(run)
        return run

    @staticmethod
    def _make_candidate_fact(db_session, site_id, canonical_field_id, file_id, value, ai_value):
        fact = ProjectFact(
            site_id=site_id,
            canonical_field_id=canonical_field_id,
            value={"v": value} if value is not None else None,
            ai_extracted_value={"v": ai_value} if ai_value is not None else None,
            status=FactStatus.candidate.value,
            source_file_id=file_id,
        )
        db_session.add(fact)
        db_session.commit()
        db_session.refresh(fact)
        return fact

    def _get_key(self, db_session, document, file):
        return DocumentKeyCRUD(db_session).get_document_key(
            name=self.BASELINE_KEY, document_id=document.id, file_id=file.id
        )

    # ------------------------------------------------------------------ happy paths

    def test_bulk_match_ai_is_accepted_without_notes(
        self, client, site_id, document, file, db_session, company_member_user_auth_header, monkeypatch
    ):
        """Accepting the run's own AI value unchanged -> accepted, no rationale, candidate (not promoted)."""
        self._patch_allowed_keys(monkeypatch, [self.BASELINE_KEY])
        field = self._make_canonical_field(db_session, self.CANONICAL_NAME, self.BASELINE_KEY)
        run = self._make_run(db_session, file.id, {self.CANONICAL_NAME: {"value": "100"}})

        response = client.post(
            self._bulk_endpoint(site_id, document.id, file.id),
            headers=company_member_user_auth_header,
            json={"run_id": run.id, "fields": [{"field_name": self.BASELINE_KEY, "value": "100"}]},
        )

        assert response.status_code == 200
        assert response.json()["accepted_count"] == 1
        saved = self._get_key(db_session, document, file)
        assert saved.status == "accepted"
        assert saved.override_notes is None
        # No baseline bridge: the fact stays a candidate and is never auto-promoted.
        fact = ProjectFactCRUD(db_session).get_candidate_fact(document.site_id, field.id, file.id)
        assert fact is not None
        assert fact.status == FactStatus.candidate.value
        assert fact.promoted_at is None

    def test_bulk_non_baseline_field_is_accepted(
        self, client, site_id, document, file, db_session, company_member_user_auth_header, monkeypatch
    ):
        """Non-baseline fields are unaffected by the guardrail (existing bulk behavior preserved)."""
        self._patch_allowed_keys(monkeypatch, [self.NON_BASELINE_KEY])
        run = self._make_run(db_session, file.id, {"quiet_enjoyment": {"value": "x"}})

        response = client.post(
            self._bulk_endpoint(site_id, document.id, file.id),
            headers=company_member_user_auth_header,
            json={"run_id": run.id, "fields": [{"field_name": self.NON_BASELINE_KEY, "value": "Anything"}]},
        )

        assert response.status_code == 200
        saved = DocumentKeyCRUD(db_session).get_document_key(
            name=self.NON_BASELINE_KEY, document_id=document.id, file_id=file.id
        )
        assert saved.status == "accepted"

    def test_bulk_divergence_with_notes_is_saved_as_override(
        self, client, site_id, document, file, db_session, company_member_user_auth_header, monkeypatch
    ):
        """Changed baseline value + per-item override_notes -> persisted as overridden."""
        self._patch_allowed_keys(monkeypatch, [self.BASELINE_KEY])
        self._make_canonical_field(db_session, self.CANONICAL_NAME, self.BASELINE_KEY)
        run = self._make_run(db_session, file.id, {self.CANONICAL_NAME: {"value": "100"}})

        response = client.post(
            self._bulk_endpoint(site_id, document.id, file.id),
            headers=company_member_user_auth_header,
            json={
                "run_id": run.id,
                "fields": [
                    {
                        "field_name": self.BASELINE_KEY,
                        "value": "999",
                        "override_notes": "Corrected per manufacturer datasheet",
                    }
                ],
            },
        )

        assert response.status_code == 200
        saved = self._get_key(db_session, document, file)
        assert saved.status == "overridden"
        assert saved.override_value == "999"
        assert saved.override_notes == "Corrected per manufacturer datasheet"
        assert saved.overridden_by_id is not None
        assert saved.overridden_at is not None

    # ------------------------------------------------------------------ guardrail / 422

    def test_bulk_divergence_without_notes_rejected_writes_nothing(
        self, client, site_id, document, file, db_session, company_member_user_auth_header, monkeypatch
    ):
        """Changed baseline value + no rationale -> 422, and NOTHING is persisted (no key, no fact)."""
        self._patch_allowed_keys(monkeypatch, [self.BASELINE_KEY])
        field = self._make_canonical_field(db_session, self.CANONICAL_NAME, self.BASELINE_KEY)
        run = self._make_run(db_session, file.id, {self.CANONICAL_NAME: {"value": "100"}})

        response = client.post(
            self._bulk_endpoint(site_id, document.id, file.id),
            headers=company_member_user_auth_header,
            json={"run_id": run.id, "fields": [{"field_name": self.BASELINE_KEY, "value": "999"}]},
        )

        assert response.status_code == 422
        assert self._get_key(db_session, document, file) is None
        assert ProjectFactCRUD(db_session).get_candidate_fact(document.site_id, field.id, file.id) is None

    def test_bulk_422_response_carries_item_details(
        self, client, site_id, document, file, db_session, company_member_user_auth_header, monkeypatch
    ):
        """The 422 body exposes message+detail (FE reads .detail) and structured per-item details."""
        self._patch_allowed_keys(monkeypatch, [self.BASELINE_KEY])
        self._make_canonical_field(db_session, self.CANONICAL_NAME, self.BASELINE_KEY)
        run = self._make_run(db_session, file.id, {self.CANONICAL_NAME: {"value": "100"}})

        response = client.post(
            self._bulk_endpoint(site_id, document.id, file.id),
            headers=company_member_user_auth_header,
            json={"run_id": run.id, "fields": [{"field_name": self.BASELINE_KEY, "value": "999"}]},
        )

        assert response.status_code == 422
        body = response.json()
        assert self.BASELINE_KEY in body["message"]
        assert self.BASELINE_KEY in body["detail"]
        assert body["code"] == 422
        items = body["items"]
        assert len(items) == 1
        assert items[0]["field_key"] == self.BASELINE_KEY
        assert items[0]["reason"]
        assert items[0]["required_action"]

    def test_bulk_mixed_batch_one_audit_failure_writes_nothing(
        self, client, site_id, document, file, db_session, company_member_user_auth_header, monkeypatch
    ):
        """A valid non-baseline field alongside an invalid baseline override -> 422, no partial accept."""
        self._patch_allowed_keys(monkeypatch, [self.BASELINE_KEY, self.NON_BASELINE_KEY])
        self._make_canonical_field(db_session, self.CANONICAL_NAME, self.BASELINE_KEY)
        run = self._make_run(db_session, file.id, {self.CANONICAL_NAME: {"value": "100"}})

        response = client.post(
            self._bulk_endpoint(site_id, document.id, file.id),
            headers=company_member_user_auth_header,
            json={
                "run_id": run.id,
                "fields": [
                    {"field_name": self.NON_BASELINE_KEY, "value": "Valid text"},
                    {"field_name": self.BASELINE_KEY, "value": "999"},
                ],
            },
        )

        assert response.status_code == 422
        # The valid non-baseline field must NOT have been written (all-or-nothing).
        assert (
            DocumentKeyCRUD(db_session).get_document_key(
                name=self.NON_BASELINE_KEY, document_id=document.id, file_id=file.id
            )
            is None
        )
        assert self._get_key(db_session, document, file) is None

    def test_bulk_ai_missing_fail_safe_blocks_silent_change(
        self, client, site_id, document, file, db_session, company_member_user_auth_header, monkeypatch
    ):
        """AI original undeterminable (run lacks the field) + an EXISTING stored value -> change needs rationale."""
        self._patch_allowed_keys(monkeypatch, [self.BASELINE_KEY])
        self._make_canonical_field(db_session, self.CANONICAL_NAME, self.BASELINE_KEY)
        # Run has no value for the baseline field, and there is no candidate fact -> undetermined.
        run = self._make_run(db_session, file.id, {"some_other_field": {"value": "x"}})
        DocumentKeyCRUD(db_session).create_item(
            {
                "document_id": document.id,
                "file_id": file.id,
                "name": self.BASELINE_KEY,
                "value": "100",
                "status": "accepted",
            }
        )

        response = client.post(
            self._bulk_endpoint(site_id, document.id, file.id),
            headers=company_member_user_auth_header,
            json={"run_id": run.id, "fields": [{"field_name": self.BASELINE_KEY, "value": "999"}]},
        )

        assert response.status_code == 422
        saved = self._get_key(db_session, document, file)
        assert saved.value == "100"
        assert saved.status == "accepted"

    # ------------------------------------------------------------------ run-preference & provenance

    def test_bulk_prefers_accepted_run_over_stale_candidate_fact(
        self, client, site_id, document, file, db_session, company_member_user_auth_header, monkeypatch
    ):
        """The run being accepted is the authoritative AI original, not a stale candidate fact value."""
        self._patch_allowed_keys(monkeypatch, [self.BASELINE_KEY])
        field = self._make_canonical_field(db_session, self.CANONICAL_NAME, self.BASELINE_KEY)
        # Stale fact says AI=999, but the run being accepted parsed 100. Submitting 100 must be accepted.
        self._make_candidate_fact(db_session, document.site_id, field.id, file.id, "999", "999")
        run = self._make_run(db_session, file.id, {self.CANONICAL_NAME: {"value": "100"}})

        response = client.post(
            self._bulk_endpoint(site_id, document.id, file.id),
            headers=company_member_user_auth_header,
            json={"run_id": run.id, "fields": [{"field_name": self.BASELINE_KEY, "value": "100"}]},
        )

        assert response.status_code == 200
        saved = self._get_key(db_session, document, file)
        assert saved.status == "accepted"

    def test_bulk_override_candidate_fact_carries_provenance(
        self, client, site_id, document, file, db_session, company_member_user_auth_header, monkeypatch
    ):
        """Bulk override candidate fact carries run-sourced AI evidence + reviewer override provenance."""
        self._patch_allowed_keys(monkeypatch, [self.BASELINE_KEY])
        field = self._make_canonical_field(db_session, self.CANONICAL_NAME, self.BASELINE_KEY)
        run = self._make_run(
            db_session,
            file.id,
            {self.CANONICAL_NAME: {"value": "100", "confidence": 0.9, "evidence": {"page": 3}}},
        )

        response = client.post(
            self._bulk_endpoint(site_id, document.id, file.id),
            headers=company_member_user_auth_header,
            json={
                "run_id": run.id,
                "fields": [
                    {"field_name": self.BASELINE_KEY, "value": "999", "override_notes": "datasheet correction"}
                ],
            },
        )

        assert response.status_code == 200
        fact = ProjectFactCRUD(db_session).get_candidate_fact(document.site_id, field.id, file.id)
        assert fact is not None
        assert fact.source_run_id == run.id
        assert fact.ai_extracted_value == {"v": "100"}
        assert fact.overridden_by_id is not None
        assert fact.override_notes == "datasheet correction"

    def test_bulk_reaccept_clears_stale_override_columns(
        self,
        client,
        site_id,
        document,
        file,
        db_session,
        company_member_user_auth_header,
        non_system_user_id,
        monkeypatch,
    ):
        """Re-accepting the AI value on a previously-overridden key clears its override metadata."""
        self._patch_allowed_keys(monkeypatch, [self.BASELINE_KEY])
        self._make_canonical_field(db_session, self.CANONICAL_NAME, self.BASELINE_KEY)
        run = self._make_run(db_session, file.id, {self.CANONICAL_NAME: {"value": "100"}})
        DocumentKeyCRUD(db_session).create_item(
            {
                "document_id": document.id,
                "file_id": file.id,
                "name": self.BASELINE_KEY,
                "value": "100",
                "status": "overridden",
                "override_value": "999",
                "overridden_by_id": non_system_user_id,
                "overridden_at": datetime.now(timezone.utc),
                "override_notes": "prior override rationale",
            }
        )

        response = client.post(
            self._bulk_endpoint(site_id, document.id, file.id),
            headers=company_member_user_auth_header,
            json={"run_id": run.id, "fields": [{"field_name": self.BASELINE_KEY, "value": "100"}]},
        )

        assert response.status_code == 200
        saved = self._get_key(db_session, document, file)
        assert saved.status == "accepted"
        assert saved.override_value is None
        assert saved.overridden_by_id is None
        assert saved.overridden_at is None
        assert saved.override_notes is None
