from enum import Enum

OM_COMPANY_DASHBOARD_TOP_NUMBER = 7


class AssetType(Enum):
    """Possible types of assets for Alerts"""

    company = "company"
    site = "site"
    device = "device"
