"""FastAPI TestClient endpoint tests for Phase C.1.1 scope filtering.

These tests verify that:
1. GET /companies/sites returns ONLY accessible sites (filtered by user's accessible entities)
2. List endpoints cannot leak data from companies/sites the user doesn't have access to
"""

import pytest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.crud.company import CompanyCRUD
from app.crud.site import SiteCRUD
from app.crud.user import UserCRUD
from app.crud.user_company_access import UserCompanyAccessCRUD
from app.helpers.authentication import AuthenticationHandler, get_current_user
from app.schema.user import CurrentUserSchema
from tests.conftest import test_app, get_test_session


class TestCompanySitesEndpointScoping:
    """Tests for GET /companies/sites endpoint scope filtering."""

    @pytest.fixture(scope="function")
    def two_companies_with_sites(self, db_session):
        """Create two companies with sites for testing scope filtering."""
        company_crud = CompanyCRUD(db_session)
        site_crud = SiteCRUD(db_session)
        
        company_a = company_crud.create_item({
            "name": "Test Company A",
            "company_type": "Portfolio Management"
        })
        company_b = company_crud.create_item({
            "name": "Test Company B", 
            "company_type": "Portfolio Management"
        })
        
        site_a1 = site_crud.create_item({
            "name": "Site A1",
            "company_id": company_a.id,
        })
        site_a2 = site_crud.create_item({
            "name": "Site A2",
            "company_id": company_a.id,
        })
        site_b1 = site_crud.create_item({
            "name": "Site B1",
            "company_id": company_b.id,
        })
        
        yield {
            "company_a": company_a,
            "company_b": company_b,
            "site_a1": site_a1,
            "site_a2": site_a2,
            "site_b1": site_b1,
        }
        
        site_crud.delete_by_id(site_a1.id)
        site_crud.delete_by_id(site_a2.id)
        site_crud.delete_by_id(site_b1.id)
        company_crud.delete_by_id(company_a.id)
        company_crud.delete_by_id(company_b.id)

    @pytest.fixture(scope="function")
    def user_with_company_a_access(self, db_session, two_companies_with_sites):
        """Create a user with access to only company A."""
        user_crud = UserCRUD(db_session)
        
        user = user_crud.create_item({
            "first_name": "Test",
            "last_name": "User",
            "email": "test_scope_user@test.com",
            "is_registered": True,
            "phone": "1234567890",
        })
        
        user_company_access_crud = UserCompanyAccessCRUD(db_session)
        access = user_company_access_crud.create_item({
            "user_id": user.id,
            "company_id": two_companies_with_sites["company_a"].id,
            "base_role": "company_admin",
            "status": "active",
        })
        
        yield user
        
        user_company_access_crud.delete_by_id(access.id)
        user_crud.delete_by_id(user.id)

    def test_companies_sites_returns_only_accessible_companies(
        self, client, db_session, two_companies_with_sites, user_with_company_a_access
    ):
        """Test that GET /companies/sites returns only companies the user has access to."""
        user = user_with_company_a_access
        
        mock_current_user = Mock(spec=CurrentUserSchema)
        mock_current_user.id = user.id
        mock_current_user.is_system_user = False
        mock_current_user.role = Mock()
        mock_current_user.role.permissions = {
            "Settings": {"view": True, "edit": True},
            "Asset Management": {"view": True, "edit": True},
        }
        mock_current_user.get_limited_companies_ids.return_value = [
            two_companies_with_sites["company_a"].id
        ]
        mock_current_user.get_limited_sites_ids.return_value = [
            two_companies_with_sites["site_a1"].id,
            two_companies_with_sites["site_a2"].id,
        ]
        
        def override_get_current_user():
            return mock_current_user
        
        test_app.dependency_overrides[get_current_user] = override_get_current_user
        
        try:
            with patch('app.routers.assets_management.companies.require_module_permission_any_context') as mock_perm:
                mock_perm.return_value = True
                
                response = client.get("/api/companies/sites")
                
                assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
                data = response.json()
                
                returned_company_ids = [c["id"] for c in data["data"]]
                
                assert two_companies_with_sites["company_a"].id in returned_company_ids, \
                    f"Expected company A ({two_companies_with_sites['company_a'].id}) in results"
                assert two_companies_with_sites["company_b"].id not in returned_company_ids, \
                    f"Company B ({two_companies_with_sites['company_b'].id}) should NOT be in results"
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)

    def test_site_only_access_filters_nested_sites(
        self, client, db_session, two_companies_with_sites, user_with_company_a_access
    ):
        """Test that user with site-only access sees only their accessible sites, not all company sites."""
        user = user_with_company_a_access
        
        mock_current_user = Mock(spec=CurrentUserSchema)
        mock_current_user.id = user.id
        mock_current_user.is_system_user = False
        mock_current_user.role = Mock()
        mock_current_user.role.permissions = {
            "Settings": {"view": True, "edit": True},
        }
        mock_current_user.get_limited_companies_ids.return_value = []
        mock_current_user.get_limited_sites_ids.return_value = [
            two_companies_with_sites["site_a1"].id,
        ]
        
        def override_get_current_user():
            return mock_current_user
        
        test_app.dependency_overrides[get_current_user] = override_get_current_user
        
        try:
            with patch('app.routers.assets_management.companies.require_module_permission_any_context') as mock_perm:
                mock_perm.return_value = True
                
                response = client.get("/api/companies/sites")
                
                assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
                data = response.json()
                
                if data["data"]:
                    company_a_data = next(
                        (c for c in data["data"] if c["id"] == two_companies_with_sites["company_a"].id), 
                        None
                    )
                    
                    if company_a_data:
                        returned_site_ids = [s["id"] for s in company_a_data.get("sites", [])]
                        
                        assert two_companies_with_sites["site_a1"].id in returned_site_ids, \
                            f"Expected site_a1 in accessible sites"
                        assert two_companies_with_sites["site_a2"].id not in returned_site_ids, \
                            f"site_a2 should NOT be in results (user has no access)"
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)

    def test_user_without_settings_permission_gets_403(
        self, client, db_session, two_companies_with_sites, user_with_company_a_access
    ):
        """Test that user without settings:edit permission gets 403."""
        user = user_with_company_a_access
        
        mock_current_user = Mock(spec=CurrentUserSchema)
        mock_current_user.id = user.id
        mock_current_user.is_system_user = False
        mock_current_user.role = Mock()
        mock_current_user.role.permissions = {
            "Asset Management": {"view": True, "edit": True},
        }
        mock_current_user.get_limited_companies_ids.return_value = [
            two_companies_with_sites["company_a"].id
        ]
        mock_current_user.get_limited_sites_ids.return_value = [
            two_companies_with_sites["site_a1"].id,
            two_companies_with_sites["site_a2"].id,
        ]
        
        def override_get_current_user():
            return mock_current_user
        
        test_app.dependency_overrides[get_current_user] = override_get_current_user
        
        try:
            with patch('app.routers.assets_management.companies.require_module_permission_any_context') as mock_perm:
                from fastapi import HTTPException
                mock_perm.side_effect = HTTPException(
                    status_code=403,
                    detail="Access denied: missing_module_permission:Settings.edit"
                )
                
                response = client.get("/api/companies/sites")
                
                assert response.status_code == 403
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)


