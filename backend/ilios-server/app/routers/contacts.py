"""Contacts API - CRM-style address book at portfolio/company/project levels.

Contacts are NOT users. A contact may optionally correspond to an existing user
account (computed via email match), but this is for display only and does not
grant any access or permissions.
"""

import logging
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.models.contact import Contact, ContactScopeType
from app.models.user import User, UserCompanyAccess, UserPortfolioAccess, UserProject
from app.models.company import Company
from app.models.site import Site
from app.schema.contact import (
    ContactCreate,
    ContactUpdate,
    ContactResponse,
    ContactListResponse,
)
from app.schema.user import CurrentUserSchema

contacts_router = APIRouter()
logger = logging.getLogger(__name__)


def _check_scope_access(
    db_session: Session,
    current_user: CurrentUserSchema,
    scope_type: str,
    portfolio_id: Optional[int],
    company_id: Optional[int],
    project_id: Optional[int],
    require_edit: bool = False
) -> bool:
    """Check if user has access to the given scope.
    
    For now, follows simple rules:
    - System users have full access
    - Portfolio level: must have portfolio access
    - Company level: must have company membership
    - Project level: must have project membership
    """
    if current_user.is_system_user:
        return True
    
    if scope_type == "portfolio":
        if portfolio_id is None:
            return False
        access = db_session.query(UserPortfolioAccess).filter(
            UserPortfolioAccess.user_id == current_user.id,
            UserPortfolioAccess.portfolio_hub_company_id == portfolio_id,
            UserPortfolioAccess.status == 'active'
        ).first()
        return access is not None
    
    elif scope_type == "company":
        if company_id is None:
            return False
        access = db_session.query(UserCompanyAccess).filter(
            UserCompanyAccess.user_id == current_user.id,
            UserCompanyAccess.company_id == company_id,
            UserCompanyAccess.status == 'active'
        ).first()
        return access is not None
    
    elif scope_type == "project":
        if project_id is None:
            return False
        access = db_session.query(UserProject).filter(
            UserProject.user_id == current_user.id,
            UserProject.site_id == project_id,
            UserProject.status == 'active'
        ).first()
        return access is not None
    
    return False


def _validate_scope_entity_exists(
    db_session: Session,
    scope_type: str,
    portfolio_id: Optional[int],
    company_id: Optional[int],
    project_id: Optional[int]
) -> None:
    """Validate that the scope entity (portfolio/company/project) exists."""
    if scope_type == "portfolio":
        if not portfolio_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="portfolio_id is required for portfolio scope"
            )
        portfolio = db_session.query(Company).filter(Company.id == portfolio_id).first()
        if not portfolio:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Portfolio with id {portfolio_id} not found"
            )
    
    elif scope_type == "company":
        if not company_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="company_id is required for company scope"
            )
        company = db_session.query(Company).filter(Company.id == company_id).first()
        if not company:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Company with id {company_id} not found"
            )
    
    elif scope_type == "project":
        if not project_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="project_id is required for project scope"
            )
        project = db_session.query(Site).filter(Site.id == project_id).first()
        if not project:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Project with id {project_id} not found"
            )


def _compute_is_user(db_session: Session, email_normalized: Optional[str]) -> tuple[bool, Optional[int]]:
    """Check if a contact's email matches an existing user (case-insensitive).
    
    Returns (is_user, matched_user_id).
    """
    if not email_normalized:
        return False, None
    
    matched_user = db_session.query(User).filter(
        func.lower(User.email) == email_normalized
    ).first()
    
    if matched_user:
        return True, matched_user.id
    return False, None


def _contact_to_response(db_session: Session, contact: Contact) -> ContactResponse:
    """Convert a Contact model to ContactResponse with computed fields."""
    is_user, matched_user_id = _compute_is_user(db_session, contact.email_normalized)
    
    return ContactResponse(
        id=contact.id,
        scope_type=contact.scope_type.value,
        portfolio_id=contact.portfolio_id,
        company_id=contact.company_id,
        project_id=contact.project_id,
        first_name=contact.first_name,
        last_name=contact.last_name,
        email=contact.email,
        phone=contact.phone,
        title=contact.title,
        organization=contact.organization,
        notes=contact.notes,
        tags=contact.tags or [],
        is_archived=contact.is_archived,
        is_user=is_user,
        matched_user_id=matched_user_id,
        created_by_user_id=contact.created_by_user_id,
        created_at=contact.created_at,
        updated_at=contact.updated_at,
    )


