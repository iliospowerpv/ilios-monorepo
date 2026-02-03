"""Legacy users router - READ-ONLY endpoints only.

Mutation endpoints have been removed. User management is now done via Portfolio Admin
through the workspace router (/api/workspace/companies/{id}/members).
"""
import logging

from fastapi import APIRouter, HTTPException, status
from fastapi.params import Depends
from fastapi_filter import FilterDepends
from sqlalchemy.orm import Session

from app.crud.user import UserCRUD
from app.db.session import get_session
from app.filters.user_filters import UserSearchFilter
from app.helpers.authorization import AuthorizedUser, SettingsPermissions, get_current_admin_user
from app.helpers.pagination import pagination_details
from app.helpers.query_params_validator import validate_query_params
from app.schema.user import (
    GetUserSchema,
    UserOrderByFieldEnum,
    UsersListResponse,
)
from app.static import (
    HTTP_404_RESPONSE,
    PermissionsActions,
)

users_router = APIRouter()

logger = logging.getLogger(__name__)


@users_router.get(
    "/",
    response_model=UsersListResponse,
    dependencies=[Depends(get_current_admin_user)],
)
async def users_list(
    search_user_filter: UserSearchFilter = FilterDepends(UserSearchFilter),
    query_params: tuple = Depends(validate_query_params(order_by=UserOrderByFieldEnum)),
    *,
    db_session: Session = Depends(get_session),
):
    """Users listing"""
    skip, limit, order_by, order_direction = query_params
    user_crud = UserCRUD(db_session)
    total, users = user_crud.get_users(search_user_filter, skip, limit, order_by, order_direction)

    return {"items": users, **pagination_details(skip, limit, total)}


@users_router.get(
    "/{user_id}",
    response_model=GetUserSchema,
    responses={**HTTP_404_RESPONSE},
    dependencies=[Depends(AuthorizedUser(SettingsPermissions(PermissionsActions.view)))],
)
async def get_by_id(
    user_id: int,
    db_session: Session = Depends(get_session),
):
    user = UserCRUD(db_session).get_by_id(user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    return user
