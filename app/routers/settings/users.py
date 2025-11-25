import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, status
from fastapi.params import Depends
from fastapi_filter import FilterDepends
from sqlalchemy.orm import Session

from app.crud.errors import UniqueConstraintViolationError
from app.crud.site import SiteCRUD
from app.crud.user import UserCRUD
from app.crud.user_project import UserProjectCRUD
from app.db.session import get_session
from app.filters.user_filters import UserSearchFilter
from app.helpers.authentication import api_key_check
from app.helpers.authorization import AuthorizedUser, SettingsPermissions, get_current_admin_user
from app.helpers.email import EmailUtility
from app.helpers.invitations_handler import UserInvitationsHandler
from app.helpers.pagination import pagination_details
from app.helpers.query_params_validator import validate_query_params
from app.helpers.user_helper import UserHelper
from app.schema.user import (
    BaseUserSchema,
    CreateUserSchema,
    CurrentUserSchema,
    EditUserSchema,
    GetUserSchema,
    UserCreationSuccess,
    UserOrderByFieldEnum,
    UserResendInvitationSuccess,
    UsersListResponse,
    UserUpdateSuccess,
)
from app.static import (
    HTTP_400_RESPONSE,
    HTTP_403_RESPONSE,
    HTTP_404_RESPONSE,
    HTTP_409_RESPONSE,
    PermissionsActions,
    UserMessages,
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


@users_router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=UserCreationSuccess,
    responses={
        **HTTP_409_RESPONSE(message=UserMessages.email_already_taken),
        **HTTP_400_RESPONSE(message="Role not found"),
    },
)
async def create(
    input_user: CreateUserSchema,
    current_user: Annotated[CurrentUserSchema, Depends(AuthorizedUser(SettingsPermissions(PermissionsActions.edit)))],
    db_session: Session = Depends(get_session),
):
    # Company admin should be able to create users only inside own company
    UserHelper().validate_company_admin_access(current_user, input_user.parent_company_id, "create")

    parent_company = UserHelper.get_company_or_400(input_user.parent_company_id, db_session)
    role = UserHelper.get_role_or_400(input_user.role_id, db_session)
    UserHelper.validate_company_type_allows_role(parent_company, role)

    # requested sites exist
    sites = SiteCRUD(db_session).bulk_get_by_id(input_user.sites_ids)

    raw_user = BaseUserSchema(**input_user.model_dump())
    if len(sites) != len(input_user.sites_ids):
        found_sites_ids = [site.id for site in sites]
        missing_sites_ids = list(set(input_user.sites_ids) - set(found_sites_ids))
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            UserMessages.sites_not_found.value.format(", ".join(str(id_) for id_ in missing_sites_ids)),
        )

    try:
        # add a user
        user = UserCRUD(db_session).create_item(raw_user.model_dump())
        # attach sites and companies
        UserProjectCRUD(db_session).create_items(
            [{"user_id": user.id, "site_id": site.id, "company_id": site.company_id} for site in sites]
        )
    except UniqueConstraintViolationError:
        logger.exception(message := UserMessages.email_already_taken)
        raise HTTPException(status.HTTP_409_CONFLICT, message)

    response_message = f"A new user {user.first_name} {user.last_name} was added"

    # create invitation instance and send an email
    user_invitation_handler = UserInvitationsHandler(db_session=db_session, user=user)
    user_invitation_handler.create_invitation_object()
    email_sending_error = EmailUtility().send_invitation_email(recipient=user, token=user_invitation_handler.token)
    if email_sending_error:
        response_message += " but the registration email could not be send. Please resend the invitation."
    return {"code": status.HTTP_201_CREATED, "message": response_message}


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


