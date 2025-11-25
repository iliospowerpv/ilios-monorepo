import time
from unittest.mock import ANY

import pytest

from app.crud.document_key import DocumentKeyCRUD
from app.models.file import FileParsingStatuses
from app.settings import settings
from app.static.default_site_documents_enum import SiteDocumentsEnum
from tests.unit import samples
from tests.utils import get_document_by_name, set_user_site_access


class TestCoTerminusProcess:
    """End-to-end co-terminus check.

    * For the init check call, validate all statuses of comparison are processed:
        1. keys matched
        2. one of key for comparison is null
        3. all the keys are null, or empty string, or string with spaces
        4. keys are populated, they are different and co-term check is passed for AI processing

    * For the init check call, handle the case if all values were compared on our BE and call to AI isn't needed

    * For the save result call, validate Pending items statuses changed based on the execution status:
        1. If failed: pending -> error
        2. If completed: statuses updated based on the request input
    """

    @staticmethod
    def _generate_check_endpoint(site_id_):
        return f"/api/due-diligence/{site_id_}/co-terminus/check"

    @staticmethod
    def _generate_key_endpoint(site_id_, document_id_):
        return f"/api/due-diligence/{site_id_}/documents/{document_id_}/keys"

    @staticmethod
    def _generate_status_endpoint(site_id_):
        return f"/api/due-diligence/{site_id_}/co-terminus/status"

    @staticmethod
    def _generate_stop_endpoint(site_id_):
        return f"/api/due-diligence/{site_id_}/co-terminus/stop"

    @staticmethod
    def _generate_result_endpoint(check_id_):
        return f"/api/internal/co-terminus-checks/{check_id_}/results"

    @pytest.fixture(autouse=True)
    def setup_method(self, db_session, api_site, company_member_user, mocker):
        """Common for all tests - provide user access to the site and setup keys"""
        set_user_site_access(db_session, api_site, company_member_user)

        # NOTE! These keys are tied to the 'test_document_name_section_mapper' keys
        mocker.patch(
            "app.routers.due_diligence.co_terminus.CoTerminusHandler.read", return_value=samples.CO_TERM_CONFIG_MOCK
        )

        # populate keys for the documents we need for the co-term config
        site_lease_doc = get_document_by_name(api_site.documents, SiteDocumentsEnum.site_lease)
        ppa_and_amendments_doc = get_document_by_name(api_site.documents, SiteDocumentsEnum.ppa_and_amendments)
        checking_keys = [
            # scenario 1 - keys are matching
            {"document_id": site_lease_doc.id, "name": "Initial Term", "value": "Matching Value"},
            {"document_id": ppa_and_amendments_doc.id, "name": "Term", "value": "matching VALUE"},
            # scenario 2 - keys are different
            {"document_id": site_lease_doc.id, "name": samples.RENEWAL_TERMS_KEY, "value": "Value 1"},
            {"document_id": ppa_and_amendments_doc.id, "name": samples.RENEWAL_TERMS_KEY, "value": "Value 2"},
            # scenario 3 - one of keys is missing - do not create item for ppa_and_amendments
            {"document_id": site_lease_doc.id, "name": samples.MCD_KEY, "value": "Yesterday"},
            # scenario 4 - keys represents different states of empty value - do not create value for ppa_and_amendments
            {"document_id": site_lease_doc.id, "name": "Nameplate Capacity (System Size)", "value": "   "},
        ]
        DocumentKeyCRUD(db_session).create_items(checking_keys)

    def test_co_terminus_full_process(
        self, client, api_site, company_member_user_auth_header, mocker, response_400, response_200
    ):
        """Happy path of the flow: partially handled by our BE, rest of the items covered by the AI successfully"""

        # call status and result endpoint before processing
        not_started_processing_status_response = client.get(
            self._generate_status_endpoint(api_site.id), headers=company_member_user_auth_header
        )
        not_started_processing_status_response_json = not_started_processing_status_response.json()
        results_before_processing_response = client.get(
            self._generate_check_endpoint(api_site.id), headers=company_member_user_auth_header
        )

        # On the 1st iteration, GCP returns error
        mocker.patch("app.helpers.cloud_function_client.service_account.Credentials.from_service_account_file")
        mocker.patch("app.helpers.cloud_function_client.google.oauth2.id_token.fetch_id_token")
        mocker.patch("app.helpers.cloud_function_client.requests.post", return_value=response_400)
        init_failed_response = client.post(
            self._generate_check_endpoint(api_site.id), headers=company_member_user_auth_header
        )
        init_failed_status_response = client.get(
            self._generate_status_endpoint(api_site.id), headers=company_member_user_auth_header
        )
        init_failed_status_response_json = init_failed_status_response.json()

        # Then, AI call is successful
        mocker.patch("app.helpers.cloud_function_client.requests.post", return_value=response_200)

        # partial processing - some values processed by our BE, some sent to the AI processing
        init_success_response = client.post(
            self._generate_check_endpoint(api_site.id), headers=company_member_user_auth_header
        )
        partial_processing_status_response = client.get(
            self._generate_status_endpoint(api_site.id), headers=company_member_user_auth_header
        )
        partial_processing_status_response_json = partial_processing_status_response.json()
        partial_results_response = client.get(
            self._generate_check_endpoint(api_site.id), headers=company_member_user_auth_header
        )

        # complete processing by setting results by the AI response
        set_results_response = client.patch(
            self._generate_result_endpoint(api_site.co_terminus_check.id),
            params={"api_key": settings.api_key},
            json=samples.CO_TERM_UPDATE_RESULT_SUCCESS_PAYLOAD,
        )
        completed_processing_status_response = client.get(
            self._generate_status_endpoint(api_site.id), headers=company_member_user_auth_header
        )
        completed_processing_status_response_json = completed_processing_status_response.json()
        completed_results_response = client.get(
            self._generate_check_endpoint(api_site.id), headers=company_member_user_auth_header
        )

        # change the value of the key, used in the co-term check, to make the results not actual:
        # change Site lease key which was before
        site_lease_doc = get_document_by_name(api_site.documents, SiteDocumentsEnum.site_lease)
        update_key_response = client.put(
            self._generate_key_endpoint(api_site.id, site_lease_doc.id),
            headers=company_member_user_auth_header,
            json={"name": samples.RENEWAL_TERMS_KEY, "value": "Test"},
        )
        processing_status_after_key_change_response = client.get(
            self._generate_status_endpoint(api_site.id), headers=company_member_user_auth_header
        )
        processing_status_after_key_change_response_json = processing_status_after_key_change_response.json()

        # then, restart processing and check the co-term check became actual again
        restart_check_response = client.post(
            self._generate_check_endpoint(api_site.id), headers=company_member_user_auth_header
        )
        processing_status_reset_response = client.get(
            self._generate_status_endpoint(api_site.id), headers=company_member_user_auth_header
        )
        processing_status_reset_response_json = processing_status_reset_response.json()

        assert results_before_processing_response.json() == samples.CO_TERM_RESULTS_EMPTY_RESPONSE
        assert init_success_response.status_code == 202
        # validate details before the processing
        assert not_started_processing_status_response_json["status"] == FileParsingStatuses.not_started.value
        assert not_started_processing_status_response_json["start_time"] is None
        assert not_started_processing_status_response_json["end_time"] is None
        assert not_started_processing_status_response_json["is_actual"] is True
        # validate details if AI init failed
        assert init_failed_response.status_code == 400
        assert init_failed_status_response_json["status"] == FileParsingStatuses.processing_start_failed.value
        assert init_failed_status_response_json["start_time"] is not None
        assert init_failed_status_response_json["end_time"] is not None
        assert init_failed_status_response_json["is_actual"] is True
        # validate details of partial processing, where some values require AI processing
        assert partial_processing_status_response_json["status"] == FileParsingStatuses.processing.value
        assert partial_processing_status_response_json["start_time"] is not None
        assert partial_processing_status_response_json["end_time"] is None
        assert partial_processing_status_response_json["is_actual"] is True
        assert partial_results_response.json() == samples.CO_TERM_PARTIAL_RESULT_RESPONSE
        # validate details of completed processing
        assert set_results_response.status_code == 202
        assert completed_processing_status_response_json["status"] == FileParsingStatuses.completed.value
        assert completed_processing_status_response_json["start_time"] is not None
        assert completed_processing_status_response_json["end_time"] is not None
        assert completed_processing_status_response_json["is_actual"] is True
        assert completed_results_response.json() == samples.CO_TERM_COMPLETED_RESULT_SUCCESS_RESPONSE
        # validate change of the status endpoint after one of source keys were changed
        assert update_key_response.status_code == 202
        assert processing_status_after_key_change_response_json["status"] == FileParsingStatuses.completed.value
        assert processing_status_after_key_change_response_json["is_actual"] is False
        # validate change of status endpoint after check restart
        assert restart_check_response.status_code == 202
        assert processing_status_reset_response_json["status"] == FileParsingStatuses.processing.value
        assert processing_status_reset_response_json["start_time"] is not None
        assert processing_status_reset_response_json["end_time"] is None
        assert processing_status_reset_response_json["is_actual"] is True

    def test_co_terminus_process_completed_by_backend(self, client, api_site, company_member_user_auth_header):
        """All values processed by our BE"""
        ppa_and_amendments_doc = get_document_by_name(api_site.documents, SiteDocumentsEnum.ppa_and_amendments)
        # set key, which represents different scenarios in the setu fixture, to be matching as well
        client.put(
            self._generate_key_endpoint(api_site.id, ppa_and_amendments_doc.id),
            headers=company_member_user_auth_header,
            json={"name": samples.RENEWAL_TERMS_KEY, "value": "Value 1"},
        )
        client.post(self._generate_check_endpoint(api_site.id), headers=company_member_user_auth_header)
        status_response = client.get(
            self._generate_status_endpoint(api_site.id), headers=company_member_user_auth_header
        )
        status_response_json = status_response.json()

        results_response = client.get(
            self._generate_check_endpoint(api_site.id), headers=company_member_user_auth_header
        )

        assert status_response_json["status"] == FileParsingStatuses.completed.value
        assert status_response_json["start_time"] is not None
        assert status_response_json["end_time"] is not None
        assert status_response_json["is_actual"] is True
        assert results_response.json() == samples.CO_TERM_BE_COMPLETED_RESULT_RESPONSE

    def test_co_terminus_process_failed_by_ai(self, client, api_site, company_member_user_auth_header, mocker):
        """AI returns error results"""
        # do not utilize the GCP CF client at all
        mocker.patch("app.routers.due_diligence.co_terminus.AIServerClient")
        init_response = client.post(self._generate_check_endpoint(api_site.id), headers=company_member_user_auth_header)
        set_results_response = client.patch(
            self._generate_result_endpoint(api_site.co_terminus_check.id),
            params={"api_key": settings.api_key},
            json=samples.CO_TERM_UPDATE_RESULT_ERROR_PAYLOAD,
        )
        status_response = client.get(
            self._generate_status_endpoint(api_site.id), headers=company_member_user_auth_header
        )
        results_response = client.get(
            self._generate_check_endpoint(api_site.id), headers=company_member_user_auth_header
        )

        assert init_response.status_code == 202
        assert status_response.json()["status"] == FileParsingStatuses.processing_failed.value
        assert set_results_response.status_code == 202
        assert results_response.json() == samples.CO_TERM_COMPLETED_RESULT_ERROR_RESPONSE

    def test_co_terminus_process_stuck(
        self, client, site, company_member_user_auth_header, monkeypatch, co_terminus_check
    ):
        """1. Start process,
        2. Validate status is running
        3. Sleep and change stuck threshold
        4. Validate status is running and process stuck
        5. Stop the execution
        6. Validate status is stopped"""
        # check processing is running, regular flow
        process_running_response = client.get(
            self._generate_status_endpoint(site.id), headers=company_member_user_auth_header
        ).json()

        # push process to stuck
        # update co_terminus_stuck_threshold to be lower to identify stuck faster
        monkeypatch.setattr(settings, "co_terminus_stuck_threshold", 2)
        # sleep for few seconds to have not-null duration
        duration_seconds = 3
        time.sleep(duration_seconds)
        process_stuck_response = client.get(
            self._generate_status_endpoint(site.id), headers=company_member_user_auth_header
        ).json()

        # stop the processing
        stop_response = client.get(self._generate_stop_endpoint(site.id), headers=company_member_user_auth_header)
        process_aborted_response = client.get(
            self._generate_status_endpoint(site.id), headers=company_member_user_auth_header
        ).json()

        assert process_running_response == {
            "status": FileParsingStatuses.processing.value,
            "end_time": None,
            "start_time": ANY,
            "is_actual": True,
            "is_stuck": False,
            "duration": ANY,
        }
        assert process_running_response["start_time"] is not None
        assert process_running_response["duration"] is not None
        assert process_stuck_response == {
            "status": FileParsingStatuses.processing.value,
            "end_time": None,
            "start_time": ANY,
            "is_actual": True,
            "is_stuck": True,
            "duration": ANY,
        }
        assert process_stuck_response["start_time"] is not None
        assert process_stuck_response["duration"] >= duration_seconds
        assert stop_response.status_code == 200
        assert process_aborted_response == {
            "status": FileParsingStatuses.processing_timeout.value,
            "end_time": ANY,
            "start_time": ANY,
            "is_actual": True,
            "is_stuck": False,
            "duration": None,
        }
        assert process_aborted_response["start_time"] is not None
        assert process_aborted_response["end_time"] is not None
