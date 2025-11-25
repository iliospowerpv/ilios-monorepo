from typing import List

from sqlalchemy.sql.functions import coalesce, concat

from app.crud.base_crud import BaseCRUD
from app.models.attachment import Attachment
from app.models.user import User


class AttachmentCRUD(BaseCRUD):
    """CRUD operations on Task Tracker Attachment model."""

    def __init__(self, db_session):
        super().__init__(model=Attachment, db_session=db_session)

    def get_task_attachments(self, task_id: int) -> List[Attachment]:
        """Get attachments for the task. Always orders by created_at DESC."""
        query = self.db_session.query(
            self.model.id,
            self.model.filename,
            self.model.created_at,
            concat(coalesce(User.first_name, "Deleted"), " ", coalesce(User.last_name, "User")).label("author"),
        )
        query = query.filter_by(task_id=task_id)
        query = query.outerjoin(User)
        query = self._add_order_by(query, self.model.created_at, "desc")
        return query.all()
