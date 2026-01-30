"""Portfolio hub boundary helpers.

This module provides utilities for working with portfolio hub boundaries.
A portfolio is a group of companies that share the same hub.

Key concepts:
- portfolio_hub_id = NULL means the company is its own hub (implicit hub = company.id)
- portfolio_hub_id = X means the company belongs to hub company X
- Users can have portfolio access to specific hubs via UserPortfolioAccess.portfolio_hub_company_id
"""

from typing import List, Optional, Set

from sqlalchemy.orm import Session

from app.models.company import Company
from app.models.user import MembershipStatus, User, UserPortfolioAccess


def resolve_company_hub_id(db_session: Session, company_id: int) -> Optional[int]:
    """Get the hub ID for a company by its ID.
    
    Args:
        db_session: Database session
        company_id: Company ID to resolve hub for
        
    Returns:
        Hub company ID, or None if company not found.
        If company.portfolio_hub_id is set, returns that.
        Otherwise, the company is its own hub, so returns company.id.
    """
    company = db_session.query(Company).get(company_id)
    if not company:
        return None
    return company.portfolio_hub_id if company.portfolio_hub_id is not None else company.id


def resolve_company_hub_id_from_model(company: Company) -> int:
    """Get the hub ID for a company object.
    
    If company.portfolio_hub_id is set, returns that.
    Otherwise, the company is its own hub, so returns company.id.
    """
    return company.portfolio_hub_id if company.portfolio_hub_id is not None else company.id


def get_portfolio_group_company_ids(db_session: Session, hub_id: int) -> List[int]:
    """Get all company IDs in the portfolio group for a given hub.
    
    Args:
        db_session: Database session
        hub_id: The hub company ID
    
    Returns IDs of:
    - The hub company itself
    - All companies with portfolio_hub_id = hub_id
    """
    companies = db_session.query(Company).filter(
        (Company.portfolio_hub_id == hub_id) | (Company.id == hub_id)
    ).all()
    return [c.id for c in companies]


def get_user_accessible_hub_ids(user_id: int, db_session: Session) -> Set[int]:
    """Get all portfolio hub IDs a user has active access to.
    
    Returns a set of hub company IDs the user can access via UserPortfolioAccess.
    """
    accesses = db_session.query(UserPortfolioAccess).filter(
        UserPortfolioAccess.user_id == user_id,
        UserPortfolioAccess.status == MembershipStatus.active,
        UserPortfolioAccess.portfolio_hub_company_id.isnot(None)
    ).all()
    return {a.portfolio_hub_company_id for a in accesses}


def get_user_portfolio_companies(user_id: int, db_session: Session) -> List[Company]:
    """Get all companies accessible to a user via their portfolio access.
    
    Returns companies from all portfolio hubs the user has active access to.
    """
    hub_ids = get_user_accessible_hub_ids(user_id, db_session)
    if not hub_ids:
        return []
    
    companies = db_session.query(Company).filter(
        (Company.portfolio_hub_id.in_(hub_ids)) | (Company.id.in_(hub_ids))
    ).order_by(Company.name).all()
    return companies


def user_has_portfolio_access_to_company(
    user_id: int,
    company_id: int,
    db_session: Session
) -> bool:
    """Check if user has portfolio-level access to a specific company.
    
    Returns True if the company is in a portfolio hub the user has access to.
    """
    company = db_session.query(Company).get(company_id)
    if not company:
        return False
    
    company_hub_id = resolve_company_hub_id_from_model(company)
    user_hub_ids = get_user_accessible_hub_ids(user_id, db_session)
    
    return company_hub_id in user_hub_ids


def get_portfolio_access_for_company(
    user_id: int,
    company_id: int,
    db_session: Session
) -> Optional[UserPortfolioAccess]:
    """Get the UserPortfolioAccess record that grants access to a company, if any."""
    company = db_session.query(Company).get(company_id)
    if not company:
        return None
    
    company_hub_id = resolve_company_hub_id_from_model(company)
    
    return db_session.query(UserPortfolioAccess).filter(
        UserPortfolioAccess.user_id == user_id,
        UserPortfolioAccess.portfolio_hub_company_id == company_hub_id,
        UserPortfolioAccess.status == MembershipStatus.active
    ).first()
