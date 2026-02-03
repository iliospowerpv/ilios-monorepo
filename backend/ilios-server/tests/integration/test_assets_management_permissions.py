"""Integration tests for assets_management module permission enforcement (Phase C.1).

These tests verify that:
1. Users with entity access but missing assets_management:view get 403
2. Users with assets_management:view but missing assets_management:edit get 403 on mutations
3. Users with assets_management:edit can perform mutations
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

from app.helpers.access_resolver import (
    AccessDecision,
    EffectiveAccessResult,
    GrantSource,
)


class TestSiteDetailsPermissions:
    """Tests for PUT /{site_id}/details endpoint permission enforcement."""

    def test_user_with_entity_access_but_no_view_permission_gets_403(self):
        """User has entity access (can see site) but lacks assets_management:view."""
        mock_site = Mock()
        mock_site.id = 1
        mock_site.company_id = 100
        mock_site.additional_fields = None
        
        mock_user = Mock()
        mock_user.id = 1
        mock_user.is_system_user = False
        
        with patch('app.routers.assets_management.sites.get_authorized_site') as mock_auth_site:
            with patch('app.routers.assets_management.sites.require_module_permission') as mock_perm:
                from fastapi import HTTPException
                mock_perm.side_effect = HTTPException(
                    status_code=403,
                    detail="Access denied: missing_module_permission:Asset Management.view"
                )
                
                from app.routers.assets_management.sites import get_site_details
                import asyncio
                
                with pytest.raises(HTTPException) as exc_info:
                    asyncio.run(get_site_details(
                        current_user=mock_user,
                        site=mock_site,
                        db_session=Mock()
                    ))
                
                assert exc_info.value.status_code == 403
                assert "missing_module_permission" in str(exc_info.value.detail)

    def test_user_with_view_but_no_edit_permission_gets_403_on_mutation(self):
        """User has assets_management:view but lacks assets_management:edit for PUT."""
        mock_site = Mock()
        mock_site.id = 1
        mock_site.company_id = 100
        mock_site.additional_fields = Mock()
        mock_site.additional_fields.id = 1
        
        mock_user = Mock()
        mock_user.id = 1
        mock_user.is_system_user = False
        
        with patch('app.routers.assets_management.sites.require_module_permission') as mock_perm:
            from fastapi import HTTPException
            mock_perm.side_effect = HTTPException(
                status_code=403,
                detail="Access denied: missing_module_permission:Asset Management.edit"
            )
            
            from app.routers.assets_management.sites import update_site_details
            from app.static.sites import SiteDetailsSections
            import asyncio
            
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(update_site_details(
                    data={"cod": "2024-01-01"},
                    section_name=SiteDetailsSections.key_dates,
                    background_tasks=Mock(),
                    current_user=mock_user,
                    site=mock_site,
                    db_session=Mock(),
                    section_schema=Mock()
                ))
            
            assert exc_info.value.status_code == 403
            assert "edit" in str(exc_info.value.detail)

    def test_user_with_edit_permission_can_mutate(self):
        """User with assets_management:edit can successfully update site details."""
        mock_site = Mock()
        mock_site.id = 1
        mock_site.company_id = 100
        mock_site.additional_fields = Mock()
        mock_site.additional_fields.id = 1
        
        mock_user = Mock()
        mock_user.id = 1
        mock_user.is_system_user = False
        
        access_result = EffectiveAccessResult(
            decision=AccessDecision.ALLOW,
            reason_code="access_granted",
            effective_base_role="company_admin",
            effective_module_permissions={
                "Asset Management": {"view", "edit"},
            },
            grant_sources=[GrantSource(level="company", access_id=1, role="company_admin")]
        )
        
        with patch('app.routers.assets_management.sites.require_module_permission') as mock_perm:
            mock_perm.return_value = access_result
            
            with patch('app.routers.assets_management.sites.SiteAdditionalFieldListCRUD') as mock_crud:
                mock_crud_instance = Mock()
                mock_crud.return_value = mock_crud_instance
                
                from app.routers.assets_management.sites import update_site_details
                from app.static.sites import SiteDetailsSections
                from pydantic import BaseModel
                import asyncio
                
                class MockSchema(BaseModel):
                    cod: str = None
                    
                    def model_dump(self):
                        return {"cod": "2024-01-01"}
                
                result = asyncio.run(update_site_details(
                    data={"cod": "2024-01-01"},
                    section_name=SiteDetailsSections.key_dates,
                    background_tasks=Mock(),
                    current_user=mock_user,
                    site=mock_site,
                    db_session=Mock(),
                    section_schema=MockSchema
                ))
                
                assert result["code"] == 202
                mock_perm.assert_called_once()
                call_kwargs = mock_perm.call_args.kwargs
                assert call_kwargs["action"] == "edit"
                assert call_kwargs["module_key"] == "Asset Management"


class TestDevicePermissions:
    """Tests for device endpoints permission enforcement."""

    def test_device_get_requires_view_permission(self):
        """GET /devices/{device_id} requires assets_management:view."""
        mock_device = Mock()
        mock_device.id = 1
        mock_device.site_id = 10
        mock_device.site = Mock()
        mock_device.site.company_id = 100
        
        mock_user = Mock()
        mock_user.id = 1
        mock_user.is_system_user = False
        
        with patch('app.routers.assets_management.devices.require_module_permission') as mock_perm:
            from fastapi import HTTPException
            mock_perm.side_effect = HTTPException(
                status_code=403,
                detail="Access denied: missing_module_permission:Asset Management.view"
            )
            
            from app.routers.assets_management.devices import get_by_id
            import asyncio
            
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(get_by_id(
                    current_user=mock_user,
                    device=mock_device,
                    db_session=Mock()
                ))
            
            assert exc_info.value.status_code == 403
            call_kwargs = mock_perm.call_args.kwargs
            assert call_kwargs["action"] == "view"

    def test_device_update_requires_edit_permission(self):
        """PUT /devices/{device_id}/general-info requires assets_management:edit."""
        mock_device = Mock()
        mock_device.id = 1
        mock_device.site_id = 10
        mock_device.site = Mock()
        mock_device.site.company_id = 100
        mock_device.status = "active"
        
        mock_user = Mock()
        mock_user.id = 1
        mock_user.is_system_user = False
        
        with patch('app.routers.assets_management.devices.require_module_permission') as mock_perm:
            from fastapi import HTTPException
            mock_perm.side_effect = HTTPException(
                status_code=403,
                detail="Access denied: missing_module_permission:Asset Management.edit"
            )
            
            from app.routers.assets_management.devices import update_general_info
            import asyncio
            
            mock_payload = Mock()
            mock_payload.model_dump.return_value = {
                "name": "Test",
                "telemetry_device_id": None,
                "telemetry_device_name": None,
            }
            
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(update_general_info(
                    device_payload=mock_payload,
                    current_user=mock_user,
                    device=mock_device,
                    db_session=Mock()
                ))
            
            assert exc_info.value.status_code == 403
            call_kwargs = mock_perm.call_args.kwargs
            assert call_kwargs["action"] == "edit"


class TestModulePermissionIntegration:
    """Tests verifying integration between entity access and module permissions."""

    def test_entity_access_checked_before_module_permission(self):
        """Verify that entity access (get_authorized_site) is checked before module permission."""
        from app.routers.assets_management.sites import get_site_details
        import inspect
        
        source = inspect.getsource(get_site_details)
        site_param_pos = source.find("site: Site")
        require_perm_pos = source.find("require_module_permission")
        
        assert site_param_pos < require_perm_pos, (
            "Entity access (via site parameter) should be resolved before "
            "require_module_permission is called"
        )

    def test_module_permission_uses_entity_context(self):
        """Verify that module permission check uses company_id and project_id from entity."""
        mock_site = Mock()
        mock_site.id = 42
        mock_site.company_id = 100
        mock_site.additional_fields = Mock()
        
        mock_user = Mock()
        mock_user.id = 1
        mock_user.is_system_user = False
        
        access_result = EffectiveAccessResult(
            decision=AccessDecision.ALLOW,
            reason_code="access_granted",
            effective_base_role="contributor",
            effective_module_permissions={"Asset Management": {"view"}},
            grant_sources=[GrantSource(level="project", access_id=42, role="contributor")]
        )
        
        with patch('app.routers.assets_management.sites.require_module_permission') as mock_perm:
            mock_perm.return_value = access_result
            
            from app.routers.assets_management.sites import get_site_details
            from app.db.object_utils import as_dict
            import asyncio
            
            with patch('app.routers.assets_management.sites.get_site_cards_with_dd_data') as mock_cards:
                mock_cards.return_value = {}
                with patch('app.routers.assets_management.sites.as_dict') as mock_as_dict:
                    mock_as_dict.return_value = {}
                    
                    asyncio.run(get_site_details(
                        current_user=mock_user,
                        site=mock_site,
                        db_session=Mock()
                    ))
            
            call_kwargs = mock_perm.call_args.kwargs
            assert call_kwargs["company_id"] == 100, "Should use site.company_id"
            assert call_kwargs["project_id"] == 42, "Should use site.id as project_id"
            assert call_kwargs["user_id"] == 1


class TestListEndpointPermissions:
    """Tests for list endpoints (GET /sites, GET /companies) permission enforcement."""

    def test_sites_list_requires_view_permission_on_any_context(self):
        """GET /sites requires assets_management:view on at least one accessible company or project."""
        mock_user = Mock()
        mock_user.id = 1
        mock_user.is_system_user = False
        mock_user.get_limited_companies_ids.return_value = [100, 200]
        mock_user.get_limited_sites_ids.return_value = [1, 2, 3]
        
        with patch('app.routers.assets_management.sites.require_module_permission_any_context') as mock_any_perm:
            from fastapi import HTTPException
            mock_any_perm.side_effect = HTTPException(
                status_code=403,
                detail="Access denied: missing_module_permission:Asset Management.view"
            )
            
            from app.routers.assets_management.sites import get
            from app.filters.site_filters import SiteFilter
            import asyncio
            
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(get(
                    query_params=(0, 10, "name", "asc"),
                    current_user=mock_user,
                    site_filter=SiteFilter(),
                    db_session=Mock()
                ))
            
            assert exc_info.value.status_code == 403
            call_kwargs = mock_any_perm.call_args.kwargs
            assert call_kwargs["action"] == "view"
            assert call_kwargs["company_ids"] == [100, 200]
            assert call_kwargs["site_ids"] == [1, 2, 3]

    def test_companies_list_requires_view_permission_on_any_context(self):
        """GET /companies requires assets_management:view on at least one accessible company or project."""
        mock_user = Mock()
        mock_user.id = 1
        mock_user.is_system_user = False
        mock_user.get_limited_companies_ids.return_value = [100, 200]
        mock_user.get_limited_sites_ids.return_value = [1, 2, 3]
        
        with patch('app.routers.assets_management.companies.require_module_permission_any_context') as mock_any_perm:
            from fastapi import HTTPException
            mock_any_perm.side_effect = HTTPException(
                status_code=403,
                detail="Access denied: missing_module_permission:Asset Management.view"
            )
            
            from app.routers.assets_management.companies import get
            from app.filters.company_filters import SearchCompanyByName
            import asyncio
            
            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(get(
                    query_params=(0, 10, "name", "asc"),
                    company_filter=SearchCompanyByName(),
                    current_user=mock_user,
                    db_session=Mock()
                ))
            
            assert exc_info.value.status_code == 403
            call_kwargs = mock_any_perm.call_args.kwargs
            assert call_kwargs["action"] == "view"
            assert call_kwargs["company_ids"] == [100, 200]
            assert call_kwargs["site_ids"] == [1, 2, 3]

    def test_system_user_bypasses_list_permission_check(self):
        """System user should bypass module permission check on list endpoints."""
        mock_user = Mock()
        mock_user.id = 1
        mock_user.is_system_user = True
        mock_user.get_limited_companies_ids.return_value = []
        mock_user.get_limited_sites_ids.return_value = []
        
        with patch('app.routers.assets_management.sites.require_module_permission_any_context') as mock_any_perm:
            with patch('app.routers.assets_management.sites.SiteCRUD') as mock_crud:
                mock_crud_instance = Mock()
                mock_crud_instance.filter.return_value = (0, [])
                mock_crud.return_value = mock_crud_instance
                
                from app.routers.assets_management.sites import get
                from app.filters.site_filters import SiteFilter
                import asyncio
                
                result = asyncio.run(get(
                    query_params=(0, 10, "name", "asc"),
                    current_user=mock_user,
                    site_filter=SiteFilter(),
                    db_session=Mock()
                ))
                
                mock_any_perm.assert_not_called()
                assert "items" in result


class TestRequireModulePermissionAnyContext:
    """Tests for require_module_permission_any_context helper function."""

    def test_returns_true_when_user_has_permission_on_first_company(self):
        """Should return True when user has permission on first company."""
        with patch('app.helpers.permission_guards.resolve_effective_access') as mock_resolve:
            mock_resolve.return_value = EffectiveAccessResult(
                decision=AccessDecision.ALLOW,
                reason_code="access_granted",
                effective_base_role="contributor",
                effective_module_permissions={"Asset Management": {"view", "edit"}},
                grant_sources=[GrantSource(level="company", access_id=100, role="contributor")]
            )
            
            from app.helpers.permission_guards import require_module_permission_any_context
            
            result = require_module_permission_any_context(
                user_id=1,
                company_ids=[100, 200],
                site_ids=[],
                db_session=Mock(),
                module_key="Asset Management",
                action="view"
            )
            
            assert result is True
            mock_resolve.assert_called_once()

    def test_checks_projects_when_companies_lack_permission(self):
        """Should check projects when user has no company-level permission."""
        mock_site = Mock()
        mock_site.company_id = 100
        
        with patch('app.helpers.permission_guards.resolve_effective_access') as mock_resolve:
            with patch('app.helpers.permission_guards.SiteCRUD') as mock_site_crud:
                mock_site_crud_instance = Mock()
                mock_site_crud_instance.get_by_id.return_value = mock_site
                mock_site_crud.return_value = mock_site_crud_instance
                
                no_permission_result = EffectiveAccessResult(
                    decision=AccessDecision.ALLOW,
                    reason_code="access_granted",
                    effective_base_role="read_only",
                    effective_module_permissions={},
                    grant_sources=[GrantSource(level="company", access_id=100, role="read_only")]
                )
                has_permission_result = EffectiveAccessResult(
                    decision=AccessDecision.ALLOW,
                    reason_code="access_granted",
                    effective_base_role="contributor",
                    effective_module_permissions={"Asset Management": {"view"}},
                    grant_sources=[GrantSource(level="project", access_id=42, role="contributor")]
                )
                mock_resolve.side_effect = [no_permission_result, has_permission_result]
                
                from app.helpers.permission_guards import require_module_permission_any_context
                
                result = require_module_permission_any_context(
                    user_id=1,
                    company_ids=[100],
                    site_ids=[42],
                    db_session=Mock(),
                    module_key="Asset Management",
                    action="view"
                )
                
                assert result is True
                assert mock_resolve.call_count == 2

    def test_raises_403_when_no_context_has_permission(self):
        """Should raise 403 when user has no module permission on any context."""
        mock_site = Mock()
        mock_site.company_id = 100
        
        with patch('app.helpers.permission_guards.resolve_effective_access') as mock_resolve:
            with patch('app.helpers.permission_guards.SiteCRUD') as mock_site_crud:
                mock_site_crud_instance = Mock()
                mock_site_crud_instance.get_by_id.return_value = mock_site
                mock_site_crud.return_value = mock_site_crud_instance
                
                mock_resolve.return_value = EffectiveAccessResult(
                    decision=AccessDecision.ALLOW,
                    reason_code="access_granted",
                    effective_base_role="read_only",
                    effective_module_permissions={},
                    grant_sources=[GrantSource(level="company", access_id=100, role="read_only")]
                )
                
                from app.helpers.permission_guards import require_module_permission_any_context
                from fastapi import HTTPException
                
                with pytest.raises(HTTPException) as exc_info:
                    require_module_permission_any_context(
                        user_id=1,
                        company_ids=[100],
                        site_ids=[42],
                        db_session=Mock(),
                        module_key="Asset Management",
                        action="view"
                    )
                
                assert exc_info.value.status_code == 403
                assert "missing_module_permission" in str(exc_info.value.detail)

    def test_raises_403_when_no_accessible_context(self):
        """Should raise 403 when user has no accessible companies or projects."""
        from app.helpers.permission_guards import require_module_permission_any_context
        from fastapi import HTTPException
        
        with pytest.raises(HTTPException) as exc_info:
            require_module_permission_any_context(
                user_id=1,
                company_ids=[],
                site_ids=[],
                db_session=Mock(),
                module_key="Asset Management",
                action="view"
            )
        
        assert exc_info.value.status_code == 403
        assert "no accessible context" in str(exc_info.value.detail)

    def test_project_only_user_can_access_list_endpoints(self):
        """User with only project-level access should be able to access list endpoints."""
        mock_site = Mock()
        mock_site.company_id = 100
        
        with patch('app.helpers.permission_guards.resolve_effective_access') as mock_resolve:
            with patch('app.helpers.permission_guards.SiteCRUD') as mock_site_crud:
                mock_site_crud_instance = Mock()
                mock_site_crud_instance.get_by_id.return_value = mock_site
                mock_site_crud.return_value = mock_site_crud_instance
                
                has_permission_result = EffectiveAccessResult(
                    decision=AccessDecision.ALLOW,
                    reason_code="access_granted",
                    effective_base_role="contributor",
                    effective_module_permissions={"Asset Management": {"view"}},
                    grant_sources=[GrantSource(level="project", access_id=42, role="contributor")]
                )
                mock_resolve.return_value = has_permission_result
                
                from app.helpers.permission_guards import require_module_permission_any_context
                
                result = require_module_permission_any_context(
                    user_id=1,
                    company_ids=[],
                    site_ids=[42],
                    db_session=Mock(),
                    module_key="Asset Management",
                    action="view"
                )
                
                assert result is True
