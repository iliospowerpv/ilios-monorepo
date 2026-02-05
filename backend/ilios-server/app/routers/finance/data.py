"""Finance data read-only endpoints.

Read endpoints require finance:view (any role with view permission).
Endpoints use query-param scoping: ?company_id=...
"""

from datetime import date
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.permission_guards import require_module_permission
from app.schema.user import CurrentUserSchema
from app.static.permissions import PermissionsModules
from app.crud.finance_account import FinanceAccountCRUD
from app.crud.finance_transaction import FinanceTransactionCRUD
from app.crud.finance_sync_run import FinanceSyncRunCRUD
from app.crud.company import CompanyCRUD
from app.schema.finance_data import (
    FinanceAccountResponse,
    FinanceAccountsListResponse,
    FinanceTransactionResponse,
    FinanceTransactionsListResponse,
    FinanceSyncRunResponse,
    FinanceSyncRunsListResponse,
    FinanceHealthSummaryResponse,
)
from app.services.finance.health_service import FinanceHealthService


router = APIRouter(tags=["finance-data"])


def _require_finance_view(
    db: Session,
    current_user: CurrentUserSchema,
    company_id: int,
) -> None:
    """Guard: finance:view + company access."""
    if current_user.is_system_user:
        return
    require_module_permission(
        user_id=current_user.id,
        company_id=company_id,
        db_session=db,
        module_key=PermissionsModules.finance.value,
        action="view",
    )


def _ensure_company_exists(db: Session, company_id: int) -> None:
    company = CompanyCRUD(db).get_by_id(company_id)
    if not company:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Company not found",
        )


@router.get(
    "/accounts",
    response_model=FinanceAccountsListResponse,
    summary="List finance accounts for a company",
)
def list_accounts(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db: Session = Depends(get_session),
    company_id: int = Query(..., description="Company ID to scope accounts"),
    provider_key: Optional[str] = None,
    is_active: Optional[bool] = None,
) -> FinanceAccountsListResponse:
    _require_finance_view(db, current_user, company_id)
    _ensure_company_exists(db, company_id)

    crud = FinanceAccountCRUD(db)
    accounts = crud.get_by_company(
        company_id, provider_key=provider_key, is_active=is_active
    )
    return FinanceAccountsListResponse(
        accounts=[FinanceAccountResponse.model_validate(a) for a in accounts],
        total=len(accounts),
    )


@router.get(
    "/transactions",
    response_model=FinanceTransactionsListResponse,
    summary="List finance transactions for a company",
)
def list_transactions(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db: Session = Depends(get_session),
    company_id: int = Query(..., description="Company ID to scope transactions"),
    provider_key: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
    account_external_id: Optional[str] = None,
    limit: int = 500,
    offset: int = 0,
) -> FinanceTransactionsListResponse:
    _require_finance_view(db, current_user, company_id)
    _ensure_company_exists(db, company_id)

    crud = FinanceTransactionCRUD(db)
    txns = crud.get_by_company(
        company_id,
        provider_key=provider_key,
        date_from=date_from,
        date_to=date_to,
        account_external_id=account_external_id,
        limit=limit,
        offset=offset,
    )
    return FinanceTransactionsListResponse(
        transactions=[FinanceTransactionResponse.model_validate(t) for t in txns],
        total=len(txns),
    )


@router.get(
    "/sync-runs",
    response_model=FinanceSyncRunsListResponse,
    summary="List sync runs for a company",
)
def list_sync_runs(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db: Session = Depends(get_session),
    company_id: int = Query(..., description="Company ID to scope sync runs"),
    provider_key: Optional[str] = None,
    limit: int = 50,
) -> FinanceSyncRunsListResponse:
    _require_finance_view(db, current_user, company_id)
    _ensure_company_exists(db, company_id)

    crud = FinanceSyncRunCRUD(db)
    runs = crud.get_by_company(company_id, provider_key=provider_key, limit=limit)
    return FinanceSyncRunsListResponse(
        sync_runs=[
            FinanceSyncRunResponse(
                id=r.id,
                company_id=r.company_id,
                provider_key=r.provider_key,
                status=r.status.value if hasattr(r.status, "value") else str(r.status),
                started_at=r.started_at,
                ended_at=r.ended_at,
                correlation_id=r.correlation_id,
                triggered_by_user_id=r.triggered_by_user_id,
                last_error=r.last_error,
                stats_json=r.stats_json,
                last_successful_sync_at=r.last_successful_sync_at,
                created_at=r.created_at,
                updated_at=r.updated_at,
            )
            for r in runs
        ],
        total=len(runs),
    )


@router.get(
    "/summary",
    response_model=FinanceHealthSummaryResponse,
    summary="Finance health summary for a company",
    description="Returns compact health signals suitable for dashboard widgets. Requires finance:view.",
)
def get_finance_summary(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db: Session = Depends(get_session),
    company_id: int = Query(..., description="Company ID to compute summary for"),
) -> FinanceHealthSummaryResponse:
    _require_finance_view(db, current_user, company_id)
    _ensure_company_exists(db, company_id)

    svc = FinanceHealthService(db)
    summary = svc.compute_summary(company_id)

    return FinanceHealthSummaryResponse(
        sync_status=summary.sync_status,
        last_sync_at=summary.last_sync_at,
        last_sync_error=summary.last_sync_error,
        accounts_count=summary.accounts_count,
        transactions_count_30d=summary.transactions_count_30d,
        unmapped_projects_count=summary.unmapped_projects_count,
        needs_attention_reasons=summary.needs_attention_reasons,
    )
