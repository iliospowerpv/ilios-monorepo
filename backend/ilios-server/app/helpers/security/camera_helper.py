from datetime import datetime

from app.static import ALERT_MAPPING_TYPES


def map_cameras_alerts(cameras, alerts):
    cameras_alerts = []
    for camera in cameras:
        for alert in alerts:
            if alert["deviceUuid"] == camera["uuid"]:
                alert_type = ", ".join(
                    [
                        ALERT_MAPPING_TYPES.get(alert_trigger, alert_trigger)
                        for alert_trigger in alert["policyAlertTriggers"]
                    ]
                )
                cameras_alerts.append(
                    {
                        "alert_uuid": alert["uuid"],
                        "camera_name": camera["name"],
                        "alert_type": alert_type,
                        "timestamp": datetime.fromtimestamp(alert["timestampMs"] / 1000).strftime(
                            "%Y-%m-%dT%H:%M:%S.%f"
                        ),
                    }
                )
    return cameras_alerts
