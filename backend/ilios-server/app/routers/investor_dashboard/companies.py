import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.crud.company import CompanyCRUD
from app.crud.site import SiteCRUD
from app.db.session import get_session
from app.helpers.authorization import AuthorizedUser, InvestorDashboardPermissions, get_authorized_company
from app.helpers.company_helper import get_company_actual_production_section_with_telemetry
from app.helpers.pagination import pagination_details
from app.helpers.query_params_validator import validate_query_params
from app.helpers.telemetry.bigquery import TelemetryCompanyBigQuery
from app.models.company import Company
from app.schema.company import CompaniesOrderByFieldEnum
from app.schema.om_company import CompanyDashboardActualProductionSection, InvestorDashboardCompaniesPaginator
from app.schema.user import CurrentUserSchema
from app.static import HTTP_404_RESPONSE, PermissionsActions

logger = logging.getLogger(__name__)
investor_companies_router = APIRouter()


@investor_companies_router.get(
    "",
    response_model=InvestorDashboardCompaniesPaginator,
    description="Returns companies with aggregated details of sites user has access to",
)
async def get_companies_list(
    query_params: tuple = Depends(validate_query_params(order_by=CompaniesOrderByFieldEnum)),
    *,
    current_user: Annotated[
        CurrentUserSchema, Depends(AuthorizedUser(InvestorDashboardPermissions(PermissionsActions.view)))
    ],
    db_session: Session = Depends(get_session),
):
    company_crud = CompanyCRUD(db_session)
    skip, limit, order_by, order_direction = query_params
    # return only details about sites user has access to
    site_ids_to_limit = current_user.get_limited_sites_ids()
    # for the system user, consider sites_ids_to_limit as IDs of all sites in the platform
    if current_user.is_system_user:
        site_ids_to_limit = SiteCRUD(db_session).get_all_sites_ids()
    total, companies = company_crud.get_with_sites_info(
        current_user.get_limited_companies_ids(),
        skip,
        limit,
        order_by,
        order_direction,
        site_ids_to_limit=site_ids_to_limit,
    )
    # get sites telemetry data
    sites_actual_production = TelemetryCompanyBigQuery().get_companies_list_actual_production(site_ids_to_limit)

    # extend companies with details from other sources
    response = []
    for company in companies:
        # get sites actual production for this company
        company_actual_kw = sum(
            [site["actual_kw"] for site in sites_actual_production if site["site_id"] in company.sites_ids]
        )
        company_expected_kw = sum(
            [site["expected_kw"] for site in sites_actual_production if site["site_id"] in company.sites_ids]
        )

        # update response object
        company_dict = company._asdict()
        company_dict.update(
            {
                "total_actual_kw": company_actual_kw,
                "total_expected_kw": company_expected_kw,
            }
        )
        response.append(company_dict)

    return {"items": response, **pagination_details(skip, limit, total)}


@investor_companies_router.get(
    "/{company_id}/actual-production",
    response_model=CompanyDashboardActualProductionSection,
    responses={**HTTP_404_RESPONSE},
    description="Company actual production aggregated by the sites user has access to",
)
async def get_company_actual_production(
    current_user: Annotated[
        CurrentUserSchema, Depends(AuthorizedUser(InvestorDashboardPermissions(PermissionsActions.view)))
    ],
    company: Company = Depends(get_authorized_company),
    db_session: Session = Depends(get_session),
):
    site_ids_to_limit = current_user.get_limited_sites_ids()
    return get_company_actual_production_section_with_telemetry(company, site_ids_to_limit, db_session)
