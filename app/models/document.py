import logging

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Identity, Index, Integer, String, UniqueConstraint, asc, cast
from sqlalchemy.orm import relationship
from sqlalchemy.schema import DefaultClause

from app.db.base_class import Base
from app.models.comment import HasComments
from app.models.helpers import utcnow
from app.static import TASK_UNDEFINED_STATUS
from app.static.default_site_documents_enum import DocumentSections, SiteDocumentsEnum

logger = logging.getLogger(__name__)


class Document(HasComments, Base):
    __tablename__ = "documents"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"))
    section_id = Column(Integer, ForeignKey("document_sections.id", ondelete="CASCADE"))

    name = Column(Enum(SiteDocumentsEnum))
    description = Column(String)
    approver_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    # use this field to define the order of appearance
    position = Column(Integer, nullable=False, default=1, server_default=DefaultClause("1"))

    site = relationship("Site", back_populates="documents")
    files = relationship("File", back_populates="document", lazy="joined")
    keys = relationship("DocumentKey", back_populates="document")
    approver = relationship("User", back_populates="approving_documents")
    section = relationship("DocumentSection", back_populates="documents", lazy="joined")
    task = relationship("Task", back_populates="document", uselist=False, lazy="joined")

    # setting up the server_default value, that will be filled on the database side
    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow())

    @property
    def files_count(self):  # noqa FNE002
        return len([file for file in self.files if not file.deleted])

    @property
    def status(self):
        # return "Undefined" status in case related board or task does not exist
        return self.task.status.name if self.task else TASK_UNDEFINED_STATUS

    @property
    def assignee(self):
        # return document assignee as None in case related board or task does not exist
        return self.task.assignee if self.task else None

    @property
    def company_id(self):
        return self.site.company_id if self.site else None


class DocumentSection(Base):
    __tablename__ = "document_sections"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"))
    parent_section_id = Column(Integer, ForeignKey("document_sections.id", ondelete="CASCADE"), nullable=True)
    # use this field to define the order of appearance
    position = Column(Integer, nullable=False, default=1, server_default=DefaultClause("1"))

    name = Column(Enum(DocumentSections))

    documents = relationship(
        "Document", back_populates="section", lazy="joined", order_by=asc(cast(Document.position, Integer))
    )
    parent_section = relationship("DocumentSection", lazy="joined", uselist=False, remote_side="DocumentSection.id")

    # setting up the server_default value, that will be filled on the database side
    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow())


class DocumentKey(HasComments, Base):
    __tablename__ = "document_keys"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"))
    # the last user who edited the key
    editor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    name = Column(String, nullable=False)
    value = Column(String)

    document = relationship("Document", back_populates="keys")
    editor = relationship("User", back_populates="edited_document_keys")

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow())

    __table_args__ = (
        # ensure each key is populated once per document
        UniqueConstraint("document_id", "name", name="_document_key_uc"),
        Index("ix_document_key_name", "document_id", "name", unique=True),
    )
