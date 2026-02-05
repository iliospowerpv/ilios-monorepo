"""Finance Transaction model for normalized external finance data."""

from sqlalchemy import (
    Column, Date, DateTime, ForeignKey, Identity, Integer,
    Numeric, String, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base_class import Base
from app.models.helpers import utcnow


class FinanceTransaction(Base):
    """Normalized finance transaction ingested from an external provider.

    Each record represents a single transaction as reported by the provider.
    The triple (company_id, provider_key, external_id) is unique and used
    for upsert semantics during sync runs.
    """
    __tablename__ = "finance_transactions"

    __table_args__ = (
        UniqueConstraint(
            "company_id", "provider_key", "external_id",
            name="uq_finance_txns_company_provider_ext",
        ),
        Index("ix_finance_transactions_company_id", "company_id"),
        Index("ix_finance_transactions_provider_key", "provider_key"),
        Index("ix_finance_transactions_txn_date", "txn_date"),
        Index("ix_finance_transactions_account_ext", "account_external_id"),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    company_id = Column(
        Integer,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_key = Column(String(50), nullable=False)
    external_id = Column(String(255), nullable=False)
    account_external_id = Column(String(255), nullable=False)
    amount = Column(Numeric(precision=18, scale=4), nullable=False)
    currency = Column(String(10), nullable=True, default="USD")
    txn_date = Column(Date, nullable=False)
    description = Column(String(1000), nullable=True)
    counterparty = Column(String(500), nullable=True)
    project_external_id = Column(String(255), nullable=True)
    raw_json = Column(JSONB, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
