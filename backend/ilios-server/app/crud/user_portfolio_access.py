"""CRUD operations on UserPortfolioAccess model."""

from typing import List, Optional, Set

from app.crud.base_crud import BaseCRUD
from app.models.user import UserPortfolioAccess, CompanyRole, MembershipStatus


class UserPortfolioAccessCRUD(BaseCRUD):
    """CRUD operations on UserPortfolioAccess model."""

    def __init__(self, db_session):
        super().__init__(model=UserPortfolioAccess, db_session=db_session)

    def get_by_user(self, user_id: int) -> Optional[UserPortfolioAccess]:
        """Get first portfolio access by user (legacy - use get_all_by_user for hub-scoped)."""
        return (
            self.db_session.query(self.model)
            .filter_by(user_id=user_id)
            .first()
        )
    
    def get_all_by_user(self, user_id: int, status: Optional[MembershipStatus] = None) -> List[UserPortfolioAccess]:
        """Get all portfolio access records for a user (supports multiple hubs)."""
        query = self.db_session.query(self.model).filter_by(user_id=user_id)
        if status:
            query = query.filter_by(status=status)
        return query.all()
    
    def get_by_user_and_hub(self, user_id: int, hub_company_id: int) -> Optional[UserPortfolioAccess]:
        """Get portfolio access for a specific user and hub."""
        return (
            self.db_session.query(self.model)
            .filter_by(user_id=user_id, portfolio_hub_company_id=hub_company_id)
            .first()
        )
    
    def get_user_hub_ids(self, user_id: int) -> Set[int]:
        """Get all hub company IDs the user has active access to."""
        accesses = self.db_session.query(self.model).filter(
            self.model.user_id == user_id,
            self.model.status == MembershipStatus.active,
            self.model.portfolio_hub_company_id.isnot(None)
        ).all()
        return {a.portfolio_hub_company_id for a in accesses}

    def get_all_portfolio_users(
        self,
        status: Optional[MembershipStatus] = None,
        hub_company_id: Optional[int] = None
    ) -> List[UserPortfolioAccess]:
        """Get all users with portfolio-level access, optionally filtered by hub."""
        query = self.db_session.query(self.model)
        if status:
            query = query.filter_by(status=status)
        if hub_company_id:
            query = query.filter_by(portfolio_hub_company_id=hub_company_id)
        return query.all()

    def add_portfolio_access(
        self,
        user_id: int,
        portfolio_hub_company_id: int,
        role: CompanyRole = CompanyRole.contributor,
        status: MembershipStatus = MembershipStatus.active,
        created_by_user_id: Optional[int] = None
    ) -> UserPortfolioAccess:
        """Grant a user portfolio-level access to a specific hub."""
        return self.create_item({
            "user_id": user_id,
            "portfolio_hub_company_id": portfolio_hub_company_id,
            "role": role,
            "status": status,
            "created_by_user_id": created_by_user_id
        })

    def update_role(
        self,
        access_id: int,
        role: CompanyRole
    ) -> int:
        """Update a portfolio access role."""
        return self.update_by_id(access_id, {"role": role})

    def update_status(
        self,
        access_id: int,
        status: MembershipStatus
    ) -> int:
        """Update a portfolio access status."""
        return self.update_by_id(access_id, {"status": status})

    def has_portfolio_access(self, user_id: int, hub_company_id: Optional[int] = None) -> bool:
        """Check if user has active portfolio-level access (to a specific hub if provided)."""
        if hub_company_id:
            access = self.get_by_user_and_hub(user_id, hub_company_id)
            return access is not None and access.status == MembershipStatus.active
        accesses = self.get_all_by_user(user_id, status=MembershipStatus.active)
        return len(accesses) > 0

    def is_portfolio_admin(self, user_id: int, hub_company_id: Optional[int] = None) -> bool:
        """Check if user is a portfolio admin (for a specific hub if provided)."""
        if hub_company_id:
            access = self.get_by_user_and_hub(user_id, hub_company_id)
            return (
                access is not None
                and access.status == MembershipStatus.active
                and access.role == CompanyRole.company_admin
            )
        accesses = self.get_all_by_user(user_id, status=MembershipStatus.active)
        return any(a.role == CompanyRole.company_admin for a in accesses)

    def remove_portfolio_access(self, user_id: int, hub_company_id: Optional[int] = None) -> int:
        """Remove portfolio-level access for a user (from specific hub if provided)."""
        if hub_company_id:
            access = self.get_by_user_and_hub(user_id, hub_company_id)
            if access:
                return self.delete_by_id(access.id)
            return 0
        accesses = self.get_all_by_user(user_id)
        deleted = 0
        for access in accesses:
            deleted += self.delete_by_id(access.id)
        return deleted
