from unittest.mock import Mock

from google.api_core.exceptions import from_http_status

from app.crud.attachment import AttachmentCRUD
from tests.unit import samples


class TestAttachments:
    TASK_TRACKER_API_ENDPOINT = "/api/task-tracker"

    def _generate_attachment_list_endpoint(self, board_id_, task_id_):
        return f"{self.TASK_TRACKER_API_ENDPOINT}/boards/{board_id_}/tasks/{task_id_}/attachments"

    def _generate_attachment_upload_url(self, board_id_, task_id_):
        return f"{self._generate_attachment_list_endpoint(board_id_, task_id_)}/upload-url"

    def _generate_upload_tracking_url(self, board_id_, task_id_):
        return f"{self._generate_attachment_list_endpoint(board_id_, task_id_)}/track-uploaded-attachment"

    def _generate_attachment_endpoint(self, board_id_, task_id_, attachment_id_):
        return f"{self._generate_attachment_list_endpoint(board_id_, task_id_)}/{attachment_id_}"

    def test_get_upload_url(self, site_default_board_id, site_task_id, mocker, client, system_user_auth_header):
        upload_url = "https://storage.googleapis.com/upload"
        mocker.patch("app.helpers.files.file_handler.service_account")
        mock_storage = mocker.patch("app.helpers.files.file_handler.storage.Client")
        mock_storage.return_value.bucket.return_value.blob.return_value.generate_signed_url.return_value = upload_url
        response = client.post(
            self._generate_attachment_upload_url(site_default_board_id, site_task_id),
            headers=system_user_auth_header,
            json={"filename": "attachment.pdf"},
        )
        assert response.status_code == 200
        assert response.json()["upload_url"] == upload_url

    def test_get_upload_url_404(self, site_default_board_id, client, system_user_auth_header):
        response = client.post(
            self._generate_attachment_upload_url(site_default_board_id, task_id_=1234),
            headers=system_user_auth_header,
            json={"filename": "attachment.pdf"},
        )
        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"

    def test_get_upload_url_403(self, site_default_board_id, site_task_id, client, non_system_user_auth_header):
        response = client.post(
            self._generate_attachment_upload_url(site_default_board_id, site_task_id),
            headers=non_system_user_auth_header,
            json={"filename": "attachment.pdf"},
        )
        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"

    def test_get_upload_url_w_wrong_extension(
        self, site_default_board_id, site_task_id, client, system_user_auth_header
    ):
        filename = "attachment.xls"
        response = client.post(
            self._generate_attachment_upload_url(site_default_board_id, site_task_id),
            headers=system_user_auth_header,
            json={"filename": filename},
        )
        assert response.status_code == 422
        assert (
            response.json()["message"]
            == f"File {filename} has invalid extension. Only {samples.ALLOWED_FILE_EXTENSIONS} are allowed"
        )

    def test_create_uploaded_file(self, site_default_board_id, site_task_id, client, system_user_auth_header):
        response = client.post(
            self._generate_upload_tracking_url(site_default_board_id, site_task_id),
            headers=system_user_auth_header,
            json={
                "filename": "attachment.pdf",
                "filepath": "boards/1/tasks/1/attachments/2024-2-5T11:00:12_attachment.pdf",
            },
        )
        assert response.status_code == 200
        assert response.json()["message"] == "File successfully uploaded"

    def test_create_uploaded_file_403(self, site_default_board_id, site_task_id, client, non_system_user_auth_header):
        response = client.post(
            self._generate_upload_tracking_url(site_default_board_id, site_task_id),
            headers=non_system_user_auth_header,
            json={
                "filename": "attachment.pdf",
                "filepath": "boards/1/tasks/1/attachments/2024-2-5T11:00:12_attachment.pdf",
            },
        )
        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"

    def test_create_uploaded_file_404(self, site_default_board_id, client, system_user_auth_header):
        response = client.post(
            self._generate_upload_tracking_url(site_default_board_id, task_id_=123224),
            headers=system_user_auth_header,
            json={
                "filename": "attachment.pdf",
                "filepath": "boards/1/tasks/1/attachments/2024-2-5T11:00:12_attachment.pdf",
            },
        )
        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"

    def test_create_uploaded_file_w_wrong_extension(
        self, site_default_board_id, site_task_id, client, system_user_auth_header
    ):
        filename = "attachment.xls"
        response = client.post(
            self._generate_upload_tracking_url(site_default_board_id, site_task_id),
            headers=system_user_auth_header,
            json={
                "filename": filename,
                "filepath": "boards/1/tasks/1/attachments/2024-2-5T11:00:12_attachment.pdf",
            },
        )
        assert response.status_code == 422
        assert (
            response.json()["message"]
            == f"File {filename} has invalid extension. Only {samples.ALLOWED_FILE_EXTENSIONS} are allowed"
        )

    def test_get_attachments_list(
        self, site_default_board_id, site_task_id, attachment, company_member_user_auth_header, client
    ):
        """Test retrieving list of attachments for document."""
        response = client.get(
            self._generate_attachment_list_endpoint(site_default_board_id, site_task_id),
            headers=company_member_user_auth_header,
        )
        attachments = [
            attachment
            for attachment in response.json()["items"]
            if attachment["filename"] == samples.TEST_ATTACHMENT_NAME
        ]
        assert response.status_code == 200
        assert len(attachments) == 1
        assert attachments[0]["filename"] == samples.TEST_ATTACHMENT_NAME
        assert attachments[0]["extension"] == "pdf"
        assert attachments[0]["author"] == f"{samples.NON_SYSTEM_USER_NAME} {samples.NON_SYSTEM_USER_LAST_NAME}"

    def test_get_attachments_list_403(
        self, site_default_board_id, site_task_id, attachment, non_system_user_auth_header, client
    ):
        """Test retrieving list of attachments return 403."""
        response = client.get(
            self._generate_attachment_list_endpoint(site_default_board_id, site_task_id),
            headers=non_system_user_auth_header,
        )
        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"

    def test_get_attachments_list_404(self, attachment, company_member_user_auth_header, client):
        """Test retrieving list of attachments return 404."""
        response = client.get(
            self._generate_attachment_list_endpoint(1234, 1234), headers=company_member_user_auth_header
        )
        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"

    def test_get_download_url(
        self, site_default_board_id, site_task_id, mocker, client, attachment, system_user_auth_header
    ):
        download_url = "https://storage.googleapis.com/"
        mocker.patch("app.helpers.files.file_handler.service_account")
        mock_storage = mocker.patch("app.helpers.files.file_handler.storage.Client")
        mock_storage.return_value.bucket.return_value.blob.return_value.generate_signed_url.return_value = download_url
        response = client.get(
            self._generate_attachment_endpoint(site_default_board_id, site_task_id, attachment.id),
            headers=system_user_auth_header,
        )
        assert response.status_code == 200
        assert response.json()["download_url"] == download_url

    def test_get_download_url_404(self, site_default_board_id, site_task_id, client, system_user_auth_header):
        response = client.get(
            self._generate_attachment_endpoint(site_default_board_id, site_task_id, 1234),
            headers=system_user_auth_header,
        )
        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"

    def test_get_download_url_403(
        self, site_default_board_id, site_task_id, attachment, client, non_system_user_auth_header
    ):
        response = client.get(
            self._generate_attachment_endpoint(site_default_board_id, site_task_id, attachment.id),
            headers=non_system_user_auth_header,
        )
        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"

    def test_delete_attachment_403_no_access(
        self, site_default_board_id, site_task_id, attachment, non_system_user_auth_header, client
    ):
        """Test that 403 is thrown if access to the site wasn't given"""
        response = client.delete(
            self._generate_attachment_endpoint(site_default_board_id, site_task_id, attachment.id),
            headers=non_system_user_auth_header,
        )
        assert response.status_code == 403

    def test_delete_attachment_404_board(
        self, site_default_board_id, site_task_id, attachment_id, company_member_user_auth_header, client, mocker
    ):
        """Test that 404 is thrown if board doesn't exist"""
        logger_mock = mocker.patch("app.helpers.authorization.project_access.logger")
        board_id = site_default_board_id + 1000
        response = client.delete(
            self._generate_attachment_endpoint(board_id, site_task_id, attachment_id),
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 404
        logger_mock.warning.assert_called_with(f"There is no board with id {board_id}")

    def test_delete_attachment_404_task(
        self,
        site_id,
        site_default_board_id,
        site_task_id,
        attachment_id,
        company_member_user_auth_header,
        client,
        mocker,
    ):
        """Test that 404 is thrown if task doesn't exist"""
        logger_mock = mocker.patch("app.helpers.authorization.project_access.logger")

        site_task_id = site_task_id + 1000
        response = client.delete(
            self._generate_attachment_endpoint(site_default_board_id, site_task_id, attachment_id),
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 404
        logger_mock.warning.assert_called_with(f"There is no task with id {site_task_id}")

    def test_delete_attachment_404_attachment(
        self,
        site_id,
        site_default_board_id,
        site_task_id,
        attachment_id,
        company_member_user_auth_header,
        client,
        mocker,
    ):
        """Test that 404 is thrown if attachment doesn't exist"""
        logger_mock = mocker.patch("app.helpers.authorization.project_access.logger")
        attachment_id = attachment_id + 1000
        response = client.delete(
            self._generate_attachment_endpoint(site_default_board_id, site_task_id, attachment_id),
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 404
        logger_mock.warning.assert_called_with(f"There is no attachment with id {attachment_id}")

    def test_delete_attachment_success(
        self,
        site_default_board_id,
        attachment,
        company_member_user_auth_header,
        client,
        mocker,
    ):
        mocker.patch("app.helpers.files.file_handler.service_account")
        mock_storage = mocker.patch("app.helpers.files.file_handler.storage.Client")
        mock_storage.bucket.blob.delete.return_value = None
        response = client.delete(
            self._generate_attachment_endpoint(site_default_board_id, attachment.task_id, attachment.id),
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 200
        assert response.json()["message"] == "File has been successfully deleted"

    def test_delete_attachment_gcs_404(
        self,
        site_id,
        site_default_board_id,
        site_task_id,
        attachment,
        company_member_user_auth_header,
        client,
        mocker,
    ):
        """Validate attachment record is removed if GCS returns 404"""
        mocker.patch("app.helpers.files.file_handler.service_account")
        logger_mock = mocker.patch("app.helpers.files.file_handler.logger")
        mock_storage = mocker.patch("app.helpers.files.file_handler.storage.Client")
        mock_storage.return_value.bucket.return_value.blob.return_value.delete.side_effect = from_http_status(
            404,
            "Not Found",
        )
        response = client.delete(
            self._generate_attachment_endpoint(site_default_board_id, site_task_id, attachment.id),
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 200
        assert response.json()["message"] == "File has been successfully deleted"
        logger_mock.warning.assert_called_with(f"Can not locate file by GCS path {attachment.filepath}")

    def test_delete_attachment_gcs_exception(
        self,
        site_id,
        site_default_board_id,
        site_task_id,
        attachment,
        company_member_user_auth_header,
        client,
        mocker,
    ):
        """Test that GCS error is handled if it returns 403"""
        mocker.patch("app.helpers.files.file_handler.service_account")
        mock_storage = mocker.patch("app.helpers.files.file_handler.storage.Client")
        mock_storage.return_value.bucket.return_value.blob.return_value.delete.side_effect = from_http_status(
            403,
            "Forbidden",
            response=Mock(
                content='{"error": {"code": 403, "message": "Permission denied on resource (or it may not exist)."}}'
            ),
        )
        response = client.delete(
            self._generate_attachment_endpoint(site_default_board_id, site_task_id, attachment.id),
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 403
        assert response.json()["message"] == "Permission denied on resource (or it may not exist)."

    def test_get_preview_attachment_url(
        self, site_default_board_id, site_task_id, attachment_id, client, system_user_auth_header, mocker
    ):
        preview_url = "https://storage.googleapis.com/attachment.pdf"
        mocker.patch("app.helpers.files.file_handler.service_account")
        mock_storage = mocker.patch("app.helpers.files.file_handler.storage.Client")
        mock_storage.return_value.bucket.return_value.blob.return_value.generate_signed_url.return_value = preview_url
        response = client.get(
            (
                f"{self._generate_attachment_endpoint(site_default_board_id, site_task_id, attachment_id)}"
                "/file-preview-url/"
            ),
            headers=system_user_auth_header,
        )
        assert response.status_code == 200
        assert response.json()["preview_url"] == preview_url

    def test_get_preview_attachment_url_non_pdf(
        self, site_default_board_id, site_task_id, attachment_id, client, system_user_auth_header, mocker, db_session
    ):
        preview_url = "https://storage.googleapis.com/attachment.pdf"
        mocker.patch("app.helpers.files.file_handler.service_account")
        mock_storage = mocker.patch("app.helpers.files.file_handler.storage.Client")
        mock_storage.return_value.bucket.return_value.blob.return_value.generate_signed_url.return_value = preview_url
        # update attachment file not to be pdf
        AttachmentCRUD(db_session).update_by_id(attachment_id, {"filename": "test_attachment.doc"})
        response = client.get(
            (
                f"{self._generate_attachment_endpoint(site_default_board_id, site_task_id, attachment_id)}"
                "/file-preview-url/"
            ),
            headers=system_user_auth_header,
        )
        assert response.status_code == 400
        assert response.json()["message"] == samples.INVALID_PREVIEW_FILE_EXTENSION_ERR_MSG

    def test_get_preview_attachment_url_403(
        self, site_default_board_id, site_task_id, attachment_id, client, non_system_user_auth_header
    ):
        response = client.get(
            (
                f"{self._generate_attachment_endpoint(site_default_board_id, site_task_id, attachment_id)}"
                "/file-preview-url/"
            ),
            headers=non_system_user_auth_header,
        )
        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"

    def test_get_preview_attachment_url_404(self, site_default_board_id, site_task_id, client, system_user_auth_header):
        response = client.get(
            f"{self._generate_attachment_endpoint(site_default_board_id, site_task_id, 9999)}/file-preview-url/",
            headers=system_user_auth_header,
        )
        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"
