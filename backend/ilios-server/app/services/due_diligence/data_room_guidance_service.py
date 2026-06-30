"""Read-only Data Room Guidance dashboard service (Task #92).

Aggregates, per Data Room stage, an honest completeness picture derived ONLY from
existing state — the static Expected Documents catalog, the live Document rows,
their file versions, archive flags, and recorded promotions. It introduces NO new
status storage and NEVER writes, parses, promotes, or mutates anything.

Per-stage metrics:
    expected        - number of documents the static catalog expects for the stage
    present         - expected documents that have a live (non-archived) Document
                      with at least one uploaded file version
    missing         - expected documents with no present match
    needs_update    - present documents that were promoted but have since received
                      a newer file version (derived from AssumptionPromotion vs.
                      the document's latest file version)
    optional        - expected documents flagged required=False in the catalog
    archived        - live Document rows in the stage that are archived
    version_count   - total non-deleted file versions across non-archived docs
    promotion_status- stage rollup: none | not_started | in_progress | complete
"""

from __future__ import annotations

import logging
from collections import defaultdict

from sqlalchemy.orm import Session

from app.crud.document_section import DocumentSectionCRUD
from app.helpers.due_diligence.expected_documents import get_expected_documents_for_section
from app.models.document import Document
from app.static.default_site_documents_enum import DocumentSections

logger = logging.getLogger(__name__)

# Stage-level promotion rollup labels.
PROMOTION_NONE = "none"  # no document in the stage has any uploaded file
PROMOTION_NOT_STARTED = "not_started"  # files exist but nothing has been promoted
PROMOTION_IN_PROGRESS = "in_progress"  # some promoted, or a promoted doc needs an update
PROMOTION_COMPLETE = "complete"  # every document with files is promoted and current


def _latest_version(files) -> int:
    """Highest version_number among non-deleted files (0 when none)."""
    versions = [f.version_number or 0 for f in files if not f.deleted]
    return max(versions) if versions else 0


def _document_needs_update(document: Document) -> bool:
    """A promoted document whose latest uploaded version is newer than the last
    promoted version. Pure read over already-loaded relationships."""
    promotions = document.assumption_promotions or []
    if not promotions:
        return False
    promoted_file_ids = {p.file_id for p in promotions}
    promoted_versions = [
        f.version_number or 0 for f in document.files if f.id in promoted_file_ids
    ]
    if not promoted_versions:
        return False
    return _latest_version(document.files) > max(promoted_versions)


class DataRoomGuidanceService:
    """Builds the read-only per-stage guidance summary for a site's Data Room."""

    def __init__(self, db_session: Session):
        self.db_session = db_session

    def build_guidance(self, site_id: int) -> dict:
        """Return ``{"items": [stage_guidance, ...]}`` for the site."""
        sections = DocumentSectionCRUD(self.db_session).get_site_sections(site_id)
        section_row_by_key = {section.name.name: section for section in sections}

        # Group live documents by their section enum key (e.g. "site_stage1").
        docs_by_section_key: dict[str, list[Document]] = defaultdict(list)
        for section in sections:
            key = section.name.name
            for document in section.documents:
                docs_by_section_key[key].append(document)

        items = []
        for stage in DocumentSections:
            expected = get_expected_documents_for_section(stage)
            if not expected:
                continue
            items.append(
                self._build_stage(
                    stage_key=stage.name,
                    stage_name=stage.value,
                    section_id=(
                        section_row_by_key[stage.name].id if stage.name in section_row_by_key else None
                    ),
                    expected=expected,
                    documents=docs_by_section_key.get(stage.name, []),
                )
            )
        return {"items": items}

    def _build_stage(
        self,
        *,
        stage_key: str,
        stage_name: str,
        section_id: int | None,
        expected: list[dict],
        documents: list[Document],
    ) -> dict:
        live_docs = [d for d in documents if not d.is_archived]
        archived_count = sum(1 for d in documents if d.is_archived)

        # Identity kinds that are actually present (live doc with >=1 file version).
        present_kinds = {d.identity_kind for d in live_docs if d.files_count > 0}

        missing_documents = [doc for doc in expected if doc["kind"] not in present_kinds]
        present_count = len(expected) - len(missing_documents)
        optional_count = sum(1 for doc in expected if not doc["required"])

        version_count = sum(d.files_count for d in live_docs)
        docs_with_files = [d for d in live_docs if d.files_count > 0]
        promoted_docs = [d for d in docs_with_files if d.assumption_promotions]
        needs_update_count = sum(1 for d in docs_with_files if _document_needs_update(d))

        promotion_status = self._rollup_promotion(
            docs_with_files=len(docs_with_files),
            promoted_docs=len(promoted_docs),
            needs_update=needs_update_count,
        )

        return {
            "section_id": section_id,
            "section_key": stage_key,
            "section_name": stage_name,
            "expected": len(expected),
            "present": present_count,
            "missing": len(missing_documents),
            "needs_update": needs_update_count,
            "optional": optional_count,
            "archived": archived_count,
            "version_count": version_count,
            "promotion_status": promotion_status,
            "missing_documents": missing_documents,
        }

    @staticmethod
    def _rollup_promotion(*, docs_with_files: int, promoted_docs: int, needs_update: int) -> str:
        if docs_with_files == 0:
            return PROMOTION_NONE
        if promoted_docs == 0:
            return PROMOTION_NOT_STARTED
        if promoted_docs == docs_with_files and needs_update == 0:
            return PROMOTION_COMPLETE
        return PROMOTION_IN_PROGRESS
