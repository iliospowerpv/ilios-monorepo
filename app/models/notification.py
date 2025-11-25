import enum

from sqlalchemy import JSON, Boolean, Column, DateTime, Enum, ForeignKey, Identity, Integer, and_, event
from sqlalchemy.orm import backref, foreign, relationship, remote

from app.db.base_class import Base
from app.models.helpers import utcnow


class NotificationKindsEnum(str, enum.Enum):
    """Types of notifications"""

    # Company or Site task status changes from the initial one
    # (default status set during task creation) to another status.
    task_status_change = "Task status changes"
    # Creator updated the task with Assignee value after task creation.
    task_assignee_added = "Assignee changed from not to a new person"
    # User 1 performed his part of the task and moved it to another person
    # to complete the work according to the business flow. e.g. New assignee is not empty.
    task_assignee_changed = "Assignee changes from one person to another"
    # Task was assigned to user by mistake and new assignee is not defined
    task_assignee_unset = "Assignee changes from one person to unassigned"
    # User was mentioned in the comment
    comment_mention = "User was tagged in the system"


class NotificationSubjectsEnum(str, enum.Enum):
    """Subject(entity) notification is related to"""

    task = "task"
    comment = "comment"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    kind = Column(Enum(NotificationKindsEnum), nullable=False)
    seen = Column(Boolean, default=False)

    actor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    recipient_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)

    # in case if notification needs some additional metadata, it can be stored in this dedicated field
    extra = Column(JSON, nullable=True)

    actor = relationship(
        "User", back_populates="triggered_notifications", primaryjoin="User.id == Notification.actor_id"
    )
    recipient = relationship(
        "User", back_populates="received_notifications", primaryjoin="User.id == Notification.recipient_id"
    )
    subject = relationship("NotificationSubject", back_populates="notification", uselist=False)

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow(), onupdate=utcnow())


class NotificationSubject(Base):
    __tablename__ = "notification_subjects"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    entity_type = Column(Enum(NotificationSubjectsEnum))
    entity_id = Column(Integer)

    notification_id = Column(Integer, ForeignKey("notifications.id", ondelete="CASCADE"))

    notification = relationship("Notification", back_populates="subject", uselist=False)

    @property
    def entity(self):
        """Provides in-Python access to the notification subject by choosing the appropriate relationship"""
        return getattr(self, "parent_entity_%s" % self.entity_type.value)


class HasNotifications:
    """HasNotifications mixin, creates a relationship to the notification_subjects table for each parent"""


@event.listens_for(HasNotifications, "mapper_configured", propagate=True)
def setup_listener(mapper, class_):  # noqa: U100
    """A listener that fires on SQLAlchemy mapper initialization and automatically resolves link to the related
    instance depending on the entity type joined by entity id.

    Based on: https://docs.sqlalchemy.org/en/20/_modules/examples/generic_associations/generic_fk.html
    """
    name = class_.__name__
    entity_type = name.lower()
    class_.notifications = relationship(
        NotificationSubject,
        primaryjoin=and_(
            class_.id == foreign(remote(NotificationSubject.entity_id)),
            NotificationSubject.entity_type == entity_type,
        ),
        backref=backref(
            "parent_entity_%s" % entity_type,
            primaryjoin=remote(class_.id) == foreign(NotificationSubject.entity_id),
        ),
        viewonly=True,
    )

    @event.listens_for(class_.notifications, "append")
    def append_notification(target, value, initiator):  # noqa: U100
        """A listener that fires on appending new notification to the .notifications of related entity
        so that it is available as one of all notifications of the entity."""
        value.entity_type = entity_type
