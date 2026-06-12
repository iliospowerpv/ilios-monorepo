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
    # Provenance columns that capture a manual override. They are force-cleared on the
    # candidate fact whenever a key is (re-)accepted (DD V2 Phase 1.5C).
    _OVERRIDE_PROVENANCE_KEYS = ("overridden_by_id", "overridden_at", "override_notes")

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
        site_id: int,
        run=None,
        source_document_type: Optional[str] = None,
    ) -> Optional[ProjectFact]:
        """Create/update a candidate fact from an accepted/overridden document key.

        DD V2 Phase 1A: captures additive provenance on the candidate fact. Reviewer
        identity/rationale (accepted_by/overridden_by/override_notes) always come from
        the document key. AI evidence/confidence/raw value are pulled from ``run`` (the
        validated parse run) when provided — the manual single-key path passes no run,
        so manual entries/overrides carry no fabricated AI evidence.
        """
        if not document_key.file_id:
            logger.warning(f"DocumentKey {document_key.id} has no file_id, cannot create candidate fact")
            return None

        canonical_field = self._resolve_canonical_field(document_key.name)
        if not canonical_field:
            logger.info(f"No canonical field mapping for key '{document_key.name}', skipping fact creation")
            return None

        effective_value = document_key.effective_value

        provenance: dict = {"source_document_type": source_document_type}

        # Reviewer identity/rationale snapshot from the document key (always available).
        if document_key.accepted_by_id is not None:
            provenance["accepted_by_id"] = document_key.accepted_by_id
            provenance["accepted_at"] = document_key.accepted_at

        # Override-provenance lifecycle (DD V2 Phase 1.5C): when the key is overridden,
        # snapshot the reviewer rationale; when it is (re-)accepted, EXPLICITLY clear any
        # stale override metadata so a prior override never lingers on the candidate fact.
        # ``ai_extracted_value`` is intentionally left untouched here — re-accepting must
        # not discard the original AI evidence captured at bulk-accept.
        is_override = document_key.status == "overridden"
        if is_override:
            provenance["overridden_by_id"] = document_key.overridden_by_id
            provenance["overridden_at"] = document_key.overridden_at
            provenance["override_notes"] = getattr(document_key, "override_notes", None)
        else:
            for clearable in self._OVERRIDE_PROVENANCE_KEYS:
                provenance[clearable] = None

        # AI evidence/confidence/raw value from the parse run (manual edits have none).
        if run is not None:
            provenance["source_run_id"] = run.id
            field_data = self._find_field_in_run(run, canonical_field.name)
            if field_data.get("evidence"):
                provenance["evidence"] = field_data["evidence"]
            if field_data.get("confidence") is not None:
                provenance["ai_confidence"] = field_data["confidence"]
            if field_data.get("value") is not None:
                provenance["ai_extracted_value"] = {"v": field_data["value"]}

        # Drop None entries so we never overwrite existing provenance with NULL on update —
        # EXCEPT the override metadata on (re-)accept, which must be force-cleared to None.
        provenance = {
            k: v
            for k, v in provenance.items()
            if v is not None or (not is_override and k in self._OVERRIDE_PROVENANCE_KEYS)
        }

        fact = self.fact_crud.create_or_update_candidate(
            site_id=site_id,
            canonical_field_id=canonical_field.id,
            value=effective_value,
            source_file_id=document_key.file_id,
            source_document_key_id=document_key.id,
            provenance=provenance,
        )
        logger.info(
            f"Created/updated candidate fact for site={site_id}, "
            f"field={canonical_field.name}, file={document_key.file_id}"
        )
        return fact

    def _resolve_canonical_field(self, extraction_key: str) -> Optional[CanonicalField]:
        return self.field_crud.find_by_extraction_key(extraction_key)

    def resolve_ai_original_value(
        self,
        site_id: int,
        canonical_field: Optional[CanonicalField],
        source_file_id: Optional[int],
    ) -> tuple[bool, any]:
        """Resolve the AI-extracted/original value for a field (DD V2 Phase 1.5A).

        Used by the override guardrail to decide whether a submitted value diverges from
        what the AI proposed. Resolution order:

        1. The candidate fact's captured ``ai_extracted_value`` (recorded at bulk-accept
           from the validated parse run) — the authoritative original.
        2. The latest completed parse run for the file (fallback for keys edited before a
           bulk-accept ever ran).

        Returns ``(determined, value)``. ``determined`` is ``False`` when no AI value can
        be established, so the caller can fail safely instead of fabricating a comparison.
        """
        if canonical_field is None or source_file_id is None:
            return False, None

        # 1. Candidate fact's captured AI value (primary, authoritative).
        fact = self.fact_crud.get_candidate_fact(site_id, canonical_field.id, source_file_id)
        if fact is not None and fact.ai_extracted_value is not None:
            return True, self._extract_value(fact.ai_extracted_value)

        # 2. Latest completed parse run for the file (pre-bulk-accept fallback).
        from app.crud.ai_parsing_result import AIParsingResultCRUD

        runs = AIParsingResultCRUD(self.db_session).get_completed_runs_for_file(source_file_id)
        for run in runs:
            field_data = self._find_field_in_run(run, canonical_field.name)
            if field_data.get("value") is not None:
                return True, field_data["value"]

        return False, None

    def resolve_ai_original_value_for_run(
        self,
        run,
        site_id: int,
        canonical_field: Optional[CanonicalField],
        source_file_id: Optional[int],
    ) -> tuple[bool, any]:
        """Resolve the AI original for a bulk-accept item (DD V2 Phase 1.6).

        Bulk-accept holds the specific parse ``run`` whose values the reviewer is accepting, and
        that run is exactly what ``create_candidate_from_document_key`` records as provenance — so
        the run's own parsed value is the authoritative AI original for the divergence check.
        Preferring the captured candidate-fact value would mis-compare when accepting a re-parse
        (whose AI value legitimately changed) or an older run via ``allow_accept_non_latest``.

        Falls back to :meth:`resolve_ai_original_value` (candidate fact, then latest completed run)
        only when the accepted run does not carry this field.
        """
        if run is not None and canonical_field is not None:
            field_data = self._find_field_in_run(run, canonical_field.name)
            if field_data.get("value") is not None:
                return True, field_data["value"]
        return self.resolve_ai_original_value(site_id, canonical_field, source_file_id)

    @staticmethod
    def _find_field_in_run(run, field_name: str) -> dict:
        """Return {value, confidence, evidence} for ``field_name`` (snake_case canonical
        name) from a parse run, handling both ``parsed_result`` shapes. Returns {} if the
        field is absent or the run has no parsed_result.

        Format A: dict keyed by snake_case field_key -> {value, confidence, evidence}.
        Format B: {"fields": [{field_key, value, evidence, confidence}, ...]}.
        """
        parsed = getattr(run, "parsed_result", None)
        if not isinstance(parsed, dict):
            return {}

        entry = parsed.get(field_name)
        if isinstance(entry, dict):
            evidence = entry.get("evidence")
            return {
                "value": entry.get("value"),
                "confidence": entry.get("confidence"),
                "evidence": evidence if isinstance(evidence, dict) else None,
            }

        fields = parsed.get("fields")
        if isinstance(fields, list):
            for field in fields:
                if isinstance(field, dict) and field.get("field_key") == field_name:
                    evidence = field.get("evidence")
                    return {
                        "value": field.get("value"),
                        "confidence": field.get("confidence"),
                        "evidence": evidence if isinstance(evidence, dict) else None,
                    }
        return {}

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
