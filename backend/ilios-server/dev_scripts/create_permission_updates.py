import sys
import pathlib
from pprint import pprint

sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.resolve()))

from app.static.default_roles import MVP_ROLES
from app.crud.role import RoleCRUD
from app.helpers.default_roles_helper import DefaultRolesHelper
from app.db.session import get_session


def create_permissions():
    """Method generates list of permissions that changed after update in default_roles.py in a format required for
    migration. List format is described in app/db/migration_utils.py"""
    session = next(get_session())
    role_helper = DefaultRolesHelper(session)
    roles_permissions = []
    existing_roles = {
        (role.name, role.description): role.permissions for role in RoleCRUD(session).get(skip_pagination=True)
    }
    for role_data in MVP_ROLES:
        role, company = role_data[0], role_data[1]
        role_data = role_helper._prepare_role_object(*role)
        old_permissions = existing_roles.get((role_data["name"], role_data["description"]))
        if old_permissions != role_data["permissions"]:
            roles_permissions.append(
                {
                    "name": role_data["name"],
                    "company_type": company.name,
                    "new_permissions": str(role_data["permissions"]).replace("False", "false").replace("True", "true"),
                    "old_permissions": str(old_permissions).replace("False", "false").replace("True", "true"),
                }
            )
    print(str(roles_permissions).replace("'", '"').replace('"{', "'''{").replace('}"', "}'''"))


if __name__ == "__main__":
    create_permissions()
