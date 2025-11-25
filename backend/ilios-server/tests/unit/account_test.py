"""Tests for account routes."""

from collections import namedtuple
from datetime import datetime, timedelta

import pytest
from fastapi import status

import tests.unit.samples as samples
from app.settings import settings

UNEXISTING_USER_MAIL = "unexisting-user@mail.com"
EXISTING_USER_MAIL = "existing-user@mail.com"
VALID_MAILGUN_TOKEN = "3mWqJggjk7n-JFKXP53DNCx5ND9vfykZN1wCG3uRumM7drIuPsUBvaHy1ctnVRIx9eYuQyxaowX8qZ4pJhghwQ"

UserInvitationFakeModel = namedtuple("UserInvitationFakeModel", "user,expires_at")
UserPasswordRecoveryFakeModel = namedtuple("UserPasswordRecoveryFakeModel", "user,expires_at")

ACCOUNT_API_ENDPOINT = "/api/users/account"


class TestAccount:

    MY_USER_ENDPOINT = f"{ACCOUNT_API_ENDPOINT}/me"

    def test_my_user_no_sites_and_roles(self, client, system_user_auth_header):
        """Test that Get my account endpoint returns basic info of logged-in user."""
        response = client.get(self.MY_USER_ENDPOINT, headers=system_user_auth_header)
        assert response.status_code == 200
        assert response.json() == {
            "email": settings.system_user_email,
            "first_name": settings.system_user_first_name,
            "last_name": settings.system_user_last_name,
            "role": None,
            "role_id": None,
            "sites": [],
            "parent_company_id": None,
            "phone": settings.system_user_phone,
            "is_system_user": True,
            "diligence_overview_access": True,
        }

    def test_my_user(self, client, company_member_user_auth_header, role_id):
        """Test that endpoint returns extended info including roles and sites of logged-in user."""

        response = client.get(self.MY_USER_ENDPOINT, headers=company_member_user_auth_header)
        response_json = response.json()
        role, sites = response_json["role"], response_json["sites"]

        assert response.status_code == 200
        assert response_json["email"] == samples.TEST_USER_EMAIL
        assert response_json["first_name"] == samples.TEST_USER_NAME
        assert response_json["last_name"] == samples.TEST_USER_LAST_NAME
        assert role["id"] == role_id
        assert role["permissions"] is not None
        assert len(sites) == 1
        site = sites[0]
        assert len(site) == 3  # after minimising site obj schema we do not expect much info, only id, name, company
        assert site["name"] == "Windmills Farm"
        assert site["id"]

        site_company = site["company"]
        assert site_company["name"] == "Green Lantern"
        assert site_company["id"]


class TestResetPassword:

    RESET_PASSWORD_ENDPOINT = f"{ACCOUNT_API_ENDPOINT}/password-recovery"

    @pytest.mark.parametrize("user_obj_raw", [True], indirect=True)
    def test_reset_password_success(self, client, response_200, mocker, user_obj_raw):
        email_mock = mocker.patch("app.helpers.email.requests.post", return_value=response_200)

        response = client.post(self.RESET_PASSWORD_ENDPOINT, json={"email": samples.TEST_USER_EMAIL})

        assert response.json() == {"code": 200, "message": samples.RESET_PASSWORD_EMAIL_SUCCESS}
        assert email_mock.call_args.kwargs["data"]["to"] == [samples.TEST_USER_EMAIL]
        assert email_mock.call_args.kwargs["data"]["template"] == "Reset password"
        assert email_mock.call_args.kwargs["data"]["subject"] == "Reset password"

    def test_reset_password_no_account_err(self, client):
        user_email = "resetpassword@email.com"

        response = client.post(self.RESET_PASSWORD_ENDPOINT, json={"email": user_email})

        assert response.json() == {"code": 400, "message": samples.RESET_PASSWORD_ACCOUNT_NOT_EXIST_ERR}

    def test_reset_password_user_not_registered_err(self, client, user_obj_raw):
        response = client.post(self.RESET_PASSWORD_ENDPOINT, json={"email": samples.TEST_USER_EMAIL})

        assert response.json() == {"code": 422, "message": samples.RESET_PASSWORD_ACCOUNT_NOT_REGISTERED_ERR}

    @pytest.mark.parametrize("user_obj_raw", [True], indirect=True)
    def test_reset_password_fail_send_email(self, client, user_obj_raw, response_400, mocker):
        email_mock = mocker.patch("app.helpers.email.requests.post", return_value=response_400)

        response = client.post(self.RESET_PASSWORD_ENDPOINT, json={"email": samples.TEST_USER_EMAIL})

        assert response.json() == {"code": 400, "message": samples.RESET_PASSWORD_ACCOUNT_EMAIL_FAIL}
        assert email_mock.call_args.kwargs["data"]["to"] == [samples.TEST_USER_EMAIL]
        assert email_mock.call_args.kwargs["data"]["template"] == "Reset password"
        assert email_mock.call_args.kwargs["data"]["subject"] == "Reset password"


