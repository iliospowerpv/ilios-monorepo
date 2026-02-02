"""Lifecycle transition endpoints with RBAC, audit, and auto-tasks."""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.models.site import Site, SiteAdditionalFieldList
from app.models.sales import SalesStateTransition
from app.models.lifecycle import LifecycleTaskTemplate
from app.models.task import Task
from app.models.board import Board
from app.models.user import User, UserCompanyAccess
from app.static.sales import LifecycleState

router = APIRouter()


class LifecycleTransitionRequest(BaseModel):
    to_state: str
    reason: Optional[str] = None


class LifecycleTransitionResponse(BaseModel):
    project_id: int
    from_state: Optional[str]
    to_state: str
    tasks_created: int
    message: str


class SignedAgreementWaiveRequest(BaseModel):
    reason: str


class SignedAgreementResponse(BaseModel):
    project_id: int
    status: str
    message: str


LIFECYCLE_ORDER = [
    LifecycleState.pre_diligence,
    LifecycleState.due_diligence,
    LifecycleState.implementation,
    LifecycleState.placed_in_service,
    LifecycleState.operations,
]

AGREEMENT_REQUIRED_STATES = [
    LifecycleState.implementation,
    LifecycleState.placed_in_service,
    LifecycleState.operations,
]


def _is_admin_or_superuser(db: Session, user_id: int, company_id: int) -> bool:
    """Check if user is company admin or superuser."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return False
    if user.is_system_user:
        return True
    
    access = db.query(UserCompanyAccess).filter(
        UserCompanyAccess.user_id == user_id,
        UserCompanyAccess.company_id == company_id,
        UserCompanyAccess.role == "company_admin",
        UserCompanyAccess.status == "active"
    ).first()
    return access is not None


def _create_lifecycle_tasks(db: Session, site: Site, to_state: str, user_id: int) -> int:
    """Create tasks from lifecycle templates for the given state."""
    templates = db.query(LifecycleTaskTemplate).filter(
        LifecycleTaskTemplate.to_state == to_state,
        LifecycleTaskTemplate.is_active == True
    ).all()
    
    tasks_created = 0
    for template in templates:
        task = Task()
        task.title = template.title
        task.description = template.description
        task.due_date = datetime.utcnow() + timedelta(days=template.due_offset_days)
        task.created_by_id = user_id
        
        if site.documents_board:
            task.board_id = site.documents_board.id
        
        db.add(task)
        tasks_created += 1
    
    return tasks_created


@router.post("/projects/{project_id}/lifecycle", response_model=LifecycleTransitionResponse)
def transition_lifecycle(
    project_id: int,
    data: LifecycleTransitionRequest,
    db: Session = Depends(get_session),
):
    """Transition project lifecycle state.
    
    Requires Company Admin or Superuser role.
    Cannot advance past Diligence without signed agreement.
    Auto-creates tasks from templates.
    All transitions are audited.
    """
    site = db.query(Site).filter(Site.id == project_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Project not found")
    
    try:
        to_state = LifecycleState(data.to_state)
    except ValueError:
        valid_states = [s.value for s in LifecycleState]
        raise HTTPException(
            status_code=400,
            detail=f"Invalid lifecycle state. Valid states: {valid_states}"
        )
    
    user_id = 1  # TODO: Get from auth context
    if not _is_admin_or_superuser(db, user_id, site.company_id):
        raise HTTPException(
            status_code=403,
            detail="Only Company Admin or Superuser can transition lifecycle state"
        )
    
    if to_state in AGREEMENT_REQUIRED_STATES:
        if site.signed_agreement_status == "missing":
            raise HTTPException(
                status_code=400,
                detail="Cannot advance past Diligence without signed agreement. Upload agreement or request waiver."
            )
    
    additional_fields = db.query(SiteAdditionalFieldList).filter(
        SiteAdditionalFieldList.site_id == project_id
    ).first()
    
    if not additional_fields:
        additional_fields = SiteAdditionalFieldList(site_id=project_id)
        db.add(additional_fields)
    
    old_state = additional_fields.lifecycle_state
    additional_fields.lifecycle_state = to_state.value
    
    transition = SalesStateTransition(
        site_id=project_id,
        transition_type="lifecycle",
        from_state=old_state if old_state else None,
        to_state=to_state.value,
        notes=data.reason or f"Lifecycle transitioned to {to_state.value}",
        changed_by_id=user_id,
        reason=data.reason,
        actor_role="system_user" if db.query(User).get(user_id).is_system_user else "company_admin"
    )
    db.add(transition)
    
    tasks_created = _create_lifecycle_tasks(db, site, to_state.value, user_id)
    
    db.commit()
    
    return LifecycleTransitionResponse(
        project_id=project_id,
        from_state=old_state,
        to_state=to_state.value,
        tasks_created=tasks_created,
        message=f"Lifecycle transitioned to {to_state.value}. {tasks_created} tasks created."
    )


@router.post("/projects/{project_id}/signed-agreement/waive", response_model=SignedAgreementResponse)
def waive_signed_agreement(
    project_id: int,
    data: SignedAgreementWaiveRequest,
    db: Session = Depends(get_session),
):
    """Waive the signed agreement requirement.
    
    Requires Company Admin or Superuser role.
    """
    site = db.query(Site).filter(Site.id == project_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Project not found")
    
    user_id = 1  # TODO: Get from auth context
    if not _is_admin_or_superuser(db, user_id, site.company_id):
        raise HTTPException(
            status_code=403,
            detail="Only Company Admin or Superuser can waive signed agreement"
        )
    
    site.signed_agreement_status = "waived"
    site.waived_by_id = user_id
    site.waived_at = datetime.utcnow()
    site.waiver_reason = data.reason
    
    transition = SalesStateTransition(
        site_id=project_id,
        transition_type="signed_agreement_waived",
        from_state="missing",
        to_state="waived",
        notes=f"Signed agreement waived: {data.reason}",
        changed_by_id=user_id,
        reason=data.reason,
    )
    db.add(transition)
    
    db.commit()
    
    return SignedAgreementResponse(
        project_id=project_id,
        status="waived",
        message="Signed agreement requirement has been waived"
    )


@router.post("/projects/{project_id}/signed-agreement/upload", response_model=SignedAgreementResponse)
def mark_agreement_uploaded(
    project_id: int,
    document_id: int,
    db: Session = Depends(get_session),
):
    """Mark signed agreement as uploaded by linking to document."""
    site = db.query(Site).filter(Site.id == project_id).first()
    if not site:
        raise HTTPException(status_code=404, detail="Project not found")
    
    site.signed_agreement_status = "uploaded"
    site.signed_agreement_document_id = document_id
    
    user_id = 1  # TODO: Get from auth context
    transition = SalesStateTransition(
        site_id=project_id,
        transition_type="signed_agreement_uploaded",
        from_state=site.signed_agreement_status or "missing",
        to_state="uploaded",
        notes=f"Signed agreement uploaded: document {document_id}",
        changed_by_id=user_id,
    )
    db.add(transition)
    
    db.commit()
    
    return SignedAgreementResponse(
        project_id=project_id,
        status="uploaded",
        message="Signed agreement has been marked as uploaded"
    )
