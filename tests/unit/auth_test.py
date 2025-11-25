"""Tests for auth-related logic."""

from datetime import datetime, timedelta, timezone
from time import sleep

import pytest

import tests.unit.samples as samples
from app.crud.session import SessionCRUD
from app.settings import settings
from tests.utils import gen_jwt


class TestLoginAPI:

    LOGIN_API_ENDPOINT = "/api/auth/login"

    @pytest.mark.parametrize(
        "input_data,expected_status,expected_error",
        (
            # missing required fields
            ({}, 422, samples.LOGIN_PAYLOAD_MISSING_REQUIRED_FIELDS_ERR),
            ({"password": "secret"}, 422, samples.LOGIN_PAYLOAD_MISSING_EMAIL_ERR),
            ({"email": "test@email.com"}, 422, samples.LOGIN_PAYLOAD_MISSING_PASSWORD_ERR),
            # user validation errors
            ({"email": "test@email.com", "password": "test"}, 400, samples.LOGIN_PAYLOAD_USER_404_ERR),
            (samples.LOGIN_PAYLOAD_WRONG_PASSWORD, 400, samples.LOGIN_PAYLOAD_WRONG_PASSWORD_ERR),
        ),
    )
    def test_login_negative(self, input_data, expected_status, expected_error, client):
        response = client.post(self.LOGIN_API_ENDPOINT, json=input_data)

        assert response.status_code == expected_status
        assert response.json() == {"code": expected_status, "message": expected_error}

    def test_login_unregistered_user(self, client, company_member_user, fake_get_current_user):
        fake_get_current_user.is_registered = False
        response = client.post(self.LOGIN_API_ENDPOINT, json={"email": samples.TEST_USER_EMAIL, "password": ""})
        assert response.status_code == 400
        assert response.json() == {"code": 400, "message": samples.LOGING_PAYLOAD_ACC_NOT_SET_UP_ERR}

    @pytest.mark.parametrize(
        "login_payload",
        (
            samples.LOGIN_PAYLOAD_VALID,
            samples.LOGIN_PAYLOAD_VALID_EMAIL_UPPER,
        ),
    )
    def test_login_positive(self, client, mocker, login_payload):
        """Validate user is able to login independently of email case
        (https://softserve-jirasw.atlassian.net/browse/IOSP1-460)"""
        test_jwt = "test.jwt.value"
        jwt_encoder_mock = mocker.patch("app.helpers.authentication.jwt.encode", return_value=test_jwt)

        response = client.post(self.LOGIN_API_ENDPOINT, json=login_payload)

        assert response.status_code == 200
        assert response.json() == {"access_token": test_jwt, "token_type": "bearer"}
        jwt_encoder_mock.assert_called_once()

    def test_logout_success(self, client, non_system_user_auth_header, non_system_user_session_id, db_session):
        response = client.delete(self.LOGIN_API_ENDPOINT, headers=non_system_user_auth_header)

        assert response.status_code == 204

        # check that session is removed from db
        assert SessionCRUD(db_session).get_by_id(non_system_user_session_id) is None

    def test_logout_401(self, client):
        response = client.delete(self.LOGIN_API_ENDPOINT)

        assert response.status_code == 401


