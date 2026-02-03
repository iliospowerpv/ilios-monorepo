"""Unit tests for GetAuthorizedEntity integration with Canonical Effective-Access Resolver.

Phase B.1: Tests that GetAuthorizedEntity uses resolver as authoritative source
with no legacy fallback. If resolver denies, access is denied.
"""

import pytest
from unittest.mock import MagicMock, patch

from fastapi import HTTPException

from app.helpers.access_resolver import (
    AccessDecision,
    AccessDeniedReason,
    EffectiveAccessResult,
)
from app.helpers.authorization.project_access import GetAuthorizedEntity
from app.static import PermissionType


class TestGetAuthorizedEntityNoLegacyFallback:
    """Tests that GetAuthorizedEntity uses resolver without legacy fallback."""

    @pytest.fixture
    def mock_user(self):
        """Create a mock user that is NOT a system user."""
        user = MagicMock()
        user.id = 1
        user.is_system_user = False
        user.companies = []
        user.sites = []
        user.parent_company_id = None
        return user

    @pytest.fixture
    def mock_db_session(self):
        """Create a mock database session."""
        return MagicMock()

    @pytest.fixture
    def mock_site_entity(self):
        """Create a mock site entity."""
        site = MagicMock()
        site.id = 10
        site.company_id = 1
        return site

    @pytest.fixture
    def mock_company_entity(self):
        """Create a mock company entity."""
        company = MagicMock()
        company.id = 1
        return company

    def test_resolver_deny_raises_403_no_fallback(
        self, mock_user, mock_db_session, mock_site_entity
    ):
        """When resolver denies, 403 is raised without attempting legacy fallback."""
        deny_result = EffectiveAccessResult(
            decision=AccessDecision.DENY,
            reason_code=AccessDeniedReason.NO_APPLICABLE_GRANT.value
        )

        with patch(
            'app.helpers.authorization.project_access.resolve_effective_access'
        ) as mock_resolve:
            mock_resolve.return_value = deny_result

            entity_handler = GetAuthorizedEntity(
                company_site_id=10,
                current_user=mock_user,
                db_session=mock_db_session,
                permission_type=PermissionType.site,
            )

            with pytest.raises(HTTPException) as exc_info:
                entity_handler._validate_access_given(mock_site_entity)

            assert exc_info.value.status_code == 403
            assert AccessDeniedReason.NO_APPLICABLE_GRANT.value in exc_info.value.detail

    def test_resolver_allow_grants_access(
        self, mock_user, mock_db_session, mock_site_entity
    ):
        """When resolver allows, access is granted."""
        allow_result = EffectiveAccessResult(
            decision=AccessDecision.ALLOW,
            reason_code="access_granted",
            effective_base_role="contributor",
            grant_sources=[]
        )

        with patch(
            'app.helpers.authorization.project_access.resolve_effective_access'
        ) as mock_resolve:
            mock_resolve.return_value = allow_result

            entity_handler = GetAuthorizedEntity(
                company_site_id=10,
                current_user=mock_user,
                db_session=mock_db_session,
                permission_type=PermissionType.site,
            )

            entity_handler._validate_access_given(mock_site_entity)

            assert entity_handler._access_result is not None
            assert entity_handler._access_result.decision == AccessDecision.ALLOW

    def test_missing_entity_context_denies_with_undetermined_context(
        self, mock_user, mock_db_session
    ):
        """When entity is None, should deny with undetermined_context reason."""
        entity_handler = GetAuthorizedEntity(
            company_site_id=10,
            current_user=mock_user,
            db_session=mock_db_session,
            permission_type=PermissionType.site,
        )

        with pytest.raises(HTTPException) as exc_info:
            entity_handler._validate_access_given(entity=None)

        assert exc_info.value.status_code == 403
        assert AccessDeniedReason.UNDETERMINED_CONTEXT.value in exc_info.value.detail

    def test_missing_company_id_on_site_denies_with_undetermined_context(
        self, mock_user, mock_db_session
    ):
        """When site entity lacks company_id, should deny with undetermined_context."""
        site_without_company = MagicMock()
        site_without_company.id = 10

        entity_handler = GetAuthorizedEntity(
            company_site_id=10,
            current_user=mock_user,
            db_session=mock_db_session,
            permission_type=PermissionType.site,
        )

        with pytest.raises(HTTPException) as exc_info:
            entity_handler._validate_access_given(site_without_company)

        assert exc_info.value.status_code == 403
        assert AccessDeniedReason.UNDETERMINED_CONTEXT.value in exc_info.value.detail

    def test_system_user_bypasses_resolver(
        self, mock_db_session, mock_site_entity
    ):
        """System users should bypass resolver entirely."""
        system_user = MagicMock()
        system_user.id = 0
        system_user.is_system_user = True

        entity_handler = GetAuthorizedEntity(
            company_site_id=10,
            current_user=system_user,
            db_session=mock_db_session,
            permission_type=PermissionType.site,
        )

        with patch(
            'app.helpers.authorization.project_access.resolve_effective_access'
        ) as mock_resolve:
            entity_handler._validate_access_given(mock_site_entity)
            mock_resolve.assert_not_called()

    def test_company_access_uses_resolver(
        self, mock_user, mock_db_session, mock_company_entity
    ):
        """Company access should also use resolver as authoritative source."""
        allow_result = EffectiveAccessResult(
            decision=AccessDecision.ALLOW,
            reason_code="access_granted",
            effective_base_role="company_admin",
            grant_sources=[]
        )

        with patch(
            'app.helpers.authorization.project_access.resolve_effective_access'
        ) as mock_resolve:
            mock_resolve.return_value = allow_result

            entity_handler = GetAuthorizedEntity(
                company_site_id=1,
                current_user=mock_user,
                db_session=mock_db_session,
                permission_type=PermissionType.company,
            )

            entity_handler._validate_access_given(mock_company_entity)

            mock_resolve.assert_called_once_with(
                user_id=mock_user.id,
                company_id=1,
                db_session=mock_db_session,
                project_id=None
            )

    def test_resolver_exception_denies_with_system_error(
        self, mock_user, mock_db_session, mock_site_entity
    ):
        """When resolver raises exception, should deny with system_error reason."""
        with patch(
            'app.helpers.authorization.project_access.resolve_effective_access'
        ) as mock_resolve:
            mock_resolve.side_effect = Exception("Database connection error")

            entity_handler = GetAuthorizedEntity(
                company_site_id=10,
                current_user=mock_user,
                db_session=mock_db_session,
                permission_type=PermissionType.site,
            )

            with pytest.raises(HTTPException) as exc_info:
                entity_handler._validate_access_given(mock_site_entity)

            assert exc_info.value.status_code == 403
            assert AccessDeniedReason.SYSTEM_ERROR.value in exc_info.value.detail

    def test_access_result_available_for_explainability(
        self, mock_user, mock_db_session, mock_site_entity
    ):
        """Access result should be available for auditing/explainability."""
        from app.helpers.access_resolver import GrantSource

        allow_result = EffectiveAccessResult(
            decision=AccessDecision.ALLOW,
            reason_code="access_granted",
            effective_base_role="contributor",
            grant_sources=[
                GrantSource(level="portfolio", access_id=100, role="contributor"),
                GrantSource(level="company", access_id=200, role="read_only"),
            ]
        )

        with patch(
            'app.helpers.authorization.project_access.resolve_effective_access'
        ) as mock_resolve:
            mock_resolve.return_value = allow_result

            entity_handler = GetAuthorizedEntity(
                company_site_id=10,
                current_user=mock_user,
                db_session=mock_db_session,
                permission_type=PermissionType.site,
            )

            entity_handler._validate_access_given(mock_site_entity)

            result = entity_handler.get_access_result()
            assert result is not None
            assert result.effective_base_role == "contributor"
            assert len(result.grant_sources) == 2
