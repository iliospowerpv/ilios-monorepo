from fastapi import HTTPException


class TestCameras:
    API_ENDPOINT = "/api/security/cameras"

    def test_get_potential_cameras_list(self, site, mocker, company_member_user_auth_header, client):
        rombus_client = mocker.patch("app.routers.security.cameras.RombusClient")
        rombus_client.return_value.get_cameras_list.return_value = [{"name": "BASE CAMERA", "uuid": "aaass123"}]

        response = client.get(self.API_ENDPOINT, headers=company_member_user_auth_header)
        assert response.status_code == 200
        assert response.json() == {"items": [{"name": "BASE CAMERA", "uuid": "aaass123"}]}

    def test_get_potential_cameras_list_rombus_err(self, site, mocker, company_member_user_auth_header, client):
        rombus_client = mocker.patch("app.routers.security.cameras.RombusClient")
        rombus_client.return_value.get_cameras_list.side_effect = HTTPException(403, "Forbidden")

        response = client.get(self.API_ENDPOINT, headers=company_member_user_auth_header)
        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"

    def test_get_potential_cameras_list_403(self, site, non_system_user_auth_header, client):
        response = client.get(self.API_ENDPOINT, headers=non_system_user_auth_header)
        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"
