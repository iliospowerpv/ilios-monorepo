import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app import static
from app.crud.site import SiteCRUD
from app.db.session import get_session
from app.helpers.authorization import AuthorizedUser, InvestorDashboardPermissions
from app.helpers.company_helper import extend_company_sites_with_energy_attributes
from app.helpers.pagination import pagination_details
from app.helpers.query_params_validator import validate_skip_and_limit
from app.schema.om_site import InvestorDashboardSitesPaginator
from app.schema.user import CurrentUserSchema
from app.static import PermissionsActions

logger = logging.getLogger(__name__)
investor_sites_router = APIRouter()


@investor_sites_router.get(
    "",
    response_model=InvestorDashboardSitesPaginator,
    dependencies=[Depends(validate_skip_and_limit)],
    description="Return sites details user has access to",
)
async def get_company_sites(
    skip: int = static.DEFAULT_PAGINATION_SKIP,
    limit: int = static.DEFAULT_PAGINATION_LIMIT,
    *,
    current_user: Annotated[
        CurrentUserSchema, Depends(AuthorizedUser(InvestorDashboardPermissions(PermissionsActions.view)))
    ],
    db_session: Session = Depends(get_session),
) -> dict:
    site_crud = SiteCRUD(db_session)

    total, sites = site_crud.filter(current_user.get_limited_sites_ids(), skip=skip, limit=limit)
    extend_company_sites_with_energy_attributes(sites)
    return {"items": sites, **pagination_details(skip, limit, total)}
