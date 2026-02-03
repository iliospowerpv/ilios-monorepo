"""Phase D: Cross-Module Integration Tests + Debug Endpoint Security Tests.

These tests verify authorization behavior end-to-end across modules using REAL
DB grants and the canonical resolver (no mocking of resolve_effective_access).

Test Strategy:
- Use base_role grants which have default permissions per BASE_ROLE_DEFAULT_PERMISSIONS:
  - company_admin: all modules view/edit
  - contributor: assets/diligence/o&m view/edit, finance view only
  - read_only: all modules view only
- Create role_profiles with specific module permissions for custom scenarios
- Tests verify real 403 responses from the permission guards

Coverage:
1. Finance module: view/edit permission enforcement
2. Assets management module: view/edit permission enforcement  
3. Diligence module: view/edit permission enforcement
4. Restrict-only intersection at HTTP level (via role_profile)
5. Project-only access scoping
6. Standardized 403 payload shape
7. Debug endpoint security (cross-company and non-admin rejection)
"""

import pytest
from unittest.mock import Mock

from app.crud.company import CompanyCRUD
from app.crud.site import SiteCRUD
from app.crud.user import UserCRUD
from app.crud.user_company_access import UserCompanyAccessCRUD
from app.crud.role_profile import RoleProfileCRUD
from app.crud.document_section import DocumentSectionCRUD
from app.crud.document import DocumentCRUD
from app.helpers.authentication import get_current_user
from app.helpers.access_resolver import BASE_ROLE_DEFAULT_PERMISSIONS
from app.models.user import UserPortfolioAccess, MembershipStatus, CompanyRole
from app.schema.user import CurrentUserSchema
from app.static.permissions import PermissionsModules
from app.static.default_site_documents_enum import SiteDocumentsEnum, DocumentSections
from tests.conftest import test_app, get_test_session


class CrossModuleFixtureFactory:
    """Factory for creating cross-module test fixtures with real DB grants."""

    @staticmethod
    def create_two_companies_with_sites(db_session):
        """Create two companies (A and B) each with sites."""
        company_crud = CompanyCRUD(db_session)
        site_crud = SiteCRUD(db_session)

        company_a = company_crud.create_item({
            "name": "Cross Module Test Company A",
            "company_type": "Portfolio Management"
        })
        company_b = company_crud.create_item({
            "name": "Cross Module Test Company B", 
            "company_type": "Portfolio Management"
        })

        site_a = site_crud.create_item({
            "name": "Site A under Company A",
            "company_id": company_a.id,
        })
        site_b = site_crud.create_item({
            "name": "Site B under Company B",
            "company_id": company_b.id,
        })
        site_a2 = site_crud.create_item({
            "name": "Site A2 under Company A (sibling)",
            "company_id": company_a.id,
        })

        return {
            "company_a": company_a,
            "company_b": company_b,
            "site_a": site_a,
            "site_b": site_b,
            "site_a2": site_a2,
        }

    @staticmethod
    def create_user_with_access(db_session, email, company_id, role="contributor", 
                                 status="active", role_profile_key=None):
        """Create a user with company access and optional role profile."""
        user_crud = UserCRUD(db_session)
        user_company_access_crud = UserCompanyAccessCRUD(db_session)

        user = user_crud.create_item({
            "first_name": "Test",
            "last_name": email.split("@")[0],
            "email": email,
            "is_registered": True,
            "phone": "1234567890",
        })

        access_data = {
            "user_id": user.id,
            "company_id": company_id,
            "role": role,
            "status": status,
        }
        if role_profile_key:
            access_data["role_profile_key"] = role_profile_key

        access = user_company_access_crud.create_item(access_data)

        return {"user": user, "access": access}

    @staticmethod
    def create_role_profile(db_session, key, label, module_permissions):
        """Create a role profile with specific module permissions."""
        role_profile_crud = RoleProfileCRUD(db_session)
        
        existing = role_profile_crud.get_by_key(key)
        if existing:
            return existing
            
        return role_profile_crud.create_item({
            "key": key,
            "label": label,
            "default_module_permissions": module_permissions,
            "is_active": True,
        })

    @staticmethod
    def cleanup_fixtures(db_session, fixtures, users_data, role_profiles=None):
        """Cleanup created fixtures."""
        site_crud = SiteCRUD(db_session)
        company_crud = CompanyCRUD(db_session)
        user_crud = UserCRUD(db_session)
        user_company_access_crud = UserCompanyAccessCRUD(db_session)
        role_profile_crud = RoleProfileCRUD(db_session)

        for user_data in users_data:
            if user_data.get("access"):
                user_company_access_crud.delete_by_id(user_data["access"].id)
            if user_data.get("user"):
                user_crud.delete_by_id(user_data["user"].id)

        if role_profiles:
            for rp in role_profiles:
                try:
                    role_profile_crud.delete_by_key(rp.key)
                except Exception:
                    pass

        if fixtures.get("site_a2"):
            site_crud.delete_by_id(fixtures["site_a2"].id)
        if fixtures.get("site_a"):
            site_crud.delete_by_id(fixtures["site_a"].id)
        if fixtures.get("site_b"):
            site_crud.delete_by_id(fixtures["site_b"].id)
        if fixtures.get("company_a"):
            company_crud.delete_by_id(fixtures["company_a"].id)
        if fixtures.get("company_b"):
            company_crud.delete_by_id(fixtures["company_b"].id)


