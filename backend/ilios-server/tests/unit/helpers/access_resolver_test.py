"""Unit tests for the Canonical Effective-Access Resolver.

Test cases per Phase B.1 specification:
1) portfolio-only access grants company access and project access under that portfolio.
2) company-only access grants access to all projects under that company.
3) project-only access grants access only to that project.
4) restrict-only: if portfolio grant has finance.edit but company grant lacks finance module, 
   effective permissions exclude finance.
5) base role restrict-only: portfolio grant company_admin + project grant read_only => 
   effective read_only for that project.
6) deny case: no grants => denied with reason no_applicable_grant.
7) AUTHORITATIVE: resolver always returns allow/deny, never undetermined.
   Missing context results in DENY with reason_code=undetermined_context.
"""

import pytest
from typing import Dict, Set
from unittest.mock import MagicMock, patch

from app.helpers.access_resolver import (
    AccessDecision,
    AccessDeniedReason,
    BASE_ROLE_DEFAULT_PERMISSIONS,
    EffectiveAccessResult,
    GrantSource,
    ROLE_RESTRICTIVENESS,
    _normalize_permissions,
    _parse_module_permissions_json,
    effective_base_role_from_grants,
    intersect_permissions,
    permissions_from_grant,
    resolve_effective_access,
    check_module_permission,
)
from app.models.user import CompanyRole, MembershipStatus
from app.static.permissions import PermissionsModules


class TestNormalizePermissions:
    """Tests for _normalize_permissions function."""

    def test_edit_implies_view(self):
        """If edit is present, view should be added."""
        perms = {"Asset Management": {"edit"}}
        result = _normalize_permissions(perms)
        assert result["Asset Management"] == {"view", "edit"}

    def test_view_only_unchanged(self):
        """View only should remain unchanged."""
        perms = {"Asset Management": {"view"}}
        result = _normalize_permissions(perms)
        assert result["Asset Management"] == {"view"}

    def test_both_already_present(self):
        """Both view and edit already present should stay."""
        perms = {"Asset Management": {"view", "edit"}}
        result = _normalize_permissions(perms)
        assert result["Asset Management"] == {"view", "edit"}

    def test_empty_permissions(self):
        """Empty dict should return empty dict."""
        result = _normalize_permissions({})
        assert result == {}


class TestParseModulePermissionsJson:
    """Tests for _parse_module_permissions_json function."""

    def test_parse_valid_json(self):
        """Parse valid permission JSON."""
        json_perms = {
            "Asset Management": {"view": True, "edit": True},
            "Finance": {"view": True}
        }
        result = _parse_module_permissions_json(json_perms)
        assert result["Asset Management"] == {"view", "edit"}
        assert result["Finance"] == {"view"}

    def test_parse_false_values_excluded(self):
        """False values should be excluded from actions."""
        json_perms = {"Asset Management": {"view": True, "edit": False}}
        result = _parse_module_permissions_json(json_perms)
        assert result["Asset Management"] == {"view"}

    def test_parse_none_returns_empty(self):
        """None input returns empty dict."""
        result = _parse_module_permissions_json(None)
        assert result == {}

    def test_edit_implies_view_after_parse(self):
        """Edit should imply view after parsing."""
        json_perms = {"Asset Management": {"edit": True}}
        result = _parse_module_permissions_json(json_perms)
        assert result["Asset Management"] == {"view", "edit"}


