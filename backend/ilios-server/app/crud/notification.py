from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

import app.static as static
from app.db.base import Notification

from ..models.board import Board, BoardModuleEnum
from ..models.notification import NotificationSubject, NotificationSubjectsEnum
from ..models.task import Task
from .base_crud import BaseCRUD


class NotificationCRUD(BaseCRUD):
    """CRUD operations on Notification model."""

    def __init__(self, db_session: Session):
        super().__init__(model=Notification, db_session=db_session)

    def get_notifications_by_user(
        self, user_id: int, skip: int = static.DEFAULT_PAGINATION_SKIP, limit: int = static.DEFAULT_PAGINATION_LIMIT
    ):
        query = self.db_session.query(
            self.model,
        )
        query = query.filter(self.model.recipient_id == user_id)
        query = query.join(NotificationSubject, self.model.id == NotificationSubject.notification_id)
        # NOTE! Temporary solution to exclude diligence tasks, which will be implemented separately
        # since we don't have an ability to use relationship on the query level,
        # we need to exclude diligence tasks by ID
        # (I know, solution is not perfect, but it works)
        diligence_notifications_query = (  # noqa: ECE001
            self.db_session.query(self.model.id)
            .join(NotificationSubject, self.model.id == NotificationSubject.notification_id)
            .outerjoin(Task, NotificationSubject.entity_id == Task.id)
            .outerjoin(Board, Task.board_id == Board.id)
            .filter(
                Notification.recipient_id == user_id,
                NotificationSubject.entity_type == NotificationSubjectsEnum.task,
                Board.module == BoardModuleEnum.diligence,
            )
        )
        diligence_notifications_ids = [row[0] for row in diligence_notifications_query.all()]
        query = query.filter(self.model.id.notin_(diligence_notifications_ids))

        # unread notifications on top of the notification list with the newest notification on top
        unread_count = query.filter(self.model.seen == False).count()  # noqa: E712
        query = query.order_by(asc(self.model.seen), desc(self.model.created_at))
        total = query.count()
        return total, unread_count, query.offset(skip).limit(limit).all()
