import logging

from fastapi import APIRouter, Depends
from fastapi_filter import FilterDepends
from sqlalchemy.orm import Session

from app.crud.company import CompanyCRUD
from app.db.session import get_session
from app.filters.company_filters import SearchCompanyByName
from app.helpers.authorization import AuthorizedUser
from app.helpers.authorization.module_based.reporting import ReportingPermissions
from app.helpers.pagination import pagination_details
from app.helpers.query_params_validator import validate_query_params
from app.schema.company import ReportCompaniesOrderByFieldEnum, ReportsCompaniesPaginator
from app.schema.user import CurrentUserSchema
from app.static import PermissionsActions

logger = logging.getLogger(__name__)
reports_companies_router = APIRouter()


@reports_companies_router.get(
    "",
    response_model=ReportsCompaniesPaginator,
    description="Get all companies available for the reports generation based on user project access",
)
async def get_companies_list(
    query_params: tuple = Depends(validate_query_params(order_by=ReportCompaniesOrderByFieldEnum)),
    company_filter: SearchCompanyByName = FilterDepends(SearchCompanyByName),
    *,
    current_user: CurrentUserSchema = Depends(AuthorizedUser(ReportingPermissions(PermissionsActions.view))),
    db_session: Session = Depends(get_session),
):
    company_crud = CompanyCRUD(db_session)
    skip, limit, order_by, order_direction = query_params
    total, companies = company_crud.get_companies_general_info(
        current_user.get_limited_companies_ids(),
        skip,
        limit,
        order_by,
        order_direction,
        search_filter=company_filter,
    )

    return {"items": companies, **pagination_details(skip, limit, total)}
