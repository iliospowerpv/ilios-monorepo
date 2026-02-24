"""Pydantic schemas for the Project Entity Directory system."""

from datetime import date, datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.static.entities import DealEntityRole, EntityRelationshipRole, EntityType


class ProjectEntityCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    entity_type: EntityType
    portfolio_id: int
    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=255)
    state: Optional[str] = Field(None, max_length=50)
    zip_code: Optional[str] = Field(None, max_length=20)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    website: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None
    linked_company_id: Optional[int] = None


class ProjectEntityUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    entity_type: Optional[EntityType] = None
    address: Optional[str] = Field(None, max_length=500)
    city: Optional[str] = Field(None, max_length=255)
    state: Optional[str] = Field(None, max_length=50)
    zip_code: Optional[str] = Field(None, max_length=20)
    phone: Optional[str] = Field(None, max_length=50)
    email: Optional[str] = Field(None, max_length=255)
    website: Optional[str] = Field(None, max_length=500)
    notes: Optional[str] = None
    linked_company_id: Optional[int] = None
    is_active: Optional[bool] = None


class ProjectEntityResponse(BaseModel):
    id: int
    portfolio_id: int
    name: str
    entity_type: EntityType
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    website: Optional[str] = None
    notes: Optional[str] = None
    is_active: bool
    linked_company_id: Optional[int] = None
    linked_company_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectEntityListResponse(BaseModel):
    items: List[ProjectEntityResponse]
    total: int
    page: int
    page_size: int
    has_more: bool


class EntityRelationshipCreate(BaseModel):
    entity_id: int
    role: EntityRelationshipRole
    contact_id: Optional[int] = None
    effective_date: Optional[date] = None
    termination_date: Optional[date] = None
    notes: Optional[str] = None


class EntityRelationshipUpdate(BaseModel):
    entity_id: Optional[int] = None
    role: Optional[EntityRelationshipRole] = None
    contact_id: Optional[int] = None
    effective_date: Optional[date] = None
    termination_date: Optional[date] = None
    notes: Optional[str] = None


class EntityRelationshipResponse(BaseModel):
    id: int
    site_id: int
    entity_id: int
    role: EntityRelationshipRole
    contact_id: Optional[int] = None
    effective_date: Optional[date] = None
    termination_date: Optional[date] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    entity_name: Optional[str] = None
    entity_type: Optional[EntityType] = None
    contact_name: Optional[str] = None

    class Config:
        from_attributes = True


class EntityRelationshipListResponse(BaseModel):
    items: List[EntityRelationshipResponse]
    total: int


class DealEntityAssignmentCreate(BaseModel):
    entity_id: int
    role: DealEntityRole
    contact_id: Optional[int] = None


class DealEntityAssignmentUpdate(BaseModel):
    entity_id: Optional[int] = None
    role: Optional[DealEntityRole] = None
    contact_id: Optional[int] = None


class DealEntityAssignmentResponse(BaseModel):
    id: int
    deal_id: int
    entity_id: int
    role: DealEntityRole
    contact_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    entity_name: Optional[str] = None
    entity_type: Optional[EntityType] = None
    contact_name: Optional[str] = None

    class Config:
        from_attributes = True


class DealEntityAssignmentListResponse(BaseModel):
    items: List[DealEntityAssignmentResponse]
    total: int


class EntityAssignmentSummary(BaseModel):
    relationship_id: int
    site_id: int
    site_name: str
    role: EntityRelationshipRole
    effective_date: Optional[date] = None
    termination_date: Optional[date] = None

    class Config:
        from_attributes = True


class EntityAssignmentsSummaryResponse(BaseModel):
    items: List[EntityAssignmentSummary]
    total: int
