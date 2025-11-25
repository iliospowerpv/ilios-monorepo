import logging

from fastapi import APIRouter, HTTPException, status
from fastapi.params import Depends
from sqlalchemy.orm import Session

import app.static as static
from app.crud.company_role_mapping import CompanyTypeRoleMappingCRUD
from app.crud.role import RoleCRUD
from app.db.session import get_session
from app.helpers.authentication import api_key_check
from app.helpers.authorization import AuthorizedUser, SettingsPermissions, get_current_admin_user
from app.helpers.pagination import pagination_details
from app.helpers.query_params_validator import validate_skip_and_limit
from app.schema.role import (
    CompanyTypeRolesMappingResponseSchema,
    RoleCreationSuccess,
    RolePermissionsUpdateSuccess,
    RolesPaginator,
    RoleUpdateSuccess,
    UpsertRoleSchema,
)
from app.static import HTTP_403_RESPONSE, HTTP_404_RESPONSE, PermissionsActions, RoleMessages

logger = logging.getLogger(__name__)
roles_router = APIRouter()


@roles_router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=RoleCreationSuccess,
    dependencies=[Depends(get_current_admin_user)],
)
async def create_role(
    payload: UpsertRoleSchema,
    db_session: Session = Depends(get_session),
):
    role = RoleCRUD(db_session).create_item(payload.model_dump())
    logger.info(f"Created role with id {role.id}")
    return {"code": status.HTTP_201_CREATED, "message": RoleMessages.role_create_success}


@roles_router.get(
    "/",
    response_model=RolesPaginator,
    description="Retrieve full list of roles",
    dependencies=[Depends(validate_skip_and_limit), Depends(get_current_admin_user)],
)
async def list_roles(
    skip: int = static.DEFAULT_PAGINATION_SKIP,
    limit: int = static.DEFAULT_PAGINATION_LIMIT,
    *,
    db_session: Session = Depends(get_session),
):
    total, roles_records = RoleCRUD(db_session).get_roles(skip, limit)
    return {"items": roles_records, **pagination_details(skip, limit, total)}


@roles_router.put(
    "/{role_id}",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=RoleUpdateSuccess,
    dependencies=[Depends(get_current_admin_user)],
)
async def update(
    role_id: int,
    role: UpsertRoleSchema,
    db_session: Session = Depends(get_session),
):
    role_crud = RoleCRUD(db_session)
    if not role_crud.get_by_id(role_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    role_crud.update_by_id(role_id, role.model_dump())
    return {"code": status.HTTP_202_ACCEPTED, "message": RoleMessages.role_update_success}


@roles_router.put(
    "/{role_id}/permissions",
    response_model=RolePermissionsUpdateSuccess,
    status_code=status.HTTP_202_ACCEPTED,
    responses={**HTTP_404_RESPONSE},
    dependencies=[Depends(get_current_admin_user)],
)
def update_permissions(
    role_id: int,
    permissions: dict[str, dict[str, bool]],
    db_session: Session = Depends(get_session),
):
    updated_count = RoleCRUD(db_session).update_by_id(role_id, {"permissions": permissions})
    if not updated_count:
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    return {"code": status.HTTP_202_ACCEPTED, "message": "Role's permissions have been updated"}


@roles_router.get(
    "/with-company-type",
    response_model=CompanyTypeRolesMappingResponseSchema,
    dependencies=[Depends(AuthorizedUser(SettingsPermissions(PermissionsActions.view)))],
)
async def retrieve_roles_with_company_type(
    db_session: Session = Depends(get_session),
):
    return {"data": CompanyTypeRoleMappingCRUD(db_session).get(skip_pagination=True)}


@roles_router.delete(
    "/{role_id}/internal",
    dependencies=[Depends(api_key_check)],
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def delete(role_id: int, db_session: Session = Depends(get_session)):
    deleted_count = RoleCRUD(db_session).delete_by_id(role_id)
    if deleted_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
