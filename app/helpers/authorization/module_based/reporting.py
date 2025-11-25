import logging

from app.helpers.authorization.module_based.base import AuthorizedUserSinglePermissionChecker
from app.static import PermissionsModules

logger = logging.getLogger(__name__)


class ReportingPermissions(AuthorizedUserSinglePermissionChecker):
    """Builder of non-admin user obj getters with applied authorization checks specific for Reporting
    permissions module and actions."""

    def __init__(self, action, validate_query_module_name=False):
        super().__init__(
            permission_module=PermissionsModules.reporting,
            action=action,
            validate_query_module_name=validate_query_module_name,
        )