class TestSitesListEndpointScoping:
    """Tests for GET /sites endpoint scope filtering."""

    @pytest.fixture(scope="function")
    def two_companies_with_sites(self, db_session):
        """Create two companies with sites for testing scope filtering."""
        company_crud = CompanyCRUD(db_session)
        site_crud = SiteCRUD(db_session)
        
        company_a = company_crud.create_item({
            "name": "Test Company A for Sites",
            "company_type": "Portfolio Management"
        })
        company_b = company_crud.create_item({
            "name": "Test Company B for Sites", 
            "company_type": "Portfolio Management"
        })
        
        site_a1 = site_crud.create_item({
            "name": "Site A1 for list test",
            "company_id": company_a.id,
        })
        site_b1 = site_crud.create_item({
            "name": "Site B1 for list test",
            "company_id": company_b.id,
        })
        
        yield {
            "company_a": company_a,
            "company_b": company_b,
            "site_a1": site_a1,
            "site_b1": site_b1,
        }
        
        site_crud.delete_by_id(site_a1.id)
        site_crud.delete_by_id(site_b1.id)
        company_crud.delete_by_id(company_a.id)
        company_crud.delete_by_id(company_b.id)

    def test_sites_list_returns_only_accessible_sites(
        self, client, db_session, two_companies_with_sites
    ):
        """Test that GET /sites returns only sites the user has access to."""
        mock_current_user = Mock(spec=CurrentUserSchema)
        mock_current_user.id = 999
        mock_current_user.is_system_user = False
        mock_current_user.role = Mock()
        mock_current_user.role.permissions = {
            "Asset Management": {"view": True, "edit": True},
        }
        mock_current_user.get_limited_companies_ids.return_value = [
            two_companies_with_sites["company_a"].id
        ]
        mock_current_user.get_limited_sites_ids.return_value = [
            two_companies_with_sites["site_a1"].id
        ]
        
        def override_get_current_user():
            return mock_current_user
        
        test_app.dependency_overrides[get_current_user] = override_get_current_user
        
        try:
            with patch('app.routers.assets_management.sites.require_module_permission_any_context') as mock_perm:
                mock_perm.return_value = True
                
                response = client.get("/api/sites")
                
                if response.status_code == 200:
                    data = response.json()
                    returned_site_ids = [s["id"] for s in data["items"]]
                    
                    assert two_companies_with_sites["site_a1"].id in returned_site_ids
                    assert two_companies_with_sites["site_b1"].id not in returned_site_ids
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)

    def test_user_without_assets_permission_gets_403_on_sites_list(self, client):
        """Test that user without assets_management:view permission gets 403 on sites list."""
        mock_current_user = Mock(spec=CurrentUserSchema)
        mock_current_user.id = 999
        mock_current_user.is_system_user = False
        mock_current_user.role = Mock()
        mock_current_user.role.permissions = {}
        mock_current_user.get_limited_companies_ids.return_value = []
        mock_current_user.get_limited_sites_ids.return_value = []
        
        def override_get_current_user():
            return mock_current_user
        
        test_app.dependency_overrides[get_current_user] = override_get_current_user
        
        try:
            with patch('app.routers.assets_management.sites.require_module_permission_any_context') as mock_perm:
                from fastapi import HTTPException
                mock_perm.side_effect = HTTPException(
                    status_code=403,
                    detail="Access denied: no accessible context for Asset Management"
                )
                
                response = client.get("/api/sites")
                
                assert response.status_code == 403
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)


