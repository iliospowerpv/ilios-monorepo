from app.crud.site import SiteCRUD
from tests.unit import samples
from tests.utils import create_response


class TestSitesCameras:
    @staticmethod
    def _generate_list_endpoint(site_id):
        return f"/api/operations-and-maintenance/sites/{site_id}/cameras"

    @staticmethod
    def _generate_camera_overview_endpoint(site_id, camera_uuid):
        return f"/api/operations-and-maintenance/sites/{site_id}/cameras/{camera_uuid}"

    @staticmethod
    def _generate_alert_overview_endpoint(site_id, alert_uuid):
        return f"/api/operations-and-maintenance/sites/{site_id}/cameras/alerts/{alert_uuid}"

    def test_get_site_cameras(
        self,
        client,
        company_member_user_auth_header,
        site,
        db_session,
        mocker,
    ):
        """Test that get site cameras returns list of cameras attached to site."""
        location_name = "BASE CAMERA LOCATION"
        mock_requests = mocker.patch("app.helpers.security.rombus_client.requests.post")
        mock_requests.side_effect = [
            create_response(200, samples.TEST_ROMBUS_CAMERAS_RESPONSE),
            create_response(200, {"locations": [{"name": location_name, "uuid": samples.TEST_LOCATION_UUID}]}),
        ]
        SiteCRUD(db_session).update_by_id(site.id, {"cameras_uuids": [samples.TEST_CAMERA_UUID]})
        response = client.get(
            self._generate_list_endpoint(site.id),
            headers=company_member_user_auth_header,
        )
        response_json = response.json()["items"][0]

        assert response.status_code == 200
        assert response_json["uuid"] == samples.TEST_CAMERA_UUID
        assert response_json["name"] == samples.TEST_CAMERA_NAME
        assert response_json["location"] == location_name
        assert response_json["status"] == "GREEN"

    def test_get_site_cameras_rombus_error(
        self,
        client,
        company_member_user_auth_header,
        site_id,
        db_session,
        mocker,
    ):
        """Test that get site cameras handles Rombus errors correctly."""
        mock_requests = mocker.patch("app.helpers.security.rombus_client.requests.post")
        mock_requests.return_value = create_response(404, {"status": 404, "msg": "Rombus Error Message"})
        SiteCRUD(db_session).update_by_id(site_id, {"cameras_uuids": ["AADAD124"]})
        response = client.get(
            self._generate_list_endpoint(site_id),
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 404
        assert response.json()["message"] == "Rombus Error Message"

    def test_get_site_cameras_403(
        self,
        client,
        non_system_user_auth_header,
        site_id,
    ):
        """Test that get site cameras returns 403."""
        response = client.get(
            self._generate_list_endpoint(site_id),
            headers=non_system_user_auth_header,
        )
        assert response.status_code == 403

    def test_get_site_cameras_404(
        self,
        client,
        system_user_auth_header,
        site_id,
    ):
        """Test that get site cameras returns 404."""
        response = client.get(
            self._generate_list_endpoint(9999),
            headers=system_user_auth_header,
        )
        assert response.status_code == 404

    def test_get_site_camera_live_stream_url(
        self,
        client,
        company_member_user_auth_header,
        site,
        db_session,
        mocker,
    ):
        """Test that get site camera live stream url return Rombus stream url."""
        mock_requests = mocker.patch("app.helpers.security.rombus_client.requests.post")
        mock_requests.return_value = create_response(200, samples.TEST_ROMBUS_LIVESTREAM_RESPONSE)
        # Attach camera to site by uuid
        SiteCRUD(db_session).update_by_id(site.id, {"cameras_uuids": [samples.TEST_CAMERA_UUID]})
        response = client.get(
            f"{self._generate_camera_overview_endpoint(site.id, samples.TEST_CAMERA_UUID)}/livestream",
            headers=company_member_user_auth_header,
        )
        response_json = response.json()

        assert response.status_code == 200
        assert response_json["live_stream_url"] == samples.TEST_CAMERA_LIVESTREAM_URL

    def test_get_site_camera_live_stream_url_non_site_camera(
        self,
        client,
        company_member_user_auth_header,
        site,
        db_session,
        mocker,
    ):
        """Test that get site camera live stream url for camera not attached to site returns 404."""
        camera_uuid = "123AA"
        logger_mock = mocker.patch("app.routers.operations_and_maintenance.site_cameras.logger")
        response = client.get(
            f"{self._generate_camera_overview_endpoint(site.id, camera_uuid)}/livestream",
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 404
        logger_mock.warning.assert_called_with(f"Camera UUID: {camera_uuid} is not attached to site ID: {site.id}")

    def test_get_site_camera_live_stream_url_create_new_stream(
        self,
        client,
        company_member_user_auth_header,
        site,
        db_session,
        mocker,
    ):
        """Test that if camera stream not exist new stream is created in Rombus."""
        mock_requests = mocker.patch("app.helpers.security.rombus_client.requests.post")
        mock_requests.side_effect = [
            create_response(200, {"sharedLiveVideoStreams": {}}),
            create_response(200, {"sharedLiveVideoStreamUrl": samples.TEST_CAMERA_LIVESTREAM_URL}),
        ]
        # Attach camera to site by uuid
        SiteCRUD(db_session).update_by_id(site.id, {"cameras_uuids": [samples.TEST_CAMERA_UUID]})
        response = client.get(
            f"{self._generate_camera_overview_endpoint(site.id, samples.TEST_CAMERA_UUID)}/livestream",
            headers=company_member_user_auth_header,
        )
        response_json = response.json()

        assert response.status_code == 200
        assert response_json["live_stream_url"] == samples.TEST_CAMERA_LIVESTREAM_URL

    def test_get_site_camera_live_stream_url_403(
        self,
        client,
        non_system_user_auth_header,
        site_id,
    ):
        """Test that get site camera live stream returns 403."""
        response = client.get(
            self._generate_list_endpoint(site_id),
            headers=non_system_user_auth_header,
        )
        assert response.status_code == 403

    def test_get_site_cameras_alerts(
        self,
        client,
        company_member_user_auth_header,
        site,
        db_session,
        mocker,
    ):
        """Test that get site camera alerts list."""
        mock_requests = mocker.patch("app.helpers.security.rombus_client.requests.post")
        mock_requests.side_effect = [
            create_response(200, samples.TEST_ROMBUS_CAMERAS_RESPONSE),
            create_response(200, samples.TEST_ROMBUS_ALERTS_RESPONSE),
        ]
        # Attach camera to site by uuid
        SiteCRUD(db_session).update_by_id(site.id, {"cameras_uuids": [samples.TEST_CAMERA_UUID]})
        response = client.get(
            f"{self._generate_list_endpoint(site.id)}/alerts",
            headers=company_member_user_auth_header,
        )
        response_json = response.json()["items"][0]
        assert response.status_code == 200
        assert response_json["alert_uuid"] == samples.TEST_ALERT_UUID
        assert response_json["alert_type"] == "Human Movement"
        assert response_json["camera_name"] == "ROMBUS CAMERA"

    def test_get_site_cameras_alerts_403(
        self,
        client,
        non_system_user_auth_header,
        site_id,
    ):
        """Test that get site camera alerts list returns 403."""
        response = client.get(
            f"{self._generate_list_endpoint(site_id)}/alerts",
            headers=non_system_user_auth_header,
        )
        assert response.status_code == 403

    def test_get_camera_alert_shared_clip_url(
        self,
        client,
        company_member_user_auth_header,
        site,
        db_session,
        mocker,
    ):
        """Test that get site camera alert clip url returns Rombus url."""
        mock_requests = mocker.patch("app.helpers.security.rombus_client.requests.post")
        mock_requests.return_value = create_response(200, samples.TEST_ALERT_SHARED_CLIPS_RESPONSE)

        response = client.get(
            f"{self._generate_alert_overview_endpoint(site.id, samples.TEST_ALERT_UUID)}/shared-clip",
            headers=company_member_user_auth_header,
        )
        response_json = response.json()
        assert response.status_code == 200
        assert response_json["shared_clip_url"].endswith(samples.TEST_SHARED_CLIP_UUID)

    def test_get_camera_alert_shared_clip_url_create_new(
        self,
        client,
        company_member_user_auth_header,
        site,
        db_session,
        mocker,
    ):
        """Test that get site camera alert clip url creates new Rombus url if alert shared clip url not exists."""
        alert_clip_url = "http://clip-url"
        mock_requests = mocker.patch("app.helpers.security.rombus_client.requests.post")
        mock_requests.side_effect = [
            create_response(200, {}),
            create_response(200, {"shareUrl": alert_clip_url}),
        ]
        response = client.get(
            f"{self._generate_alert_overview_endpoint(site.id, samples.TEST_ALERT_UUID)}/shared-clip",
            headers=company_member_user_auth_header,
        )
        response_json = response.json()
        assert response.status_code == 200
        assert response_json["shared_clip_url"] == alert_clip_url

    def test_get_camera_alert_shared_clip_rombus_err(
        self,
        client,
        company_member_user_auth_header,
        site,
        mocker,
    ):
        """Test rombus call errors are properly handled"""
        mocker.patch(
            "app.helpers.security.rombus_client.requests.post",
            return_value=create_response(404, {"status": 500, "msg": "Test Error Message"}),
        )
        response = client.get(
            f"{self._generate_alert_overview_endpoint(site.id, samples.TEST_ALERT_UUID)}/shared-clip",
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 400
        assert response.json()["message"] == "Rombus call failed with an error: 500: Test Error Message"
