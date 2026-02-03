"""Finance actuals router.

This router uses the Canonical Effective-Access Resolver (Phase C) for module-level
permission enforcement. All endpoints require Finance module permissions:
- GET endpoints require Finance:view
- POST/PATCH/DELETE endpoints require Finance:edit
"""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.finance import FinanceActualCRUD
from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.permission_guards import require_module_permission
from app.schema.finance import (
    FinanceActualCreate,
    FinanceActualPaginator,
    FinanceActualSchema,
    FinanceActualUpdate,
)
from app.schema.user import CurrentUserSchema
from app.static.permissions import PermissionsModules

finance_actuals_router = APIRouter()


def _actual_to_schema(actual) -> FinanceActualSchema:
    return FinanceActualSchema(
        id=actual.id,
        company_id=actual.company_id,
        site_id=actual.site_id,
        vendor_id=actual.vendor_id,
        category=actual.category,
        description=actual.description,
        amount=actual.amount,
        transaction_date=actual.transaction_date,
        reference_id=actual.reference_id,
        source_system=actual.source_system,
        created_at=actual.created_at,
        updated_at=actual.updated_at,
        created_by_id=actual.created_by_id,
        vendor_name=actual.vendor.name if actual.vendor else None,
        site_name=actual.site.name if actual.site else None,
    )


@finance_actuals_router.get(
    "",
    response_model=FinanceActualPaginator,
    summary="Get all actuals for a company",
)
def get_actuals(
    company_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    site_id: Optional[int] = None,
):
    require_module_permission(
        user_id=current_user.id,
        company_id=company_id,
        db_session=db_session,
        module_key=PermissionsModules.finance.value,
        action="view",
    )
    items, total = FinanceActualCRUD.get_all(db_session, company_id, site_id, skip, limit)
    return FinanceActualPaginator(
        items=[_actual_to_schema(a) for a in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@finance_actuals_router.get(
    "/{actual_id}",
    response_model=FinanceActualSchema,
    summary="Get an actual by ID",
)
def get_actual(
    company_id: int,
    actual_id: int,
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
    actual = FinanceActualCRUD.get_by_id(db_session, actual_id)
    if not actual or actual.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Actual not found")
    return _actual_to_schema(actual)


@finance_actuals_router.post(
    "",
    response_model=FinanceActualSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new actual",
)
def create_actual(
    company_id: int,
    data: FinanceActualCreate,
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
    actual = FinanceActualCRUD.create(db_session, company_id, current_user.id, data.model_dump())
    return _actual_to_schema(actual)


@finance_actuals_router.patch(
    "/{actual_id}",
    response_model=FinanceActualSchema,
    summary="Update an actual",
)
def update_actual(
    company_id: int,
    actual_id: int,
    data: FinanceActualUpdate,
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
    actual = FinanceActualCRUD.get_by_id(db_session, actual_id)
    if not actual or actual.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Actual not found")
    updated = FinanceActualCRUD.update(db_session, actual, data.model_dump(exclude_unset=True))
    return _actual_to_schema(updated)


@finance_actuals_router.delete(
    "/{actual_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an actual",
)
def delete_actual(
    company_id: int,
    actual_id: int,
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
    actual = FinanceActualCRUD.get_by_id(db_session, actual_id)
    if not actual or actual.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Actual not found")
    FinanceActualCRUD.delete(db_session, actual)
