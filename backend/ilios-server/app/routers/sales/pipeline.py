"""Sales pipeline endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.crud import sales as sales_crud
from app.schema.sales import (
    SalesListFilters,
    SalesPipelineResponse,
    SalesPipelineSummary,
    SalesProjectResponse,
    UserSummary,
    CompanySummary,
)
from app.static.sales import LifecycleState, SalesStage

router = APIRouter()


def _project_to_pipeline_summary(project) -> SalesPipelineSummary:
    """Convert a project to pipeline summary."""
    additional = project.additional_fields
    return SalesPipelineSummary(
        id=project.id,
        name=project.name,
        company_name=project.company.name if project.company else "",
        sales_stage=additional.sales_stage if additional else None,
        lifecycle_state=additional.lifecycle_state if additional else None,
        pipeline_value=additional.pipeline_value if additional else None,
        probability=additional.probability if additional else None,
        target_close_date=additional.target_close_date if additional else None,
        next_action_date=additional.next_action_date if additional else None,
        assigned_owner=UserSummary(
            id=additional.assigned_owner.id,
            first_name=additional.assigned_owner.first_name,
            last_name=additional.assigned_owner.last_name,
            email=additional.assigned_owner.email,
        ) if additional and additional.assigned_owner else None,
        system_size_ac=project.system_size_ac,
    )


def _project_to_response(project) -> SalesProjectResponse:
    """Convert a project to full response."""
    additional = project.additional_fields
    return SalesProjectResponse(
        id=project.id,
        name=project.name,
        address=project.address,
        city=project.city,
        state=project.state.value if project.state else "",
        system_size_ac=project.system_size_ac,
        system_size_dc=project.system_size_dc,
        company=CompanySummary(id=project.company.id, name=project.company.name),
        sales_stage=additional.sales_stage if additional else None,
        lifecycle_state=additional.lifecycle_state if additional else None,
        sales_source=additional.sales_source if additional else None,
        target_close_date=additional.target_close_date if additional else None,
        probability=additional.probability if additional else None,
        pipeline_value=additional.pipeline_value if additional else None,
        assigned_owner=UserSummary(
            id=additional.assigned_owner.id,
            first_name=additional.assigned_owner.first_name,
            last_name=additional.assigned_owner.last_name,
            email=additional.assigned_owner.email,
        ) if additional and additional.assigned_owner else None,
        next_action_date=additional.next_action_date if additional else None,
        next_action_notes=additional.next_action_notes if additional else None,
        sales_notes=additional.sales_notes if additional else None,
        handoff_checklist_completed=additional.handoff_checklist_completed if additional else None,
        created_at=project.created_at,
        updated_at=project.updated_at,
    )


@router.get("/pipeline", response_model=SalesPipelineResponse)
def get_sales_pipeline(
    company_id: Optional[int] = Query(None, description="Filter by company"),
    db: Session = Depends(get_session),
):
    """Get sales pipeline grouped by stage (for kanban view)."""
    pipeline = sales_crud.get_sales_pipeline(db, company_id=company_id)
    
    return SalesPipelineResponse(
        discovery=[_project_to_pipeline_summary(p) for p in pipeline["discovery"]],
        qualified=[_project_to_pipeline_summary(p) for p in pipeline["qualified"]],
        loi_term_sheet=[_project_to_pipeline_summary(p) for p in pipeline["loi_term_sheet"]],
        under_contract=[_project_to_pipeline_summary(p) for p in pipeline["under_contract"]],
        handoff_to_diligence=[_project_to_pipeline_summary(p) for p in pipeline["handoff_to_diligence"]],
    )


@router.get("/list", response_model=List[SalesProjectResponse])
def get_sales_list(
    company_id: Optional[int] = Query(None),
    sales_stage: Optional[SalesStage] = Query(None),
    lifecycle_state: Optional[LifecycleState] = Query(None),
    assigned_owner_id: Optional[int] = Query(None),
    needs_action: Optional[bool] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_session),
):
    """Get list of sales projects with filters."""
    filters = SalesListFilters(
        company_id=company_id,
        sales_stage=sales_stage,
        lifecycle_state=lifecycle_state,
        assigned_owner_id=assigned_owner_id,
        needs_action=needs_action,
        skip=skip,
        limit=limit,
    )
    
    projects = sales_crud.get_sales_projects(db, filters=filters)
    return [_project_to_response(p) for p in projects]
