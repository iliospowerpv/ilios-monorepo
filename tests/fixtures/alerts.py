import enum

import pytest
from random import choice

from app.crud.alert import AlertCRUD
from app.models.alert import AlertSeverity


class AlertType(enum.Enum):
    inverter_energy_ratio = "1133 - Inverter Energy Ratio"
    device_communication = "250 - Device Communication"
    inverter_faults = "511 - Sungrow Inverter Faults"


class AlertErrorMessage(enum.Enum):
    no_device_connection = "No connection with device"
    abnormal_alarm = "String 13 abnormal alarm run"


def generate_random_alert(device_id):
    return {
        "type": choice(tuple(AlertType)).value,
        "error_message": choice(tuple(AlertErrorMessage)).value,
        "severity": choice(tuple(AlertSeverity)),
        "device_id": device_id,
    }


@pytest.fixture(scope="function", params=[1])
def alerts(request, db_session, device_id):
    amount_of_alerts = request.param
    alerts_crud = AlertCRUD(db_session)
    generated_alerts = []
    for _ in range(amount_of_alerts):
        alert_data = generate_random_alert(device_id)
        generated_alert = alerts_crud.create_item(alert_data)
        generated_alerts.append(generated_alert)

    yield generated_alerts

    for generated_alert in generated_alerts:
        alerts_crud.delete_by_id(generated_alert.id)
