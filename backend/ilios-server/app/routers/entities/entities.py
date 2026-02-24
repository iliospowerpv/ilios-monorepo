"""Entity Directory CRUD endpoints - portfolio-scoped entity management."""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.project_entity import (
    count_entities,
    create_entity,
    get_entity,
    list_entities,
    list_entity_assignments_by_entity,
    soft_delete_entity,
    update_entity,
)
from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.models.company import Company
from app.models.user import UserPortfolioAccess
from app.schema.project_entity import (
    EntityAssignmentSummary,
    EntityAssignmentsSummaryResponse,
    ProjectEntityCreate,
    ProjectEntityListResponse,
    ProjectEntityResponse,
    ProjectEntityUpdate,
)
from app.schema.user import CurrentUserSchema
from app.static.entities import EntityType

router = APIRouter(prefix="/entities")
logger = logging.getLogger(__name__)


def _check_portfolio_access(
    db_session: Session,
    current_user: CurrentUserSchema,
    portfolio_id: int,
) -> None:
    if current_user.is_system_user:
        return

    portfolio = db_session.query(Company).filter(Company.id == portfolio_id).first()
    if not portfolio:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Portfolio {portfolio_id} not found")

    access = db_session.query(UserPortfolioAccess).filter(
        UserPortfolioAccess.user_id == current_user.id,
        UserPortfolioAccess.portfolio_hub_company_id == portfolio_id,
        UserPortfolioAccess.status == "active",
    ).first()
    if not access:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No access to this portfolio")


@router.get("/", response_model=ProjectEntityListResponse)
async def list_entities_endpoint(
    portfolio_id: int = Query(...),
    search: Optional[str] = Query(None),
    entity_type: Optional[EntityType] = Query(None),
    include_inactive: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    current_user: CurrentUserSchema = Depends(get_current_user),
    db_session: Session = Depends(get_session),
):
    _check_portfolio_access(db_session, current_user, portfolio_id)

    skip = (page - 1) * page_size
    items = list_entities(
        db_session,
        portfolio_id=portfolio_id,
        search=search,
        entity_type=entity_type,
        include_inactive=include_inactive,
        skip=skip,
        limit=page_size,
    )
    total = count_entities(
        db_session,
        portfolio_id=portfolio_id,
        search=search,
        entity_type=entity_type,
        include_inactive=include_inactive,
    )

    return ProjectEntityListResponse(
        items=[_entity_to_response(e) for e in items],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(skip + page_size) < total,
    )


@router.post("/", response_model=ProjectEntityResponse, status_code=status.HTTP_201_CREATED)
async def create_entity_endpoint(
    body: ProjectEntityCreate,
    current_user: CurrentUserSchema = Depends(get_current_user),
    db_session: Session = Depends(get_session),
):
    _check_portfolio_access(db_session, current_user, body.portfolio_id)

    data = body.model_dump()
    data["entity_type"] = data["entity_type"].value if hasattr(data["entity_type"], "value") else data["entity_type"]
    try:
        entity = create_entity(db_session, data)
    except Exception as exc:
        if "uq_project_entities_portfolio_name" in str(exc):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                f"An entity named '{body.name}' already exists in this portfolio",
            )
        raise

    db_session.refresh(entity)
    return _entity_to_response(entity)


@router.get("/{entity_id}", response_model=ProjectEntityResponse)
async def get_entity_endpoint(
    entity_id: int,
    current_user: CurrentUserSchema = Depends(get_current_user),
    db_session: Session = Depends(get_session),
):
    entity = get_entity(db_session, entity_id)
    if not entity:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Entity {entity_id} not found")

    _check_portfolio_access(db_session, current_user, entity.portfolio_id)
    return _entity_to_response(entity)


@router.put("/{entity_id}", response_model=ProjectEntityResponse)
async def update_entity_endpoint(
    entity_id: int,
    body: ProjectEntityUpdate,
    current_user: CurrentUserSchema = Depends(get_current_user),
    db_session: Session = Depends(get_session),
):
    entity = get_entity(db_session, entity_id)
    if not entity:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Entity {entity_id} not found")

    _check_portfolio_access(db_session, current_user, entity.portfolio_id)

    updates = body.model_dump(exclude_unset=True)
    if "entity_type" in updates and updates["entity_type"] is not None:
        updates["entity_type"] = updates["entity_type"].value if hasattr(updates["entity_type"], "value") else updates["entity_type"]

    entity = update_entity(db_session, entity_id, updates)
    return _entity_to_response(entity)


@router.delete("/{entity_id}", status_code=status.HTTP_200_OK)
async def delete_entity_endpoint(
    entity_id: int,
    current_user: CurrentUserSchema = Depends(get_current_user),
    db_session: Session = Depends(get_session),
):
    entity = get_entity(db_session, entity_id)
    if not entity:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Entity {entity_id} not found")

    _check_portfolio_access(db_session, current_user, entity.portfolio_id)
    soft_delete_entity(db_session, entity_id)

    return {"message": f"Entity '{entity.name}' deactivated"}


@router.get("/{entity_id}/assignments", response_model=EntityAssignmentsSummaryResponse)
async def get_entity_assignments_endpoint(
    entity_id: int,
    current_user: CurrentUserSchema = Depends(get_current_user),
    db_session: Session = Depends(get_session),
):
    entity = get_entity(db_session, entity_id)
    if not entity:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Entity {entity_id} not found")

    _check_portfolio_access(db_session, current_user, entity.portfolio_id)

    relationships = list_entity_assignments_by_entity(db_session, entity_id)
    items = []
    for rel in relationships:
        site_name = rel.site.name if hasattr(rel, "site") and rel.site else "Unknown"
        items.append(
            EntityAssignmentSummary(
                relationship_id=rel.id,
                site_id=rel.site_id,
                site_name=site_name,
                role=rel.role,
                effective_date=rel.effective_date,
                termination_date=rel.termination_date,
            )
        )

    return EntityAssignmentsSummaryResponse(items=items, total=len(items))


def _entity_to_response(entity) -> ProjectEntityResponse:
    linked_company_name = None
    if entity.linked_company_id and hasattr(entity, "linked_company") and entity.linked_company:
        linked_company_name = entity.linked_company.name

    return ProjectEntityResponse(
        id=entity.id,
        portfolio_id=entity.portfolio_id,
        name=entity.name,
        entity_type=entity.entity_type,
        address=entity.address,
        city=entity.city,
        state=entity.state,
        zip_code=entity.zip_code,
        phone=entity.phone,
        email=entity.email,
        website=entity.website,
        notes=entity.notes,
        is_active=entity.is_active,
        linked_company_id=entity.linked_company_id,
        linked_company_name=linked_company_name,
        created_at=entity.created_at,
        updated_at=entity.updated_at,
    )
