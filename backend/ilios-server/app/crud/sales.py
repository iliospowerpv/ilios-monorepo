"""Sales module CRUD operations."""

from datetime import date, datetime
from typing import List, Optional

from sqlalchemy import and_, or_
from sqlalchemy.orm import Session, joinedload

from app.models.sales import Deal, SalesStateTransition
from app.models.site import Site, SiteAdditionalFieldList
from app.schema.sales import DealCreate, DealUpdate, SalesListFilters, SalesProjectUpdate
from app.static.sales import HANDOFF_CHECKLIST_ITEMS, LifecycleState, SalesStage


def get_deals(
    db: Session,
    company_id: Optional[int] = None,
    sales_stage: Optional[SalesStage] = None,
    skip: int = 0,
    limit: int = 50,
) -> List[Deal]:
    """Get list of deals."""
    query = (
        db.query(Deal)
        .options(
            joinedload(Deal.company),
            joinedload(Deal.assigned_owner),
        )
        .filter(Deal.is_converted == False)
    )
    
    if company_id:
        query = query.filter(Deal.company_id == company_id)
    
    if sales_stage:
        query = query.filter(Deal.sales_stage == sales_stage.value)
    
    return query.offset(skip).limit(limit).all()


def get_deals_pipeline(db: Session, company_id: Optional[int] = None) -> dict:
    """Get deals grouped by sales stage for kanban view."""
    query = (
        db.query(Deal)
        .options(
            joinedload(Deal.company),
            joinedload(Deal.assigned_owner),
        )
        .filter(Deal.is_converted == False)
    )
    
    if company_id:
        query = query.filter(Deal.company_id == company_id)
    
    deals = query.all()
    
    pipeline = {
        "prospect": [],
        "nda_signed": [],
        "inputs_received": [],
        "modeling": [],
        "model_review": [],
        "model_approved": [],
        "quoted": [],
        "term_sheet_neg": [],
        "term_sheet_signed": [],
        "phase_1_diligence": [],
        "mipa_negotiating": [],
        "mipa_signed": [],
        "passed": [],
        "dead": [],
    }
    
    stage_mapping = {
        SalesStage.prospect.value: "prospect",
        SalesStage.nda_signed.value: "nda_signed",
        SalesStage.inputs_received.value: "inputs_received",
        SalesStage.modeling.value: "modeling",
        SalesStage.model_review.value: "model_review",
        SalesStage.model_approved.value: "model_approved",
        SalesStage.quoted.value: "quoted",
        SalesStage.term_sheet_neg.value: "term_sheet_neg",
        SalesStage.term_sheet_signed.value: "term_sheet_signed",
        SalesStage.phase_1_diligence.value: "phase_1_diligence",
        SalesStage.mipa_negotiating.value: "mipa_negotiating",
        SalesStage.mipa_signed.value: "mipa_signed",
        SalesStage.passed.value: "passed",
        SalesStage.dead.value: "dead",
    }
    
    for deal in deals:
        if deal.sales_stage:
            stage_key = stage_mapping.get(deal.sales_stage, "prospect")
        else:
            stage_key = "prospect"
        pipeline[stage_key].append(deal)
    
    return pipeline


def get_deal(db: Session, deal_id: int) -> Optional[Deal]:
    """Get a single deal by ID."""
    return (
        db.query(Deal)
        .options(
            joinedload(Deal.company),
            joinedload(Deal.assigned_owner),
        )
        .filter(Deal.id == deal_id)
        .first()
    )


