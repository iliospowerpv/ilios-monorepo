"""DD V2 Phase 1.5C — stale override provenance cleanup on the candidate fact.

When a previously-overridden document key is re-accepted, ``create_candidate_from_document_key``
must clear the stale override metadata (``overridden_by_id``/``overridden_at``/``override_notes``)
on the existing candidate fact, while leaving the captured ``ai_extracted_value`` intact.
"""
from datetime import datetime, timezone

from app.crud.document_key import DocumentKeyCRUD
from app.crud.project_fact import ProjectFactCRUD
from app.models.project_facts import CanonicalField
from app.services.project_facts_service import ProjectFactsService

BASELINE_KEY = "Module Wattage"
CANONICAL_NAME = "module_wattage"


class TestCandidateFactOverrideProvenance:
    def test_reaccept_clears_stale_override_provenance(self, db_session, document, file, non_system_user_id):
        # Session-scoped db_session with no rollback + UNIQUE canonical_fields.name -> get-or-create.
        field = db_session.query(CanonicalField).filter_by(name=CANONICAL_NAME).first()
        if field is None:
            field = CanonicalField(
                name=CANONICAL_NAME, display_name=BASELINE_KEY, field_type="text", is_active=True
            )
            db_session.add(field)
            db_session.commit()
            db_session.refresh(field)

        # Re-accepted document key: status "accepted", no override metadata on the key.
        doc_key = DocumentKeyCRUD(db_session).create_item(
            {
                "document_id": document.id,
                "file_id": file.id,
                "name": BASELINE_KEY,
                "value": "100",
                "status": "accepted",
                "accepted_by_id": non_system_user_id,
                "accepted_at": datetime.now(timezone.utc),
            }
        )

        # Existing candidate fact still carrying STALE override provenance from a prior override.
        fact_crud = ProjectFactCRUD(db_session)
        fact = fact_crud.create_or_update_candidate(
            site_id=document.site_id,
            canonical_field_id=field.id,
            value="100",
            source_file_id=file.id,
            source_document_key_id=doc_key.id,
            provenance={
                "ai_extracted_value": {"v": "100"},
                "overridden_by_id": non_system_user_id,
                "overridden_at": datetime.now(timezone.utc),
                "override_notes": "stale prior override reason",
            },
        )
        assert fact.override_notes == "stale prior override reason"
        assert fact.overridden_by_id == non_system_user_id

        # Re-accept via the service: stale override metadata must be cleared.
        ProjectFactsService(db_session).create_candidate_from_document_key(
            doc_key, document.site_id, source_document_type="Executive Summary"
        )
        db_session.refresh(fact)

        assert fact.overridden_by_id is None
        assert fact.overridden_at is None
        assert fact.override_notes is None
        # The original AI evidence is preserved across re-accept.
        assert fact.ai_extracted_value == {"v": "100"}
        # Reviewer (acceptance) identity is captured from the key.
        assert fact.accepted_by_id == non_system_user_id
