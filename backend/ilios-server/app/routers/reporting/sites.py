import logging

from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends
from sqlalchemy.orm import Session

from app.crud.site import SiteCRUD
from app.db.session import get_session
from app.filters.site_filters import SearchSiteByName
from app.helpers.authorization import AuthorizedUser, get_authorized_company
from app.helpers.authorization.module_based.reporting import ReportingPermissions
from app.helpers.pagination import pagination_details
from app.helpers.query_params_validator import validate_query_params
from app.models.company import Company
from app.schema.site import ReportSitesPaginator, ReportsSiteOrderByFieldEnum
from app.schema.user import CurrentUserSchema
from app.static import PermissionsActions

logger = logging.getLogger(__name__)
reports_sites_router = APIRouter()


@reports_sites_router.get(
    "",
    response_model=ReportSitesPaginator,
    description="Get company sites available for the reports generation based on user project access",
)
async def get_company_sites_list(
    query_params: tuple = Depends(validate_query_params(order_by=ReportsSiteOrderByFieldEnum)),
    site_filter: SearchSiteByName = FilterDepends(SearchSiteByName),
    *,
    company: Company = Depends(get_authorized_company),
    current_user: CurrentUserSchema = Depends(AuthorizedUser(ReportingPermissions(PermissionsActions.view))),
    db_session: Session = Depends(get_session),
):
    site_crud = SiteCRUD(db_session)
    skip, limit, order_by, order_direction = query_params
    total, sites = site_crud.get_sites_by_company_id(
        company.id,
        site_filter,
        skip,
        limit,
        order_by,
        order_direction,
        site_ids_to_limit=current_user.get_limited_sites_ids(),
    )

    return {"items": sites, **pagination_details(skip, limit, total)}
