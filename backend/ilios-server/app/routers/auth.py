import logging
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.params import Depends
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.crud.session import SessionCRUD
from app.db.session import get_session
from app.helpers.auth_security import (
    EVENT_LOGIN,
    OUTCOME_FAILURE,
    OUTCOME_LOCKED,
    OUTCOME_RATE_LIMITED,
    OUTCOME_SUCCESS,
    check_account_lockout,
    check_login_ip_rate_limit,
    clear_failed_logins_for_identifier,
    get_request_ip,
    get_request_ua,
    hash_identifier,
    record_event,
)
from app.helpers.authentication import AuthenticationHandler, cleanup_expired_auth_sessions, get_current_user
from app.schema.auth_token import Token, UserLoginSchema
from app.schema.message import BadRequestError
from app.schema.user import CurrentUserSchema
from app.static import HTTP_400_RESPONSE

logger = logging.getLogger(__name__)
auth_router = APIRouter()

# Generic message used for both bad-credentials and account-lockout
# responses so the caller cannot tell whether the account exists or
# is currently locked.
_GENERIC_BAD_CREDENTIALS = "Wrong credentials"
# Generic message for rate-limited responses. Kept distinct from
# bad-credentials so a legitimate user knows to wait, but contains no
# information about the targeted account.
_GENERIC_RATE_LIMITED = "Too many login attempts. Please try again later."


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
        status.HTTP_429_TOO_MANY_REQUESTS: {
            "content": {
                "application/json": {
                    "example": {
                        "code": status.HTTP_429_TOO_MANY_REQUESTS,
                        "message": _GENERIC_RATE_LIMITED,
                    }
                }
            },
        },
    },
)
async def login_for_access_token(
    request: Request, user_creds: UserLoginSchema, db_session: Session = Depends(get_session)
):
    ip = get_request_ip(request)
    ua = get_request_ua(request)
    identifier_hash = hash_identifier(user_creds.email)

    # 1) Per-IP rate limit. Counts only failed/limited attempts so legitimate
    # users behind a shared NAT don't penalize each other on success.
    rl = check_login_ip_rate_limit(db_session, ip)
    if not rl.allowed:
        record_event(
            db_session,
            event_type=EVENT_LOGIN,
            outcome=OUTCOME_RATE_LIMITED,
            identifier_hash=identifier_hash,
            ip_address=ip,
            user_agent=ua,
            reason=rl.reason,
        )
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content=jsonable_encoder(
                BadRequestError(code=status.HTTP_429_TOO_MANY_REQUESTS, message=_GENERIC_RATE_LIMITED)
            ),
            headers={"Retry-After": str(rl.retry_after_seconds or 60)},
        )

    # 2) Per-account lockout. Returns the same generic 400 as bad credentials
    # so the response does not disclose whether the account exists.
    lk = check_account_lockout(db_session, identifier_hash)
    if not lk.allowed:
        record_event(
            db_session,
            event_type=EVENT_LOGIN,
            outcome=OUTCOME_LOCKED,
            identifier_hash=identifier_hash,
            ip_address=ip,
            user_agent=ua,
            reason=lk.reason,
        )
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=jsonable_encoder(BadRequestError(message=_GENERIC_BAD_CREDENTIALS)),
        )

    # 3) Delegate to the existing handler, then record the outcome.
    response = AuthenticationHandler().authenticate_user(
        request=request, db_session=db_session, **user_creds.model_dump()
    )
    is_success = 200 <= response.status_code < 300
    user_id = getattr(request.state, "current_user_id", None)
    if is_success:
        record_event(
            db_session,
            event_type=EVENT_LOGIN,
            outcome=OUTCOME_SUCCESS,
            user_id=user_id,
            identifier_hash=identifier_hash,
            ip_address=ip,
            user_agent=ua,
        )
        clear_failed_logins_for_identifier(db_session, identifier_hash)
    else:
        # Granular internal reason set by AuthenticationHandler. Defaults
        # to "bad_credentials" for unexpected paths (e.g. legacy/forced
        # 4xx). Reasons stay in the security-event log only — never on
        # the user-facing response (see Phase 0C / runbook §11).
        reason = getattr(request.state, "auth_failure_reason", None) or "bad_credentials"
        record_event(
            db_session,
            event_type=EVENT_LOGIN,
            outcome=OUTCOME_FAILURE,
            user_id=user_id,
            identifier_hash=identifier_hash,
            ip_address=ip,
            user_agent=ua,
            reason=reason,
        )
    return response


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
