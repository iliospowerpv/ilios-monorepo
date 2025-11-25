from app.static.messages import BaseMessageEnum


class PermissionsModules(BaseMessageEnum):
    assets_management = "Asset Management"
    diligence = "Diligence"
    # todo rename to 'om' like in the rest of the app
    operation_maintenance = "O&M (Production Monitoring)"
    investor_dashboard = "Investor Dashboard"
    role_based_dashboard = "Role-based Homepage/Tab"
    settings = "Settings Page"
    reporting = "Reports"


class PermissionsActions(BaseMessageEnum):
    view = "view"
    edit = "edit"


class PermissionType:
    site = "site"
    company = "company"
