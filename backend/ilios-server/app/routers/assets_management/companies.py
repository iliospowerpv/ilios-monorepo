"""Companies related endpoint serves Assets Management module.

Authorization Pattern (Phase C.1):
- Entity access: get_authorized_company (canonical resolver, fail-closed)
- Module permission: require_module_permission (assets_management:view/edit)
- Order: Entity check first, then module permission check
"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends
from sqlalchemy.orm import Session

from app.crud.company import CompanyCRUD
from app.db.session import get_session
from app.filters.company_filters import SearchCompanyByName
from app.helpers.authentication import get_current_user
from app.helpers.authorization.project_access import get_authorized_company
from app.helpers.pagination import pagination_details
from app.helpers.permission_guards import require_module_permission, require_module_permission_any_context
from app.helpers.query_params_validator import validate_query_params
from app.models.company import Company
from app.schema.company import (
    CompaniesOrderByFieldEnum,
    CompaniesPaginator,
    CompanyListSiteSchema,
    CompanySchemaSitesInfo,
)
from app.schema.user import CurrentUserSchema
from app.static import HTTP_403_RESPONSE, HTTP_404_RESPONSE
from app.static.permissions import PermissionsModules

logger = logging.getLogger(__name__)
companies_router = APIRouter()


@companies_router.get(
    "/",
    response_model=CompaniesPaginator,
    responses={**HTTP_403_RESPONSE},
)
async def get(
    query_params: tuple = Depends(validate_query_params(order_by=CompaniesOrderByFieldEnum)),
    company_filter: SearchCompanyByName = FilterDepends(SearchCompanyByName),
    *,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    if not current_user.is_system_user:
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
    )

    return {"items": companies, **pagination_details(skip, limit, total)}


@companies_router.get(
    "/sites",
    response_model=CompanyListSiteSchema,
    description="Returns companies with nested sites (without pagination). Utilized on the user creation screen. "
    "Note: This is a Settings-related endpoint - uses user's role permissions directly (not company-scoped). "
    "Future work: Move to settings router or use role-based permission check.",
    responses={**HTTP_403_RESPONSE},
)
async def get_company_sites(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    if not current_user.is_system_user:
        settings_perms = current_user.role.permissions.get(PermissionsModules.settings.value, {}) if current_user.role else {}
        if not settings_perms.get("edit"):
            from fastapi import HTTPException, status
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: requires settings:edit permission"
            )
    company_crud = CompanyCRUD(db_session)
    companies = company_crud.get(skip_pagination=True)
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
