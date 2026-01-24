"""Finance budgets router."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.finance import FinanceBudgetCRUD, FinanceBudgetLineItemCRUD
from app.db.session import get_session
from app.helpers.authorization import AuthorizedUser, get_authorized_company
from app.helpers.authorization.module_based.finance import FinancePermissions
from app.schema.finance import (
    FinanceBudgetCreate,
    FinanceBudgetDetailSchema,
    FinanceBudgetLineItemCreate,
    FinanceBudgetLineItemSchema,
    FinanceBudgetLineItemUpdate,
    FinanceBudgetPaginator,
    FinanceBudgetSchema,
    FinanceBudgetUpdate,
)
from app.schema.user import CurrentUserSchema
from app.static.permissions import PermissionsActions

finance_budgets_router = APIRouter()


def _budget_to_schema(budget, db_session) -> FinanceBudgetSchema:
    totals = FinanceBudgetCRUD.get_budget_totals(db_session, budget.id)
    return FinanceBudgetSchema(
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
    )


def _budget_to_detail_schema(budget, db_session) -> FinanceBudgetDetailSchema:
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
        for item in budget.line_items
    ]
    return FinanceBudgetDetailSchema(
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
        site_name=budget.site.name if budget.site else None,
    )


@finance_budgets_router.get(
    "",
    response_model=FinanceBudgetPaginator,
    summary="Get all budgets for a company",
)
def get_budgets(
    company_id: int,
    current_user: Annotated[
        CurrentUserSchema,
        Depends(AuthorizedUser([FinancePermissions(PermissionsActions.view)])),
    ],
    db_session: Session = Depends(get_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    site_id: Optional[int] = None,
):
    get_authorized_company(company_id, current_user, db_session)
    items, total = FinanceBudgetCRUD.get_all(db_session, company_id, site_id, skip, limit)
    return FinanceBudgetPaginator(
        items=[_budget_to_schema(b, db_session) for b in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@finance_budgets_router.get(
    "/{budget_id}",
    response_model=FinanceBudgetDetailSchema,
    summary="Get a budget by ID with line items",
)
def get_budget(
    company_id: int,
    budget_id: int,
    current_user: Annotated[
        CurrentUserSchema,
        Depends(AuthorizedUser([FinancePermissions(PermissionsActions.view)])),
    ],
    db_session: Session = Depends(get_session),
):
    get_authorized_company(company_id, current_user, db_session)
    budget = FinanceBudgetCRUD.get_by_id(db_session, budget_id)
    if not budget or budget.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    return _budget_to_detail_schema(budget, db_session)


@finance_budgets_router.post(
    "",
    response_model=FinanceBudgetDetailSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new budget",
)
def create_budget(
    company_id: int,
    data: FinanceBudgetCreate,
    current_user: Annotated[
        CurrentUserSchema,
        Depends(AuthorizedUser([FinancePermissions(PermissionsActions.edit)])),
    ],
    db_session: Session = Depends(get_session),
):
    get_authorized_company(company_id, current_user, db_session)
    budget = FinanceBudgetCRUD.create(db_session, company_id, current_user.id, data.model_dump())
    budget = FinanceBudgetCRUD.get_by_id(db_session, budget.id)
    return _budget_to_detail_schema(budget, db_session)


@finance_budgets_router.patch(
    "/{budget_id}",
    response_model=FinanceBudgetDetailSchema,
    summary="Update a budget",
)
def update_budget(
    company_id: int,
    budget_id: int,
    data: FinanceBudgetUpdate,
    current_user: Annotated[
        CurrentUserSchema,
        Depends(AuthorizedUser([FinancePermissions(PermissionsActions.edit)])),
    ],
    db_session: Session = Depends(get_session),
):
    get_authorized_company(company_id, current_user, db_session)
    budget = FinanceBudgetCRUD.get_by_id(db_session, budget_id)
    if not budget or budget.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    updated = FinanceBudgetCRUD.update(db_session, budget, data.model_dump(exclude_unset=True))
    updated = FinanceBudgetCRUD.get_by_id(db_session, updated.id)
    return _budget_to_detail_schema(updated, db_session)


@finance_budgets_router.delete(
    "/{budget_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a budget",
)
def delete_budget(
    company_id: int,
    budget_id: int,
    current_user: Annotated[
        CurrentUserSchema,
        Depends(AuthorizedUser([FinancePermissions(PermissionsActions.edit)])),
    ],
    db_session: Session = Depends(get_session),
):
    get_authorized_company(company_id, current_user, db_session)
    budget = FinanceBudgetCRUD.get_by_id(db_session, budget_id)
    if not budget or budget.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    FinanceBudgetCRUD.delete(db_session, budget)


@finance_budgets_router.post(
    "/{budget_id}/line-items",
    response_model=FinanceBudgetLineItemSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Add a line item to a budget",
)
def create_line_item(
    company_id: int,
    budget_id: int,
    data: FinanceBudgetLineItemCreate,
    current_user: Annotated[
        CurrentUserSchema,
        Depends(AuthorizedUser([FinancePermissions(PermissionsActions.edit)])),
    ],
    db_session: Session = Depends(get_session),
):
    get_authorized_company(company_id, current_user, db_session)
    budget = FinanceBudgetCRUD.get_by_id(db_session, budget_id)
    if not budget or budget.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    item = FinanceBudgetLineItemCRUD.create(db_session, budget_id, data.model_dump())
    return FinanceBudgetLineItemSchema.model_validate(item, from_attributes=True)


@finance_budgets_router.patch(
    "/{budget_id}/line-items/{item_id}",
    response_model=FinanceBudgetLineItemSchema,
    summary="Update a line item",
)
def update_line_item(
    company_id: int,
    budget_id: int,
    item_id: int,
    data: FinanceBudgetLineItemUpdate,
    current_user: Annotated[
        CurrentUserSchema,
        Depends(AuthorizedUser([FinancePermissions(PermissionsActions.edit)])),
    ],
    db_session: Session = Depends(get_session),
):
    get_authorized_company(company_id, current_user, db_session)
    budget = FinanceBudgetCRUD.get_by_id(db_session, budget_id)
    if not budget or budget.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    item = FinanceBudgetLineItemCRUD.get_by_id(db_session, item_id)
    if not item or item.budget_id != budget_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Line item not found")
    updated = FinanceBudgetLineItemCRUD.update(db_session, item, data.model_dump(exclude_unset=True))
    return FinanceBudgetLineItemSchema.model_validate(updated, from_attributes=True)


@finance_budgets_router.delete(
    "/{budget_id}/line-items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a line item",
)
def delete_line_item(
    company_id: int,
    budget_id: int,
    item_id: int,
    current_user: Annotated[
        CurrentUserSchema,
        Depends(AuthorizedUser([FinancePermissions(PermissionsActions.edit)])),
    ],
    db_session: Session = Depends(get_session),
):
    get_authorized_company(company_id, current_user, db_session)
    budget = FinanceBudgetCRUD.get_by_id(db_session, budget_id)
    if not budget or budget.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    item = FinanceBudgetLineItemCRUD.get_by_id(db_session, item_id)
    if not item or item.budget_id != budget_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Line item not found")
    FinanceBudgetLineItemCRUD.delete(db_session, item)
