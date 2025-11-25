import enum

from sqlalchemy import (
    JSON,
    VARCHAR,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Integer,
    PrimaryKeyConstraint,
    and_,
    event,
)
from sqlalchemy.orm import backref, foreign, relationship, remote

from app.db.base_class import Base
from app.models.helpers import utcnow
from app.models.notification import HasNotifications


class CommentedEntityTypeEnum(str, enum.Enum):
    """Commented entity type name derived from lower-cased model name"""

    document = "document"
    task = "task"
    document_key = "document_key"


class Comment(HasNotifications, Base):
    __tablename__ = "comments"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    text = Column(VARCHAR(length=1000))
    extra = Column(JSON, nullable=True)
    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow(), onupdate=utcnow())

    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    commented_entity = relationship("CommentedEntity", back_populates="comment", uselist=False)
    mentions = relationship("CommentMention", back_populates="comment")


class CommentedEntity(Base):
    __tablename__ = "commented_entities"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    entity_type = Column(Enum(CommentedEntityTypeEnum))
    entity_id = Column(Integer)

    comment_id = Column(Integer, ForeignKey("comments.id", ondelete="CASCADE"))

    comment = relationship("Comment", back_populates="commented_entity", uselist=False)

    @property
    def entity(self):
        """Provides in-Python access to the commented entity by choosing the appropriate relationship"""
        return getattr(self, "parent_entity_%s" % self.entity_type.value)


class HasComments:
    """HasComments mixin, creates a relationship to the commented_entities table for each parent"""


@event.listens_for(HasComments, "mapper_configured", propagate=True)
def setup_listener(mapper, class_):  # noqa: U100
    """A listener that fires on SQLAlchemy mapper initialization and automatically resolves link to the related
    instance depending on the entity type joined by entity id.

    Based on: https://docs.sqlalchemy.org/en/20/_modules/examples/generic_associations/generic_fk.html
    """
    name = class_.__name__
    entity_type = name.lower()
    class_.comments = relationship(
        CommentedEntity,
        primaryjoin=and_(
            class_.id == foreign(remote(CommentedEntity.entity_id)),
            CommentedEntity.entity_type == entity_type,
        ),
        backref=backref(
            "parent_entity_%s" % entity_type,
            primaryjoin=remote(class_.id) == foreign(CommentedEntity.entity_id),
        ),
        viewonly=True,
    )

    @event.listens_for(class_.comments, "append")
    def append_comment(target, value, initiator):  # noqa: U100
        """A listener that fires on appending new comment to the .comments of related entity so that it is available as
        one of all comments of the entity.
        """
        value.entity_type = entity_type


class CommentMention(Base):
    __tablename__ = "comments_mentions"
    __table_args__ = (PrimaryKeyConstraint("comment_id", "user_id"),)

    comment_id = Column(Integer, ForeignKey("comments.id", ondelete="CASCADE"))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"))

    comment = relationship("Comment", back_populates="mentions")
    user = relationship("User", back_populates="mentions")