def create_deal(db: Session, data: DealCreate, user_id: int) -> Deal:
    """Create a new deal."""
    deal = Deal(
        name=data.name,
        developer_name=data.developer_name,
        sales_stage=data.sales_stage.value if data.sales_stage else SalesStage.prospect.value,
        lifecycle_state=LifecycleState.sales_pre_diligence.value,
        quoted_by=data.quoted_by,
        last_action=data.last_action,
        next_action=data.next_action,
        next_action_status=data.next_action_status.value if data.next_action_status else None,
        ownership_structure=data.ownership_structure,
        address=data.address,
        city=data.city,
        state=data.state,
        zip_code=data.zip_code,
        county=data.county,
        latitude=data.latitude,
        longitude=data.longitude,
        notice_to_proceed_date=data.notice_to_proceed_date,
        mechanical_completion_date=data.mechanical_completion_date,
        permission_to_operate_date=data.permission_to_operate_date,
        substantial_completion_date=data.substantial_completion_date,
        project_company=data.project_company,
        mipa_per_watt=data.mipa_per_watt,
        offtaker_legal_name=data.offtaker_legal_name,
        utility_zone=data.utility_zone,
        system_size_kw_dc=data.system_size_kw_dc,
        itc_percent=data.itc_percent,
        itc_amount=data.itc_amount,
        fmv=data.fmv,
        grant_amount=data.grant_amount,
        tax_equity=data.tax_equity,
        company_id=data.company_id,
        assigned_owner_id=data.assigned_owner_id or user_id,
        pipeline_value=data.pipeline_value,
        probability=data.probability,
        target_close_date=data.target_close_date,
    )
    
    db.add(deal)
    db.flush()
    
    transition = SalesStateTransition(
        deal_id=deal.id,
        transition_type="deal_created",
        from_state=None,
        to_state=deal.sales_stage,
        notes="Deal created",
        changed_by_id=user_id,
    )
    db.add(transition)
    
    db.commit()
    db.refresh(deal)
    
    return deal


def update_deal(db: Session, deal_id: int, data: DealUpdate, user_id: int) -> Optional[Deal]:
    """Update an existing deal."""
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    
    if not deal:
        return None
    
    update_data = data.model_dump(exclude_unset=True)
    
    old_stage = deal.sales_stage
    
    for field, value in update_data.items():
        if field == "sales_stage" and value:
            value = value.value
        elif field == "next_action_status" and value:
            value = value.value
        setattr(deal, field, value)
    
    deal.updated_at = datetime.utcnow()
    
    if "sales_stage" in update_data and update_data["sales_stage"] and update_data["sales_stage"].value != old_stage:
        transition = SalesStateTransition(
            deal_id=deal.id,
            transition_type="sales_stage",
            from_state=old_stage,
            to_state=deal.sales_stage,
            notes=None,
            changed_by_id=user_id,
        )
        db.add(transition)
    
    db.commit()
    db.refresh(deal)
    
    return deal


def transition_deal_stage(
    db: Session,
    deal_id: int,
    new_stage: SalesStage,
    user_id: int,
    notes: Optional[str] = None,
) -> Optional[Deal]:
    """Transition deal sales stage with audit logging."""
    deal = db.query(Deal).filter(Deal.id == deal_id).first()
    
    if not deal:
        return None
    
    old_stage = deal.sales_stage
    deal.sales_stage = new_stage.value
    deal.updated_at = datetime.utcnow()
    
    transition = SalesStateTransition(
        deal_id=deal.id,
        transition_type="sales_stage",
        from_state=old_stage,
        to_state=new_stage.value,
        notes=notes,
        changed_by_id=user_id,
    )
    db.add(transition)
    
    db.commit()
    db.refresh(deal)
    
    return deal


def get_deal_transitions(db: Session, deal_id: int) -> List[SalesStateTransition]:
    """Get audit log of state transitions for a deal."""
    return (
        db.query(SalesStateTransition)
        .options(joinedload(SalesStateTransition.changed_by))
        .filter(SalesStateTransition.deal_id == deal_id)
        .order_by(SalesStateTransition.created_at.desc())
        .all()
    )


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
    """Get projects grouped by sales stage for kanban view (deprecated - use get_deals_pipeline)."""
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
    
    pipeline = {stage.name: [] for stage in SalesStage}
    
    for project in projects:
        if project.additional_fields and project.additional_fields.sales_stage:
            stage_key = project.additional_fields.sales_stage.name
        else:
            stage_key = "prospect"
        if stage_key in pipeline:
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
