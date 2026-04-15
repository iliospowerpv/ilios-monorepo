from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from fastapi_filter import FilterDepends
from sqlalchemy.orm import Session
from starlette import status

from app.crud.user import UserCRUD
from app.db.session import get_session
from app.filters.user_filters import UserSearchFilter
from app.helpers.authorization.module_based.base import get_current_admin_user
from app.helpers.pagination import pagination_details
from app.helpers.query_params_validator import validate_query_params
from app.schema.user import (
    CreateUserSchema,
    CurrentUserSchema,
    GetUserSchema,
    EditUserSchema,
    UserOrderByFieldEnum,
    UsersListResponse,
)
from app.static import HTTP_403_RESPONSE, HTTP_404_RESPONSE

users_router = APIRouter()


@users_router.get(
    "/",
    response_model=UsersListResponse,
    responses={**HTTP_403_RESPONSE},
)
async def list_users(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_admin_user)],
    query_params: tuple = Depends(validate_query_params(order_by=UserOrderByFieldEnum)),
    search_filter: UserSearchFilter = FilterDepends(UserSearchFilter),
    db_session: Session = Depends(get_session),
):
    skip, limit, order_by, order_direction = query_params
    user_crud = UserCRUD(db_session)
    total, items = user_crud.get_users(
        search_filter=search_filter,
        skip=skip,
        limit=limit,
        order_by=order_by,
        order_direction=order_direction,
    )
    return {"items": items, **pagination_details(skip, limit, total)}


@users_router.get(
    "/{user_id}",
    response_model=GetUserSchema,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def get_user(
    user_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_admin_user)],
    db_session: Session = Depends(get_session),
):
    user_crud = UserCRUD(db_session)
    user = user_crud.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


@users_router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    responses={**HTTP_403_RESPONSE},
)
async def create_user(
    payload: CreateUserSchema,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_admin_user)],
    db_session: Session = Depends(get_session),
):
    user_crud = UserCRUD(db_session)
    existing = user_crud.get_by_email(payload.email)
    if existing:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="A user with this email already exists")
    new_user = user_crud.create_item(payload.model_dump())
    return {"message": "User created successfully", "code": 201, "id": new_user.id}


@users_router.put(
    "/{user_id}",
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def edit_user(
    user_id: int,
    payload: EditUserSchema,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_admin_user)],
    db_session: Session = Depends(get_session),
):
    user_crud = UserCRUD(db_session)
    user = user_crud.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    update_data = payload.model_dump(exclude_unset=True)
    user_crud.update_by_id(user_id, update_data)
    return {"message": "User updated successfully", "code": 200}


@users_router.post(
    "/{user_id}/resend-invite",
    responses={**HTTP_404_RESPONSE},
)
async def resend_invite(
    user_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_admin_user)],
    db_session: Session = Depends(get_session),
):
    user_crud = UserCRUD(db_session)
    user = user_crud.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return {"message": "Invitation resent successfully", "code": 200}
