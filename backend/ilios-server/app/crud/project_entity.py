"""CRUD operations for the Entity Directory system."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session, joinedload

from app.models.project_entity import (
    DealEntityAssignment,
    EntityRelationship,
    ProjectEntity,
)
from app.static.entities import DealEntityRole, EntityRelationshipRole, EntityType


def list_entities(
    db: Session,
    portfolio_id: int,
    search: Optional[str] = None,
    entity_type: Optional[EntityType] = None,
    include_inactive: bool = False,
    skip: int = 0,
    limit: int = 50,
) -> List[ProjectEntity]:
    query = db.query(ProjectEntity).filter(ProjectEntity.portfolio_id == portfolio_id)

    if not include_inactive:
        query = query.filter(ProjectEntity.is_active == True)

    if search:
        query = query.filter(ProjectEntity.name.ilike(f"%{search}%"))

    if entity_type:
        query = query.filter(ProjectEntity.entity_type == entity_type)

    return query.order_by(ProjectEntity.name).offset(skip).limit(limit).all()


def count_entities(
    db: Session,
    portfolio_id: int,
    search: Optional[str] = None,
    entity_type: Optional[EntityType] = None,
    include_inactive: bool = False,
) -> int:
    query = db.query(ProjectEntity).filter(ProjectEntity.portfolio_id == portfolio_id)

    if not include_inactive:
        query = query.filter(ProjectEntity.is_active == True)

    if search:
        query = query.filter(ProjectEntity.name.ilike(f"%{search}%"))

    if entity_type:
        query = query.filter(ProjectEntity.entity_type == entity_type)

    return query.count()


def get_entity(db: Session, entity_id: int) -> Optional[ProjectEntity]:
    return (
        db.query(ProjectEntity)
        .options(
            joinedload(ProjectEntity.portfolio),
            joinedload(ProjectEntity.linked_company),
        )
        .filter(ProjectEntity.id == entity_id)
        .first()
    )


def create_entity(db: Session, data: dict) -> ProjectEntity:
    entity = ProjectEntity(**data)
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return entity


def update_entity(db: Session, entity_id: int, data: dict) -> Optional[ProjectEntity]:
    entity = db.query(ProjectEntity).filter(ProjectEntity.id == entity_id).first()
    if not entity:
        return None

    for field, value in data.items():
        setattr(entity, field, value)

    entity.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(entity)
    return entity


def soft_delete_entity(db: Session, entity_id: int) -> Optional[ProjectEntity]:
    entity = db.query(ProjectEntity).filter(ProjectEntity.id == entity_id).first()
    if not entity:
        return None

    entity.is_active = False
    entity.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(entity)
    return entity


def list_entity_relationships(
    db: Session,
    site_id: int,
    role: Optional[EntityRelationshipRole] = None,
) -> List[EntityRelationship]:
    query = (
        db.query(EntityRelationship)
        .options(
            joinedload(EntityRelationship.entity),
            joinedload(EntityRelationship.contact),
        )
        .filter(EntityRelationship.site_id == site_id)
    )

    if role:
        query = query.filter(EntityRelationship.role == role)

    return query.order_by(EntityRelationship.role, EntityRelationship.id).all()


def get_entity_relationship(db: Session, relationship_id: int) -> Optional[EntityRelationship]:
    return (
        db.query(EntityRelationship)
        .options(
            joinedload(EntityRelationship.entity),
            joinedload(EntityRelationship.contact),
        )
        .filter(EntityRelationship.id == relationship_id)
        .first()
    )


def create_entity_relationship(db: Session, data: dict) -> EntityRelationship:
    rel = EntityRelationship(**data)
    db.add(rel)
    db.commit()
    db.refresh(rel)
    return rel


def update_entity_relationship(
    db: Session, relationship_id: int, data: dict
) -> Optional[EntityRelationship]:
    rel = (
        db.query(EntityRelationship)
        .filter(EntityRelationship.id == relationship_id)
        .first()
    )
    if not rel:
        return None

    for field, value in data.items():
        setattr(rel, field, value)

    rel.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(rel)
    return rel


def delete_entity_relationship(db: Session, relationship_id: int) -> bool:
    deleted = (
        db.query(EntityRelationship)
        .filter(EntityRelationship.id == relationship_id)
        .delete()
    )
    if deleted:
        db.commit()
    return deleted > 0


def list_deal_entity_assignments(
    db: Session,
    deal_id: int,
    role: Optional[DealEntityRole] = None,
) -> List[DealEntityAssignment]:
    query = (
        db.query(DealEntityAssignment)
        .options(
            joinedload(DealEntityAssignment.entity),
            joinedload(DealEntityAssignment.contact),
        )
        .filter(DealEntityAssignment.deal_id == deal_id)
    )

    if role:
        query = query.filter(DealEntityAssignment.role == role)

    return query.order_by(DealEntityAssignment.role, DealEntityAssignment.id).all()


def get_deal_entity_assignment(db: Session, assignment_id: int) -> Optional[DealEntityAssignment]:
    return (
        db.query(DealEntityAssignment)
        .options(
            joinedload(DealEntityAssignment.entity),
            joinedload(DealEntityAssignment.contact),
        )
        .filter(DealEntityAssignment.id == assignment_id)
        .first()
    )


def create_deal_entity_assignment(db: Session, data: dict) -> DealEntityAssignment:
    assignment = DealEntityAssignment(**data)
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


def update_deal_entity_assignment(
    db: Session, assignment_id: int, data: dict
) -> Optional[DealEntityAssignment]:
    assignment = (
        db.query(DealEntityAssignment)
        .filter(DealEntityAssignment.id == assignment_id)
        .first()
    )
    if not assignment:
        return None

    for field, value in data.items():
        setattr(assignment, field, value)

    assignment.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(assignment)
    return assignment


def delete_deal_entity_assignment(db: Session, assignment_id: int) -> bool:
    deleted = (
        db.query(DealEntityAssignment)
        .filter(DealEntityAssignment.id == assignment_id)
        .delete()
    )
    if deleted:
        db.commit()
    return deleted > 0
