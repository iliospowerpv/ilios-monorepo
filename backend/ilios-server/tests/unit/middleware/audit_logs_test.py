import pytest

from app.crud.audit_log import AuditLogCRUD
from app.settings import settings
from tests.unit import samples


class TestAuditLog:
    LOGIN_API_ENDPOINT = "/api/auth/login"

    @pytest.fixture(autouse=True)
    def setup_method(self, db_session):
        settings.enable_audit_logger = True

    def teardown_method(self):
        settings.enable_audit_logger = False

    def test_audit_log_w_login_positive(self, client, mocker, db_session):
        mocker.patch("app.helpers.authentication.jwt.encode", return_value="test.jwt.value")

        response = client.post(self.LOGIN_API_ENDPOINT, json=samples.LOGIN_PAYLOAD_VALID)

        assert response.status_code == 200
        assert response.json() == {"access_token": "test.jwt.value", "token_type": "bearer"}

        audit_log = AuditLogCRUD(db_session).get_by_id(response.headers["x-request-audit-id"])
        assert audit_log.is_success is True
        assert audit_log.details is None
        assert audit_log.source == "Authentication"
        assert audit_log.action == "Login"
        assert audit_log.user.email == samples.LOGIN_PAYLOAD_VALID["email"]

    def test_audit_log_w_missing_pw_auth(self, client, db_session):
        response = client.post(self.LOGIN_API_ENDPOINT, json=samples.LOGIN_PAYLOAD_WRONG_PASSWORD)

        assert response.status_code == 400
        assert response.json() == {"code": 400, "message": samples.LOGIN_PAYLOAD_WRONG_PASSWORD_ERR}

        audit_log = AuditLogCRUD(db_session).get_by_id(response.headers["x-request-audit-id"])
        assert audit_log.is_success is False
        assert audit_log.details == "The password is incorrect"
        assert audit_log.source == "Authentication"
        assert audit_log.action == "Login"
        assert audit_log.user.email == samples.LOGIN_PAYLOAD_VALID["email"]

    @pytest.mark.parametrize(
        "input_data,expected_status",
        (
            # missing required fields
            ({}, 422),
            ({"password": "secret"}, 422),
            ({"email": "test@email.com"}, 422),
            # user wrong email
            ({"email": "test@email.com", "password": "test"}, 400),
        ),
    )
    def test_no_audit_log(self, input_data, expected_status, client):
        """Test that there are no audit logs in case of ambiguous user identity"""
        response = client.post(self.LOGIN_API_ENDPOINT, json=input_data)

        assert response.status_code == expected_status

        assert response.headers.get("x-request-audit-id") is None

    def test_logout_log(self, db_session, client, func_scoped_system_user_auth_header):
        response = client.delete(self.LOGIN_API_ENDPOINT, headers=func_scoped_system_user_auth_header)
        audit_log = AuditLogCRUD(db_session).get_by_id(response.headers["x-request-audit-id"])

        assert response.status_code == 204

        assert audit_log.is_success is True
        assert audit_log.source == "Authentication"
        assert audit_log.action == "Logout"
        assert audit_log.user.email == samples.LOGIN_PAYLOAD_VALID["email"]
