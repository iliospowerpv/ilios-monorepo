import pytest
from pytest_lazy_fixtures import lf

import tests.unit.samples as samples
from tests.utils import remove_dynamic_fields


class TestCompanies:
    """Tests for companies routes."""

    @staticmethod
    def _gen_list_endpoint():
        return "/api/reporting/companies"

    @pytest.mark.parametrize(
        "auth_header,setup_companies,expected_response_items",
        (
            # system user - should have all companies in the system
            (
                lf("system_user_auth_header"),
                3,
                [
                    {
                        "name": samples.TEST_COMPANY_NAME2,
                    },
                    {
                        "name": samples.TEST_COMPANY_NAME,
                    },
                ],
            ),
            # company admin - has only companies assigned to him
            (
                lf("company_member_user_auth_header"),
                3,
                [
                    {
                        "name": samples.TEST_COMPANY_NAME,
                    },
                ],
            ),
        ),
        indirect=["setup_companies"],
    )
    def test_get_companies_success(self, client, auth_header, setup_companies, expected_response_items):
        response = client.get(self._gen_list_endpoint(), params={"skip": 0, "limit": 2}, headers=auth_header)
        response_json = response.json()

        # remove ID since it's dynamic field
        response_items = response_json["items"]
        remove_dynamic_fields(response_items)

        assert response.status_code == 200
        assert response_json["skip"] == 0
        assert response_json["limit"] == 2

        assert response_items == expected_response_items
