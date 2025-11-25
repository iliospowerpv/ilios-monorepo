import pytest

from app.crud.co_terminus_check import CoTerminusCheckCRUD
from app.models.file import FileParsingStatuses
from app.static import CoTerminusMessages
from tests.unit import samples


class TestCoTerminusCheck:

    @staticmethod
    def _generate_check_endpoint_with_suffix(site_id_, suffix):
        return f"/api/due-diligence/{site_id_}/co-terminus/{suffix}"

    def _generate_check_endpoint(self, site_id_):
        """/api/due-diligence/SITE_ID/co-terminus/check"""
        return self._generate_check_endpoint_with_suffix(site_id_, "check")

    def _generate_check_status_endpoint(self, site_id_):
        """/api/due-diligence/SITE_ID/co-terminus/status"""
        return self._generate_check_endpoint_with_suffix(site_id_, "status")

    def _generate_check_stop_endpoint(self, site_id_):
        """/api/due-diligence/SITE_ID/co-terminus/stop"""
        return self._generate_check_endpoint_with_suffix(site_id_, "stop")

    def test_init_check_404(self, client, company_member_user_auth_header):
        response = client.post(self._generate_check_endpoint(1234), headers=company_member_user_auth_header)
        assert response.status_code == 404

    def test_init_check_403(self, client, site_id, non_system_user_auth_header):
        response = client.post(self._generate_check_endpoint(site_id), headers=non_system_user_auth_header)
        assert response.status_code == 403

    def test_init_check_no_diligence_overview_access(
        self, client, site_id, company_member_user_auth_header, limit_role_dd_overview_access
    ):
        response = client.post(self._generate_check_endpoint(site_id), headers=company_member_user_auth_header)
        assert response.status_code == 403

    def test_init_check_success(self, client, site, company_member_user_auth_header, db_session):
        response = client.post(self._generate_check_endpoint(site.id), headers=company_member_user_auth_header)

        # refresh existing site object to validate check status
        db_session.refresh(site)

        assert response.status_code == 202
        assert response.json()["message"] == CoTerminusMessages.check_start_success.value
        # since with don't have any keys populated, it's expected check to be with completed status
        assert site.co_terminus_check.status == FileParsingStatuses.completed

    def test_init_check_conflicting_status(self, client, db_session, site_id, company_member_user_auth_header):
        # create check which is in progress to simulate the error
        CoTerminusCheckCRUD(db_session).create_item({"site_id": site_id, "status": FileParsingStatuses.processing})

        response = client.post(self._generate_check_endpoint(site_id), headers=company_member_user_auth_header)
        assert response.status_code == 409
        assert response.json()["message"] == CoTerminusMessages.check_is_running.value

    def test_get_check_status_403(self, client, site_id, non_system_user_auth_header):
        response = client.get(
            self._generate_check_status_endpoint(site_id),
            headers=non_system_user_auth_header,
        )
        assert response.status_code == 403

    def test_get_check_status_404(self, client, site_id, system_user_auth_header):
        response = client.get(
            self._generate_check_status_endpoint(1234),
            headers=system_user_auth_header,
        )
        assert response.status_code == 404

    def test_get_check_status_no_diligence_overview_access(
        self, client, site_id, company_member_user_auth_header, limit_role_dd_overview_access
    ):
        response = client.get(
            self._generate_check_status_endpoint(site_id),
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 403

    def test_get_check_status_success(self, client, site_id, company_member_user_auth_header):
        response = client.get(
            self._generate_check_status_endpoint(site_id),
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 200
        assert response.json() == {
            "status": FileParsingStatuses.not_started.value,
            "end_time": None,
            "start_time": None,
            "is_actual": True,
            "is_stuck": False,
            "duration": None,
        }

    def test_get_check_result_403(self, client, site_id, non_system_user_auth_header):
        response = client.get(
            self._generate_check_endpoint(site_id),
            headers=non_system_user_auth_header,
        )
        assert response.status_code == 403

    def test_get_check_result_404(self, client, site_id, system_user_auth_header):
        response = client.get(
            self._generate_check_endpoint(1234),
            headers=system_user_auth_header,
        )
        assert response.status_code == 404

    def test_get_check_result_no_diligence_overview_access(
        self, client, site_id, company_member_user_auth_header, limit_role_dd_overview_access
    ):
        response = client.get(
            self._generate_check_endpoint(site_id),
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 403

    @pytest.mark.parametrize(
        "populate_result,db_result_items,expected_response",
        (
            (False, [], samples.CO_TERM_RESULTS_EMPTY_RESPONSE),
            (
                True,
                samples.CO_TERM_RESULTS_SAMPLE,
                samples.CO_TERM_RESULTS_API_RESPONSE,
            ),
        ),
    )
    def test_get_check_result_success(
        self,
        client,
        site_id,
        company_member_user_auth_header,
        populate_result,
        db_result_items,
        expected_response,
        db_session,
        mocker,
    ):
        if populate_result:
            CoTerminusCheckCRUD(db_session).create_item(
                {"site_id": site_id, "status": "completed", "result": db_result_items}
            )
            mocker.patch("app.helpers.configs.base_config_helper.BaseConfigHandler.read").return_value = (
                samples.CO_TERM_CONFIG
            )
        response = client.get(
            self._generate_check_endpoint(site_id),
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 200
        assert response.json() == expected_response

    def test_check_stop_not_started(self, client, site_id, company_member_user_auth_header):
        """Validate API is not available if no co-term has been started."""
        response = client.get(
            self._generate_check_stop_endpoint(site_id),
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 404
        assert response.json()["message"] == CoTerminusMessages.check_is_not_started.value

    def test_check_stop_completed(self, client, db_session, site_id, company_member_user_auth_header, co_terminus_check):
        """Validate API is not available if no co-term is running right now."""
        # stop the execution
        co_terminus_check.status = FileParsingStatuses.completed
        db_session.commit()

        response = client.get(
            self._generate_check_stop_endpoint(site_id),
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 400
        assert response.json()["message"] == CoTerminusMessages.check_is_not_running.value

    def test_check_stop_success(self, client, site_id, company_member_user_auth_header, co_terminus_check):
        response = client.get(
            self._generate_check_stop_endpoint(site_id),
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 200
        assert response.json()["message"] == CoTerminusMessages.check_is_aborted.value
