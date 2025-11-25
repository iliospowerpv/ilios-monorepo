import pytest

from app.crud.alert import AlertCRUD
from app.crud.device import DeviceCRUD
from app.models.alert import AlertSeverity
from tests.fixtures.alerts import AlertErrorMessage, AlertType
from tests.unit.samples.alerts import ASCENDING_ORDERED_ALERTS_TYPES, DESCENDING_ORDERED_ALERTS_TYPES


class TestAlert:
    ALERTS_ENDPOINT = "/api/operations-and-maintenance/alerts"
    FAKE_ALERTS_ENDPOINT = "/api/internal/fake-alerts"

    @pytest.mark.parametrize(
        "auth_header_getter",
        (
            # system user
            lambda system_user_auth_header, non_system_user_auth_header: system_user_auth_header,
            # non-system user
            lambda system_user_auth_header, non_system_user_auth_header: non_system_user_auth_header,
        ),
    )
    def test_get_device_alerts(
        self,
        client,
        system_user_auth_header,
        company_member_user_auth_header,
        device_id,
        alerts,
        auth_header_getter,
    ):
        """Test that non-system or system is able to get alerts with different allowed params combination"""
        response = client.get(
            f"{self.ALERTS_ENDPOINT}/devices/{device_id}",
            headers=auth_header_getter(system_user_auth_header, company_member_user_auth_header),
        )
        assert response.status_code == 200

        response_items = response.json()["items"]
        assert len(response_items) == 1

        response_alert = response_items[0]
        assert response_alert["error_message"] in AlertErrorMessage
        assert response_alert["severity"] in AlertSeverity
        assert response_alert["type"] in AlertType
        assert response_alert["device_id"] == device_id
        assert response_alert["task"] is None
        assert response_alert["alert_end"] is None

    @pytest.mark.parametrize(
        "auth_header_getter",
        (
            # system user
            lambda system_user_auth_header, non_system_user_auth_header: system_user_auth_header,
            # non-system user
            lambda system_user_auth_header, non_system_user_auth_header: non_system_user_auth_header,
        ),
    )
    def test_get_site_alerts(
        self,
        client,
        system_user_auth_header,
        company_member_user_auth_header,
        device_id,
        site_id,
        alerts,
        auth_header_getter,
        db_session,
    ):
        response = client.get(
            f"{self.ALERTS_ENDPOINT}/sites/{site_id}",
            headers=auth_header_getter(system_user_auth_header, company_member_user_auth_header),
        )
        assert response.status_code == 200

        response_items = response.json()["items"]
        assert len(response_items) == 1

        response_alert = response_items[0]
        assert response_alert["error_message"] in AlertErrorMessage
        assert response_alert["severity"] in AlertSeverity
        assert response_alert["type"] in AlertType
        assert response_alert["device_id"] == device_id
        assert response_alert["device_name"] == DeviceCRUD(db_session).get_by_id(device_id).name
        assert response_alert["task"] is None
        assert response_alert["alert_end"] is None

    @pytest.mark.parametrize(
        "auth_header_getter",
        (
            # system user
            lambda system_user_auth_header, non_system_user_auth_header: system_user_auth_header,
            # non-system user
            lambda system_user_auth_header, non_system_user_auth_header: non_system_user_auth_header,
        ),
    )
    def test_get_company_alerts(
        self,
        client,
        system_user_auth_header,
        company_member_user_auth_header,
        device_id,
        site,
        company_id,
        alerts,
        auth_header_getter,
        db_session,
    ):
        response = client.get(
            f"{self.ALERTS_ENDPOINT}/companies/{company_id}",
            headers=auth_header_getter(system_user_auth_header, company_member_user_auth_header),
        )
        assert response.status_code == 200

        response_items = response.json()["items"]
        assert len(response_items) == 1

        response_alert = response_items[0]
        assert response_alert["error_message"] in AlertErrorMessage
        assert response_alert["severity"] in AlertSeverity
        assert response_alert["type"] in AlertType
        assert response_alert["device_id"] == device_id
        assert response_alert["device_name"] == DeviceCRUD(db_session).get_by_id(device_id).name
        assert response_alert["site_name"] == site.name
        assert response_alert["task"] is None
        assert response_alert["alert_end"] is None
        assert response_alert["site_id"] == site.id

    @pytest.mark.parametrize(
        "target_entity",
        ("devices", "companies"),
    )
    def test_get_404(self, client, company_member_user_auth_header, target_entity):
        """Test that GET throws 404 if requested entity is not found"""
        response = client.get(f"{self.ALERTS_ENDPOINT}/{target_entity}/12321", headers=company_member_user_auth_header)
        assert response.status_code == 404

    @pytest.mark.parametrize(
        "target_entity, id_getter",
        (
            ("devices", lambda device_id, site_id, company_id: device_id),
            ("companies", lambda device_id, site_id, company_id: company_id),
            ("sites", lambda device_id, site_id, company_id: site_id),
        ),
    )
    def test_get_alerts_missing_access(
        self, client, non_system_user_auth_header, target_entity, id_getter, device_id, site_id, company_id
    ):
        target_id = id_getter(device_id, site_id, company_id)
        response = client.get(
            f"{self.ALERTS_ENDPOINT}/{target_entity}/{target_id}",
            headers=non_system_user_auth_header,
        )
        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"

    @pytest.mark.parametrize(
        "auth_header_getter",
        (
            # system user
            lambda system_user_auth_header, non_system_user_auth_header: system_user_auth_header,
            # non-system user
            lambda system_user_auth_header, non_system_user_auth_header: non_system_user_auth_header,
        ),
    )
    def test_edit_alert(
        self,
        client,
        system_user_auth_header,
        company_member_user_auth_header,
        db_session,
        device_id,
        site_id,
        alerts,
        auth_header_getter,
    ):
        auth_header = auth_header_getter(system_user_auth_header, company_member_user_auth_header)
        alert_crud = AlertCRUD(db_session)
        alert_id = alerts[0].id
        alert = alert_crud.get_by_id(alert_id)
        alert.is_resolved = False
        db_session.commit()
        assert alert.is_resolved is False
        assert alert.alert_end is None

        # edit alert
        response = client.put(
            f"{self.ALERTS_ENDPOINT}/{alert_id}/resolve",
            headers=auth_header,
        )
        assert response.status_code == 202
        assert response.json()["message"] == "Alert has been successfully updated"

        # fetch alert
        get_response = client.get(
            f"{self.ALERTS_ENDPOINT}/devices/{device_id}", headers=auth_header, params={"is_resolved": True}
        )
        assert get_response.status_code == 200
        assert get_response.json()["items"][0]["is_resolved"]
        assert get_response.json()["items"][0]["alert_end"] is not None

    @pytest.mark.parametrize(
        "alert_id_getter, expected_status_code, auth_header_getter",
        (
            # test edit alert with curr user missing site access:
            (
                lambda alert: alert.id,
                403,
                lambda non_system_user_auth_header, company_member_user_auth_header: non_system_user_auth_header,
            ),
            # test edit non-existing alert:
            (
                lambda alert: alert.id + 999999,
                404,
                lambda non_system_user_auth_header, company_member_user_auth_header: company_member_user_auth_header,
            ),
        ),
    )
    def test_edit_alert_unhappy_path(
        self,
        client,
        non_system_user_auth_header,
        company_member_user_auth_header,
        alerts,
        alert_id_getter,
        expected_status_code,
        auth_header_getter,
    ):
        response = client.put(
            f"{self.ALERTS_ENDPOINT}/{alert_id_getter(alerts[0])}/resolve",
            headers=auth_header_getter(non_system_user_auth_header, company_member_user_auth_header),
        )

        assert response.status_code == expected_status_code

    @pytest.mark.parametrize(
        "alerts, target_entity, id_getter",
        (
            (2, "devices", lambda device_id, site_id, company_id: device_id),
            (2, "companies", lambda device_id, site_id, company_id: company_id),
            (2, "sites", lambda device_id, site_id, company_id: site_id),
        ),
        indirect=["alerts"],
    )
    def test_get_alerts_is_resolved(
        self,
        client,
        system_user_auth_header,
        db_session,
        alerts,
        device_id,
        site_id,
        company_id,
        target_entity,
        id_getter,
    ):
        """Test GET alerts endpoints with is_resolved query param"""
        AlertCRUD(db_session).get_by_id(alerts[0].id).is_resolved = True
        db_session.commit()

        target_id = id_getter(device_id, site_id, company_id)

        # fetch with missing is_resolved query param which means all alerts fetch disregarding status
        response = client.get(
            f"{self.ALERTS_ENDPOINT}/{target_entity}/{target_id}",
            headers=system_user_auth_header,
        )

        assert response.status_code == 200
        assert len(response.json()["items"]) == 2

        # fetch and test resolved alerts
        response = client.get(
            f"{self.ALERTS_ENDPOINT}/{target_entity}/{target_id}",
            headers=system_user_auth_header,
            params={"is_resolved": True},
        )

        assert response.status_code == 200
        assert response.json()["items"][0]["is_resolved"]

        # fetch and test non-resolved alerts
        response = client.get(
            f"{self.ALERTS_ENDPOINT}/{target_entity}/{target_id}",
            headers=system_user_auth_header,
            params={"is_resolved": False},
        )

        assert response.status_code == 200
        assert len(response.json()["items"]) == 1

    @pytest.mark.parametrize(
        "alerts, target_entity, id_getter, order_direction, expected_first_severity, expected_second_severity",
        (
            # asc, [c]ritical should go before [w]arning
            (
                2,
                "devices",
                lambda device_id, site_id, company_id: device_id,
                "asc",
                AlertSeverity.critical.value,
                AlertSeverity.warning.value,
            ),
            (
                2,
                "sites",
                lambda device_id, site_id, company_id: site_id,
                "asc",
                AlertSeverity.critical.value,
                AlertSeverity.warning.value,
            ),
            (
                2,
                "companies",
                lambda device_id, site_id, company_id: company_id,
                "asc",
                AlertSeverity.critical.value,
                AlertSeverity.warning.value,
            ),
            # desc, [w]arning should go before [c]ritical
            (
                2,
                "devices",
                lambda device_id, site_id, company_id: device_id,
                "desc",
                AlertSeverity.warning.value,
                AlertSeverity.critical.value,
            ),
            (
                2,
                "sites",
                lambda device_id, site_id, company_id: site_id,
                "desc",
                AlertSeverity.warning.value,
                AlertSeverity.critical.value,
            ),
            (
                2,
                "companies",
                lambda device_id, site_id, company_id: company_id,
                "desc",
                AlertSeverity.warning.value,
                AlertSeverity.critical.value,
            ),
        ),
        indirect=["alerts"],
    )
    def test_get_w_ordering_by_severity(
        self,
        client,
        system_user_auth_header,
        device_id,
        site_id,
        company_id,
        db_session,
        alerts,
        target_entity,
        id_getter,
        order_direction,
        expected_first_severity,
        expected_second_severity,
    ):
        """Test that system user is able to get alerts with ordering by severity"""
        alert, another_alert = alerts
        alert.severity = "critical"
        another_alert.severity = "warning"
        db_session.commit()

        response = client.get(
            f"{self.ALERTS_ENDPOINT}/{target_entity}/{id_getter(device_id, site_id, company_id)}",
            headers=system_user_auth_header,
            params={"order_by": "severity", "order_direction": order_direction},
        )
        assert response.status_code == 200

        response_items = response.json()["items"]
        assert len(response_items) == 2

        assert response_items[0]["severity"] == expected_first_severity
        assert response_items[1]["severity"] == expected_second_severity

    @pytest.mark.parametrize(
        "alerts, target_entity, id_getter, order_direction, expected_first_type, expected_second_type, "
        "expected_third_type",
        (
            # asc, "1133 - Inverter Energy Ratio" should go before "250 - Device communication"
            (3, "devices", lambda device_id, site_id, company_id: device_id, "asc", *ASCENDING_ORDERED_ALERTS_TYPES),
            (3, "sites", lambda device_id, site_id, company_id: site_id, "asc", *ASCENDING_ORDERED_ALERTS_TYPES),
            (3, "companies", lambda device_id, site_id, company_id: company_id, "asc", *ASCENDING_ORDERED_ALERTS_TYPES),
            # desc, "511 - Sungrow inverter faults" should go before "250 - Device communication"
            (3, "devices", lambda device_id, site_id, company_id: device_id, "desc", *DESCENDING_ORDERED_ALERTS_TYPES),
            (3, "sites", lambda device_id, site_id, company_id: site_id, "desc", *DESCENDING_ORDERED_ALERTS_TYPES),
            (
                3,
                "companies",
                lambda device_id, site_id, company_id: company_id,
                "desc",
                *DESCENDING_ORDERED_ALERTS_TYPES,
            ),
        ),
        indirect=["alerts"],
    )
    def test_get_w_ordering_by_type(
        self,
        client,
        system_user_auth_header,
        device_id,
        site_id,
        company_id,
        db_session,
        alerts,
        target_entity,
        id_getter,
        order_direction,
        expected_first_type,
        expected_second_type,
        expected_third_type,
    ):
        """Test that system user is able to get alerts with ordering by type.

        Tests fix for IOSP1-863 bug.
        """
        alert, second_alert, third_alert = alerts
        alert.type = AlertType.inverter_energy_ratio.value  # "1133 - Inverter Energy Ratio"
        second_alert.type = AlertType.device_communication.value  # "250 - Device communication"
        third_alert.type = AlertType.inverter_faults.value  # "511 - Sungrow inverter faults"
        db_session.commit()

        response = client.get(
            f"{self.ALERTS_ENDPOINT}/{target_entity}/{id_getter(device_id, site_id, company_id)}",
            headers=system_user_auth_header,
            params={"order_by": "type", "order_direction": order_direction},
        )
        assert response.status_code == 200

        response_items = response.json()["items"]
        assert len(response_items) == 3

        assert response_items[0]["type"] == expected_first_type
        assert response_items[1]["type"] == expected_second_type
        assert response_items[2]["type"] == expected_third_type
