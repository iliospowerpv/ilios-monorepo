import enum

from sqlalchemy import VARCHAR, Boolean, Column, DateTime, Enum, ForeignKey, Identity, Integer
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.helpers import utcnow


class AlertSeverity(enum.Enum):
    critical = "Critical"
    warning = "Warning"
    informational = "Informational"


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    device_id = Column(Integer, ForeignKey("devices.id", ondelete="CASCADE"))
    type = Column(VARCHAR, nullable=False)
    severity = Column(Enum(AlertSeverity))
    is_resolved = Column(Boolean, default=False)
    error_message = Column(VARCHAR, nullable=False)
    alert_start = Column(DateTime, server_default=utcnow())
    alert_end = Column(DateTime)
    external_id = Column(VARCHAR, nullable=True)

    # relationships
    device = relationship("Device", back_populates="alerts")
    task = relationship("Task", back_populates="alert", uselist=False, lazy="joined")

    # setting up the server_default value, that will be filled on the database side
    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow())
