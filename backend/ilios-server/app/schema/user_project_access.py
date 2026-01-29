"""API Schema for user project access management."""

from datetime import datetime
from enum import Enum
from typing import Optional, List

from pydantic import BaseModel, ConfigDict, Field

from app.schema.user_company_access import CompanyRoleEnum, MembershipStatusEnum


class UserProjectAccessBase(BaseModel):
    """Base schema for user project access."""
    user_id: int = Field(..., examples=[1])
    site_id: int = Field(..., examples=[1])
    role: CompanyRoleEnum = Field(default=CompanyRoleEnum.contributor)


class UserProjectAccessCreate(BaseModel):
    """Schema for creating a new user project access."""
    user_id: int = Field(..., examples=[1])
    role: CompanyRoleEnum = Field(default=CompanyRoleEnum.contributor)


class UserProjectAccessUpdate(BaseModel):
    """Schema for updating user project access."""
    role: Optional[CompanyRoleEnum] = None
    status: Optional[MembershipStatusEnum] = None


class UserProjectAccessSchema(UserProjectAccessBase):
    """Full schema for user project access with all fields."""
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(examples=[1])
    company_id: int = Field(examples=[1])
    status: MembershipStatusEnum = Field(default=MembershipStatusEnum.active)
    created_at: Optional[datetime] = None
    created_by_user_id: Optional[int] = None
    updated_at: Optional[datetime] = None


class ProjectAccessSourceEnum(str, Enum):
    """Source of a user's access to a project."""
    direct_project = "direct_project"
    inherited_company = "inherited_company"
    inherited_portfolio = "inherited_portfolio"


class ProjectMemberSchema(BaseModel):
    """Schema for a project member in the member list."""
    model_config = ConfigDict(from_attributes=True)
    
    membership_id: Optional[int] = Field(default=None, examples=[1], description="Direct membership ID (null if inherited)")
    user_id: int = Field(examples=[1])
    email: str = Field(examples=["user@example.com"])
    first_name: str = Field(examples=["John"])
    last_name: str = Field(examples=["Doe"])
    access_source: ProjectAccessSourceEnum = Field(examples=[ProjectAccessSourceEnum.direct_project])
    resolved_role: CompanyRoleEnum = Field(examples=[CompanyRoleEnum.contributor], description="Effective role after precedence resolution")
    resolved_status: MembershipStatusEnum = Field(examples=[MembershipStatusEnum.active], description="Effective status")


class ProjectMembersListSchema(BaseModel):
    """Schema for list of project members."""
    members: List[ProjectMemberSchema]
    total: int = Field(examples=[10])


class ProjectWithCompanyContextSchema(BaseModel):
    """Schema for project info including parent company context."""
    model_config = ConfigDict(from_attributes=True)
    
    project_id: int = Field(examples=[1])
    project_name: str = Field(examples=["Solar Park Alpha"])
    company_id: int = Field(examples=[1])
    company_name: str = Field(examples=["Green Lantern"])
    role: CompanyRoleEnum = Field(examples=[CompanyRoleEnum.contributor])
    status: MembershipStatusEnum = Field(examples=[MembershipStatusEnum.active])
