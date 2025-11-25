import copy

import pytest

from app.crud.site import SiteCRUD
from tests.unit import samples


class TestSettingsSite:

    SETTINGS_SITE_API_ENDPOINT = "/api/settings/sites"

    def test_get_settings_sites(self, client, system_user_auth_header, site_id):
        response = client.get(self.SETTINGS_SITE_API_ENDPOINT, headers=system_user_auth_header)
        response_json = response.json()

        assert response.status_code == 200
        assert response_json["skip"] == 0
        assert response_json["limit"] == 10

        items = response_json["items"]

        assert len(items) == 1
        assert items[0]["name"] == samples.TEST_SITE_NAME
        assert items[0]["address"] == samples.TEST_SITE_ADDRESS
        assert items[0]["company_name"] == samples.TEST_COMPANY_NAME

    def test_get_settings_sites_403(self, client, non_system_user_auth_header):
        response = client.get(self.SETTINGS_SITE_API_ENDPOINT, headers=non_system_user_auth_header)
        response_json = response.json()

        assert response.status_code == 403
        assert response_json["message"] == "Forbidden"

    @pytest.mark.parametrize(
        "order_by, order_direction, expected_first_name, expected_second_name",
        (
            # if ascending order: "Test site 2" should go first before "Windmills Farm"
            ("name", "asc", samples.VALID_SITE_BODY2["name"], samples.TEST_SITE_NAME),
            # if order_direction is not provided "asc" should be default
            ("name", None, samples.VALID_SITE_BODY2["name"], samples.TEST_SITE_NAME),
            # if descending order: "Windmills Farm" should go first before "Test site 2"
            ("name", "desc", samples.TEST_SITE_NAME, samples.VALID_SITE_BODY2["name"]),
            # if ascending order: "6645" should go first before "833"
            ("address", "asc", samples.VALID_SITE_BODY2["address"], samples.TEST_SITE_ADDRESS),
            # if order_direction is not provided "asc" should be default
            ("address", None, samples.VALID_SITE_BODY2["address"], samples.TEST_SITE_ADDRESS),
            # if descending order: "833" should go first before "6645"
            ("address", "desc", samples.TEST_SITE_ADDRESS, samples.VALID_SITE_BODY2["address"]),
        ),
    )
    def test_get_settings_sites_order_by(
        self,
        client,
        db_session,
        company_id,
        system_user_auth_header,
        site_id,
        order_by,
        order_direction,
        expected_first_name,
        expected_second_name,
    ):
        payload = copy.deepcopy(samples.VALID_SITE_BODY2)
        payload.update({"company_id": company_id})

        sites_crud = SiteCRUD(db_session)
        another_test_site_id = sites_crud.create_item(payload).id

        params = {"order_by": order_by}
        if order_direction:
            params["order_direction"] = order_direction
        response = client.get(self.SETTINGS_SITE_API_ENDPOINT, params=params, headers=system_user_auth_header)
        response_json = response.json()

        assert response.status_code == 200
        assert response_json["skip"] == 0
        assert response_json["limit"] == 10

        items = response_json["items"]
        assert items[0][order_by] == expected_first_name
        assert items[1][order_by] == expected_second_name

        sites_crud.delete_by_id(another_test_site_id)

    def test_get_settings_sites_search(self, client, db_session, company_id, system_user_auth_header, site_id):

        response = client.get(
            self.SETTINGS_SITE_API_ENDPOINT, params={"search": samples.TEST_SITE_NAME}, headers=system_user_auth_header
        )
        response_json = response.json()

        assert response.status_code == 200
        assert response_json["skip"] == 0
        assert response_json["limit"] == 10

        items = response_json["items"]

        assert len(items) == 1
        assert items[0]["name"] == samples.TEST_SITE_NAME
        assert items[0]["company_id"] == company_id

    def test_get_settings_sites_search_zero(self, client, db_session, company_id, system_user_auth_header, site_id):

        response = client.get(
            self.SETTINGS_SITE_API_ENDPOINT, params={"search": "Some fake name"}, headers=system_user_auth_header
        )
        response_json = response.json()

        assert response.status_code == 200
        assert response_json["skip"] == 0
        assert response_json["limit"] == 10

        assert len(response_json["items"]) == 0
