TEST_USER_NAME = "Jane"
TEST_USER_LAST_NAME = "Doe"
TEST_USER_EMAIL = "test@user.com"
TEST_USER_PHONE = "0302456789"
BASE_USER_OBJECT = {
    "first_name": TEST_USER_NAME,
    "last_name": TEST_USER_LAST_NAME,
    "email": TEST_USER_EMAIL,
    "phone": TEST_USER_PHONE,
}
USER_CREATION_WRONG_SITE_ID = 1234321

CREATE_USER_SUCCESS_MSG = f"A new user {TEST_USER_NAME} {TEST_USER_LAST_NAME} was added"
RESEND_INVITATION_SUCCESS_MSG = "The registration email has been resent"
CREATE_USER_PARTIAL_SUCCESS_MSG = (
    CREATE_USER_SUCCESS_MSG + " but the registration email could not be send. Please resend the invitation."
)
USER_UNIQUE_EMAIL_CONSTRAINT_ERR = "Another user with such email already exists"
USER_EMPTY_SITES_ERR = "Validation error: body.sites_ids - List should have at least 1 item after validation, not 0"
USER_NOT_INT_SITES_ERR = (
    "Validation error: body.sites_ids.1 - Input should be a valid integer, unable to parse string as an integer"
)
USER_MISSING_SITES_ERR = f"Some of requested sites not found: {USER_CREATION_WRONG_SITE_ID}"
USER_MISSING_REQ_FIELDS_ERR = (
    "Validation error: body.email - Field required; body.parent_company_id - Field required; body.role_id - Field "
    "required; body.phone - Field required; body.first_name - Field required; body.last_name - Field required; "
    "body.sites_ids - Field required"
)

RESEND_INVITATION_USER_REGISTERED_ERR = "The user has registered already"
RESEND_INVITATION_EMAIL_SENDING_ERR = "The registration email could not be resend. Please try again later"

NON_SYSTEM_USER_NAME = "Non-system"
NON_SYSTEM_USER_LAST_NAME = "Non-admin"
NON_SYSTEM_USER_EMAIL = "nonsystem@gmail.com"
