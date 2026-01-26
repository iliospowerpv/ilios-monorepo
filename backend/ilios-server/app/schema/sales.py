"""Sales module Pydantic schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, Field

from app.static.sales import LifecycleState, NextActionStatus, SalesSource, SalesStage


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


class DealCreate(BaseModel):
    """Schema for creating a new deal."""
    name: str = Field(..., min_length=1, max_length=255, description="Project name")
    developer_name: Optional[str] = None
    sales_stage: SalesStage = SalesStage.prospect
    quoted_by: Optional[str] = None
    last_action: Optional[str] = None
    next_action: Optional[str] = None
    next_action_status: Optional[NextActionStatus] = None
    ownership_structure: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    county: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    notice_to_proceed_date: Optional[date] = None
    mechanical_completion_date: Optional[date] = None
    permission_to_operate_date: Optional[date] = None
    substantial_completion_date: Optional[date] = None
    project_company: Optional[str] = None
    mipa_per_watt: Optional[Decimal] = None
    offtaker_name: Optional[str] = None
    offtaker_legal_name: Optional[str] = None
    utility_rate: Optional[str] = None
    utility_zone: Optional[str] = None
    system_size_ac: Optional[Decimal] = None
    system_size_dc: Optional[Decimal] = None
    itc_percent: Optional[Decimal] = None
    itc_amount: Optional[Decimal] = None
    fmv: Optional[Decimal] = None
    grant_amount: Optional[Decimal] = None
    tax_equity: Optional[Decimal] = None
    company_id: Optional[int] = None
    assigned_owner_id: Optional[int] = None
    pipeline_value: Optional[Decimal] = None
    probability: Optional[int] = Field(None, ge=0, le=100)
    target_close_date: Optional[date] = None
    next_action_date: Optional[date] = None
    sales_notes: Optional[str] = None


class DealUpdate(BaseModel):
    """Schema for updating a deal."""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    developer_name: Optional[str] = None
    sales_stage: Optional[SalesStage] = None
    quoted_by: Optional[str] = None
    last_action: Optional[str] = None
    next_action: Optional[str] = None
    next_action_status: Optional[NextActionStatus] = None
    ownership_structure: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    county: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    notice_to_proceed_date: Optional[date] = None
    mechanical_completion_date: Optional[date] = None
    permission_to_operate_date: Optional[date] = None
    substantial_completion_date: Optional[date] = None
    project_company: Optional[str] = None
    mipa_per_watt: Optional[Decimal] = None
    offtaker_name: Optional[str] = None
    offtaker_legal_name: Optional[str] = None
    utility_rate: Optional[str] = None
    utility_zone: Optional[str] = None
    system_size_ac: Optional[Decimal] = None
    system_size_dc: Optional[Decimal] = None
    itc_percent: Optional[Decimal] = None
    itc_amount: Optional[Decimal] = None
    fmv: Optional[Decimal] = None
    grant_amount: Optional[Decimal] = None
    tax_equity: Optional[Decimal] = None
    company_id: Optional[int] = None
    assigned_owner_id: Optional[int] = None
    pipeline_value: Optional[Decimal] = None
    probability: Optional[int] = Field(None, ge=0, le=100)
    target_close_date: Optional[date] = None
    next_action_date: Optional[date] = None
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


class DealResponse(BaseModel):
    """Full response for a deal."""
    id: int
    name: str
    developer_name: Optional[str] = None
    sales_stage: Optional[SalesStage] = None
    lifecycle_state: Optional[LifecycleState] = None
    quoted_by: Optional[str] = None
    last_action: Optional[str] = None
    next_action: Optional[str] = None
    next_action_status: Optional[NextActionStatus] = None
    ownership_structure: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    county: Optional[str] = None
    latitude: Optional[Decimal] = None
    longitude: Optional[Decimal] = None
    notice_to_proceed_date: Optional[date] = None
    mechanical_completion_date: Optional[date] = None
    permission_to_operate_date: Optional[date] = None
    substantial_completion_date: Optional[date] = None
    project_company: Optional[str] = None
    mipa_per_watt: Optional[Decimal] = None
    offtaker_name: Optional[str] = None
    offtaker_legal_name: Optional[str] = None
    utility_rate: Optional[str] = None
    utility_zone: Optional[str] = None
    system_size_ac: Optional[Decimal] = None
    system_size_dc: Optional[Decimal] = None
    itc_percent: Optional[Decimal] = None
    itc_amount: Optional[Decimal] = None
    fmv: Optional[Decimal] = None
    grant_amount: Optional[Decimal] = None
    tax_equity: Optional[Decimal] = None
    company: Optional[CompanySummary] = None
    company_id: Optional[int] = None
    assigned_owner: Optional[UserSummary] = None
    pipeline_value: Optional[Decimal] = None
    probability: Optional[int] = None
    target_close_date: Optional[date] = None
    next_action_date: Optional[date] = None
    sales_notes: Optional[str] = None
    is_converted: bool = False
    converted_project_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

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
    company_name: Optional[str] = None
    developer_name: Optional[str] = None
    sales_stage: Optional[SalesStage] = None
    lifecycle_state: Optional[LifecycleState] = None
    pipeline_value: Optional[Decimal] = None
    probability: Optional[int] = None
    target_close_date: Optional[date] = None
    next_action: Optional[str] = None
    next_action_status: Optional[NextActionStatus] = None
    assigned_owner: Optional[UserSummary] = None
    system_size_ac: Optional[Decimal] = None
    system_size_dc: Optional[Decimal] = None
    mipa_per_watt: Optional[Decimal] = None
    is_converted: bool = False

    class Config:
        from_attributes = True


class SalesPipelineResponse(BaseModel):
    """Grouped pipeline response for kanban view."""
    prospect: List[SalesPipelineSummary] = []
    nda_signed: List[SalesPipelineSummary] = []
    inputs_received: List[SalesPipelineSummary] = []
    modeling: List[SalesPipelineSummary] = []
    model_review: List[SalesPipelineSummary] = []
    model_approved: List[SalesPipelineSummary] = []
    quoted: List[SalesPipelineSummary] = []
    term_sheet_neg: List[SalesPipelineSummary] = []
    term_sheet_signed: List[SalesPipelineSummary] = []
    phase_1_diligence: List[SalesPipelineSummary] = []
    mipa_negotiating: List[SalesPipelineSummary] = []
    mipa_signed: List[SalesPipelineSummary] = []
    passed: List[SalesPipelineSummary] = []
    dead: List[SalesPipelineSummary] = []


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


class ConvertToProjectRequest(BaseModel):
    """Request to convert a deal to a project."""
    company_id: int
    additional_notes: Optional[str] = None


class ConvertToProjectResponse(BaseModel):
    """Response after converting a deal to a project."""
    deal_id: int
    project_id: int
    message: str
