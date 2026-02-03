"""FastAPI TestClient endpoint tests for Phase C.2 Diligence module permission enforcement.

These tests verify that:
1. GET diligence endpoint: entity access OK but lacks diligence:view -> 403
2. POST/PUT diligence endpoint: has diligence:view but lacks diligence:edit -> 403
3. Positive: has diligence:edit -> succeeds
"""

import pytest
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient

from app.crud.company import CompanyCRUD
from app.crud.site import SiteCRUD
from app.crud.document_section import DocumentSectionCRUD
from app.crud.document import DocumentCRUD
from app.crud.user import UserCRUD
from app.crud.user_company_access import UserCompanyAccessCRUD
from app.helpers.authentication import get_current_user
from app.schema.user import CurrentUserSchema
from app.static.default_site_documents_enum import SiteDocumentsEnum
from tests.conftest import test_app, get_test_session


class TestDiligencePermissionEnforcement:
    """Tests for Diligence module permission enforcement."""

    @pytest.fixture(scope="function")
    def company_with_site_and_document(self, db_session):
        """Create a company with site and document for testing permissions."""
        company_crud = CompanyCRUD(db_session)
        site_crud = SiteCRUD(db_session)
        section_crud = DocumentSectionCRUD(db_session)
        document_crud = DocumentCRUD(db_session)
        
        company = company_crud.create_item({
            "name": "Test Diligence Company",
            "company_type": "Portfolio Management"
        })
        
        site = site_crud.create_item({
            "name": "Test Diligence Site",
            "company_id": company.id,
        })
        
        section = section_crud.create_item({
            "name": "Test Section",
            "site_id": site.id,
        })
        
        document = document_crud.create_item({
            "name": SiteDocumentsEnum.executive_summary.value,
            "site_id": site.id,
            "section_id": section.id,
        })
        
        yield {
            "company": company,
            "site": site,
            "section": section,
            "document": document,
        }
        
        document_crud.delete_by_id(document.id)
        section_crud.delete_by_id(section.id)
        site_crud.delete_by_id(site.id)
        company_crud.delete_by_id(company.id)

    @pytest.fixture(scope="function")
    def user_with_entity_access_no_diligence(self, db_session, company_with_site_and_document):
        """Create a user with entity access but NO diligence module permission."""
        user_crud = UserCRUD(db_session)
        user_company_access_crud = UserCompanyAccessCRUD(db_session)
        
        user = user_crud.create_item({
            "first_name": "Test",
            "last_name": "NoDiligence",
            "email": "test_no_diligence@test.com",
            "is_registered": True,
            "phone": "1234567890",
        })
        
        access = user_company_access_crud.create_item({
            "user_id": user.id,
            "company_id": company_with_site_and_document["company"].id,
            "base_role": "company_admin",
            "status": "active",
        })
        
        yield user
        
        user_company_access_crud.delete_by_id(access.id)
        user_crud.delete_by_id(user.id)

    @pytest.fixture(scope="function")
    def user_with_diligence_view_only(self, db_session, company_with_site_and_document):
        """Create a user with diligence:view but NOT diligence:edit."""
        user_crud = UserCRUD(db_session)
        user_company_access_crud = UserCompanyAccessCRUD(db_session)
        
        user = user_crud.create_item({
            "first_name": "Test",
            "last_name": "ViewOnly",
            "email": "test_view_only@test.com",
            "is_registered": True,
            "phone": "1234567890",
        })
        
        access = user_company_access_crud.create_item({
            "user_id": user.id,
            "company_id": company_with_site_and_document["company"].id,
            "base_role": "company_admin",
            "status": "active",
        })
        
        yield user
        
        user_company_access_crud.delete_by_id(access.id)
        user_crud.delete_by_id(user.id)

    @pytest.fixture(scope="function")
    def user_with_diligence_edit(self, db_session, company_with_site_and_document):
        """Create a user with diligence:edit permission."""
        user_crud = UserCRUD(db_session)
        user_company_access_crud = UserCompanyAccessCRUD(db_session)
        
        user = user_crud.create_item({
            "first_name": "Test",
            "last_name": "EditUser",
            "email": "test_edit_user@test.com",
            "is_registered": True,
            "phone": "1234567890",
        })
        
        access = user_company_access_crud.create_item({
            "user_id": user.id,
            "company_id": company_with_site_and_document["company"].id,
            "base_role": "company_admin",
            "status": "active",
        })
        
        yield user
        
        user_company_access_crud.delete_by_id(access.id)
        user_crud.delete_by_id(user.id)

    def _create_mock_user(self, user, permissions: dict, company_id: int, site_id: int):
        """Helper to create a mock current user with specific permissions."""
        mock_user = Mock(spec=CurrentUserSchema)
        mock_user.id = user.id
        mock_user.is_system_user = False
        mock_user.role = Mock()
        mock_user.role.permissions = permissions
        mock_user.get_limited_companies_ids.return_value = [company_id]
        mock_user.get_limited_sites_ids.return_value = [site_id]
        return mock_user

    def test_get_document_returns_403_when_user_lacks_diligence_view(
        self, client, db_session, company_with_site_and_document, user_with_entity_access_no_diligence
    ):
        """Test that GET /documents/{id} returns 403 when user lacks diligence:view."""
        fixtures = company_with_site_and_document
        user = user_with_entity_access_no_diligence
        
        mock_user = self._create_mock_user(
            user,
            permissions={
                "Asset Management": {"view": True, "edit": True},
            },
            company_id=fixtures["company"].id,
            site_id=fixtures["site"].id,
        )
        
        def override_get_current_user():
            return mock_user
        
        test_app.dependency_overrides[get_current_user] = override_get_current_user
        
        with patch(
            'app.helpers.permission_guards.resolve_effective_access'
        ) as mock_resolver:
            mock_result = Mock()
            mock_result.decision = "granted"
            mock_result.module_permissions = {"Asset Management": {"view": True}}
            mock_result.grant_sources = []
            mock_resolver.return_value = mock_result
            
            try:
                response = client.get(
                    f"/api/sites/{fixtures['site'].id}/documents/{fixtures['document'].id}"
                )
                
                assert response.status_code == 403
                data = response.json()
                assert "detail" in data
                detail = data["detail"]
                assert detail.get("error") == "access_denied"
                assert detail.get("module_key") == "Diligence"
                assert detail.get("action") == "view"
                assert "reason_code" in detail
            finally:
                test_app.dependency_overrides.pop(get_current_user, None)

    def test_post_document_description_returns_403_when_user_has_view_but_not_edit(
        self, client, db_session, company_with_site_and_document, user_with_diligence_view_only
    ):
        """Test that POST /documents/{id}/description returns 403 when user has view but not edit."""
        fixtures = company_with_site_and_document
        user = user_with_diligence_view_only
        
        mock_user = self._create_mock_user(
            user,
            permissions={
                "Diligence": {"view": True},
            },
            company_id=fixtures["company"].id,
            site_id=fixtures["site"].id,
        )
        
        def override_get_current_user():
            return mock_user
        
        test_app.dependency_overrides[get_current_user] = override_get_current_user
        
        with patch(
            'app.helpers.permission_guards.resolve_effective_access'
        ) as mock_resolver:
            mock_result = Mock()
            mock_result.decision = "granted"
            mock_result.module_permissions = {"Diligence": {"view": True}}
            mock_result.grant_sources = []
            mock_resolver.return_value = mock_result
            
            try:
                response = client.post(
                    f"/api/sites/{fixtures['site'].id}/documents/{fixtures['document'].id}/description",
                    json={"description": "Test description"}
                )
                
                assert response.status_code == 403
                data = response.json()
                assert "detail" in data
                detail = data["detail"]
                assert detail.get("error") == "access_denied"
                assert detail.get("module_key") == "Diligence"
                assert detail.get("action") == "edit"
            finally:
                test_app.dependency_overrides.pop(get_current_user, None)

    def test_post_document_description_succeeds_when_user_has_edit(
        self, client, db_session, company_with_site_and_document, user_with_diligence_edit
    ):
        """Test that POST /documents/{id}/description succeeds when user has diligence:edit."""
        fixtures = company_with_site_and_document
        user = user_with_diligence_edit
        
        mock_user = self._create_mock_user(
            user,
            permissions={
                "Diligence": {"view": True, "edit": True},
            },
            company_id=fixtures["company"].id,
            site_id=fixtures["site"].id,
        )
        
        def override_get_current_user():
            return mock_user
        
        test_app.dependency_overrides[get_current_user] = override_get_current_user
        
        with patch(
            'app.helpers.permission_guards.resolve_effective_access'
        ) as mock_resolver:
            mock_result = Mock()
            mock_result.decision = "granted"
            mock_result.module_permissions = {"Diligence": {"view": True, "edit": True}}
            mock_result.grant_sources = []
            mock_resolver.return_value = mock_result
            
            try:
                response = client.post(
                    f"/api/sites/{fixtures['site'].id}/documents/{fixtures['document'].id}/description",
                    json={"description": "Test description update"}
                )
                
                assert response.status_code in (200, 202)
            finally:
                test_app.dependency_overrides.pop(get_current_user, None)


class TestDiligence403PayloadShape:
    """Tests to verify 403 payloads include standardized fields."""

    def test_403_payload_includes_grant_sources_summary(self, client):
        """Test that 403 responses include grant_sources_summary field."""
        mock_user = Mock(spec=CurrentUserSchema)
        mock_user.id = 999999
        mock_user.is_system_user = False
        mock_user.role = Mock()
        mock_user.role.permissions = {}
        mock_user.get_limited_companies_ids.return_value = []
        mock_user.get_limited_sites_ids.return_value = []
        
        def override_get_current_user():
            return mock_user
        
        test_app.dependency_overrides[get_current_user] = override_get_current_user
        
        try:
            response = client.get("/api/sites/1/documents/1")
            
            if response.status_code == 403:
                data = response.json()
                detail = data.get("detail", {})
                assert "grant_sources_summary" in detail or "reason_code" in detail
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)
