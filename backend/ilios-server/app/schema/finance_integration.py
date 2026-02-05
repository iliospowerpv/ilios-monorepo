"""Pydantic schemas for finance integration configuration."""

from datetime import datetime
from typing import Optional, Any
from enum import Enum

from pydantic import BaseModel, Field


class FinanceIntegrationStatus(str, Enum):
    """Status of a finance integration configuration."""
    pending = "pending"
    configured = "configured"
    error = "error"
    disabled = "disabled"


class FinanceProviderInfo(BaseModel):
    """Information about an available finance provider."""
    key: str
    display_name: str
    supports_budgets: bool


class FinanceIntegrationCredentials(BaseModel):
    """Credentials for a finance provider.
    
    This schema is used for input only - credentials are never returned in responses.
    """
    api_key: Optional[str] = None
    api_secret: Optional[str] = None
    base_url: Optional[str] = None
    additional: Optional[dict[str, Any]] = None


class FinanceIntegrationCreate(BaseModel):
    """Schema for creating a finance integration."""
    provider_key: str = Field(..., description="Provider identifier (e.g., 'gravity', 'quickbooks')")
    credentials: FinanceIntegrationCredentials = Field(..., description="Provider credentials")
    config: Optional[dict[str, Any]] = Field(default=None, description="Additional configuration options")


class FinanceIntegrationUpdate(BaseModel):
    """Schema for updating a finance integration."""
    credentials: Optional[FinanceIntegrationCredentials] = Field(default=None, description="Updated credentials")
    config: Optional[dict[str, Any]] = Field(default=None, description="Updated configuration")
    status: Optional[FinanceIntegrationStatus] = Field(default=None, description="Integration status")


class FinanceIntegrationResponse(BaseModel):
    """Schema for finance integration response.
    
    NOTE: Credentials are never included in responses for security.
    """
    id: int
    company_id: int
    provider_key: str
    provider_display_name: Optional[str] = None
    config: Optional[dict[str, Any]] = None
    status: FinanceIntegrationStatus
    last_tested_at: Optional[datetime] = None
    last_test_success: Optional[bool] = None
    last_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class FinanceIntegrationTestRequest(BaseModel):
    """Schema for testing a finance integration connection."""
    pass


class FinanceIntegrationTestResponse(BaseModel):
    """Schema for finance integration test result."""
    success: bool
    status: str
    message: str
    tested_at: datetime
    details: Optional[dict[str, Any]] = None


class FinanceIntegrationsListResponse(BaseModel):
    """Schema for listing finance integrations for a company."""
    integrations: list[FinanceIntegrationResponse]
    available_providers: list[FinanceProviderInfo]
