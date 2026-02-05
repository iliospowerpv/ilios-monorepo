"""Project-level due diligence summary stats endpoint"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy import func, distinct, exists, and_, select
from sqlalchemy.orm import Session, aliased

from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.authorization.project_access import get_authorized_site
from app.helpers.permission_guards import require_module_permission
from app.models.document import Document, DocumentKey
from app.models.file import File, FileParsingStatuses
from app.models.project_facts import ProjectFact, FactStatus
from app.models.site import Site
from app.schema.summary_stats import ProjectSummaryStats, CoTerminusStats
from app.schema.user import CurrentUserSchema
from app.static import HTTP_403_RESPONSE, HTTP_404_RESPONSE

logger = logging.getLogger(__name__)
summary_stats_router = APIRouter()


def is_meaningful_value(value) -> bool:
    """Check if a value is meaningful (not null, empty, or N/A)."""
    if value is None:
        return False
    if isinstance(value, dict):
        actual_value = value.get("v")
        if actual_value is None:
            return False
        if isinstance(actual_value, str):
            stripped = actual_value.strip()
            if not stripped or stripped.lower() == "n/a":
                return False
        return True
    if isinstance(value, str):
        stripped = value.strip()
        return bool(stripped) and stripped.lower() != "n/a"
    return True


def map_parsing_status_to_coterminus_status(status: FileParsingStatuses, is_stuck: bool = False) -> str:
    """Map FileParsingStatuses to co-terminus status string."""
    if status == FileParsingStatuses.processing:
        return "stuck" if is_stuck else "running"
    if status == FileParsingStatuses.completed:
        return "completed"
    if status in (FileParsingStatuses.processing_failed, FileParsingStatuses.processing_start_failed):
        return "failed"
    if status == FileParsingStatuses.processing_timeout:
        return "stuck"
    return "not_run"


@summary_stats_router.get(
    "/summary-stats",
    response_model=ProjectSummaryStats,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Get project-level due diligence summary stats including promoted terms and co-terminus status",
)
async def get_summary_stats(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    site: Site = Depends(get_authorized_site),
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=site.company_id,
        project_id=site.id,
        db_session=db_session,
        module_key="Diligence",
        action="view",
    )

    documents_total = db_session.query(func.count(Document.id)).filter(
        Document.site_id == site.id,
        Document.is_archived == False
    ).scalar() or 0

    superseding_fact = aliased(ProjectFact)
    superseded_subquery = select(superseding_fact.id).where(
        superseding_fact.supersedes_fact_id == ProjectFact.id
    ).exists()
    
    current_active_facts = db_session.query(ProjectFact).filter(
        ProjectFact.site_id == site.id,
        ProjectFact.status == FactStatus.active.value,
        ~superseded_subquery
    ).all()

    meaningful_facts = [f for f in current_active_facts if is_meaningful_value(f.value)]
    promoted_terms_total = len(meaningful_facts)

    document_ids = set()
    file_based_fact_ids = []
    dockey_based_fact_ids = []
    
    for fact in meaningful_facts:
        if fact.source_file_id:
            file_based_fact_ids.append(fact.id)
        if fact.source_document_key_id:
            dockey_based_fact_ids.append(fact.id)
    
    if file_based_fact_ids:
        file_doc_ids = db_session.query(distinct(File.document_id)).join(
            ProjectFact, ProjectFact.source_file_id == File.id
        ).filter(
            ProjectFact.id.in_(file_based_fact_ids),
            File.document_id.isnot(None)
        ).all()
        document_ids.update(doc_id[0] for doc_id in file_doc_ids if doc_id[0])
    
    if dockey_based_fact_ids:
        dockey_doc_ids = db_session.query(distinct(DocumentKey.document_id)).join(
            ProjectFact, ProjectFact.source_document_key_id == DocumentKey.id
        ).filter(
            ProjectFact.id.in_(dockey_based_fact_ids),
            DocumentKey.document_id.isnot(None)
        ).all()
        document_ids.update(doc_id[0] for doc_id in dockey_doc_ids if doc_id[0])
    
    documents_with_promoted_terms = len(document_ids)

    coterminus_status = "not_run"
    coterminus_mismatches = None
    coterminus_last_run = None

    if site.co_terminus_check:
        check = site.co_terminus_check
        is_stuck = False

        if check.status == FileParsingStatuses.processing and check.start_time:
            from app.helpers.common import get_utc_now
            from app.settings import settings
            duration = get_utc_now() - check.start_time
            is_stuck = duration.seconds > settings.co_terminus_stuck_threshold

        coterminus_status = map_parsing_status_to_coterminus_status(check.status, is_stuck)
        coterminus_last_run = check.end_time

        if check.status == FileParsingStatuses.completed and check.result:
            mismatch_count = 0
            for item in check.result:
                item_status = item.get("status", "")
                if item_status in ("Not Equal", "Ambiguous"):
                    mismatch_count += 1
            coterminus_mismatches = mismatch_count

    return ProjectSummaryStats(
        documents_total=documents_total,
        documents_with_promoted_terms=documents_with_promoted_terms,
        promoted_terms_total=promoted_terms_total,
        coterminus=CoTerminusStats(
            status=coterminus_status,
            mismatches=coterminus_mismatches,
            last_run_at=coterminus_last_run
        )
    )
