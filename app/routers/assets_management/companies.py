"""Companies related endpoint serves Assets Management module"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends
from sqlalchemy.orm import Session

from app.crud.company import CompanyCRUD
from app.db.session import get_session
from app.filters.company_filters import SearchCompanyByName
from app.helpers.authorization import AssetPermissions, AuthorizedUser, DiligencePermissions, SettingsPermissions
from app.helpers.authorization.project_access import get_authorized_company
from app.helpers.pagination import pagination_details
from app.helpers.query_params_validator import validate_query_params
from app.models.company import Company
from app.schema.company import (
    CompaniesOrderByFieldEnum,
    CompaniesPaginator,
    CompanyListSiteSchema,
    CompanySchemaSitesInfo,
)
from app.schema.user import CurrentUserSchema
from app.static import HTTP_404_RESPONSE, PermissionsActions

logger = logging.getLogger(__name__)
companies_router = APIRouter()


@companies_router.get(
    "/",
    response_model=CompaniesPaginator,
)
async def get(
    query_params: tuple = Depends(validate_query_params(order_by=CompaniesOrderByFieldEnum)),
    company_filter: SearchCompanyByName = FilterDepends(SearchCompanyByName),
    *,
    current_user: Annotated[
        CurrentUserSchema,
        Depends(
            AuthorizedUser([AssetPermissions(PermissionsActions.view), DiligencePermissions(PermissionsActions.view)])
        ),
    ],
    db_session: Session = Depends(get_session),
):
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


# TODO rename endpoint and move it to the settings directory, it's not part of the assets management
@companies_router.get(
    "/sites",
    response_model=CompanyListSiteSchema,
    description="Returns companies with nested sites (without pagination). Utilized on the user creation screen",
    dependencies=[Depends(AuthorizedUser(SettingsPermissions(PermissionsActions.edit)))],
)
async def get_company_sites(db_session: Session = Depends(get_session)):
    company_crud = CompanyCRUD(db_session)
    companies = company_crud.get(skip_pagination=True)
    return {"data": companies}


@companies_router.get(
    "/{company_id}",
    response_model=CompanySchemaSitesInfo,
    responses={**HTTP_404_RESPONSE},
)
async def get_by_id(
    current_user: Annotated[
        CurrentUserSchema,
        Depends(AuthorizedUser([AssetPermissions(PermissionsActions.view)])),
    ],
    company: Company = Depends(get_authorized_company),
    db_session: Session = Depends(get_session),
):
    logger.debug(f"GET /companies/{company.id}")
    company = CompanyCRUD(db_session).get_with_total_sites(company.id, current_user.get_limited_sites_ids())
    return company
