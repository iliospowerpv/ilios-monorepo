import logging
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy.exc import DataError
from sqlalchemy.orm import Session

from app.crud.session import SessionCRUD
from app.crud.user import UserCRUD
from app.db.session import get_session
from app.dependencies import validate_auth_header
from app.schema import Token
from app.schema.message import BadRequestError
from app.settings import settings
from app.static.messages import UserAccountMessages

logger = logging.getLogger(__name__)

ALGORYTHM = "HS256"


def get_password_hash(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


class AuthenticationHandler:
    """Handles user login process"""

    @staticmethod
    def _verify_password(plain_password, hashed_password):
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())

    @staticmethod
    def create_access_token(data: dict, access_token_expire_minutes: int = settings.access_token_expire_minutes):
        to_encode = data.copy()
        expires_delta = timedelta(minutes=access_token_expire_minutes)
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=ALGORYTHM)
        return encoded_jwt

    def authenticate_user(self, request: Request, email: str, password: str, db_session: Session):  # noqa: CFQ004
        """Authenticate user and if valid return JWT token for the session"""
        user = UserCRUD(db_session).get_by_email(email=email)
        if not user:
            return JSONResponse(
                content=jsonable_encoder(BadRequestError(message=UserAccountMessages.account_not_exists)),
                status_code=status.HTTP_400_BAD_REQUEST,
            )

        request.state.current_user_id = user.id

        if not user.is_registered:
            return JSONResponse(
                content=jsonable_encoder(BadRequestError(message=UserAccountMessages.account_not_setup)),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        if not self._verify_password(password, user.hashed_password):
            return JSONResponse(
                content=jsonable_encoder(BadRequestError(message="The password is incorrect")),
                status_code=status.HTTP_400_BAD_REQUEST,
            )
        # generate and save auth session to db
        session_id = SessionCRUD(db_session).create_item({"user_id": user.id}).id

        # generate JWT using session_id as primary key
        access_token = self.create_access_token(data={"sub": session_id})

        return JSONResponse(content=jsonable_encoder(Token(access_token=access_token, token_type="bearer")))


def get_current_user(
    request: Request, token: str = Depends(validate_auth_header), db_session: Session = Depends(get_session)
):
    """Parse JWT and return current user object"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate JWT",
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORYTHM])
    except (jwt.ExpiredSignatureError, jwt.DecodeError) as exc:
        logger.error(f"JWT parsing error: {str(exc)}")
        raise credentials_exception

    session_id: int = payload.get("sub")
    if session_id is None:
        logger.error("JWT payload doesn't have the 'sub' key.")
        raise credentials_exception

    auth_session = None
    try:
        auth_session = SessionCRUD(db_session).get_by_id(session_id)
    except DataError:
        # handle the case of JWT transition, otherwise old tokens will raise 500, for example
        #   (psycopg2.errors.InvalidTextRepresentation) invalid input syntax for type integer: "admin@admin.com"
        #   LINE 3: WHERE sessions.id = 'admin@admin.com'
        # since before <sub> was email, and now it's ID
        # TODO can be removed in a couple of sprints
        logger.error(f"Data error occurred while getting session by session_id <{session_id}>")
    if auth_session is None:
        logger.error(f"No auth session found by session_id <{session_id}>")
        raise credentials_exception

    user = auth_session.user

    user_id = user.id
    request.state.current_user_id = user_id
    request.state.auth_session_id = session_id
    logger.debug(f"Successfully authenticated user with id={user_id} (session_id={session_id}) for '{request.url.path}'")
    return user


def api_key_check(api_key: str) -> str:
    """Raises 403 Forbidden if provided api key param doesn't match api key configured in the app settings"""
    if api_key != settings.api_key:
        raise HTTPException(403)
    return api_key


def cleanup_expired_auth_sessions(db_session: Session):
    """Function that can be used as a background task to remove expired sessions from db"""
    logger.debug("Starting background task for expired sessions cleanup...")
    deleted_count = SessionCRUD(db_session).delete_expired()
    logger.info(f"Background task for expired sessions cleanup has concluded, deleted count: {deleted_count}")