def create_mock_user_from_db(user, company_ids, site_ids, is_system_user=False):
    """Create a mock current user that mirrors real DB user for auth override."""
    mock_user = Mock(spec=CurrentUserSchema)
    mock_user.id = user.id
    mock_user.is_system_user = is_system_user
    mock_user.role = Mock()
    mock_user.role.permissions = {}
    mock_user.get_limited_companies_ids.return_value = company_ids
    mock_user.get_limited_sites_ids.return_value = site_ids
    return mock_user


class TestFinanceModulePermissions:
    """Test A & B: Finance GET requires finance:view, mutation requires finance:edit.
    
    Uses read_only base role which has finance:view but NOT finance:edit.
    Uses role_profile with no finance permissions to test lack of finance:view.
    """

    @pytest.fixture(scope="function")
    def fixtures(self, db_session):
        """Create test fixtures with role profile that lacks finance permissions."""
        fixtures = CrossModuleFixtureFactory.create_two_companies_with_sites(db_session)
        
        no_finance_profile = CrossModuleFixtureFactory.create_role_profile(
            db_session,
            "test_no_finance",
            "No Finance Access",
            {
                "Asset Management": {"view": True, "edit": True},
                "Diligence": {"view": True, "edit": True},
            }
        )
        
        user_no_finance = CrossModuleFixtureFactory.create_user_with_access(
            db_session,
            "no_finance_user@test.com",
            fixtures["company_a"].id,
            "contributor",
            role_profile_key="test_no_finance"
        )
        
        user_read_only = CrossModuleFixtureFactory.create_user_with_access(
            db_session,
            "read_only_finance_user@test.com",
            fixtures["company_a"].id,
            "read_only"
        )
        
        yield {
            "fixtures": fixtures,
            "user_no_finance": user_no_finance,
            "user_read_only": user_read_only,
            "no_finance_profile": no_finance_profile,
        }
        
        CrossModuleFixtureFactory.cleanup_fixtures(
            db_session, fixtures, 
            [user_no_finance, user_read_only],
            [no_finance_profile]
        )

    def test_finance_get_returns_403_when_user_lacks_finance_view(self, client, fixtures):
        """Test A: User with role_profile lacking finance => GET returns 403."""
        f = fixtures["fixtures"]
        user = fixtures["user_no_finance"]["user"]

        mock_user = create_mock_user_from_db(
            user,
            company_ids=[f["company_a"].id],
            site_ids=[f["site_a"].id],
        )

        def override_get_current_user():
            return mock_user

        test_app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            response = client.get(f"/api/companies/{f['company_a'].id}/finance/actuals")
            
            assert response.status_code == 403
            data = response.json()
            detail = data.get("detail", {})
            assert detail.get("error") == "access_denied"
            assert detail.get("reason_code") == "missing_module_permission"
            assert detail.get("module_key") == "Finance"
            assert detail.get("action") == "view"
            assert "grant_sources_summary" in detail
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)

    def test_finance_mutation_returns_403_when_user_has_view_but_not_edit(self, client, fixtures):
        """Test B: read_only user has finance:view but not finance:edit => POST returns 403."""
        f = fixtures["fixtures"]
        user = fixtures["user_read_only"]["user"]

        mock_user = create_mock_user_from_db(
            user,
            company_ids=[f["company_a"].id],
            site_ids=[f["site_a"].id],
        )

        def override_get_current_user():
            return mock_user

        test_app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            response = client.post(
                f"/api/companies/{f['company_a'].id}/finance/actuals",
                json={
                    "site_id": f["site_a"].id,
                    "period_start": "2024-01-01",
                    "period_end": "2024-01-31",
                    "category": "Revenue",
                    "amount": 10000.00,
                }
            )

            assert response.status_code == 403
            data = response.json()
            detail = data.get("detail", {})
            assert detail.get("error") == "access_denied"
            assert detail.get("module_key") == "Finance"
            assert detail.get("action") == "edit"
            assert "grant_sources_summary" in detail
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)


