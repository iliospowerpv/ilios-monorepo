import pytest
from pytest_lazy_fixtures import lf

import tests.unit.samples as samples
from tests.utils import remove_dynamic_fields


class TestSites:

    @staticmethod
    def _gen_list_endpoint(company_id_):
        return f"/api/reporting/companies/{company_id_}/sites"

    @pytest.mark.parametrize(
        "auth_header,sites,expected_response_items",
        (
            # system user - should have all sites in the system
            (
                lf("system_user_auth_header"),
                3,
                [
                    {
                        "name": samples.TEST_SITE_NAME,
                    },
                    {
                        "name": samples.TEST_SITE_NAME,
                    },
                ],
            ),
            # company admin - has only sites assigned to him
            (
                lf("company_member_user_auth_header"),
                3,
                [
                    {
                        "name": samples.TEST_SITE_NAME,
                    },
                ],
            ),
        ),
        indirect=["sites"],
    )
    def test_get_sites_success(self, client, auth_header, company_id, sites, expected_response_items):
        response = client.get(self._gen_list_endpoint(company_id), params={"skip": 0, "limit": 2}, headers=auth_header)
        response_json = response.json()

        # remove ID since it's dynamic field
        response_items = response_json["items"]
        remove_dynamic_fields(response_items)

        assert response.status_code == 200
        assert response_json["skip"] == 0
        assert response_json["limit"] == 2

        assert response_items == expected_response_items

    def test_get_sites_access_denied(
        self, client, non_system_user_auth_header, create_non_system_user, company_id, sites, mocker
    ):
        """User without company access is prohibited from the sites retrieval"""
        logger_mock = mocker.patch("app.helpers.authorization.project_access.logger")
        response = client.get(self._gen_list_endpoint(company_id), headers=non_system_user_auth_header)

        assert response.status_code == 403
        logger_mock.warning.assert_called_with(
            f"User {create_non_system_user.id} tried to access company {company_id} without company access."
        )
