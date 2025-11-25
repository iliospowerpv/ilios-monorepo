"""Tests for users routes."""

from copy import deepcopy

import pytest

import tests.unit.samples as samples
from app.crud.site import SiteCRUD
from app.crud.user import UserCRUD
from app.crud.user_project import UserProjectCRUD
from app.settings import settings


class TestUser:
    """Tests for users routes."""

    USERS_API_ENDPOINT = "/api/users"
    ROLES_API_ENDPOINT = "/api/roles"
    RESEND_INVITATION_ENDPOINT_NAME = "resend-invite"

    def test_create_user_missing_required_fields(self, client, user_payload, system_user_auth_header):
        response = client.post(self.USERS_API_ENDPOINT, json={}, headers=system_user_auth_header)

        assert response.status_code == 422
        assert response.json() == {"code": 422, "message": samples.USER_MISSING_REQ_FIELDS_ERR}

    def test_create_user_no_parent_company(self, client, user_payload, system_user_auth_header):
        # adjust payload to have wrong parent company id
        payload = deepcopy(user_payload)
        payload["parent_company_id"] += 1

        response = client.post(self.USERS_API_ENDPOINT, json=payload, headers=system_user_auth_header)

        assert response.status_code == 400
        assert response.json() == {"code": 400, "message": "Parent company not found"}

    def test_create_user_no_role(self, client, user_payload, system_user_auth_header):
        # adjust payload to have wrong role id
        payload = deepcopy(user_payload)
        payload["role_id"] += 1

        response = client.post(self.USERS_API_ENDPOINT, json=payload, headers=system_user_auth_header)

        assert response.status_code == 400
        assert response.json() == {"code": 400, "message": "Role not found"}

    @pytest.mark.parametrize("role_id", [samples.TEST_COMPANY_TYPE2], indirect=True)
    def test_create_user_invalid_company_type_role_mapping(self, client, user_payload, system_user_auth_header, role_id):
        # use different role, which is not linked to the same company type as company from request
        payload = deepcopy(user_payload)
        payload["role_id"] = role_id

        response = client.post(self.USERS_API_ENDPOINT, json=payload, headers=system_user_auth_header)

        assert response.status_code == 400
        assert response.json() == {"code": 400, "message": "This role is not allowed for chosen company type"}

    @pytest.mark.parametrize(
        "sites_ids,expected_status_code,expected_error_message",
        (
            # validation errors
            # empty site ids
            ([], 422, samples.USER_EMPTY_SITES_ERR),
            # sites ids are not int
            ([1, "test"], 422, samples.USER_NOT_INT_SITES_ERR),
            # user input errors
            # non-existing site ID pass
            ([samples.USER_CREATION_WRONG_SITE_ID], 400, samples.USER_MISSING_SITES_ERR),
        ),
    )
    def test_create_user_wrong_sites(
        self, client, user_payload, system_user_auth_header, sites_ids, expected_status_code, expected_error_message
    ):
        # adjust payload to have wrong sites IDs
        payload = deepcopy(user_payload)
        payload["sites_ids"] = sites_ids

        response = client.post(self.USERS_API_ENDPOINT, json=payload, headers=system_user_auth_header)

        assert response.status_code == expected_status_code
        assert response.json() == {"code": expected_status_code, "message": expected_error_message}

    def test_create_user_success(self, client, user_payload, system_user_auth_header, response_200, mocker):
        email_mock = mocker.patch("app.helpers.email.requests.post", return_value=response_200)
        # Create user with new email to not mess up with company_member_user
        user_payload = deepcopy(user_payload)
        user_payload["email"] = "fully_new@user.email"
        response = client.post(self.USERS_API_ENDPOINT, json=user_payload, headers=system_user_auth_header)

        assert response.status_code == 201
        assert response.json() == {"code": 201, "message": samples.CREATE_USER_SUCCESS_MSG}
        assert email_mock.call_args.kwargs["data"]["to"] == ["fully_new@user.email"]
        assert email_mock.call_args.kwargs["data"]["template"] == "Invitation email"
        assert email_mock.call_args.kwargs["data"]["subject"] == "You're invited"

    def test_create_user_long_email_err(self, client, user_payload, system_user_auth_header, response_200, mocker):
        mocker.patch("app.helpers.email.requests.post", return_value=response_200)
        user_payload = deepcopy(user_payload)
        user_payload["email"] = samples.LONGER_THAN_100_CHARS_EMAIL
        response = client.post(self.USERS_API_ENDPOINT, json=user_payload, headers=system_user_auth_header)

        assert response.status_code == 422
        assert response.json() == {
            "code": 422,
            "message": samples.EMAIL_LENGTH_ERROR,
        }

    def test_create_user_partial_success(self, client, user_payload, system_user_auth_header, response_400, mocker):
        email_mock = mocker.patch("app.helpers.email.requests.post", return_value=response_400)
        user_payload = deepcopy(user_payload)
        user_payload["email"] = "another@email.com"
        response = client.post(self.USERS_API_ENDPOINT, json=user_payload, headers=system_user_auth_header)

        assert response.status_code == 201
        assert response.json() == {"code": 201, "message": samples.CREATE_USER_PARTIAL_SUCCESS_MSG}
        email_mock.assert_called_once()

    def test_create_user_duplicated(self, client, user_payload, system_user_auth_header, response_200, mocker):
        email_mock = mocker.patch("app.helpers.email.requests.post", return_value=response_200)
        user_payload = deepcopy(user_payload)
        user_payload["email"] = "another2@email.com"
        initial_user_adding_response = client.post(
            self.USERS_API_ENDPOINT, json=user_payload, headers=system_user_auth_header
        )
        duplicated_user_adding_response = client.post(
            self.USERS_API_ENDPOINT, json=user_payload, headers=system_user_auth_header
        )

        assert initial_user_adding_response.status_code == 201
        assert initial_user_adding_response.json() == {"code": 201, "message": samples.CREATE_USER_SUCCESS_MSG}
        assert duplicated_user_adding_response.status_code == 409
        assert duplicated_user_adding_response.json() == {
            "code": 409,
            "message": samples.USER_UNIQUE_EMAIL_CONSTRAINT_ERR,
        }
        email_mock.assert_called_once()

    def test_get_users(self, client, db_session, system_user_auth_header):
        """Test get users list."""
        response = client.get(self.USERS_API_ENDPOINT, headers=system_user_auth_header)
        response_json = response.json()
        first_user = sorted(response_json["items"], key=lambda d: d["id"])[0]
        user_crud = UserCRUD(db_session)

        assert response.status_code == 200
        assert response_json["skip"] == 0
        assert response_json["limit"] == 10

        assert len(response_json["items"]) == user_crud.total()
        assert first_user["email"] == settings.system_user_email
        assert first_user["first_name"] == settings.system_user_first_name
        assert first_user["last_name"] == settings.system_user_last_name
        assert first_user["role"] is None

    def test_get_users_with_search(self, client, system_user_auth_header, company_member_user):
        """Test get users with search value."""
        response = client.get(
            self.USERS_API_ENDPOINT, params={"search": samples.TEST_USER_EMAIL}, headers=system_user_auth_header
        )
        response_json = response.json()
        user = response_json["items"][0]

        assert response.status_code == 200
        assert response_json["skip"] == 0
        assert response_json["limit"] == 10

        assert len(response_json["items"]) == 1
        assert user["email"] == samples.BASE_USER_OBJECT["email"]
        assert user["first_name"] == samples.BASE_USER_OBJECT["first_name"]
        assert user["last_name"] == samples.BASE_USER_OBJECT["last_name"]

    def test_resend_invitation_user_not_fount(self, client, system_user_auth_header):
        request_url = f"{self.USERS_API_ENDPOINT}/1234567890/{self.RESEND_INVITATION_ENDPOINT_NAME}"
        response = client.post(request_url, headers=system_user_auth_header)

        assert response.status_code == 404

    @pytest.mark.parametrize("user_obj_raw", [True], indirect=True)
    def test_resend_invitation_user_already_registered(self, client, system_user_auth_header, user_obj_raw):
        request_url = f"{self.USERS_API_ENDPOINT}/{user_obj_raw.id}/{self.RESEND_INVITATION_ENDPOINT_NAME}"
        response = client.post(request_url, headers=system_user_auth_header)

        # assert
        assert response.status_code == 400
        assert response.json() == {"code": 400, "message": samples.RESEND_INVITATION_USER_REGISTERED_ERR}

    def test_resend_invitation_email_sending_error(
        self, client, system_user_auth_header, user_obj_raw, response_400, mocker
    ):
        email_mock = mocker.patch("app.helpers.email.requests.post", return_value=response_400)

        # act
        request_url = f"{self.USERS_API_ENDPOINT}/{user_obj_raw.id}/{self.RESEND_INVITATION_ENDPOINT_NAME}"
        response = client.post(request_url, headers=system_user_auth_header)

        # assert
        assert response.status_code == 400
        assert response.json() == {"code": 400, "message": samples.RESEND_INVITATION_EMAIL_SENDING_ERR}
        assert email_mock.call_args.kwargs["data"]["to"] == [samples.TEST_USER_EMAIL]
        assert email_mock.call_args.kwargs["data"]["template"] == "Invitation email"
        assert email_mock.call_args.kwargs["data"]["subject"] == "Reminder: You're invited"

    def test_resend_invitation_success(self, client, system_user_auth_header, user_obj_raw, response_200, mocker):
        # arrange
        email_mock = mocker.patch("app.helpers.email.requests.post", return_value=response_200)

        # act
        request_url = f"{self.USERS_API_ENDPOINT}/{user_obj_raw.id}/{self.RESEND_INVITATION_ENDPOINT_NAME}"
        response = client.post(request_url, headers=system_user_auth_header)

        # assert
        assert response.status_code == 200
        assert response.json() == {"code": 200, "message": samples.RESEND_INVITATION_SUCCESS_MSG}
        assert email_mock.call_args.kwargs["data"]["to"] == [samples.TEST_USER_EMAIL]
        assert email_mock.call_args.kwargs["data"]["template"] == "Invitation email"
        assert email_mock.call_args.kwargs["data"]["subject"] == "Reminder: You're invited"

    def test_get_user_by_id_404(self, client, system_user_auth_header):
        response = client.get(f"{self.USERS_API_ENDPOINT}/111111", headers=system_user_auth_header)
        assert response.status_code == 404

    def test_get_user_by_id(self, client, system_user_auth_header, company_member_user):
        response = client.get(f"{self.USERS_API_ENDPOINT}/{company_member_user.id}", headers=system_user_auth_header)
        response_json = response.json()

        assert response.status_code == 200
        assert response_json["email"] == samples.TEST_USER_EMAIL

    def test_edit_user(self, client, db_session, system_user_auth_header, mocker, company_member_user):
        mocker.patch("app.routers.settings.users.EmailUtility")
        target_user_id, target_user_email, new_email, new_phone = (
            company_member_user.id,
            company_member_user.email,
            "user@spam.com",
            "0123456789",
        )

        put_response = client.put(
            f"{self.USERS_API_ENDPOINT}/{target_user_id}",
            json={
                "email": new_email,
                "phone": new_phone,
                "parent_company_id": company_member_user.parent_company_id,
                "sites_ids": [site.id for site in company_member_user.sites],
                "role_id": company_member_user.role.id,
            },
            headers=system_user_auth_header,
        )

        assert put_response.status_code == 202

        # check the email was indeed changed in the system:
        get_response = client.get(
            f"{self.USERS_API_ENDPOINT}/{target_user_id}",
            headers=system_user_auth_header,
        )
        assert get_response.status_code == 200
        assert get_response.json()["email"] == new_email

    def test_edit_user_but_404(self, client, db_session, system_user_auth_header):
        payload = {
            "parent_company_id": 555,
            "sites_ids": [999, 888],
            "role_id": 444,
            "email": "user@spam.com",
            "phone": "0123456789",
        }

        put_response = client.put(
            f"{self.USERS_API_ENDPOINT}/9999999",
            json=payload,
            headers=system_user_auth_header,
        )

        assert put_response.status_code == 404
        assert put_response.json()["message"] == "Not Found"

    @pytest.mark.parametrize(
        "payload_part, expected_message",
        (
            ({"parent_company_id": 12051}, "Parent company not found"),
            ({"role_id": 12052}, "Role not found"),
            ({"sites_ids": [12053]}, "Some of requested sites not found: 12053"),
            ({"sites_ids": [12053, 12054]}, "Some of requested sites not found: 12053, 12054"),
        ),
    )
    def test_edit_user_w_target_non_existance(
        self,
        client,
        system_user_auth_header,
        mocker,
        company_member_user,
        payload_part,
        expected_message,
    ):
        mocker.patch("app.routers.settings.users.EmailUtility")
        payload = {
            "email": company_member_user.email,
            "parent_company_id": company_member_user.parent_company_id,
            "sites_ids": [site.id for site in company_member_user.sites],
            "role_id": company_member_user.role.id,
            "phone": company_member_user.phone,
        }
        payload.update(payload_part)

        put_response = client.put(
            f"{self.USERS_API_ENDPOINT}/{company_member_user.id}", json=payload, headers=system_user_auth_header
        )

        assert put_response.status_code == 400
        assert put_response.json()["message"] == expected_message

    def test_edit_user_w_taken_email(
        self, client, db_session, system_user_auth_header, mocker, user_payload, company_member_user, response_400
    ):
        email_mock = mocker.patch("app.helpers.email.requests.post", return_value=response_400)
        taken_email = "already_existing@email.com"
        new_user_payload = deepcopy(user_payload)
        new_user_payload["email"] = taken_email
        client.post(self.USERS_API_ENDPOINT, json=new_user_payload, headers=system_user_auth_header)
        user = UserCRUD(db_session).get_by_email(taken_email)

        payload = {
            "email": company_member_user.email,  # another existing user's email
            "parent_company_id": company_member_user.parent_company_id,
            "sites_ids": [site.id for site in company_member_user.sites],
            "role_id": company_member_user.role.id,
            "phone": company_member_user.phone,
        }

        mocker.patch("app.routers.settings.users.EmailUtility")
        put_response = client.put(f"{self.USERS_API_ENDPOINT}/{user.id}", json=payload, headers=system_user_auth_header)

        assert put_response.status_code == 400
        assert put_response.json()["message"] == "Another user with such email already exists"

    def test_edit_user_company(self, client, db_session, system_user_auth_header, company_member_user, company_id):
        target_user_id = company_member_user.id

        put_response = client.put(
            f"{self.USERS_API_ENDPOINT}/{target_user_id}",
            json={
                "parent_company_id": company_id,
                "email": company_member_user.email,
                "sites_ids": [site.id for site in company_member_user.sites],
                "role_id": company_member_user.role.id,
                "phone": company_member_user.phone,
            },
            headers=system_user_auth_header,
        )

        assert put_response.status_code == 202

        # check the parent company was indeed changed in the system:
        get_response = client.get(
            f"{self.USERS_API_ENDPOINT}/{target_user_id}",
            headers=system_user_auth_header,
        )
        assert get_response.status_code == 200
        assert get_response.json()["parent_company"]["id"] == company_id

    @pytest.mark.parametrize(
        "new_role_name, expected_status_code, expected_message, expected_role_name",
        (
            (
                "Asset Manager",
                202,
                f"User {samples.TEST_USER_NAME} {samples.TEST_USER_LAST_NAME} was updated",
                "Asset Manager",
            ),
            # should keep old "test" role if the new role is not allowed for the company:
            ("Field Technician", 400, "This role is not allowed for chosen company type", "test"),
        ),
    )
    def test_edit_user_role(
        self,
        client,
        db_session,
        system_user_auth_header,
        company_member_user,
        new_role_name,
        expected_status_code,
        expected_message,
        expected_role_name,
    ):
        # fetch target role id that is dynamic during tests
        get_response = client.get(
            self.ROLES_API_ENDPOINT,
            headers=system_user_auth_header,
            params={"limit": 1000},
        )
        assert get_response.status_code == 200

        roles = get_response.json()["items"]
        new_role_id = None
        for role in roles:
            if role["name"] == new_role_name:
                new_role_id = role["id"]
                break
        assert new_role_id

        # perform user role change
        target_user_id = company_member_user.id
        put_response = client.put(
            f"{self.USERS_API_ENDPOINT}/{target_user_id}",
            json={
                "role_id": new_role_id,
                "email": company_member_user.email,
                "parent_company_id": company_member_user.parent_company_id,
                "sites_ids": [site.id for site in company_member_user.sites],
                "phone": company_member_user.phone,
            },
            headers=system_user_auth_header,
        )

        assert put_response.status_code == expected_status_code
        assert put_response.json()["message"] == expected_message

        # check user was changed
        get_response = client.get(
            f"{self.USERS_API_ENDPOINT}/{target_user_id}",
            headers=system_user_auth_header,
        )
        assert get_response.status_code == 200
        get_response_json = get_response.json()
        assert get_response_json["role"]["name"] == expected_role_name

    def test_edit_user_sites(self, client, db_session, system_user_auth_header, company_member_user):
        user_crud, sites_crud, project_crud = UserCRUD(db_session), SiteCRUD(db_session), UserProjectCRUD(db_session)
        payload = deepcopy(samples.TEST_SITE_BODY)
        user_id, parent_company_id = company_member_user.id, company_member_user.parent_company_id
        payload["company_id"] = parent_company_id

        existing_sites_ids = [site.id for site in company_member_user.sites]
        # create sites that must be already present in the system per user before test
        payload["name"] = "first site"
        test_site1 = sites_crud.create_item(payload)
        test_site1_id = test_site1.id
        project_crud.create_item({"company_id": parent_company_id, "user_id": user_id, "site_id": test_site1_id})

        payload["name"] = "second site"
        test_site2 = sites_crud.create_item(payload)
        test_site2_id = test_site2.id
        project_crud.create_item({"company_id": parent_company_id, "user_id": user_id, "site_id": test_site2_id})

        # assert setup is fine, use set for comparison to handle a case if order is different
        assert set([site.id for site in company_member_user.sites]) == set(
            existing_sites_ids + [test_site1_id, test_site2_id]
        )

        # create 3rd site to attach to the user during the update operation
        payload["name"] = "third site"
        test_site3 = sites_crud.create_item(payload)
        test_site3_id = test_site3.id

        # finally, test
        put_response = client.put(
            f"{self.USERS_API_ENDPOINT}/{user_id}",
            json={
                "sites_ids": [test_site1_id, test_site3_id],
                "email": company_member_user.email,
                "parent_company_id": company_member_user.parent_company_id,
                "role_id": company_member_user.role.id,
                "phone": company_member_user.phone,
            },
            headers=system_user_auth_header,
        )

        assert put_response.status_code == 202
        # check that first site remained unchanged, second was removed along other existing, third was added
        assert {site.id for site in company_member_user.sites} == {test_site1_id, test_site3_id}

    def test_edit_user_without_phone(self, client, db_session, system_user_auth_header, company_member_user, company_id):
        target_user_id = company_member_user.id

        response = client.put(
            f"{self.USERS_API_ENDPOINT}/{target_user_id}",
            json={
                "parent_company_id": company_id,
                "email": company_member_user.email,
                "sites_ids": [site.id for site in company_member_user.sites],
                "role_id": company_member_user.role.id,
            },
            headers=system_user_auth_header,
        )
        assert response.status_code == 422
        assert response.json()["message"] == "Validation error: body.phone - Field required"

    def test_edit_user_invalid_phone_format(
        self, client, db_session, system_user_auth_header, company_member_user, company_id
    ):
        target_user_id = company_member_user.id

        response = client.put(
            f"{self.USERS_API_ENDPOINT}/{target_user_id}",
            json={
                "parent_company_id": company_id,
                "email": company_member_user.email,
                "sites_ids": [site.id for site in company_member_user.sites],
                "role_id": company_member_user.role.id,
                "phone": "143134",
            },
            headers=system_user_auth_header,
        )
        assert response.status_code == 422
        assert response.json()["message"] == "Validation error: body.phone - String should have at least 10 characters"

    def test_edit_user_with_too_long_email(
        self, client, db_session, system_user_auth_header, company_member_user, company_id
    ):
        target_user_id = company_member_user.id

        response = client.put(
            f"{self.USERS_API_ENDPOINT}/{target_user_id}",
            json={
                "parent_company_id": company_id,
                "email": samples.LONGER_THAN_100_CHARS_EMAIL,
                "sites_ids": [site.id for site in company_member_user.sites],
                "role_id": company_member_user.role.id,
                "phone": company_member_user.phone,
            },
            headers=system_user_auth_header,
        )
        assert response.status_code == 422
        assert response.json()["message"] == samples.EMAIL_LENGTH_ERROR


