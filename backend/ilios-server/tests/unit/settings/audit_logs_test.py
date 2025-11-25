class TestAuditLog:
    API_ENDPOINT = "/api/settings/audit-logs"

    def test_audit_log_success(self, client, system_user_auth_header):
        """Validate system user is able to access audit logs page"""
        response = client.get(self.API_ENDPOINT, headers=system_user_auth_header)

        assert response.status_code == 200

    def test_audit_log_non_system_403(self, client, non_system_user_auth_header):
        """Validate non system user is not able to access audit logs page"""
        response = client.get(self.API_ENDPOINT, headers=non_system_user_auth_header)

        assert response.status_code == 403
