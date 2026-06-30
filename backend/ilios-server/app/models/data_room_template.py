import logging

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Identity, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import expression

from app.db.base_class import Base
from app.models.helpers import utcnow

logger = logging.getLogger(__name__)


class DataRoomTemplate(Base):
    """Reusable, company-scoped snapshot of a Data Room's *structure* (Task #91).

    A template captures structure only — stages/sections, the expected documents
    per section, their ordering, descriptions, guidance and optionality. It NEVER
    captures files, file versions, document metadata/keys, approvals or any
    workflow history. Applying a template scaffolds a new Data Room's sections and
    expected-document slots through the existing creation path; it never creates
    placeholder File rows.

    The ``structure`` JSON is enum-anchored (``DocumentSections`` / ``SiteDocumentsEnum``)
    so it stays portable and validates against the canonical Data Room blueprint.
    The canonical ``Site`` entity is untouched (Project == Site is a UI label only).
    """

    __tablename__ = "data_room_templates"

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    created_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    structure = Column(JSONB, nullable=False)
    is_archived = Column(Boolean, nullable=False, default=False, server_default=expression.false())

    company = relationship("Company")
    created_by = relationship("User", foreign_keys=[created_by_id])

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow())

    __table_args__ = (Index("ix_data_room_templates_company", "company_id", "is_archived"),)
