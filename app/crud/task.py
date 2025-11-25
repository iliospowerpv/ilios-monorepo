from typing import Optional

from fastapi_filter.contrib.sqlalchemy import Filter
from sqlalchemy import Integer, asc, case, func, nullsfirst

import app.static as static
from app.crud.base_crud import BaseCRUD
from app.models.task import Task, TaskPriorityEnum
from app.schema.task import TaskOrderByFieldEnum


class TaskCRUD(BaseCRUD):
    """CRUD operations on Task model."""

    def __init__(self, db_session):
        super().__init__(model=Task, db_session=db_session)

    def get_max_prefix_number(self, prefix: str):
        """Get max number followed by the input prefix.
        For example, if prefix is EXP, and we have several external IDs like EXP-1, ..., EXP-8, it will return 8"""
        query = self.db_session.query(func.max(func.substr(Task.external_id, len(prefix) + 2).cast(Integer)))
        query = query.filter(Task.external_id.like(prefix + "-%"))
        return query.scalar()

    def get_tasks_by_board_id(
        self,
        board_id: int,
        search_filter: Filter | None = None,
        skip: int = static.DEFAULT_PAGINATION_SKIP,
        limit: int = static.DEFAULT_PAGINATION_LIMIT,
        order_by: Optional[str] = None,
        order_direction: Optional[str] = None,
    ):
        query = self.db_session.query(self.model)
        if search_filter:
            query = search_filter.filter(query)
        query = query.filter(self.model.board_id == board_id)
        if not order_by:
            # default ordering for tasks no due date first and older due dates next
            query = query.order_by(nullsfirst(asc(TaskOrderByFieldEnum.due_date.value)))
        else:
            query = self._add_order_by(query, order_by, order_direction)
        total = query.count()
        return total, query.offset(skip).limit(limit).all()

    def get_user_tasks(
        self, user_id: int, skip: int = static.DEFAULT_PAGINATION_SKIP, limit: int = static.DEFAULT_PAGINATION_LIMIT
    ):
        query = self.db_session.query(self.model)
        query = query.filter(self.model.assignee_id == user_id)
        query = self._add_order_by(query, "due_date", "asc")
        query = query.order_by(
            case(
                (self.model.priority == TaskPriorityEnum.high, 1),
                (self.model.priority == TaskPriorityEnum.medium, 2),
                (self.model.priority == TaskPriorityEnum.low, 3),
                else_=4,
            ),
            # order by name in case same priority
            asc(self.model.name),
        )
        total = query.count()
        return total, query.offset(skip).limit(limit).all()
