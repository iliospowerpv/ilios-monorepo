"""Sales deals endpoints."""

from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.crud import sales as sales_crud
from app.models.site import Site, SiteAdditionalFieldList, State
from app.models.sales import SalesStateTransition
from app.schema.sales import (
    ConvertToProjectRequest,
    ConvertToProjectResponse,
    DealCreate,
    DealResponse,
    DealUpdate,
    SalesPipelineResponse,
    SalesPipelineSummary,
    SalesStageTransition,
    SalesStateTransitionResponse,
    UserSummary,
    CompanySummary,
)
from app.static.sales import LifecycleState, NextActionStatus, SalesStage

router = APIRouter()


def _deal_to_response(deal) -> DealResponse:
    """Convert a deal to response."""
    return DealResponse(
        id=deal.id,
        name=deal.name,
        developer_name=deal.developer_name,
        sales_stage=SalesStage(deal.sales_stage) if deal.sales_stage else None,
        lifecycle_state=LifecycleState(deal.lifecycle_state) if deal.lifecycle_state else None,
        quoted_by=deal.quoted_by,
        last_action=deal.last_action,
        next_action=deal.next_action,
        next_action_status=NextActionStatus(deal.next_action_status) if deal.next_action_status else None,
        ownership_structure=deal.ownership_structure,
        address=deal.address,
        city=deal.city,
        state=deal.state,
        zip_code=deal.zip_code,
        county=deal.county,
        latitude=deal.latitude,
        longitude=deal.longitude,
        notice_to_proceed_date=deal.notice_to_proceed_date,
        mechanical_completion_date=deal.mechanical_completion_date,
        permission_to_operate_date=deal.permission_to_operate_date,
        substantial_completion_date=deal.substantial_completion_date,
        project_company=deal.project_company,
        mipa_per_watt=deal.mipa_per_watt,
        offtaker_legal_name=deal.offtaker_legal_name,
        utility_zone=deal.utility_zone,
        system_size_ac=deal.system_size_ac,
        system_size_dc=deal.system_size_dc,
        offtaker_name=deal.offtaker_name,
        utility_rate=deal.utility_rate,
        next_action_date=deal.next_action_date,
        sales_notes=deal.sales_notes,
        itc_percent=deal.itc_percent,
        itc_amount=deal.itc_amount,
        fmv=deal.fmv,
        grant_amount=deal.grant_amount,
        tax_equity=deal.tax_equity,
        company=CompanySummary(id=deal.company.id, name=deal.company.name) if deal.company else None,
        assigned_owner=UserSummary(
            id=deal.assigned_owner.id,
            first_name=deal.assigned_owner.first_name,
            last_name=deal.assigned_owner.last_name,
            email=deal.assigned_owner.email,
        ) if deal.assigned_owner else None,
        pipeline_value=deal.pipeline_value,
        probability=deal.probability,
        target_close_date=deal.target_close_date,
        created_at=deal.created_at,
        updated_at=deal.updated_at,
    )


def _deal_to_pipeline_summary(deal) -> SalesPipelineSummary:
    """Convert a deal to pipeline summary."""
    return SalesPipelineSummary(
        id=deal.id,
        name=deal.name,
        company_name=deal.company.name if deal.company else None,
        developer_name=deal.developer_name,
        sales_stage=SalesStage(deal.sales_stage) if deal.sales_stage else None,
        lifecycle_state=LifecycleState(deal.lifecycle_state) if deal.lifecycle_state else None,
        pipeline_value=deal.pipeline_value,
        probability=deal.probability,
        target_close_date=deal.target_close_date,
        next_action=deal.next_action,
        next_action_status=NextActionStatus(deal.next_action_status) if deal.next_action_status else None,
        assigned_owner=UserSummary(
            id=deal.assigned_owner.id,
            first_name=deal.assigned_owner.first_name,
            last_name=deal.assigned_owner.last_name,
            email=deal.assigned_owner.email,
        ) if deal.assigned_owner else None,
        system_size_ac=deal.system_size_ac,
        system_size_dc=deal.system_size_dc,
        mipa_per_watt=deal.mipa_per_watt,
        is_converted=deal.is_converted,
    )