class TestIntersectPermissions:
    """Tests for intersect_permissions function."""

    def test_single_set_returns_same(self):
        """Single permission set should return itself normalized."""
        perms = [{"Asset Management": {"view", "edit"}}]
        result = intersect_permissions(perms)
        assert result["Asset Management"] == {"view", "edit"}

    def test_intersection_keeps_common_modules(self):
        """Intersection should only keep modules in ALL sets."""
        perms = [
            {"Asset Management": {"view", "edit"}, "Finance": {"view"}},
            {"Asset Management": {"view"}, "Diligence": {"view"}}
        ]
        result = intersect_permissions(perms)
        # Only Asset Management is in both
        assert "Asset Management" in result
        assert "Finance" not in result
        assert "Diligence" not in result

    def test_intersection_intersects_actions(self):
        """Actions should be intersected within common modules."""
        perms = [
            {"Asset Management": {"view", "edit"}},
            {"Asset Management": {"view"}}
        ]
        result = intersect_permissions(perms)
        assert result["Asset Management"] == {"view"}

    def test_empty_list_returns_empty(self):
        """Empty list returns empty dict."""
        result = intersect_permissions([])
        assert result == {}

    def test_no_common_modules_returns_empty(self):
        """No common modules returns empty dict."""
        perms = [
            {"Asset Management": {"view"}},
            {"Finance": {"view"}}
        ]
        result = intersect_permissions(perms)
        assert result == {}

    def test_restrict_only_finance_removed(self):
        """Test spec scenario 4: portfolio has finance.edit, company lacks finance => no finance."""
        portfolio_perms = {
            "Asset Management": {"view", "edit"},
            "Finance": {"view", "edit"}
        }
        company_perms = {
            "Asset Management": {"view"}
            # No Finance module
        }
        result = intersect_permissions([portfolio_perms, company_perms])
        assert "Finance" not in result
        assert result["Asset Management"] == {"view"}


class TestEffectiveBaseRoleFromGrants:
    """Tests for effective_base_role_from_grants function."""

    def test_empty_grants_returns_none(self):
        """Empty grants list returns None."""
        result = effective_base_role_from_grants([])
        assert result is None

    def test_single_grant_returns_role(self):
        """Single grant returns its role."""
        mock_grant = MagicMock()
        mock_grant.role = CompanyRole.company_admin
        result = effective_base_role_from_grants([mock_grant])
        assert result == CompanyRole.company_admin

    def test_most_restrictive_role_wins(self):
        """Most restrictive role should win (read_only < contributor < company_admin)."""
        admin_grant = MagicMock()
        admin_grant.role = CompanyRole.company_admin
        
        read_only_grant = MagicMock()
        read_only_grant.role = CompanyRole.read_only
        
        result = effective_base_role_from_grants([admin_grant, read_only_grant])
        assert result == CompanyRole.read_only

    def test_spec_scenario_5_admin_plus_read_only(self):
        """Test spec scenario 5: portfolio admin + project read_only => read_only."""
        portfolio_grant = MagicMock()
        portfolio_grant.role = CompanyRole.company_admin
        
        project_grant = MagicMock()
        project_grant.role = CompanyRole.read_only
        
        result = effective_base_role_from_grants([portfolio_grant, project_grant])
        assert result == CompanyRole.read_only


class TestRoleRestrictiveness:
    """Tests for role restrictiveness ordering."""

    def test_read_only_is_most_restrictive(self):
        """read_only should have lowest (most restrictive) value."""
        assert ROLE_RESTRICTIVENESS[CompanyRole.read_only] < ROLE_RESTRICTIVENESS[CompanyRole.contributor]
        assert ROLE_RESTRICTIVENESS[CompanyRole.read_only] < ROLE_RESTRICTIVENESS[CompanyRole.company_admin]

    def test_contributor_middle(self):
        """contributor should be between read_only and company_admin."""
        assert ROLE_RESTRICTIVENESS[CompanyRole.contributor] > ROLE_RESTRICTIVENESS[CompanyRole.read_only]
        assert ROLE_RESTRICTIVENESS[CompanyRole.contributor] < ROLE_RESTRICTIVENESS[CompanyRole.company_admin]

    def test_company_admin_least_restrictive(self):
        """company_admin should have highest (least restrictive) value."""
        assert ROLE_RESTRICTIVENESS[CompanyRole.company_admin] > ROLE_RESTRICTIVENESS[CompanyRole.contributor]
        assert ROLE_RESTRICTIVENESS[CompanyRole.company_admin] > ROLE_RESTRICTIVENESS[CompanyRole.read_only]


