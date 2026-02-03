"""Role Profiles API endpoints."""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.crud.role_profile import RoleProfileCRUD
from app.crud.company import CompanyCRUD
from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.schema.role_profile import (
    RoleProfileSchema,
    RoleProfileListResponse,
    RoleProfileFilteredResponse,
)
from app.schema.user import CurrentUserSchema

logger = logging.getLogger(__name__)
role_profiles_router = APIRouter()


@role_profiles_router.get(
    "/",
    response_model=RoleProfileListResponse,
    summary="List all active role profiles",
    description="Retrieve all active role profiles."
)
async def list_role_profiles(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> RoleProfileListResponse:
    """List all active role profiles."""
    crud = RoleProfileCRUD(db_session)
    profiles = crud.get_active_profiles()
    return RoleProfileListResponse(
        items=[RoleProfileSchema.model_validate(p) for p in profiles]
    )


@role_profiles_router.get(
    "/by-company-type/{company_type_key}",
    response_model=RoleProfileFilteredResponse,
    summary="Get role profiles for a company type",
    description="Retrieve role profiles applicable to a specific company type."
)
async def get_profiles_for_company_type(
    company_type_key: str,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> RoleProfileFilteredResponse:
    """Get role profiles applicable to a specific company type."""
    crud = RoleProfileCRUD(db_session)
    profiles = crud.get_profiles_for_company_type(company_type_key)
    return RoleProfileFilteredResponse(
        company_type=company_type_key,
        profiles=[RoleProfileSchema.model_validate(p) for p in profiles]
    )


@role_profiles_router.get(
    "/by-company/{company_id}",
    response_model=RoleProfileFilteredResponse,
    summary="Get role profiles for a specific company",
    description="Retrieve role profiles applicable to a specific company based on its type."
)
async def get_profiles_for_company(
    company_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> RoleProfileFilteredResponse:
    """Get role profiles applicable to a specific company."""
    company = CompanyCRUD(db_session).get_by_id(company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found"
        )
    
    company_type_key = company.company_type.name if hasattr(company.company_type, 'name') else str(company.company_type)
    
    profile_crud = RoleProfileCRUD(db_session)
    profiles = profile_crud.get_profiles_for_company_type(company_type_key)
    
    return RoleProfileFilteredResponse(
        company_type=company_type_key,
        profiles=[RoleProfileSchema.model_validate(p) for p in profiles]
    )


@role_profiles_router.get(
    "/{profile_key}",
    response_model=RoleProfileSchema,
    summary="Get a specific role profile",
    description="Retrieve a specific role profile by its key."
)
async def get_role_profile(
    profile_key: str,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> RoleProfileSchema:
    """Get a specific role profile by key."""
    crud = RoleProfileCRUD(db_session)
    profile = crud.get_by_key(profile_key)
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Role profile '{profile_key}' not found"
        )
    return RoleProfileSchema.model_validate(profile)
