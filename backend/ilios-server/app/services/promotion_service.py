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

# Umbrella error_code for a promotion blocked by the freshness guard. Per-field
# ``reason`` values carry the specifics. The router maps this code (and the
# legacy alias ``STALE_CANDIDATE_FACT``) to HTTP 409 with a structured body;
# every other PromotionError stays HTTP 400.
PROMOTION_SOURCE_STALE_CODE = "PROMOTION_SOURCE_STALE"

# Human-facing remediation surfaced on every stale field.
STALE_REQUIRED_ACTION = "Re-review this value in Data Room before promotion."


class PromotionError(Exception):
    def __init__(
        self,
        message: str,
        error_code: str = "PROMOTION_ERROR",
        details: Optional[dict] = None,
    ):
        self.message = message
        self.error_code = error_code
        # Machine-readable, additive payload (e.g. {"stale_fields": [...]}).
        self.details = details or {}
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
        active_facts = self.fact_crud.get_active_facts_for_site(site_id)

        candidate_field_ids = {cf.canonical_field_id for cf in candidate_facts}
        active_facts_by_field = {af.canonical_field_id: af for af in active_facts}

        changes = []

        for candidate in candidate_facts:
            field_name = candidate.canonical_field.display_name if candidate.canonical_field else "Unknown"
            candidate_value = self._extract_value(candidate.value)
            
            if candidate.canonical_field_id in active_facts_by_field:
                active_fact = active_facts_by_field[candidate.canonical_field_id]
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

        target_file = self.file_crud.get_by_id(file_id)
        target_document_id = target_file.document_id if target_file else None

        for active_fact in active_facts:
            if active_fact.canonical_field_id not in candidate_field_ids:
                is_same_document = False
                if active_fact.source_file_id and target_document_id:
                    source_file = self.file_crud.get_by_id(active_fact.source_file_id)
                    if source_file and source_file.document_id == target_document_id:
                        is_same_document = True
                
                if is_same_document:
                    field_name = active_fact.canonical_field.display_name if active_fact.canonical_field else "Unknown"
                    active_value = self._extract_value(active_fact.value)
                    changes.append({
                        "type": "removed",
                        "field_name": field_name,
                        "field_id": active_fact.canonical_field_id,
                        "current_value": active_value,
                        "new_value": None,
                        "current_source_file_id": active_fact.source_file_id,
                        "new_source_file_id": None,
                    })

        summary = {
            "added": len([c for c in changes if c["type"] == "added"]),
            "changed": len([c for c in changes if c["type"] == "changed"]),
            "removed": len([c for c in changes if c["type"] == "removed"]),
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

        # Freshness guard (fail-closed). Runs BEFORE any writes and BEFORE the
        # write transaction's try/except (which wraps everything as
        # PROMOTION_FAILED), so a stale source raises PROMOTION_SOURCE_STALE
        # with structured per-field details that the router can surface as 409.
        # No promotion, no fact transitions, and no audit record are written
        # when a single candidate is stale (all-or-nothing).
        self.validate_promotion_freshness(site_id, file_id, promoted_by_id)

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

    def validate_promotion_freshness(
        self,
        site_id: int,
        file_id: int,
        promoted_by_id: Optional[int] = None,
    ) -> list[dict]:
        """Fail-closed preflight: prove every candidate fact is current.

        A candidate fact may only be promoted when its accepted *source basis*
        can be proven current against the file version's CURRENT parse run (the
        latest run by ``extraction_run_number`` — the same anchor
        ``bulk_accept_ai_values`` uses). This is a PURE read: it performs NO DB
        writes and NO commits. It either returns a (possibly empty) list of
        non-blocking warnings, or raises :class:`PromotionError`
        (``PROMOTION_SOURCE_STALE``) carrying ``details['stale_fields']`` when
        ANY candidate is stale — one stale candidate blocks the whole promotion.

        Per-candidate decision matrix:

        * No usable current parse for the version (no run, latest run not
          ``completed``, or latest run has no parseable result) -> every
          candidate is stale (``no_current_parse`` / ``latest_parse_not_completed``
          / ``latest_parse_unusable``). Promotion is refused while a reparse is
          in flight or the latest attempt failed.
        * ``source_run_id`` present and == current run id -> FRESH by lineage
          (override-safe: an override legitimately differs from the AI value, so
          no value comparison is made). A corruption guard still requires the
          field to be readable in the current run (``source_basis_unreadable``).
        * ``source_run_id`` present and != current run id -> STALE
          (``source_run_outdated``): accepted from a superseded parse.
        * ``source_run_id`` NULL (manual / single-key / legacy acceptance):
            - field absent from the current parse -> STALE (``field_removed``).
            - baseline-driving field -> STALE (``no_lineage_baseline_field``)
              even when the value matches: a value that feeds expected/baseline
              math may never be promoted without provable parse lineage.
            - non-baseline field whose normalized value matches the current
              extracted value -> ALLOWED (warning ``no_lineage_value_match``).
            - non-baseline field whose value diverged -> STALE
              (``value_diverged_no_lineage``).
        """
        candidate_facts = self.fact_crud.get_candidate_facts_for_file(file_id)
        if not candidate_facts:
            # Nothing to promote -> nothing to prove. Preserves the existing
            # (no-op) behavior of promoting a version with no candidate facts.
            return []

        # Local imports keep this guard self-contained and avoid any import-cycle
        # / heavy-module load at PromotionService import time.
        from app.crud.ai_parsing_result import AIParsingResultCRUD
        from app.helpers.due_diligence.override_guardrail import normalize_term
        from app.models.file import FileParsingStatuses
        from app.services.project_facts_service import ProjectFactsService
        from app.services.telemetry.baseline_from_facts_service import (
            BASELINE_DRIVING_FACT_FIELDS,
        )

        current_run = AIParsingResultCRUD(self.db_session).get_latest_run_for_file(
            file_id
        )

        # Version-level gate: with no usable current parse basis, EVERY candidate
        # is unprovable. Classify the reason (fail-closed; never fall back to an
        # older completed run).
        run_level_reason: Optional[str] = None
        if current_run is None:
            run_level_reason = "no_current_parse"
        elif current_run.status != FileParsingStatuses.completed:
            run_level_reason = "latest_parse_not_completed"
        elif not isinstance(getattr(current_run, "parsed_result", None), dict) or not current_run.parsed_result:
            run_level_reason = "latest_parse_unusable"

        stale_fields: list[dict] = []
        warnings: list[dict] = []

        for candidate in candidate_facts:
            canonical = candidate.canonical_field
            field_name = canonical.name if canonical else None
            display_name = (
                canonical.display_name if canonical else (field_name or "Unknown")
            )
            item = {
                "canonical_field": field_name,
                "field_display_name": display_name,
                "canonical_field_id": candidate.canonical_field_id,
                "fact_id": candidate.id,
                "required_action": STALE_REQUIRED_ACTION,
            }

            if run_level_reason is not None:
                stale_fields.append({**item, "reason": run_level_reason})
                continue

            field_data = (
                ProjectFactsService._find_field_in_run(current_run, field_name)
                if field_name
                else {}
            )
            current_extracted = field_data.get("value")
            field_present = current_extracted is not None
            is_baseline_driving = field_name in BASELINE_DRIVING_FACT_FIELDS

            if candidate.source_run_id is not None:
                if candidate.source_run_id == current_run.id:
                    # Lineage proves freshness. Corruption guard only: the field
                    # must still be readable in the (immutable) current run.
                    if not field_present:
                        stale_fields.append({**item, "reason": "source_basis_unreadable"})
                    # else: FRESH (no value-vs-AI comparison — override-safe).
                else:
                    stale_fields.append({**item, "reason": "source_run_outdated"})
            else:
                # No parse-run lineage (manual / single-key / legacy acceptance).
                if not field_present:
                    stale_fields.append({**item, "reason": "field_removed"})
                elif is_baseline_driving:
                    stale_fields.append({**item, "reason": "no_lineage_baseline_field"})
                else:
                    candidate_value = self._extract_value(candidate.value)
                    if normalize_term(candidate_value) == normalize_term(current_extracted):
                        warnings.append({**item, "reason": "no_lineage_value_match"})
                    else:
                        stale_fields.append({**item, "reason": "value_diverged_no_lineage"})

        if stale_fields:
            for s in stale_fields:
                logger.warning(
                    "Promotion blocked (stale source): site_id=%s file_id=%s "
                    "canonical_field=%s fact_id=%s reason=%s user_id=%s ts=%s",
                    site_id,
                    file_id,
                    s["canonical_field"],
                    s["fact_id"],
                    s["reason"],
                    promoted_by_id,
                    datetime.now(timezone.utc).isoformat(),
                )
            raise PromotionError(
                (
                    f"Promotion blocked: {len(stale_fields)} value(s) cannot be "
                    "proven current against the latest parse of this version. "
                    "Re-review them in the Data Room before promoting."
                ),
                error_code=PROMOTION_SOURCE_STALE_CODE,
                details={"stale_fields": stale_fields},
            )

        for w in warnings:
            logger.info(
                "Promotion freshness warning: site_id=%s file_id=%s "
                "canonical_field=%s fact_id=%s reason=%s user_id=%s",
                site_id,
                file_id,
                w["canonical_field"],
                w["fact_id"],
                w["reason"],
                promoted_by_id,
            )
        return warnings

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