class TestBaseRoleDefaultPermissions:
    """Tests for base role default permissions."""

    def test_company_admin_has_all_modules(self):
        """company_admin should have view+edit on all major modules."""
        admin_perms = BASE_ROLE_DEFAULT_PERMISSIONS[CompanyRole.company_admin]
        assert "Asset Management" in admin_perms
        assert "Finance" in admin_perms
        assert "Settings Page" in admin_perms
        assert "edit" in admin_perms["Finance"]
        assert "view" in admin_perms["Finance"]

    def test_read_only_has_view_only(self):
        """read_only should have only view actions."""
        ro_perms = BASE_ROLE_DEFAULT_PERMISSIONS[CompanyRole.read_only]
        for module, actions in ro_perms.items():
            assert "edit" not in actions, f"read_only should not have edit on {module}"
            assert "view" in actions, f"read_only should have view on {module}"

    def test_contributor_middle_ground(self):
        """contributor should have view+edit on some, view only on others."""
        contrib_perms = BASE_ROLE_DEFAULT_PERMISSIONS[CompanyRole.contributor]
        assert "edit" in contrib_perms.get("Asset Management", set())
        # contributor may not have edit on finance
        assert "view" in contrib_perms.get("Finance", set())


class TestCheckModulePermission:
    """Tests for check_module_permission function."""

    def test_denied_access_returns_denied(self):
        """If access is denied, should return False with reason."""
        result = EffectiveAccessResult(
            decision=AccessDecision.DENY,
            reason_code=AccessDeniedReason.NO_APPLICABLE_GRANT.value
        )
        allowed, reason = check_module_permission(result, "Finance", "edit")
        assert allowed is False
        assert reason == AccessDeniedReason.NO_APPLICABLE_GRANT.value

    def test_missing_module_permission(self):
        """If module permission is missing, should return False with reason."""
        result = EffectiveAccessResult(
            decision=AccessDecision.ALLOW,
            reason_code="access_granted",
            effective_base_role="contributor",
            effective_module_permissions={
                "Asset Management": {"view", "edit"}
            }
        )
        allowed, reason = check_module_permission(result, "Finance", "edit")
        assert allowed is False
        assert reason is not None and "missing_permission" in reason

    def test_missing_action_permission(self):
        """If action is missing on module, should return False with reason."""
        result = EffectiveAccessResult(
            decision=AccessDecision.ALLOW,
            reason_code="access_granted",
            effective_base_role="contributor",
            effective_module_permissions={
                "Finance": {"view"}
            }
        )
        allowed, reason = check_module_permission(result, "Finance", "edit")
        assert allowed is False
        assert reason is not None and "missing_permission" in reason

    def test_allowed_permission(self):
        """If permission exists, should return True."""
        result = EffectiveAccessResult(
            decision=AccessDecision.ALLOW,
            reason_code="access_granted",
            effective_base_role="contributor",
            effective_module_permissions={
                "Finance": {"view", "edit"}
            }
        )
        allowed, reason = check_module_permission(result, "Finance", "edit")
        assert allowed is True
        assert reason is None


