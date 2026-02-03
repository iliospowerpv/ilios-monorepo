"""Finance budgets router.

This router uses the Canonical Effective-Access Resolver (Phase C) for module-level
permission enforcement. All endpoints require Finance module permissions:
- GET endpoints require Finance:view
- POST/PATCH/DELETE endpoints require Finance:edit
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.finance import FinanceApprovalCRUD, FinanceBudgetCRUD, FinanceBudgetLineItemCRUD
from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.permission_guards import require_module_permission
from app.schema.finance import (
    FinanceApprovalCreate,
    FinanceApprovalSchema,
    FinanceBudgetCreate,
    FinanceBudgetDetailSchema,
    FinanceBudgetLineItemCreate,
    FinanceBudgetLineItemSchema,
    FinanceBudgetLineItemUpdate,
    FinanceBudgetPaginator,
    FinanceBudgetSchema,
    FinanceBudgetSubmit,
    FinanceBudgetUpdate,
)
from app.static.finance import FinanceBudgetStatus
from app.schema.user import CurrentUserSchema
from app.static.permissions import PermissionsModules

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
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    site_id: Optional[int] = None,
    status: Optional[str] = None,
):
    require_module_permission(
        user_id=current_user.id,
        company_id=company_id,
        db_session=db_session,
        module_key=PermissionsModules.finance.value,
        action="view",
    )
    status_enum = None
    if status:
        try:
            status_enum = FinanceBudgetStatus(status.lower())
        except ValueError:
            pass
    items, total = FinanceBudgetCRUD.get_all(db_session, company_id, site_id, skip, limit, status_enum)
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
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=company_id,
        db_session=db_session,
        module_key=PermissionsModules.finance.value,
        action="view",
    )
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
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=company_id,
        db_session=db_session,
        module_key=PermissionsModules.finance.value,
        action="edit",
    )
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
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=company_id,
        db_session=db_session,
        module_key=PermissionsModules.finance.value,
        action="edit",
    )
    budget = FinanceBudgetCRUD.get_by_id(db_session, budget_id)
    if not budget or budget.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    if budget.status != FinanceBudgetStatus.draft:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only edit budgets in Draft status",
        )
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
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=company_id,
        db_session=db_session,
        module_key=PermissionsModules.finance.value,
        action="edit",
    )
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
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=company_id,
        db_session=db_session,
        module_key=PermissionsModules.finance.value,
        action="edit",
    )
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
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=company_id,
        db_session=db_session,
        module_key=PermissionsModules.finance.value,
        action="edit",
    )
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
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=company_id,
        db_session=db_session,
        module_key=PermissionsModules.finance.value,
        action="edit",
    )
    budget = FinanceBudgetCRUD.get_by_id(db_session, budget_id)
    if not budget or budget.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    item = FinanceBudgetLineItemCRUD.get_by_id(db_session, item_id)
    if not item or item.budget_id != budget_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Line item not found")
    FinanceBudgetLineItemCRUD.delete(db_session, item)


@finance_budgets_router.post(
    "/{budget_id}/submit",
    response_model=FinanceBudgetDetailSchema,
    summary="Submit a budget for approval",
)
def submit_budget(
    company_id: int,
    budget_id: int,
    data: FinanceBudgetSubmit,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=company_id,
        db_session=db_session,
        module_key=PermissionsModules.finance.value,
        action="edit",
    )
    budget = FinanceBudgetCRUD.get_by_id(db_session, budget_id)
    if not budget or budget.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    if budget.status != FinanceBudgetStatus.draft:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only submit budgets in Draft status",
        )
    updated = FinanceBudgetCRUD.submit(db_session, budget)
    updated = FinanceBudgetCRUD.get_by_id(db_session, updated.id)
    return _budget_to_detail_schema(updated, db_session)


@finance_budgets_router.post(
    "/{budget_id}/approve",
    response_model=FinanceApprovalSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Approve or reject a budget",
)
def approve_budget(
    company_id: int,
    budget_id: int,
    data: FinanceApprovalCreate,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=company_id,
        db_session=db_session,
        module_key=PermissionsModules.finance.value,
        action="edit",
    )
    budget = FinanceBudgetCRUD.get_by_id(db_session, budget_id)
    if not budget or budget.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    if budget.status != FinanceBudgetStatus.submitted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only approve/reject budgets in Submitted status",
        )
    if data.decision.value == "override" and not data.override_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Override reason is required for override decisions",
        )
    approval = FinanceApprovalCRUD.create_for_budget(db_session, budget_id, current_user.id, data.model_dump())
    return FinanceApprovalSchema(
        id=approval.id,
        obligation_id=approval.obligation_id,
        budget_id=approval.budget_id,
        approved_by_id=approval.approved_by_id,
        decision=approval.decision,
        notes=approval.notes,
        override_reason=approval.override_reason,
        approved_at=approval.approved_at,
        approved_by_name=approval.approved_by.email if approval.approved_by else None,
    )


@finance_budgets_router.get(
    "/{budget_id}/approvals",
    response_model=list[FinanceApprovalSchema],
    summary="Get approval history for a budget",
)
def get_budget_approvals(
    company_id: int,
    budget_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=company_id,
        db_session=db_session,
        module_key=PermissionsModules.finance.value,
        action="view",
    )
    budget = FinanceBudgetCRUD.get_by_id(db_session, budget_id)
    if not budget or budget.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Budget not found")
    approvals = FinanceApprovalCRUD.get_by_budget(db_session, budget_id)
    return [
        FinanceApprovalSchema(
            id=a.id,
            obligation_id=a.obligation_id,
            budget_id=a.budget_id,
            approved_by_id=a.approved_by_id,
            decision=a.decision,
            notes=a.notes,
            override_reason=a.override_reason,
            approved_at=a.approved_at,
            approved_by_name=a.approved_by.email if a.approved_by else None,
        )
        for a in approvals
    ]
