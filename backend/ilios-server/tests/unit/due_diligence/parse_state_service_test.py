"""Unit tests for the Data Room parse-state service (Phase 1).

These are pure service-level tests: they build the company -> site -> document ->
file -> (runs / document keys / project facts) graph directly on ``db_session``
and call :func:`build_parse_state_summary` straight, deliberately avoiding the
session-scoped ``client`` fixture (which runs the full FastAPI lifespan against
the dev DB and hangs while the Backend workflow is live).

The extraction registry is not seeded in the test DB, so
``AIParsingHandler.get_extraction_config`` is monkeypatched to return controlled
configs keyed by document-type display value, keeping every assertion
deterministic and independent of registry seeding.
"""

import copy
from datetime import datetime, timezone

import pytest

from app.crud.ai_parsing_result import AIParsingResultCRUD
from app.crud.company import CompanyCRUD
from app.crud.document import DocumentCRUD
from app.crud.document_key import DocumentKeyCRUD
from app.crud.file import FileCRUD
from app.crud.site import SiteCRUD
from app.helpers.configs.ai_parsing_helper import AIParsingHandler
from app.models.file import FileParsingStatuses
from app.models.project_facts import CanonicalField, FactStatus, ProjectFact
from app.schema.file import NoUsableFieldsReason, ParseNextAction, ParseState
from app.services.due_diligence.parse_state_service import (
    GENERIC_CONTRACTUAL_FIELD_SET,
    build_parse_state_summary,
)
from app.static.default_site_documents_enum import SiteDocumentsEnum
from tests.unit import samples

# The generic 10-field contractual stub schema (what equipment types resolve to).
GENERIC_STUB_CONFIG = {
    "fields": [{"name": name, "display_name": name} for name in sorted(GENERIC_CONTRACTUAL_FIELD_SET)]
}
# A specialized (non-stub) schema with operational fields.
RICH_CONFIG = {
    "fields": [
        {"name": "lessor", "display_name": "Lessor"},
        {"name": "term", "display_name": "Term"},
    ]
}
_CONFIG_PRESETS = {"generic": GENERIC_STUB_CONFIG, "rich": RICH_CONFIG, "none": None}


class _ParseStateFactory:
    """Builds parse-state test rows directly on the DB session."""

    def __init__(self, db_session, site, company, user_id, canonical_field, config_map):
        self.db = db_session
        self.site = site
        self.company = company
        self.user_id = user_id
        self.canonical_field = canonical_field
        self._config_map = config_map

    def make_document(self, name=SiteDocumentsEnum.module_specs, config="generic"):
        doc = DocumentCRUD(self.db).create_item({"site_id": self.site.id, "name": name})
        self._config_map[name.value] = _CONFIG_PRESETS.get(config, config)
        return doc

    def make_file(self, doc, is_actual=False, deleted=False):
        return FileCRUD(self.db).create_item(
            {
                "filepath": "test/path/doc.pdf",
                "filename": "doc.pdf",
                "user_id": self.user_id,
                "document_id": doc.id,
                "is_actual": is_actual,
                "deleted": deleted,
            }
        )

    def add_run(
        self,
        file,
        status=FileParsingStatuses.completed,
        run_number=1,
        parsed_result=None,
        result=None,
        start_time=None,
    ):
        return AIParsingResultCRUD(self.db).create_item(
            {
                "file_id": file.id,
                "status": status,
                "extraction_run_number": run_number,
                "parsed_result": parsed_result,
                "result": result,
                "start_time": start_time or datetime.now(timezone.utc),
            }
        )

    def add_key(self, doc, file, name="Summary", value="value", status="accepted"):
        return DocumentKeyCRUD(self.db).create_item(
            {
                "document_id": doc.id,
                "file_id": file.id,
                "name": name,
                "value": value,
                "status": status,
            }
        )

    def add_active_fact(self, file):
        fact = ProjectFact(
            site_id=self.site.id,
            canonical_field_id=self.canonical_field.id,
            status=FactStatus.active.value,
            source_file_id=file.id,
            value="promoted-value",
        )
        self.db.add(fact)
        self.db.commit()
        self.db.refresh(fact)
        return fact