@contacts_router.get(
    "",
    response_model=ContactListResponse,
    summary="List contacts for a scope",
    description="Get contacts at a specific scope (portfolio, company, or project). "
                "Returns exact-scope contacts only - no cascading/inheritance."
)
async def list_contacts(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
    scope_type: str = Query(..., pattern="^(portfolio|company|project)$"),
    portfolio_id: Optional[int] = Query(None),
    company_id: Optional[int] = Query(None),
    project_id: Optional[int] = Query(None),
    q: Optional[str] = Query(None, description="Search query for name/email/organization/title"),
    include_archived: bool = Query(False),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
) -> ContactListResponse:
    """List contacts at a specific scope level."""
    if not _check_scope_access(db_session, current_user, scope_type, portfolio_id, company_id, project_id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this scope"
        )
    
    query = db_session.query(Contact).filter(
        Contact.scope_type == ContactScopeType(scope_type)
    )
    
    if scope_type == "portfolio":
        query = query.filter(Contact.portfolio_id == portfolio_id)
    elif scope_type == "company":
        query = query.filter(Contact.company_id == company_id)
    elif scope_type == "project":
        query = query.filter(Contact.project_id == project_id)
    
    if not include_archived:
        query = query.filter(Contact.is_archived == False)
    
    if q:
        search_term = f"%{q.lower()}%"
        query = query.filter(
            or_(
                func.lower(Contact.first_name).like(search_term),
                func.lower(Contact.last_name).like(search_term),
                func.lower(Contact.email).like(search_term),
                func.lower(Contact.organization).like(search_term),
                func.lower(Contact.title).like(search_term),
            )
        )
    
    total = query.count()
    
    offset = (page - 1) * page_size
    contacts = query.order_by(Contact.last_name, Contact.first_name).offset(offset).limit(page_size).all()
    
    items = [_contact_to_response(db_session, c) for c in contacts]
    
    return ContactListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        has_more=(offset + len(contacts)) < total
    )


@contacts_router.post(
    "",
    response_model=ContactResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new contact",
    description="Create a new contact at a specific scope."
)
async def create_contact(
    contact_data: ContactCreate,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> ContactResponse:
    """Create a new contact."""
    _validate_scope_entity_exists(
        db_session, 
        contact_data.scope_type, 
        contact_data.portfolio_id, 
        contact_data.company_id, 
        contact_data.project_id
    )
    
    if not _check_scope_access(
        db_session, 
        current_user, 
        contact_data.scope_type, 
        contact_data.portfolio_id, 
        contact_data.company_id, 
        contact_data.project_id,
        require_edit=True
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to create contacts in this scope"
        )
    
    email_normalized = Contact.normalize_email(contact_data.email)
    
    if email_normalized:
        existing_query = db_session.query(Contact).filter(
            Contact.scope_type == ContactScopeType(contact_data.scope_type),
            Contact.email_normalized == email_normalized,
            Contact.is_archived == False
        )
        
        if contact_data.scope_type == "portfolio":
            existing_query = existing_query.filter(Contact.portfolio_id == contact_data.portfolio_id)
        elif contact_data.scope_type == "company":
            existing_query = existing_query.filter(Contact.company_id == contact_data.company_id)
        elif contact_data.scope_type == "project":
            existing_query = existing_query.filter(Contact.project_id == contact_data.project_id)
        
        if existing_query.first():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"A contact with email '{contact_data.email}' already exists in this scope"
            )
    
    contact = Contact(
        scope_type=ContactScopeType(contact_data.scope_type),
        portfolio_id=contact_data.portfolio_id if contact_data.scope_type == "portfolio" else None,
        company_id=contact_data.company_id if contact_data.scope_type == "company" else None,
        project_id=contact_data.project_id if contact_data.scope_type == "project" else None,
        first_name=contact_data.first_name,
        last_name=contact_data.last_name,
        email=contact_data.email,
        email_normalized=email_normalized,
        phone=contact_data.phone,
        title=contact_data.title,
        organization=contact_data.organization,
        notes=contact_data.notes,
        tags=contact_data.tags,
        created_by_user_id=current_user.id,
    )
    
    db_session.add(contact)
    db_session.commit()
    db_session.refresh(contact)
    
    logger.info(f"Contact {contact.id} created by user {current_user.id} in {contact_data.scope_type} scope")
    
    return _contact_to_response(db_session, contact)


