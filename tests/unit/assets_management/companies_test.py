"""Tests for companies routes."""

import pytest

import tests.unit.samples as samples
from app.crud.site import SiteCRUD
from app.crud.site_additional_fields_list import SiteAdditionalFieldListCRUD
from app.models.site import SiteStatuses
from tests.utils import remove_dynamic_fields


class TestCompanies:
    """Tests for companies routes."""

    COMPANIES_API_ENDPOINT = "/api/companies"
    COMPANIES_SITES_API_ENDPOINT = "/api/companies/sites"

    def test_get_without_existing_companies(self, client, company_member_user_auth_header, mocker):
        """Test that without providing project access GET /companies returns empty list of items."""
        mocker.patch("app.models.user.User.get_limited_companies_ids", return_value=[])
        response = client.get(
            self.COMPANIES_API_ENDPOINT, params={"skip": 0, "limit": 2}, headers=company_member_user_auth_header
        )
        assert response.status_code == 200
        assert response.json()["items"] == []

    @pytest.mark.parametrize("setup_companies", [3], indirect=True)
    def test_get_companies_with_total_sites_info_system_user(self, client, system_user_auth_header, setup_companies):
        """Test that companies GET endpoint works as expected: provides correct status, pagination,
        maintains default ordering by id field and typical body structure.
        """
        response = client.get(
            self.COMPANIES_API_ENDPOINT,
            params={"skip": 0, "limit": 2, "order_by": "name"},
            headers=system_user_auth_header,
        )
        response_json = response.json()

        # remove ID since it's dynamic field
        response_items = response_json["items"]
        remove_dynamic_fields(response_items)

        assert response.status_code == 200
        assert response_json["skip"] == 0
        assert response_json["limit"] == 2

        assert response_items == [
            {"name": samples.VALID_COMPANY2_BODY["name"], "total_capacity": 0.0, "total_sites": 0},
            {"name": samples.TEST_COMPANY_NAME, "total_sites": 0.0, "total_capacity": 0},
        ]

    @pytest.mark.parametrize("setup_companies", [3], indirect=True)
    def test_get_companies_with_total_sites_search_by_name(self, client, system_user_auth_header, setup_companies):
        """Test that companies GET endpoint works as expected: returns only company searched by name."""
        response = client.get(
            self.COMPANIES_API_ENDPOINT,
            params={"search": "Apple"},
            headers=system_user_auth_header,
        )
        response_json = response.json()
        response_items = [item for item in response_json["items"]]

        assert response.status_code == 200
        assert len(response_items) == 1
        assert response_items[0]["name"] == samples.VALID_COMPANY2_BODY["name"]

    def test_get_companies_with_total_sites_info(
        self, client, site_id, company_member_user_auth_header, sites_placed_in_service
    ):
        """Test that GET /companies returns info about company's total sites and capacity."""
        response = client.get(
            self.COMPANIES_API_ENDPOINT,
            headers=company_member_user_auth_header,
        )
        # remove ID since it's dynamic field
        response_items = response.json()["items"]
        remove_dynamic_fields(response_items)

        assert response.status_code == 200
        assert {"name": samples.TEST_COMPANY_NAME, "total_sites": 1, "total_capacity": 100} in response_items

    def test_get_companies_with_total_capacity_rounded(
        self, client, company_id, site, system_user_auth_header, db_session, sites_placed_in_service
    ):
        """Use System user because new site is created, and it has access to all sites around company."""

        # set up a site with capacity size in long float
        site.system_size_ac = 7.34576501423413
        db_session.commit()

        response = client.get(
            self.COMPANIES_API_ENDPOINT,
            headers=system_user_auth_header,
        )
        target_company = [item for item in response.json()["items"] if item["id"] == company_id][0]

        assert response.status_code == 200
        # ensure site float capacity is rounded and limited to 2 digits scale
        assert target_company["total_capacity"] == 7.35

    @pytest.mark.parametrize("setup_companies", [3], indirect=True)
    def test_get_companies_ordered_by_name(self, client, system_user_auth_header, setup_companies, company):
        """Test that companies GET with order_by field 'name' orders output companies by their names.

        Use system user to check ordering since it has access to all companies list.
        """
        response = client.get(self.COMPANIES_API_ENDPOINT, params={"order_by": "name"}, headers=system_user_auth_header)
        response_json = response.json()
        items = response_json["items"]

        assert items[0]["name"] == "Apple Inc."

    def test_get_companies_w_invalid_order_by(self, client, company_member_user_auth_header):
        """Test that other normal company entity fields that are not in company page schema are invalidated when
        provided as order_by param.
        """
        response = client.get(
            self.COMPANIES_API_ENDPOINT, params={"order_by": "email"}, headers=company_member_user_auth_header
        )
        assert response.status_code == 422

    def test_get_companies_w_missing_order_by(self, client, non_system_user_auth_header):
        """Test that companies GET query param validation disallows order_direction without order_by."""
        response = client.get(
            self.COMPANIES_API_ENDPOINT, params={"order_direction": "desc"}, headers=non_system_user_auth_header
        )
        assert response.status_code == 400
        assert response.json()["message"] == (
            "It is required to have order_by column specified first before applying ordering direction"
        )

    def test_get_companies_w_wrong_order_direction(self, client, company_member_user_auth_header):
        """Test that companies GET query param validation catches invalid values of order_direction."""
        response = client.get(
            self.COMPANIES_API_ENDPOINT,
            params={"order_by": "name", "order_direction": "ascendente"},
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 422
        assert response.json()["message"] == "Validation error: query.order_direction - Input should be 'asc' or 'desc'"

    @pytest.mark.parametrize("setup_companies", [3], indirect=True)
    def test_get_companies_ordered_desc(self, client, system_user_auth_header, setup_companies, company):
        """Test that companies GET returns output ordered descending by id, if such params are given.

        Use system user to check ordering since it has access to all companies list.
        """
        response = client.get(
            self.COMPANIES_API_ENDPOINT,
            params={"skip": 0, "limit": 3, "order_by": "name", "order_direction": "desc"},
            headers=system_user_auth_header,
        )
        response_json = response.json()

        # keep only name to validate companies are sorted desc and exclude dependencies on creation order
        response_items_names = [item["name"] for item in response_json["items"]]

        assert response.status_code == 200
        assert response_items_names == ["Nvidia Corporation", "Green Lantern", "Apple Inc."]

    @pytest.mark.parametrize("sites", [3], indirect=True)
    def test_get_company_by_id_system_user(
        self, client, system_user_auth_header, company_id, sites, db_session, sites_placed_in_service
    ):
        """Test that company fetch by id returns appropriate values as expected, system user is allowed to see
        all company sites"""
        # crete additional sites in different statuses
        payload = samples.TEST_SITE_BODY
        payload["company_id"] = company_id
        sites_crud = SiteCRUD(db_session)
        sites_extra_crud = SiteAdditionalFieldListCRUD(db_session)
        created_sites = []
        for status in SiteStatuses:
            test_site = sites_crud.create_item(payload)
            created_sites.append(test_site)
            sites_extra_crud.create_item({"site_id": test_site.id, "status": status})

        response = client.get(f"{self.COMPANIES_API_ENDPOINT}/{company_id}", headers=system_user_auth_header)
        response_json = response.json()

        assert response.status_code == 200
        assert response_json["id"] == company_id
        assert response_json["name"] == samples.TEST_COMPANY_NAME
        assert response_json["total_capacity"] == samples.TEST_SITE_SYSTEM_SIZE_AC * 4
        assert response_json["sites_under_construction"] == 1
        assert response_json["sites_placed_in_service"] == 4
        assert response_json["sites_decommissioned"] == 1
        assert response_json["sites_sold"] == 1
        assert response_json["total_sites"] == 7

        # cleanup
        for site_ in created_sites:
            sites_crud.delete_by_id(site_.id)

    @pytest.mark.parametrize("sites", [5], indirect=True)
    def test_get_company_by_id_company_user(
        self, client, company, company_member_user_auth_header, sites, db_session, sites_placed_in_service
    ):
        """Test that regular user has access only to the sites provided by the project access"""
        response = client.get(f"{self.COMPANIES_API_ENDPOINT}/{company.id}", headers=company_member_user_auth_header)
        response_json = response.json()

        assert response.status_code == 200
        assert response_json["id"] == company.id
        assert response_json["name"] == samples.TEST_COMPANY_NAME
        assert response_json["total_capacity"] == samples.TEST_SITE_SYSTEM_SIZE_AC
        assert response_json["sites_under_construction"] == 0
        assert response_json["sites_placed_in_service"] == 1
        assert response_json["total_sites"] == 1
        assert len(company.sites) == 5

    def test_company_by_id_w_float_capacity(
        self, client, system_user_auth_header, company_id, site, db_session, sites_placed_in_service
    ):
        """This test creates new site and only System user has access to fetch all sites from company."""
        site.system_size_ac = 15.34432101423413
        db_session.commit()

        response = client.get(f"{self.COMPANIES_API_ENDPOINT}/{company_id}", headers=system_user_auth_header)
        response_json = response.json()

        # ensure site float capacity is rounded and limited to 2 digits scale
        assert response_json["total_capacity"] == 15.34

    def test_get_company_by_id_403(self, client, non_system_user_auth_header, company_id):
        """Test that user with no company rights gets 403."""
        # define non-existing company ID as next to created in the fixture

        response = client.get(f"{self.COMPANIES_API_ENDPOINT}/{company_id}", headers=non_system_user_auth_header)
        assert response.status_code == 403

    def test_get_company_by_id_404(self, client, company_member_user_auth_header, company_id):
        """Test that companies GET with id of unexisting company gives 404."""
        # define non-existing company ID as next to created in the fixture

        response = client.get(f"{self.COMPANIES_API_ENDPOINT}/{company_id + 1}", headers=company_member_user_auth_header)
        assert response.status_code == 404

    def test_get_company_with_sites_system_user(self, client, company_id, site_id, system_user_auth_header):
        """Test system user is allowed to retrieve companies/sites"""
        response = client.get(self.COMPANIES_SITES_API_ENDPOINT, headers=system_user_auth_header)
        expected_body = {
            "id": company_id,
            "name": samples.TEST_COMPANY_NAME,
            "sites": [{"id": site_id, "name": samples.TEST_SITE_NAME}],
        }

        assert response.status_code == 200
        assert expected_body in response.json()["data"]

    def test_get_company_with_sites_non_system_user(self, client, company_id, site_id, non_system_user_auth_header):
        """Test non-system user is prohibited to retrieve companies/sites"""
        response = client.get(self.COMPANIES_SITES_API_ENDPOINT, headers=non_system_user_auth_header)

        assert response.status_code == 403

    def test_get_company_with_sites_company_admin_full(self, client, company_id, company_admin_full_access_header):
        """Validate company admin with full access is allowed to call sites endpoint"""
        response = client.get(self.COMPANIES_SITES_API_ENDPOINT, headers=company_admin_full_access_header)
        assert response.status_code == 200

    def test_get_company_with_sites_company_admin_read(self, client, company_id, company_admin_read_access_header):
        """Validate company admin with read access is not allowed to call sites endpoint"""
        response = client.get(self.COMPANIES_SITES_API_ENDPOINT, headers=company_admin_read_access_header)
        assert response.status_code == 403
