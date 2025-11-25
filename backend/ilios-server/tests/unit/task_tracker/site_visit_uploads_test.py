import pytest

from app.static import TaskMessages
from app.static.site_visits import SiteVisitsUploads
from tests.unit import samples


class TestSiteVisitUploads:
    """Please, note - feature applicable only for O&M site visit level tasks,
    it's precondition for the tests execution"""

    @staticmethod
    def _generate_list_endpoint(board_id_, task_id_, section_name_):
        return f"/api/task-tracker/boards/{board_id_}/tasks/{task_id_}/site-visits/{section_name_}"

    def _generate_upload_url(self, board_id_, task_id_, section_name_):
        return f"{self._generate_list_endpoint(board_id_, task_id_, section_name_)}/upload-url"

    def _generate_upload_tracking_url(self, board_id_, task_id_, section_name_):
        return f"{self._generate_list_endpoint(board_id_, task_id_, section_name_)}/track-uploaded-attachment"

    def _generate_individual_endpoint(self, board_id_, task_id_, section_name_, upload_id_):
        return f"{self._generate_list_endpoint(board_id_, task_id_, section_name_)}/{upload_id_}"

    def _generate_preview_url_endpoint(self, board_id_, task_id_, section_name_, upload_id_):
        return f"{self._generate_individual_endpoint(board_id_, task_id_, section_name_, upload_id_)}/file-preview-url"

    @pytest.mark.parametrize(
        "section_name",
        (
            SiteVisitsUploads.site_conditions.value,
            SiteVisitsUploads.field_discovery.value,
        ),
    )
    def test_get_upload_url_success(
        self, client, site_visit, company_member_user_auth_header, gcs_signed_url_generation, section_name
    ):
        response = client.post(
            self._generate_upload_url(site_visit.task.board_id, site_visit.task.id, section_name),
            headers=company_member_user_auth_header,
            json=samples.TEST_SV_UPLOAD_GEN_UPLOAD_LINK_VALID_PAYLOAD,
        )
        assert response.status_code == 200
        assert response.json()["upload_url"] == samples.TEST_GCP_LINK

    @pytest.mark.parametrize(
        "section_name",
        (
            SiteVisitsUploads.site_conditions.value,
            SiteVisitsUploads.field_discovery.value,
        ),
    )
    def test_get_upload_url_validation_error(self, site_visit, client, company_member_user_auth_header, section_name):
        response = client.post(
            self._generate_upload_url(site_visit.task.board_id, site_visit.task.id, section_name),
            headers=company_member_user_auth_header,
            json=samples.TEST_SV_UPLOAD_GEN_UPLOAD_LINK_WRONG_PAYLOAD,
        )
        assert response.status_code == 422
        assert response.json()["message"] == samples.TEST_SV_UPLOAD_INVALID_EXTENSION_ERR

    @pytest.mark.parametrize(
        "section_name",
        (
            SiteVisitsUploads.site_conditions.value,
            SiteVisitsUploads.field_discovery.value,
        ),
    )
    def test_get_upload_url_404(self, site_om_task, client, company_member_user_auth_header, section_name):
        """Validate user-friendly message is returned if there is attempt to manage attachments without site visit"""
        response = client.post(
            self._generate_upload_url(site_om_task.board_id, site_om_task.id, section_name),
            headers=company_member_user_auth_header,
            json=samples.TEST_SV_UPLOAD_GEN_UPLOAD_LINK_VALID_PAYLOAD,
        )
        assert response.status_code == 404
        assert response.json()["message"] == TaskMessages.site_visit_not_found.value

    @pytest.mark.parametrize(
        "section_name",
        (
            SiteVisitsUploads.site_conditions.value,
            SiteVisitsUploads.field_discovery.value,
        ),
    )
    def test_get_upload_url_403(self, site_visit, client, non_system_user_auth_header, section_name):
        response = client.post(
            self._generate_upload_url(site_visit.task.board_id, site_visit.task.id, section_name),
            headers=non_system_user_auth_header,
            json=samples.TEST_SV_UPLOAD_GEN_UPLOAD_LINK_VALID_PAYLOAD,
        )
        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"

    @pytest.mark.parametrize(
        "section_name",
        (
            SiteVisitsUploads.site_conditions.value,
            SiteVisitsUploads.field_discovery.value,
        ),
    )
    def test_create_uploaded_file_success(self, client, site_visit, company_member_user_auth_header, section_name):
        response = client.post(
            self._generate_upload_tracking_url(site_visit.task.board_id, site_visit.task.id, section_name),
            headers=company_member_user_auth_header,
            json=samples.TEST_SV_UPLOAD_TRACK_UPLOAD_VALID_PAYLOAD,
        )
        assert response.status_code == 200
        assert response.json()["message"] == "File successfully uploaded"

    @pytest.mark.parametrize(
        "section_name, site_visit_upload",
        (
            (SiteVisitsUploads.site_conditions.value, SiteVisitsUploads.site_conditions.value),
            (SiteVisitsUploads.field_discovery.value, SiteVisitsUploads.field_discovery.value),
        ),
        indirect=["site_visit_upload"],
    )
    def test_get_list_success(self, site_visit_upload, company_member_user_auth_header, client, section_name):
        response = client.get(
            self._generate_list_endpoint(
                site_visit_upload.site_visit.task.board_id, site_visit_upload.site_visit.task.id, section_name
            ),
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 200
        assert response.json()["items"][0] == samples.TEST_SV_UPLOAD_ITEM

    @pytest.mark.parametrize(
        "section_name, site_visit_upload",
        (
            (SiteVisitsUploads.site_conditions.value, SiteVisitsUploads.site_conditions.value),
            (SiteVisitsUploads.field_discovery.value, SiteVisitsUploads.field_discovery.value),
        ),
        indirect=["site_visit_upload"],
    )
    def test_get_download_url_success(
        self, client, company_member_user_auth_header, gcs_signed_url_generation, section_name, site_visit_upload
    ):
        response = client.get(
            self._generate_individual_endpoint(
                site_visit_upload.site_visit.task.board_id,
                site_visit_upload.site_visit.task.id,
                section_name,
                site_visit_upload.id,
            ),
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 200
        assert response.json()["download_url"] == samples.TEST_GCP_LINK

    @pytest.mark.parametrize(
        "section_name, site_visit_upload",
        (
            (SiteVisitsUploads.site_conditions.value, SiteVisitsUploads.site_conditions.value),
            (SiteVisitsUploads.field_discovery.value, SiteVisitsUploads.field_discovery.value),
        ),
        indirect=["site_visit_upload"],
    )
    def test_delete_upload_success(
        self,
        client,
        company_member_user_auth_header,
        section_name,
        site_visit_upload,
        mocker,
    ):
        mocker.patch("app.helpers.files.file_handler.service_account")
        mock_storage = mocker.patch("app.helpers.files.file_handler.storage.Client")
        mock_storage.bucket.blob.delete.return_value = None
        response = client.delete(
            self._generate_individual_endpoint(
                site_visit_upload.site_visit.task.board_id,
                site_visit_upload.site_visit.task.id,
                section_name,
                site_visit_upload.id,
            ),
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 200
        assert response.json()["message"] == "File has been successfully deleted"

    @pytest.mark.parametrize(
        "section_name, site_visit_upload",
        (
            (SiteVisitsUploads.site_conditions.value, SiteVisitsUploads.site_conditions.value),
            (SiteVisitsUploads.field_discovery.value, SiteVisitsUploads.field_discovery.value),
        ),
        indirect=["site_visit_upload"],
    )
    def test_get_preview_url_success(
        self, client, company_member_user_auth_header, gcs_signed_url_generation, section_name, site_visit_upload
    ):
        response = client.get(
            self._generate_preview_url_endpoint(
                site_visit_upload.site_visit.task.board_id,
                site_visit_upload.site_visit.task.id,
                section_name,
                site_visit_upload.id,
            ),
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 200
        assert response.json()["preview_url"] == samples.TEST_GCP_LINK

    def test_site_visit_wrong_section(
        self,
        client,
        company_member_user_auth_header,
        company_member_user,
        site_visit_upload,
        mocker,
    ):
        """If user tries to retrieve image from the different section"""
        logger_mock = mocker.patch("app.helpers.authorization.entity_based.task.logger")
        response = client.get(
            self._generate_individual_endpoint(
                site_visit_upload.site_visit.task.board_id,
                site_visit_upload.site_visit.task.id,
                SiteVisitsUploads.field_discovery.value,
                site_visit_upload.id,
            ),
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 403
        logger_mock.warning.assert_called_with(
            f"User {company_member_user.id} tried to access site visit attachment {site_visit_upload.id} which "
            f"belongs to different site visit section"
        )
