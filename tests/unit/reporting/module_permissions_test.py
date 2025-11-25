"""Validate each reporting module API is protected with the permissions check"""

import pytest


class TestModulePermissionsCheck:

    @pytest.mark.parametrize(
        "request_url",
        (
            "/api/reporting/companies",
            "/api/reporting/companies/{company_id}/sites",
            "/api/reporting/reports",
            "/api/reporting/reports/report_id_/generate-embedding-token",
        ),
    )
    # def test_permissions_validation_403(self, client, auth_header, setup_companies, expected_response_items):
    def test_permissions_validation_403(
        self,
        client,
        company,
        company_member_user_auth_header,
        company_member_user,
        role_without_reports_access,
        mocker,
        request_url,
    ):
        """Check user without reporting access cannot reach the endpoint"""

        logger_mock = mocker.patch("app.helpers.authorization.module_based.base.logger")

        # to support parametrized URLs, make substitution params for the URL formatting
        substitution_params = {
            "company_id": company.id,
        }
        request_url = request_url.format(**substitution_params)

        response = client.get(request_url, headers=company_member_user_auth_header)

        assert response.status_code == 403

        logger_mock.warning.assert_called_with(
            f"User with ID <{company_member_user.id}> (role <{company_member_user.role.name}>) is not authorized "
            f"for the endpoint <{request_url}>"
        )
