from copy import deepcopy

import pytest

from tests.unit import samples


class TestMyCompany:

    MY_COMPANY_API_ENDPOINT = "/api/my-company"

    def test_get_my_company_sites_system_user(self, client, site_id, system_user_auth_header):
        """Test get all sites for settings page with system user."""

        response = client.get(f"{self.MY_COMPANY_API_ENDPOINT}/sites", headers=system_user_auth_header)

        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"

    def test_get_my_company_sites_non_system_user_403(self, client, site_id, non_system_user_auth_header):
        """Test get all sites for settings page for non system user."""

        response = client.get(f"{self.MY_COMPANY_API_ENDPOINT}/sites", headers=non_system_user_auth_header)

        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"

    def test_get_my_company_sites_allow_edit(self, client, company_admin_full_access_header):
        """Test get all sites for settings page for user with edit permissions."""

        response = client.get(f"{self.MY_COMPANY_API_ENDPOINT}/sites", headers=company_admin_full_access_header)
        assert response.status_code == 200

    def test_get_my_company_sites_allow_view(self, client, company_admin_read_access_header):
        """Test get all sites for settings page for user with view permissions."""

        response = client.get(f"{self.MY_COMPANY_API_ENDPOINT}/sites", headers=company_admin_read_access_header)
        assert response.status_code == 200

    def test_get_my_company_sites_search_name(self, client, company_admin_read_access_header):
        """Test get all sites for settings page for user and search."""

        response = client.get(
            f"{self.MY_COMPANY_API_ENDPOINT}/sites",
            params={"search": samples.TEST_SITE_NAME},
            headers=company_admin_read_access_header,
        )
        response_json_site = response.json()["items"][0]

        assert response.status_code == 200
        assert response_json_site["name"] == samples.TEST_SITE_NAME
        assert response_json_site["address"] == samples.TEST_SITE_ADDRESS

    @pytest.mark.parametrize("sites", [2], indirect=True)
    def test_get_my_company_allow_view(self, client, company_member_user, company_admin_read_access_header, sites):
        """Test my-company for company admin user with view permissions, check user can see all sites
        independently of the project access settings"""
        response = client.get(self.MY_COMPANY_API_ENDPOINT, headers=company_admin_read_access_header)
        response_json = response.json()

        assert response.status_code == 200
        assert response_json["name"] == samples.TEST_COMPANY_NAME
        assert response_json["email"] == samples.TEST_COMPANY_EMAIL
        assert response_json["address"] == samples.TEST_COMPANY_ADDRESS
        assert response_json["phone"] == samples.TEST_COMPANY_PHONE
        assert response_json["total_sites"] == 2
        assert len(company_member_user.sites) == 1

    @pytest.mark.parametrize("sites", [4], indirect=True)
    def test_get_my_company_allow_edit(self, client, company_member_user, company_admin_full_access_header, sites):
        """Test my-company for company admin user with edit permissions, check user can see all sites
        independently of the project access settings"""
        response = client.get(self.MY_COMPANY_API_ENDPOINT, headers=company_admin_full_access_header)
        response_json = response.json()

        assert response.status_code == 200
        assert response_json["name"] == samples.TEST_COMPANY_NAME
        assert response_json["email"] == samples.TEST_COMPANY_EMAIL
        assert response_json["address"] == samples.TEST_COMPANY_ADDRESS
        assert response_json["phone"] == samples.TEST_COMPANY_PHONE
        assert response_json["total_sites"] == 4
        assert len(company_member_user.sites) == 1

    def test_get_my_company_regular_user_403(self, client, non_system_user_auth_header):
        """Test that regular user with no admin rights has no access to my company."""
        response = client.get(self.MY_COMPANY_API_ENDPOINT, headers=non_system_user_auth_header)
        assert response.status_code == 403

    def test_get_my_company_system_user_403(self, client, system_user_auth_header):
        """Test that system user has no access to my company."""
        response = client.get(self.MY_COMPANY_API_ENDPOINT, headers=system_user_auth_header)
        assert response.status_code == 404

    def test_get_my_company_site_by_id(
        self,
        client,
        site_id,
        company_id,
        company_admin_read_access_header,
    ):
        """Test that site fetch by id returns appropriate values as expected."""
        # build full site body considering dynamic fields
        expected_response = deepcopy(samples.TEST_SITE_BODY_JSON)
        expected_response["id"] = site_id
        expected_response.update(samples.TEST_SITE_DAS_CONNECTION_FIELDS)
        company = deepcopy(samples.TEST_COMPANY_PAYLOAD_JSON)
        company["id"] = company_id
        expected_response["company"] = company

        response = client.get(
            f"{self.MY_COMPANY_API_ENDPOINT}/sites/{site_id}", headers=company_admin_read_access_header
        )
        response_json = response.json()

        assert response.status_code == 200
        assert response_json == expected_response

    def test_get_my_company_site_by_id_403(
        self,
        client,
        non_system_user_auth_header,
        site_id,
    ):
        """Test that site fetch by id returns 403 if no access."""
        response = client.get(f"{self.MY_COMPANY_API_ENDPOINT}/sites/{site_id}", headers=non_system_user_auth_header)

        assert response.status_code == 403

    def test_get_my_company_site_by_id_site_not_belongs_to_user_403(
        self,
        client,
        site_id,
        company_admin_read_access_header,
    ):
        """Test that site fetch by id returns 403 if site is not included in user parent company sites."""
        response = client.get(
            f"{self.MY_COMPANY_API_ENDPOINT}/sites/{site_id+1}", headers=company_admin_read_access_header
        )

        assert response.status_code == 403

    def test_get_my_company_users(self, client, company_member_user, company_admin_read_access_header):
        """Test get users list for my company."""
        response = client.get(f"{self.MY_COMPANY_API_ENDPOINT}/users", headers=company_admin_read_access_header)
        response_json = response.json()
        first_user = response_json["items"][0]

        assert response.status_code == 200
        assert response_json["skip"] == 0
        assert response_json["limit"] == 10

        assert first_user["email"] == company_member_user.email
        assert first_user["first_name"] == company_member_user.first_name
        assert first_user["last_name"] == company_member_user.last_name
        assert first_user["role"]["name"] == company_member_user.role.name
        assert first_user["phone"] == company_member_user.phone
        assert first_user["is_registered"] == company_member_user.is_registered
        assert first_user["parent_company_id"] == company_member_user.parent_company_id

    def test_get_my_company_users_403(self, client, non_system_user_auth_header):
        """Test get users list for my company 403."""
        response = client.get(f"{self.MY_COMPANY_API_ENDPOINT}/users", headers=non_system_user_auth_header)
        assert response.status_code == 403
