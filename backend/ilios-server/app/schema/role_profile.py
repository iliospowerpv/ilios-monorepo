"""API Schema for role profiles management."""

from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ModulePermission(BaseModel):
    """Module permission definition."""
    view: bool = Field(default=False)
    edit: bool = Field(default=False)


class RoleProfileBase(BaseModel):
    """Base schema for role profiles."""
    key: str = Field(..., examples=["asset_manager"], max_length=50)
    label: str = Field(..., examples=["Asset Manager"], max_length=100)
    description: Optional[str] = Field(None, examples=["Manages asset portfolio"])
    applicable_company_types: Optional[List[str]] = Field(
        None, 
        examples=[["project_site_owner", "operation_maintenance_contractor"]],
        description="Company type KEYS this profile applies to. Null = all types."
    )
    default_module_permissions: Dict[str, Dict[str, bool]] = Field(
        default_factory=dict,
        examples=[{
            "assets_management": {"view": True, "edit": True},
            "diligence": {"view": True, "edit": False}
        }]
    )
    default_dashboard_key: Optional[str] = Field(None, examples=["default"])


class RoleProfileCreate(RoleProfileBase):
    """Schema for creating a new role profile."""
    pass


class RoleProfileUpdate(BaseModel):
    """Schema for updating a role profile."""
    label: Optional[str] = None
    description: Optional[str] = None
    applicable_company_types: Optional[List[str]] = None
    default_module_permissions: Optional[Dict[str, Dict[str, bool]]] = None
    default_dashboard_key: Optional[str] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None


class RoleProfileSchema(RoleProfileBase):
    """Full schema for role profile with all fields."""
    model_config = ConfigDict(from_attributes=True)
    
    is_active: bool = Field(default=True)
    display_order: int = Field(default=0)


class RoleProfileListResponse(BaseModel):
    """Response schema for list of role profiles."""
    items: List[RoleProfileSchema]


class RoleProfileFilteredResponse(BaseModel):
    """Response schema for role profiles filtered by company type."""
    company_type: str = Field(..., examples=["project_site_owner"])
    profiles: List[RoleProfileSchema]