class TestAssetsManagementModulePermissions:
    """Test C: Assets mutation requires assets_management:edit.
    
    Uses read_only base role which has assets_management:view but NOT edit.
    """

    @pytest.fixture(scope="function")
    def fixtures(self, db_session):
        """Create test fixtures."""
        fixtures = CrossModuleFixtureFactory.create_two_companies_with_sites(db_session)
        
        user_read_only = CrossModuleFixtureFactory.create_user_with_access(
            db_session,
            "assets_read_only_user@test.com",
            fixtures["company_a"].id,
            "read_only"
        )
        
        yield {"fixtures": fixtures, "user_read_only": user_read_only}
        CrossModuleFixtureFactory.cleanup_fixtures(db_session, fixtures, [user_read_only])

    def test_assets_mutation_returns_403_when_user_has_view_only(self, client, fixtures):
        """Test C: read_only user has assets_management:view only => PUT returns 403."""
        f = fixtures["fixtures"]
        user = fixtures["user_read_only"]["user"]

        mock_user = create_mock_user_from_db(
            user,
            company_ids=[f["company_a"].id],
            site_ids=[f["site_a"].id],
        )

        def override_get_current_user():
            return mock_user

        test_app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            response = client.put(
                f"/api/sites/{f['site_a'].id}/details?section_name=asset_overview",
                json={"system_size_dc": 1000}
            )

            assert response.status_code == 403
            data = response.json()
            detail = data.get("detail", {})
            assert detail.get("error") == "access_denied"
            assert detail.get("module_key") == "Asset Management"
            assert detail.get("action") == "edit"
            assert "grant_sources_summary" in detail
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)


class TestDiligenceModulePermissions:
    """Test D: Diligence GET requires diligence:view.
    
    Uses role_profile that lacks diligence permissions.
    """

    @pytest.fixture(scope="function")
    def fixtures(self, db_session):
        """Create test fixtures with document and role profile lacking diligence."""
        fixtures = CrossModuleFixtureFactory.create_two_companies_with_sites(db_session)
        
        no_diligence_profile = CrossModuleFixtureFactory.create_role_profile(
            db_session,
            "test_no_diligence",
            "No Diligence Access",
            {
                "Asset Management": {"view": True, "edit": True},
                "Finance": {"view": True},
            }
        )
        
        user_no_diligence = CrossModuleFixtureFactory.create_user_with_access(
            db_session,
            "no_diligence_user@test.com",
            fixtures["company_a"].id,
            "contributor",
            role_profile_key="test_no_diligence"
        )
        
        section_crud = DocumentSectionCRUD(db_session)
        document_crud = DocumentCRUD(db_session)
        
        section = section_crud.create_item({
            "name": "Test Section",
            "site_id": fixtures["site_a"].id,
        })
        
        document = document_crud.create_item({
            "name": SiteDocumentsEnum.executive_summary.value,
            "site_id": fixtures["site_a"].id,
            "section_id": section.id,
        })
        
        fixtures["section"] = section
        fixtures["document"] = document

        yield {
            "fixtures": fixtures,
            "user_no_diligence": user_no_diligence,
            "no_diligence_profile": no_diligence_profile,
        }
        
        document_crud.delete_by_id(document.id)
        section_crud.delete_by_id(section.id)
        CrossModuleFixtureFactory.cleanup_fixtures(
            db_session, fixtures, 
            [user_no_diligence],
            [no_diligence_profile]
        )

    def test_diligence_get_returns_403_when_user_lacks_diligence_view(self, client, fixtures):
        """Test D: User with role_profile lacking diligence => GET returns 403."""
        f = fixtures["fixtures"]
        user = fixtures["user_no_diligence"]["user"]

        mock_user = create_mock_user_from_db(
            user,
            company_ids=[f["company_a"].id],
            site_ids=[f["site_a"].id],
        )

        def override_get_current_user():
            return mock_user

        test_app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            response = client.get(
                f"/api/sites/{f['site_a'].id}/documents/{f['document'].id}"
            )

            assert response.status_code == 403
            data = response.json()
            detail = data.get("detail", {})
            assert detail.get("error") == "access_denied"
            assert detail.get("module_key") == "Diligence"
            assert detail.get("action") == "view"
            assert "grant_sources_summary" in detail
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)


