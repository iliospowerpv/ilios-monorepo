from app.static import ChatBotMessages
from tests.utils import create_response
from tests.unit import samples


class TestChatBot:

    @staticmethod
    def _generate_chatbot_endpoint(site_id_):
        """/api/due-diligence/chatbot/SITE_ID/session-token"""
        return f"/api/due-diligence/chatbot/{site_id_}/session-token"

    def test_get_chatbot_session_token_success(
        self, db_session, site_id, company_member_user_auth_header, client, mocker
    ):
        ai_client_mock = mocker.patch("app.helpers.chatbot.session_maker.AIServerClient")
        ai_client_mock().post.return_value = create_response(200, samples.CHATBOT_RESPONSE_200_BODY)
        response = client.get(
            self._generate_chatbot_endpoint(site_id),
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 200
        assert response.json() == samples.CHATBOT_RESPONSE_200_BODY

    def test_get_chatbot_session_token_403(self, db_session, site_id, non_system_user_auth_header, client):
        response = client.get(
            self._generate_chatbot_endpoint(site_id),
            headers=non_system_user_auth_header,
        )
        assert response.status_code == 403

    def test_get_chatbot_session_token_404(self, db_session, system_user_auth_header, client):
        response = client.get(
            self._generate_chatbot_endpoint(9999),
            headers=system_user_auth_header,
        )
        assert response.status_code == 404

    def test_get_chatbot_session_token_ai_call_error(
        self, db_session, site_id, company_member_user_auth_header, client, mocker
    ):
        ai_client_mock = mocker.patch("app.helpers.chatbot.session_maker.AIServerClient")
        ai_client_mock().post.return_value = create_response(400, "Error")
        response = client.get(
            self._generate_chatbot_endpoint(site_id),
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 400
        assert response.json()["message"] == ChatBotMessages.ai_api_error.value
