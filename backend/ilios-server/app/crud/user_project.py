"""CRUD operations on UserProject model."""

from typing import Iterable, List, Optional

from fastapi_filter.contrib.sqlalchemy import Filter
from sqlalchemy import String, and_, cast, or_

from app.crud.base_crud import BaseCRUD
from app.models.role import Role
from app.models.user import User, UserProject, CompanyRole, MembershipStatus


class UserProjectCRUD(BaseCRUD):
    """CRUD operations on UserProject model."""

    def __init__(self, db_session):
        super().__init__(model=UserProject, db_session=db_session)

    def create_items(self, items: Iterable, autocommit: bool = True):
        """Create multiple items

        :param items: dicts of items to create
        :param autocommit: bool flag to allow automatic commit or delegate to the caller
        :return: None
        """
        objects = [self.model(**item) for item in items]
        self.db_session.bulk_save_objects(objects)

        if autocommit:
            self.db_session.commit()

    def delete_items_by_composite_nonpk(self, filter_criteria: Iterable[dict], autocommit: bool = True):
        """Delete multiple items by provided criteria - list of combos of user id, site id, company id.

        :param filter_criteria: list of combos of user id, site id, company id
        :param autocommit: bool flag to allow automatic commit or delegate to the caller
        :return: count of items to delete
        """
        where_condition = or_(
            *[
                and_(
                    self.model.user_id == filter_criterion["user_id"],
                    self.model.site_id == filter_criterion["site_id"],
                    self.model.company_id == filter_criterion["company_id"],
                )
                for filter_criterion in filter_criteria
            ]
        )

        deleted_count = self.db_session.query(self.model).filter(where_condition).delete()

        if autocommit:
            self.db_session.commit()
        return deleted_count

    def get_potential_task_assignees(
        self, module: str, search_filter: Filter | None = None, company_id: int = None, site_id: int = None
    ):
        query = self.db_session.query(
            UserProject.id.label("project_id"), User.id, User.first_name, User.last_name, User.role_id
        )
        if company_id:
            query = query.filter(UserProject.company_id == company_id)
        if site_id:
            query = query.filter(UserProject.site_id == site_id)
        query = query.join(UserProject, UserProject.user_id == User.id)
        query = query.join(Role, Role.id == User.role_id)
        # filter user by module permission
        query = query.filter(cast(Role.permissions[module]["view"], String) == "true")
        # Filter only registered users
        query = query.filter(User.is_registered)
        query = query.distinct(self.model.user_id, User.first_name)
        if search_filter:
            query = search_filter.filter(query)
        query = self._add_order_by(query, User.first_name, "asc")
        return query.all()

    def get_by_user_and_site(self, user_id: int, site_id: int) -> Optional[UserProject]:
        """Get project membership by user and site."""
        return (
            self.db_session.query(self.model)
            .filter_by(user_id=user_id, site_id=site_id)
            .first()
        )

    def get_memberships_by_user(
        self,
        user_id: int,
        status: Optional[MembershipStatus] = None
    ) -> List[UserProject]:
        """Get all project memberships for a user."""
        query = self.db_session.query(self.model).filter_by(user_id=user_id)
        if status:
            query = query.filter_by(status=status)
        return query.all()

    def get_memberships_by_site(
        self,
        site_id: Optional[int] = None,
        company_id: Optional[int] = None,
        status: Optional[MembershipStatus] = None
    ) -> List[UserProject]:
        """Get all user memberships for a site/project or company."""
        query = self.db_session.query(self.model)
        if site_id:
            query = query.filter_by(site_id=site_id)
        if company_id:
            query = query.filter_by(company_id=company_id)
        if status:
            query = query.filter_by(status=status)
        return query.all()

    def validate_company_id_integrity(self, site_id: int, company_id: int) -> bool:
        """Validate that company_id matches the site's actual company_id.
        
        INVARIANT: UserProject.company_id MUST equal sites.company_id
        """
        from app.models.site import Site
        site = self.db_session.query(Site).get(site_id)
        if not site:
            raise ValueError(f"Site {site_id} not found")
        if site.company_id != company_id:
            raise ValueError(
                f"company_id mismatch: UserProject.company_id ({company_id}) "
                f"does not match Site.company_id ({site.company_id})"
            )
        return True

    def add_membership(
        self,
        user_id: int,
        site_id: int,
        company_id: int,
        role: CompanyRole = CompanyRole.contributor,
        status: MembershipStatus = MembershipStatus.active,
        created_by_user_id: Optional[int] = None
    ) -> UserProject:
        """Add a user to a project with specified role.
        
        Enforces INV-1: UserProject.company_id MUST equal sites.company_id
        """
        self.validate_company_id_integrity(site_id, company_id)
        return self.create_item({
            "user_id": user_id,
            "site_id": site_id,
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
        """Update a project membership's role."""
        return self.update_by_id(membership_id, {"role": role})

    def update_membership_status(
        self,
        membership_id: int,
        status: MembershipStatus
    ) -> int:
        """Update a project membership's status."""
        return self.update_by_id(membership_id, {"status": status})

    def update_membership_company_id(
        self,
        membership_id: int,
        company_id: int
    ) -> int:
        """Update a project membership's company_id.
        
        Enforces INV-1: UserProject.company_id MUST equal sites.company_id
        """
        membership = self.get_by_id(membership_id)
        if membership:
            self.validate_company_id_integrity(membership.site_id, company_id)
        return self.update_by_id(membership_id, {"company_id": company_id})

    def has_project_access(self, user_id: int, site_id: int) -> bool:
        """Check if user has active access to the given project."""
        membership = self.get_by_user_and_site(user_id, site_id)
        return membership is not None and membership.status == MembershipStatus.active

    def is_project_admin(self, user_id: int, site_id: int) -> bool:
        """Check if user is an admin of the given project."""
        membership = self.get_by_user_and_site(user_id, site_id)
        return (
            membership is not None
            and membership.status == MembershipStatus.active
            and membership.role == CompanyRole.company_admin
        )
