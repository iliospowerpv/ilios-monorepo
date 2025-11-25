from unittest.mock import Mock

from google.api_core.exceptions import from_http_status

from app.crud.device_document import DeviceDocumentCRUD
from tests.unit import samples


class TestDeviceDocuments:

    @staticmethod
    def _generate_device_documents_list_endpoint(site_id, device_id):
        return f"/api/sites/{site_id}/devices/{device_id}/documents"

    def _generate_device_document_endpoint(self, site_id, device_id, document_id_):
        return f"{self._generate_device_documents_list_endpoint(site_id, device_id)}/{document_id_}"

    def _generate_device_documents_upload_url(self, site_id, device_id):
        return f"{self._generate_device_documents_list_endpoint(site_id, device_id)}/upload-url"

    def _generate_device_documents_download_url(self, site_id, device_id, document_id_):
        return f"{self._generate_device_document_endpoint(site_id, device_id, document_id_)}/download-url"

    def _generate_upload_tracking_url(self, site_id, device_id):
        return f"{self._generate_device_documents_list_endpoint(site_id, device_id)}/track-uploaded-document"

    def test_get_upload_url(self, site_id, device_id, mocker, client, company_member_user_auth_header):
        upload_url = "https://storage.googleapis.com/upload"
        mocker.patch("app.helpers.files.file_handler.service_account")
        mock_storage = mocker.patch("app.helpers.files.file_handler.storage.Client")
        mock_storage.return_value.bucket.return_value.blob.return_value.generate_signed_url.return_value = upload_url
        response = client.post(
            self._generate_device_documents_upload_url(site_id, device_id),
            headers=company_member_user_auth_header,
            json={"filename": "document.pdf"},
        )
        assert response.status_code == 200
        assert response.json()["upload_url"] == upload_url

    def test_get_upload_url_404(self, site_id, client, company_member_user_auth_header):
        response = client.post(
            self._generate_device_documents_upload_url(site_id, device_id=1234),
            headers=company_member_user_auth_header,
            json={"filename": "document.pdf"},
        )
        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"

    def test_get_upload_url_403(self, site_id, device_id, client, non_system_user_auth_header):
        response = client.post(
            self._generate_device_documents_upload_url(site_id, device_id),
            headers=non_system_user_auth_header,
            json={"filename": "document.pdf"},
        )
        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"

    def test_get_upload_url_w_wrong_extension(self, site_id, device_id, client, system_user_auth_header):
        filename = "document.xls"
        response = client.post(
            self._generate_device_documents_upload_url(site_id, device_id),
            headers=system_user_auth_header,
            json={"filename": filename},
        )
        assert response.status_code == 422
        assert (
            response.json()["message"]
            == f"File {filename} has invalid extension. Only {samples.ALLOWED_FILE_EXTENSIONS} are allowed"
        )

    def test_track_uploaded_file(self, site_id, device_id, client, company_member_user_auth_header):
        response = client.post(
            self._generate_upload_tracking_url(site_id, device_id),
            headers=company_member_user_auth_header,
            json={
                "filename": "document.pdf",
                "filepath": "sites/1/devices/1/documents/2024-2-5T11:00:12_document.pdf",
                "category": "Warranty",
            },
        )
        assert response.status_code == 200
        assert response.json()["message"] == "File successfully uploaded"

    def test_track_uploaded_file_403(self, site_id, device_id, client, non_system_user_auth_header):
        response = client.post(
            self._generate_upload_tracking_url(site_id, device_id),
            headers=non_system_user_auth_header,
            json={
                "filename": "document.pdf",
                "filepath": "sites/1/devices/1/documents/2024-2-5T11:00:12_document.pdf",
                "category": "Warranty",
            },
        )
        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"

    def test_track_uploaded_file_404(self, site_id, client, company_member_user_auth_header):
        response = client.post(
            self._generate_upload_tracking_url(site_id, device_id=123224),
            headers=company_member_user_auth_header,
            json={
                "filename": "document.pdf",
                "filepath": "sites/1/devices/1/documents/2024-2-5T11:00:12_document.pdf",
                "category": "Warranty",
            },
        )
        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"

    def test_track_uploaded_file_w_wrong_extension(self, site_id, device_id, client, company_member_user_auth_header):
        filename = "document.xls"
        response = client.post(
            self._generate_upload_tracking_url(site_id, device_id),
            headers=company_member_user_auth_header,
            json={
                "filename": filename,
                "filepath": "sites/1/devices/1/documents/2024-2-5T11:00:12_document.xls",
                "category": "Warranty",
            },
        )
        assert response.status_code == 422
        assert (
            response.json()["message"]
            == f"File {filename} has invalid extension. Only {samples.ALLOWED_FILE_EXTENSIONS} are allowed"
        )

    def test_get_download_url(
        self, site_id, device_id, mocker, client, device_document_id, company_member_user_auth_header
    ):
        download_url = "https://storage.googleapis.com/"
        mocker.patch("app.helpers.files.file_handler.service_account")
        mock_storage = mocker.patch("app.helpers.files.file_handler.storage.Client")
        mock_storage.return_value.bucket.return_value.blob.return_value.generate_signed_url.return_value = download_url
        response = client.get(
            self._generate_device_documents_download_url(site_id, device_id, device_document_id),
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 200
        assert response.json()["download_url"] == download_url

    def test_get_download_url_404(self, site_id, device_id, client, company_member_user_auth_header):
        response = client.get(
            self._generate_device_documents_download_url(site_id, device_id, 1234),
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"

    def test_get_download_url_403(self, site_id, device_id, device_document_id, client, non_system_user_auth_header):
        response = client.get(
            self._generate_device_documents_download_url(site_id, device_id, device_document_id),
            headers=non_system_user_auth_header,
        )
        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"

    def test_delete_device_documents_403_no_access(
        self, site_id, device_id, device_document_id, non_system_user_auth_header, client
    ):
        response = client.delete(
            self._generate_device_document_endpoint(site_id, device_id, device_document_id),
            headers=non_system_user_auth_header,
        )
        assert response.status_code == 403

    def test_delete_document_404(
        self,
        site_id,
        device_id,
        device_document_id,
        company_member_user_auth_header,
        client,
        mocker,
    ):
        logger_mock = mocker.patch("app.helpers.authorization.project_access.logger")
        device_document_id = device_document_id + 1000
        response = client.delete(
            self._generate_device_document_endpoint(site_id, device_id, device_document_id),
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 404
        logger_mock.warning.assert_called_with(f"There is no device document with id {device_document_id}")

    def test_delete_device_document_success(
        self,
        site_id,
        device_document,
        company_member_user_auth_header,
        client,
        mocker,
    ):
        mocker.patch("app.helpers.files.file_handler.service_account")
        mock_storage = mocker.patch("app.helpers.files.file_handler.storage.Client")
        mock_storage.bucket.blob.delete.return_value = None
        response = client.delete(
            self._generate_device_document_endpoint(site_id, device_document.device_id, device_document.id),
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 200
        assert response.json()["message"] == "File has been successfully deleted"

    def test_delete_device_document_gcs_404(
        self,
        site_id,
        device_document,
        company_member_user_auth_header,
        client,
        mocker,
    ):
        mocker.patch("app.helpers.files.file_handler.service_account")
        logger_mock = mocker.patch("app.helpers.files.file_handler.logger")
        mock_storage = mocker.patch("app.helpers.files.file_handler.storage.Client")
        mock_storage.return_value.bucket.return_value.blob.return_value.delete.side_effect = from_http_status(
            404,
            "Not Found",
        )
        response = client.delete(
            self._generate_device_document_endpoint(site_id, device_document.device_id, device_document.id),
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 200
        assert response.json()["message"] == "File has been successfully deleted"
        logger_mock.warning.assert_called_with(f"Can not locate file by GCS path {device_document.filepath}")

    def test_delete_device_document_gcs_exception(
        self,
        site_id,
        device_document,
        company_member_user_auth_header,
        client,
        mocker,
    ):
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
            self._generate_device_document_endpoint(site_id, device_document.device_id, device_document.id),
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 403
        assert response.json()["message"] == "Permission denied on resource (or it may not exist)."

    def test_get_preview_device_document_url(
        self, site_id, device_id, device_document_id, client, company_member_user_auth_header, mocker
    ):
        preview_url = "https://storage.googleapis.com/document.pdf"
        mocker.patch("app.helpers.files.file_handler.service_account")
        mock_storage = mocker.patch("app.helpers.files.file_handler.storage.Client")
        mock_storage.return_value.bucket.return_value.blob.return_value.generate_signed_url.return_value = preview_url
        response = client.get(
            f"{self._generate_device_document_endpoint(site_id, device_id, device_document_id)}/file-preview-url/",
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 200
        assert response.json()["preview_url"] == preview_url

    def test_get_preview_device_document_url_non_pdf(
        self, site_id, device_id, device_document_id, client, company_member_user_auth_header, mocker, db_session
    ):
        preview_url = "https://storage.googleapis.com/document.pdf"
        mocker.patch("app.helpers.files.file_handler.service_account")
        mock_storage = mocker.patch("app.helpers.files.file_handler.storage.Client")
        mock_storage.return_value.bucket.return_value.blob.return_value.generate_signed_url.return_value = preview_url
        DeviceDocumentCRUD(db_session).update_by_id(device_document_id, {"filename": "test_document.doc"})
        response = client.get(
            f"{self._generate_device_document_endpoint(site_id, device_id, device_document_id)}/file-preview-url/",
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 400
        assert response.json()["message"] == samples.INVALID_PREVIEW_FILE_EXTENSION_ERR_MSG

    def test_get_preview_device_document_url_403(
        self, site_id, device_id, device_document_id, client, non_system_user_auth_header
    ):
        response = client.get(
            f"{self._generate_device_document_endpoint(site_id, device_id, device_document_id)}/file-preview-url/",
            headers=non_system_user_auth_header,
        )
        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"

    def test_get_preview_device_document_url_404(self, site_id, device_id, client, company_member_user_auth_header):
        response = client.get(
            f"{self._generate_device_document_endpoint(site_id, device_id, 1234)}/file-preview-url/",
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"
