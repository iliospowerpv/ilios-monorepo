from sqlalchemy import Column, DateTime, ForeignKey, Identity, Integer, String
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.helpers import utcnow


class Attachment(Base):
    __tablename__ = "attachments"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    filepath = Column(String)
    filename = Column(String)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"))

    user = relationship("User", back_populates="attachments")
    task = relationship("Task", back_populates="attachments")

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow())
