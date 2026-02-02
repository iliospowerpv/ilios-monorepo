import logging

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Identity, Index, Integer, String, UniqueConstraint, asc, cast
from sqlalchemy.orm import relationship
from sqlalchemy.schema import DefaultClause
from sqlalchemy.sql import expression

from app.db.base_class import Base
from app.models.comment import HasComments
from app.models.helpers import utcnow
from app.static import TASK_UNDEFINED_STATUS
from app.static.default_site_documents_enum import DocumentSections, SiteDocumentsEnum
from app.static.sales import DocumentKeySource, DocumentKeyStatus

logger = logging.getLogger(__name__)


class Document(HasComments, Base):
    __tablename__ = "documents"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"))
    section_id = Column(Integer, ForeignKey("document_sections.id", ondelete="CASCADE"))

    name = Column(Enum(SiteDocumentsEnum))
    custom_name = Column(String, nullable=True)
    description = Column(String)
    approver_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    position = Column(Integer, nullable=False, default=1, server_default=DefaultClause("1"))
    is_archived = Column(Boolean, nullable=False, default=False, server_default=expression.false())

    site = relationship("Site", back_populates="documents", foreign_keys=[site_id])
    files = relationship("File", back_populates="document", lazy="joined")
    keys = relationship("DocumentKey", back_populates="document")
    approver = relationship("User", back_populates="approving_documents")
    section = relationship("DocumentSection", back_populates="documents", lazy="joined")
    task = relationship("Task", back_populates="document", uselist=False, lazy="joined")

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow())

    @property
    def files_count(self):
        return len([file for file in self.files if not file.deleted])

    @property
    def status(self):
        return self.task.status.name if self.task else TASK_UNDEFINED_STATUS

    @property
    def assignee(self):
        return self.task.assignee if self.task else None

    @property
    def company_id(self):
        return self.site.company_id if self.site else None


class DocumentSection(Base):
    __tablename__ = "document_sections"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"))
    parent_section_id = Column(Integer, ForeignKey("document_sections.id", ondelete="CASCADE"), nullable=True)
    position = Column(Integer, nullable=False, default=1, server_default=DefaultClause("1"))

    name = Column(Enum(DocumentSections))

    documents = relationship(
        "Document", back_populates="section", lazy="joined", order_by=asc(cast(Document.position, Integer))
    )
    parent_section = relationship("DocumentSection", lazy="joined", uselist=False, remote_side="DocumentSection.id")

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow())


class DocumentKey(HasComments, Base):
    __tablename__ = "document_keys"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"))
    editor_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"))

    name = Column(String, nullable=False)
    value = Column(String)

    source = Column(String(20), nullable=True, default="manual_entry")
    status = Column(String(20), nullable=True, default="accepted")
    accepted_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    accepted_at = Column(DateTime, nullable=True)
    override_value = Column(String, nullable=True)
    overridden_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    overridden_at = Column(DateTime, nullable=True)
    canonical_field = Column(String(100), nullable=True)

    document = relationship("Document", back_populates="keys")
    editor = relationship("User", back_populates="edited_document_keys", foreign_keys=[editor_id])
    accepted_by = relationship("User", foreign_keys=[accepted_by_id])
    overridden_by = relationship("User", foreign_keys=[overridden_by_id])

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow())

    __table_args__ = (
        UniqueConstraint("document_id", "name", name="_document_key_uc"),
        Index("ix_document_key_name", "document_id", "name", unique=True),
        Index("idx_document_keys_status", "status"),
        Index("idx_document_keys_canonical_field", "canonical_field"),
    )

    @property
    def effective_value(self):
        """Return the effective value (override if overridden, else original)."""
        if self.status == "overridden" and self.override_value is not None:
            return self.override_value
        return self.value

    @property
    def is_pending(self):
        """Check if this key is pending acceptance."""
        return self.status == "proposed"
