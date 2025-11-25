import logging

import pytest

from app.settings import settings
from tests.unit import samples


class TestMiddlewares:
    """Test custom middlewares in turned on/off states using login endpoint"""

    LOGIN_API_ENDPOINT = "/api/auth/login"

    @classmethod
    def setup_class(cls):
        """Dump settings which are supposed to be changes"""
        cls.enable_audit_logger = settings.enable_audit_logger
        cls.enable_requests_logger = settings.enable_requests_logger
        cls.requests_logger_max_response = settings.requests_logger_max_response

    @classmethod
    def teardown_class(cls):
        """Restore app settings after tests"""
        settings.enable_audit_logger = cls.enable_audit_logger
        settings.enable_requests_logger = cls.enable_requests_logger
        settings.requests_logger_max_response = cls.requests_logger_max_response

    @pytest.fixture(autouse=True)
    def mock_jwt_generator(self, mocker):
        mocker.patch("app.helpers.authentication.jwt.encode", return_value="test.jwt.value")

    def test_auditing_log_on(self, client, caplog):
        settings.enable_audit_logger = True
        caplog.set_level(logging.DEBUG)
        response = client.post(self.LOGIN_API_ENDPOINT, json=samples.LOGIN_PAYLOAD_VALID)

        audit_log_record_created = False
        for log in caplog.records:
            if "Added audit log record" in log.message:
                audit_log_record_created = True

        assert response.status_code == 200
        assert response.json() == {"access_token": "test.jwt.value", "token_type": "bearer"}
        assert audit_log_record_created

    def test_auditing_log_off(self, client, caplog):
        settings.enable_audit_logger = False
        caplog.set_level(logging.DEBUG)
        response = client.post(self.LOGIN_API_ENDPOINT, json=samples.LOGIN_PAYLOAD_VALID)

        audit_log_record_created = False
        for log in caplog.records:
            if "Added audit log record" in log.message:
                audit_log_record_created = True

        assert response.status_code == 200
        assert response.json() == {"access_token": "test.jwt.value", "token_type": "bearer"}
        assert audit_log_record_created is False

    def test_request_response_log_on(self, client, caplog):
        settings.enable_requests_logger = True
        settings.requests_logger_max_response = 10
        caplog.set_level(logging.DEBUG)
        response = client.post(self.LOGIN_API_ENDPOINT, json=samples.LOGIN_PAYLOAD_VALID)

        request_logged = False
        for log in caplog.records:
            # validate request data is printed, response data is shortened according to the settings
            if all(
                log_key in log.message
                for log_key in [
                    "{'request_method': 'POST', 'request_path': '/api/auth/login'",
                    f"'request_body': {samples.LOGIN_PAYLOAD_VALID}",
                    "'response_body': \"{'access_t[...]\", 'response_status_code': 200",
                ]
            ):
                request_logged = True

        assert response.status_code == 200
        assert response.json() == {"access_token": "test.jwt.value", "token_type": "bearer"}
        assert request_logged

    def test_request_response_log_off(self, client, caplog):
        settings.enable_requests_logger = False
        caplog.set_level(logging.DEBUG)
        response = client.post(self.LOGIN_API_ENDPOINT, json=samples.LOGIN_PAYLOAD_VALID)

        request_logged = False
        for log in caplog.records:
            if all(
                log_key in log.message
                for log_key in [
                    "{'request_method': 'POST', 'request_path': '/api/auth/login'",
                    f"'request_body': {samples.LOGIN_PAYLOAD_VALID}",
                ]
            ):
                request_logged = True

        assert response.status_code == 200
        assert response.json() == {"access_token": "test.jwt.value", "token_type": "bearer"}
        assert request_logged is False
