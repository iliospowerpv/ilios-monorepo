"""CRUD operations on UserPortfolioAccess model."""

from typing import List, Optional

from app.crud.base_crud import BaseCRUD
from app.models.user import UserPortfolioAccess, CompanyRole, MembershipStatus


class UserPortfolioAccessCRUD(BaseCRUD):
    """CRUD operations on UserPortfolioAccess model."""

    def __init__(self, db_session):
        super().__init__(model=UserPortfolioAccess, db_session=db_session)

    def get_by_user(self, user_id: int) -> Optional[UserPortfolioAccess]:
        """Get portfolio access by user. Returns None if user doesn't have portfolio access."""
        return (
            self.db_session.query(self.model)
            .filter_by(user_id=user_id)
            .first()
        )

    def get_all_portfolio_users(
        self,
        status: Optional[MembershipStatus] = None
    ) -> List[UserPortfolioAccess]:
        """Get all users with portfolio-level access."""
        query = self.db_session.query(self.model)
        if status:
            query = query.filter_by(status=status)
        return query.all()

    def add_portfolio_access(
        self,
        user_id: int,
        role: CompanyRole = CompanyRole.contributor,
        status: MembershipStatus = MembershipStatus.active,
        created_by_user_id: Optional[int] = None
    ) -> UserPortfolioAccess:
        """Grant a user portfolio-level access with specified role."""
        return self.create_item({
            "user_id": user_id,
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

    def has_portfolio_access(self, user_id: int) -> bool:
        """Check if user has active portfolio-level access."""
        access = self.get_by_user(user_id)
        return access is not None and access.status == MembershipStatus.active

    def is_portfolio_admin(self, user_id: int) -> bool:
        """Check if user is a portfolio admin."""
        access = self.get_by_user(user_id)
        return (
            access is not None
            and access.status == MembershipStatus.active
            and access.role == CompanyRole.company_admin
        )

    def remove_portfolio_access(self, user_id: int) -> int:
        """Remove portfolio-level access for a user."""
        access = self.get_by_user(user_id)
        if access:
            return self.delete_by_id(access.id)
        return 0
