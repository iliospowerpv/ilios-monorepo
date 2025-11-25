import copy
import json
import os

from app.crud.file import FileCRUD
from app.settings import settings
from app.static import PermissionsModules


class TestFileParsing:
    @staticmethod
    def _generate_file_endpoint(site_id_, document_id_, file_id_):
        """/api/due-diligence/SITE_ID/documents/DOCUMENT_ID/files/FILE_ID/parsing"""
        return f"/api/due-diligence/{site_id_}/documents/{document_id_}/files/{file_id_}"

    def _generate_file_parsing_related_endpoint(self, site_id_, document_id_, file_id_, endpoint_suffix):
        return f"{self._generate_file_endpoint(site_id_, document_id_, file_id_)}/{endpoint_suffix}/"

    def _generate_files_parsing_status_endpoint(self, site_id_, document_id_, file_id_):
        """/api/due-diligence/SITE_ID/documents/DOCUMENT_ID/files/FILE_ID/parsing-status"""
        return self._generate_file_parsing_related_endpoint(site_id_, document_id_, file_id_, "parsing-status")

    def _generate_files_parsing_endpoint(self, site_id_, document_id_, file_id_):
        """/api/due-diligence/SITE_ID/documents/DOCUMENT_ID/files/FILE_ID/parsing"""
        return self._generate_file_parsing_related_endpoint(site_id_, document_id_, file_id_, "parsing")

    def _generate_files_parsing_result_endpoint(self, site_id_, document_id_, file_id_):
        """/api/due-diligence/SITE_ID/documents/DOCUMENT_ID/files/FILE_ID/parsing-result"""
        return self._generate_file_parsing_related_endpoint(site_id_, document_id_, file_id_, "parsing-result")

    @staticmethod
    def _generate_internal_files_endpoint(file_id):
        return f"/api/internal/files/{file_id}/parsing"

    @staticmethod
    def _generate_key_endpoint(site_id_, document_id_):
        """/api/due-diligence/SITE_ID/documents/DOCUMENT_ID/keys"""
        return f"/api/due-diligence/{site_id_}/documents/{document_id_}/keys"

    @staticmethod
    def _get_parsing_result():
        """Return payload from json"""
        json_file_path = os.path.join(os.path.dirname(__file__), "../unit/samples/site_lease_ai_response.json")
        with open(json_file_path) as file_sample:
            data = json.load(file_sample)
        return data

    def test_file_parsing_processing(
        self,
        client,
        db_session,
        site_id,
        site_lease_document,
        file,
        company_member_user_auth_header,
        mocker,
        response_200,
    ):
        """Check full file parsing flow, from the init to the results gathering"""
        mocker.patch("app.helpers.cloud_function_client.service_account.Credentials.from_service_account_file")
        mocker.patch("app.helpers.cloud_function_client.AuthorizedSession.post", return_value=response_200)
        # attach file to the site lease document
        FileCRUD(db_session).update_by_id(file.id, {"document_id": site_lease_document.id})
        expected_first_key = {
            "name": "Lessor (Landlord) Entity Name",
            "value": None,
            "ai_value": " Land lease agreement for solar project between Jared N. Connell and Nutting Ridge Solar LLC.",
            "is_poison_pill": True,
            "poison_pill": "Yes, rule was violated",
            "poison_pill_detailed": "The document appear to contain any text related to a 'Prevailing Party Provision' "
            "regarding attorneys\\' fees being awarded to the prevailing party in a dispute or litigation.",
            "updated_at": None,
            "legal_term": "```\nThis Land Lease Agreement For Solar Project (the “Agreement” or “Lease”) is made "
            "and\nentered into as of the Effective Date (as such term is hereinafter defined), by and "
            "between\nJARED N. CONNELL, an individual having a mailing address of 45 Palmer Way, Carlisle, MA\n01741 "
            "(“Owner”), and NUTTING RIDGE SOLAR LLC, a Maine limited liability company\nhaving a business address of "
            "P.O. Box 1320, Portsmouth, NH 03802 (“Tenant”). \n```",
            "comments": None,
            "id": None,
        }
        first_key_update = {"name": "Lessor (Landlord) Entity Name", "value": "This is manual input value"}
        expected_updated_first_key = copy.deepcopy(expected_first_key)
        expected_updated_first_key.update(first_key_update)
        del expected_updated_first_key["updated_at"]
        del expected_updated_first_key["id"]

        # step 1, no parsing is in progress
        parsing_status_not_started_response = client.get(
            self._generate_files_parsing_status_endpoint(site_id, site_lease_document.id, file.id),
            headers=company_member_user_auth_header,
        )

        # step 2, init parsing
        parsing_started_response = client.post(
            self._generate_files_parsing_endpoint(site_id, site_lease_document.id, file.id),
            headers=company_member_user_auth_header,
        )

        # step 3, parsing is in progress
        parsing_status_in_progress_response = client.get(
            self._generate_files_parsing_status_endpoint(site_id, site_lease_document.id, file.id),
            headers=company_member_user_auth_header,
        )
        parsing_result_in_progress_response = client.get(
            self._generate_files_parsing_result_endpoint(site_id, site_lease_document.id, file.id),
            headers=company_member_user_auth_header,
        )

        # step 4, parsing results stored, but parsing was failed
        save_parsing_failed_results_response = client.put(
            self._generate_internal_files_endpoint(file.latest_ai_result.id),
            params={"api_key": settings.api_key},
            json={
                "ai_app_version": "test",
                "ai_model_version": "test",
                "status": "Processing Failed",
                "result": [
                    {
                        "message": "Pipeline failed for provided file: 10. ",
                        "error": "Error: Unsupported file format: 2024-07-11T09%3A48%3A03_Site%20Lease%20-%20GLD%20",
                    }
                ],
            },
        )
        parsing_status_processing_failed_response = client.get(
            self._generate_files_parsing_status_endpoint(site_id, site_lease_document.id, file.id),
            headers=company_member_user_auth_header,
        )
        parsing_result_processing_failed_response = client.get(
            self._generate_files_parsing_result_endpoint(site_id, site_lease_document.id, file.id),
            headers=company_member_user_auth_header,
        )

        # step 5, parsing results stored, parsing was completed fine
        save_parsing_results_success_response = client.put(
            self._generate_internal_files_endpoint(file.latest_ai_result.id),
            params={"api_key": settings.api_key},
            json=self._get_parsing_result(),
        )
        parsing_status_completed_response = client.get(
            self._generate_files_parsing_status_endpoint(site_id, site_lease_document.id, file.id),
            headers=company_member_user_auth_header,
        )
        parsing_status_completed_response_json = parsing_status_completed_response.json()

        # step 6, parsing result can be retrieved without errors
        parsing_result_completed_response = client.get(
            self._generate_files_parsing_result_endpoint(site_id, site_lease_document.id, file.id),
            headers=company_member_user_auth_header,
        )

        # step 7, user can set the key value
        update_key_response = client.put(
            self._generate_key_endpoint(site_id, site_lease_document.id),
            headers=company_member_user_auth_header,
            json=first_key_update,
        )

        # step 8, retrieve parsing results together with the user input
        parsing_result_updated_response = client.get(
            self._generate_files_parsing_result_endpoint(site_id, site_lease_document.id, file.id),
            headers=company_member_user_auth_header,
        )
        key0 = parsing_result_updated_response.json()["keys"][0]
        # remove datetime value to not play with freezetime utility, it's not quite important in this case
        del key0["updated_at"]
        # save id to make comments
        key0_id = key0.pop("id")

        # step 9, leave comments on the key and re-retrieve the list
        for comment_index in range(3):
            comment_text = f"Comment #{comment_index}"
            client.post(
                url="/api/comments",
                headers=company_member_user_auth_header,
                json={
                    "entity_type": "document_key",
                    "entity_id": key0_id,
                    "text": comment_text,
                },
                params={"permission_module": PermissionsModules.diligence.value},
            )
        parsing_result_with_comments_response = client.get(
            self._generate_files_parsing_result_endpoint(site_id, site_lease_document.id, file.id),
            headers=company_member_user_auth_header,
        )
        key0_with_comments = parsing_result_with_comments_response.json()["keys"][0]
        key0_comments = key0_with_comments["comments"]

        assert parsing_status_not_started_response.status_code == 200
        assert parsing_status_not_started_response.json() == {
            "status": "Not Started",
            "end_time": None,
            "start_time": None,
        }
        assert parsing_started_response.status_code == 202
        assert parsing_started_response.json()["message"] == "Parsing has been started"
        assert parsing_status_in_progress_response.json()["status"] == "Processing"
        assert save_parsing_failed_results_response.status_code == 202
        assert save_parsing_failed_results_response.json()["message"] == "File parsing results has been stored"
        assert parsing_status_processing_failed_response.status_code == 200
        assert parsing_status_processing_failed_response.json()["status"] == "Processing Failed"
        assert parsing_result_processing_failed_response.status_code == 200
        assert save_parsing_results_success_response.status_code == 202
        assert save_parsing_results_success_response.json()["message"] == "File parsing results has been stored"
        assert parsing_status_completed_response_json["status"] == "Completed"
        assert parsing_status_completed_response_json["start_time"] is not None
        assert parsing_status_completed_response_json["end_time"] is not None
        assert parsing_status_completed_response_json["start_time"] != parsing_status_completed_response_json["end_time"]
        assert parsing_result_in_progress_response.status_code == 200
        assert parsing_result_completed_response.status_code == 200
        assert len(parsing_result_completed_response.json()["keys"]) > 0
        assert parsing_result_completed_response.json()["keys"][0] == expected_first_key
        assert update_key_response.status_code == 202
        assert key0 == expected_updated_first_key
        assert parsing_result_with_comments_response.status_code == 200
        assert len(key0_comments) == 3
        assert key0_comments[0]["created_at"] > key0_comments[-1]["created_at"]
