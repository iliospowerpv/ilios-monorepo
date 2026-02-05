"""Finance Account model for normalized external finance data."""

from sqlalchemy import (
    Boolean, Column, DateTime, ForeignKey, Identity, Integer,
    String, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base_class import Base
from app.models.helpers import utcnow


class FinanceAccount(Base):
    """Normalized finance account ingested from an external provider.

    Each record represents a single account as reported by the provider.
    The triple (company_id, provider_key, external_id) is unique and used
    for upsert semantics during sync runs.
    """
    __tablename__ = "finance_accounts"

    __table_args__ = (
        UniqueConstraint(
            "company_id", "provider_key", "external_id",
            name="uq_finance_accounts_company_provider_ext",
        ),
        Index("ix_finance_accounts_company_id", "company_id"),
        Index("ix_finance_accounts_provider_key", "provider_key"),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    company_id = Column(
        Integer,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_key = Column(String(50), nullable=False)
    external_id = Column(String(255), nullable=False)
    name = Column(String(500), nullable=False)
    account_type = Column(String(100), nullable=True)
    parent_external_id = Column(String(255), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True)
    raw_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