@contacts_router.get(
    "/{contact_id}",
    response_model=ContactResponse,
    summary="Get a contact by ID"
)
async def get_contact(
    contact_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> ContactResponse:
    """Get a single contact by ID."""
    contact = db_session.query(Contact).filter(Contact.id == contact_id).first()
    
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact with id {contact_id} not found"
        )
    
    if not _check_scope_access(
        db_session, 
        current_user, 
        contact.scope_type.value, 
        contact.portfolio_id, 
        contact.company_id, 
        contact.project_id
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this contact"
        )
    
    return _contact_to_response(db_session, contact)


@contacts_router.put(
    "/{contact_id}",
    response_model=ContactResponse,
    summary="Update a contact"
)
async def update_contact(
    contact_id: int,
    contact_data: ContactUpdate,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> ContactResponse:
    """Update an existing contact. Scope cannot be changed."""
    contact = db_session.query(Contact).filter(Contact.id == contact_id).first()
    
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact with id {contact_id} not found"
        )
    
    if not _check_scope_access(
        db_session, 
        current_user, 
        contact.scope_type.value, 
        contact.portfolio_id, 
        contact.company_id, 
        contact.project_id,
        require_edit=True
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to edit this contact"
        )
    
    update_data = contact_data.model_dump(exclude_unset=True)
    
    if 'email' in update_data:
        new_email = update_data['email']
        new_email_normalized = Contact.normalize_email(new_email)
        
        if new_email_normalized and new_email_normalized != contact.email_normalized:
            existing_query = db_session.query(Contact).filter(
                Contact.id != contact_id,
                Contact.scope_type == contact.scope_type,
                Contact.email_normalized == new_email_normalized,
                Contact.is_archived == False
            )
            
            if contact.scope_type == ContactScopeType.portfolio:
                existing_query = existing_query.filter(Contact.portfolio_id == contact.portfolio_id)
            elif contact.scope_type == ContactScopeType.company:
                existing_query = existing_query.filter(Contact.company_id == contact.company_id)
            elif contact.scope_type == ContactScopeType.project:
                existing_query = existing_query.filter(Contact.project_id == contact.project_id)
            
            if existing_query.first():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"A contact with email '{new_email}' already exists in this scope"
                )
        
        update_data['email_normalized'] = new_email_normalized
    
    for field, value in update_data.items():
        setattr(contact, field, value)
    
    db_session.commit()
    db_session.refresh(contact)
    
    logger.info(f"Contact {contact.id} updated by user {current_user.id}")
    
    return _contact_to_response(db_session, contact)


@contacts_router.delete(
    "/{contact_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Archive a contact (soft delete)"
)
async def delete_contact(
    contact_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
) -> None:
    """Soft delete (archive) a contact."""
    contact = db_session.query(Contact).filter(Contact.id == contact_id).first()
    
    if not contact:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contact with id {contact_id} not found"
        )
    
    if not _check_scope_access(
        db_session, 
        current_user, 
        contact.scope_type.value, 
        contact.portfolio_id, 
        contact.company_id, 
        contact.project_id,
        require_edit=True
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to delete this contact"
        )
    
    contact.is_archived = True
    db_session.commit()
    
    logger.info(f"Contact {contact.id} archived by user {current_user.id}")
