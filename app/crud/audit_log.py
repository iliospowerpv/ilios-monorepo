from sqlalchemy.sql.functions import coalesce, concat

from app.crud.base_crud import BaseCRUD
from app.models.audit_log import AuditLog
from app.models.user import User
from app.static import DEFAULT_PAGINATION_LIMIT, DEFAULT_PAGINATION_SKIP


class AuditLogCRUD(BaseCRUD):
    """CRUD operations on AuditLog model."""

    def __init__(self, db_session):
        super().__init__(model=AuditLog, db_session=db_session)

    def get_logs(self, skip: int = DEFAULT_PAGINATION_SKIP, limit: int = DEFAULT_PAGINATION_LIMIT):
        query = self.db_session.query(
            self.model.id,
            self.model.source,
            self.model.action,
            self.model.is_success,
            self.model.details,
            self.model.created_at,
            concat(coalesce(User.first_name, "Deleted"), " ", coalesce(User.last_name, "User")).label("user_name"),
            User.email.label("user_email"),
        )
        query = query.outerjoin(User, self.model.user_id == User.id)
        query = self._add_order_by(query, self.model.created_at, order_direction="desc")

        total = query.count()
        return total, query.offset(skip).limit(limit).all()
