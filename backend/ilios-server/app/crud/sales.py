"""Sales module CRUD operations."""

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from app.models.sales import SalesStateTransition
from app.models.site import Site, SiteAdditionalFieldList
from app.schema.sales import SalesListFilters, SalesProjectUpdate
from app.static.sales import HANDOFF_CHECKLIST_ITEMS, LifecycleState, SalesStage


def get_sales_projects(
    db: Session,
    company_id: Optional[int] = None,
    filters: Optional[SalesListFilters] = None,
) -> List[Site]:
    """Get list of projects with sales data."""
    query = (
        db.query(Site)
        .join(Site.additional_fields)
        .options(
            joinedload(Site.additional_fields).joinedload(SiteAdditionalFieldList.assigned_owner),
            joinedload(Site.company),
        )
    )
    
    if company_id:
        query = query.filter(Site.company_id == company_id)
    
    if filters:
        if filters.company_id:
            query = query.filter(Site.company_id == filters.company_id)
        if filters.sales_stage:
            query = query.filter(SiteAdditionalFieldList.sales_stage == filters.sales_stage)
        if filters.lifecycle_state:
            query = query.filter(SiteAdditionalFieldList.lifecycle_state == filters.lifecycle_state)
        if filters.assigned_owner_id:
            query = query.filter(SiteAdditionalFieldList.assigned_owner_id == filters.assigned_owner_id)
        if filters.needs_action:
            today = date.today()
            query = query.filter(
                or_(
                    SiteAdditionalFieldList.next_action_date <= today,
                    SiteAdditionalFieldList.next_action_date.is_(None),
                )
            )
        query = query.offset(filters.skip).limit(filters.limit)
    
    return query.all()


def get_sales_pipeline(db: Session, company_id: Optional[int] = None) -> dict:
    """Get projects grouped by sales stage for kanban view."""
    query = (
        db.query(Site)
        .join(Site.additional_fields)
        .options(
            joinedload(Site.additional_fields).joinedload(SiteAdditionalFieldList.assigned_owner),
            joinedload(Site.company),
        )
        .filter(
            or_(
                SiteAdditionalFieldList.lifecycle_state == LifecycleState.sales_pre_diligence,
                SiteAdditionalFieldList.lifecycle_state.is_(None),
            )
        )
    )
    
    if company_id:
        query = query.filter(Site.company_id == company_id)
    
    projects = query.all()
    
    pipeline = {
        "discovery": [],
        "qualified": [],
        "loi_term_sheet": [],
        "under_contract": [],
        "handoff_to_diligence": [],
    }
    
    stage_mapping = {
        SalesStage.discovery: "discovery",
        SalesStage.qualified: "qualified",
        SalesStage.loi_term_sheet: "loi_term_sheet",
        SalesStage.under_contract: "under_contract",
        SalesStage.handoff_to_diligence: "handoff_to_diligence",
    }
    
    for project in projects:
        if project.additional_fields and project.additional_fields.sales_stage:
            stage_key = stage_mapping.get(project.additional_fields.sales_stage, "discovery")
        else:
            stage_key = "discovery"
        pipeline[stage_key].append(project)
    
    return pipeline


def get_project_with_sales(db: Session, site_id: int) -> Optional[Site]:
    """Get a single project with sales data."""
    return (
        db.query(Site)
        .options(
            joinedload(Site.additional_fields).joinedload(SiteAdditionalFieldList.assigned_owner),
            joinedload(Site.company),
        )
        .filter(Site.id == site_id)
        .first()
    )


def update_sales_fields(
    db: Session,
    site_id: int,
    data: SalesProjectUpdate,
) -> Optional[SiteAdditionalFieldList]:
    """Update sales-specific fields on a project."""
    additional_fields = (
        db.query(SiteAdditionalFieldList)
        .filter(SiteAdditionalFieldList.site_id == site_id)
        .first()
    )
    
    if not additional_fields:
        additional_fields = SiteAdditionalFieldList(site_id=site_id)
        db.add(additional_fields)
    
    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(additional_fields, field, value)
    
    additional_fields.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(additional_fields)
    
    return additional_fields