@users_router.put(
    "/{user_id}",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=UserUpdateSuccess,
    responses={**HTTP_404_RESPONSE, **HTTP_409_RESPONSE(message=UserMessages.email_already_taken)},
)
def update_user(
    user_id: int,
    payload: EditUserSchema,
    current_user: Annotated[CurrentUserSchema, Depends(AuthorizedUser(SettingsPermissions(PermissionsActions.edit)))],
    db_session: Session = Depends(get_session),
):
    # validation
    user_crud = UserCRUD(db_session)
    if not (user := user_crud.get_by_id(user_id)):
        logger.warning(f"Target user with id {user_id} is not found")
        raise HTTPException(status.HTTP_404_NOT_FOUND)

    # Company admin should be able to create/update users only inside own company
    UserHelper().validate_company_admin_access(current_user, payload.parent_company_id, "update")

    new_parent_company_id, old_parent_company_id = payload.parent_company_id, user.parent_company_id
    is_parent_company_id_changed = new_parent_company_id != old_parent_company_id
    is_role_id_changed = (new_role_id := payload.role_id) != user.role.id
    is_phone_changed = (new_phone := payload.phone) != user.phone

    if is_parent_company_id_changed or is_role_id_changed:
        parent_company = (
            UserHelper.get_company_or_400(new_parent_company_id, db_session)
            if is_parent_company_id_changed
            else user.parent_company
        )
        role = UserHelper.get_role_or_400(new_role_id, db_session) if is_role_id_changed else user.role
        UserHelper.validate_company_type_allows_role(parent_company, role)

    new_sites_ids, existing_sites_ids, site_by_id_map = set(payload.sites_ids), set(), {}
    for site in user.sites:
        existing_sites_ids.add(site_id := site.id)
        site_by_id_map[site_id] = site

    sites_ids_to_add = new_sites_ids - existing_sites_ids  # those from new that are not present in existing
    user_projects_to_add, missing_sites_ids = [], []
    if sites_ids_to_add:
        for site_id in sites_ids_to_add:
            target_site = SiteCRUD(db_session).get_by_id(site_id)
            if not target_site:
                missing_sites_ids.append(site_id)
                continue
            user_projects_to_add.append({"user_id": user.id, "site_id": site_id, "company_id": target_site.company_id})
        if missing_sites_ids:
            logger.warning(
                msg := UserMessages.sites_not_found.value.format(", ".join(str(id_) for id_ in missing_sites_ids))
            )
            raise HTTPException(status.HTTP_400_BAD_REQUEST, msg)

    new_email, old_email = payload.email, user.email
    if (is_email_changed := new_email != old_email) and user_crud.get_by_email(new_email):
        logger.warning("Provided new email can't be used as it is already registered in the system")
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            UserMessages.email_already_taken,
        )

    # db change
    if is_parent_company_id_changed:
        user.parent_company_id = new_parent_company_id
    if is_role_id_changed:
        user.role_id = new_role_id
    if is_email_changed:
        user.email = new_email
        EmailUtility().send_email_change_notification(
            username=user.first_name, old_user_email=old_email, user_email=new_email
        )
    if is_phone_changed:
        user.phone = new_phone

    user_project_crud = UserProjectCRUD(db_session)
    if sites_ids_to_remove := existing_sites_ids - new_sites_ids:  # those from existing that are not present in new
        user_project_crud.delete_items_by_composite_nonpk(
            [
                {"user_id": user.id, "site_id": site_id, "company_id": site_by_id_map[site_id].company_id}
                for site_id in sites_ids_to_remove
            ],
            autocommit=False,
        )

    if user_projects_to_add:
        user_project_crud.create_items(user_projects_to_add, autocommit=False)

    db_session.commit()

    return {"code": status.HTTP_202_ACCEPTED, "message": f"User {user.first_name} {user.last_name} was updated"}


@users_router.post(
    "/{user_id}/resend-invite",
    description="Resend invitation email for non-registered users",
    response_model=UserResendInvitationSuccess,
    responses={**HTTP_404_RESPONSE},
    dependencies=[Depends(AuthorizedUser(SettingsPermissions(PermissionsActions.edit)))],
)
async def resend_invitation_email(
    user_id: int,
    db_session: Session = Depends(get_session),
):
    # validate that user exists, and they are not registered so far
    user = UserCRUD(db_session).get_by_id(user_id)
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
    if user.is_registered:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "The user has registered already",
        )
    # update existing transactional record
    user_invitation_handler = UserInvitationsHandler(db_session=db_session, user=user)
    user_invitation_handler.update_invitation_object()
    email_sending_error = EmailUtility().send_invitation_reminder_email(
        recipient=user, token=user_invitation_handler.token
    )
    if email_sending_error:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "The registration email could not be resend. Please try again later",
        )
    return {"code": status.HTTP_200_OK, "message": "The registration email has been resent"}


@users_router.delete(
    "/{user_id}/internal",
    dependencies=[Depends(api_key_check)],
    status_code=status.HTTP_204_NO_CONTENT,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
)
async def delete(user_id: int, db_session: Session = Depends(get_session)):
    deleted_count = UserCRUD(db_session).delete_by_id(user_id)
    if deleted_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND)
