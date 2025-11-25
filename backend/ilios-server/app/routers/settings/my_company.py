import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_filter import FilterDepends
from requests import Session

from app.crud.company import CompanyCRUD
from app.crud.site import SiteCRUD
from app.crud.user import UserCRUD
from app.db.session import get_session
from app.filters.site_filters import SearchSiteByName
from app.filters.user_filters import UserSearchFilter
from app.helpers.authorization import AuthorizedUser, SettingsPermissions
from app.helpers.pagination import pagination_details
from app.helpers.query_params_validator import validate_query_params
from app.helpers.user_helper import UserHelper
from app.schema.company import CompanySchemaSitesInfo
from app.schema.site import ExtendedSiteSchemaWithConnection, SiteSettingsOrderByFieldEnum, SitesSettingsList
from app.schema.user import CurrentUserSchema, UserOrderByFieldEnum, UsersListResponse
from app.static import HTTP_404_RESPONSE, PermissionsActions

logger = logging.getLogger(__name__)
my_company_router = APIRouter()


@my_company_router.get(
    "/",
    response_model=CompanySchemaSitesInfo,
    responses={**HTTP_404_RESPONSE},
)
async def get_my_company(
    current_user: Annotated[CurrentUserSchema, Depends(AuthorizedUser(SettingsPermissions(PermissionsActions.view)))],
    db_session: Session = Depends(get_session),
):
    UserHelper.validate_user_parent_company(current_user)
    company = CompanyCRUD(db_session).get_with_total_sites(current_user.parent_company_id)
    return company


@my_company_router.get(
    "/sites",
    response_model=SitesSettingsList,
)
async def get_sites_for_settings(
    query_params: tuple = Depends(validate_query_params(order_by=SiteSettingsOrderByFieldEnum)),
    *,
    current_user: Annotated[CurrentUserSchema, Depends(AuthorizedUser(SettingsPermissions(PermissionsActions.view)))],
    site_filter: SearchSiteByName = FilterDepends(SearchSiteByName),
    db_session: Session = Depends(get_session),
) -> dict:
    UserHelper.validate_user_parent_company(current_user)
    site_crud = SiteCRUD(db_session)
    skip, limit, order_by, order_direction = query_params
    total, sites = site_crud.get_sites_by_company_id(
        current_user.parent_company_id, site_filter, skip, limit, order_by, order_direction
    )
    return {"items": sites, **pagination_details(skip, limit, total)}


@my_company_router.get(
    "/sites/{site_id}",
    response_model=ExtendedSiteSchemaWithConnection,
    responses={**HTTP_404_RESPONSE},
    description="Site info to populate site editing form",
)
async def get_company_site_by_id(
    site_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(AuthorizedUser(SettingsPermissions(PermissionsActions.view)))],
    db_session: Session = Depends(get_session),
):
    UserHelper.validate_user_parent_company(current_user)
    if current_user.parent_company_id and site_id not in [site.id for site in current_user.parent_company.sites]:
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    site = SiteCRUD(db_session).get_by_id(site_id)
    return site


@my_company_router.get(
    "/users",
    response_model=UsersListResponse,
)
async def my_company_users_list(
    search_user_filter: UserSearchFilter = FilterDepends(UserSearchFilter),
    query_params: tuple = Depends(validate_query_params(order_by=UserOrderByFieldEnum)),
    *,
    current_user: Annotated[CurrentUserSchema, Depends(AuthorizedUser(SettingsPermissions(PermissionsActions.view)))],
    db_session: Session = Depends(get_session),
):
    UserHelper.validate_user_parent_company(current_user)
    skip, limit, order_by, order_direction = query_params
    user_crud = UserCRUD(db_session)
    total, users = user_crud.get_users(
        search_user_filter, skip, limit, order_by, order_direction, current_user.parent_company_id
    )
    return {"items": users, **pagination_details(skip, limit, total)}