class TestAuthoritativeDecision:
    """Tests for Phase B.1: Authoritative decision behavior (no undetermined)."""

    def test_decision_is_always_allow_or_deny(self):
        """EffectiveAccessResult decision must always be ALLOW or DENY, never None."""
        allow_result = EffectiveAccessResult(
            decision=AccessDecision.ALLOW,
            reason_code="access_granted"
        )
        assert allow_result.decision in [AccessDecision.ALLOW, AccessDecision.DENY]
        assert allow_result.is_allowed is True

        deny_result = EffectiveAccessResult(
            decision=AccessDecision.DENY,
            reason_code=AccessDeniedReason.NO_APPLICABLE_GRANT.value
        )
        assert deny_result.decision in [AccessDecision.ALLOW, AccessDecision.DENY]
        assert deny_result.is_allowed is False

    def test_undetermined_context_reason_exists(self):
        """UNDETERMINED_CONTEXT reason code must exist for missing context cases."""
        assert AccessDeniedReason.UNDETERMINED_CONTEXT.value == "undetermined_context"

    def test_system_error_reason_exists(self):
        """SYSTEM_ERROR reason code must exist for exception cases."""
        assert AccessDeniedReason.SYSTEM_ERROR.value == "system_error"

    def test_denied_reason_property_backward_compatible(self):
        """denied_reason property should work for backward compatibility."""
        deny_result = EffectiveAccessResult(
            decision=AccessDecision.DENY,
            reason_code=AccessDeniedReason.NO_APPLICABLE_GRANT.value
        )
        assert deny_result.denied_reason == AccessDeniedReason.NO_APPLICABLE_GRANT.value

        allow_result = EffectiveAccessResult(
            decision=AccessDecision.ALLOW,
            reason_code="access_granted"
        )
        assert allow_result.denied_reason is None