def transition_sales_stage(
    db: Session,
    site_id: int,
    new_stage: SalesStage,
    user_id: int,
    notes: Optional[str] = None,
) -> SiteAdditionalFieldList:
    """Transition sales stage with audit logging."""
    additional_fields = (
        db.query(SiteAdditionalFieldList)
        .filter(SiteAdditionalFieldList.site_id == site_id)
        .first()
    )
    
    if not additional_fields:
        additional_fields = SiteAdditionalFieldList(site_id=site_id)
        db.add(additional_fields)
        db.flush()
    
    old_stage = additional_fields.sales_stage
    additional_fields.sales_stage = new_stage
    additional_fields.updated_at = datetime.utcnow()
    
    transition = SalesStateTransition(
        site_id=site_id,
        transition_type="sales_stage",
        from_state=old_stage.value if old_stage else None,
        to_state=new_stage.value,
        notes=notes,
        changed_by_id=user_id,
    )
    db.add(transition)
    
    db.commit()
    db.refresh(additional_fields)
    
    return additional_fields


def transition_lifecycle_state(
    db: Session,
    site_id: int,
    new_state: LifecycleState,
    user_id: int,
    notes: Optional[str] = None,
) -> SiteAdditionalFieldList:
    """Transition lifecycle state with audit logging."""
    additional_fields = (
        db.query(SiteAdditionalFieldList)
        .filter(SiteAdditionalFieldList.site_id == site_id)
        .first()
    )
    
    if not additional_fields:
        additional_fields = SiteAdditionalFieldList(site_id=site_id)
        db.add(additional_fields)
        db.flush()
    
    old_state = additional_fields.lifecycle_state
    additional_fields.lifecycle_state = new_state
    additional_fields.updated_at = datetime.utcnow()
    
    transition = SalesStateTransition(
        site_id=site_id,
        transition_type="lifecycle_state",
        from_state=old_state.value if old_state else None,
        to_state=new_state.value,
        notes=notes,
        changed_by_id=user_id,
    )
    db.add(transition)
    
    db.commit()
    db.refresh(additional_fields)
    
    return additional_fields


def get_handoff_checklist(db: Session, site_id: int) -> dict:
    """Get handoff checklist status for a project."""
    site = (
        db.query(Site)
        .options(joinedload(Site.additional_fields))
        .filter(Site.id == site_id)
        .first()
    )
    
    if not site:
        return {"site_id": site_id, "all_complete": False, "items": []}
    
    checklist_items = []
    field_labels = {
        "address": "Address",
        "system_size_ac": "System Size (AC)",
        "system_size_dc": "System Size (DC)",
        "utility_rate": "Utility Rate",
        "ownership_structure": "Ownership Structure",
        "offtaker_name": "Offtaker Name",
    }
    
    for field in HANDOFF_CHECKLIST_ITEMS:
        if field in ["address", "system_size_ac", "system_size_dc"]:
            value = getattr(site, field, None)
        elif site.additional_fields:
            value = getattr(site.additional_fields, field, None)
        else:
            value = None
        
        completed = value is not None and value != ""
        checklist_items.append({
            "field": field,
            "label": field_labels.get(field, field),
            "completed": completed,
            "value": str(value) if value else None,
        })
    
    all_complete = all(item["completed"] for item in checklist_items)
    
    return {
        "site_id": site_id,
        "all_complete": all_complete,
        "items": checklist_items,
    }


def get_state_transitions(db: Session, site_id: int) -> List[SalesStateTransition]:
    """Get audit log of state transitions for a project."""
    return (
        db.query(SalesStateTransition)
        .options(joinedload(SalesStateTransition.changed_by))
        .filter(SalesStateTransition.site_id == site_id)
        .order_by(SalesStateTransition.created_at.desc())
        .all()
    )
