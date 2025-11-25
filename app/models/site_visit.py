"""Site visit if an object, which is related to the O&M site-level tasks"""

from sqlalchemy import VARCHAR, Column, Date, DateTime, ForeignKey, Identity, Integer, UniqueConstraint
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.helpers import utcnow


class SiteVisit(Base):
    __tablename__ = "site_visits"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    service_date = Column(Date, nullable=True)
    technician_assignee = Column(VARCHAR, nullable=True)
    reasons = Column(VARCHAR, nullable=True)
    scope_of_work = Column(VARCHAR, nullable=True)
    status = Column(VARCHAR, nullable=True)
    resolution = Column(VARCHAR, nullable=True)
    next_steps = Column(VARCHAR, nullable=True)
    pending_work = Column(VARCHAR, nullable=True)
    recommendations = Column(VARCHAR, nullable=True)

    task_id = Column(Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False, unique=True)
    creator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    task = relationship("Task", back_populates="site_visit", uselist=False)
    creator = relationship("User", back_populates="created_site_visits", primaryjoin="User.id == SiteVisit.creator_id")
    uploads = relationship("SiteVisitUpload", back_populates="site_visit")

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow(), onupdate=utcnow())

    # Ensure only one visit per task
    __table_args__ = (UniqueConstraint("task_id", name="uq_visits_task_id"),)