@router.get("/pipeline", response_model=SalesPipelineResponse)
def get_deals_pipeline(
    company_id: Optional[int] = None,
    db: Session = Depends(get_session),
):
    """Get deals grouped by sales stage for kanban view."""
    pipeline = sales_crud.get_deals_pipeline(db, company_id)
    
    return SalesPipelineResponse(
        prospect=[_deal_to_pipeline_summary(d) for d in pipeline["prospect"]],
        nda_signed=[_deal_to_pipeline_summary(d) for d in pipeline["nda_signed"]],
        inputs_received=[_deal_to_pipeline_summary(d) for d in pipeline["inputs_received"]],
        modeling=[_deal_to_pipeline_summary(d) for d in pipeline["modeling"]],
        model_review=[_deal_to_pipeline_summary(d) for d in pipeline["model_review"]],
        model_approved=[_deal_to_pipeline_summary(d) for d in pipeline["model_approved"]],
        quoted=[_deal_to_pipeline_summary(d) for d in pipeline["quoted"]],
        term_sheet_neg=[_deal_to_pipeline_summary(d) for d in pipeline["term_sheet_neg"]],
        term_sheet_signed=[_deal_to_pipeline_summary(d) for d in pipeline["term_sheet_signed"]],
        phase_1_diligence=[_deal_to_pipeline_summary(d) for d in pipeline["phase_1_diligence"]],
        mipa_negotiating=[_deal_to_pipeline_summary(d) for d in pipeline["mipa_negotiating"]],
        mipa_signed=[_deal_to_pipeline_summary(d) for d in pipeline["mipa_signed"]],
        passed=[_deal_to_pipeline_summary(d) for d in pipeline["passed"]],
        dead=[_deal_to_pipeline_summary(d) for d in pipeline["dead"]],
    )


@router.get("/list", response_model=List[DealResponse])
def get_deals_list(
    company_id: Optional[int] = None,
    sales_stage: Optional[SalesStage] = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_session),
):
    """Get list of deals with optional filters."""
    deals = sales_crud.get_deals(db, company_id, sales_stage, skip, limit)
    return [_deal_to_response(d) for d in deals]


@router.post("/deals", response_model=DealResponse, status_code=status.HTTP_201_CREATED)
def create_deal(
    data: DealCreate,
    db: Session = Depends(get_session),
):
    """Create a new deal."""
    user_id = 1
    deal = sales_crud.create_deal(db, data, user_id)
    return _deal_to_response(deal)


