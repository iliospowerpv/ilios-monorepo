"""Finance Integration model for company-level finance provider configuration."""

from enum import Enum as PyEnum

from sqlalchemy import Boolean, Column, DateTime, Enum, ForeignKey, Identity, Integer, LargeBinary, String, Text, Index, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship

from app.db.base_class import Base
from app.models.helpers import utcnow


class FinanceIntegrationStatus(PyEnum):
    """Status of a finance integration configuration."""
    pending = "pending"
    configured = "configured"
    error = "error"
    disabled = "disabled"


class FinanceIntegration(Base):
    """Finance integration configuration for a company.
    
    Stores the configuration for connecting to external finance systems
    like Gravity, QuickBooks, etc. Each company can have one configuration
    per provider.
    
    NOTE: This is a READ-ONLY integration. No write-back to external
    finance systems is supported.
    """
    __tablename__ = "finance_integrations"
    
    __table_args__ = (
        UniqueConstraint('company_id', 'provider_key', name='uq_finance_integrations_company_provider'),
        Index('ix_finance_integrations_company_id', 'company_id'),
        Index('ix_finance_integrations_provider_key', 'provider_key'),
        Index('ix_finance_integrations_status', 'status'),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    
    company_id = Column(Integer, ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    provider_key = Column(String(50), nullable=False)
    
    encrypted_credentials = Column(LargeBinary, nullable=True)
    config_json = Column(JSONB, nullable=True)
    
    status = Column(
        Enum(FinanceIntegrationStatus),
        nullable=False,
        default=FinanceIntegrationStatus.pending,
    )
    
    last_tested_at = Column(DateTime, nullable=True)
    last_test_success = Column(Boolean, nullable=True)
    last_error = Column(Text, nullable=True)
    
    created_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by_user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
    
    company = relationship("Company", foreign_keys=[company_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    updated_by = relationship("User", foreign_keys=[updated_by_user_id])
