"""Companies related endpoint serves Assets Management module.

Authorization Pattern (Phase C.1):
- Entity access: get_authorized_company (canonical resolver, fail-closed)
- Module permission: require_module_permission (assets_management:view/edit)
- Order: Entity check first, then module permission check
"""

import logging
from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi_filter import FilterDepends
from sqlalchemy.orm import Session
from starlette import status

from app.crud.audit_log import AuditLogCRUD
from app.crud.company import CompanyCRUD
from app.crud.user_company_access import UserCompanyAccessCRUD
from app.db.session import get_session
from app.filters.company_filters import SearchCompanyByName
from app.helpers.authentication import get_current_user
from app.helpers.authorization.module_based.base import get_current_admin_user
from app.helpers.authorization.project_access import get_authorized_company
from app.helpers.pagination import pagination_details
from app.helpers.permission_guards import require_module_permission, require_module_permission_any_context
from app.helpers.query_params_validator import validate_query_params
from app.models.company import Company
from app.models.site import Site
from app.models.user import CompanyRole, MembershipStatus
from app.schema.company import (
    CompaniesOrderByFieldEnum,
    CompaniesPaginator,
    CompanyCreationSuccess,
    CompanyListSiteSchema,
    CompanySchemaSitesInfo,
    CreateCompanySchema,
)
from app.schema.user import CurrentUserSchema
from app.static import HTTP_403_RESPONSE, HTTP_404_RESPONSE
from app.static.permissions import PermissionsModules

logger = logging.getLogger(__name__)
companies_router = APIRouter()


