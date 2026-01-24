"""Finance vendors router."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.finance import FinanceVendorCRUD
from app.db.session import get_session
from app.helpers.authorization import AuthorizedUser, get_authorized_company
from app.helpers.authorization.module_based.finance import FinancePermissions
from app.schema.finance import (
    FinanceVendorCreate,
    FinanceVendorPaginator,
    FinanceVendorSchema,
    FinanceVendorUpdate,
)
from app.schema.user import CurrentUserSchema
from app.static.permissions import PermissionsActions

finance_vendors_router = APIRouter()


@finance_vendors_router.get(
    "",
    response_model=FinanceVendorPaginator,
    summary="Get all vendors for a company",
)
def get_vendors(
    company_id: int,
    current_user: Annotated[
        CurrentUserSchema,
        Depends(AuthorizedUser([FinancePermissions(PermissionsActions.view)])),
    ],
    db_session: Session = Depends(get_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    is_active: Optional[bool] = None,
):
    get_authorized_company(company_id, current_user, db_session)
    items, total = FinanceVendorCRUD.get_all(db_session, company_id, skip, limit, is_active)
    return FinanceVendorPaginator(
        items=[FinanceVendorSchema.model_validate(v, from_attributes=True) for v in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@finance_vendors_router.get(
    "/{vendor_id}",
    response_model=FinanceVendorSchema,
    summary="Get a vendor by ID",
)
def get_vendor(
    company_id: int,
    vendor_id: int,
    current_user: Annotated[
        CurrentUserSchema,
        Depends(AuthorizedUser([FinancePermissions(PermissionsActions.view)])),
    ],
    db_session: Session = Depends(get_session),
):
    get_authorized_company(company_id, current_user, db_session)
    vendor = FinanceVendorCRUD.get_by_id(db_session, vendor_id)
    if not vendor or vendor.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    return FinanceVendorSchema.model_validate(vendor, from_attributes=True)


@finance_vendors_router.post(
    "",
    response_model=FinanceVendorSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new vendor",
)
def create_vendor(
    company_id: int,
    data: FinanceVendorCreate,
    current_user: Annotated[
        CurrentUserSchema,
        Depends(AuthorizedUser([FinancePermissions(PermissionsActions.edit)])),
    ],
    db_session: Session = Depends(get_session),
):
    get_authorized_company(company_id, current_user, db_session)
    vendor = FinanceVendorCRUD.create(db_session, company_id, data.model_dump())
    return FinanceVendorSchema.model_validate(vendor, from_attributes=True)


@finance_vendors_router.patch(
    "/{vendor_id}",
    response_model=FinanceVendorSchema,
    summary="Update a vendor",
)
def update_vendor(
    company_id: int,
    vendor_id: int,
    data: FinanceVendorUpdate,
    current_user: Annotated[
        CurrentUserSchema,
        Depends(AuthorizedUser([FinancePermissions(PermissionsActions.edit)])),
    ],
    db_session: Session = Depends(get_session),
):
    get_authorized_company(company_id, current_user, db_session)
    vendor = FinanceVendorCRUD.get_by_id(db_session, vendor_id)
    if not vendor or vendor.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    updated = FinanceVendorCRUD.update(db_session, vendor, data.model_dump(exclude_unset=True))
    return FinanceVendorSchema.model_validate(updated, from_attributes=True)


@finance_vendors_router.delete(
    "/{vendor_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a vendor",
)
def delete_vendor(
    company_id: int,
    vendor_id: int,
    current_user: Annotated[
        CurrentUserSchema,
        Depends(AuthorizedUser([FinancePermissions(PermissionsActions.edit)])),
    ],
    db_session: Session = Depends(get_session),
):
    get_authorized_company(company_id, current_user, db_session)
    vendor = FinanceVendorCRUD.get_by_id(db_session, vendor_id)
    if not vendor or vendor.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    FinanceVendorCRUD.delete(db_session, vendor)
