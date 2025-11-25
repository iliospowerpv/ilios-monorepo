import enum

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Identity, Integer, String
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.helpers import utcnow


class DocumentCategories(enum.Enum):
    warranty = "Warranty"
    specifications = "Specifications"


class DeviceDocument(Base):
    __tablename__ = "device_documents"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    filepath = Column(String)
    filename = Column(String)

    category = Column(Enum(DocumentCategories))
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    device = relationship("Device", back_populates="documents")

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow())
