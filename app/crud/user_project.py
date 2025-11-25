"""CRUD operations on UserProject model."""

from typing import Iterable

from fastapi_filter.contrib.sqlalchemy import Filter
from sqlalchemy import String, and_, cast, or_

from app.crud.base_crud import BaseCRUD
from app.models.role import Role
from app.models.user import User, UserProject


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
