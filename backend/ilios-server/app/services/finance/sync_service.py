"""Finance Sync Service: orchestrates read-only data ingestion.

Fetches accounts and transactions from an external provider,
upserts them into normalized tables, and tracks execution via sync runs.
"""

import logging
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.crud.finance_account import FinanceAccountCRUD
from app.crud.finance_integration import FinanceIntegrationCRUD
from app.crud.finance_sync_run import FinanceSyncRunCRUD
from app.crud.finance_transaction import FinanceTransactionCRUD
from app.models.finance_sync_run import FinanceSyncRun
from app.services.finance.registry import get_provider_registry
from app.services.finance.provider import FinanceProviderError

logger = logging.getLogger(__name__)


class FinanceSyncService:
    """Orchestrates a single sync run for a company+provider pair."""

    def __init__(self, db: Session):
        self._db = db
        self._account_crud = FinanceAccountCRUD(db)
        self._txn_crud = FinanceTransactionCRUD(db)
        self._run_crud = FinanceSyncRunCRUD(db)
        self._integration_crud = FinanceIntegrationCRUD(db)

    def execute_sync(
        self,
        company_id: int,
        provider_key: str,
        triggered_by_user_id: Optional[int] = None,
    ) -> FinanceSyncRun:
        """Run a full sync: fetch from provider, upsert locally, track progress.

        Returns the completed FinanceSyncRun record.
        """
        correlation_id = str(uuid.uuid4())

        logger.info(
            "finance_sync_start",
            extra={
                "company_id": company_id,
                "provider_key": provider_key,
                "correlation_id": correlation_id,
            },
        )

        run = self._run_crud.create_run(
            company_id=company_id,
            provider_key=provider_key,
            correlation_id=correlation_id,
            triggered_by_user_id=triggered_by_user_id,
        )

        self._run_crud.mark_running(run.id)

        stats = {
            "accounts_upserted": 0,
            "txns_upserted": 0,
            "txns_skipped": 0,
        }

        try:
            integration = self._integration_crud.get_by_company_and_provider(
                company_id, provider_key
            )
            if not integration:
                raise FinanceProviderError(
                    message=f"No integration configured for provider {provider_key}",
                    provider_key=provider_key,
                    error_code="INTEGRATION_NOT_FOUND",
                )

            credentials = self._integration_crud.get_decrypted_credentials(
                integration.id
            )
            if not credentials:
                raise FinanceProviderError(
                    message="No credentials configured for this integration",
                    provider_key=provider_key,
                    error_code="MISSING_CREDENTIALS",
                )

            registry = get_provider_registry()
            provider = registry.create_provider(
                provider_key=provider_key,
                credentials=credentials,
                config=integration.config_json,
            )

            t0 = datetime.utcnow()
            raw_accounts = provider.fetch_accounts()
            account_dicts = [
                {
                    "external_id": a.id,
                    "name": a.name,
                    "account_type": a.account_type,
                    "is_active": a.is_active,
                    "raw_json": a.metadata,
                }
                for a in raw_accounts
            ]
            accounts_upserted = self._account_crud.upsert_batch(
                company_id, provider_key, account_dicts
            )
            stats["accounts_upserted"] = accounts_upserted

            logger.info(
                "finance_sync_accounts_done",
                extra={
                    "correlation_id": correlation_id,
                    "accounts_fetched": len(raw_accounts),
                    "accounts_upserted": accounts_upserted,
                    "duration_ms": int(
                        (datetime.utcnow() - t0).total_seconds() * 1000
                    ),
                },
            )

            t1 = datetime.utcnow()
            raw_txns = provider.fetch_transactions()
            txn_dicts = [
                {
                    "external_id": t.id,
                    "account_external_id": t.account_id,
                    "amount": t.amount,
                    "txn_date": t.date.date() if isinstance(t.date, datetime) else t.date,
                    "description": t.description,
                    "counterparty": getattr(t, "reference", None),
                    "raw_json": t.metadata,
                }
                for t in raw_txns
            ]
            txns_upserted = self._txn_crud.upsert_batch(
                company_id, provider_key, txn_dicts
            )
            stats["txns_upserted"] = txns_upserted

            logger.info(
                "finance_sync_txns_done",
                extra={
                    "correlation_id": correlation_id,
                    "txns_fetched": len(raw_txns),
                    "txns_upserted": txns_upserted,
                    "duration_ms": int(
                        (datetime.utcnow() - t1).total_seconds() * 1000
                    ),
                },
            )

            self._db.commit()
            run = self._run_crud.mark_succeeded(run.id, stats)

            logger.info(
                "finance_sync_succeeded",
                extra={
                    "correlation_id": correlation_id,
                    "company_id": company_id,
                    "provider_key": provider_key,
                    "stats": stats,
                },
            )
            return run

        except Exception as exc:
            self._db.rollback()
            error_msg = str(exc)
            logger.error(
                "finance_sync_failed",
                extra={
                    "correlation_id": correlation_id,
                    "company_id": company_id,
                    "provider_key": provider_key,
                    "error": error_msg,
                    "stats": stats,
                },
                exc_info=True,
            )
            run = self._run_crud.mark_failed(run.id, error_msg, stats)
            return run
