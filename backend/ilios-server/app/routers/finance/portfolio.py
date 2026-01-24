"""Finance portfolio router."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.crud.finance import (
    FinanceActualCRUD,
    FinanceApprovalCRUD,
    FinanceBudgetCRUD,
    FinanceObligationCRUD,
    FinancePortfolioCRUD,
)
from app.db.session import get_session
from app.helpers.authorization import AuthorizedUser, get_authorized_company, get_authorized_site
from app.helpers.authorization.module_based.finance import FinancePermissions
from app.schema.finance import (
    FinanceApprovalSchema,
    FinanceBudgetDetailSchema,
    FinanceBudgetLineItemSchema,
    FinanceDataRoomPackageSchema,
    FinanceObligationSchema,
    FinanceActualSchema,
    FinancePortfolioResponseSchema,
    FinancePortfolioSummarySchema,
    FinanceSiteSummarySchema,
)
from app.schema.user import CurrentUserSchema
from app.static.permissions import PermissionsActions

finance_portfolio_router = APIRouter()


@finance_portfolio_router.get(
    "/summary",
    response_model=FinancePortfolioResponseSchema,
    summary="Get portfolio-level finance summary",
)
def get_portfolio_summary(
    company_id: int,
    current_user: Annotated[
        CurrentUserSchema,
        Depends(AuthorizedUser([FinancePermissions(PermissionsActions.view)])),
    ],
    db_session: Session = Depends(get_session),
):
    get_authorized_company(company_id, current_user, db_session)
    result = FinancePortfolioCRUD.get_portfolio_summary(db_session, company_id)
    return FinancePortfolioResponseSchema(
        summary=FinancePortfolioSummarySchema(**result["summary"]),
        sites=[FinanceSiteSummarySchema(**s) for s in result["sites"]],
    )


@finance_portfolio_router.get(
    "/sites/{site_id}/summary",
    response_model=FinanceSiteSummarySchema,
    summary="Get finance summary for a specific site",
)
def get_site_summary(
    company_id: int,
    site_id: int,
    current_user: Annotated[
        CurrentUserSchema,
        Depends(AuthorizedUser([FinancePermissions(PermissionsActions.view)])),
    ],
    db_session: Session = Depends(get_session),
):
    get_authorized_company(company_id, current_user, db_session)
    site = get_authorized_site(site_id, current_user, db_session)
    if site.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    result = FinancePortfolioCRUD.get_site_summary(db_session, site)
    return FinanceSiteSummarySchema(**result)


@finance_portfolio_router.get(
    "/sites/{site_id}/data-room-package",
    summary="Generate data room finance package for a site",
)
def get_data_room_package(
    company_id: int,
    site_id: int,
    current_user: Annotated[
        CurrentUserSchema,
        Depends(AuthorizedUser([FinancePermissions(PermissionsActions.view)])),
    ],
    db_session: Session = Depends(get_session),
):
    get_authorized_company(company_id, current_user, db_session)
    site = get_authorized_site(site_id, current_user, db_session)
    if site.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Site not found")
    budgets, _ = FinanceBudgetCRUD.get_all(db_session, company_id, site_id, 0, 1000)
    budget_details = []
    for budget in budgets:
        budget_full = FinanceBudgetCRUD.get_by_id(db_session, budget.id)
        totals = FinanceBudgetCRUD.get_budget_totals(db_session, budget.id)
        line_items = [
            FinanceBudgetLineItemSchema(
                id=item.id,
                budget_id=item.budget_id,
                vendor_id=item.vendor_id,
                category=item.category,
                description=item.description,
                amount_planned=item.amount_planned,
                amount_authorized=item.amount_authorized,
                amount_actual=item.amount_actual,
                start_date=item.start_date,
                end_date=item.end_date,
                created_at=item.created_at,
                updated_at=item.updated_at,
                vendor_name=item.vendor.name if item.vendor else None,
            )
            for item in budget_full.line_items
        ]
        budget_details.append(
            FinanceBudgetDetailSchema(
                id=budget.id,
                company_id=budget.company_id,
                site_id=budget.site_id,
                deal_id=budget.deal_id,
                name=budget.name,
                description=budget.description,
                period_start=budget.period_start,
                period_end=budget.period_end,
                status=budget.status,
                created_at=budget.created_at,
                updated_at=budget.updated_at,
                created_by_id=budget.created_by_id,
                total_planned=totals["total_planned"],
                total_authorized=totals["total_authorized"],
                total_actual=totals["total_actual"],
                variance=totals["variance"],
                line_items=line_items,
                site_name=site.name,
            )
        )
    obligations, _ = FinanceObligationCRUD.get_all(db_session, company_id, site_id, None, 0, 1000)
    obligation_schemas = []
    all_approvals = []
    for obl in obligations:
        obl_full = FinanceObligationCRUD.get_by_id(db_session, obl.id)
        obligation_schemas.append(
            FinanceObligationSchema(
                id=obl.id,
                company_id=obl.company_id,
                site_id=obl.site_id,
                vendor_id=obl.vendor_id,
                budget_line_item_id=obl.budget_line_item_id,
                obligation_type=obl.obligation_type,
                description=obl.description,
                amount_requested=obl.amount_requested,
                requested_date=obl.requested_date,
                due_date=obl.due_date,
                status=obl.status,
                prerequisite_snapshot=obl.prerequisite_snapshot,
                reference_number=obl.reference_number,
                created_at=obl.created_at,
                updated_at=obl.updated_at,
                created_by_id=obl.created_by_id,
                vendor_name=obl_full.vendor.name if obl_full.vendor else None,
                site_name=site.name,
            )
        )
        approvals = FinanceApprovalCRUD.get_by_obligation(db_session, obl.id)
        for a in approvals:
            all_approvals.append(
                FinanceApprovalSchema(
                    id=a.id,
                    obligation_id=a.obligation_id,
                    approved_by_id=a.approved_by_id,
                    decision=a.decision,
                    notes=a.notes,
                    override_reason=a.override_reason,
                    approved_at=a.approved_at,
                    approved_by_name=a.approved_by.email if a.approved_by else None,
                )
            )
    actuals, _ = FinanceActualCRUD.get_all(db_session, company_id, site_id, 0, 1000)
    actual_schemas = [
        FinanceActualSchema(
            id=a.id,
            company_id=a.company_id,
            site_id=a.site_id,
            vendor_id=a.vendor_id,
            category=a.category,
            description=a.description,
            amount=a.amount,
            transaction_date=a.transaction_date,
            reference_id=a.reference_id,
            source_system=a.source_system,
            created_at=a.created_at,
            updated_at=a.updated_at,
            created_by_id=a.created_by_id,
            vendor_name=a.vendor.name if a.vendor else None,
            site_name=site.name,
        )
        for a in actuals
    ]
    summary = FinancePortfolioCRUD.get_site_summary(db_session, site)
    package = FinanceDataRoomPackageSchema(
        site_id=site.id,
        site_name=site.name,
        generated_at=datetime.utcnow(),
        budgets=budget_details,
        obligations=obligation_schemas,
        approvals=all_approvals,
        actuals=actual_schemas,
        summary=FinanceSiteSummarySchema(**summary),
    )
    return JSONResponse(
        content=package.model_dump(mode="json"),
        headers={
            "Content-Disposition": f"attachment; filename=finance_package_site_{site_id}.json"
        },
    )
