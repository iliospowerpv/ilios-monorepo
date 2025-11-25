from app.models.alert import AlertSeverity
from tests.fixtures.alerts import AlertType

ASCENDING_ORDERED_ALERTS_TYPES = [
    AlertType.inverter_energy_ratio.value,
    AlertType.device_communication.value,
    AlertType.inverter_faults.value,
]
DESCENDING_ORDERED_ALERTS_TYPES = [
    AlertType.inverter_faults.value,
    AlertType.device_communication.value,
    AlertType.inverter_energy_ratio.value,
]


TEST_ALERT_BODY = {
    "severity": AlertSeverity.critical.value,
    "alert_start": "2024-10-23T14:15:42.524913",
    "type": "inverter_energy_ratio",
    "is_resolved": False,
    "error_message": "device connection failed",
    "external_id": "121w2DFw",
}