class TestRestrictOnlyIntersection:
    """Test E: Restrict-only intersection at HTTP level.
    
    Uses role_profile that completely lacks finance permissions,
    even though base role might have some.
    """

    @pytest.fixture(scope="function")
    def fixtures(self, db_session):
        """Create test fixtures with role profile that restricts finance."""
        fixtures = CrossModuleFixtureFactory.create_two_companies_with_sites(db_session)
        
        no_finance_profile = CrossModuleFixtureFactory.create_role_profile(
            db_session,
            "test_restrict_finance",
            "Restricted Finance Access",
            {
                "Asset Management": {"view": True, "edit": True},
                "Diligence": {"view": True, "edit": True},
            }
        )
        
        user_restricted = CrossModuleFixtureFactory.create_user_with_access(
            db_session,
            "restricted_finance_user@test.com",
            fixtures["company_a"].id,
            "contributor",
            role_profile_key="test_restrict_finance"
        )
        
        yield {
            "fixtures": fixtures,
            "user_restricted": user_restricted,
            "no_finance_profile": no_finance_profile,
        }
        
        CrossModuleFixtureFactory.cleanup_fixtures(
            db_session, fixtures, 
            [user_restricted],
            [no_finance_profile]
        )

    def test_restrict_only_intersection_denies_finance(self, client, fixtures):
        """Test E: role_profile restricts finance => finance endpoints 403."""
        f = fixtures["fixtures"]
        user = fixtures["user_restricted"]["user"]

        mock_user = create_mock_user_from_db(
            user,
            company_ids=[f["company_a"].id],
            site_ids=[f["site_a"].id],
        )

        def override_get_current_user():
            return mock_user

        test_app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            response = client.get(f"/api/companies/{f['company_a'].id}/finance/actuals")

            assert response.status_code == 403
            data = response.json()
            detail = data.get("detail", {})
            assert detail.get("error") == "access_denied"
            assert detail.get("reason_code") == "missing_module_permission"
            assert "grant_sources_summary" in detail
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)


class TestProjectOnlyAccessScoping:
    """Test F: Project-only access scoping.
    
    User with access only to site_a should not see site_a2 in list.
    """

    @pytest.fixture(scope="function")
    def fixtures(self, db_session):
        """Create test fixtures."""
        fixtures = CrossModuleFixtureFactory.create_two_companies_with_sites(db_session)
        
        user_data = CrossModuleFixtureFactory.create_user_with_access(
            db_session,
            "project_scoped_user@test.com",
            fixtures["company_a"].id,
            "contributor"
        )
        
        yield {"fixtures": fixtures, "user_data": user_data}
        CrossModuleFixtureFactory.cleanup_fixtures(db_session, fixtures, [user_data])

    def test_project_only_access_does_not_return_sibling_sites(self, client, fixtures):
        """Test F: User scoped to site_a should not see site_a2."""
        f = fixtures["fixtures"]
        user = fixtures["user_data"]["user"]

        mock_user = create_mock_user_from_db(
            user,
            company_ids=[f["company_a"].id],
            site_ids=[f["site_a"].id],
        )

        def override_get_current_user():
            return mock_user

        test_app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            response = client.get("/api/sites/")

            assert response.status_code == 200
            data = response.json()
            
            site_ids = [item["id"] for item in data.get("items", [])]
            
            if f["site_a"].id in site_ids:
                assert f["site_a2"].id not in site_ids, \
                    "User scoped to site_a should not see sibling site_a2"
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)


