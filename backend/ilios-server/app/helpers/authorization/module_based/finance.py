"""Finance module authorization."""

from app.helpers.authorization.module_based.base import AuthorizedUserSinglePermissionChecker
from app.static.permissions import PermissionsModules


class FinancePermissions(AuthorizedUserSinglePermissionChecker):
    """Builder of non-admin user obj getters with applied authorization checks specific for Finance
    permissions module and actions."""

    def __init__(self, action, validate_query_module_name=False):
        super().__init__(
            permission_module=PermissionsModules.finance,
            action=action,
            validate_query_module_name=validate_query_module_name,
        )