@router.get("/deals/{deal_id}", response_model=DealResponse)
def get_deal(
    deal_id: int,
    db: Session = Depends(get_session),
):
    """Get a single deal by ID."""
    deal = sales_crud.get_deal(db, deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return _deal_to_response(deal)


@router.patch("/deals/{deal_id}", response_model=DealResponse)
def update_deal(
    deal_id: int,
    data: DealUpdate,
    db: Session = Depends(get_session),
):
    """Update an existing deal."""
    user_id = 1
    deal = sales_crud.update_deal(db, deal_id, data, user_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return _deal_to_response(deal)


@router.post("/deals/{deal_id}/stage-transition", response_model=DealResponse)
def transition_deal_stage(
    deal_id: int,
    data: SalesStageTransition,
    db: Session = Depends(get_session),
):
    """Transition deal to a new sales stage."""
    user_id = 1
    deal = sales_crud.transition_deal_stage(db, deal_id, data.new_stage, user_id, data.notes)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    return _deal_to_response(deal)


@router.get("/deals/{deal_id}/transitions", response_model=List[SalesStateTransitionResponse])
def get_deal_transitions(
    deal_id: int,
    db: Session = Depends(get_session),
):
    """Get audit log of state transitions for a deal."""
    deal = sales_crud.get_deal(db, deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    transitions = sales_crud.get_deal_transitions(db, deal_id)
    
    return [
        SalesStateTransitionResponse(
            id=t.id,
            site_id=t.site_id or 0,
            transition_type=t.transition_type,
            from_state=t.from_state,
            to_state=t.to_state,
            notes=t.notes,
            changed_by=UserSummary(
                id=t.changed_by.id,
                first_name=t.changed_by.first_name,
                last_name=t.changed_by.last_name,
                email=t.changed_by.email,
            ) if t.changed_by else None,
            created_at=t.created_at,
        )
        for t in transitions
    ]


@router.post("/deals/{deal_id}/convert-to-project", response_model=ConvertToProjectResponse)
def convert_deal_to_project(
    deal_id: int,
    data: ConvertToProjectRequest,
    db: Session = Depends(get_session),
):
    """Convert a deal to a project (Site).
    
    Idempotency: If already converted, returns existing project reference.
    Validation: Requires name and company_id.
    Transaction safety: Uses DB transaction with rollback on failure.
    """
    deal = sales_crud.get_deal(db, deal_id)
    if not deal:
        raise HTTPException(status_code=404, detail="Deal not found")
    
    # IDEMPOTENCY: Return existing project if already converted
    if deal.is_converted and deal.converted_to_project_id:
        return ConvertToProjectResponse(
            deal_id=deal.id,
            project_id=deal.converted_to_project_id,
            message=f"Deal '{deal.name}' was already converted to project {deal.converted_to_project_id}",
        )
    
    # VALIDATION: Check minimum required fields
    if not deal.name:
        raise HTTPException(status_code=400, detail="Deal name is required for conversion")
    if not data.company_id:
        raise HTTPException(status_code=400, detail="Company ID is required for conversion")
    
    # Parse and validate US state (required for compliance)
    state_value = None
    if deal.state:
        try:
            state_value = State(deal.state)
        except ValueError:
            # Try case-insensitive match
            for s in State:
                if s.name.upper() == deal.state.upper() or s.value.upper() == deal.state.upper():
                    state_value = s
                    break
    
    # VALIDATION: State is required for downstream compliance - no fallback to CA
    if not state_value:
        raise HTTPException(
            status_code=400,
            detail=f"Valid US state is required for conversion. '{deal.state or '(empty)'}' is not a recognized state. Please update the deal with a valid 2-letter US state code."
        )
    
    try:
        # Create the canonical Site record
        site = Site()
        site.name = deal.name
        site.address = deal.address or "TBD"
        site.city = deal.city or "TBD"
        site.state = state_value
        site.zip_code = deal.zip_code or "00000"
        site.county = deal.county
        site.lon_lat_url = ""
        site.system_size_ac = float(deal.system_size_ac) if deal.system_size_ac else 0.0
        site.system_size_dc = float(deal.system_size_dc) if deal.system_size_dc else 0.0
        site.company_id = data.company_id
        
        db.add(site)
        db.flush()
        
        # Create additional fields with lifecycle state
        additional_fields = SiteAdditionalFieldList()
        additional_fields.site_id = site.id
        additional_fields.lifecycle_state = LifecycleState.due_diligence.value
        additional_fields.sales_stage = SalesStage.mipa_signed.value
        additional_fields.ownership_structure = deal.ownership_structure
        additional_fields.offtaker_name = deal.offtaker_legal_name or deal.offtaker_name
        db.add(additional_fields)
        
        # Update deal to mark as converted (one-way link)
        deal.is_converted = True
        deal.converted_to_project_id = site.id
        deal.updated_at = datetime.utcnow()
        
        # Create audit log entry
        user_id = 1  # TODO: Get from auth context
        transition = SalesStateTransition(
            deal_id=deal.id,
            site_id=site.id,
            transition_type="converted_to_project",
            from_state=deal.sales_stage,
            to_state="project_created",
            notes=data.additional_notes or "Deal converted to project",
            changed_by_id=user_id,
        )
        db.add(transition)
        
        db.commit()
        
        return ConvertToProjectResponse(
            deal_id=deal.id,
            project_id=site.id,
            message=f"Deal '{deal.name}' successfully converted to project",
        )
    except HTTPException:
        db.rollback()
        raise
    except Exception as e:
        db.rollback()
        error_msg = str(e)
        # Handle unique constraint violation (race condition: two requests tried to convert same deal)
        if "uq_deals_converted_to_project_id" in error_msg or "unique constraint" in error_msg.lower():
            # Re-fetch the deal to check if it was converted by another request
            db.refresh(deal)
            if deal.is_converted and deal.converted_to_project_id:
                return ConvertToProjectResponse(
                    deal_id=deal.id,
                    project_id=deal.converted_to_project_id,
                    message=f"Deal '{deal.name}' was already converted to project {deal.converted_to_project_id} (concurrent request)",
                )
        raise HTTPException(status_code=500, detail=f"Conversion failed: {error_msg}")
