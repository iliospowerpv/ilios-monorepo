from sqlalchemy.orm import Session

from ..models.notification import NotificationSubject
from .base_crud import BaseCRUD


class NotificationSubjectCRUD(BaseCRUD):
    """CRUD operations on NotificationSubject model."""

    def __init__(self, db_session: Session):
        super().__init__(model=NotificationSubject, db_session=db_session)
