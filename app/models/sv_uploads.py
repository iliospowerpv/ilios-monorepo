from sqlalchemy import Column, DateTime, ForeignKey, Identity, Integer, String
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.helpers import utcnow


class SiteVisitUpload(Base):
    """Site visit uploads"""

    __tablename__ = "site_visit_uploads"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    filepath = Column(String)
    filename = Column(String)
    section_name = Column(String)

    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    site_visit_id = Column(Integer, ForeignKey("site_visits.id", ondelete="CASCADE"))

    user = relationship("User", back_populates="site_visit_uploads")
    site_visit = relationship("SiteVisit", back_populates="uploads")

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow(), onupdate=utcnow())
