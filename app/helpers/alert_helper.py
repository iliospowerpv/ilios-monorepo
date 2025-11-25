from app.helpers.alerts import get_max_severity
from app.static.alerts import AssetType

MAX_RANDOM_ALERTS_PER_DEVICE = 3


def get_alerts_overview(instance_id, instance_alerts, asset_type: AssetType):
    """Get alerts overview for each type of asset - total alerts and highest severity.

    :param instance_id: id of the asset instance company/site/device
    :param instance_alerts: list of alerts for specific type of asset
    :param asset_type: type of asset"""

    alerts_overview = {
        "total": 0,
        "severity": None,
    }
    # mapping between asset type and ID column names
    type_id_mapping = {
        AssetType.company: "company_id",
        AssetType.site: "site_id",
        AssetType.device: "device_id",
    }
    alerts_info = list(
        filter(lambda company_alert: getattr(company_alert, type_id_mapping[asset_type]) == instance_id, instance_alerts)
    )
    if alerts_info:
        alert_info = alerts_info[0]
        alerts_overview["total"] = alert_info.total
        alerts_overview["severity"] = get_max_severity(alert_info.severity)
    return alerts_overview
