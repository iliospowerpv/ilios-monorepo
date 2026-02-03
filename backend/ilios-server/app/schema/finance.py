"""Finance module validation schemas."""

from datetime import date, datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schema.paginator import BasePaginator
from app.static.finance import (
    FinanceActualSource,
    FinanceApprovalDecision,
    FinanceBudgetCategory,
    FinanceBudgetStatus,
    FinanceObligationStatus,
    FinanceObligationType,
    FinanceVendorType,
)


class FinanceVendorBase(BaseModel):
    name: str = Field(max_length=255)
    vendor_type: FinanceVendorType
    contact_name: Optional[str] = Field(None, max_length=255)
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None
    is_active: bool = True


class FinanceVendorCreate(FinanceVendorBase):
    model_config = ConfigDict(extra="forbid")


class FinanceVendorUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = Field(None, max_length=255)
    vendor_type: Optional[FinanceVendorType] = None
    contact_name: Optional[str] = Field(None, max_length=255)
    contact_email: Optional[str] = Field(None, max_length=255)
    contact_phone: Optional[str] = Field(None, max_length=50)
    notes: Optional[str] = None
    is_active: Optional[bool] = None


class FinanceVendorSchema(FinanceVendorBase):
    id: int
    company_id: int
    created_at: datetime
    updated_at: datetime


class FinanceVendorOrderByEnum(str, Enum):
    name = "name"
    vendor_type = "vendor_type"
    is_active = "is_active"


class FinanceVendorPaginator(BasePaginator):
    items: list[FinanceVendorSchema]


class FinanceBudgetLineItemBase(BaseModel):
    category: FinanceBudgetCategory
    description: Optional[str] = Field(None, max_length=500)
    amount_planned: float = 0.0
    amount_authorized: float = 0.0
    amount_actual: float = 0.0
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    vendor_id: Optional[int] = None


class FinanceBudgetLineItemCreate(FinanceBudgetLineItemBase):
    model_config = ConfigDict(extra="forbid")


class FinanceBudgetLineItemUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: Optional[FinanceBudgetCategory] = None
    description: Optional[str] = Field(None, max_length=500)
    amount_planned: Optional[float] = None
    amount_authorized: Optional[float] = None
    amount_actual: Optional[float] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    vendor_id: Optional[int] = None


class FinanceBudgetLineItemSchema(FinanceBudgetLineItemBase):
    id: int
    budget_id: int
    created_at: datetime
    updated_at: datetime
    vendor_name: Optional[str] = None


class FinanceBudgetBase(BaseModel):
    name: str = Field(max_length=255)
    description: Optional[str] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    status: FinanceBudgetStatus = FinanceBudgetStatus.draft
    site_id: Optional[int] = None
    deal_id: Optional[int] = None


class FinanceBudgetCreate(FinanceBudgetBase):
    model_config = ConfigDict(extra="forbid")
    line_items: Optional[list[FinanceBudgetLineItemCreate]] = None


class FinanceBudgetUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    status: Optional[FinanceBudgetStatus] = None


class FinanceBudgetSchema(FinanceBudgetBase):
    id: int
    company_id: int
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[int] = None
    total_planned: float = 0.0
    total_authorized: float = 0.0
    total_actual: float = 0.0
    variance: float = 0.0


class FinanceBudgetDetailSchema(FinanceBudgetSchema):
    line_items: list[FinanceBudgetLineItemSchema] = []
    site_name: Optional[str] = None


class FinanceBudgetOrderByEnum(str, Enum):
    name = "name"
    status = "status"
    created_at = "created_at"


class FinanceBudgetPaginator(BasePaginator):
    items: list[FinanceBudgetSchema]


class FinanceObligationBase(BaseModel):
    obligation_type: FinanceObligationType
    description: Optional[str] = None
    amount_requested: float
    requested_date: date
    due_date: Optional[date] = None
    reference_number: Optional[str] = Field(None, max_length=100)
    site_id: Optional[int] = None
    vendor_id: Optional[int] = None
    budget_line_item_id: Optional[int] = None


class FinanceObligationCreate(FinanceObligationBase):
    model_config = ConfigDict(extra="forbid")


class FinanceObligationUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    obligation_type: Optional[FinanceObligationType] = None
    description: Optional[str] = None
    amount_requested: Optional[float] = None
    requested_date: Optional[date] = None
    due_date: Optional[date] = None
    reference_number: Optional[str] = Field(None, max_length=100)
    vendor_id: Optional[int] = None
    budget_line_item_id: Optional[int] = None


class FinanceObligationSubmit(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FinanceObligationSchema(FinanceObligationBase):
    id: int
    company_id: int
    status: FinanceObligationStatus
    prerequisite_snapshot: Optional[dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[int] = None
    vendor_name: Optional[str] = None
    site_name: Optional[str] = None


class FinanceObligationOrderByEnum(str, Enum):
    requested_date = "requested_date"
    due_date = "due_date"
    amount_requested = "amount_requested"
    status = "status"


class FinanceObligationPaginator(BasePaginator):
    items: list[FinanceObligationSchema]


class FinanceApprovalBase(BaseModel):
    decision: FinanceApprovalDecision
    notes: Optional[str] = None
    override_reason: Optional[str] = None


class FinanceApprovalCreate(FinanceApprovalBase):
    model_config = ConfigDict(extra="forbid")


class FinanceApprovalSchema(FinanceApprovalBase):
    id: int
    obligation_id: Optional[int] = None
    budget_id: Optional[int] = None
    approved_by_id: Optional[int] = None
    approved_at: datetime
    approved_by_name: Optional[str] = None


class FinanceBudgetSubmit(BaseModel):
    model_config = ConfigDict(extra="forbid")


class FinanceActualBase(BaseModel):
    category: FinanceBudgetCategory
    description: Optional[str] = Field(None, max_length=500)
    amount: float
    transaction_date: date
    reference_id: Optional[str] = Field(None, max_length=100)
    source_system: FinanceActualSource = FinanceActualSource.manual
    site_id: Optional[int] = None
    vendor_id: Optional[int] = None


class FinanceActualCreate(FinanceActualBase):
    model_config = ConfigDict(extra="forbid")


class FinanceActualUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: Optional[FinanceBudgetCategory] = None
    description: Optional[str] = Field(None, max_length=500)
    amount: Optional[float] = None
    transaction_date: Optional[date] = None
    reference_id: Optional[str] = Field(None, max_length=100)
    source_system: Optional[FinanceActualSource] = None
    vendor_id: Optional[int] = None


class FinanceActualSchema(FinanceActualBase):
    id: int
    company_id: int
    created_at: datetime
    updated_at: datetime
    created_by_id: Optional[int] = None
    vendor_name: Optional[str] = None
    site_name: Optional[str] = None


class FinanceActualOrderByEnum(str, Enum):
    transaction_date = "transaction_date"
    amount = "amount"
    category = "category"


class FinanceActualPaginator(BasePaginator):
    items: list[FinanceActualSchema]


class FinanceSiteSummarySchema(BaseModel):
    site_id: int
    site_name: str
    total_budget_planned: float = 0.0
    total_budget_authorized: float = 0.0
    total_budget_actual: float = 0.0
    budget_variance: float = 0.0
    pending_obligations: int = 0
    pending_obligations_amount: float = 0.0
    finance_ready: bool = False
    missing_prerequisites: list[str] = []


class FinancePortfolioSummarySchema(BaseModel):
    total_budget_planned: float = 0.0
    total_budget_authorized: float = 0.0
    total_budget_actual: float = 0.0
    total_variance: float = 0.0
    sites_finance_ready: int = 0
    sites_not_ready: int = 0
    total_pending_obligations: int = 0
    total_pending_amount: float = 0.0


class FinancePortfolioResponseSchema(BaseModel):
    summary: FinancePortfolioSummarySchema
    sites: list[FinanceSiteSummarySchema]


class FinanceAuditTrailSchema(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    action: str
    user_id: Optional[int] = None
    user_name: Optional[str] = None
    timestamp: datetime
    details: Optional[dict[str, Any]] = None


class FinanceDataRoomPackageSchema(BaseModel):
    site_id: int
    site_name: str
    generated_at: datetime
    budgets: list[FinanceBudgetDetailSchema]
    obligations: list[FinanceObligationSchema]
    approvals: list[FinanceApprovalSchema]
    actuals: list[FinanceActualSchema]
    summary: FinanceSiteSummarySchema
