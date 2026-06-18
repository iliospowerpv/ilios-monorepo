"""Project Assumptions Router - Lender-quality facts management and promotion workflow

This router provides endpoints for:
- Querying active project facts (downstream module consumption)
- Computing promotion diff preview
- Promoting document versions to current assumptions (role-gated)
- Viewing promotion audit trail
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.authorization.project_access import get_authorized_site
from app.helpers.permission_guards import require_module_permission
from app.crud.file import FileCRUD
from app.crud.assumption_promotion import AssumptionPromotionCRUD
from app.models.site import Site
from app.schema.user import CurrentUserSchema
from app.services.project_facts_service import ProjectFactsService
from app.services.promotion_service import (
    PromotionService,
    PromotionError,
    PROMOTION_SOURCE_STALE_CODE,
)
from app.static import HTTP_403_RESPONSE, HTTP_404_RESPONSE

logger = logging.getLogger(__name__)
assumptions_router = APIRouter()

# PromotionError codes that map to HTTP 409 (fail-closed freshness conflict)
# with a structured body. ``STALE_CANDIDATE_FACT`` is a forward-compatible alias.
STALE_PROMOTION_ERROR_CODES = {PROMOTION_SOURCE_STALE_CODE, "STALE_CANDIDATE_FACT"}


class PromotionRequest(BaseModel):
    document_id: int = Field(..., examples=[1])
    file_id: int = Field(..., examples=[42])
    notes: str | None = Field(default=None, max_length=2000)


class PromotionDiffRequest(BaseModel):
    file_id: int = Field(..., examples=[42])


class FactSchema(BaseModel):
    id: int
    field_name: str | None
    field_display_name: str | None
    value: str | None
    status: str
    source_file_id: int | None
    promoted_at: str | None


class ActiveFactsResponse(BaseModel):
    site_id: int
    facts: list[FactSchema]
    total: int


class DiffChangeSchema(BaseModel):
    type: str
    field_name: str
    field_id: int
    current_value: str | None
    new_value: str | None
    current_source_file_id: int | None
    new_source_file_id: int | None


class DiffSummarySchema(BaseModel):
    added: int
    changed: int
    removed: int


class DiffResponse(BaseModel):
    has_changes: bool
    changes: list[DiffChangeSchema]
    summary: DiffSummarySchema


class PromotionResponse(BaseModel):
    promoted: bool
    file_id: int
    document_id: int
    promotion_id: int
    facts_promoted: int
    diff: DiffResponse


class PromotionHistoryItem(BaseModel):
    id: int
    document_id: int
    file_id: int
    promoted_by_id: int
    promoted_at: str
    notes: str | None
    changes_summary: DiffSummarySchema | None


class PromotionHistoryResponse(BaseModel):
    site_id: int
    promotions: list[PromotionHistoryItem]


@assumptions_router.get(
    "/facts",
    response_model=ActiveFactsResponse,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Get active project facts (current assumptions) for a site. Used by downstream modules.",
)
async def get_active_facts(
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
    facts_service = ProjectFactsService(db_session)
    facts = facts_service.get_active_facts(site.id)
    return {
        "site_id": site.id,
        "facts": facts,
        "total": len(facts),
    }


@assumptions_router.get(
    "/facts/candidates/{file_id}",
    response_model=ActiveFactsResponse,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Get candidate facts for a specific file version (pending promotion).",
)
async def get_candidate_facts(
    file_id: int,
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
    file = FileCRUD(db_session).get_by_id(file_id)
    if not file or file.document.site_id != site.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found or does not belong to this project")

    facts_service = ProjectFactsService(db_session)
    facts = facts_service.get_candidate_facts_for_file(file_id)
    return {
        "site_id": site.id,
        "facts": facts,
        "total": len(facts),
    }


@assumptions_router.post(
    "/promotion/diff",
    response_model=DiffResponse,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Compute promotion diff - shows what would change if this version is promoted.",
)
async def compute_promotion_diff(
    request: PromotionDiffRequest,
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
    file = FileCRUD(db_session).get_by_id(request.file_id)
    if not file or file.document.site_id != site.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "File not found or does not belong to this project")

    promotion_service = PromotionService(db_session)
    diff = promotion_service.compute_promotion_diff(site.id, request.file_id)
    return diff


@assumptions_router.post(
    "/promote",
    response_model=PromotionResponse,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Promote a document version to current assumptions. Role-gated: Company Admin or System User only.",
)
async def promote_version(
    request: PromotionRequest,
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
        action="edit",
    )

    try:
        promotion_service = PromotionService(db_session)
        result = promotion_service.promote_version(
            site_id=site.id,
            document_id=request.document_id,
            file_id=request.file_id,
            promoted_by_id=current_user.id,
            notes=request.notes,
        )
        return result
    except PromotionError as e:
        # Freshness-guard failures are a fail-closed conflict, not a bad request:
        # surface a machine-readable 409 body (error_code + per-field stale list)
        # so the client can route the user back to the Data Room to re-review.
        # Every other PromotionError keeps the legacy 400 string contract.
        #
        # NOTE: the app's ``http_exception_handler`` collapses an HTTPException
        # ``detail`` to ``str(detail)``, which would destroy a structured dict.
        # Return a ``JSONResponse`` directly (mirroring the bulk-accept
        # guardrail) so the machine-readable body reaches the client intact.
        if e.error_code in STALE_PROMOTION_ERROR_CODES:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "error_code": e.error_code,
                    "message": e.message,
                    **e.details,
                },
            )
        raise HTTPException(status.HTTP_400_BAD_REQUEST, detail=e.message)


@assumptions_router.get(
    "/promotions",
    response_model=PromotionHistoryResponse,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description="Get promotion audit trail for a site.",
)
async def get_promotion_history(
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
    promotions_crud = AssumptionPromotionCRUD(db_session)
    promotions = promotions_crud.get_promotions_for_site(site.id)

    history = []
    for p in promotions:
        summary = None
        if p.diff_json and "summary" in p.diff_json:
            summary = p.diff_json["summary"]
        history.append({
            "id": p.id,
            "document_id": p.document_id,
            "file_id": p.file_id,
            "promoted_by_id": p.promoted_by_id,
            "promoted_at": p.promoted_at.isoformat() if p.promoted_at else None,
            "notes": p.notes,
            "changes_summary": summary,
        })

    return {
        "site_id": site.id,
        "promotions": history,
    }