class TestResolveEffectiveAccessIntegration:
    """Integration tests for resolve_effective_access with mocked database."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return MagicMock()

    @pytest.fixture
    def mock_company(self, mock_db_session):
        """Create a mock company."""
        company = MagicMock()
        company.id = 1
        company.portfolio_hub_id = None
        mock_db_session.query.return_value.get.return_value = company
        return company

    def test_no_grants_returns_denied(self, mock_db_session):
        """Test spec scenario 6: no grants => denied with reason."""
        # Setup: company exists but no grants
        mock_company = MagicMock()
        mock_company.id = 1
        mock_db_session.query.return_value.get.return_value = mock_company
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        with patch('app.helpers.access_resolver.get_portfolio_access_for_company') as mock_portfolio:
            mock_portfolio.return_value = None
            
            result = resolve_effective_access(
                user_id=1,
                company_id=1,
                db_session=mock_db_session,
                project_id=None
            )
            
            assert result.is_allowed is False
            assert result.denied_reason == AccessDeniedReason.NO_APPLICABLE_GRANT.value

    def test_company_not_found_returns_denied(self, mock_db_session):
        """Company not found returns denied."""
        mock_db_session.query.return_value.get.return_value = None
        
        result = resolve_effective_access(
            user_id=1,
            company_id=999,
            db_session=mock_db_session,
            project_id=None
        )
        
        assert result.is_allowed is False
        assert result.denied_reason == AccessDeniedReason.COMPANY_NOT_FOUND.value

    def test_project_not_found_returns_denied(self, mock_db_session):
        """Project not found returns denied."""
        mock_company = MagicMock()
        mock_db_session.query.return_value.get.side_effect = [mock_company, None]
        
        result = resolve_effective_access(
            user_id=1,
            company_id=1,
            db_session=mock_db_session,
            project_id=999
        )
        
        assert result.is_allowed is False
        assert result.denied_reason == AccessDeniedReason.PROJECT_NOT_FOUND.value


class TestEligibilityScenarios:
    """Test spec scenarios 1-3 for eligibility rules."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        session = MagicMock()
        return session

    def _create_mock_grant(self, role: CompanyRole, grant_id: int = 1, 
                           role_profile_key: str = None, module_permissions: dict = None):
        """Helper to create a mock grant."""
        grant = MagicMock()
        grant.id = grant_id
        grant.role = role
        grant.role_profile_key = role_profile_key
        grant.module_permissions = module_permissions
        grant.status = MembershipStatus.active
        return grant

    def test_scenario_1_portfolio_only_grants_company_access(self, mock_db_session):
        """Test spec scenario 1: portfolio-only access grants company access."""
        # Setup: company exists, portfolio grant exists, no company/project grant
        mock_company = MagicMock()
        mock_company.id = 1
        mock_project = MagicMock()
        mock_project.id = 10
        
        portfolio_grant = self._create_mock_grant(CompanyRole.company_admin, grant_id=100)
        
        # Configure mock to return company, then project for project-level check
        mock_db_session.query.return_value.get.side_effect = [mock_company, mock_project]
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        with patch('app.helpers.access_resolver.get_portfolio_access_for_company') as mock_portfolio:
            mock_portfolio.return_value = portfolio_grant
            
            # Company-level access should work
            result = resolve_effective_access(
                user_id=1,
                company_id=1,
                db_session=mock_db_session,
                project_id=None
            )
            
            assert result.is_allowed is True
            assert result.effective_base_role == "company_admin"
            assert len(result.grant_sources) == 1
            assert result.grant_sources[0].level == "portfolio"

    def test_scenario_1_portfolio_only_grants_project_access(self, mock_db_session):
        """Test spec scenario 1: portfolio-only access grants project access under that portfolio."""
        mock_company = MagicMock()
        mock_company.id = 1
        mock_project = MagicMock()
        mock_project.id = 10
        
        portfolio_grant = self._create_mock_grant(CompanyRole.contributor, grant_id=100)
        
        mock_db_session.query.return_value.get.side_effect = [mock_company, mock_project]
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        with patch('app.helpers.access_resolver.get_portfolio_access_for_company') as mock_portfolio:
            mock_portfolio.return_value = portfolio_grant
            
            # Project-level access should also work via portfolio
            result = resolve_effective_access(
                user_id=1,
                company_id=1,
                db_session=mock_db_session,
                project_id=10
            )
            
            assert result.is_allowed is True
            assert result.effective_base_role == "contributor"
            assert any(gs.level == "portfolio" for gs in result.grant_sources)

    def test_scenario_2_company_only_grants_project_access(self, mock_db_session):
        """Test spec scenario 2: company-only access grants access to all projects under that company."""
        mock_company = MagicMock()
        mock_company.id = 1
        mock_project = MagicMock()
        mock_project.id = 10
        
        company_grant = self._create_mock_grant(CompanyRole.contributor, grant_id=200)
        
        mock_db_session.query.return_value.get.side_effect = [mock_company, mock_project]
        
        # Company grant found, but no project grant
        def filter_side_effect(*args, **kwargs):
            mock_result = MagicMock()
            mock_result.first.return_value = company_grant
            return mock_result
        
        mock_db_session.query.return_value.filter.side_effect = filter_side_effect
        
        with patch('app.helpers.access_resolver.get_portfolio_access_for_company') as mock_portfolio:
            mock_portfolio.return_value = None  # No portfolio access
            
            result = resolve_effective_access(
                user_id=1,
                company_id=1,
                db_session=mock_db_session,
                project_id=10
            )
            
            assert result.is_allowed is True
            assert any(gs.level == "company" for gs in result.grant_sources)

    def test_scenario_3_project_only_grants_that_project_only(self, mock_db_session):
        """Test spec scenario 3: project-only access grants access only to that project."""
        mock_company = MagicMock()
        mock_company.id = 1
        mock_project = MagicMock()
        mock_project.id = 10
        
        project_grant = self._create_mock_grant(CompanyRole.read_only, grant_id=300)
        
        mock_db_session.query.return_value.get.side_effect = [mock_company, mock_project]
        
        call_count = [0]
        def filter_side_effect(*args, **kwargs):
            mock_result = MagicMock()
            call_count[0] += 1
            # First call is company access (none), second is project access (found)
            if call_count[0] == 1:
                mock_result.first.return_value = None  # No company access
            else:
                mock_result.first.return_value = project_grant  # Has project access
            return mock_result
        
        mock_db_session.query.return_value.filter.side_effect = filter_side_effect
        
        with patch('app.helpers.access_resolver.get_portfolio_access_for_company') as mock_portfolio:
            mock_portfolio.return_value = None  # No portfolio access
            
            result = resolve_effective_access(
                user_id=1,
                company_id=1,
                db_session=mock_db_session,
                project_id=10
            )
            
            assert result.is_allowed is True
            assert result.effective_base_role == "read_only"
            assert any(gs.level == "project" for gs in result.grant_sources)

    def test_scenario_3_project_only_denies_other_projects(self, mock_db_session):
        """Test spec scenario 3: project-only access should not grant access to OTHER projects."""
        mock_company = MagicMock()
        mock_company.id = 1
        mock_project = MagicMock()
        mock_project.id = 20  # Different project
        
        mock_db_session.query.return_value.get.side_effect = [mock_company, mock_project]
        
        # No grants for this user to project 20
        mock_db_session.query.return_value.filter.return_value.first.return_value = None
        
        with patch('app.helpers.access_resolver.get_portfolio_access_for_company') as mock_portfolio:
            mock_portfolio.return_value = None
            
            result = resolve_effective_access(
                user_id=1,
                company_id=1,
                db_session=mock_db_session,
                project_id=20
            )
            
            assert result.is_allowed is False
            assert result.denied_reason == AccessDeniedReason.NO_APPLICABLE_GRANT.value


