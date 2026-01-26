"""Sales module database models."""

from sqlalchemy import (
    TIMESTAMP,
    VARCHAR,
    Column,
    ForeignKey,
    Identity,
    Integer,
    Text,
)
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.helpers import utcnow


class SalesStateTransition(Base):
    """Audit log for sales stage and lifecycle state transitions."""

    __tablename__ = "sales_state_transitions"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False)
    
    transition_type = Column(VARCHAR(50), nullable=False)
    from_state = Column(VARCHAR(100), nullable=True)
    to_state = Column(VARCHAR(100), nullable=False)
    notes = Column(Text, nullable=True)
    
    changed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(TIMESTAMP, server_default=utcnow())

    site = relationship("Site", backref="sales_transitions")
    changed_by = relationship("User", foreign_keys=[changed_by_id])
