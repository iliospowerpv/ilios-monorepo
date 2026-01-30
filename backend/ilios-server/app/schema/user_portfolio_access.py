"""API Schema for user portfolio access management."""

from datetime import datetime
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field

from app.schema.user_company_access import CompanyRoleEnum, MembershipStatusEnum


class UserPortfolioAccessBase(BaseModel):
    """Base schema for user portfolio access."""
    user_id: int = Field(..., examples=[1])
    portfolio_hub_company_id: int = Field(..., examples=[1], description="The hub company ID this access grants access to")
    role: CompanyRoleEnum = Field(default=CompanyRoleEnum.contributor)


class UserPortfolioAccessCreate(UserPortfolioAccessBase):
    """Schema for creating a new user portfolio access."""
    pass


class UserPortfolioAccessUpdate(BaseModel):
    """Schema for updating user portfolio access."""
    role: Optional[CompanyRoleEnum] = None
    status: Optional[MembershipStatusEnum] = None


class UserPortfolioAccessSchema(UserPortfolioAccessBase):
    """Full schema for user portfolio access with all fields."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(examples=[1])
    status: MembershipStatusEnum = Field(default=MembershipStatusEnum.active)
    created_at: Optional[datetime] = None
    created_by_user_id: Optional[int] = None
    updated_at: Optional[datetime] = None


class PortfolioHubSchema(BaseModel):
    """Schema for a portfolio hub company."""
    model_config = ConfigDict(from_attributes=True)
    
    hub_company_id: int = Field(examples=[1])
    hub_company_name: str = Field(examples=["Acme Portfolio"])
    companies_count: int = Field(examples=[5])


class PortfolioMemberSchema(BaseModel):
    """Schema for a portfolio member in the member list."""
    model_config = ConfigDict(from_attributes=True)
    
    access_id: int = Field(examples=[1])
    user_id: int = Field(examples=[1])
    email: str = Field(examples=["user@example.com"])
    first_name: str = Field(examples=["John"])
    last_name: str = Field(examples=["Doe"])
    role: CompanyRoleEnum = Field(examples=[CompanyRoleEnum.contributor])
    status: MembershipStatusEnum = Field(examples=[MembershipStatusEnum.active])
    portfolio_hub_company_id: Optional[int] = Field(None, examples=[1])
    portfolio_hub_company_name: Optional[str] = Field(None, examples=["Acme Portfolio"])


class PortfolioMembersListSchema(BaseModel):
    """Schema for list of portfolio members."""
    members: List[PortfolioMemberSchema]
    total: int = Field(examples=[10])


class AvailableHubsSchema(BaseModel):
    """Schema for available portfolio hubs."""
    hubs: List[PortfolioHubSchema]