class TestRestrictOnlyScenarios:
    """Test restrict-only combination scenarios 4 and 5."""

    def test_scenario_4_permission_intersection_removes_module(self):
        """Test spec scenario 4: portfolio has finance.edit, company lacks finance => no finance."""
        portfolio_perms = {
            "Asset Management": {"view", "edit"},
            "Finance": {"view", "edit"},
            "Diligence": {"view"}
        }
        company_perms = {
            "Asset Management": {"view"},
            "Diligence": {"view"}
            # No Finance at all
        }
        
        result = intersect_permissions([portfolio_perms, company_perms])
        
        # Finance should be completely removed (not in company grant)
        assert "Finance" not in result
        # Asset Management should be restricted to view only
        assert result["Asset Management"] == {"view"}
        # Diligence should remain view
        assert result["Diligence"] == {"view"}

    def test_scenario_5_base_role_restriction(self):
        """Test spec scenario 5: portfolio admin + project read_only => effective read_only."""
        portfolio_grant = MagicMock()
        portfolio_grant.role = CompanyRole.company_admin
        
        project_grant = MagicMock()
        project_grant.role = CompanyRole.read_only
        
        result = effective_base_role_from_grants([portfolio_grant, project_grant])
        
        assert result == CompanyRole.read_only

    def test_scenario_5_three_way_restriction(self):
        """Three grants: portfolio admin, company contributor, project read_only => read_only."""
        portfolio_grant = MagicMock()
        portfolio_grant.role = CompanyRole.company_admin
        
        company_grant = MagicMock()
        company_grant.role = CompanyRole.contributor
        
        project_grant = MagicMock()
        project_grant.role = CompanyRole.read_only
        
        result = effective_base_role_from_grants([portfolio_grant, company_grant, project_grant])
        
        assert result == CompanyRole.read_only

    def test_permission_intersection_three_way(self):
        """Three-way permission intersection keeps only common modules/actions."""
        portfolio_perms = {
            "Asset Management": {"view", "edit"},
            "Finance": {"view", "edit"},
            "Diligence": {"view", "edit"}
        }
        company_perms = {
            "Asset Management": {"view", "edit"},
            "Finance": {"view"},  # Downgraded
            "Diligence": {"view", "edit"}
        }
        project_perms = {
            "Asset Management": {"view"},  # Further downgraded
            "Finance": {"view"},
            # No Diligence
        }
        
        result = intersect_permissions([portfolio_perms, company_perms, project_perms])
        
        # Asset Management: only view (project restriction)
        assert result["Asset Management"] == {"view"}
        # Finance: only view (company restriction)
        assert result["Finance"] == {"view"}
        # Diligence: removed (not in project grant)
        assert "Diligence" not in result


