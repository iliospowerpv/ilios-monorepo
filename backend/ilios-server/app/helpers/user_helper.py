import logging

from fastapi import HTTPException, status

from app.crud.company import CompanyCRUD
from app.crud.role import RoleCRUD

logger = logging.getLogger(__name__)


class UserHelper:
    """Common operations for users handling"""

    @staticmethod
    def get_company_or_400(company_id, db_session):  # NOTE: looks like a company helper candidate
        """Get the company from db or raise 400 fastapi.HTTPException if not found"""
        company = CompanyCRUD(db_session).get_by_id(company_id)
        if not company:
            logger.warning(f"Cannot find company with id {company_id}")
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Parent company not found")
        return company

    @staticmethod
    def get_role_or_400(role_id, db_session):  # NOTE: looks like a role helper candidate
        """Get the role from db or raise 400 fastapi.HTTPException if not found"""
        role = RoleCRUD(db_session).get_by_id(role_id)
        if not role:
            logger.warning(f"Cannot find role with id {role_id}")
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Role not found")
        return role

    @staticmethod
    def validate_company_type_allows_role(company, role):
        """Validate that company allows the role"""
        if not role.related_company_type or role.related_company_type.company_type != company.company_type:
            logger.warning(
                f"Role '{role.name}'(id={role.id}) is not allowed for the company "
                f"'{company.name}'(id={company.id}) with company type '{company.company_type}'"
            )
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "This role is not allowed for chosen company type")

    @staticmethod
    def validate_company_admin_access(admin_user, parent_company_id, action):
        """Validate that company admin is creating/updating users inside own company"""
        if not admin_user.is_system_user and parent_company_id != admin_user.parent_company_id:
            logger.warning(
                f"User {admin_user.id} tried {action} user for company ID: {parent_company_id} "
                "with no admin rights for this company"
            )
            raise HTTPException(status.HTTP_403_FORBIDDEN)

    @staticmethod
    def validate_user_parent_company(current_user):
        """Check user has parent company ID, otherwise throws 404 HTTPException."""
        if not current_user.parent_company_id:
            logger.warning(f"User with ID <{current_user.id}> doesn't have a parent company ID")
            raise HTTPException(status.HTTP_404_NOT_FOUND)
