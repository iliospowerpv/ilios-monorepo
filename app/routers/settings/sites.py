import logging

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.crud.site import SiteCRUD
from app.db.session import get_session
from app.helpers.authorization.module_based.base import get_current_admin_user
from app.helpers.pagination import pagination_details
from app.helpers.query_params_validator import validate_query_params
from app.schema.site import SitesSystemUserSettingsList, SiteSystemUserSettingsOrderByFieldEnum

logger = logging.getLogger(__name__)
settings_sites_router = APIRouter()


@settings_sites_router.get(
    "/", response_model=SitesSystemUserSettingsList, dependencies=[Depends(get_current_admin_user)]
)
async def get(
    search: str = None,
    query_params: tuple = Depends(validate_query_params(order_by=SiteSystemUserSettingsOrderByFieldEnum)),
    *,
    db_session: Session = Depends(get_session),
) -> dict:
    site_crud = SiteCRUD(db_session)
    skip, limit, order_by, order_direction = query_params

    total, sites = site_crud.get_sites_for_settings(search, skip, limit, order_by, order_direction)
    return {"items": sites, **pagination_details(skip, limit, total)}