class TestPermissionsFromGrant:
    """Tests for permissions_from_grant function."""

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return MagicMock()

    def test_base_role_permissions_without_profile(self, mock_db_session):
        """Grant without role_profile uses base role defaults."""
        mock_grant = MagicMock()
        mock_grant.role = CompanyRole.company_admin
        mock_grant.role_profile_key = None
        mock_grant.module_permissions = None
        
        result = permissions_from_grant(mock_grant, mock_db_session)
        
        # Should have company_admin defaults
        assert "Asset Management" in result
        assert "edit" in result["Asset Management"]

    def test_module_override_restricts_permissions(self, mock_db_session):
        """Module override can only restrict, not expand."""
        mock_grant = MagicMock()
        mock_grant.role = CompanyRole.company_admin
        mock_grant.role_profile_key = None
        mock_grant.module_permissions = {
            "Asset Management": {"view": True, "edit": False}  # Remove edit
        }
        
        result = permissions_from_grant(mock_grant, mock_db_session)
        
        # Asset Management should only have view now
        assert result["Asset Management"] == {"view"}

    def test_role_profile_permissions(self, mock_db_session):
        """Grant with role_profile uses profile permissions."""
        mock_grant = MagicMock()
        mock_grant.role = CompanyRole.contributor
        mock_grant.role_profile_key = "asset_manager"
        mock_grant.module_permissions = None
        
        # Mock the role profile lookup
        mock_profile = MagicMock()
        mock_profile.default_module_permissions = {
            "Asset Management": {"view": True, "edit": True},
            "O&M (Production Monitoring)": {"view": True}
        }
        mock_db_session.query.return_value.filter.return_value.first.return_value = mock_profile
        
        result = permissions_from_grant(mock_grant, mock_db_session)
        
        assert "Asset Management" in result
        assert "O&M (Production Monitoring)" in result


class TestGrantSourceDataclass:
    """Tests for GrantSource dataclass."""

    def test_grant_source_creation(self):
        """GrantSource can be created with all fields."""
        source = GrantSource(
            level="portfolio",
            access_id=1,
            role="company_admin",
            has_role_profile=False,
            role_profile_key=None
        )
        assert source.level == "portfolio"
        assert source.access_id == 1
        assert source.role == "company_admin"
        assert source.has_role_profile is False

    def test_grant_source_with_role_profile(self):
        """GrantSource can track role profile."""
        source = GrantSource(
            level="company",
            access_id=2,
            role="contributor",
            has_role_profile=True,
            role_profile_key="asset_manager"
        )
        assert source.has_role_profile is True
        assert source.role_profile_key == "asset_manager"


class TestEffectiveAccessResultDataclass:
    """Tests for EffectiveAccessResult dataclass."""

    def test_allowed_result(self):
        """Allowed result has all fields populated."""
        result = EffectiveAccessResult(
            is_allowed=True,
            effective_base_role="contributor",
            effective_module_permissions={"Finance": {"view"}},
            grant_sources=[
                GrantSource(level="company", access_id=1, role="contributor")
            ]
        )
        assert result.is_allowed is True
        assert result.effective_base_role == "contributor"
        assert "Finance" in result.effective_module_permissions
        assert len(result.grant_sources) == 1

    def test_denied_result(self):
        """Denied result has reason and minimal fields."""
        result = EffectiveAccessResult(
            is_allowed=False,
            denied_reason="no_applicable_grant"
        )
        assert result.is_allowed is False
        assert result.denied_reason == "no_applicable_grant"
        assert result.effective_base_role is None
        assert result.effective_module_permissions == {}
        assert result.grant_sources == []
