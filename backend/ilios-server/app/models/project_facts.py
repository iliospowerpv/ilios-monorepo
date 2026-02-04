import enum

from sqlalchemy import Column, DateTime, ForeignKey, Identity, Integer, String, Text, Boolean, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.helpers import utcnow


class FactStatus(str, enum.Enum):
    candidate = "candidate"
    active = "active"
    retired = "retired"


class CanonicalField(Base):
    __tablename__ = "canonical_fields"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    display_name = Column(String(255), nullable=False)
    field_type = Column(String(50), nullable=False, default="text")
    validation_regex = Column(String(500), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow())

    project_facts = relationship("ProjectFact", back_populates="canonical_field")

    def __repr__(self):
        return f"<CanonicalField(id={self.id}, name='{self.name}')>"


class ProjectFact(Base):
    __tablename__ = "project_facts"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False)
    canonical_field_id = Column(Integer, ForeignKey("canonical_fields.id", ondelete="CASCADE"), nullable=False)
    value = Column(JSONB, nullable=True)
    status = Column(String(20), nullable=False, default=FactStatus.candidate.value)
    source_file_id = Column(Integer, ForeignKey("files.id", ondelete="CASCADE"), nullable=True)
    source_document_key_id = Column(Integer, ForeignKey("document_keys.id", ondelete="SET NULL"), nullable=True)
    promoted_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    promoted_at = Column(DateTime, nullable=True)
    promotion_notes = Column(Text, nullable=True)
    supersedes_fact_id = Column(Integer, ForeignKey("project_facts.id", ondelete="SET NULL"), nullable=True)

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow())

    site = relationship("Site", back_populates="project_facts")
    canonical_field = relationship("CanonicalField", back_populates="project_facts")
    source_file = relationship("File", back_populates="project_facts")
    source_document_key = relationship("DocumentKey", back_populates="project_facts")
    promoted_by = relationship("User", foreign_keys=[promoted_by_id])
    supersedes_fact = relationship("ProjectFact", remote_side=[id], foreign_keys=[supersedes_fact_id])

    __table_args__ = (
        Index("ix_project_facts_site_field", "site_id", "canonical_field_id"),
        Index("ix_project_facts_status", "status"),
        Index("ix_project_facts_source_file", "source_file_id"),
    )

    @property
    def is_active(self):
        return self.status == FactStatus.active.value

    @property
    def is_candidate(self):
        return self.status == FactStatus.candidate.value

    def __repr__(self):
        return f"<ProjectFact(id={self.id}, site_id={self.site_id}, status='{self.status}')>"


class AssumptionPromotion(Base):
    __tablename__ = "assumptions_promotions"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False)
    file_id = Column(Integer, ForeignKey("files.id", ondelete="CASCADE"), nullable=False)
    promoted_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=False)
    promoted_at = Column(DateTime, server_default=utcnow(), nullable=False)
    notes = Column(Text, nullable=True)
    diff_json = Column(JSONB, nullable=True)

    created_at = Column(DateTime, server_default=utcnow())

    site = relationship("Site", back_populates="assumption_promotions")
    document = relationship("Document", back_populates="assumption_promotions")
    file = relationship("File", back_populates="assumption_promotions")
    promoted_by = relationship("User", foreign_keys=[promoted_by_id])

    __table_args__ = (
        Index("ix_assumptions_promotions_site", "site_id"),
        Index("ix_assumptions_promotions_file", "file_id"),
        Index("ix_assumptions_promotions_promoted_at", "promoted_at"),
    )

    def __repr__(self):
        return f"<AssumptionPromotion(id={self.id}, site_id={self.site_id}, file_id={self.file_id})>"
