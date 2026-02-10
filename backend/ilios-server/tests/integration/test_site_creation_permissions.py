"""Integration tests for POST /api/sites/ endpoint permission enforcement (Phase C.1).

These tests verify that:
1. Users without assets_management:edit get 403 when creating a site
2. Users with assets_management:edit can create a site (201)
3. Default artifacts (boards, DD sections, documents, project access) are created
4. Authorization uses require_module_permission (canonical resolver), not legacy SettingsPermissions
"""

import pytest
from unittest.mock import Mock, patch, MagicMock, call
from fastapi import HTTPException

from app.schema.site import CreateSiteSchema


class TestSiteCreationPermissions:
    """Tests for POST / endpoint permission enforcement."""

    def _build_mock_user(self, user_id=1, is_system_user=False):
        mock_user = Mock()
        mock_user.id = user_id
        mock_user.is_system_user = is_system_user
        return mock_user

    def _build_site_payload(self, company_id=100):
        return CreateSiteSchema(
            company_id=company_id,
            name="Test Site",
            address="123 Main St",
            city="Springfield",
            state="NY",
            zip_code="12345",
            system_size_ac=0,
            system_size_dc=0,
            lon_lat_url="",
        )

    def test_user_without_edit_permission_gets_403(self):
        """User lacks assets_management:edit at company level -> 403."""
        mock_user = self._build_mock_user()
        site_payload = self._build_site_payload()

        with patch("app.routers.assets_management.sites.require_module_permission") as mock_perm:
            mock_perm.side_effect = HTTPException(
                status_code=403,
                detail="Access denied: missing_module_permission:Asset Management.edit",
            )

            from app.routers.assets_management.sites import create
            import asyncio

            with pytest.raises(HTTPException) as exc_info:
                asyncio.run(create(site=site_payload, current_user=mock_user, db_session=Mock()))

            assert exc_info.value.status_code == 403
            assert "missing_module_permission" in str(exc_info.value.detail)

    def test_permission_check_uses_correct_module_and_action(self):
        """Verify require_module_permission is called with assets_management:edit."""
        mock_user = self._build_mock_user()
        mock_db = Mock()
        site_payload = self._build_site_payload(company_id=42)

        mock_site_obj = Mock()
        mock_site_obj.id = 99
        mock_site_obj.company_id = 42
        mock_site_obj.documents_board = Mock()
        mock_site_obj.documents_board.related_entity = Mock()
        mock_site_obj.documents_board.related_entity.extra_entity_type = "document"
        mock_site_obj.documents = []

        with (
            patch("app.routers.assets_management.sites.require_module_permission") as mock_perm,
            patch("app.routers.assets_management.sites.SiteCRUD") as mock_site_crud,
            patch("app.routers.assets_management.sites.create_default_site_document_sections"),
            patch("app.routers.assets_management.sites.DocumentCRUD"),
            patch("app.routers.assets_management.sites.generate_default_site_documents", return_value=[]),
            patch("app.routers.assets_management.sites.create_default_board"),
            patch("app.routers.assets_management.sites.create_default_document_tasks"),
            patch("app.routers.assets_management.sites.UserProjectCRUD"),
        ):
            mock_site_crud.return_value.create_item.return_value = mock_site_obj

            from app.routers.assets_management.sites import create
            import asyncio

            asyncio.run(create(site=site_payload, current_user=mock_user, db_session=mock_db))

            mock_perm.assert_called_once_with(
                user_id=1,
                company_id=42,
                db_session=mock_db,
                module_key="Asset Management",
                action="edit",
            )

    def test_permission_check_does_not_pass_project_id(self):
        """For creation, no project_id should be passed since site doesn't exist yet."""
        mock_user = self._build_mock_user()
        mock_db = Mock()
        site_payload = self._build_site_payload()

        mock_site_obj = Mock()
        mock_site_obj.id = 1
        mock_site_obj.company_id = 100
        mock_site_obj.documents_board = Mock()
        mock_site_obj.documents_board.related_entity = Mock()
        mock_site_obj.documents_board.related_entity.extra_entity_type = "document"
        mock_site_obj.documents = []

        with (
            patch("app.routers.assets_management.sites.require_module_permission") as mock_perm,
            patch("app.routers.assets_management.sites.SiteCRUD") as mock_site_crud,
            patch("app.routers.assets_management.sites.create_default_site_document_sections"),
            patch("app.routers.assets_management.sites.DocumentCRUD"),
            patch("app.routers.assets_management.sites.generate_default_site_documents", return_value=[]),
            patch("app.routers.assets_management.sites.create_default_board"),
            patch("app.routers.assets_management.sites.create_default_document_tasks"),
            patch("app.routers.assets_management.sites.UserProjectCRUD"),
        ):
            mock_site_crud.return_value.create_item.return_value = mock_site_obj

            from app.routers.assets_management.sites import create
            import asyncio

            asyncio.run(create(site=site_payload, current_user=mock_user, db_session=mock_db))

            call_kwargs = mock_perm.call_args[1]
            assert "project_id" not in call_kwargs


