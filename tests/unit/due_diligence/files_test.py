import pytest

import tests.unit.samples as samples
from app.crud.file import FileCRUD
from app.settings import settings
from app.static import FileMessages
from tests.utils import set_user_site_access


class TestFile:
    """Tests for due diligence requirements (files) routes."""

    @staticmethod
    def _generate_files_list_endpoint(site_id_, document_id_):
        """/api/due-diligence/SITE_ID/documents/DOCUMENT_ID/files"""
        return f"/api/due-diligence/{site_id_}/documents/{document_id_}/files"

    def _generate_file_endpoint(self, site_id_, document_id_, file_id):
        """/api/due-diligence/SITE_ID/documents/DOCUMENT_ID/files/FILE_ID"""
        return f"{self._generate_files_list_endpoint(site_id_, document_id_)}/{file_id}"

    def test_get_files_list(self, site_id, document, file, company_member_user_auth_header, client):
        """Test retrieving list of files for document."""
        response = client.get(
            self._generate_files_list_endpoint(site_id, document.id), headers=company_member_user_auth_header
        )
        files = [file for file in response.json()["items"] if file["filename"] == samples.TEST_FILE_NAME]
        assert response.status_code == 200
        assert len(files) == 1
        assert files[0]["filename"] == samples.TEST_FILE_NAME
        assert files[0]["extension"] == "pdf"
        assert files[0]["author"] == f"{samples.NON_SYSTEM_USER_NAME} {samples.NON_SYSTEM_USER_LAST_NAME}"

    def test_get_files_list_empty(self, db_session, site_id, document, file, company_member_user_auth_header, client):
        """Validate if `file.deleted` is set to True, this file doesn't appear in the list"""
        # adjust file removal status
        file.deleted = True
        db_session.commit()
        db_session.refresh(file)
        response = client.get(
            self._generate_files_list_endpoint(site_id, document.id), headers=company_member_user_auth_header
        )
        assert response.status_code == 200
        assert response.json()["items"] == []

    def test_get_files_list_403(self, site_id, document, file, non_system_user_auth_header, client):
        """Test retrieving list of files return 403."""
        response = client.get(
            self._generate_files_list_endpoint(site_id, document.id), headers=non_system_user_auth_header
        )
        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"

    def test_get_files_list_404(self, file, company_member_user_auth_header, client):
        """Test retrieving list of files return 404."""
        response = client.get(self._generate_files_list_endpoint(1234, 1234), headers=company_member_user_auth_header)
        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"

    def test_delete_file_403_no_access(self, site_id, document, file, non_system_user_auth_header, client):
        """Through 403 if access to the site wasn't given"""
        response = client.delete(
            self._generate_file_endpoint(site_id, document.id, file.id), headers=non_system_user_auth_header
        )
        assert response.status_code == 403

    def test_delete_file_403_scope_mismatch_site(
        self,
        document,
        site_lease_document,
        file,
        create_non_system_user,
        non_system_user_auth_header,
        client,
        mocker,
        db_session,
    ):
        """Through 403 if error in path values: user is trying to access file which is attached to different document
        than provided in the request"""
        logger_mock = mocker.patch("app.helpers.authorization.project_access.logger")
        set_user_site_access(db_session=db_session, user=create_non_system_user, site=site_lease_document.site)
        # patch user to bypass authorized document validation for this specific case
        create_non_system_user.is_system_user = True
        db_session.commit()

        # the 'file' fixture generates file for the document (Executive summary),
        # thus pass site_lease_document to the request path
        response = client.delete(
            self._generate_file_endpoint(site_lease_document.site.id, site_lease_document.id, file.id),
            headers=non_system_user_auth_header,
        )
        assert response.status_code == 403
        logger_mock.warning.assert_called_with(
            f"Scope mismatch! User {create_non_system_user.id} tried to access file {file.id} which attached to "
            "different document_id"
        )

    @pytest.mark.parametrize("sites", [2], indirect=True)
    def test_delete_file_403_scope_mismatch_document(
        self, client, sites, document, file, company_member_user_auth_header, company_member_user, mocker, db_session
    ):
        """Through 403 if error in path values: user is trying to access document which is attached to different site
        than provided in the request"""
        logger_mock = mocker.patch("app.helpers.authorization.project_access.logger")
        site2 = sites[1]
        set_user_site_access(db_session, site2, company_member_user)
        # the 'document' fixture returns first document for the site1, thus pass site2 to the request path
        response = client.delete(
            self._generate_file_endpoint(site2.id, document.id, file.id),
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 403
        logger_mock.warning.assert_called_with(
            f"Scope mismatch! User {company_member_user.id} tried to access document {document.id} which attached to "
            "different site_id"
        )

    def test_delete_file_404_site(self, site_id, document, file, company_member_user_auth_header, client, mocker):
        """Through 404 if site doesn't exist"""
        logger_mock = mocker.patch("app.helpers.authorization.project_access.logger")
        site_id = site_id + 1
        response = client.delete(
            self._generate_file_endpoint(site_id, document.id, file.id), headers=company_member_user_auth_header
        )
        assert response.status_code == 404
        logger_mock.warning.assert_called_with(f"There is no site with id {site_id}")

    def test_delete_file_404_document(self, site, file, company_member_user_auth_header, client, mocker):
        """Through 404 if document doesn't exist"""
        logger_mock = mocker.patch("app.helpers.authorization.project_access.logger")
        document_id = len(site.documents) + 1
        response = client.delete(
            self._generate_file_endpoint(site.id, document_id, file.id), headers=company_member_user_auth_header
        )
        assert response.status_code == 404
        logger_mock.warning.assert_called_with(f"There is no document with id {document_id}")

    def test_delete_file_404_file(self, site_id, document, file, company_member_user_auth_header, client, mocker):
        """Through 404 if file doesn't exist"""
        logger_mock = mocker.patch("app.helpers.authorization.project_access.logger")
        file_id = file.id + 1
        response = client.delete(
            self._generate_file_endpoint(site_id, document.id, file_id), headers=company_member_user_auth_header
        )
        assert response.status_code == 404
        logger_mock.warning.assert_called_with(f"There is no file with id {file_id}")

    def test_delete_file_success(self, db_session, file, company_member_user_auth_header, client, mocker):
        ai_server = mocker.patch("app.helpers.chatbot.files_sync.AIServerClient")
        # store file removal status before the API call to validate it's changed
        file_deleted_before_api = file.deleted
        response = client.delete(
            self._generate_file_endpoint(file.document.site.id, file.document.id, file.id),
            headers=company_member_user_auth_header,
        )
        db_session.refresh(file)
        file_deleted_after_api = file.deleted

        assert response.status_code == 200
        assert response.json()["message"] == "File has been successfully deleted"
        assert file_deleted_before_api is False
        assert file_deleted_after_api is True
        ai_server().post.assert_called_once_with(params={"file_id": file.id}, use_api_key=True)

    def test_get_download_url(self, site_id, document, mocker, client, file, system_user_auth_header):
        download_url = "https://storage.googleapis.com/"
        mocker.patch("app.helpers.files.file_handler.service_account")
        mock_storage = mocker.patch("app.helpers.files.file_handler.storage.Client")
        mock_storage.return_value.bucket.return_value.blob.return_value.generate_signed_url.return_value = download_url
        response = client.get(
            self._generate_file_endpoint(site_id, document.id, file.id), headers=system_user_auth_header
        )
        assert response.status_code == 200
        assert response.json()["download_url"] == download_url

    def test_get_download_url_404(self, site_id, document, client, system_user_auth_header):
        response = client.get(self._generate_file_endpoint(site_id, document.id, 1234), headers=system_user_auth_header)
        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"

    def test_get_download_url_403(self, site_id, document, file, client, non_system_user_auth_header):
        response = client.get(
            self._generate_file_endpoint(site_id, document.id, file.id), headers=non_system_user_auth_header
        )
        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"

    def test_get_upload_url(self, site, document, mocker, client, file, system_user_auth_header):
        upload_url = "https://storage.googleapis.com/upload"
        mocker.patch("app.helpers.files.file_handler.service_account")
        mock_storage = mocker.patch("app.helpers.files.file_handler.storage.Client")
        mock_storage.return_value.bucket.return_value.blob.return_value.generate_signed_url.return_value = upload_url
        response = client.post(
            f"{self._generate_files_list_endpoint(site.id, document.id)}/upload-url/",
            headers=system_user_auth_header,
            json={"filename": "analytics.pdf"},
        )
        assert response.status_code == 200
        assert response.json()["upload_url"] == upload_url

    def test_get_upload_url_404(self, site_id, document, client, system_user_auth_header):
        response = client.post(
            f"{self._generate_files_list_endpoint(site_id, 1234)}/upload-url/",
            headers=system_user_auth_header,
            json={"filename": "analytics.pdf"},
        )
        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"

    def test_get_upload_url_403(self, site_id, document, file, client, non_system_user_auth_header):
        response = client.post(
            f"{self._generate_files_list_endpoint(site_id, document.id)}/upload-url/",
            headers=non_system_user_auth_header,
            json={"filename": "analytics.pdf"},
        )
        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"

    def test_get_upload_url_w_wrong_extension(self, site_id, document, file, client, system_user_auth_header):
        filename = "analytics.xls"
        response = client.post(
            f"{self._generate_files_list_endpoint(site_id, document.id)}/upload-url/",
            headers=system_user_auth_header,
            json={"filename": filename},
        )
        assert response.status_code == 422
        assert (
            response.json()["message"]
            == f"File {filename} has invalid extension. Only {samples.ALLOWED_FILE_EXTENSIONS} are allowed"
        )

    def test_create_uploaded_file(self, site, document, file, client, system_user_auth_header, mocker):
        ai_server = mocker.patch("app.helpers.chatbot.files_sync.AIServerClient")
        uploaded_file_url = "companies/1/sites/1/documents/1/2024-2-5T11:00:12_file.pdf"
        uploaded_file_name = "O&M document pre-signed.pdf"
        response = client.post(
            f"{self._generate_files_list_endpoint(site.id, document.id)}/track-uploaded-file/",
            headers=system_user_auth_header,
            json={
                "filename": uploaded_file_name,
                "filepath": uploaded_file_url,
            },
        )
        assert response.status_code == 200
        assert response.json()["message"] == "File successfully uploaded"
        # check call to AI was made
        ai_server().post.assert_called_once_with(
            payload={
                "agreement_name": "Other",
                "company_id": site.company_id,
                "company_name": site.company.name,
                # tricky but works: we can specify newly added file ID as next to the known file ID
                "file_id": file.id + 1,
                "file_link": f"gs://{settings.due_diligence_gcs_bucket}/{uploaded_file_url}",
                "site_id": site.id,
                "site_name": site.name,
                "document_name": document.name.value,
                "file_name": uploaded_file_name,
                "section_name": "Executive Summary",
                "subsection_name": None,
            },
            use_api_key=True,
        )

    def test_create_uploaded_file_403(self, site_id, document, file, client, non_system_user_auth_header):
        response = client.post(
            f"{self._generate_files_list_endpoint(site_id, document.id)}/track-uploaded-file/",
            headers=non_system_user_auth_header,
            json={
                "filename": "analytics.pdf",
                "filepath": "companies/1/sites/1/documents/1/2024-2-5T11:00:12_file.pdf",
            },
        )
        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"

    def test_create_uploaded_file_404(self, site_id, document, file, client, system_user_auth_header):
        response = client.post(
            f"{self._generate_files_list_endpoint(site_id, 123224)}/track-uploaded-file/",
            headers=system_user_auth_header,
            json={
                "filename": "analytics.pdf",
                "filepath": "companies/1/sites/1/documents/1/2024-2-5T11:00:12_file.pdf",
            },
        )
        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"

    def test_create_uploaded_file_w_wrong_extension(self, site_id, document, file, client, system_user_auth_header):
        filename = "analytics.xls"
        response = client.post(
            f"{self._generate_files_list_endpoint(site_id, document.id)}/track-uploaded-file/",
            headers=system_user_auth_header,
            json={
                "filename": filename,
                "filepath": "companies/1/sites/1/documents/1/2024-2-5T11:00:12_file.pdf",
            },
        )
        assert response.status_code == 422
        assert (
            response.json()["message"]
            == f"File {filename} has invalid extension. Only {samples.ALLOWED_FILE_EXTENSIONS} are allowed"
        )

    def test_get_preview_file_url(self, site_id, document, file, client, system_user_auth_header, mocker):
        preview_url = "https://storage.googleapis.com/file.pdf"
        mocker.patch("app.helpers.files.file_handler.service_account")
        mock_storage = mocker.patch("app.helpers.files.file_handler.storage.Client")
        mock_storage.return_value.bucket.return_value.blob.return_value.generate_signed_url.return_value = preview_url
        response = client.get(
            f"{self._generate_file_endpoint(site_id, document.id, file.id)}/file-preview-url/",
            headers=system_user_auth_header,
        )
        assert response.status_code == 200
        assert response.json()["preview_url"] == preview_url

    def test_get_preview_file_url_non_pdf(
        self, site_id, document, file, client, system_user_auth_header, mocker, db_session
    ):
        preview_url = "https://storage.googleapis.com/file.pdf"
        mocker.patch("app.helpers.files.file_handler.service_account")
        mock_storage = mocker.patch("app.helpers.files.file_handler.storage.Client")
        mock_storage.return_value.bucket.return_value.blob.return_value.generate_signed_url.return_value = preview_url
        # update file not to be pdf
        FileCRUD(db_session).update_by_id(file.id, {"filename": "test_file.doc"})
        response = client.get(
            f"{self._generate_file_endpoint(site_id, document.id, file.id)}/file-preview-url/",
            headers=system_user_auth_header,
        )
        assert response.status_code == 400
        assert response.json()["message"] == samples.INVALID_PREVIEW_FILE_EXTENSION_ERR_MSG

    def test_get_preview_file_url_403(self, site_id, document, file, client, non_system_user_auth_header):
        response = client.get(
            f"{self._generate_file_endpoint(site_id, document.id, file.id)}/file-preview-url/",
            headers=non_system_user_auth_header,
        )
        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"

    def test_get_preview_file_url_404(self, site_id, document, file, client, system_user_auth_header):
        response = client.get(
            f"{self._generate_file_endpoint(site_id, document.id, 1234)}/file-preview-url/",
            headers=system_user_auth_header,
        )
        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"

    def test_update_file_is_actual(
        self, site_id, document, file, client, company_member_user_auth_header, db_session, mocker
    ):
        ai_server = mocker.patch("app.helpers.chatbot.files_sync.AIServerClient")
        assert file.is_actual is False
        response = client.put(
            f"{self._generate_file_endpoint(site_id, document.id, file.id)}/file-is-actual/",
            headers=company_member_user_auth_header,
            json={
                "is_actual": True,
            },
        )
        assert response.status_code == 202
        assert response.json()["message"] == FileMessages.file_actual_status_updated.value
        db_session.refresh(file)
        assert file.is_actual is True
        ai_server().post.assert_called_once_with(params={"file_id": file.id, "actual": "true"}, use_api_key=True)

    def test_update_file_is_actual_403(self, site_id, document, file, client, non_system_user_auth_header):
        response = client.put(
            f"{self._generate_file_endpoint(site_id, document.id, file.id)}/file-is-actual/",
            headers=non_system_user_auth_header,
        )
        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"

    def test_update_file_is_actual_404(self, site_id, document, file, client, system_user_auth_header):
        response = client.put(
            f"{self._generate_file_endpoint(site_id, document.id, 1234)}/file-is-actual/",
            headers=system_user_auth_header,
        )
        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"
