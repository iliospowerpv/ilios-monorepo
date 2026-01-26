"""API Schema for user company access management."""

from datetime import datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field


class CompanyRoleEnum(str, Enum):
    """Role a user can have within a company."""
    company_admin = "company_admin"
    contributor = "contributor"
    read_only = "read_only"


class MembershipStatusEnum(str, Enum):
    """Status of a user's membership in a company."""
    active = "active"
    invited = "invited"
    disabled = "disabled"


class UserCompanyAccessBase(BaseModel):
    """Base schema for user company access."""
    user_id: int = Field(..., examples=[1])
    company_id: int = Field(..., examples=[1])
    role: CompanyRoleEnum = Field(default=CompanyRoleEnum.contributor)


class UserCompanyAccessCreate(UserCompanyAccessBase):
    """Schema for creating a new user company access."""
    pass


class UserCompanyAccessUpdate(BaseModel):
    """Schema for updating user company access."""
    role: Optional[CompanyRoleEnum] = None
    status: Optional[MembershipStatusEnum] = None


class UserCompanyAccessSchema(UserCompanyAccessBase):
    """Full schema for user company access with all fields."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(examples=[1])
    status: MembershipStatusEnum = Field(default=MembershipStatusEnum.active)
    created_at: Optional[datetime] = None
    created_by_user_id: Optional[int] = None
    updated_at: Optional[datetime] = None


class CompanyMemberSchema(BaseModel):
    """Schema for a company member in the member list."""
    model_config = ConfigDict(from_attributes=True)
    
    membership_id: int = Field(examples=[1])
    user_id: int = Field(examples=[1])
    email: str = Field(examples=["user@example.com"])
    first_name: str = Field(examples=["John"])
    last_name: str = Field(examples=["Doe"])
    role: CompanyRoleEnum = Field(examples=[CompanyRoleEnum.contributor])
    status: MembershipStatusEnum = Field(examples=[MembershipStatusEnum.active])
    access_source: str = Field(examples=["membership"], description="Source of access: 'membership', 'project', or 'parent_company'")


class UserCompanySchema(BaseModel):
    """Schema for a company in the user's company list."""
    model_config = ConfigDict(from_attributes=True)
    
    company_id: int = Field(examples=[1])
    company_name: str = Field(examples=["Green Lantern"])
    role: Optional[CompanyRoleEnum] = Field(default=None, examples=[CompanyRoleEnum.contributor])
    access_source: str = Field(examples=["membership"], description="Source of access: 'membership', 'project', or 'parent_company'")
    project_count: int = Field(default=0, examples=[5])


class WorkspaceSummarySchema(BaseModel):
    """Summary statistics for the workspace page."""
    companies_count: int = Field(default=0, examples=[3])
    projects_count: int = Field(default=0, examples=[12])
    pending_tasks_count: int = Field(default=0, examples=[5])
    needs_attention_count: int = Field(default=0, examples=[2])


class WorkspaceResponseSchema(BaseModel):
    """Full workspace response with summary and entity lists."""
    summary: WorkspaceSummarySchema
    companies: List[UserCompanySchema]
