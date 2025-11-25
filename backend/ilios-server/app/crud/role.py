from sqlalchemy import and_, case, or_
from sqlalchemy.orm import Session

from app.db.base import Role
from app.static import DEFAULT_PAGINATION_LIMIT, DEFAULT_PAGINATION_SKIP

from ..models.role import CompanyTypeRoleMapping
from ..static.companies import CompanyTypes
from .base_crud import BaseCRUD


class RoleCRUD(BaseCRUD):
    """CRUD operations on Role model."""

    def __init__(self, db_session: Session):
        super().__init__(model=Role, db_session=db_session)

    def delete_by_name(self, role_name: str):
        deleted_count = self.db_session.query(self.model).filter_by(name=role_name).delete()
        if deleted_count == 0:
            return deleted_count  # nothing to commit, return early
        self.db_session.commit()
        return deleted_count

    def get_roles(self, skip: int = DEFAULT_PAGINATION_SKIP, limit: int = DEFAULT_PAGINATION_LIMIT):
        """Retrieve roles list together with the company type role attached to"""
        query = self.db_session.query(
            self.model.id,
            self.model.created_at,
            self.model.updated_at,
            self.model.name,
            self.model.description,
            self.model.permissions,
            CompanyTypeRoleMapping.company_type,
        )
        query = query.outerjoin(CompanyTypeRoleMapping, self.model.id == CompanyTypeRoleMapping.role_id)

        # implement complex order by considering enum fields: by company type and role name
        # first define proper order of the company types enum
        company_types = CompanyTypeRoleMapping.company_type.type.enums
        company_types.sort()
        # dynamically create <whens> dict
        whens = {priority: index for index, priority in enumerate(company_types)}
        company_types_sorting_condition = case(whens, value=CompanyTypeRoleMapping.company_type)
        # finally, apply sorting to the query
        query = query.order_by(company_types_sorting_condition, self.model.name.asc())

        total = query.count()
        return total, query.offset(skip).limit(limit).all()

    def get_role_with_document_access(self, roles_pairs):
        """Return roles IDs:
        - either filtered by the input name and company type pair
        - OR it belongs to the Project/Site Owner company type
        args:
            roles_pairs = list of dicts, for example:
                [
                    {"role_name": "Role 1", "company_type": "Company 1"}
                ]
        """
        conditions = [
            and_(
                self.model.name == filter_item["role_name"],
                CompanyTypeRoleMapping.company_type == filter_item["company_type"],
            )
            for filter_item in roles_pairs
        ]
        # if conditions list is empty, it provokes SQLAlchemy deprecation warning:
        #   """SADeprecationWarning: Invoking or_() without arguments is deprecated, and will be disallowed in a future
        #   release.   For an empty or_() construct, use 'or_(false(), *args)' or 'or_(False, *args)'."""
        # need to set it False explicitly
        pair_conditions_statement = False
        if conditions:
            pair_conditions_statement = or_(*conditions)
        query = self.db_session.query(self.model.id)
        query = query.join(CompanyTypeRoleMapping, self.model.id == CompanyTypeRoleMapping.role_id)
        query = query.filter(
            or_(pair_conditions_statement, CompanyTypeRoleMapping.company_type == CompanyTypes.project_site_owner)
        )
        return query.all()
