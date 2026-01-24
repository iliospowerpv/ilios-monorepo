"""Finance obligations router."""

from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.finance import FinanceApprovalCRUD, FinanceObligationCRUD, FinancePortfolioCRUD
from app.db.session import get_session
from app.helpers.authorization import AuthorizedUser, get_authorized_company, get_authorized_site
from app.helpers.authorization.module_based.finance import FinancePermissions
from app.schema.finance import (
    FinanceApprovalCreate,
    FinanceApprovalSchema,
    FinanceObligationCreate,
    FinanceObligationPaginator,
    FinanceObligationSchema,
    FinanceObligationSubmit,
    FinanceObligationUpdate,
)
from app.schema.user import CurrentUserSchema
from app.static.finance import FinanceObligationStatus
from app.static.permissions import PermissionsActions

finance_obligations_router = APIRouter()


def _obligation_to_schema(obligation) -> FinanceObligationSchema:
    return FinanceObligationSchema(
        id=obligation.id,
        company_id=obligation.company_id,
        site_id=obligation.site_id,
        vendor_id=obligation.vendor_id,
        budget_line_item_id=obligation.budget_line_item_id,
        obligation_type=obligation.obligation_type,
        description=obligation.description,
        amount_requested=obligation.amount_requested,
        requested_date=obligation.requested_date,
        due_date=obligation.due_date,
        status=obligation.status,
        prerequisite_snapshot=obligation.prerequisite_snapshot,
        reference_number=obligation.reference_number,
        created_at=obligation.created_at,
        updated_at=obligation.updated_at,
        created_by_id=obligation.created_by_id,
        vendor_name=obligation.vendor.name if obligation.vendor else None,
        site_name=obligation.site.name if obligation.site else None,
    )


@finance_obligations_router.get(
    "",
    response_model=FinanceObligationPaginator,
    summary="Get all obligations for a company",
)
def get_obligations(
    company_id: int,
    current_user: Annotated[
        CurrentUserSchema,
        Depends(AuthorizedUser([FinancePermissions(PermissionsActions.view)])),
    ],
    db_session: Session = Depends(get_session),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    site_id: Optional[int] = None,
    status_filter: Optional[FinanceObligationStatus] = Query(None, alias="status"),
):
    get_authorized_company(company_id, current_user, db_session)
    items, total = FinanceObligationCRUD.get_all(db_session, company_id, site_id, status_filter, skip, limit)
    return FinanceObligationPaginator(
        items=[_obligation_to_schema(o) for o in items],
        total=total,
        skip=skip,
        limit=limit,
    )


@finance_obligations_router.get(
    "/{obligation_id}",
    response_model=FinanceObligationSchema,
    summary="Get an obligation by ID",
)
def get_obligation(
    company_id: int,
    obligation_id: int,
    current_user: Annotated[
        CurrentUserSchema,
        Depends(AuthorizedUser([FinancePermissions(PermissionsActions.view)])),
    ],
    db_session: Session = Depends(get_session),
):
    get_authorized_company(company_id, current_user, db_session)
    obligation = FinanceObligationCRUD.get_by_id(db_session, obligation_id)
    if not obligation or obligation.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Obligation not found")
    return _obligation_to_schema(obligation)


@finance_obligations_router.post(
    "",
    response_model=FinanceObligationSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new obligation",
)
def create_obligation(
    company_id: int,
    data: FinanceObligationCreate,
    current_user: Annotated[
        CurrentUserSchema,
        Depends(AuthorizedUser([FinancePermissions(PermissionsActions.edit)])),
    ],
    db_session: Session = Depends(get_session),
):
    get_authorized_company(company_id, current_user, db_session)
    obligation = FinanceObligationCRUD.create(db_session, company_id, current_user.id, data.model_dump())
    obligation = FinanceObligationCRUD.get_by_id(db_session, obligation.id)
    return _obligation_to_schema(obligation)


@finance_obligations_router.patch(
    "/{obligation_id}",
    response_model=FinanceObligationSchema,
    summary="Update an obligation",
)
def update_obligation(
    company_id: int,
    obligation_id: int,
    data: FinanceObligationUpdate,
    current_user: Annotated[
        CurrentUserSchema,
        Depends(AuthorizedUser([FinancePermissions(PermissionsActions.edit)])),
    ],
    db_session: Session = Depends(get_session),
):
    get_authorized_company(company_id, current_user, db_session)
    obligation = FinanceObligationCRUD.get_by_id(db_session, obligation_id)
    if not obligation or obligation.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Obligation not found")
    if obligation.status not in [FinanceObligationStatus.draft]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only update obligations in Draft status",
        )
    updated = FinanceObligationCRUD.update(db_session, obligation, data.model_dump(exclude_unset=True))
    updated = FinanceObligationCRUD.get_by_id(db_session, updated.id)
    return _obligation_to_schema(updated)


