import copy
from unittest.mock import Mock

import pytest

from app.crud.session import SessionCRUD
from app.crud.user import UserCRUD
from app.crud.user_project import UserProjectCRUD
from app.helpers.authentication import AuthenticationHandler, get_current_user
from app.settings import settings
from tests.conftest import test_app
from tests.unit import samples


@pytest.fixture(scope="session")
def system_user_id(db_session):
    return UserCRUD(db_session).get_by_email(settings.system_user_email).id


@pytest.fixture(scope="session")
def system_user_session_id(db_session, system_user_id):
    return SessionCRUD(db_session).create_item({"user_id": system_user_id}).id


@pytest.fixture(scope="session")
def system_user_jwt(system_user_session_id):
    """Returns system user JWT"""
    return AuthenticationHandler().create_access_token({"sub": system_user_session_id})


@pytest.fixture(scope="session")
def system_user_auth_header(system_user_jwt):
    return {"Authorization": f"Bearer {system_user_jwt}"}


@pytest.fixture(scope="function")
def func_scoped_system_user_auth_header(db_session, system_user_id):
    """System user auth header that can be used for logout operations testing at the function-level scope.

    Why it exists? Well, if you decide to use similar session-scoped sibling system_user_auth_header for the logout
    test such user's session will be removed causing all consequent tests to fail with 401.
    """
    session_id = SessionCRUD(db_session).create_item({"user_id": system_user_id}).id
    jwt_token = AuthenticationHandler().create_access_token({"sub": session_id})
    return {"Authorization": f"Bearer {jwt_token}"}


@pytest.fixture(scope="function")
# TODO discuss possible renaming, since it return an object: create_non_system_user -> non_system_user
def create_non_system_user(db_session):
    """Creates non-system non-admin with no company access user in db."""
    user_crud = UserCRUD(db_session)
    user = user_crud.create_item(
        {
            "first_name": samples.NON_SYSTEM_USER_NAME,
            "last_name": samples.NON_SYSTEM_USER_LAST_NAME,
            "email": samples.NON_SYSTEM_USER_EMAIL,
            "is_registered": True,
            "phone": "1234567890",
        }
    )

    yield user

    user_crud.delete_by_id(user.id)


@pytest.fixture(scope="function")
def non_system_user_id(create_non_system_user):
    """Return non-system non-admin user ID"""

    return create_non_system_user.id


@pytest.fixture(scope="function")
def non_system_user_session_id(db_session, non_system_user_id):
    return SessionCRUD(db_session).create_item({"user_id": non_system_user_id}).id


@pytest.fixture(scope="function")
def non_system_user_jwt(non_system_user_session_id):
    """Return non-system user JWT"""
    return AuthenticationHandler().create_access_token({"sub": non_system_user_session_id})


@pytest.fixture(scope="function")
def non_system_user_auth_header(non_system_user_jwt):
    return {"Authorization": f"Bearer {non_system_user_jwt}"}


@pytest.fixture(scope="function")
def user_payload(company_id, role_id, site_id):
    """Dynamically create user payload data."""
    user_payload = copy.deepcopy(samples.BASE_USER_OBJECT)
    user_payload.update(
        {
            "role_id": role_id,
            "parent_company_id": company_id,
            "sites_ids": [site_id],
            "phone": "1234567890",
        }
    )

    yield user_payload


@pytest.fixture(scope="function")
def company_member_user(db_session, client, user_payload, system_user_auth_header, site_id):
    """Create company member with company level access and no company-admin rights."""
    user_data = copy.deepcopy(user_payload)
    site_id = user_data.pop("sites_ids")[0]
    user_crud = UserCRUD(db_session)
    user = user_crud.create_item(user_data)
    # Setup user project access
    UserProjectCRUD(db_session).create_item(
        {"user_id": user.id, "company_id": user.parent_company_id, "site_id": site_id}
    )

    yield user

    user_crud.delete_by_id(user.id)


@pytest.fixture(scope="function")
def company_member_user_session_id(db_session, company_member_user):
    return SessionCRUD(db_session).create_item({"user_id": company_member_user.id}).id


@pytest.fixture(scope="function")
def company_member_user_jwt(company_member_user_session_id):
    """Return company member non-company-admin user JWT"""
    return AuthenticationHandler().create_access_token({"sub": company_member_user_session_id})


@pytest.fixture(scope="function")
def company_member_user_auth_header(company_member_user_jwt):
    return {"Authorization": f"Bearer {company_member_user_jwt}"}


@pytest.fixture(scope="function", params=[False])
def user_obj_raw(db_session, request):
    """
    Create user object directly to DB, without dependent entities.
    Params corresponds to value of the 'is_registered' flag.
    """
    payload = copy.deepcopy(samples.BASE_USER_OBJECT)
    payload["is_registered"] = request.param
    user_crud = UserCRUD(db_session)
    user = user_crud.create_item(payload)

    yield user

    user_crud.delete_by_id(user.id)


@pytest.fixture(scope="function")
def fake_get_current_user():
    get_current_user_spy = Mock()
    get_current_user_spy.get_limited_sites_ids.return_value = None
    get_current_user_spy.is_system_user = False

    test_app.dependency_overrides[get_current_user] = lambda: get_current_user_spy
    # why lambda? https://github.com/tiangolo/fastapi/issues/3331

    yield get_current_user_spy

    test_app.dependency_overrides[get_current_user] = get_current_user
