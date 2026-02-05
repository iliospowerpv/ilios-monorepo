"""CRUD operations for FinanceAccount model with upsert support."""

from typing import List, Optional

from sqlalchemy import and_
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.crud.base_crud import BaseCRUD
from app.models.finance_account import FinanceAccount


class FinanceAccountCRUD(BaseCRUD):
    """CRUD operations for FinanceAccount with upsert semantics."""

    def __init__(self, db_session: Session):
        super().__init__(model=FinanceAccount, db_session=db_session)

    def get_by_company(
        self,
        company_id: int,
        provider_key: Optional[str] = None,
        is_active: Optional[bool] = None,
    ) -> List[FinanceAccount]:
        q = self.db_session.query(FinanceAccount).filter(
            FinanceAccount.company_id == company_id
        )
        if provider_key:
            q = q.filter(FinanceAccount.provider_key == provider_key)
        if is_active is not None:
            q = q.filter(FinanceAccount.is_active == is_active)
        return q.order_by(FinanceAccount.name).all()

    def upsert_batch(
        self,
        company_id: int,
        provider_key: str,
        accounts: list[dict],
    ) -> int:
        """Upsert a batch of accounts. Returns count of rows affected.

        Uses PostgreSQL ON CONFLICT ... DO UPDATE for idempotent reruns.
        Each dict must contain: external_id, name.
        Optional keys: account_type, parent_external_id, is_active, raw_json.
        """
        if not accounts:
            return 0

        rows = []
        for acct in accounts:
            rows.append({
                "company_id": company_id,
                "provider_key": provider_key,
                "external_id": acct["external_id"],
                "name": acct["name"],
                "account_type": acct.get("account_type"),
                "parent_external_id": acct.get("parent_external_id"),
                "is_active": acct.get("is_active", True),
                "raw_json": acct.get("raw_json"),
            })

        stmt = pg_insert(FinanceAccount).values(rows)
        stmt = stmt.on_conflict_do_update(
            constraint="uq_finance_accounts_company_provider_ext",
            set_={
                "name": stmt.excluded.name,
                "account_type": stmt.excluded.account_type,
                "parent_external_id": stmt.excluded.parent_external_id,
                "is_active": stmt.excluded.is_active,
                "raw_json": stmt.excluded.raw_json,
            },
        )
        result = self.db_session.execute(stmt)
        self.db_session.flush()
        return result.rowcount

    def count_by_company_provider(self, company_id: int, provider_key: str) -> int:
        return (
            self.db_session.query(FinanceAccount)
            .filter(
                and_(
                    FinanceAccount.company_id == company_id,
                    FinanceAccount.provider_key == provider_key,
                )
            )
            .count()
        )