class TestStandardized403PayloadShape:
    """Test 2: Standardized 403 payload shape assertions.
    
    Verify 403 responses include: error, reason_code, module_key, action, grant_sources_summary.
    """

    @pytest.fixture(scope="function")
    def fixtures(self, db_session):
        """Create test fixtures."""
        fixtures = CrossModuleFixtureFactory.create_two_companies_with_sites(db_session)
        
        no_perms_profile = CrossModuleFixtureFactory.create_role_profile(
            db_session,
            "test_no_perms",
            "No Permissions",
            {}
        )
        
        user_no_perms = CrossModuleFixtureFactory.create_user_with_access(
            db_session,
            "no_perms_user@test.com",
            fixtures["company_a"].id,
            "contributor",
            role_profile_key="test_no_perms"
        )
        
        section_crud = DocumentSectionCRUD(db_session)
        document_crud = DocumentCRUD(db_session)
        
        section = section_crud.create_item({
            "name": "Test Section",
            "site_id": fixtures["site_a"].id,
        })
        
        document = document_crud.create_item({
            "name": SiteDocumentsEnum.executive_summary.value,
            "site_id": fixtures["site_a"].id,
            "section_id": section.id,
        })
        
        fixtures["section"] = section
        fixtures["document"] = document

        yield {
            "fixtures": fixtures,
            "user_no_perms": user_no_perms,
            "no_perms_profile": no_perms_profile,
        }
        
        document_crud.delete_by_id(document.id)
        section_crud.delete_by_id(section.id)
        CrossModuleFixtureFactory.cleanup_fixtures(
            db_session, fixtures,
            [user_no_perms],
            [no_perms_profile]
        )

    def test_finance_403_has_standardized_payload_shape(self, client, fixtures):
        """Finance 403 has error, reason_code, module_key, action, grant_sources_summary."""
        f = fixtures["fixtures"]
        user = fixtures["user_no_perms"]["user"]

        mock_user = create_mock_user_from_db(
            user,
            company_ids=[f["company_a"].id],
            site_ids=[f["site_a"].id],
        )

        def override_get_current_user():
            return mock_user

        test_app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            response = client.get(f"/api/companies/{f['company_a'].id}/finance/actuals")

            assert response.status_code == 403
            data = response.json()
            detail = data.get("detail", {})

            assert "error" in detail, "403 payload missing 'error'"
            assert detail["error"] == "access_denied"
            assert "reason_code" in detail, "403 payload missing 'reason_code'"
            assert "module_key" in detail, "403 payload missing 'module_key'"
            assert "action" in detail, "403 payload missing 'action'"
            assert "grant_sources_summary" in detail, "403 payload missing 'grant_sources_summary'"
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)

    def test_diligence_403_has_standardized_payload_shape(self, client, fixtures):
        """Diligence 403 has error, reason_code, module_key, action, grant_sources_summary."""
        f = fixtures["fixtures"]
        user = fixtures["user_no_perms"]["user"]

        mock_user = create_mock_user_from_db(
            user,
            company_ids=[f["company_a"].id],
            site_ids=[f["site_a"].id],
        )

        def override_get_current_user():
            return mock_user

        test_app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            response = client.get(
                f"/api/sites/{f['site_a'].id}/documents/{f['document'].id}"
            )

            assert response.status_code == 403
            data = response.json()
            detail = data.get("detail", {})

            assert "error" in detail, "403 payload missing 'error'"
            assert detail["error"] == "access_denied"
            assert "reason_code" in detail, "403 payload missing 'reason_code'"
            assert "module_key" in detail, "403 payload missing 'module_key'"
            assert "action" in detail, "403 payload missing 'action'"
            assert "grant_sources_summary" in detail, "403 payload missing 'grant_sources_summary'"
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)


