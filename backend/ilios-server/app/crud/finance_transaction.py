"""CRUD operations for FinanceTransaction model with upsert support."""

from datetime import date
from typing import List, Optional

from sqlalchemy import and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.crud.base_crud import BaseCRUD
from app.models.finance_transaction import FinanceTransaction


class FinanceTransactionCRUD(BaseCRUD):
    """CRUD operations for FinanceTransaction with upsert semantics."""

    def __init__(self, db_session: Session):
        super().__init__(model=FinanceTransaction, db_session=db_session)

    def get_by_company(
        self,
        company_id: int,
        provider_key: Optional[str] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        account_external_id: Optional[str] = None,
        limit: int = 500,
        offset: int = 0,
    ) -> List[FinanceTransaction]:
        q = self.db_session.query(FinanceTransaction).filter(
            FinanceTransaction.company_id == company_id
        )
        if provider_key:
            q = q.filter(FinanceTransaction.provider_key == provider_key)
        if date_from:
            q = q.filter(FinanceTransaction.txn_date >= date_from)
        if date_to:
            q = q.filter(FinanceTransaction.txn_date <= date_to)
        if account_external_id:
            q = q.filter(FinanceTransaction.account_external_id == account_external_id)
        return q.order_by(FinanceTransaction.txn_date.desc()).limit(limit).offset(offset).all()

    def upsert_batch(
        self,
        company_id: int,
        provider_key: str,
        transactions: list[dict],
    ) -> int:
        """Upsert a batch of transactions. Returns count of rows affected.

        Uses PostgreSQL ON CONFLICT ... DO UPDATE for idempotent reruns.
        Each dict must contain: external_id, account_external_id, amount, txn_date.
        Optional keys: currency, description, counterparty, project_external_id, raw_json.
        """
        if not transactions:
            return 0

        rows = []
        for txn in transactions:
            rows.append({
                "company_id": company_id,
                "provider_key": provider_key,
                "external_id": txn["external_id"],
                "account_external_id": txn["account_external_id"],
                "amount": txn["amount"],
                "currency": txn.get("currency", "USD"),
                "txn_date": txn["txn_date"],
                "description": txn.get("description"),
                "counterparty": txn.get("counterparty"),
                "project_external_id": txn.get("project_external_id"),
                "raw_json": txn.get("raw_json"),
            })

        stmt = pg_insert(FinanceTransaction).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_finance_txns_company_provider_ext",
            set_={
                "account_external_id": stmt.excluded.account_external_id,
                "amount": stmt.excluded.amount,
                "currency": stmt.excluded.currency,
                "txn_date": stmt.excluded.txn_date,
                "description": stmt.excluded.description,
                "counterparty": stmt.excluded.counterparty,
                "project_external_id": stmt.excluded.project_external_id,
                "raw_json": stmt.excluded.raw_json,
            },
        )
        result = self.db_session.execute(stmt)
        self.db_session.flush()
        return result.rowcount

    def count_by_company_provider(self, company_id: int, provider_key: str) -> int:
        return (
            self.db_session.query(FinanceTransaction)
            .filter(
                and_(
                    FinanceTransaction.company_id == company_id,
                    FinanceTransaction.provider_key == provider_key,
                )
            )
            .count()
        )