class TestCompaniesListEndpointScoping:
    """Tests for GET /companies endpoint scope filtering."""

    def test_user_with_one_company_access_cannot_see_other_companies(self, client, db_session):
        """Test that user with access to one company cannot see other companies."""
        company_crud = CompanyCRUD(db_session)
        
        company_a = company_crud.create_item({
            "name": "Visible Company",
            "company_type": "Portfolio Management"
        })
        company_b = company_crud.create_item({
            "name": "Hidden Company", 
            "company_type": "Portfolio Management"
        })
        
        try:
            mock_current_user = Mock(spec=CurrentUserSchema)
            mock_current_user.id = 999
            mock_current_user.is_system_user = False
            mock_current_user.role = Mock()
            mock_current_user.role.permissions = {
                "Asset Management": {"view": True},
            }
            mock_current_user.get_limited_companies_ids.return_value = [company_a.id]
            mock_current_user.get_limited_sites_ids.return_value = []
            
            def override_get_current_user():
                return mock_current_user
            
            test_app.dependency_overrides[get_current_user] = override_get_current_user
            
            with patch('app.routers.assets_management.companies.require_module_permission_any_context') as mock_perm:
                mock_perm.return_value = True
                
                response = client.get("/api/companies")
                
                if response.status_code == 200:
                    data = response.json()
                    returned_company_ids = [c["id"] for c in data["items"]]
                    
                    assert company_a.id in returned_company_ids
                    assert company_b.id not in returned_company_ids
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)
            company_crud.delete_by_id(company_a.id)
            company_crud.delete_by_id(company_b.id)
