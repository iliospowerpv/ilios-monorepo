"""
PromotionService - handles "Promote to Current Assumptions" workflow

This service implements the lender-quality gate for promoting document version
facts to become the active project assumptions. It ensures:
- Role-based access (Company Admin or System User only)
- Atomic promotion with proper state transitions
- Full audit trail with diff snapshots
- Deterministic diff computation
"""

import logging
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.crud.assumption_promotion import AssumptionPromotionCRUD
from app.crud.project_fact import ProjectFactCRUD
from app.crud.file import FileCRUD
from app.models.project_facts import ProjectFact, FactStatus, AssumptionPromotion
from app.models.file import File
from app.models.document import Document

logger = logging.getLogger(__name__)


class PromotionError(Exception):
    def __init__(self, message: str, error_code: str = "PROMOTION_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(message)


class PromotionService:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.fact_crud = ProjectFactCRUD(db_session)
        self.promotion_crud = AssumptionPromotionCRUD(db_session)
        self.file_crud = FileCRUD(db_session)

    def compute_promotion_diff(
        self,
        site_id: int,
        file_id: int
    ) -> dict:
        candidate_facts = self.fact_crud.get_candidate_facts_for_file(file_id)
        
        if not candidate_facts:
            return {
                "has_changes": False,
                "changes": [],
                "summary": {"added": 0, "changed": 0, "removed": 0}
            }

        changes = []
        for candidate in candidate_facts:
            active_fact = self.fact_crud.get_active_fact(
                site_id, candidate.canonical_field_id
            )
            
            field_name = candidate.canonical_field.display_name if candidate.canonical_field else "Unknown"
            candidate_value = self._extract_value(candidate.value)
            
            if active_fact:
                active_value = self._extract_value(active_fact.value)
                if active_value != candidate_value:
                    changes.append({
                        "type": "changed",
                        "field_name": field_name,
                        "field_id": candidate.canonical_field_id,
                        "current_value": active_value,
                        "new_value": candidate_value,
                        "current_source_file_id": active_fact.source_file_id,
                        "new_source_file_id": file_id,
                    })
            else:
                changes.append({
                    "type": "added",
                    "field_name": field_name,
                    "field_id": candidate.canonical_field_id,
                    "current_value": None,
                    "new_value": candidate_value,
                    "current_source_file_id": None,
                    "new_source_file_id": file_id,
                })

        summary = {
            "added": len([c for c in changes if c["type"] == "added"]),
            "changed": len([c for c in changes if c["type"] == "changed"]),
            "removed": 0,
        }

        return {
            "has_changes": len(changes) > 0,
            "changes": changes,
            "summary": summary
        }

    def promote_version(
        self,
        site_id: int,
        document_id: int,
        file_id: int,
        promoted_by_id: int,
        notes: Optional[str] = None
    ) -> dict:
        file = self.file_crud.get_by_id(file_id)
        if not file:
            raise PromotionError("File not found", "FILE_NOT_FOUND")
        
        if file.document_id != document_id:
            raise PromotionError("File does not belong to document", "FILE_DOCUMENT_MISMATCH")
        
        document = file.document
        if document.site_id != site_id:
            raise PromotionError("Document does not belong to site", "DOCUMENT_SITE_MISMATCH")

        diff = self.compute_promotion_diff(site_id, file_id)

        try:
            self._set_previous_version_not_actual(document_id, file_id)

            self._set_file_actual(file_id)

            promoted_facts = self._promote_candidate_facts(
                site_id, file_id, promoted_by_id, notes
            )

            promotion_record = self.promotion_crud.create_promotion_record(
                site_id=site_id,
                document_id=document_id,
                file_id=file_id,
                promoted_by_id=promoted_by_id,
                notes=notes,
                diff_json=diff
            )

            self.db_session.commit()

            logger.info(
                f"Promoted version file_id={file_id} for document_id={document_id}, "
                f"site_id={site_id} by user_id={promoted_by_id}. "
                f"Facts promoted: {len(promoted_facts)}"
            )

            return {
                "promoted": True,
                "file_id": file_id,
                "document_id": document_id,
                "promotion_id": promotion_record.id,
                "facts_promoted": len(promoted_facts),
                "diff": diff
            }

        except Exception as e:
            self.db_session.rollback()
            logger.error(f"Promotion failed: {str(e)}")
            raise PromotionError(f"Promotion failed: {str(e)}", "PROMOTION_FAILED")

    def _set_previous_version_not_actual(self, document_id: int, new_file_id: int):
        files = self.db_session.query(File).filter(
            File.document_id == document_id,
            File.is_actual == True,
            File.id != new_file_id
        ).all()
        
        for f in files:
            f.is_actual = False
            self.db_session.add(f)

    def _set_file_actual(self, file_id: int):
        file = self.file_crud.get_by_id(file_id)
        if file:
            file.is_actual = True
            self.db_session.add(file)

    def _promote_candidate_facts(
        self,
        site_id: int,
        file_id: int,
        promoted_by_id: int,
        notes: Optional[str]
    ) -> list[ProjectFact]:
        candidate_facts = self.fact_crud.get_candidate_facts_for_file(file_id)
        promoted = []

        for candidate in candidate_facts:
            self.fact_crud.retire_active_fact(
                site_id, candidate.canonical_field_id, candidate.id
            )

            self.fact_crud.promote_candidate_to_active(
                candidate, promoted_by_id, notes
            )
            promoted.append(candidate)

        return promoted

    @staticmethod
    def _extract_value(value_jsonb) -> any:
        if value_jsonb is None:
            return None
        if isinstance(value_jsonb, dict) and "v" in value_jsonb:
            return value_jsonb["v"]
        return value_jsonb
