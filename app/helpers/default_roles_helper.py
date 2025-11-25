from copy import deepcopy

from sqlalchemy.orm import Session

from app.crud.company_role_mapping import CompanyTypeRoleMappingCRUD
from app.crud.role import RoleCRUD
from app.helpers.permissions import get_default_permissions
from app.static.default_roles import MVP_ROLES


class DefaultRolesHelper:
    def __init__(self, db_session: Session):
        self.db_session = db_session
        self.roles_crud = RoleCRUD(self.db_session)
        self.company_role_mapping_crud = CompanyTypeRoleMappingCRUD(self.db_session)
        self.permissions_template = get_default_permissions()

    def _prepare_role_object(self, name, description, permissions):
        user_permissions = deepcopy(self.permissions_template)
        for perm in permissions:
            module, action = perm.split(".")
            user_permissions[module][action] = True
        role_obj = {"name": name, "permissions": user_permissions}
        if description:
            role_obj["description"] = description
        return role_obj

    def create_default_user_roles(self):
        """Create default user roles if not exist."""
        existing_roles = [(role.name, role.description) for role in self.roles_crud.get(skip_pagination=True)]
        for role_data in MVP_ROLES:
            role, company_type = role_data[0], role_data[1]
            role_data = self._prepare_role_object(*role)
            if not (role_data["name"], role_data["description"]) in existing_roles:
                db_role = self.roles_crud.create_item(role_data)
                self.company_role_mapping_crud.create_item({"role_id": db_role.id, "company_type": company_type})

    def delete_default_user_roles(self):
        """Delete default user roles."""
        for role in MVP_ROLES:
            self.roles_crud.delete_by_name(role[0][0])
