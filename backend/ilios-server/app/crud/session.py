from datetime import datetime, timezone

from app.crud.base_crud import BaseCRUD
from app.models.session import Session


class SessionCRUD(BaseCRUD):
    """CRUD operations on Session model."""

    def __init__(self, db_session):
        super().__init__(model=Session, db_session=db_session)

    def delete_expired(self):
        query = self.db_session.query(self.model)
        deleted_count = query.filter(self.model.expires_at < datetime.now(timezone.utc)).delete()
        self.db_session.commit()
        return deleted_count
