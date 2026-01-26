"""Sales project detail endpoints."""

from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.crud import sales as sales_crud
from app.schema.sales import (
    DataRoomPackageResponse,
    HandoffChecklistResponse,
    HandoffChecklistItem,
    LifecycleStateTransition,
    SalesProjectResponse,
    SalesProjectUpdate,
    SalesStageTransition,
    SalesStateTransitionResponse,
    UserSummary,
    CompanySummary,
)
from app.static.sales import LifecycleState, SalesStage

router = APIRouter()


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


@router.get("/projects/{site_id}", response_model=SalesProjectResponse)
def get_sales_project(
    site_id: int,
    db: Session = Depends(get_session),
):
    """Get a single project with sales data."""
    project = sales_crud.get_project_with_sales(db, site_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return _project_to_response(project)


@router.patch("/projects/{site_id}", response_model=SalesProjectResponse)
def update_sales_project(
    site_id: int,
    data: SalesProjectUpdate,
    db: Session = Depends(get_session),
):
    """Update sales fields on a project."""
    project = sales_crud.get_project_with_sales(db, site_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    sales_crud.update_sales_fields(db, site_id, data)
    
    project = sales_crud.get_project_with_sales(db, site_id)
    return _project_to_response(project)


@router.post("/projects/{site_id}/stage-transition", response_model=SalesProjectResponse)
def transition_sales_stage(
    site_id: int,
    data: SalesStageTransition,
    db: Session = Depends(get_session),
):
    """Transition sales stage with audit logging."""
    project = sales_crud.get_project_with_sales(db, site_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    user_id = 1
    
    sales_crud.transition_sales_stage(db, site_id, data.new_stage, user_id, data.notes)
    
    if data.new_stage == SalesStage.handoff_to_diligence:
        checklist = sales_crud.get_handoff_checklist(db, site_id)
        if not checklist["all_complete"]:
            missing = [item["label"] for item in checklist["items"] if not item["completed"]]
            raise HTTPException(
                status_code=400,
                detail=f"Handoff checklist incomplete. Missing: {', '.join(missing)}"
            )
        
        sales_crud.transition_lifecycle_state(
            db, site_id, LifecycleState.due_diligence, user_id, 
            "Automatic transition from Sales handoff"
        )
    
    project = sales_crud.get_project_with_sales(db, site_id)
    return _project_to_response(project)


@router.post("/projects/{site_id}/lifecycle-transition", response_model=SalesProjectResponse)
def transition_lifecycle_state(
    site_id: int,
    data: LifecycleStateTransition,
    db: Session = Depends(get_session),
):
    """Transition lifecycle state with audit logging."""
    project = sales_crud.get_project_with_sales(db, site_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    user_id = 1
    
    sales_crud.transition_lifecycle_state(db, site_id, data.new_state, user_id, data.notes)
    
    project = sales_crud.get_project_with_sales(db, site_id)
    return _project_to_response(project)


@router.get("/projects/{site_id}/handoff-checklist", response_model=HandoffChecklistResponse)
def get_handoff_checklist(
    site_id: int,
    db: Session = Depends(get_session),
):
    """Get handoff checklist status for a project."""
    project = sales_crud.get_project_with_sales(db, site_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    checklist = sales_crud.get_handoff_checklist(db, site_id)
    
    return HandoffChecklistResponse(
        site_id=site_id,
        all_complete=checklist["all_complete"],
        items=[HandoffChecklistItem(**item) for item in checklist["items"]],
    )


@router.get("/projects/{site_id}/transitions", response_model=List[SalesStateTransitionResponse])
def get_state_transitions(
    site_id: int,
    db: Session = Depends(get_session),
):
    """Get audit log of state transitions for a project."""
    project = sales_crud.get_project_with_sales(db, site_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    transitions = sales_crud.get_state_transitions(db, site_id)
    
    return [
        SalesStateTransitionResponse(
            id=t.id,
            site_id=t.site_id,
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


@router.get("/projects/{site_id}/data-room-package", response_model=DataRoomPackageResponse)
def get_data_room_package(
    site_id: int,
    db: Session = Depends(get_session),
):
    """Generate data room package (stub for future expansion)."""
    project = sales_crud.get_project_with_sales(db, site_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    transitions = sales_crud.get_state_transitions(db, site_id)
    additional = project.additional_fields
    
    return DataRoomPackageResponse(
        site_id=site_id,
        site_name=project.name,
        company_name=project.company.name if project.company else "",
        sales_history=[
            SalesStateTransitionResponse(
                id=t.id,
                site_id=t.site_id,
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
        ],
        current_stage=additional.sales_stage if additional else None,
        lifecycle_state=additional.lifecycle_state if additional else None,
        generated_at=datetime.utcnow(),
    )
