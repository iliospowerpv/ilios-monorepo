"""Contact model for CRM-style address book at portfolio/company/project levels."""

from enum import Enum as PyEnum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Identity, Integer, String, Text, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.helpers import utcnow


class ContactScopeType(PyEnum):
    """Scope type for a contact - which level it belongs to."""
    portfolio = "portfolio"
    company = "company"
    project = "project"


class Contact(Base):
    """Contact entity - CRM-style address book entry at portfolio/company/project level.
    
    Contacts are NOT users by default. A contact may optionally correspond to an
    existing user account (computed via email match), but this is for display only
    and does not grant any access or permissions.
    """
    __tablename__ = "contacts"
    
    __table_args__ = (
        CheckConstraint(
            "(scope_type = 'portfolio' AND portfolio_id IS NOT NULL AND company_id IS NULL AND project_id IS NULL) OR "
            "(scope_type = 'company' AND company_id IS NOT NULL AND portfolio_id IS NULL AND project_id IS NULL) OR "
            "(scope_type = 'project' AND project_id IS NOT NULL AND portfolio_id IS NULL AND company_id IS NULL)",
            name='ck_contacts_scope_fk_consistency'
        ),
        Index('ix_contacts_scope_type', 'scope_type'),
        Index('ix_contacts_portfolio_id', 'portfolio_id'),
        Index('ix_contacts_company_id', 'company_id'),
        Index('ix_contacts_project_id', 'project_id'),
        Index('ix_contacts_is_archived', 'is_archived'),
        Index('ix_contacts_email_normalized', 'email_normalized'),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    
    scope_type = Column(Enum(ContactScopeType), nullable=False)
    portfolio_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=True)
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=True)
    project_id = Column(Integer, ForeignKey("sites.id", ondelete="CASCADE"), nullable=True)
    
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), nullable=False)
    email = Column(String(255), nullable=True)
    email_normalized = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    title = Column(String(100), nullable=True)
    organization = Column(String(200), nullable=True)
    notes = Column(Text, nullable=True)
    tags = Column(JSONB, nullable=True)
    
    is_archived = Column(Boolean, server_default='false', nullable=False)
    
    entity_id = Column(Integer, ForeignKey("project_entities.id", ondelete="SET NULL"), nullable=True, index=True)

    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, server_default=utcnow())
    updated_at = Column(DateTime, server_default=utcnow(), onupdate=utcnow())
    
    portfolio = relationship("Company", foreign_keys=[portfolio_id])
    company = relationship("Company", foreign_keys=[company_id])
    project = relationship("Site", foreign_keys=[project_id])
    entity = relationship("ProjectEntity", foreign_keys=[entity_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
    
    @staticmethod
    def normalize_email(email: str | None) -> str | None:
        """Normalize email for case-insensitive comparison."""
        if email is None:
            return None
        return email.strip().lower() or None
