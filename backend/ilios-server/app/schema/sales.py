"""Sales module Pydantic schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from app.static.sales import LifecycleState, SalesSource, SalesStage


class SalesProjectBase(BaseModel):
    """Base schema for sales project data."""
    sales_stage: Optional[SalesStage] = None
    lifecycle_state: Optional[LifecycleState] = None
    sales_source: Optional[SalesSource] = None
    target_close_date: Optional[date] = None
    probability: Optional[int] = Field(None, ge=0, le=100)
    pipeline_value: Optional[Decimal] = None
    assigned_owner_id: Optional[int] = None
    next_action_date: Optional[date] = None
    next_action_notes: Optional[str] = None
    sales_notes: Optional[str] = None


class SalesProjectUpdate(SalesProjectBase):
    """Schema for updating sales fields on a project."""
    pass


class SalesStageTransition(BaseModel):
    """Schema for transitioning sales stage."""
    new_stage: SalesStage
    notes: Optional[str] = None


class LifecycleStateTransition(BaseModel):
    """Schema for transitioning lifecycle state."""
    new_state: LifecycleState
    notes: Optional[str] = None


class HandoffChecklistItem(BaseModel):
    """Individual handoff checklist item."""
    field: str
    label: str
    completed: bool
    value: Optional[str] = None


class HandoffChecklistResponse(BaseModel):
    """Response for handoff checklist status."""
    site_id: int
    all_complete: bool
    items: List[HandoffChecklistItem]


class UserSummary(BaseModel):
    """Summary of user for assigned owner."""
    id: int
    first_name: str
    last_name: str
    email: str

    class Config:
        from_attributes = True


class CompanySummary(BaseModel):
    """Summary of company."""
    id: int
    name: str

    class Config:
        from_attributes = True


class SalesProjectResponse(BaseModel):
    """Full response for a sales project."""
    id: int
    name: str
    address: str
    city: str
    state: str
    system_size_ac: float
    system_size_dc: float
    
    company: CompanySummary
    
    sales_stage: Optional[SalesStage] = None
    lifecycle_state: Optional[LifecycleState] = None
    sales_source: Optional[SalesSource] = None
    target_close_date: Optional[date] = None
    probability: Optional[int] = None
    pipeline_value: Optional[Decimal] = None
    assigned_owner: Optional[UserSummary] = None
    next_action_date: Optional[date] = None
    next_action_notes: Optional[str] = None
    sales_notes: Optional[str] = None
    handoff_checklist_completed: Optional[bool] = None

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SalesPipelineSummary(BaseModel):
    """Summary for pipeline/kanban view."""
    id: int
    name: str
    company_name: str
    sales_stage: Optional[SalesStage] = None
    lifecycle_state: Optional[LifecycleState] = None
    pipeline_value: Optional[Decimal] = None
    probability: Optional[int] = None
    target_close_date: Optional[date] = None
    next_action_date: Optional[date] = None
    assigned_owner: Optional[UserSummary] = None
    system_size_ac: float

    class Config:
        from_attributes = True


class SalesPipelineResponse(BaseModel):
    """Grouped pipeline response for kanban view."""
    discovery: List[SalesPipelineSummary] = []
    qualified: List[SalesPipelineSummary] = []
    loi_term_sheet: List[SalesPipelineSummary] = []
    under_contract: List[SalesPipelineSummary] = []
    handoff_to_diligence: List[SalesPipelineSummary] = []


class SalesStateTransitionResponse(BaseModel):
    """Audit log entry for state transitions."""
    id: int
    site_id: int
    transition_type: str
    from_state: Optional[str] = None
    to_state: str
    notes: Optional[str] = None
    changed_by: Optional[UserSummary] = None
    created_at: datetime

    class Config:
        from_attributes = True


class SalesListFilters(BaseModel):
    """Filters for sales list view."""
    company_id: Optional[int] = None
    sales_stage: Optional[SalesStage] = None
    lifecycle_state: Optional[LifecycleState] = None
    assigned_owner_id: Optional[int] = None
    needs_action: Optional[bool] = None
    skip: int = 0
    limit: int = 50


class DataRoomPackageResponse(BaseModel):
    """Response for data room package export."""
    site_id: int
    site_name: str
    company_name: str
    sales_history: List[SalesStateTransitionResponse]
    current_stage: Optional[SalesStage] = None
    lifecycle_state: Optional[LifecycleState] = None
    generated_at: datetime
