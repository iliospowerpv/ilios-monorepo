"""Finance Integration v1: Authorization Tests.

Tests verify that finance integration endpoints enforce:
1. company_admin role requirement
2. Finance module edit permission requirement

Uses real DB grants and the canonical resolver (no mocking of resolve_effective_access).
Does NOT reference Settings module - finance integrations use Finance:edit permission.
"""

import pytest
from unittest.mock import Mock

from app.crud.company import CompanyCRUD
from app.crud.user import UserCRUD
from app.crud.user_company_access import UserCompanyAccessCRUD
from app.helpers.authentication import get_current_user
from app.schema.user import CurrentUserSchema
from app.static.permissions import PermissionsModules
from tests.conftest import test_app, get_test_session


class FinanceIntegrationFixtureFactory:
    """Factory for creating finance integration test fixtures."""

    @staticmethod
    def create_company(db_session, name="Finance Test Company"):
        """Create a test company."""
        company_crud = CompanyCRUD(db_session)
        return company_crud.create_item({
            "name": name,
            "company_type": "Portfolio Management"
        })

    @staticmethod
    def create_user_with_access(db_session, email, company_id, role="contributor", status="active"):
        """Create a user with company access."""
        user_crud = UserCRUD(db_session)
        user_company_access_crud = UserCompanyAccessCRUD(db_session)

        user = user_crud.create_item({
            "first_name": "Test",
            "last_name": email.split("@")[0],
            "email": email,
            "is_registered": True,
            "phone": "1234567890",
        })

        access = user_company_access_crud.create_item({
            "user_id": user.id,
            "company_id": company_id,
            "role": role,
            "status": status,
        })

        return {"user": user, "access": access}

    @staticmethod
    def cleanup_fixtures(db_session, company, users_data):
        """Cleanup created fixtures."""
        company_crud = CompanyCRUD(db_session)
        user_crud = UserCRUD(db_session)
        user_company_access_crud = UserCompanyAccessCRUD(db_session)

        for user_data in users_data:
            if user_data.get("access"):
                user_company_access_crud.delete_by_id(user_data["access"].id)
            if user_data.get("user"):
                user_crud.delete_by_id(user_data["user"].id)

        if company:
            company_crud.delete_by_id(company.id)


def create_mock_user_from_db(user, company_ids, is_system_user=False):
    """Create a mock current user that mirrors real DB user for auth override."""
    mock_user = Mock(spec=CurrentUserSchema)
    mock_user.id = user.id
    mock_user.is_system_user = is_system_user
    mock_user.role = Mock()
    mock_user.role.permissions = {}
    mock_user.get_limited_companies_ids.return_value = company_ids
    mock_user.get_limited_sites_ids.return_value = []
    return mock_user


class TestFinanceIntegrationPermissions:
    """Finance Integration endpoints require company_admin + Finance:edit.
    
    Test matrix:
    - company_admin with finance:edit -> allowed (200)
    - company_admin without finance:edit -> denied (403)
    - contributor with finance:edit -> denied (403, insufficient_role)
    - read_only -> denied (403)
    """

    @pytest.fixture(scope="function")
    def setup_fixtures(self):
        """Setup test fixtures."""
        db = next(get_test_session())
        factory = FinanceIntegrationFixtureFactory
        
        company = factory.create_company(db, "Finance Integration Test Company")
        
        company_admin_user = factory.create_user_with_access(
            db, 
            email="fin_admin@test.com",
            company_id=company.id,
            role="company_admin"
        )
        
        contributor_user = factory.create_user_with_access(
            db,
            email="fin_contributor@test.com", 
            company_id=company.id,
            role="contributor"
        )
        
        read_only_user = factory.create_user_with_access(
            db,
            email="fin_readonly@test.com",
            company_id=company.id,
            role="read_only"
        )

        yield {
            "db": db,
            "company": company,
            "company_admin_user": company_admin_user,
            "contributor_user": contributor_user,
            "read_only_user": read_only_user,
        }

        factory.cleanup_fixtures(
            db,
            company,
            [company_admin_user, contributor_user, read_only_user]
        )

    def test_company_admin_with_finance_edit_allowed(self, setup_fixtures, test_app):
        """company_admin with default finance:edit should be allowed."""
        fixtures = setup_fixtures
        company_id = fixtures["company"].id
        user_data = fixtures["company_admin_user"]
        
        mock_user = create_mock_user_from_db(
            user_data["user"],
            company_ids=[company_id]
        )
        
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            response = test_app.get(f"/api/finance/integrations/{company_id}")
            assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.json()}"
            
            data = response.json()
            assert "integrations" in data
            assert "available_providers" in data
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)

    def test_contributor_denied_insufficient_role(self, setup_fixtures, test_app):
        """contributor role should be denied even with finance:edit (requires company_admin)."""
        fixtures = setup_fixtures
        company_id = fixtures["company"].id
        user_data = fixtures["contributor_user"]
        
        mock_user = create_mock_user_from_db(
            user_data["user"],
            company_ids=[company_id]
        )
        
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            response = test_app.get(f"/api/finance/integrations/{company_id}")
            assert response.status_code == 403, f"Expected 403, got {response.status_code}"
            
            error = response.json()
            assert error["error"] == "access_denied"
            assert error["reason_code"] == "insufficient_role"
            assert error["module_key"] == PermissionsModules.finance.value
            assert error["action"] == "edit"
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)

    def test_read_only_denied(self, setup_fixtures, test_app):
        """read_only role should be denied (no finance:edit)."""
        fixtures = setup_fixtures
        company_id = fixtures["company"].id
        user_data = fixtures["read_only_user"]
        
        mock_user = create_mock_user_from_db(
            user_data["user"],
            company_ids=[company_id]
        )
        
        test_app.dependency_overrides[get_current_user] = lambda: mock_user
        
        try:
            response = test_app.get(f"/api/finance/integrations/{company_id}")
            assert response.status_code == 403, f"Expected 403, got {response.status_code}"
            
            error = response.json()
            assert error["error"] == "access_denied"
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)

    def test_no_settings_module_reference(self, setup_fixtures):
        """Verify no Settings module reference in finance integration auth.
        
        This is a code inspection test to prevent regression to deprecated
        Settings module gating.
        """
        import inspect
        from app.routers.finance.integrations import _require_company_admin_with_finance_permission
        
        source = inspect.getsource(_require_company_admin_with_finance_permission)
        
        assert "PermissionsModules.settings" not in source, \
            "Finance integration auth should NOT reference Settings module"
        
        assert "PermissionsModules.finance" in source, \
            "Finance integration auth MUST use Finance module"