@pytest.fixture()
def ps_env(db_session, non_system_user_id, monkeypatch):
    """Build an isolated company/site/canonical-field and a row factory.

    Cleanup deletes the site (cascading documents -> files -> runs -> keys ->
    facts), the canonical field, then the company, so each test starts clean and
    the unique company/canonical-field constraints never collide across tests.
    """
    company = CompanyCRUD(db_session).create_item(copy.deepcopy(samples.SETUP_COMPANIES[0]))
    site = SiteCRUD(db_session).create_item(
        {**copy.deepcopy(samples.TEST_SITE_BODY), "company_id": company.id}
    )
    canonical_field = CanonicalField(
        name="ps_test_field", display_name="PS Test Field", field_type="text"
    )
    db_session.add(canonical_field)
    db_session.commit()
    db_session.refresh(canonical_field)

    config_map: dict = {}
    monkeypatch.setattr(
        AIParsingHandler, "get_extraction_config", lambda self, doc_type: config_map.get(doc_type)
    )

    yield _ParseStateFactory(db_session, site, company, non_system_user_id, canonical_field, config_map)

    SiteCRUD(db_session).delete_by_id(site.id)
    db_session.query(CanonicalField).filter(CanonicalField.id == canonical_field.id).delete()
    db_session.commit()
    CompanyCRUD(db_session).delete_by_id(company.id)


