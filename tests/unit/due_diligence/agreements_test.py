from app.helpers.configs.ai_parsing_helper import AIParsingHandler
from app.helpers.files.file_helper import combine_user_ai_parsing_results
from tests.unit import samples


class TestAgreements:
    """Tests for due diligence requirements (documents) routes, specific for the parsable documents."""

    @staticmethod
    def _generate_list_endpoint(site_id_):
        """/api/due-diligence/SITE_ID/agreements"""
        return f"/api/due-diligence/{site_id_}/agreements"

    def _generate_overview_endpoint(self, site_id_, document_id_):
        """/api/due-diligence/SITE_ID/agreements/DOCUMENT_ID/overview"""
        return f"{self._generate_list_endpoint(site_id_)}/{document_id_}/overview"

    def test_get_agreements(self, client, site, all_site_documents, company_member_user_auth_header, db_session):

        response = client.get(self._generate_list_endpoint(site.id), headers=company_member_user_auth_header)

        assert response.status_code == 200
        # agreement names count can be more or equal to the parsable documents
        # since some document names are duplicated across different sections
        assert len(response.json()["items"]) >= len(AIParsingHandler(db_session).get_parsable_documents_list())

    def test_get_agreements_no_diligence_overview_access(
        self,
        client,
        site,
        documents,
        company_member_user_auth_header,
        company_member_user,
        limit_role_dd_overview_access,
        mocker,
    ):
        """Check user shouldn't see overview page despite Diligence access"""
        logger_mock = mocker.patch("app.helpers.authorization.custom.diligence_overview_page.logger")
        response = client.get(self._generate_list_endpoint(site.id), headers=company_member_user_auth_header)

        assert response.status_code == 403
        logger_mock.warning.assert_called_with(
            f"User with ID <{company_member_user.id}> (role <{company_member_user.role.name}>, "
            f"role company type <{samples.TEST_COMPANY_TYPE2}>) is not allowed to review Due Diligence Overview page"
        )

    def test_get_agreements_are_sorted_a_z(self, client, site, documents, company_member_user_auth_header, db_session):

        response = client.get(self._generate_list_endpoint(site.id), headers=company_member_user_auth_header)

        is_sorted = response.json()["items"] == sorted(response.json()["items"], key=lambda x: x["name"])

        assert response.status_code == 200
        assert is_sorted

    def test_get_agreement_overview_403(self, client, site_id, non_system_user_auth_header):
        """Test that user cannot access the documents if they don't have access to the site"""

        response = client.get(self._generate_overview_endpoint(site_id, 456), headers=non_system_user_auth_header)

        assert response.status_code == 403

    def test_get_agreement_overview_404(self, client, site_id, company_member_user_auth_header, mocker):
        """Regular 404 handling - document doesn't exist"""
        logger_mock = mocker.patch("app.helpers.authorization.project_access.logger")

        response = client.get(self._generate_overview_endpoint(site_id, 123), headers=company_member_user_auth_header)

        assert response.status_code == 404
        logger_mock.warning.assert_called_with("There is no document with id 123")

    def test_get_agreement_overview_success(
        self, client, site_id, site_lease_document, company_member_user_auth_header, db_session
    ):
        response = client.get(
            self._generate_overview_endpoint(site_id, site_lease_document.id), headers=company_member_user_auth_header
        )

        assert response.status_code == 200
        assert len(response.json()["items"]) == len(
            combine_user_ai_parsing_results(site_lease_document, db_session=db_session)
        )

    def test_get_agreements_overview_no_diligence_overview_access(
        self, client, site_id, site_lease_document, company_member_user_auth_header, limit_role_dd_overview_access
    ):
        response = client.get(
            self._generate_overview_endpoint(site_id, site_lease_document.id), headers=company_member_user_auth_header
        )

        assert response.status_code == 403
