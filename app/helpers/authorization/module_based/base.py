import logging
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status

from app.helpers.authentication import get_current_user
from app.schema.user import CurrentUserSchema

logger = logging.getLogger(__name__)


def get_current_admin_user(current_user: Annotated[CurrentUserSchema, Depends(get_current_user)]):
    """Provide current user object if it is system user, otherwise throws 403 HTTPException."""
    if not current_user.is_system_user:
        logger.info(f"User {current_user.id} tried to access system-user endpoint without such status.")
        raise HTTPException(status.HTTP_403_FORBIDDEN)
    return current_user


class AuthorizedUserSinglePermissionChecker:
    """Builder of non-admin user obj getters with applied authorization checks specific for permissions modules and
    actions."""

    def __init__(self, permission_module, action, validate_query_module_name, query_parameter_name="permission_module"):
        self.permission_module = permission_module
        self.action = action
        self.validate_query_module_name = validate_query_module_name
        self.query_parameter_name = query_parameter_name

    def __call__(self, current_user: CurrentUserSchema, request: Request):
        permissions_provided = current_user.role.permissions.get(self.permission_module.value, {}).get(self.action.value)
        if self.validate_query_module_name:
            # query module name validation requires permission be matched with the module name from request
            query_param = request.query_params.get(self.query_parameter_name)
            if permissions_provided and query_param == self.permission_module.value:
                return True
        else:
            # otherwise check only permission from the role
            if permissions_provided:
                return True

        return False


class AuthorizedUser:

    def __init__(self, required_permissions_list):
        if not isinstance(required_permissions_list, list):
            required_permissions_list = [required_permissions_list]
        self.required_permissions_list = required_permissions_list

    def __call__(self, current_user: Annotated[CurrentUserSchema, Depends(get_current_user)], request: Request):
        """Check at least one of required actions are allowed to provide access"""
        if current_user.is_system_user:
            return current_user

        if not current_user.role:
            logger.warning(f"User with ID <{current_user.id}> doesn't have a role")
            raise HTTPException(status.HTTP_403_FORBIDDEN)

        action_allowed = any(
            [permissions_class(current_user, request) is True for permissions_class in self.required_permissions_list]
        )
        if action_allowed:
            return current_user

        logger.warning(
            f"User with ID <{current_user.id}> (role <{current_user.role.name}>) is not authorized "
            f"for the endpoint <{request.url.path}>"
        )
        raise HTTPException(status.HTTP_403_FORBIDDEN)
