"""Place of /account views."""

import logging
from typing import Annotated

from fastapi import APIRouter, HTTPException, status
from fastapi.params import Depends
from pydantic import EmailStr
from sqlalchemy.orm import Session

from app.crud.user import UserCRUD
from app.crud.user_invitation import UserInvitationCRUD
from app.crud.user_password_recovery import UserPasswordRecoveryCRUD
from app.db.session import get_session
from app.helpers.authentication import get_current_user, get_password_hash
from app.helpers.authorization.custom.diligence_overview_page import DiligenceOverviewPagePermissions
from app.helpers.email import EmailTokenValidator, EmailUtility
from app.helpers.password_recovery_handler import UserPasswordRecoveryHandler
from app.schema.account import PasswordCreationSuccess, PasswordSetupPayload
from app.schema.auth_token import ResetPasswordSchema
from app.schema.message import Success
from app.schema.user import AccountMgmtModeEnum, CurrentUserSchema, InvitationTokenValidationSuccess, MyUserSchema
from app.static import HTTP_400_RESPONSE, HTTP_410_RESPONSE
from app.static.messages import AccountMessages, UserAccountMessages

account_router = APIRouter()

logger = logging.getLogger(__name__)

MAP_OF_CRUD_HANDLERS_BY_MODE = {
    "sign-up": UserInvitationCRUD,
    "recovery": UserPasswordRecoveryCRUD,
}


@account_router.get(
    "/me",
    response_model=MyUserSchema,
)
async def my_user(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
):
    # define if user has permission for the Diligence Overview page access
    # set it as false by default
    try:
        DiligenceOverviewPagePermissions()(current_user)
        # set it as True if user passes the validation
        diligence_overview_access = True
    except HTTPException:
        diligence_overview_access = False
    current_user.diligence_overview_access = diligence_overview_access
    return current_user


@account_router.get(
    "/email-token",
    response_model=InvitationTokenValidationSuccess,
    responses={
        **HTTP_400_RESPONSE(message=AccountMessages.link_deactivated),
        **HTTP_410_RESPONSE(message=AccountMessages.link_expired),
    },
)
async def email_token_validation(
    email: EmailStr,
    token: str,
    mode: AccountMgmtModeEnum,
    db_session: Session = Depends(get_session),
):
    db_access_layer = MAP_OF_CRUD_HANDLERS_BY_MODE[mode]
    user_password_deeplink = db_access_layer(db_session).get_by_token(token)
    EmailTokenValidator.validate(email, token, user_password_deeplink)
    return {"code": status.HTTP_200_OK, "message": "Token is valid"}


@account_router.post(
    "/password-setup",
    response_model=PasswordCreationSuccess,
    responses={
        **HTTP_400_RESPONSE(message=AccountMessages.link_deactivated),
        **HTTP_410_RESPONSE(message=AccountMessages.link_expired),
    },
)
async def password_setup(
    payload: PasswordSetupPayload,
    mode: AccountMgmtModeEnum,
    db_session: Session = Depends(get_session),
):
    token, password = payload.token, payload.password
    db_access_layer = MAP_OF_CRUD_HANDLERS_BY_MODE[mode]
    user_password_deeplink = db_access_layer(db_session).get_by_token(token)

    EmailTokenValidator.validate(payload.email, token, user_password_deeplink)

    user = user_password_deeplink.user
    user.hashed_password = get_password_hash(password)
    user.is_registered = True
    db_session.delete(user_password_deeplink)

    db_session.commit()

    return {"code": status.HTTP_200_OK, "message": "Password has been set successfully"}


@account_router.post(
    "/password-recovery",
    response_model=Success,
    responses={
        **HTTP_400_RESPONSE(message=UserAccountMessages.account_not_exists),
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "content": {
                "application/json": {
                    "example": {
                        "code": status.HTTP_422_UNPROCESSABLE_ENTITY,
                        "message": UserAccountMessages.account_not_setup,
                    }
                }
            },
        },
        status.HTTP_200_OK: {
            "content": {
                "application/json": {
                    "example": {"code": status.HTTP_200_OK, "message": "Email with password reset instructions was sent"}
                }
            },
        },
    },
)
async def password_recovery(reset_data: ResetPasswordSchema, db_session: Session = Depends(get_session)):
    user = UserCRUD(db_session).get_by_email(reset_data.email)
    if not user:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, UserAccountMessages.account_not_exists)
    if not user.is_registered:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, UserAccountMessages.account_not_setup)

    password_reset_handler = UserPasswordRecoveryHandler(db_session=db_session, user=user)
    password_reset_handler.update_password_recovery_object()
    email_sending_error = EmailUtility().send_password_recovery_email(recipient=user, token=password_reset_handler.token)
    if email_sending_error:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "The reset password email could not be send. Please try again.",
        )
    return {"code": status.HTTP_200_OK, "message": "Email with password reset instructions was sent"}
