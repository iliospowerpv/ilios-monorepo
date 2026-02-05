"""Finance Health Service – computes company-level finance health summary.

Computation rules (v1):
- not_configured: no finance_integration exists for this company
- never_synced: integration configured but no successful sync run
- running: latest sync run status is running or queued
- error: latest sync run failed OR integration test failing
- healthy: last successful sync within threshold AND no last_error
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional

from sqlalchemy import and_, func
from sqlalchemy.orm import Session

from app.crud.finance_integration import FinanceIntegrationCRUD
from app.models.finance_account import FinanceAccount
from app.models.finance_sync_run import FinanceSyncRun, FinanceSyncRunStatus
from app.models.finance_transaction import FinanceTransaction

logger = logging.getLogger(__name__)

HEALTHY_SYNC_THRESHOLD_HOURS = 24


class FinanceHealthSummary:
    __slots__ = (
        "sync_status",
        "last_sync_at",
        "last_sync_error",
        "accounts_count",
        "transactions_count_30d",
        "unmapped_projects_count",
        "needs_attention_reasons",
    )

    def __init__(
        self,
        sync_status: str,
        last_sync_at: Optional[datetime],
        last_sync_error: Optional[str],
        accounts_count: int,
        transactions_count_30d: int,
        unmapped_projects_count: Optional[int],
        needs_attention_reasons: List[str],
    ):
        self.sync_status = sync_status
        self.last_sync_at = last_sync_at
        self.last_sync_error = last_sync_error
        self.accounts_count = accounts_count
        self.transactions_count_30d = transactions_count_30d
        self.unmapped_projects_count = unmapped_projects_count
        self.needs_attention_reasons = needs_attention_reasons


class FinanceHealthService:
    def __init__(self, db: Session):
        self._db = db

    def compute_summary(self, company_id: int) -> FinanceHealthSummary:
        integrations = FinanceIntegrationCRUD(self._db).get_by_company(company_id)
        if not integrations:
            return FinanceHealthSummary(
                sync_status="not_configured",
                last_sync_at=None,
                last_sync_error=None,
                accounts_count=0,
                transactions_count_30d=0,
                unmapped_projects_count=None,
                needs_attention_reasons=["no_integration_configured"],
            )

        latest_run = self._latest_sync_run(company_id)
        latest_success = self._latest_successful_run(company_id)

        sync_status = self._derive_status(integrations, latest_run, latest_success)

        last_sync_at = latest_success.ended_at if latest_success else None
        last_sync_error = latest_run.last_error if latest_run and latest_run.last_error else None

        accounts_count = self._count_accounts(company_id)
        transactions_count_30d = self._count_transactions_30d(company_id)

        needs_attention = self._compute_attention_reasons(
            sync_status, integrations, latest_run, latest_success, accounts_count
        )

        return FinanceHealthSummary(
            sync_status=sync_status,
            last_sync_at=last_sync_at,
            last_sync_error=last_sync_error,
            accounts_count=accounts_count,
            transactions_count_30d=transactions_count_30d,
            unmapped_projects_count=None,
            needs_attention_reasons=needs_attention,
        )

    def _latest_sync_run(self, company_id: int) -> Optional[FinanceSyncRun]:
        return (
            self._db.query(FinanceSyncRun)
            .filter(FinanceSyncRun.company_id == company_id)
            .order_by(FinanceSyncRun.created_at.desc())
            .first()
        )

    def _latest_successful_run(self, company_id: int) -> Optional[FinanceSyncRun]:
        return (
            self._db.query(FinanceSyncRun)
            .filter(
                and_(
                    FinanceSyncRun.company_id == company_id,
                    FinanceSyncRun.status == FinanceSyncRunStatus.succeeded,
                )
            )
            .order_by(FinanceSyncRun.ended_at.desc())
            .first()
        )

    def _count_accounts(self, company_id: int) -> int:
        return (
            self._db.query(func.count(FinanceAccount.id))
            .filter(FinanceAccount.company_id == company_id)
            .scalar()
            or 0
        )

    def _count_transactions_30d(self, company_id: int) -> int:
        cutoff = datetime.utcnow().date() - timedelta(days=30)
        return (
            self._db.query(func.count(FinanceTransaction.id))
            .filter(
                and_(
                    FinanceTransaction.company_id == company_id,
                    FinanceTransaction.txn_date >= cutoff,
                )
            )
            .scalar()
            or 0
        )

    def _derive_status(self, integrations, latest_run, latest_success) -> str:
        if latest_run:
            run_status = (
                latest_run.status.value
                if hasattr(latest_run.status, "value")
                else str(latest_run.status)
            )
            if run_status in ("running", "queued"):
                return "running"

            if run_status == "failed":
                return "error"

        has_error_integration = any(
            getattr(i, "status", None)
            and (
                (i.status.value if hasattr(i.status, "value") else str(i.status))
                == "error"
            )
            for i in integrations
        )
        if has_error_integration and not latest_success:
            return "error"

        if not latest_success:
            return "never_synced"

        threshold = datetime.utcnow() - timedelta(hours=HEALTHY_SYNC_THRESHOLD_HOURS)
        if latest_success.ended_at and latest_success.ended_at >= threshold:
            if has_error_integration:
                return "error"
            return "healthy"

        return "error"

    def _compute_attention_reasons(
        self, sync_status, integrations, latest_run, latest_success, accounts_count
    ) -> List[str]:
        reasons: List[str] = []

        if sync_status == "error":
            if latest_run and latest_run.last_error:
                reasons.append("last_sync_failed")
            has_error_int = any(
                getattr(i, "status", None)
                and (
                    (i.status.value if hasattr(i.status, "value") else str(i.status))
                    == "error"
                )
                for i in integrations
            )
            if has_error_int:
                reasons.append("integration_test_failing")

        if sync_status == "never_synced":
            reasons.append("never_synced")

        if latest_success:
            threshold = datetime.utcnow() - timedelta(hours=HEALTHY_SYNC_THRESHOLD_HOURS)
            if latest_success.ended_at and latest_success.ended_at < threshold:
                reasons.append("sync_stale")

        if accounts_count == 0 and sync_status not in ("not_configured", "never_synced"):
            reasons.append("no_accounts")

        return reasons
