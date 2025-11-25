"""Companies related endpoint serves O&M (Operations and Maintenance, previously - Production monitoring) module"""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends
from sqlalchemy.orm import Session

from app import static
from app.crud.alert import AlertCRUD
from app.crud.company import CompanyCRUD
from app.crud.site import SiteCRUD
from app.db.session import get_session
from app.filters.company_filters import SearchCompanyByName
from app.filters.site_filters import SiteFilter
from app.helpers.alert_helper import get_alerts_overview
from app.helpers.alerts import populate_company_alerts_summary_section
from app.helpers.authorization import AuthorizedUser, OnMPermissions
from app.helpers.authorization.project_access import get_authorized_company
from app.helpers.company_helper import (
    extend_company_sites_with_energy_attributes,
    get_company_actual_production_section_with_telemetry,
    get_company_actual_vs_expected_production_section_with_telemetry,
    get_company_site_ids_to_limit,
)
from app.helpers.pagination import pagination_details
from app.helpers.query_params_validator import validate_query_params, validate_skip_and_limit
from app.helpers.telemetry.bigquery import TelemetryCompanyBigQuery
from app.models.company import Company
from app.schema.company import CompaniesOrderByFieldEnum
from app.schema.om_company import (
    CompanyDashboardActualProductionSection,
    CompanyDashboardActualVsExpectedSection,
    CompanyDashboardResponse,
    CompanyLosesForADaySchema,
    OMCompaniesPaginator,
)
from app.schema.om_site import OMSitesPaginator
from app.schema.user import CurrentUserSchema
from app.static import HTTP_404_RESPONSE, PermissionsActions
from app.static.alerts import AssetType

logger = logging.getLogger(__name__)
om_companies_router = APIRouter()


@om_companies_router.get(
    "/",
    response_model=OMCompaniesPaginator,
)
async def get_companies_list(
    query_params: tuple = Depends(validate_query_params(order_by=CompaniesOrderByFieldEnum)),
    *,
    current_user: Annotated[CurrentUserSchema, Depends(AuthorizedUser(OnMPermissions(PermissionsActions.view)))],
    company_filter: SearchCompanyByName = FilterDepends(SearchCompanyByName),
    db_session: Session = Depends(get_session),
):
    company_crud = CompanyCRUD(db_session)
    alert_crud = AlertCRUD(db_session)
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
        search_filter=company_filter,
        site_ids_to_limit=site_ids_to_limit,
    )
    # for response companies, get their alerts overview
    # return alerts only for sites user has access to
    companies_alerts = alert_crud.get_company_alerts_overview({company.id for company in companies}, site_ids_to_limit)
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
        # extend companies with the alerts info
        company_alerts_overview = get_alerts_overview(company.id, companies_alerts, AssetType.company)

        # update response object
        company_dict = company._asdict()
        company_dict.update(
            {
                "total_actual_kw": company_actual_kw,
                "total_expected_kw": company_expected_kw,
                "alerts_overview": company_alerts_overview,
            }
        )
        response.append(company_dict)

    return {"items": response, **pagination_details(skip, limit, total)}


@om_companies_router.get(
    "/{company_id}/sites",
    response_model=OMSitesPaginator,
    dependencies=[Depends(validate_skip_and_limit)],
)
async def get_company_sites(
    company: Company = Depends(get_authorized_company),
    skip: int = static.DEFAULT_PAGINATION_SKIP,
    limit: int = static.DEFAULT_PAGINATION_LIMIT,
    *,
    current_user: Annotated[CurrentUserSchema, Depends(AuthorizedUser(OnMPermissions(PermissionsActions.view)))],
    db_session: Session = Depends(get_session),
) -> dict:
    """Return sites user has access via `user.project access`, filtered by the specific company ID"""
    site_crud = SiteCRUD(db_session)

    total, sites = site_crud.filter(
        current_user.get_limited_sites_ids(), site_filter=SiteFilter(company_id=company.id), skip=skip, limit=limit
    )
    sites_alerts = AlertCRUD(db_session).get_site_alerts_overview({site.id for site in sites})
    for site in sites:
        site.alerts_overview = get_alerts_overview(site.id, sites_alerts, AssetType.site)
    extend_company_sites_with_energy_attributes(sites)
    return {"items": sites, **pagination_details(skip, limit, total)}


@om_companies_router.get(
    "/{company_id}",
    response_model=CompanyDashboardResponse,
    responses={**HTTP_404_RESPONSE},
    description="Combined data to be served on the company dashboard",
)
async def get_by_id(
    current_user: Annotated[CurrentUserSchema, Depends(AuthorizedUser(OnMPermissions(PermissionsActions.view)))],
    company: Company = Depends(get_authorized_company),
    db_session: Session = Depends(get_session),
):
    # return only details about sites user has access to
    site_ids_to_limit = current_user.get_limited_sites_ids()
    # retrieve details for alerts and sites related section
    alert_crud = AlertCRUD(db_session)

    return {
        # serve ID and NAME on the root level
        "id": company.id,
        "name": company.name,
        # rest of data wrapped into sections
        "alerts_section": alert_crud.get_company_most_critical_alerts(company.id, site_ids_to_limit),
        "alerts_summary_section": populate_company_alerts_summary_section(
            alert_crud.get_company_alerts_stats_with_tasks(company.id, site_ids_to_limit)
        ),
    }


@om_companies_router.get(
    "/{company_id}/actual-production-chart",
    response_model=CompanyDashboardActualProductionSection,
    responses={**HTTP_404_RESPONSE},
    description="Returns company actual dashboard chart (limited with sites user has access to)",
)
async def get_actual_production_chart(
    current_user: Annotated[CurrentUserSchema, Depends(AuthorizedUser(OnMPermissions(PermissionsActions.view)))],
    company: Company = Depends(get_authorized_company),
    db_session: Session = Depends(get_session),
):
    site_ids_to_limit = current_user.get_limited_sites_ids()
    return get_company_actual_production_section_with_telemetry(company, site_ids_to_limit, db_session)


@om_companies_router.get(
    "/{company_id}/actual-vs-expected-production-chart",
    response_model=CompanyDashboardActualVsExpectedSection,
    responses={**HTTP_404_RESPONSE},
    description="Returns company actual vs expected production chart (limited with sites user has access to)",
)
async def get_actual_vs_expected_production_chart(
    current_user: Annotated[CurrentUserSchema, Depends(AuthorizedUser(OnMPermissions(PermissionsActions.view)))],
    company: Company = Depends(get_authorized_company),
):
    site_ids_to_limit = current_user.get_limited_sites_ids()
    return {"items": get_company_actual_vs_expected_production_section_with_telemetry(company, site_ids_to_limit)}


@om_companies_router.get(
    "/{company_id}/loses-for-a-day-chart",
    response_model=CompanyLosesForADaySchema,
    responses={**HTTP_404_RESPONSE},
    description="Returns loses for a day accumulative details (limited with sites user has access to)",
)
async def get_loses_for_a_day_chart(
    current_user: Annotated[CurrentUserSchema, Depends(AuthorizedUser(OnMPermissions(PermissionsActions.view)))],
    company: Company = Depends(get_authorized_company),
):
    return TelemetryCompanyBigQuery().get_company_loses(get_company_site_ids_to_limit(company, current_user))
