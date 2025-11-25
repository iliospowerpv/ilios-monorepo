import random
from datetime import datetime, timezone

from app.crud.ai_parsing_result import AIParsingResultCRUD
from app.crud.file import FileCRUD
from app.helpers.files.file_helper import combine_user_ai_parsing_results
from app.models.file import AIParsingResult, FileParsingStatuses


class TestFileAIIntegration:
    """Tests for interfaces related to the AI integration"""

    @staticmethod
    def _generate_file_endpoint(site_id_, document_id_, file_id_):
        """/api/due-diligence/SITE_ID/documents/DOCUMENT_ID/files/FILE_ID/parsing"""
        return f"/api/due-diligence/{site_id_}/documents/{document_id_}/files/{file_id_}"

    def _generate_file_parsing_related_endpoint(self, site_id_, document_id_, file_id_, endpoint_suffix):
        return f"{self._generate_file_endpoint(site_id_, document_id_, file_id_)}/{endpoint_suffix}"

    def _generate_files_parsing_endpoint(self, site_id_, document_id_, file_id_):
        """/api/due-diligence/SITE_ID/documents/DOCUMENT_ID/files/FILE_ID/parsing"""
        return self._generate_file_parsing_related_endpoint(site_id_, document_id_, file_id_, "parsing")

    def _generate_files_parsing_status_endpoint(self, site_id_, document_id_, file_id_):
        """/api/due-diligence/SITE_ID/documents/DOCUMENT_ID/files/FILE_ID/parsing-status"""
        return self._generate_file_parsing_related_endpoint(site_id_, document_id_, file_id_, "parsing-status")

    def _generate_files_parsing_result_endpoint(self, site_id_, document_id_, file_id_):
        """/api/due-diligence/SITE_ID/documents/DOCUMENT_ID/files/FILE_ID/parsing-result"""
        return self._generate_file_parsing_related_endpoint(site_id_, document_id_, file_id_, "parsing-result")

    def test_parse_started(
        self, site_id, site_lease_document, file, client, company_member_user_auth_header, mocker, db_session
    ):
        mocker.patch("app.routers.due_diligence.files_parsing.FileParseFuncHTTPClient")
        FileCRUD(db_session).update_by_id(file.id, {"document_id": site_lease_document.id})
        response = client.post(
            self._generate_files_parsing_endpoint(site_id, site_lease_document.id, file.id),
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 202
        assert response.json()["message"] == "Parsing has been started"

        db_session.refresh(file)  # re-fetch affected file row
        assert file.latest_ai_result.status == FileParsingStatuses.processing

        now, parsing_start_time = datetime.now(timezone.utc), file.latest_ai_result.start_time
        assert parsing_start_time.day == now.day
        assert parsing_start_time.month == now.month

    def test_file_for_parse_not_found(self, site_id, document, client, company_member_user_auth_header):
        response = client.post(
            self._generate_files_parsing_endpoint(site_id, document.id, 9999999),
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"

    def test_parse_for_unauthorized_user(self, site_id, document, file, client, non_system_user_auth_header):
        response = client.post(
            self._generate_files_parsing_endpoint(site_id, document.id, file.id),
            headers=non_system_user_auth_header,
        )

        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"

    def test_parse_conflict(
        self, site_id, site_lease_document, file, client, company_member_user_auth_header, db_session
    ):
        FileCRUD(db_session).update_by_id(file.id, {"document_id": site_lease_document.id})
        AIParsingResultCRUD(db_session).create_item({"file_id": file.id, "status": FileParsingStatuses.processing})

        response = client.post(
            self._generate_files_parsing_endpoint(site_id, site_lease_document.id, file.id),
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 409
        assert response.json()["message"] == "There is already parse processing started for file"

    def test_parse_func_failed(
        self,
        site_id,
        site_lease_document,
        file,
        client,
        company_member_user_auth_header,
        mocker,
        response_400,
        db_session,
    ):
        FileCRUD(db_session).update_by_id(file.id, {"document_id": site_lease_document.id})
        mocker.patch("app.helpers.cloud_function_client.service_account.Credentials.from_service_account_file")
        mocker.patch("app.helpers.cloud_function_client.AuthorizedSession.post", return_value=response_400)

        response = client.post(
            self._generate_files_parsing_endpoint(site_id, site_lease_document.id, file.id),
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 400
        assert (
            response.json()["message"] == "An error occurred during file AI processing: 400: Bad request custom reason"
        )

        db_session.refresh(file)  # re-fetch affected file row
        assert file.latest_ai_result.status == FileParsingStatuses.processing_start_failed

        now, parsing_end_time = datetime.now(timezone.utc), file.latest_ai_result.end_time
        assert parsing_end_time.day == now.day
        assert parsing_end_time.month == now.month

    def test_parse_func_wrong_document_type(
        self, site_id, document, file, client, company_member_user_auth_header, response_400, db_session
    ):
        """Ensure executive summary parsing is not allowed"""
        response = client.post(
            self._generate_files_parsing_endpoint(site_id, document.id, file.id),
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 400
        assert response.json()["message"] == "Parsing feature is not available for the <Executive Summary> files"

    def test_parse_func_wrong_file_type(
        self, site_id, site_lease_document, file, client, company_member_user_auth_header, response_400, db_session
    ):
        """Ensure parsing is not allowed for jpeg file"""
        FileCRUD(db_session).update_by_id(file.id, {"filename": "image.jpeg", "document_id": site_lease_document.id})
        response = client.post(
            self._generate_files_parsing_endpoint(site_id, site_lease_document.id, file.id),
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 400
        assert (
            response.json()["message"]
            == "Parsing feature is not available for the <jpeg> file type. Allowed file types: <pdf,docx>"
        )

    def test_get_file_parsing_status(self, site_id, document, file, client, company_member_user_auth_header):
        response = client.get(
            self._generate_files_parsing_status_endpoint(site_id, document.id, file.id),
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 200
        assert response.json() == {"status": "Not Started", "end_time": None, "start_time": None}

    def test_get_file_parsing_status_403(self, site_id, document, file, client, non_system_user_auth_header):
        response = client.get(
            self._generate_files_parsing_status_endpoint(site_id, document.id, file.id),
            headers=non_system_user_auth_header,
        )
        assert response.status_code == 403

    def test_get_file_parsing_status_404(self, site_id, document, client, system_user_auth_header):
        response = client.get(
            self._generate_files_parsing_status_endpoint(site_id, document.id, 999),
            headers=system_user_auth_header,
        )
        assert response.status_code == 404

    def test_get_parsing_results(
        self, site_id, site_lease_document, client, company_member_user_auth_header, file, db_session
    ):
        FileCRUD(db_session).update_by_id(file.id, {"document_id": site_lease_document.id})
        response = client.get(
            self._generate_files_parsing_result_endpoint(site_id, site_lease_document.id, file.id),
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 200
        assert response.json()["keys"] == combine_user_ai_parsing_results(
            document=site_lease_document, db_session=db_session, due_diligence_file=file
        )

    def test_get_parsing_results_keys_ordering(
        self, site_id, site_lease_document, client, company_member_user_auth_header, file, db_session
    ):
        FileCRUD(db_session).update_by_id(file.id, {"document_id": site_lease_document.id})

        response_before_update = client.get(
            self._generate_files_parsing_result_endpoint(site_id, site_lease_document.id, file.id),
            headers=company_member_user_auth_header,
        )
        keys_order_before_update = [key["name"] for key in response_before_update.json()["keys"]]
        assert response_before_update.status_code == 200
        assert response_before_update.json()["keys"] == combine_user_ai_parsing_results(
            document=site_lease_document, db_session=db_session, due_diligence_file=file
        )

        put_response = client.put(
            f"/api/due-diligence/{site_id}/documents/{site_lease_document.id}/keys",
            headers=company_member_user_auth_header,
            json={"name": "Quiet Enjoyment", "value": "Test"},
        )
        assert put_response.status_code == 202

        response_after_update = client.get(
            self._generate_files_parsing_result_endpoint(site_id, site_lease_document.id, file.id),
            headers=company_member_user_auth_header,
        )
        # check keys are in the same order as before the update
        assert [key["name"] for key in response_after_update.json()["keys"]] == keys_order_before_update

    def test_get_parsing_results_403(self, site_id, document, client, non_system_user_auth_header, file, db_session):
        response = client.get(
            self._generate_files_parsing_result_endpoint(site_id, document.id, file.id),
            headers=non_system_user_auth_header,
        )
        assert response.status_code == 403

    def test_get_parsing_results_404(self, site_id, document, client, system_user_auth_header, db_session):
        response = client.get(
            self._generate_files_parsing_result_endpoint(site_id, document.id, 999),
            headers=system_user_auth_header,
        )
        assert response.status_code == 404

    def test_parsing_results_ordering(
        self, db_session, site_id, document, file, client, company_member_user_auth_header
    ):
        """Validate the very last parsing result item is treated as the actual one,
        https://softserve-jirasw.atlassian.net/browse/IOSP1-1570"""
        # create several parsing result items
        for _ in range(10):
            file.ai_parsing_results.append(
                AIParsingResult(**{"file_id": file.id, "status": random.choice(list(FileParsingStatuses))})
            )
        db_session.commit()
        db_session.refresh(file)
        file_parsing_results_ids = [result.id for result in file.ai_parsing_results]

        response = client.get(
            self._generate_files_parsing_status_endpoint(site_id, document.id, file.id),
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 200
        assert sorted(file_parsing_results_ids, reverse=True) == file_parsing_results_ids
        assert file.latest_ai_result.id == file_parsing_results_ids[0]
