import copy

import pytest

from app.crud.company_role_mapping import CompanyTypeRoleMappingCRUD
from app.crud.role import RoleCRUD
from app.helpers.permissions import get_default_permissions
from tests.unit import samples


@pytest.fixture(scope="function", params=[samples.TEST_COMPANY_TYPE])
def role_id(db_session, request):
    """Create role with all permissions turned on"""
    role_crud = RoleCRUD(db_session)
    company_type_role_mapping_crud = CompanyTypeRoleMappingCRUD(db_session)

    # adjust permissions
    default_permissions = get_default_permissions()
    permissions = copy.deepcopy(default_permissions)
    for module_name, module_permissions in default_permissions.items():
        for action_name in module_permissions.keys():
            permissions[module_name][action_name] = True

    test_role = role_crud.create_item({"name": "test", "permissions": permissions})

    test_company_type_role_mapping = company_type_role_mapping_crud.create_item(
        {"role_id": test_role.id, "company_type": request.param}
    )

    yield test_role.id

    company_type_role_mapping_crud.delete_by_id(test_company_type_role_mapping.id)
    role_crud.delete_by_id(test_role.id)


@pytest.fixture(scope="function")
def limit_role_dd_overview_access(db_session, role_id):
    # patch user role company type
    company_type_role_mapping_crud = CompanyTypeRoleMappingCRUD(db_session)
    mapping_details = company_type_role_mapping_crud.get_by_id(role_id)
    company_type_role_mapping_crud.update_by_id(role_id, {"company_type": samples.TEST_COMPANY_TYPE2})

    yield

    # rollback changes
    company_type_role_mapping_crud.update_by_id(role_id, {"company_type": mapping_details.company_type})
