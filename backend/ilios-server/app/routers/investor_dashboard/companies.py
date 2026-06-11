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
from app.helpers.telemetry.v2_company_data import (
    aggregate_company_expected,
    compute_sites_expected_today,
    get_active_baselines,
    get_sites_latest_power,
)
from app.models.company import Company
from app.models.site import Site
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
    if current_user.has_platform_bypass:
        site_ids_to_limit = SiteCRUD(db_session).get_all_sites_ids()
    total, companies = company_crud.get_with_sites_info(
        current_user.get_limited_companies_ids(),
        skip,
        limit,
        order_by,
        order_direction,
        site_ids_to_limit=site_ids_to_limit,
    )
    # get sites actual production from V2 PostgreSQL rollups (no BigQuery). Sites
    # without V2 rollups simply contribute 0 to actual.
    power_by_site = get_sites_latest_power(db_session, site_ids_to_limit)

    # Expected is honest-or-null per company. Compute it once for just the sites
    # on this page (intersected with access): load Site ORM objects (timezone
    # needed for per-site local-day attribution), batch the active baselines, and
    # compute today's expected per site via the pure V2 core. A company's expected
    # is a real number only when every telemetry-backed site is fully computable;
    # otherwise it is None with metadata explaining the gap (never fabricated).
    site_ids_to_limit_set = set(site_ids_to_limit)
    page_site_ids = set()
    for company in companies:
        page_site_ids |= set(company.sites_ids) & site_ids_to_limit_set
    sites_by_id = (
        {site.id: site for site in db_session.query(Site).filter(Site.id.in_(page_site_ids)).all()}
        if page_site_ids
        else {}
    )
    telemetry_site_ids = set(power_by_site)
    baselines_by_site = get_active_baselines(db_session, page_site_ids)
    computable_sites = [
        sites_by_id[sid]
        for sid in (telemetry_site_ids & set(baselines_by_site))
        if sid in sites_by_id
    ]
    expected_by_site = compute_sites_expected_today(db_session, computable_sites, baselines_by_site)

    # extend companies with details from other sources
    response = []
    for company in companies:
        # get sites actual production for this company (V2 actuals only)
        company_actual_kw = sum(power_by_site.get(site_id, 0.0) for site_id in company.sites_ids)
        company_site_ids = set(company.sites_ids) & site_ids_to_limit_set
        company_sites = [sites_by_id[sid] for sid in company_site_ids if sid in sites_by_id]
        expected = aggregate_company_expected(
            company_sites, telemetry_site_ids, baselines_by_site, expected_by_site
        )

        # update response object
        company_dict = company._asdict()
        company_dict.update(
            {
                "total_actual_kw": company_actual_kw,
                "total_expected_kw": expected["total_expected_kw"],
                "expected_baseline_available": expected["expected_baseline_available"],
                "expected_state": expected["expected_state"],
                "sites_with_telemetry": expected["sites_with_telemetry"],
                "sites_with_active_baseline": expected["sites_with_active_baseline"],
                "sites_missing_baseline": expected["sites_missing_baseline"],
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
