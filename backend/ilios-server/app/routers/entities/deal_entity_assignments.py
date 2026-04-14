"""Deal Entity Assignment endpoints - deal-level entity role references."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.project_entity import (
    create_deal_entity_assignment,
    delete_deal_entity_assignment,
    get_deal_entity_assignment,
    get_entity,
    list_deal_entity_assignments,
    update_deal_entity_assignment,
)
from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.models.sales import Deal
from app.schema.project_entity import (
    DealEntityAssignmentCreate,
    DealEntityAssignmentListResponse,
    DealEntityAssignmentResponse,
    DealEntityAssignmentUpdate,
)
from app.schema.user import CurrentUserSchema
from app.static.entities import DealEntityRole

router = APIRouter(prefix="/deals/{deal_id}/entity-assignments")
logger = logging.getLogger(__name__)


def _get_deal_or_404(db_session: Session, deal_id: int) -> Deal:
    deal = db_session.query(Deal).filter(Deal.id == deal_id).first()
    if not deal:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Deal {deal_id} not found")
    return deal


def _assignment_to_response(a) -> DealEntityAssignmentResponse:
    entity_name = a.entity.name if a.entity else None
    entity_type = a.entity.entity_type if a.entity else None
    contact_name = None
    if a.contact:
        contact_name = f"{a.contact.first_name} {a.contact.last_name}".strip()

    return DealEntityAssignmentResponse(
        id=a.id,
        deal_id=a.deal_id,
        entity_id=a.entity_id,
        role=a.role,
        contact_id=a.contact_id,
        entity_name=entity_name,
        entity_type=entity_type,
        contact_name=contact_name,
        created_at=a.created_at,
        updated_at=a.updated_at,
    )


@router.get("/", response_model=DealEntityAssignmentListResponse)
async def list_assignments_endpoint(
    deal_id: int,
    role: Optional[DealEntityRole] = Query(None),
    current_user: CurrentUserSchema = Depends(get_current_user),
    db_session: Session = Depends(get_session),
):
    deal = _get_deal_or_404(db_session, deal_id)

    items = list_deal_entity_assignments(db_session, deal_id=deal_id, role=role)
    return DealEntityAssignmentListResponse(
        items=[_assignment_to_response(a) for a in items],
        total=len(items),
    )


@router.post("/", response_model=DealEntityAssignmentResponse, status_code=status.HTTP_201_CREATED)
async def create_assignment_endpoint(
    deal_id: int,
    body: DealEntityAssignmentCreate,
    current_user: CurrentUserSchema = Depends(get_current_user),
    db_session: Session = Depends(get_session),
):
    deal = _get_deal_or_404(db_session, deal_id)

    entity = get_entity(db_session, body.entity_id)
    if not entity:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Entity {body.entity_id} not found")

    data = body.model_dump()
    data["deal_id"] = deal_id
    data["role"] = data["role"].value if hasattr(data["role"], "value") else data["role"]

    try:
        assignment = create_deal_entity_assignment(db_session, data)
    except Exception as exc:
        if "uq_deal_entity_assignments_deal_role" in str(exc):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "An entity is already assigned to this role on this deal",
            )
        raise

    db_session.refresh(assignment)
    assignment = get_deal_entity_assignment(db_session, assignment.id)
    return _assignment_to_response(assignment)


@router.put("/{assignment_id}", response_model=DealEntityAssignmentResponse)
async def update_assignment_endpoint(
    deal_id: int,
    assignment_id: int,
    body: DealEntityAssignmentUpdate,
    current_user: CurrentUserSchema = Depends(get_current_user),
    db_session: Session = Depends(get_session),
):
    deal = _get_deal_or_404(db_session, deal_id)

    assignment = get_deal_entity_assignment(db_session, assignment_id)
    if not assignment or assignment.deal_id != deal_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assignment not found")

    updates = body.model_dump(exclude_unset=True)
    if "role" in updates and updates["role"] is not None:
        updates["role"] = updates["role"].value if hasattr(updates["role"], "value") else updates["role"]

    assignment = update_deal_entity_assignment(db_session, assignment_id, updates)
    assignment = get_deal_entity_assignment(db_session, assignment.id)
    return _assignment_to_response(assignment)


@router.delete("/{assignment_id}", status_code=status.HTTP_200_OK)
async def delete_assignment_endpoint(
    deal_id: int,
    assignment_id: int,
    current_user: CurrentUserSchema = Depends(get_current_user),
    db_session: Session = Depends(get_session),
):
    deal = _get_deal_or_404(db_session, deal_id)

    assignment = get_deal_entity_assignment(db_session, assignment_id)
    if not assignment or assignment.deal_id != deal_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Assignment not found")

    delete_deal_entity_assignment(db_session, assignment_id)
    return {"message": "Assignment removed"}