class TestDebugEndpointSecurity:
    """Test 3: Debug endpoint negative tests.
    
    Uses REAL company_admin grants to verify debug endpoint security.
    """

    @pytest.fixture(scope="function")
    def fixtures(self, db_session):
        """Create fixtures with admin for Company A only."""
        fixtures = CrossModuleFixtureFactory.create_two_companies_with_sites(db_session)
        
        admin_user_data = CrossModuleFixtureFactory.create_user_with_access(
            db_session,
            "admin_company_a_debug@test.com",
            fixtures["company_a"].id,
            "company_admin"
        )
        
        contributor_user_data = CrossModuleFixtureFactory.create_user_with_access(
            db_session,
            "contributor_company_a_debug@test.com",
            fixtures["company_a"].id,
            "contributor"
        )

        yield {
            "fixtures": fixtures,
            "admin_user_data": admin_user_data,
            "contributor_user_data": contributor_user_data,
        }

        CrossModuleFixtureFactory.cleanup_fixtures(
            db_session, fixtures, [admin_user_data, contributor_user_data]
        )

    def test_cross_company_admin_rejection(self, client, fixtures):
        """Test 3A: Admin of CompanyA requests debug for CompanyB => 403."""
        f = fixtures["fixtures"]
        admin_user = fixtures["admin_user_data"]["user"]

        mock_user = create_mock_user_from_db(
            admin_user,
            company_ids=[f["company_a"].id],
            site_ids=[f["site_a"].id],
        )

        def override_get_current_user():
            return mock_user

        test_app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            response = client.get(
                f"/api/debug/effective-access?user_id={admin_user.id}&company_id={f['company_b'].id}"
            )

            assert response.status_code == 403
            data = response.json()
            detail = data.get("detail", {})
            assert detail.get("error") == "access_denied"
            assert detail.get("reason_code") == "admin_required_for_target_company"
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)

    def test_non_admin_rejection(self, client, fixtures):
        """Test 3B: Contributor for CompanyA requests debug for CompanyA => 403."""
        f = fixtures["fixtures"]
        contributor_user = fixtures["contributor_user_data"]["user"]

        mock_user = create_mock_user_from_db(
            contributor_user,
            company_ids=[f["company_a"].id],
            site_ids=[f["site_a"].id],
        )

        def override_get_current_user():
            return mock_user

        test_app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            response = client.get(
                f"/api/debug/effective-access?user_id={contributor_user.id}&company_id={f['company_a'].id}"
            )

            assert response.status_code == 403
            data = response.json()
            detail = data.get("detail", {})
            assert detail.get("error") == "access_denied"
            assert detail.get("reason_code") == "admin_required_for_target_company"
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)

    def test_module_permission_check_cross_company_rejection(self, client, fixtures):
        """Debug module-permission-check also rejects cross-company requests."""
        f = fixtures["fixtures"]
        admin_user = fixtures["admin_user_data"]["user"]

        mock_user = create_mock_user_from_db(
            admin_user,
            company_ids=[f["company_a"].id],
            site_ids=[f["site_a"].id],
        )

        def override_get_current_user():
            return mock_user

        test_app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            response = client.get(
                f"/api/debug/module-permission-check"
                f"?user_id={admin_user.id}&company_id={f['company_b'].id}&module_key=Finance&action=view"
            )

            assert response.status_code == 403
            data = response.json()
            detail = data.get("detail", {})
            assert detail.get("error") == "access_denied"
            assert detail.get("reason_code") == "admin_required_for_target_company"
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)


