import enum

from sqlalchemy import (
    VARCHAR,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Integer,
    UniqueConstraint,
    and_,
    event,
)
from sqlalchemy.orm import backref, foreign, relationship, remote

from app.db.base_class import Base
from app.models.helpers import utcnow


class BoardRelatedEntityTypeEnum(str, enum.Enum):
    """Board related entity type name derived from lower-cased model name"""

    site = "site"
    company = "company"


class BoardRelatedEntityTypeExtraEnum(str, enum.Enum):
    document = "document"


class BoardModuleEnum(str, enum.Enum):
    """Represents which module board relates to"""

    asset = "Asset"
    diligence = "Diligence"
    om = "O&M"


class Board(Base):
    __tablename__ = "boards"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    name = Column(VARCHAR)
    description = Column(VARCHAR)
    is_active = Column(Boolean, default=True)
    module = Column(Enum(BoardModuleEnum), nullable=False)

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow(), onupdate=utcnow())

    related_entity = relationship("BoardRelatedEntity", back_populates="board", uselist=False)
    statuses = relationship("BoardStatus", back_populates="board")
    tasks = relationship("Task", back_populates="board")

    def get_statuses_ids(self):
        """Return IDs of board statuses"""
        return [status.id for status in self.statuses]


class BoardRelatedEntity(Base):
    __tablename__ = "board_related_entities"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    entity_type = Column(Enum(BoardRelatedEntityTypeEnum))
    entity_id = Column(Integer)

    board_id = Column(Integer, ForeignKey("boards.id", ondelete="CASCADE"))
    extra_entity_type = Column(Enum(BoardRelatedEntityTypeExtraEnum), nullable=True)

    board = relationship("Board", back_populates="related_entity", uselist=False)

    @property
    def entity(self):
        """Provides in-Python access to the related entity by choosing the appropriate relationship"""
        return getattr(self, "parent_entity_%s" % self.entity_type.value)


class RelatedBoards:
    """RelatedBoards mixin, creates a relationship to the board_related_entities table for each parent"""


@event.listens_for(RelatedBoards, "mapper_configured", propagate=True)
def setup_listener(mapper, class_):  # noqa: U100
    """A listener that fires on SQLAlchemy mapper initialization and automatically resolves link to the related
    instance depending on the entity type joined by entity id.

    Based on: https://docs.sqlalchemy.org/en/20/_modules/examples/generic_associations/generic_fk.html
    """
    name = class_.__name__
    entity_type = name.lower()
    class_.related_boards = relationship(
        BoardRelatedEntity,
        primaryjoin=and_(
            class_.id == foreign(remote(BoardRelatedEntity.entity_id)),
            BoardRelatedEntity.entity_type == entity_type,
        ),
        backref=backref(
            "parent_entity_%s" % entity_type,
            primaryjoin=remote(class_.id) == foreign(BoardRelatedEntity.entity_id),
            overlaps="parent_entity_company,related_boards",
        ),
        overlaps="parent_entity_company,related_boards",
        viewonly=True,
    )

    @event.listens_for(class_.related_boards, "append")
    def append_board(target, value, initiator):  # noqa: U100
        """A listener that fires on appending new board to the .boards of related entity so that it is available as
        one of all boards of the entity.
        """
        value.entity_type = entity_type


class BoardStatus(Base):
    __tablename__ = "board_statuses"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    name = Column(VARCHAR)

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow(), onupdate=utcnow())

    board_id = Column(Integer, ForeignKey("boards.id", ondelete="CASCADE"), nullable=False)
    board = relationship("Board", back_populates="statuses")
    tasks = relationship("Task", back_populates="status")

    __table_args__ = (UniqueConstraint(board_id, name, name="u_board_id_name"),)
