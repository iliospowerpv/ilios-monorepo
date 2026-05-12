from app.settings import settings

LOGIN_PAYLOAD_VALID = {"email": settings.system_user_email, "password": settings.system_user_password}
LOGIN_PAYLOAD_VALID_EMAIL_UPPER = {
    "email": settings.system_user_email.upper(),
    "password": settings.system_user_password,
}
LOGIN_PAYLOAD_WRONG_PASSWORD = {"email": settings.system_user_email, "password": "wrong"}

LOGIN_PAYLOAD_MISSING_REQUIRED_FIELDS_ERR = (
    "Validation error: body.email - Field required; body.password - Field required"
)
LOGIN_PAYLOAD_MISSING_EMAIL_ERR = "Validation error: body.email - Field required"
LOGIN_PAYLOAD_MISSING_PASSWORD_ERR = "Validation error: body.password - Field required"
# Phase 0C: all login failure modes (no-such-account, account-not-set-up,
# wrong-password) return the SAME generic user-facing message so the
# response body cannot be used to enumerate accounts. Internal reason
# categories are preserved on the AuthSecurityEvent record.
_GENERIC_LOGIN_FAILURE = "Wrong credentials"
LOGIN_PAYLOAD_USER_404_ERR = _GENERIC_LOGIN_FAILURE
LOGIN_PAYLOAD_WRONG_PASSWORD_ERR = _GENERIC_LOGIN_FAILURE
LOGING_PAYLOAD_ACC_NOT_SET_UP_ERR = _GENERIC_LOGIN_FAILURE

AUTH_MISSING_HEADER_ERR = "Missing 'Authorization' header."
AUTH_HEADER_TOO_SHORT_ERR = "Expected 'Authorization' header in the format 'Bearer JWT', got 'wrong'."
AUTH_HEADER_TOO_LONG_ERR = "Expected 'Authorization' header in the format 'Bearer JWT', got 'wrong header value'."
AUTH_HEADER_WRONG_FORMAT = "Expected 'Authorization' header to be Bearer, got 'not'."
AUTH_HEADER_NOT_JWT_ERR = "JWT parsing error: Not enough segments"
AUTH_HEADER_JWT_EXPIRED_ERR = "JWT parsing error: Signature has expired"
AUTH_HEADER_JWT_MISSING_SUB_ERR = "JWT payload doesn't have the 'sub' key."
AUTH_HEADER_JWT_WRONG_SUB_FORMAT_ERR = (
    f"Data error occurred while getting session by session_id <{settings.system_user_email}>"
)
AUTH_HEADER_USER_NOT_FOUND_ERR = "No user found by email test@email.com"
AUTH_SESSION_ID_NOT_FOUND_ERR = "No auth session found by session_id <99999999>"
