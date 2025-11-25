"""CRUD operations on User model."""

from typing import List, Optional, Tuple

from fastapi_filter.contrib.sqlalchemy import Filter

import app.static as static
from app.crud.base_crud import BaseCRUD
from app.db.base_class import Base
from app.models.role import Role
from app.models.user import User
from app.schema.user import UserOrderByFieldEnum


class UserCRUD(BaseCRUD):
    """CRUD operations on User model."""

    def __init__(self, db_session):
        super().__init__(model=User, db_session=db_session)

    def get_by_email(self, email):
        """Get user by email."""
        return self.db_session.query(self.model).filter_by(email=email).first()

    def get_users(
        self,
        search_filter: Filter | None,
        skip: int = static.DEFAULT_PAGINATION_SKIP,
        limit: int = static.DEFAULT_PAGINATION_LIMIT,
        order_by: Optional[str] = None,
        order_direction: Optional[str] = None,
        company_id: Optional[int] = None,
    ) -> Tuple[int, List[Base]]:
        """Get all users with applied skip (offset) and limits, sorted ascending by pk.

        :param search_filter: User search field by first_name, last_name and email
        :param skip: number of items to skip (offset)
        :param limit: number of items to get per page
        :param order_by: field name to order by
        :param order_direction: asc or desc order direction
        :param company_id: if given - get only users for company_id
        :return: tuple (total, list of items)
        """
        query = self.db_session.query(self.model)
        query = search_filter.filter(query)
        # Replace ordering by role with ordering by Role.name
        if order_by == UserOrderByFieldEnum.role:
            order_by = "name"
            query = query.outerjoin(Role)
        query = self._add_order_by(query, order_by, order_direction)
        if company_id:
            query = query.filter(self.model.parent_company_id == company_id)
        total = query.count()
        return total, query.offset(skip).limit(limit).all()

    def get_system_user(self):
        """Retrieve the very first system user"""
        return self.db_session.query(self.model).filter_by(is_system_user=True).first()

    def get_users_by_roles(self, roles_ids):
        """Retrieve users ids by the input roles IDs"""
        query = self.db_session.query(self.model.id)
        query = query.filter(self.model.role_id.in_(roles_ids))
        return query.all()
