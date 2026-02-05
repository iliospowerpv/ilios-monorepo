"""CRUD operations for FinanceSyncRun model."""

from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from app.crud.base_crud import BaseCRUD
from app.models.finance_sync_run import FinanceSyncRun, FinanceSyncRunStatus


class FinanceSyncRunCRUD(BaseCRUD):
    """CRUD operations for FinanceSyncRun."""

    def __init__(self, db_session: Session):
        super().__init__(model=FinanceSyncRun, db_session=db_session)

    def get_by_company(
        self,
        company_id: int,
        provider_key: Optional[str] = None,
        limit: int = 50,
    ) -> List[FinanceSyncRun]:
        q = self.db_session.query(FinanceSyncRun).filter(
            FinanceSyncRun.company_id == company_id
        )
        if provider_key:
            q = q.filter(FinanceSyncRun.provider_key == provider_key)
        return q.order_by(FinanceSyncRun.created_at.desc()).limit(limit).all()

    def create_run(
        self,
        company_id: int,
        provider_key: str,
        correlation_id: str,
        triggered_by_user_id: Optional[int] = None,
    ) -> FinanceSyncRun:
        run = FinanceSyncRun(
            company_id=company_id,
            provider_key=provider_key,
            status=FinanceSyncRunStatus.queued,
            correlation_id=correlation_id,
            triggered_by_user_id=triggered_by_user_id,
        )
        self.db_session.add(run)
        self.db_session.commit()
        self.db_session.refresh(run)
        return run

    def mark_running(self, run_id: int) -> Optional[FinanceSyncRun]:
        run = self.get_by_id(run_id)
        if not run:
            return None
        run.status = FinanceSyncRunStatus.running
        run.started_at = datetime.utcnow()
        self.db_session.commit()
        self.db_session.refresh(run)
        return run

    def mark_succeeded(
        self,
        run_id: int,
        stats: dict,
    ) -> Optional[FinanceSyncRun]:
        run = self.get_by_id(run_id)
        if not run:
            return None
        now = datetime.utcnow()
        run.status = FinanceSyncRunStatus.succeeded
        run.ended_at = now
        run.stats_json = stats
        run.last_successful_sync_at = now
        run.updated_at = now
        self.db_session.commit()
        self.db_session.refresh(run)
        return run

    def mark_failed(
        self,
        run_id: int,
        error_message: str,
        stats: Optional[dict] = None,
    ) -> Optional[FinanceSyncRun]:
        run = self.get_by_id(run_id)
        if not run:
            return None
        now = datetime.utcnow()
        run.status = FinanceSyncRunStatus.failed
        run.ended_at = now
        run.last_error = error_message
        if stats:
            run.stats_json = stats
        run.updated_at = now
        self.db_session.commit()
        self.db_session.refresh(run)
        return run
