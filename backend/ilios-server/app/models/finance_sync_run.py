"""Finance Sync Run model for tracking ingestion executions."""

from enum import Enum as PyEnum

from sqlalchemy import (
    Column, DateTime, Enum, ForeignKey, Identity, Integer,
    String, Text, Index,
)
from sqlalchemy.dialects.postgresql import JSONB

from app.db.base_class import Base
from app.models.helpers import utcnow


class FinanceSyncRunStatus(PyEnum):
    """Status lifecycle for a sync run."""
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"


class FinanceSyncRun(Base):
    """Tracks execution of a finance data ingestion run.

    Each run fetches data from a provider and upserts it into the
    normalized finance tables. Status transitions:
    queued -> running -> succeeded | failed
    """
    __tablename__ = "finance_sync_runs"

    __table_args__ = (
        Index("ix_finance_sync_runs_company_provider", "company_id", "provider_key"),
        Index("ix_finance_sync_runs_status", "status"),
        Index("ix_finance_sync_runs_started_at", "started_at"),
    )

    id = Column(Integer, Identity(start=1, increment=1), primary_key=True)
    company_id = Column(
        Integer,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
    )
    provider_key = Column(String(50), nullable=False)
    status = Column(
        Enum(FinanceSyncRunStatus),
        nullable=False,
        default=FinanceSyncRunStatus.queued,
    )
    started_at = Column(DateTime, nullable=True)
    ended_at = Column(DateTime, nullable=True)
    correlation_id = Column(String(36), nullable=False)
    triggered_by_user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    last_error = Column(Text, nullable=True)
    stats_json = Column(JSONB, nullable=True)
    last_successful_sync_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, nullable=False, default=utcnow)
    updated_at = Column(DateTime, nullable=False, default=utcnow, onupdate=utcnow)