@finance_obligations_router.post(
    "/{obligation_id}/submit",
    response_model=FinanceObligationSchema,
    summary="Submit an obligation for approval",
)
def submit_obligation(
    company_id: int,
    obligation_id: int,
    data: FinanceObligationSubmit,
    current_user: Annotated[
        CurrentUserSchema,
        Depends(AuthorizedUser([FinancePermissions(PermissionsActions.edit)])),
    ],
    db_session: Session = Depends(get_session),
):
    get_authorized_company(company_id, current_user, db_session)
    obligation = FinanceObligationCRUD.get_by_id(db_session, obligation_id)
    if not obligation or obligation.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Obligation not found")
    if obligation.status != FinanceObligationStatus.draft:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only submit obligations in Draft status",
        )
    prerequisite_snapshot = {}
    if obligation.site_id:
        site = get_authorized_site(obligation.site_id, current_user, db_session)
        missing = FinancePortfolioCRUD.get_missing_prerequisites(site)
        prerequisite_snapshot = {
            "site_id": site.id,
            "site_name": site.name,
            "missing_prerequisites": missing,
            "prerequisites_satisfied": len(missing) == 0,
        }
    updated = FinanceObligationCRUD.submit(db_session, obligation, prerequisite_snapshot)
    updated = FinanceObligationCRUD.get_by_id(db_session, updated.id)
    return _obligation_to_schema(updated)


@finance_obligations_router.post(
    "/{obligation_id}/approve",
    response_model=FinanceApprovalSchema,
    status_code=status.HTTP_201_CREATED,
    summary="Approve or reject an obligation",
)
def approve_obligation(
    company_id: int,
    obligation_id: int,
    data: FinanceApprovalCreate,
    current_user: Annotated[
        CurrentUserSchema,
        Depends(AuthorizedUser([FinancePermissions(PermissionsActions.edit)])),
    ],
    db_session: Session = Depends(get_session),
):
    get_authorized_company(company_id, current_user, db_session)
    obligation = FinanceObligationCRUD.get_by_id(db_session, obligation_id)
    if not obligation or obligation.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Obligation not found")
    if obligation.status != FinanceObligationStatus.submitted:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only approve/reject obligations in Submitted status",
        )
    if data.decision.value == "override" and not data.override_reason:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Override reason is required for override decisions",
        )
    approval = FinanceApprovalCRUD.create(db_session, obligation_id, current_user.id, data.model_dump())
    return FinanceApprovalSchema(
        id=approval.id,
        obligation_id=approval.obligation_id,
        approved_by_id=approval.approved_by_id,
        decision=approval.decision,
        notes=approval.notes,
        override_reason=approval.override_reason,
        approved_at=approval.approved_at,
        approved_by_name=approval.approved_by.email if approval.approved_by else None,
    )


@finance_obligations_router.get(
    "/{obligation_id}/approvals",
    response_model=list[FinanceApprovalSchema],
    summary="Get approval history for an obligation",
)
def get_approvals(
    company_id: int,
    obligation_id: int,
    current_user: Annotated[
        CurrentUserSchema,
        Depends(AuthorizedUser([FinancePermissions(PermissionsActions.view)])),
    ],
    db_session: Session = Depends(get_session),
):
    get_authorized_company(company_id, current_user, db_session)
    obligation = FinanceObligationCRUD.get_by_id(db_session, obligation_id)
    if not obligation or obligation.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Obligation not found")
    approvals = FinanceApprovalCRUD.get_by_obligation(db_session, obligation_id)
    return [
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
        for a in approvals
    ]


@finance_obligations_router.delete(
    "/{obligation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an obligation",
)
def delete_obligation(
    company_id: int,
    obligation_id: int,
    current_user: Annotated[
        CurrentUserSchema,
        Depends(AuthorizedUser([FinancePermissions(PermissionsActions.edit)])),
    ],
    db_session: Session = Depends(get_session),
):
    get_authorized_company(company_id, current_user, db_session)
    obligation = FinanceObligationCRUD.get_by_id(db_session, obligation_id)
    if not obligation or obligation.company_id != company_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Obligation not found")
    if obligation.status not in [FinanceObligationStatus.draft, FinanceObligationStatus.canceled]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only delete obligations in Draft or Canceled status",
        )
    FinanceObligationCRUD.delete(db_session, obligation)
