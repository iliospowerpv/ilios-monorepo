from sqlalchemy import VARCHAR, Boolean, Column, DateTime, ForeignKey, Identity, Index, Integer
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.helpers import utcnow


class AuditLog(Base):
    __tablename__ = "audit_logs"

    __table_args__ = (
        Index("ix_audit_logs_created_at", "created_at"),
        Index("ix_audit_logs_user_id", "user_id"),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    created_at = Column(DateTime, server_default=utcnow())
    source = Column(VARCHAR, nullable=True)
    action = Column(VARCHAR, nullable=True)
    is_success = Column(Boolean, nullable=False)
    details = Column(VARCHAR, nullable=True)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    user = relationship("User")