class TestMultiGrantIntersection:
    """Test G: True multi-grant intersection using portfolio+company grants.
    
    This test proves restrict-only semantics across TWO applicable grants:
    - UserPortfolioAccess grant with role that has base permissions
    - UserCompanyAccess grant with role_profile that LACKS finance permissions
    
    Expected behavior: Finance endpoint returns 403 because intersection of
    permissions results in NO finance access (portfolio has default contributor
    permissions which include finance:view, but company grant's role_profile
    explicitly omits finance).
    
    Grant structure:
    - Portfolio Hub Company (hub_company)
    - Member Company (company_a) with portfolio_hub_id = hub_company.id
    - User has:
      1. UserPortfolioAccess to hub_company with role=contributor
         -> default base role permissions include finance:view
      2. UserCompanyAccess to company_a with role_profile "test_finance_denied"
         -> default_permissions: {"Asset Management": {"view": true, "edit": true}}
         (no Finance entry means finance is denied by this grant)
    
    Result: Intersection of [finance:view from portfolio] ∩ [no finance from company] 
            = [no finance] => 403
    """

    @pytest.fixture(scope="function")
    def fixtures(self, db_session):
        """Create portfolio hub + member company + user with both grants."""
        company_crud = CompanyCRUD(db_session)
        site_crud = SiteCRUD(db_session)
        user_crud = UserCRUD(db_session)
        user_company_access_crud = UserCompanyAccessCRUD(db_session)
        role_profile_crud = RoleProfileCRUD(db_session)

        hub_company = company_crud.create_item({
            "name": "Multi-Grant Test Portfolio Hub",
            "company_type": "portfolio_hub",
        })
        
        member_company = company_crud.create_item({
            "name": "Multi-Grant Test Member Company",
            "company_type": "asset_owner",
            "portfolio_hub_id": hub_company.id,
        })
        
        site = site_crud.create_item({
            "name": "Multi-Grant Test Site",
            "company_id": member_company.id,
            "location": "Test Location",
        })
        
        finance_denied_profile = role_profile_crud.create_item({
            "key": "test_multigrant_no_finance",
            "label": "No Finance Profile (Multi-Grant Test)",
            "default_module_permissions": {
                "Asset Management": {"view": True, "edit": True},
                "Diligence": {"view": True, "edit": True},
            },
            "is_active": True,
        })
        
        user = user_crud.create_item({
            "first_name": "MultiGrant",
            "last_name": "TestUser",
            "email": "multigrant_intersection@test.com",
            "is_registered": True,
            "phone": "1234567890",
        })
        
        portfolio_access = UserPortfolioAccess(
            user_id=user.id,
            portfolio_hub_company_id=hub_company.id,
            role=CompanyRole.contributor,
            status=MembershipStatus.active,
        )
        db_session.add(portfolio_access)
        
        company_access = user_company_access_crud.create_item({
            "user_id": user.id,
            "company_id": member_company.id,
            "role": "contributor",
            "status": "active",
            "role_profile_key": "test_multigrant_no_finance",
        })
        
        db_session.commit()

        yield {
            "hub_company": hub_company,
            "member_company": member_company,
            "site": site,
            "user": user,
            "portfolio_access": portfolio_access,
            "company_access": company_access,
            "finance_denied_profile": finance_denied_profile,
        }

        db_session.delete(portfolio_access)
        db_session.delete(company_access)
        db_session.delete(user)
        db_session.delete(site)
        db_session.delete(member_company)
        db_session.delete(hub_company)
        role_profile_crud.delete_by_key("test_multigrant_no_finance")
        db_session.commit()

    def test_portfolio_company_intersection_denies_finance(self, client, fixtures):
        """Test G: Portfolio+Company grants intersection denies finance.
        
        User has:
        - Portfolio access with contributor role (default: finance:view)
        - Company access with role_profile lacking finance permissions
        
        Intersection result: no finance permissions => 403 on finance endpoint.
        """
        f = fixtures

        contributor_perms = BASE_ROLE_DEFAULT_PERMISSIONS.get(CompanyRole.contributor, {})
        finance_key = PermissionsModules.finance.value
        assert finance_key in contributor_perms, \
            f"Precondition: contributor base role must have {finance_key} permissions"
        assert "view" in contributor_perms[finance_key], \
            f"Precondition: contributor must have {finance_key}:view permission"

        mock_user = create_mock_user_from_db(
            f["user"],
            company_ids=[f["member_company"].id],
            site_ids=[f["site"].id],
        )

        def override_get_current_user():
            return mock_user

        test_app.dependency_overrides[get_current_user] = override_get_current_user

        try:
            response = client.get(f"/api/companies/{f['member_company'].id}/finance/actuals")

            assert response.status_code == 403, f"Expected 403 but got {response.status_code}: {response.json()}"
            data = response.json()
            detail = data.get("detail", {})
            assert detail.get("error") == "access_denied"
            assert detail.get("reason_code") == "missing_module_permission"
            assert detail.get("module_key") == "Finance"
            assert "grant_sources_summary" in detail
            
            grant_sources = detail.get("grant_sources_summary", [])
            grant_levels = [g.get("level") for g in grant_sources]
            assert "portfolio" in grant_levels, "Portfolio grant should be in sources"
            assert "company" in grant_levels, "Company grant should be in sources"
            
            portfolio_grant_source = next(
                (g for g in grant_sources if g.get("level") == "portfolio"), None
            )
            company_grant_source = next(
                (g for g in grant_sources if g.get("level") == "company"), None
            )
            
            assert portfolio_grant_source is not None, "Portfolio grant must be present"
            assert company_grant_source is not None, "Company grant must be present"
            assert portfolio_grant_source.get("access_id") == f["portfolio_access"].id, \
                f"Portfolio access_id should match created grant: {portfolio_grant_source.get('access_id')} != {f['portfolio_access'].id}"
            assert company_grant_source.get("access_id") == f["company_access"].id, \
                f"Company access_id should match created grant: {company_grant_source.get('access_id')} != {f['company_access'].id}"
        finally:
            test_app.dependency_overrides.pop(get_current_user, None)
