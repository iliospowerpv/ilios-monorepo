"""Pydantic schemas for finance data ingestion read endpoints and sync responses."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any, List, Optional

from pydantic import BaseModel, Field


class FinanceAccountResponse(BaseModel):
    id: int
    company_id: int
    provider_key: str
    external_id: str
    name: str
    account_type: Optional[str] = None
    parent_external_id: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FinanceAccountsListResponse(BaseModel):
    accounts: List[FinanceAccountResponse]
    total: int


class FinanceTransactionResponse(BaseModel):
    id: int
    company_id: int
    provider_key: str
    external_id: str
    account_external_id: str
    amount: Decimal
    currency: Optional[str] = "USD"
    txn_date: date
    description: Optional[str] = None
    counterparty: Optional[str] = None
    project_external_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FinanceTransactionsListResponse(BaseModel):
    transactions: List[FinanceTransactionResponse]
    total: int


class FinanceSyncRunResponse(BaseModel):
    id: int
    company_id: int
    provider_key: str
    status: str
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    correlation_id: str
    triggered_by_user_id: Optional[int] = None
    last_error: Optional[str] = None
    stats_json: Optional[dict] = None
    last_successful_sync_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class FinanceSyncRunsListResponse(BaseModel):
    sync_runs: List[FinanceSyncRunResponse]
    total: int


class FinanceSyncTriggerResponse(BaseModel):
    sync_run_id: int
    correlation_id: str
    status: str
    message: str
