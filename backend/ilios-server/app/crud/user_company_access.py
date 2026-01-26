"""CRUD operations on UserCompanyAccess model."""

from typing import List, Optional

from app.crud.base_crud import BaseCRUD
from app.models.user import UserCompanyAccess, CompanyRole, MembershipStatus


class UserCompanyAccessCRUD(BaseCRUD):
    """CRUD operations on UserCompanyAccess model."""

    def __init__(self, db_session):
        super().__init__(model=UserCompanyAccess, db_session=db_session)

    def get_by_user_and_company(self, user_id: int, company_id: int) -> Optional[UserCompanyAccess]:
        """Get membership by user and company."""
        return (
            self.db_session.query(self.model)
            .filter_by(user_id=user_id, company_id=company_id)
            .first()
        )

    def get_memberships_by_user(
        self,
        user_id: int,
        status: Optional[MembershipStatus] = None
    ) -> List[UserCompanyAccess]:
        """Get all company memberships for a user."""
        query = self.db_session.query(self.model).filter_by(user_id=user_id)
        if status:
            query = query.filter_by(status=status)
        return query.all()

    def get_memberships_by_company(
        self,
        company_id: int,
        status: Optional[MembershipStatus] = None
    ) -> List[UserCompanyAccess]:
        """Get all user memberships for a company."""
        query = self.db_session.query(self.model).filter_by(company_id=company_id)
        if status:
            query = query.filter_by(status=status)
        return query.all()

    def add_membership(
        self,
        user_id: int,
        company_id: int,
        role: CompanyRole = CompanyRole.contributor,
        status: MembershipStatus = MembershipStatus.active,
        created_by_user_id: Optional[int] = None
    ) -> UserCompanyAccess:
        """Add a user to a company with specified role."""
        return self.create_item({
            "user_id": user_id,
            "company_id": company_id,
            "role": role,
            "status": status,
            "created_by_user_id": created_by_user_id
        })

    def update_membership_role(
        self,
        membership_id: int,
        role: CompanyRole
    ) -> int:
        """Update a membership's role."""
        return self.update_by_id(membership_id, {"role": role})

    def update_membership_status(
        self,
        membership_id: int,
        status: MembershipStatus
    ) -> int:
        """Update a membership's status."""
        return self.update_by_id(membership_id, {"status": status})

    def is_company_admin(self, user_id: int, company_id: int) -> bool:
        """Check if user is an admin of the given company."""
        membership = self.get_by_user_and_company(user_id, company_id)
        return (
            membership is not None
            and membership.status == MembershipStatus.active
            and membership.role == CompanyRole.company_admin
        )

    def has_company_access(self, user_id: int, company_id: int) -> bool:
        """Check if user has any active access to the given company."""
        membership = self.get_by_user_and_company(user_id, company_id)
        return membership is not None and membership.status == MembershipStatus.active
