"""Pydantic schemas for Contact CRUD operations."""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator


class ContactScopeType:
    PORTFOLIO = "portfolio"
    COMPANY = "company"
    PROJECT = "project"


class ContactBase(BaseModel):
    """Base contact schema with common fields."""
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    title: Optional[str] = Field(None, max_length=100)
    organization: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if v is not None:
            v = v.strip()
            if v and '@' not in v:
                raise ValueError('Invalid email format')
        return v or None


class ContactCreate(ContactBase):
    """Schema for creating a new contact."""
    scope_type: str = Field(..., pattern="^(portfolio|company|project)$")
    portfolio_id: Optional[int] = None
    company_id: Optional[int] = None
    project_id: Optional[int] = None
    entity_id: Optional[int] = None
    
    @field_validator('scope_type')
    @classmethod
    def validate_scope_type(cls, v):
        if v not in ['portfolio', 'company', 'project']:
            raise ValueError('scope_type must be portfolio, company, or project')
        return v


class ContactUpdate(BaseModel):
    """Schema for updating an existing contact."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[str] = Field(None, max_length=255)
    phone: Optional[str] = Field(None, max_length=50)
    title: Optional[str] = Field(None, max_length=100)
    organization: Optional[str] = Field(None, max_length=200)
    notes: Optional[str] = None
    tags: Optional[List[str]] = None
    is_archived: Optional[bool] = None
    
    @field_validator('email')
    @classmethod
    def validate_email(cls, v):
        if v is not None:
            v = v.strip()
            if v and '@' not in v:
                raise ValueError('Invalid email format')
        return v or None


class ContactResponse(ContactBase):
    """Response schema for a contact with computed fields."""
    id: int
    scope_type: str
    portfolio_id: Optional[int] = None
    company_id: Optional[int] = None
    project_id: Optional[int] = None
    entity_id: Optional[int] = None
    is_archived: bool = False
    is_user: bool = False
    matched_user_id: Optional[int] = None
    created_by_user_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


class ContactListResponse(BaseModel):
    """Paginated list of contacts."""
    items: List[ContactResponse]
    total: int
    page: int
    page_size: int
    has_more: bool
