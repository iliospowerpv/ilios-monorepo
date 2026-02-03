"""Tests for module-level permission enforcement (Phase C).

These tests verify that the canonical permission guards correctly enforce
module-level permissions via the Effective-Access Resolver.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock

from app.helpers.access_resolver import (
    AccessDecision,
    AccessDeniedReason,
    EffectiveAccessResult,
    GrantSource,
)
from app.helpers.permission_guards import (
    require_module_permission,
    ModulePermissionDeniedReason,
)
from app.static.permissions import PermissionsModules


class TestRequireModulePermission:
    """Tests for require_module_permission function."""

    def test_user_with_entity_access_but_without_module_permission_gets_403(self):
        """User has entity access but lacks finance:view permission."""
        mock_db = Mock()
        
        with patch('app.helpers.permission_guards.resolve_effective_access') as mock_resolve:
            mock_resolve.return_value = EffectiveAccessResult(
                decision=AccessDecision.ALLOW,
                reason_code="access_granted",
                effective_base_role="contributor",
                effective_module_permissions={
                    "Asset Management": {"view", "edit"},
                },
                grant_sources=[
                    GrantSource(level="company", access_id=1, role="contributor")
                ]
            )
            
            with pytest.raises(Exception) as exc_info:
                require_module_permission(
                    user_id=1,
                    company_id=100,
                    db_session=mock_db,
                    module_key=PermissionsModules.finance.value,
                    action="view",
                )
            
            assert "403" in str(exc_info.value.status_code)
            assert "missing_module_permission" in str(exc_info.value.detail)

    def test_user_with_view_permission_but_without_edit_gets_403(self):
        """User has finance:view but lacks finance:edit permission."""
        mock_db = Mock()
        
        with patch('app.helpers.permission_guards.resolve_effective_access') as mock_resolve:
            mock_resolve.return_value = EffectiveAccessResult(
                decision=AccessDecision.ALLOW,
                reason_code="access_granted",
                effective_base_role="read_only",
                effective_module_permissions={
                    PermissionsModules.finance.value: {"view"},
                },
                grant_sources=[
                    GrantSource(level="company", access_id=1, role="read_only")
                ]
            )
            
            with pytest.raises(Exception) as exc_info:
                require_module_permission(
                    user_id=1,
                    company_id=100,
                    db_session=mock_db,
                    module_key=PermissionsModules.finance.value,
                    action="edit",
                )
            
            assert "403" in str(exc_info.value.status_code)
            assert "missing_module_permission" in str(exc_info.value.detail)

    def test_user_with_edit_permission_can_view(self):
        """User with finance:edit can also view (edit implies view)."""
        mock_db = Mock()
        
        with patch('app.helpers.permission_guards.resolve_effective_access') as mock_resolve:
            mock_resolve.return_value = EffectiveAccessResult(
                decision=AccessDecision.ALLOW,
                reason_code="access_granted",
                effective_base_role="company_admin",
                effective_module_permissions={
                    PermissionsModules.finance.value: {"view", "edit"},
                },
                grant_sources=[
                    GrantSource(level="company", access_id=1, role="company_admin")
                ]
            )
            
            result = require_module_permission(
                user_id=1,
                company_id=100,
                db_session=mock_db,
                module_key=PermissionsModules.finance.value,
                action="view",
            )
            
            assert result.decision == AccessDecision.ALLOW
            assert "view" in result.effective_module_permissions[PermissionsModules.finance.value]

    def test_user_without_entity_access_gets_403(self):
        """User without any applicable grants gets 403."""
        mock_db = Mock()
        
        with patch('app.helpers.permission_guards.resolve_effective_access') as mock_resolve:
            mock_resolve.return_value = EffectiveAccessResult(
                decision=AccessDecision.DENY,
                reason_code=AccessDeniedReason.NO_APPLICABLE_GRANT.value,
            )
            
            with pytest.raises(Exception) as exc_info:
                require_module_permission(
                    user_id=1,
                    company_id=100,
                    db_session=mock_db,
                    module_key=PermissionsModules.finance.value,
                    action="view",
                )
            
            assert "403" in str(exc_info.value.status_code)
            assert "no_applicable_grant" in str(exc_info.value.detail)


class TestIntersectionSemantics:
    """Tests for restrict-only intersection semantics."""

    def test_portfolio_with_finance_edit_company_lacks_finance_has_no_finance(self):
        """Portfolio grant has finance:edit, company grant lacks finance entirely.
        
        Result: effective has no finance permissions (intersection = empty)
        """
        mock_db = Mock()
        
        with patch('app.helpers.permission_guards.resolve_effective_access') as mock_resolve:
            mock_resolve.return_value = EffectiveAccessResult(
                decision=AccessDecision.ALLOW,
                reason_code="access_granted",
                effective_base_role="contributor",
                effective_module_permissions={},
                grant_sources=[
                    GrantSource(level="portfolio", access_id=1, role="company_admin"),
                    GrantSource(level="company", access_id=2, role="contributor"),
                ]
            )
            
            with pytest.raises(Exception) as exc_info:
                require_module_permission(
                    user_id=1,
                    company_id=100,
                    db_session=mock_db,
                    module_key=PermissionsModules.finance.value,
                    action="view",
                )
            
            assert "403" in str(exc_info.value.status_code)
            assert "missing_module_permission" in str(exc_info.value.detail)

    def test_both_grants_have_finance_view_intersection_works(self):
        """Both portfolio and company grants have finance:view.
        
        Result: effective has finance:view
        """
        mock_db = Mock()
        
        with patch('app.helpers.permission_guards.resolve_effective_access') as mock_resolve:
            mock_resolve.return_value = EffectiveAccessResult(
                decision=AccessDecision.ALLOW,
                reason_code="access_granted",
                effective_base_role="contributor",
                effective_module_permissions={
                    PermissionsModules.finance.value: {"view"},
                },
                grant_sources=[
                    GrantSource(level="portfolio", access_id=1, role="company_admin"),
                    GrantSource(level="company", access_id=2, role="contributor"),
                ]
            )
            
            result = require_module_permission(
                user_id=1,
                company_id=100,
                db_session=mock_db,
                module_key=PermissionsModules.finance.value,
                action="view",
            )
            
            assert result.decision == AccessDecision.ALLOW


class TestNormalizationRule:
    """Tests for the normalization rule: edit implies view."""

    def test_edit_implies_view_is_enforced(self):
        """When user has edit permission, view is automatically included."""
        mock_db = Mock()
        
        with patch('app.helpers.permission_guards.resolve_effective_access') as mock_resolve:
            mock_resolve.return_value = EffectiveAccessResult(
                decision=AccessDecision.ALLOW,
                reason_code="access_granted",
                effective_base_role="company_admin",
                effective_module_permissions={
                    PermissionsModules.finance.value: {"view", "edit"},
                },
                grant_sources=[
                    GrantSource(level="company", access_id=1, role="company_admin")
                ]
            )
            
            result_view = require_module_permission(
                user_id=1,
                company_id=100,
                db_session=mock_db,
                module_key=PermissionsModules.finance.value,
                action="view",
            )
            assert result_view.decision == AccessDecision.ALLOW
            
            result_edit = require_module_permission(
                user_id=1,
                company_id=100,
                db_session=mock_db,
                module_key=PermissionsModules.finance.value,
                action="edit",
            )
            assert result_edit.decision == AccessDecision.ALLOW


class TestProjectLevelPermissions:
    """Tests for project-level module permission checks."""

    def test_project_level_permission_check_includes_site_context(self):
        """Module permission check at project level includes site_id."""
        mock_db = Mock()
        
        with patch('app.helpers.permission_guards.resolve_effective_access') as mock_resolve:
            mock_resolve.return_value = EffectiveAccessResult(
                decision=AccessDecision.ALLOW,
                reason_code="access_granted",
                effective_base_role="contributor",
                effective_module_permissions={
                    PermissionsModules.assets_management.value: {"view", "edit"},
                },
                grant_sources=[
                    GrantSource(level="project", access_id=1, role="contributor")
                ]
            )
            
            result = require_module_permission(
                user_id=1,
                company_id=100,
                db_session=mock_db,
                module_key=PermissionsModules.assets_management.value,
                action="view",
                project_id=50,
            )
            
            mock_resolve.assert_called_once_with(
                user_id=1,
                company_id=100,
                db_session=mock_db,
                project_id=50,
            )
            assert result.decision == AccessDecision.ALLOW