class TestCompanyAdminUser:
    """Tests for users routes that have company access."""

    USERS_API_ENDPOINT = "/api/users"

    def test_create_user_by_company_admin_success(
        self, client, user_payload, company_member_user, company_admin_full_access_header, response_400, mocker
    ):
        email_mock = mocker.patch("app.helpers.email.requests.post", return_value=response_400)
        payload = deepcopy(user_payload)
        payload["email"] = "by_company_admin@email.com"
        response = client.post(self.USERS_API_ENDPOINT, json=payload, headers=company_admin_full_access_header)

        assert response.json() == {"code": 201, "message": samples.CREATE_USER_PARTIAL_SUCCESS_MSG}

    def test_create_user_no_company_admin_rights(self, client, user_payload, non_system_user_auth_header):
        response = client.post(self.USERS_API_ENDPOINT, json=user_payload, headers=non_system_user_auth_header)

        assert response.json() == {"code": 403, "message": "Forbidden"}

    def test_create_user_by_company_admin_of_other_company(
        self, client, user_payload, company_member_user, company_id, company_admin_full_access_header
    ):
        payload = deepcopy(user_payload)
        payload["parent_company_id"] = company_id + 1
        response = client.post(self.USERS_API_ENDPOINT, json=payload, headers=company_admin_full_access_header)

        assert response.json() == {"code": 403, "message": "Forbidden"}

    def test_create_user_by_company_admin_view_access(
        self, client, user_payload, company_member_user, company_id, company_admin_read_access_header
    ):
        payload = deepcopy(user_payload)
        response = client.post(self.USERS_API_ENDPOINT, json=payload, headers=company_admin_read_access_header)

        assert response.json() == {"code": 403, "message": "Forbidden"}

    def test_edit_user_by_company_admin(self, client, mocker, company_member_user, company_admin_full_access_header):
        mocker.patch("app.routers.settings.users.EmailUtility")
        target_user_id, target_user_email, new_email, new_phone = (
            company_member_user.id,
            company_member_user.email,
            "user@spam.com",
            "0123456789",
        )

        put_response = client.put(
            f"{self.USERS_API_ENDPOINT}/{target_user_id}",
            json={
                "email": new_email,
                "phone": new_phone,
                "parent_company_id": company_member_user.parent_company_id,
                "sites_ids": [site.id for site in company_member_user.sites],
                "role_id": company_member_user.role.id,
            },
            headers=company_admin_full_access_header,
        )

        assert put_response.status_code == 202

    def test_edit_user_by_company_admin_view_rights(self, client, company_member_user, company_admin_read_access_header):
        target_user_id, target_user_email, new_email, new_phone = (
            company_member_user.id,
            company_member_user.email,
            "user@spam.com",
            "0123456789",
        )

        put_response = client.put(
            f"{self.USERS_API_ENDPOINT}/{target_user_id}",
            json={
                "email": new_email,
                "phone": new_phone,
                "parent_company_id": company_member_user.parent_company_id,
                "sites_ids": [site.id for site in company_member_user.sites],
                "role_id": company_member_user.role.id,
            },
            headers=company_admin_read_access_header,
        )

        assert put_response.status_code == 403

    def test_edit_user_by_company_admin_other_company(
        self, client, company_member_user, company_admin_full_access_header
    ):
        target_user_id, target_user_email, new_email, new_phone = (
            company_member_user.id,
            company_member_user.email,
            "user@spam.com",
            "0123456789",
        )

        put_response = client.put(
            f"{self.USERS_API_ENDPOINT}/{target_user_id}",
            json={
                "email": new_email,
                "phone": new_phone,
                "parent_company_id": company_member_user.parent_company_id + 1,
                "sites_ids": [site.id for site in company_member_user.sites],
                "role_id": company_member_user.role.id,
            },
            headers=company_admin_full_access_header,
        )

        assert put_response.status_code == 403
