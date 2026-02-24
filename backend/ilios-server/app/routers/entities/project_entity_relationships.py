"""Entity Relationship endpoints - project-level entity role assignments."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.project_entity import (
    create_entity_relationship,
    delete_entity_relationship,
    get_entity,
    get_entity_relationship,
    list_entity_relationships,
    update_entity_relationship,
)
from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.authorization.project_access import get_authorized_site
from app.models.site import Site
from app.schema.project_entity import (
    EntityRelationshipCreate,
    EntityRelationshipListResponse,
    EntityRelationshipResponse,
    EntityRelationshipUpdate,
)
from app.schema.user import CurrentUserSchema
from app.static.entities import EntityRelationshipRole

router = APIRouter(prefix="/projects/{site_id}/entity-relationships")
logger = logging.getLogger(__name__)


def _relationship_to_response(rel) -> EntityRelationshipResponse:
    entity_name = rel.entity.name if rel.entity else None
    entity_type = rel.entity.entity_type if rel.entity else None
    contact_name = None
    if rel.contact:
        contact_name = f"{rel.contact.first_name} {rel.contact.last_name}".strip()

    return EntityRelationshipResponse(
        id=rel.id,
        site_id=rel.site_id,
        entity_id=rel.entity_id,
        role=rel.role,
        contact_id=rel.contact_id,
        effective_date=rel.effective_date,
        termination_date=rel.termination_date,
        notes=rel.notes,
        entity_name=entity_name,
        entity_type=entity_type,
        contact_name=contact_name,
        created_at=rel.created_at,
        updated_at=rel.updated_at,
    )


@router.get("/", response_model=EntityRelationshipListResponse)
async def list_relationships_endpoint(
    site_id: int,
    role: Optional[EntityRelationshipRole] = Query(None),
    current_user: CurrentUserSchema = Depends(get_current_user),
    db_session: Session = Depends(get_session),
):
    site = db_session.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Project {site_id} not found")

    items = list_entity_relationships(db_session, site_id=site_id, role=role)
    return EntityRelationshipListResponse(
        items=[_relationship_to_response(r) for r in items],
        total=len(items),
    )


@router.post("/", response_model=EntityRelationshipResponse, status_code=status.HTTP_201_CREATED)
async def create_relationship_endpoint(
    site_id: int,
    body: EntityRelationshipCreate,
    current_user: CurrentUserSchema = Depends(get_current_user),
    db_session: Session = Depends(get_session),
):
    site = db_session.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Project {site_id} not found")

    entity = get_entity(db_session, body.entity_id)
    if not entity:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Entity {body.entity_id} not found")

    data = body.model_dump()
    data["site_id"] = site_id
    data["role"] = data["role"].value if hasattr(data["role"], "value") else data["role"]

    try:
        rel = create_entity_relationship(db_session, data)
    except Exception as exc:
        if "uq_entity_relationships_site_role_entity" in str(exc):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "This entity is already assigned to this role on this project",
            )
        raise

    db_session.refresh(rel)
    rel = get_entity_relationship(db_session, rel.id)
    return _relationship_to_response(rel)


@router.put("/{relationship_id}", response_model=EntityRelationshipResponse)
async def update_relationship_endpoint(
    site_id: int,
    relationship_id: int,
    body: EntityRelationshipUpdate,
    current_user: CurrentUserSchema = Depends(get_current_user),
    db_session: Session = Depends(get_session),
):
    rel = get_entity_relationship(db_session, relationship_id)
    if not rel or rel.site_id != site_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Relationship not found")

    updates = body.model_dump(exclude_unset=True)
    if "role" in updates and updates["role"] is not None:
        updates["role"] = updates["role"].value if hasattr(updates["role"], "value") else updates["role"]

    rel = update_entity_relationship(db_session, relationship_id, updates)
    rel = get_entity_relationship(db_session, rel.id)
    return _relationship_to_response(rel)


@router.delete("/{relationship_id}", status_code=status.HTTP_200_OK)
async def delete_relationship_endpoint(
    site_id: int,
    relationship_id: int,
    current_user: CurrentUserSchema = Depends(get_current_user),
    db_session: Session = Depends(get_session),
):
    rel = get_entity_relationship(db_session, relationship_id)
    if not rel or rel.site_id != site_id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Relationship not found")

    delete_entity_relationship(db_session, relationship_id)
    return {"message": "Relationship removed"}
