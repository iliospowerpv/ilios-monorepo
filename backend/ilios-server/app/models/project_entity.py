"""Project Entity models for the Entity Directory system.

ProjectEntity: Portfolio-scoped directory of legal/business entities.
EntityRelationship: Project-level role assignments with temporal tracking.
DealEntityAssignment: Deal-level entity references for acquisitions.
"""

from sqlalchemy import (
    Boolean,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.helpers import utcnow
from app.static.entities import DealEntityRole, EntityRelationshipRole, EntityType


class ProjectEntity(Base):
    """Portfolio-scoped entity directory entry.

    Represents a legal/business organization that participates in project
    ownership, service delivery, or compliance — whether or not they are
    licensed platform users. Examples: EPC contractors, O&M providers,
    offtakers, tax equity partners, holding companies, etc.
    """

    __tablename__ = "project_entities"

    __table_args__ = (
        UniqueConstraint("portfolio_id", "name", name="uq_project_entities_portfolio_name"),
        Index("ix_project_entities_portfolio_id", "portfolio_id"),
        Index("ix_project_entities_entity_type", "entity_type"),
        Index("ix_project_entities_is_active", "is_active"),
        Index("ix_project_entities_linked_company_id", "linked_company_id"),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    portfolio_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(255), nullable=False)
    entity_type = Column(Enum(EntityType), nullable=False)

    address = Column(String(500), nullable=True)
    city = Column(String(255), nullable=True)
    state = Column(String(50), nullable=True)
    zip_code = Column(String(20), nullable=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    website = Column(String(500), nullable=True)
    notes = Column(Text, nullable=True)

    is_active = Column(Boolean, server_default="true", nullable=False)

    linked_company_id = Column(
        Integer,
        ForeignKey("companies.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow(), onupdate=utcnow())

    portfolio = relationship("Company", foreign_keys=[portfolio_id])
    linked_company = relationship("Company", foreign_keys=[linked_company_id])
    relationships = relationship(
        "EntityRelationship",
        back_populates="entity",
        cascade="all, delete-orphan",
    )
    deal_assignments = relationship(
        "DealEntityAssignment",
        back_populates="entity",
        cascade="all, delete-orphan",
    )


class EntityRelationship(Base):
    """Project-level entity role assignment with temporal tracking.

    Links a ProjectEntity to a Site (project) in a specific role, with
    optional effective/termination dates for tracking ownership changes,
    flips, buyouts, and service provider transitions.
    """

    __tablename__ = "entity_relationships"

    __table_args__ = (
        UniqueConstraint(
            "site_id",
            "role",
            "entity_id",
            name="uq_entity_relationships_site_role_entity",
        ),
        Index("ix_entity_relationships_site_id", "site_id"),
        Index("ix_entity_relationships_entity_id", "entity_id"),
        Index("ix_entity_relationships_role", "role"),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    site_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=False)
    entity_id = Column(Integer, ForeignKey("project_entities.id", ondelete="CASCADE"), nullable=False)
    role = Column(Enum(EntityRelationshipRole), nullable=False)

    contact_id = Column(
        Integer,
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
    )

    effective_date = Column(Date, nullable=True)
    termination_date = Column(Date, nullable=True)
    notes = Column(Text, nullable=True)

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow(), onupdate=utcnow())

    site = relationship("Site", foreign_keys=[site_id])
    entity = relationship("ProjectEntity", back_populates="relationships", foreign_keys=[entity_id])
    contact = relationship("Contact", foreign_keys=[contact_id])


class DealEntityAssignment(Base):
    """Deal-level entity reference for acquisitions.

    Links a ProjectEntity to a Deal in a specific role (developer,
    project company, offtaker, etc.).
    """

    __tablename__ = "deal_entity_assignments"

    __table_args__ = (
        UniqueConstraint("deal_id", "role", name="uq_deal_entity_assignments_deal_role"),
        Index("ix_deal_entity_assignments_deal_id", "deal_id"),
        Index("ix_deal_entity_assignments_entity_id", "entity_id"),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    deal_id = Column(Integer, ForeignKey("deals.id", ondelete="CASCADE"), nullable=False)
    entity_id = Column(Integer, ForeignKey("project_entities.id", ondelete="CASCADE"), nullable=False)
    role = Column(Enum(DealEntityRole), nullable=False)

    contact_id = Column(
        Integer,
        ForeignKey("contacts.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow(), onupdate=utcnow())

    deal = relationship("Deal", foreign_keys=[deal_id])
    entity = relationship("ProjectEntity", back_populates="deal_assignments", foreign_keys=[entity_id])
    contact = relationship("Contact", foreign_keys=[contact_id])
