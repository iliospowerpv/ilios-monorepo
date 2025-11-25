import enum

from sqlalchemy import VARCHAR, Column, Date, DateTime, Enum, ForeignKey, Identity, Integer
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.comment import HasComments
from app.models.helpers import utcnow
from app.models.notification import HasNotifications


class TaskPriorityEnum(str, enum.Enum):
    """Board related entity type name derived from lower-cased model name"""

    low = "Low"
    medium = "Medium"
    high = "High"


class Task(HasComments, HasNotifications, Base):
    __tablename__ = "tasks"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    external_id = Column(VARCHAR, unique=True, index=True)  # the field to store pretty name, such as IOSP1-867
    name = Column(VARCHAR)
    description = Column(VARCHAR, nullable=True)
    due_date = Column(Date, nullable=True)
    priority = Column(Enum(TaskPriorityEnum), default=TaskPriorityEnum.medium.value)
    status_id = Column(Integer, ForeignKey("board_statuses.id", ondelete="CASCADE"))
    board_id = Column(Integer, ForeignKey("boards.id", ondelete="CASCADE"))
    # field special for O&M and AM tasks
    summary_of_events = Column(VARCHAR, nullable=True)
    # indicates when task was completed
    completed_at = Column(DateTime, nullable=True)

    assignee_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    creator_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))
    affected_device_id = Column(Integer, ForeignKey("devices.id", ondelete="SET NULL"), nullable=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="SET NULL"), nullable=True)
    alert_id = Column(Integer, ForeignKey("alerts.id", ondelete="SET NULL"), nullable=True, unique=True)

    assignee = relationship("User", back_populates="assigned_tasks", primaryjoin="User.id == Task.assignee_id")
    creator = relationship("User", back_populates="created_tasks", primaryjoin="User.id == Task.creator_id")
    status = relationship("BoardStatus", back_populates="tasks", uselist=False)
    board = relationship("Board", back_populates="tasks")
    attachments = relationship("Attachment", back_populates="task")
    affected_device = relationship("Device", back_populates="tasks")
    document = relationship("Document", back_populates="task")
    alert = relationship("Alert", back_populates="task")
    site_visit = relationship("SiteVisit", back_populates="task", uselist=False)

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow(), onupdate=utcnow())

    @property
    def site_visit_added(self):  # noqa: FNE002
        """Boolean representation if site visit was created."""
        return True if self.site_visit else False
