"""API Schema for roles-related Endpoints"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field

from app.schema.common import SuccessUpdateSchema
from app.schema.paginator import BasePaginator
from app.static.companies import CompanyTypes


class UpsertRoleSchema(BaseModel):
    """Role upsert schema (upsert = insert + update)."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(examples=["Bank Specialist"])
    description: Optional[str] = Field(examples=["Bank"], default=None)


class Role(UpsertRoleSchema):
    id: int = Field(examples=[1])
    created_at: datetime = Field(examples=["2024-02-06T10:54:35.531977"])
    updated_at: datetime = Field(examples=["2024-02-06T10:54:35.531977"])


class RoleWithPermissions(Role):
    permissions: Dict[str, Dict[str, bool]] = Field(examples=[{"Finance": {"view": True, "edit": False}}])


class RoleSettingsSchema(RoleWithPermissions):
    company_type: Optional[str] = Field(None, examples=["Bank"])


class RolesPaginator(BasePaginator):
    items: List[RoleSettingsSchema]


class RoleCreationSuccess(BaseModel):
    message: str = Field(description="Success message", examples=["Role has been created"])
    code: int = Field(description="Success status code", examples=[201])


class RoleUpdateSuccess(SuccessUpdateSchema):
    message: str = Field(description="Success message", examples=["Role has been updated"])


class RolePermissionsUpdateSuccess(SuccessUpdateSchema):
    message: str = Field(description="Success message", examples=["Role's permissions have been updated"])


class RoleShortenedSchema(BaseModel):

    id: int = Field(examples=[1])
    name: str = Field(examples=["Executive"])


class CompanyTypeRolesMappingSchema(BaseModel):
    company_type: CompanyTypes
    role: RoleShortenedSchema


class CompanyTypeRolesMappingResponseSchema(BaseModel):

    data: list[CompanyTypeRolesMappingSchema]
