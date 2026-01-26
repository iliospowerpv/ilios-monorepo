"""API Schema for accessible entities endpoint (context bar)."""

from typing import List

from pydantic import BaseModel, ConfigDict, Field


class AccessibleCompanySchema(BaseModel):
    """Minimal company info for context bar picker."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(examples=[1])
    name: str = Field(examples=["Green Lantern"])


class AccessibleProjectSchema(BaseModel):
    """Minimal project (site) info for context bar picker."""
    
    model_config = ConfigDict(from_attributes=True)
    
    id: int = Field(examples=[1])
    name: str = Field(examples=["Apollo Solar Farm"])
    company_id: int = Field(examples=[1])
    company_name: str = Field(examples=["Green Lantern"])


class AccessibleEntitiesResponse(BaseModel):
    """Response containing all accessible companies and projects for a user."""
    
    companies: List[AccessibleCompanySchema] = Field(default_factory=list)
    projects: List[AccessibleProjectSchema] = Field(default_factory=list)
