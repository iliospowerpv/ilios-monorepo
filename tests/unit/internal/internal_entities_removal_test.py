from copy import deepcopy

import pytest

from app.crud.company import CompanyCRUD
from app.crud.device import DeviceCRUD
from app.crud.role import RoleCRUD
from app.crud.site import SiteCRUD
from app.crud.user import UserCRUD
from app.settings import settings
from tests.unit import samples


class TestInternalRemoval:
    USERS_API_ENDPOINT = "/api/users"
    COMPANIES_API_ENDPOINT = "/api/companies"
    CONTRACTORS_API_ENDPOINT = "/api/contractors"
    SITES_API_ENDPOINT = "/api/sites"
    # for the removal endpoint, site id is not validates, we can pass whatever we want
    DEVICE_API_ENDPOINT = "/api/sites/1/devices"
    ROLES_API_ENDPOINT = "/api/roles"

    def test_delete_company(self, client, system_user_auth_header, db_session):
        companies_crud = CompanyCRUD(db_session)
        company_body = deepcopy(samples.TEST_COMPANY_PAYLOAD)
        company_body["name"] = "NewCo"
        test_company = companies_crud.create_item(company_body)

        response = client.delete(
            f"{self.CONTRACTORS_API_ENDPOINT}/{test_company.id}/internal", params={"api_key": settings.api_key}
        )
        assert response.status_code == 204

        get_response = client.get(f"{self.COMPANIES_API_ENDPOINT}/{test_company.id}", headers=system_user_auth_header)
        assert get_response.status_code == 404

    @pytest.mark.parametrize(
        "api_key, expected_status_code",
        (
            (settings.api_key, 404),
            ("WRONG_API_KEY", 403),
        ),
    )
    def test_delete_company_negative(self, client, api_key, expected_status_code):
        """Test negative cases are caught and handled appropriately"""
        response = client.delete(f"{self.CONTRACTORS_API_ENDPOINT}/9999/internal", params={"api_key": api_key})
        assert response.status_code == expected_status_code

    def test_delete_company_of_user(self, client, db_session, system_user_auth_header, user_payload, mocker):
        """Test that with user's company removal the SET NULL rule sets company id as None in the user obj"""
        # create parent company that should be attached to the user and then removed
        companies_crud = CompanyCRUD(db_session)
        company_body = deepcopy(samples.TEST_COMPANY_PAYLOAD)
        company_body["name"] = "NewCo"
        test_company = companies_crud.create_item(company_body)

        # create user
        user_email = "user_with_company@email.com"
        new_user_payload = deepcopy(user_payload)
        new_user_payload.update({"email": user_email, "parent_company_id": test_company.id})

        mocker.patch("app.routers.settings.users.EmailUtility")
        post_response = client.post(self.USERS_API_ENDPOINT, json=new_user_payload, headers=system_user_auth_header)
        assert post_response.status_code == 201

        user = UserCRUD(db_session).get_by_email(user_email)

        # delete company
        response = client.delete(
            f"{self.CONTRACTORS_API_ENDPOINT}/{test_company.id}/internal",
            params={"api_key": settings.api_key},
        )
        assert response.status_code == 204

        # check user is fine and parent_company_id is None
        user_get_response = client.get(f"{self.USERS_API_ENDPOINT}/{user.id}/", headers=system_user_auth_header)
        assert user_get_response.status_code == 200
        response_json = user_get_response.json()
        assert response_json["parent_company"] is None

    def test_delete_company_of_site(self, client, db_session, system_user_auth_header):
        """Test that with company deletion its site is also gone by CASCADE removal"""
        # create parent company that should be attached to the site and then removed
        company_body = deepcopy(samples.TEST_COMPANY_PAYLOAD)
        company_body["name"] = "NewCo"
        test_company_id = CompanyCRUD(db_session).create_item(company_body).id

        payload = deepcopy(samples.TEST_SITE_BODY)
        payload["company_id"] = test_company_id
        test_site_id = SiteCRUD(db_session).create_item(payload).id

        # check setup is fine
        user_get_response = client.get(f"{self.SITES_API_ENDPOINT}/{test_site_id}/", headers=system_user_auth_header)
        assert user_get_response.status_code == 200
        response_json = user_get_response.json()
        assert response_json["company"]["id"] == test_company_id

        # delete company
        response = client.delete(
            f"{self.CONTRACTORS_API_ENDPOINT}/{test_company_id}/internal",
            params={"api_key": settings.api_key},
        )
        assert response.status_code == 204

        # check site is gone with its company
        user_get_response = client.get(f"{self.SITES_API_ENDPOINT}/{test_site_id}/", headers=system_user_auth_header)
        assert user_get_response.status_code == 404

    @pytest.mark.parametrize(
        "target_user_id_getter, api_key, expected_status_code",
        (
            (lambda user: user.id, settings.api_key, 204),
            (lambda user: user.id + 100, settings.api_key, 404),
            (lambda user: user.id, "WRONG_API_KEY", 403),
        ),
    )
    def test_delete_user(self, client, company_member_user, target_user_id_getter, api_key, expected_status_code):
        user_id = target_user_id_getter(company_member_user)
        response = client.delete(f"{self.USERS_API_ENDPOINT}/{user_id}/internal", params={"api_key": api_key})

        assert response.status_code == expected_status_code

    def test_delete_site(self, client, db_session, company_id, system_user_auth_header):
        payload = samples.TEST_SITE_BODY
        payload["company_id"] = company_id
        sites_crud = SiteCRUD(db_session)
        target_site_id = sites_crud.create_item(payload).id

        response = client.delete(
            f"{self.SITES_API_ENDPOINT}/{target_site_id}/internal", params={"api_key": settings.api_key}
        )

        assert response.status_code == 204

        get_response = client.get(f"{self.SITES_API_ENDPOINT}/{target_site_id}", headers=system_user_auth_header)
        assert get_response.status_code == 404

    @pytest.mark.parametrize(
        "api_key, expected_status_code",
        (
            (settings.api_key, 404),
            ("WRONG_API_KEY", 403),
        ),
    )
    def test_delete_site_negative(self, client, api_key, expected_status_code):
        """Test negative cases are caught and handled appropriately"""
        response = client.delete(f"{self.SITES_API_ENDPOINT}/99999/internal", params={"api_key": api_key})

        assert response.status_code == expected_status_code

    def test_delete_device(self, client, db_session, site_id):
        payload = samples.TEST_INVERTER_DEVICE_BODY
        payload["site_id"] = site_id
        device_crud = DeviceCRUD(db_session)
        target_device_id = device_crud.create_item(payload).id

        response = client.delete(
            f"{self.DEVICE_API_ENDPOINT}/{target_device_id}/internal", params={"api_key": settings.api_key}
        )

        assert response.status_code == 204

        device = device_crud.get_by_id(target_device_id)
        assert device is None

    @pytest.mark.parametrize(
        "api_key, expected_status_code",
        (
            (settings.api_key, 404),
            ("WRONG_API_KEY", 403),
        ),
    )
    def test_delete_device_negative(self, client, db_session, api_key, expected_status_code):
        """Test negative cases are caught and handled appropriately"""
        response = client.delete(f"{self.DEVICE_API_ENDPOINT}/99999/internal", params={"api_key": api_key})

        assert response.status_code == expected_status_code

    def test_delete_role(self, client, db_session):
        role_crud = RoleCRUD(db_session)
        target_role_id = role_crud.create_item(samples.VALID_ROLE_BODY).id

        response = client.delete(
            f"{self.ROLES_API_ENDPOINT}/{target_role_id}/internal", params={"api_key": settings.api_key}
        )
        assert response.status_code == 204

        role = role_crud.get_by_id(target_role_id)
        assert role is None

    @pytest.mark.parametrize(
        "api_key, expected_status_code",
        (
            (settings.api_key, 404),
            ("WRONG_API_KEY", 403),
        ),
    )
    def test_delete_role_negative(self, client, api_key, expected_status_code):
        """Test negative cases are caught and handled appropriately"""
        response = client.delete(f"{self.ROLES_API_ENDPOINT}/99999/internal", params={"api_key": api_key})
        assert response.status_code == expected_status_code
