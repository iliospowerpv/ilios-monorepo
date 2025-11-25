import pytest

from app.crud.role import RoleCRUD
from app.helpers.authentication import AuthenticationHandler
from app.helpers.permissions import get_default_permissions
from app.static import PermissionsActions, PermissionsModules


@pytest.fixture(scope="function")
def settings_management_allow_view(db_session, role_id):
    # Set allow view permissions
    allow_view_permissions = get_default_permissions()
    allow_view_permissions["Settings Page"]["view"] = True
    RoleCRUD(db_session).update_by_id(role_id, {"permissions": allow_view_permissions})
    yield
    RoleCRUD(db_session).update_by_id(role_id, {"permissions": get_default_permissions()})


@pytest.fixture(scope="function")
def settings_management_allow_edit(db_session, role_id):
    # Set allow edit permissions
    allow_view_permissions = get_default_permissions()
    allow_view_permissions["Settings Page"]["edit"] = True
    allow_view_permissions["Settings Page"]["view"] = True
    RoleCRUD(db_session).update_by_id(role_id, {"permissions": allow_view_permissions})
    yield
    RoleCRUD(db_session).update_by_id(role_id, {"permissions": get_default_permissions()})


@pytest.fixture(scope="function")
def company_admin_full_access_header(company_member_user_session_id, settings_management_allow_edit):
    company_admin_jwt = AuthenticationHandler().create_access_token({"sub": company_member_user_session_id})
    return {"Authorization": f"Bearer {company_admin_jwt}"}


@pytest.fixture(scope="function")
def company_admin_read_access_header(company_member_user_session_id, settings_management_allow_view):
    company_admin_jwt = AuthenticationHandler().create_access_token({"sub": company_member_user_session_id})
    return {"Authorization": f"Bearer {company_admin_jwt}"}


@pytest.fixture(scope="function")
def role_without_reports_access(db_session, role_id):
    patched_permissions = get_default_permissions()
    patched_permissions[PermissionsModules.reporting.value][PermissionsActions.view.value] = False
    patched_permissions[PermissionsModules.reporting.value][PermissionsActions.edit.value] = False
    RoleCRUD(db_session).update_by_id(role_id, {"permissions": patched_permissions})
    yield
    RoleCRUD(db_session).update_by_id(role_id, {"permissions": get_default_permissions()})
