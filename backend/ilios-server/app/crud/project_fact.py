from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.crud.base_crud import BaseCRUD
from app.models.project_facts import ProjectFact, FactStatus


class ProjectFactCRUD(BaseCRUD):
    def __init__(self, db_session: Session):
        super().__init__(ProjectFact, db_session)

    def get_active_facts_for_site(self, site_id: int) -> list[ProjectFact]:
        return self.db_session.query(ProjectFact).filter(
            ProjectFact.site_id == site_id,
            ProjectFact.status == FactStatus.active.value
        ).all()

    def get_candidate_facts_for_file(self, file_id: int) -> list[ProjectFact]:
        return self.db_session.query(ProjectFact).filter(
            ProjectFact.source_file_id == file_id,
            ProjectFact.status == FactStatus.candidate.value
        ).all()

    def get_active_fact(self, site_id: int, canonical_field_id: int) -> Optional[ProjectFact]:
        return self.db_session.query(ProjectFact).filter(
            ProjectFact.site_id == site_id,
            ProjectFact.canonical_field_id == canonical_field_id,
            ProjectFact.status == FactStatus.active.value
        ).first()

    def get_candidate_fact(
        self, site_id: int, canonical_field_id: int, source_file_id: int
    ) -> Optional[ProjectFact]:
        return self.db_session.query(ProjectFact).filter(
            ProjectFact.site_id == site_id,
            ProjectFact.canonical_field_id == canonical_field_id,
            ProjectFact.source_file_id == source_file_id,
            ProjectFact.status == FactStatus.candidate.value
        ).first()

    def create_or_update_candidate(
        self,
        site_id: int,
        canonical_field_id: int,
        value: any,
        source_file_id: int,
        source_document_key_id: int,
        provenance: Optional[dict] = None,
    ) -> ProjectFact:
        """Create or update a candidate fact.

        ``provenance`` (DD V2 Phase 1A) is an optional dict of additive provenance/audit
        columns (source_run_id, evidence, ai_confidence, ai_extracted_value,
        accepted_by_id/at, overridden_by_id/at, override_notes, source_document_type).
        It is written on BOTH the create and the update branch so re-accepting a key
        refreshes its evidence instead of leaving stale provenance behind. Callers must
        pre-filter out None values they do not wish to overwrite.
        """
        wrapped_value = {"v": value} if not isinstance(value, dict) else value
        provenance = provenance or {}

        existing = self.get_candidate_fact(site_id, canonical_field_id, source_file_id)
        if existing:
            update_payload = {
                "value": wrapped_value,
                "source_document_key_id": source_document_key_id,
                **provenance,
            }
            self.update_by_id(existing.id, update_payload)
            self.db_session.refresh(existing)
            return existing

        create_payload = {
            "site_id": site_id,
            "canonical_field_id": canonical_field_id,
            "value": wrapped_value,
            "status": FactStatus.candidate.value,
            "source_file_id": source_file_id,
            "source_document_key_id": source_document_key_id,
            **provenance,
        }
        return self.create_item(create_payload)

    def retire_active_fact(self, site_id: int, canonical_field_id: int, superseding_fact_id: int) -> Optional[ProjectFact]:
        active = self.get_active_fact(site_id, canonical_field_id)
        if active:
            self.update_by_id(active.id, {
                "status": FactStatus.retired.value,
                # Legacy backward pointer left untouched (read by summary_stats.py).
                "supersedes_fact_id": superseding_fact_id,
                # DD V2 Phase 1A forward-semantics reverse pointer + closed window.
                "superseded_by_fact_id": superseding_fact_id,
                "effective_to": datetime.now(timezone.utc),
            })
            self.db_session.refresh(active)
        return active

    def promote_candidate_to_active(
        self,
        fact: ProjectFact,
        promoted_by_id: int,
        notes: Optional[str] = None
    ) -> ProjectFact:
        self.update_by_id(fact.id, {
            "status": FactStatus.active.value,
            "promoted_by_id": promoted_by_id,
            "promoted_at": datetime.now(timezone.utc),
            "promotion_notes": notes,
            "effective_from": datetime.now(timezone.utc),
        })
        self.db_session.refresh(fact)
        return fact