class TestSiteCreationSideEffects:
    """Tests for creation side-effects: boards, DD sections, documents, project access."""

    def _build_mock_user(self, user_id=1, is_system_user=False):
        mock_user = Mock()
        mock_user.id = user_id
        mock_user.is_system_user = is_system_user
        return mock_user

    def _build_site_payload(self, company_id=100):
        return CreateSiteSchema(
            company_id=company_id,
            name="Test Site",
            address="123 Main St",
            city="Springfield",
            state="NY",
            zip_code="12345",
            system_size_ac=0,
            system_size_dc=0,
            lon_lat_url="",
        )

    def _run_create_with_mocks(self, mock_user=None, site_id=1, company_id=100):
        if mock_user is None:
            mock_user = self._build_mock_user()

        mock_db = Mock()
        site_payload = self._build_site_payload(company_id=company_id)

        mock_site_obj = Mock()
        mock_site_obj.id = site_id
        mock_site_obj.company_id = company_id
        mock_site_obj.documents_board = Mock()
        mock_site_obj.documents_board.related_entity = Mock()
        mock_site_obj.documents_board.related_entity.extra_entity_type = "document"
        mock_site_obj.documents = [Mock(), Mock()]

        mocks = {}
        with (
            patch("app.routers.assets_management.sites.require_module_permission") as mock_perm,
            patch("app.routers.assets_management.sites.SiteCRUD") as mock_site_crud,
            patch("app.routers.assets_management.sites.create_default_site_document_sections") as mock_dd_sections,
            patch("app.routers.assets_management.sites.DocumentCRUD") as mock_doc_crud,
            patch("app.routers.assets_management.sites.generate_default_site_documents", return_value=[]) as mock_gen_docs,
            patch("app.routers.assets_management.sites.create_default_board") as mock_board,
            patch("app.routers.assets_management.sites.create_default_document_tasks") as mock_doc_tasks,
            patch("app.routers.assets_management.sites.UserProjectCRUD") as mock_user_project,
        ):
            mock_site_crud.return_value.create_item.return_value = mock_site_obj
            mocks = {
                "perm": mock_perm,
                "site_crud": mock_site_crud,
                "dd_sections": mock_dd_sections,
                "doc_crud": mock_doc_crud,
                "gen_docs": mock_gen_docs,
                "board": mock_board,
                "doc_tasks": mock_doc_tasks,
                "user_project": mock_user_project,
                "site_obj": mock_site_obj,
                "db": mock_db,
            }

            from app.routers.assets_management.sites import create
            import asyncio

            result = asyncio.run(create(site=site_payload, current_user=mock_user, db_session=mock_db))
            mocks["result"] = result

        return mocks

    def test_creates_dd_sections_for_new_site(self):
        mocks = self._run_create_with_mocks(site_id=55)
        mocks["dd_sections"].assert_called_once_with([55], mocks["db"])

    def test_creates_default_documents_for_new_site(self):
        mocks = self._run_create_with_mocks(site_id=55)
        mocks["gen_docs"].assert_called_once_with([55], mocks["db"])
        mocks["doc_crud"].return_value.create_items.assert_called_once()

    def test_creates_three_default_boards(self):
        from app.models.board import BoardModuleEnum, BoardRelatedEntityTypeEnum, BoardRelatedEntityTypeExtraEnum

        mocks = self._run_create_with_mocks(site_id=10)
        assert mocks["board"].call_count == 3

        calls = mocks["board"].call_args_list
        assert calls[0] == call(10, BoardRelatedEntityTypeEnum.site, mocks["db"])
        assert calls[1] == call(10, BoardRelatedEntityTypeEnum.site, mocks["db"], module=BoardModuleEnum.om)
        assert calls[2] == call(10, BoardRelatedEntityTypeEnum.site, mocks["db"], BoardRelatedEntityTypeExtraEnum.document)

    def test_creates_default_document_tasks(self):
        mocks = self._run_create_with_mocks()
        mocks["doc_tasks"].assert_called_once_with(
            mocks["db"],
            mocks["site_obj"].documents_board,
            mocks["site_obj"].documents,
            1,
            freeze_external_id=True,
        )

    def test_assigns_project_access_for_non_system_user(self):
        mock_user = self._build_mock_user(user_id=5, is_system_user=False)
        mocks = self._run_create_with_mocks(mock_user=mock_user, site_id=20, company_id=100)
        mocks["user_project"].return_value.create_item.assert_called_once_with(
            {"user_id": 5, "site_id": 20, "company_id": 100}
        )

    def test_skips_project_access_for_system_user(self):
        mock_user = self._build_mock_user(user_id=1, is_system_user=True)
        mocks = self._run_create_with_mocks(mock_user=mock_user)
        mocks["user_project"].return_value.create_item.assert_not_called()

    def test_returns_201_with_site_id(self):
        mocks = self._run_create_with_mocks(site_id=42)
        result = mocks["result"]
        assert result["code"] == 201
        assert result["id"] == 42
        assert result["message"] == "Site has been created"


class TestSiteCreationNoLegacyAuth:
    """Verify the endpoint does NOT use legacy authorization patterns."""

    def test_no_settings_permissions_dependency(self):
        """The create endpoint must NOT use SettingsPermissions (legacy pattern)."""
        import inspect
        from app.routers.assets_management.sites import create

        source = inspect.getsource(create)
        assert "SettingsPermissions" not in source
        assert "AuthorizedUser" not in source

    def test_no_parent_company_id_check(self):
        """The create endpoint must NOT use manual parent_company_id check (legacy pattern)."""
        import inspect
        from app.routers.assets_management.sites import create

        source = inspect.getsource(create)
        assert "parent_company_id" not in source

    def test_uses_require_module_permission(self):
        """The create endpoint must use require_module_permission (canonical resolver)."""
        import inspect
        from app.routers.assets_management.sites import create

        source = inspect.getsource(create)
        assert "require_module_permission" in source