class TestSetupPassword:
    """Includes tests for token validation and password setup itself"""

    VALIDATE_TOKEN_ENDPOINT = f"{ACCOUNT_API_ENDPOINT}/email-token"
    PASSWORD_SETUP_ENDPOINT = f"{ACCOUNT_API_ENDPOINT}/password-setup"

    def test_validate_token(self, client, mocker):
        """Test that /validate-token endpoint gives 200 OK for valid token"""
        invitation_crud_spy = mocker.patch(
            "app.routers.account.UserInvitationCRUD.get_by_token",
            return_value=UserInvitationFakeModel(
                user=samples.UserFakeModel(email=EXISTING_USER_MAIL), expires_at=datetime.now() + timedelta(hours=1)
            ),
        )
        response = client.get(
            self.VALIDATE_TOKEN_ENDPOINT,
            params={
                "token": VALID_MAILGUN_TOKEN,
                "email": EXISTING_USER_MAIL,
                "mode": "sign-up",
            },
        )
        invitation_crud_spy.assert_called_with(VALID_MAILGUN_TOKEN)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Token is valid"

    def test_validate_token_recovery_mode(self, client, mocker):
        recovery_crud_spy = mocker.patch(
            "app.routers.account.UserPasswordRecoveryCRUD.get_by_token",
            return_value=UserPasswordRecoveryFakeModel(
                user=samples.UserFakeModel(email=EXISTING_USER_MAIL), expires_at=datetime.now() + timedelta(hours=1)
            ),
        )
        response = client.get(
            self.VALIDATE_TOKEN_ENDPOINT,
            params={
                "token": VALID_MAILGUN_TOKEN,
                "email": EXISTING_USER_MAIL,
                "mode": "recovery",
            },
        )
        recovery_crud_spy.assert_called_with(VALID_MAILGUN_TOKEN)
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Token is valid"

    @pytest.mark.parametrize(
        ("params", "expected_status_code", "expected_msg"),
        (
            # test token absence in db
            (
                {
                    "token": VALID_MAILGUN_TOKEN,
                    "email": UNEXISTING_USER_MAIL,
                    "mode": "sign-up",
                },
                status.HTTP_400_BAD_REQUEST,
                "The link is not active anymore, please, contact the admin",
            ),
            # test "email" query param validation
            (
                {
                    "token": VALID_MAILGUN_TOKEN,
                    "email": "unexisting#mail.com",
                    "mode": "sign-up",
                },
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                samples.QUERY_EMAIL_PATTERN_MISMATCH_ERR,
            ),
            # test wrong value of "mode" query param
            (
                {
                    "token": VALID_MAILGUN_TOKEN,
                    "email": UNEXISTING_USER_MAIL,
                    "mode": "sign-out",
                },
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Validation error: query.mode - Input should be 'sign-up' or 'recovery'",
            ),
        ),
    )
    def test_validate_token_exceptions(self, client, params, expected_status_code, expected_msg):
        """Test that multiple validations of /validate-token endpoint provide expected status codes and msgs"""
        response = client.get(
            self.VALIDATE_TOKEN_ENDPOINT,
            params=params,
        )
        assert response.status_code == expected_status_code
        assert response.json()["message"] == expected_msg

    def test_validate_token_wrong_invitation_email(self, client, mocker):
        """Test that /validate-token endpoint gives 400 for wrong email that is not attached to the token"""
        invitation_crud_mock = mocker.patch(
            "app.routers.account.UserInvitationCRUD.get_by_token",
            return_value=UserInvitationFakeModel(user=samples.UserFakeModel(email=EXISTING_USER_MAIL), expires_at=None),
        )
        response = client.get(
            self.VALIDATE_TOKEN_ENDPOINT,
            params={
                "token": VALID_MAILGUN_TOKEN,
                "email": UNEXISTING_USER_MAIL,
                "mode": "sign-up",
            },
        )

        invitation_crud_mock.assert_called_with(VALID_MAILGUN_TOKEN)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["message"] == "The link is not active anymore, please, contact the admin"

    def test_validate_token_gone(self, client, mocker):
        """Test that /validate-token endpoint gives 410 if request is for token that is expired"""
        invitation_crud_spy = mocker.patch(
            "app.routers.account.UserInvitationCRUD.get_by_token",
            return_value=UserInvitationFakeModel(
                user=samples.UserFakeModel(email=EXISTING_USER_MAIL), expires_at=datetime(year=1960, month=1, day=1)
            ),
        )
        response = client.get(
            self.VALIDATE_TOKEN_ENDPOINT,
            params={
                "token": VALID_MAILGUN_TOKEN,
                "email": EXISTING_USER_MAIL,
                "mode": "sign-up",
            },
        )
        invitation_crud_spy.assert_called_with(VALID_MAILGUN_TOKEN)
        assert response.status_code == status.HTTP_410_GONE
        assert response.json()["message"] == "The link has expired, please, contact the admin"

    @pytest.mark.parametrize(
        ("payload", "expected_status_code", "expected_msg"),
        (
            # test with valid pw and email format, but with token absence in db
            (
                {
                    "token": VALID_MAILGUN_TOKEN,
                    "email": UNEXISTING_USER_MAIL,
                    "password": "A1#password",
                },
                status.HTTP_400_BAD_REQUEST,
                "The link is not active anymore, please, contact the admin",
            ),
            # test "email" field validation
            (
                {
                    "token": VALID_MAILGUN_TOKEN,
                    "email": "unexisting#mail.com",
                    "password": "A1#password",
                },
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                samples.BODY_EMAIL_PATTERN_MISMATCH_ERR,
            ),
        ),
    )
    def test_password_setup_w_invalid_token(self, client, payload, expected_status_code, expected_msg):
        """Test that multiple validations of /validate-token endpoint provide expected status codes and msgs"""
        response = client.post(
            self.PASSWORD_SETUP_ENDPOINT,
            params={"mode": "sign-up"},
            json=payload,
        )
        assert response.status_code == expected_status_code
        assert response.json()["message"] == expected_msg

    @pytest.mark.parametrize(
        "password",
        (
            # at least 1 upper-case char required
            "a1#password",
            # at least 1 lower-case char required
            "A1#PASSWORD",
            # at least 1 digit required
            "A#password",
            # no white space required
            "A #1password",
        ),
    )
    def test_password_setup_w_invalid_pw_format(self, client, password):
        response = client.post(
            self.PASSWORD_SETUP_ENDPOINT,
            params={"mode": "sign-up"},
            json={"token": VALID_MAILGUN_TOKEN, "email": UNEXISTING_USER_MAIL, "password": password},
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert (
            response.json()["message"]
            == "Validation error: body.password - Value error, Password doesn't match required criteria"
        )

    def test_password_setup_wrong_invitation_email(self, client, mocker):
        """Test that /validate-token endpoint gives 400 for wrong email that is not attached to the token"""
        invitation_crud_mock = mocker.patch(
            "app.routers.account.UserInvitationCRUD.get_by_token",
            return_value=UserInvitationFakeModel(user=samples.UserFakeModel(email=EXISTING_USER_MAIL), expires_at=None),
        )
        response = client.post(
            self.PASSWORD_SETUP_ENDPOINT,
            json={
                "token": VALID_MAILGUN_TOKEN,
                "email": UNEXISTING_USER_MAIL,
                "password": "A1#password",
            },
            params={"mode": "sign-up"},
        )

        invitation_crud_mock.assert_called_with(VALID_MAILGUN_TOKEN)
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert response.json()["message"] == "The link is not active anymore, please, contact the admin"

    def test_password_setup_token_is_gone(self, client, mocker):
        """Test that /validate-token endpoint gives 410 if request is for token that is expired"""
        invitation_crud_spy = mocker.patch(
            "app.routers.account.UserInvitationCRUD.get_by_token",
            return_value=UserInvitationFakeModel(
                user=samples.UserFakeModel(email=EXISTING_USER_MAIL),
                expires_at=datetime(year=1960, month=1, day=1),
            ),
        )
        response = client.post(
            self.PASSWORD_SETUP_ENDPOINT,
            json={
                "token": VALID_MAILGUN_TOKEN,
                "email": EXISTING_USER_MAIL,
                "password": "A1#password",
            },
            params={"mode": "sign-up"},
        )
        invitation_crud_spy.assert_called_with(VALID_MAILGUN_TOKEN)
        assert response.status_code == status.HTTP_410_GONE
        assert response.json()["message"] == "The link has expired, please, contact the admin"

    def test_password_setup(self, client, mocker, db_session_spy):
        faked_user = samples.UserFakeModel(email=EXISTING_USER_MAIL)
        user_invitation_fake = UserInvitationFakeModel(user=faked_user, expires_at=datetime.now() + timedelta(hours=1))
        invitation_crud_spy = mocker.patch(
            "app.routers.account.UserInvitationCRUD.get_by_token",
            return_value=user_invitation_fake,
        )

        response = client.post(
            self.PASSWORD_SETUP_ENDPOINT,
            params={"mode": "sign-up"},
            json={
                "token": VALID_MAILGUN_TOKEN,
                "email": EXISTING_USER_MAIL,
                "password": "A1#password",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Password has been set successfully"
        invitation_crud_spy.assert_called_with(VALID_MAILGUN_TOKEN)
        assert faked_user.is_registered
        assert faked_user.hashed_password
        db_session_spy.delete.assert_called_with(user_invitation_fake)
        db_session_spy.commit.assert_called_once()

    def test_password_setup_recovery_mode(self, client, mocker, db_session_spy):
        faked_user = samples.UserFakeModel(email=EXISTING_USER_MAIL)
        user_recovery_fake = UserPasswordRecoveryFakeModel(
            user=faked_user, expires_at=datetime.now() + timedelta(hours=1)
        )
        recovery_crud_spy = mocker.patch(
            "app.routers.account.UserPasswordRecoveryCRUD.get_by_token",
            return_value=user_recovery_fake,
        )

        response = client.post(
            self.PASSWORD_SETUP_ENDPOINT,
            params={"mode": "recovery"},
            json={
                "token": VALID_MAILGUN_TOKEN,
                "email": EXISTING_USER_MAIL,
                "password": "A1#password",
            },
        )
        assert response.status_code == status.HTTP_200_OK
        assert response.json()["message"] == "Password has been set successfully"
        recovery_crud_spy.assert_called_with(VALID_MAILGUN_TOKEN)
        assert faked_user.is_registered
        assert faked_user.hashed_password
        db_session_spy.delete.assert_called_with(user_recovery_fake)
        db_session_spy.commit.assert_called_once()
