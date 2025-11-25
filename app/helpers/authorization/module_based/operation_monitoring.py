from app.helpers.authorization.module_based.base import AuthorizedUserSinglePermissionChecker
from app.static import PermissionsModules


# TODO consider module renaming
class OnMPermissions(AuthorizedUserSinglePermissionChecker):
    """Builder of non-admin user obj getters with applied authorization checks specific for O&M (Production Monitoring)
    permissions module and actions."""

    def __init__(self, action, validate_query_module_name=False):
        super().__init__(
            permission_module=PermissionsModules.operation_maintenance,
            action=action,
            validate_query_module_name=validate_query_module_name,
        )