@companies_router.post(
    "/",
    response_model=CompanyCreationSuccess,
    status_code=status.HTTP_201_CREATED,
    responses={**HTTP_403_RESPONSE},
)
async def create_company(
    payload: CreateCompanySchema,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    if not current_user.has_platform_bypass:
        raise HTTPException(status_code=403, detail="Only system users can create companies")

    company_crud = CompanyCRUD(db_session)
    new_company = company_crud.create_item(payload.model_dump())
    db_session.flush()

    access_crud = UserCompanyAccessCRUD(db_session)
    access_crud.add_membership(
        user_id=current_user.id,
        company_id=new_company.id,
        role=CompanyRole.company_admin,
        status=MembershipStatus.active,
        created_by_user_id=current_user.id,
    )

    db_session.commit()
    db_session.refresh(new_company)

    return CompanyCreationSuccess(
        id=new_company.id,
        message="Company has been successfully created",
        code=201,
    )


@companies_router.get(
    "/",
    response_model=CompaniesPaginator,
    responses={**HTTP_403_RESPONSE},
)
async def get(
    query_params: tuple = Depends(validate_query_params(order_by=CompaniesOrderByFieldEnum)),
    company_filter: SearchCompanyByName = FilterDepends(SearchCompanyByName),
    *,
    is_archived: bool = Query(False, description="Show only archived companies"),
    include_all: bool = Query(False, description="Show both active and archived companies"),
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    if not current_user.has_platform_bypass:
        if is_archived or include_all:
            raise HTTPException(status_code=403, detail="Only system users can view archived companies")
        require_module_permission_any_context(
            user_id=current_user.id,
            company_ids=current_user.get_limited_companies_ids(),
            site_ids=current_user.get_limited_sites_ids(),
            db_session=db_session,
            module_key=PermissionsModules.assets_management.value,
            action="view",
        )
    company_crud = CompanyCRUD(db_session)
    skip, limit, order_by, order_direction = query_params
    total, companies = company_crud.get_with_sites_info(
        current_user.get_limited_companies_ids(),
        skip,
        limit,
        order_by,
        order_direction,
        search_filter=company_filter,
        site_ids_to_limit=current_user.get_limited_sites_ids(),
        include_archived=include_all,
        archived_only=is_archived,
    )

    return {"items": companies, **pagination_details(skip, limit, total)}


@companies_router.get(
    "/sites",
    response_model=CompanyListSiteSchema,
    description="Returns companies with nested sites (without pagination). Utilized on the user creation screen. "
    "Authorization: Requires settings:edit or workspace:edit permission on at least one accessible company/project. "
    "Results are filtered to only include companies/sites the user can access.",
    responses={**HTTP_403_RESPONSE},
)
async def get_company_sites(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    if not current_user.has_platform_bypass:
        require_module_permission_any_context(
            user_id=current_user.id,
            company_ids=current_user.get_limited_companies_ids(),
            site_ids=current_user.get_limited_sites_ids(),
            db_session=db_session,
            module_key=PermissionsModules.settings.value,
            action="edit",
        )
    company_crud = CompanyCRUD(db_session)
    accessible_company_ids = current_user.get_limited_companies_ids()
    accessible_site_ids = current_user.get_limited_sites_ids()
    companies = company_crud.get_filtered_with_sites(
        company_ids=accessible_company_ids if accessible_company_ids else None,
        site_ids=accessible_site_ids if accessible_site_ids else None,
        skip_pagination=True,
    )
    return {"data": companies}


@companies_router.get(
    "/{company_id}",
    response_model=CompanySchemaSitesInfo,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def get_by_id(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    company: Company = Depends(get_authorized_company),
    db_session: Session = Depends(get_session),
):
    require_module_permission(
        user_id=current_user.id,
        company_id=company.id,
        db_session=db_session,
        module_key=PermissionsModules.assets_management.value,
        action="view",
    )
    logger.debug(f"GET /companies/{company.id}")
    company = CompanyCRUD(db_session).get_with_total_sites(company.id, current_user.get_limited_sites_ids())
    return company


@companies_router.patch(
    "/{company_id}/archive",
    status_code=status.HTTP_200_OK,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def archive_company(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_admin_user)],
    company: Company = Depends(get_authorized_company),
    db_session: Session = Depends(get_session),
):
    if company.is_archived:
        return {"message": "Company is already archived", "id": company.id}

    now = datetime.utcnow()
    company.is_archived = True
    company.archived_at = now
    company.archived_by = current_user.id

    child_sites = db_session.query(Site).filter(
        Site.company_id == company.id,
        Site.is_archived == False,
    ).all()
    for site in child_sites:
        site.is_archived = True
        site.archived_at = now
        site.archived_by = current_user.id
        site.cascade_archived_by_company = True

    audit_crud = AuditLogCRUD(db_session)
    audit_crud.create_item({
        "source": "companies",
        "action": f"Archived company '{company.name}' (ID: {company.id}) and {len(child_sites)} child project(s)",
        "is_success": True,
        "details": f"Company archived by admin. {len(child_sites)} child projects cascade-archived.",
        "user_id": current_user.id,
    })

    db_session.commit()
    return {"message": f"Company '{company.name}' and {len(child_sites)} child project(s) archived", "id": company.id}


@companies_router.patch(
    "/{company_id}/restore",
    status_code=status.HTTP_200_OK,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def restore_company(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_admin_user)],
    company: Company = Depends(get_authorized_company),
    db_session: Session = Depends(get_session),
):
    if not company.is_archived:
        return {"message": "Company is already active", "id": company.id}

    cascade_sites = db_session.query(Site).filter(
        Site.company_id == company.id,
        Site.is_archived == True,
        Site.cascade_archived_by_company == True,
    ).all()
    for site in cascade_sites:
        site.is_archived = False
        site.archived_at = None
        site.archived_by = None
        site.cascade_archived_by_company = False

    company.is_archived = False
    company.archived_at = None
    company.archived_by = None

    audit_crud = AuditLogCRUD(db_session)
    audit_crud.create_item({
        "source": "companies",
        "action": f"Restored company '{company.name}' (ID: {company.id}) and {len(cascade_sites)} child project(s)",
        "is_success": True,
        "details": f"Company restored by admin. {len(cascade_sites)} cascade-archived projects restored.",
        "user_id": current_user.id,
    })

    db_session.commit()
    return {"message": f"Company '{company.name}' and {len(cascade_sites)} child project(s) restored", "id": company.id}