class TestParseStateService:
    def test_not_yet_parsed_with_sole_non_current_warning(self, ps_env, db_session):
        doc = ps_env.make_document(SiteDocumentsEnum.module_specs, config="generic")
        file = ps_env.make_file(doc)  # is_actual defaults False -> not current, sole version

        summary = build_parse_state_summary(file, db_session)

        assert summary.parse_state == ParseState.not_yet_parsed
        assert summary.next_action == ParseNextAction.parse_document
        assert summary.latest_run is None
        assert summary.last_parse_attempt_at is None
        assert summary.active_reprocess_in_progress is False
        # Equipment + generic-stub classification surfaces even before any parse.
        assert summary.selected_document_type.is_equipment_type is True
        assert summary.selected_document_type.is_generic_contractual_stub is True
        assert summary.file_version.is_sole_version is True
        assert summary.file_version.is_current_version is False
        assert "sole_non_current_version" in summary.warnings
        assert "no_equipment_extraction_schema" in summary.warnings

    def test_not_current_version_warning_when_multiple_versions(self, ps_env, db_session):
        doc = ps_env.make_document(SiteDocumentsEnum.site_lease, config="rich")
        older = ps_env.make_file(doc, is_actual=False)
        ps_env.make_file(doc, is_actual=True)  # a newer current sibling exists

        summary = build_parse_state_summary(older, db_session)

        assert summary.file_version.is_sole_version is False
        assert "not_current_version" in summary.warnings
        assert "sole_non_current_version" not in summary.warnings

    def test_parsing_in_progress(self, ps_env, db_session):
        doc = ps_env.make_document(SiteDocumentsEnum.site_lease, config="rich")
        file = ps_env.make_file(doc)
        ps_env.add_run(file, status=FileParsingStatuses.queued, run_number=1)

        summary = build_parse_state_summary(file, db_session)

        assert summary.parse_state == ParseState.parsing_in_progress
        assert summary.next_action == ParseNextAction.wait_for_parse
        assert summary.active_reprocess_in_progress is False
        assert summary.latest_run is not None
        assert summary.last_parse_attempt_at is not None

    def test_parse_failed(self, ps_env, db_session):
        doc = ps_env.make_document(SiteDocumentsEnum.site_lease, config="rich")
        file = ps_env.make_file(doc)
        ps_env.add_run(file, status=FileParsingStatuses.processing_failed, run_number=1)

        summary = build_parse_state_summary(file, db_session)

        assert summary.parse_state == ParseState.parse_failed
        assert summary.next_action == ParseNextAction.retry_parse
        assert "parse_failed" in summary.warnings

    def test_parsed_awaiting_review(self, ps_env, db_session):
        doc = ps_env.make_document(SiteDocumentsEnum.site_lease, config="rich")
        file = ps_env.make_file(doc)
        ps_env.add_run(
            file,
            status=FileParsingStatuses.completed,
            run_number=1,
            parsed_result={"fields": [{"field_key": "lessor", "value": "Acme LLC"}]},
        )

        summary = build_parse_state_summary(file, db_session)

        assert summary.parse_state == ParseState.parsed_awaiting_review
        assert summary.next_action == ParseNextAction.review_fields
        assert summary.reviewable_field_count == 1
        assert summary.no_usable_fields_reason is None

    def test_parsed_awaiting_review_legacy_result_format(self, ps_env, db_session):
        doc = ps_env.make_document(SiteDocumentsEnum.site_lease, config="rich")
        file = ps_env.make_file(doc)
        ps_env.add_run(
            file,
            status=FileParsingStatuses.completed,
            run_number=1,
            parsed_result=None,
            result=[{"key_item": "lessor", "value": "Legacy Corp"}],
        )

        summary = build_parse_state_summary(file, db_session)

        assert summary.parse_state == ParseState.parsed_awaiting_review
        assert summary.reviewable_field_count == 1

    def test_parsed_no_usable_fields_equipment_generic_stub(self, ps_env, db_session):
        doc = ps_env.make_document(SiteDocumentsEnum.module_specs, config="generic")
        file = ps_env.make_file(doc)
        # AI extracted equipment-specific fields the generic stub schema cannot hold.
        ps_env.add_run(
            file,
            status=FileParsingStatuses.completed,
            run_number=1,
            parsed_result={"fields": [{"field_key": "max_power_watts", "value": "400"}]},
        )

        summary = build_parse_state_summary(file, db_session)

        assert summary.parse_state == ParseState.parsed_no_usable_fields
        assert summary.no_usable_fields_reason == NoUsableFieldsReason.generic_contractual_schema
        assert summary.next_action == ParseNextAction.awaiting_equipment_schema
        assert summary.reviewable_field_count == 0
        assert "no_equipment_extraction_schema" in summary.warnings

    def test_parsed_no_usable_fields_non_equipment_generic_stub(self, ps_env, db_session):
        doc = ps_env.make_document(SiteDocumentsEnum.site_lease, config="generic")
        file = ps_env.make_file(doc)
        ps_env.add_run(
            file,
            status=FileParsingStatuses.completed,
            run_number=1,
            parsed_result={"fields": [{"field_key": "unmapped_thing", "value": "x"}]},
        )

        summary = build_parse_state_summary(file, db_session)

        assert summary.parse_state == ParseState.parsed_no_usable_fields
        assert summary.no_usable_fields_reason == NoUsableFieldsReason.generic_contractual_schema
        # Non-equipment generic stub steers to change document type, not equipment schema.
        assert summary.next_action == ParseNextAction.change_document_type
        assert "generic_contractual_schema" in summary.warnings
        assert "no_equipment_extraction_schema" not in summary.warnings

    def test_parsed_no_usable_fields_no_fields_found(self, ps_env, db_session):
        doc = ps_env.make_document(SiteDocumentsEnum.site_lease, config="rich")
        file = ps_env.make_file(doc)
        ps_env.add_run(
            file,
            status=FileParsingStatuses.completed,
            run_number=1,
            parsed_result={"fields": []},
        )

        summary = build_parse_state_summary(file, db_session)

        assert summary.parse_state == ParseState.parsed_no_usable_fields
        assert summary.no_usable_fields_reason == NoUsableFieldsReason.no_fields_found

    def test_parsed_no_usable_fields_no_schema_fields(self, ps_env, db_session):
        doc = ps_env.make_document(SiteDocumentsEnum.site_lease, config="none")
        file = ps_env.make_file(doc)
        ps_env.add_run(
            file,
            status=FileParsingStatuses.completed,
            run_number=1,
            parsed_result={"fields": [{"field_key": "anything", "value": "x"}]},
        )

        summary = build_parse_state_summary(file, db_session)

        assert summary.parse_state == ParseState.parsed_no_usable_fields
        assert summary.no_usable_fields_reason == NoUsableFieldsReason.no_schema_fields
        assert summary.selected_document_type.is_generic_contractual_stub is False

    def test_parsed_no_usable_fields_fields_did_not_map(self, ps_env, db_session):
        doc = ps_env.make_document(SiteDocumentsEnum.site_lease, config="rich")
        file = ps_env.make_file(doc)
        ps_env.add_run(
            file,
            status=FileParsingStatuses.completed,
            run_number=1,
            parsed_result={"fields": [{"field_key": "totally_other", "value": "x"}]},
        )

        summary = build_parse_state_summary(file, db_session)

        assert summary.parse_state == ParseState.parsed_no_usable_fields
        assert summary.no_usable_fields_reason == NoUsableFieldsReason.fields_did_not_map
        assert summary.next_action == ParseNextAction.change_document_type

    def test_accepted_or_overridden_outranks_parsed(self, ps_env, db_session):
        doc = ps_env.make_document(SiteDocumentsEnum.site_lease, config="rich")
        file = ps_env.make_file(doc)
        # Even with a reviewable completed run, an accepted key wins precedence.
        ps_env.add_run(
            file,
            status=FileParsingStatuses.completed,
            run_number=1,
            parsed_result={"fields": [{"field_key": "lessor", "value": "Acme"}]},
        )
        ps_env.add_key(doc, file, name="Lessor", status="accepted")

        summary = build_parse_state_summary(file, db_session)

        assert summary.parse_state == ParseState.accepted_or_overridden
        assert summary.next_action == ParseNextAction.review_or_promote
        assert summary.accepted_overridden_count == 1

    def test_promoted_outranks_everything(self, ps_env, db_session):
        doc = ps_env.make_document(SiteDocumentsEnum.site_lease, config="rich")
        file = ps_env.make_file(doc)
        ps_env.add_run(
            file,
            status=FileParsingStatuses.completed,
            run_number=1,
            parsed_result={"fields": [{"field_key": "lessor", "value": "Acme"}]},
        )
        ps_env.add_key(doc, file, name="Lessor", status="accepted")
        ps_env.add_active_fact(file)

        summary = build_parse_state_summary(file, db_session)

        assert summary.parse_state == ParseState.promoted
        assert summary.next_action == ParseNextAction.none
        assert summary.promoted_count == 1

    def test_active_reprocess_keeps_advanced_state(self, ps_env, db_session):
        doc = ps_env.make_document(SiteDocumentsEnum.site_lease, config="rich")
        file = ps_env.make_file(doc)
        # A completed run produced reviewable data...
        ps_env.add_run(
            file,
            status=FileParsingStatuses.completed,
            run_number=1,
            parsed_result={"fields": [{"field_key": "lessor", "value": "Acme"}]},
        )
        # ...and a NEWER run is queued/processing (reprocess).
        ps_env.add_run(file, status=FileParsingStatuses.processing, run_number=2)

        summary = build_parse_state_summary(file, db_session)

        # Durable advanced state is preserved, not regressed to parsing_in_progress.
        assert summary.parse_state == ParseState.parsed_awaiting_review
        assert summary.active_reprocess_in_progress is True
        assert summary.latest_run is not None
        assert summary.latest_run.status == FileParsingStatuses.processing.value

    def test_service_is_read_only(self, ps_env, db_session):
        doc = ps_env.make_document(SiteDocumentsEnum.site_lease, config="rich")
        file = ps_env.make_file(doc)
        ps_env.add_run(
            file,
            status=FileParsingStatuses.completed,
            run_number=1,
            parsed_result={"fields": [{"field_key": "lessor", "value": "Acme"}]},
        )

        def _counts():
            from app.models.document import DocumentKey
            from app.models.file import AIParsingResult, File

            return (
                db_session.query(File).count(),
                db_session.query(AIParsingResult).count(),
                db_session.query(DocumentKey).count(),
                db_session.query(ProjectFact).count(),
            )

        before = _counts()
        build_parse_state_summary(file, db_session)
        after = _counts()

        assert before == after
        assert not db_session.new
        assert not db_session.dirty
        assert not db_session.deleted
