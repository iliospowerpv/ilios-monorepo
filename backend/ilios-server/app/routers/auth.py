import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Request, status
from fastapi.params import Depends
from sqlalchemy.orm import Session

from app.crud.session import SessionCRUD
from app.db.session import get_session
from app.helpers.authentication import AuthenticationHandler, cleanup_expired_auth_sessions, get_current_user
from app.schema.auth_token import Token, UserLoginSchema
from app.schema.user import CurrentUserSchema
from app.static import HTTP_400_RESPONSE

logger = logging.getLogger(__name__)
auth_router = APIRouter()


@auth_router.post(
    "/login",
    response_model=Token,
    responses={
        **HTTP_400_RESPONSE(message="Wrong credentials"),
        status.HTTP_422_UNPROCESSABLE_ENTITY: {
            "content": {
                "application/json": {
                    "example": {"code": status.HTTP_422_UNPROCESSABLE_ENTITY, "message": "Validation error"}
                }
            },
        },
    },
)
async def login_for_access_token(
    request: Request, user_creds: UserLoginSchema, db_session: Session = Depends(get_session)
):
    return AuthenticationHandler().authenticate_user(request=request, db_session=db_session, **user_creds.model_dump())


@auth_router.delete("/login", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    background_tasks: BackgroundTasks,
    db_session: Session = Depends(get_session),
):
    auth_session_id = request.state.auth_session_id
    SessionCRUD(db_session).delete_by_id(auth_session_id)
    logger.info(f"Successfully logged out user with id {current_user.id} of {auth_session_id} session")
    background_tasks.add_task(cleanup_expired_auth_sessions, db_session)
