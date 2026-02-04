"""
ProjectFactsService - manages project facts (lender-quality assumptions)

This service handles:
- Creating candidate facts from accepted document keys
- Querying active facts for downstream modules
- Mapping extraction keys to canonical fields
"""

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.crud.canonical_field import CanonicalFieldCRUD
from app.crud.project_fact import ProjectFactCRUD
from app.models.document import DocumentKey
from app.models.project_facts import ProjectFact, CanonicalField

logger = logging.getLogger(__name__)


class ProjectFactsService:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.fact_crud = ProjectFactCRUD(db_session)
        self.field_crud = CanonicalFieldCRUD(db_session)

    def get_active_facts(self, site_id: int) -> list[dict]:
        facts = self.fact_crud.get_active_facts_for_site(site_id)
        return [self._fact_to_dict(f) for f in facts]

    def get_active_fact_value(self, site_id: int, field_name: str) -> Optional[any]:
        field = self.field_crud.get_by_name(field_name)
        if not field:
            return None
        fact = self.fact_crud.get_active_fact(site_id, field.id)
        if not fact:
            return None
        return self._extract_value(fact.value)

    def get_candidate_facts_for_file(self, file_id: int) -> list[dict]:
        facts = self.fact_crud.get_candidate_facts_for_file(file_id)
        return [self._fact_to_dict(f) for f in facts]

    def create_candidate_from_document_key(
        self,
        document_key: DocumentKey,
        site_id: int
    ) -> Optional[ProjectFact]:
        if not document_key.file_id:
            logger.warning(f"DocumentKey {document_key.id} has no file_id, cannot create candidate fact")
            return None

        canonical_field = self._resolve_canonical_field(document_key.name)
        if not canonical_field:
            logger.info(f"No canonical field mapping for key '{document_key.name}', skipping fact creation")
            return None

        effective_value = document_key.effective_value

        fact = self.fact_crud.create_or_update_candidate(
            site_id=site_id,
            canonical_field_id=canonical_field.id,
            value=effective_value,
            source_file_id=document_key.file_id,
            source_document_key_id=document_key.id,
        )
        logger.info(
            f"Created/updated candidate fact for site={site_id}, "
            f"field={canonical_field.name}, file={document_key.file_id}"
        )
        return fact

    def _resolve_canonical_field(self, extraction_key: str) -> Optional[CanonicalField]:
        return self.field_crud.find_by_extraction_key(extraction_key)

    def _fact_to_dict(self, fact: ProjectFact) -> dict:
        return {
            "id": fact.id,
            "site_id": fact.site_id,
            "canonical_field_id": fact.canonical_field_id,
            "field_name": fact.canonical_field.name if fact.canonical_field else None,
            "field_display_name": fact.canonical_field.display_name if fact.canonical_field else None,
            "value": self._extract_value(fact.value),
            "status": fact.status,
            "source_file_id": fact.source_file_id,
            "source_document_key_id": fact.source_document_key_id,
            "promoted_by_id": fact.promoted_by_id,
            "promoted_at": fact.promoted_at.isoformat() if fact.promoted_at else None,
        }

    @staticmethod
    def _extract_value(value_jsonb) -> any:
        if value_jsonb is None:
            return None
        if isinstance(value_jsonb, dict) and "v" in value_jsonb:
            return value_jsonb["v"]
        return value_jsonb