class TestAuthBackgroundTasks:

    LOGIN_API_ENDPOINT = "/api/auth/login"

    def test_expired_session_cleanup(
        self, client, non_system_user_id, non_system_user_auth_header, non_system_user_session_id, db_session
    ):
        # create another session in db with expiration date in past so that it makes session already expired
        expires_at = datetime.now(timezone.utc) - timedelta(minutes=settings.access_token_expire_minutes)
        session_crud = SessionCRUD(db_session)
        target_session_id = session_crud.create_item({"user_id": non_system_user_id, "expires_at": expires_at}).id
        assert session_crud.get_by_id(target_session_id) is not None

        response = client.delete(self.LOGIN_API_ENDPOINT, headers=non_system_user_auth_header)
        assert response.status_code == 204

        # wait for background task to fire; should be faster than 1 sec, but prevent tests flakiness by longer wait
        sleep(1)

        # check that session is removed from db
        assert session_crud.get_by_id(target_session_id) is None

    def test_non_expired_session_remains(
        self, client, non_system_user_id, non_system_user_auth_header, non_system_user_session_id, db_session
    ):
        # create another session in db with expiration date in future so that it makes session not expired yet
        expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
        session_crud = SessionCRUD(db_session)
        target_session_id = session_crud.create_item({"user_id": non_system_user_id, "expires_at": expires_at}).id
        assert session_crud.get_by_id(target_session_id) is not None

        response = client.delete(self.LOGIN_API_ENDPOINT, headers=non_system_user_auth_header)
        assert response.status_code == 204

        # wait for background task to fire; should be faster than 1 sec, but prevent tests flakiness by longer wait
        sleep(1)

        # check that session is not removed from db
        assert session_crud.get_by_id(target_session_id) is not None


class TestAuthDependency:
    """Test for Authorization header processing"""

    AUTH_TEST_ENDPOINT = "/auth-test"

    def test_auth_missing_header(self, client, mocker):
        logger_mock = mocker.patch("app.dependencies.logger")

        response = client.get(self.AUTH_TEST_ENDPOINT)

        assert response.status_code == 401
        logger_mock.error.assert_called_with(samples.AUTH_MISSING_HEADER_ERR)

    @pytest.mark.parametrize(
        "header,expected_log_message",
        (
            # missing header
            ("", samples.AUTH_MISSING_HEADER_ERR),
            # wrong format
            ("wrong", samples.AUTH_HEADER_TOO_SHORT_ERR),
            ("wrong header value", samples.AUTH_HEADER_TOO_LONG_ERR),
            ("not bearer", samples.AUTH_HEADER_WRONG_FORMAT),
        ),
    )
    def test_auth_invalid_header(self, header, expected_log_message, client, mocker):
        logger_mock = mocker.patch("app.dependencies.logger")

        response = client.get(self.AUTH_TEST_ENDPOINT, headers={"Authorization": header})

        assert response.status_code == 401
        logger_mock.error.assert_called_with(expected_log_message)

    @pytest.mark.parametrize(
        "jwt_value,expected_log_message",
        (
            # invalid jwt format
            ("test", samples.AUTH_HEADER_NOT_JWT_ERR),
            # expired JWT
            (gen_jwt(payload={}, ttl=-1), samples.AUTH_HEADER_JWT_EXPIRED_ERR),
            # sub isn't an integer
            (
                gen_jwt(payload={"sub": settings.system_user_email}, ttl=1),
                samples.AUTH_HEADER_JWT_WRONG_SUB_FORMAT_ERR,
            ),
            # wrong session id in payload
            (
                gen_jwt(payload={"sub": 99999999}, ttl=1),
                samples.AUTH_SESSION_ID_NOT_FOUND_ERR,
            ),
        ),
    )
    def test_auth_invalid_jwt(self, jwt_value, expected_log_message, client, mocker):
        logger_mock = mocker.patch("app.helpers.authentication.logger")

        response = client.get(self.AUTH_TEST_ENDPOINT, headers={"Authorization": f"Bearer {jwt_value}"})

        assert response.status_code == 401
        logger_mock.error.assert_any_call(expected_log_message)

    def test_auth_without_sub_in_payload(self, client, mocker, non_system_user_session_id):
        logger_mock = mocker.patch("app.helpers.authentication.logger")
        jwt_value = gen_jwt(payload={"session_id": non_system_user_session_id}, ttl=1)
        response = client.get(self.AUTH_TEST_ENDPOINT, headers={"Authorization": f"Bearer {jwt_value}"})

        assert response.status_code == 401
        logger_mock.error.assert_called_with(samples.AUTH_HEADER_JWT_MISSING_SUB_ERR)

    def test_auth_valid(self, client, system_user_auth_header):
        response = client.get(self.AUTH_TEST_ENDPOINT, headers=system_user_auth_header)

        assert response.status_code == 200
        assert response.json() == {"message": "test"}
