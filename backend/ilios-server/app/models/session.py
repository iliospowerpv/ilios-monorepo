from datetime import datetime, timedelta, timezone

from sqlalchemy import Column, DateTime, ForeignKey, Identity, Integer
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.helpers import utcnow
from app.settings import settings


def default_value_of_expires_at():
    return datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    created_at = Column(DateTime, server_default=utcnow())
    expires_at = Column(DateTime, nullable=False, default=default_value_of_expires_at)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))
    user = relationship("User", back_populates="sessions")
