import pickle
from copy import deepcopy
from datetime import date

import pytest
from pydantic.v1.utils import deep_update

import tests.unit.samples as samples
from app.crud.device import DeviceCRUD
from app.crud.site_additional_fields_list import SiteAdditionalFieldListCRUD
from app.crud.telemetry_mapping import TelemetryDeviceMappingCRUD
from app.models.device import DeviceCategories, DeviceManufacturers, DeviceStatuses, DeviceTypes
from app.schema.device_technical_detail import (
    InverterTechnicalDetailsViewSchema,
    MeterTechnicalDetailsSchema,
    RachMountTechnicalDetailsSchema,
)
from app.static import DeviceMessages, TelemetryMessages
from tests.utils import create_response, set_user_site_access


class TestDevices:
    """Tests for devices routes."""

    @staticmethod
    def _generate_device_endpoint(_site_id):
        return f"/api/sites/{_site_id}/devices"

    def _generate_device_section_endpoint(self, _site_id, _device_id, section_name):
        return f"{self._generate_device_endpoint(_site_id)}/{_device_id}/{section_name}"

    def _generate_device_general_info_endpoint(self, _site_id, _device_id):
        return self._generate_device_section_endpoint(_site_id, _device_id, "general-info")

    def _generate_device_service_details_endpoint(self, _site_id, _device_id):
        return self._generate_device_section_endpoint(_site_id, _device_id, "service-details")

    def _generate_device_technical_details_endpoint(self, _site_id, _device_id):
        return self._generate_device_section_endpoint(_site_id, _device_id, "technical-details")

    def _generate_device_telemetry_details_endpoint(self, _site_id, _device_id):
        return self._generate_device_section_endpoint(_site_id, _device_id, "telemetry-details")

    @pytest.mark.parametrize(
        "auth_header_getter",
        (
            # system user
            lambda system_user_auth_header, company_member_user_auth_header: system_user_auth_header,
            # company member user
            lambda system_user_auth_header, company_member_user_auth_header: company_member_user_auth_header,
        ),
    )
    def test_get_site_devices(
        self, client, site_id, device_id, system_user_auth_header, company_member_user_auth_header, auth_header_getter
    ):
        """Test that GET sites with devices returns list of devices."""

        response = client.get(
            self._generate_device_endpoint(site_id),
            headers=auth_header_getter(system_user_auth_header, company_member_user_auth_header),
        )
        response_json = response.json()
        response_device = response_json["items"][0]

        assert response.status_code == 200
        assert len(response_json["items"]) == 1
        assert response_json["items"][0]["name"] == samples.TEST_INVERTER_DEVICE_NAME
        for field_name, value in response_json["items"][0].items():
            assert response_device[field_name] == value

    def test_get_site_devices_without_access(self, client, site_id, company_member_user_auth_header):
        response = client.get(self._generate_device_endpoint(site_id + 1), headers=company_member_user_auth_header)

        assert response.status_code == 404

    def test_get_site_devices_empty(self, client, site_id, company_member_user_auth_header):
        """Test that GET sites with devices returns empty list of devices."""
        response = client.get(self._generate_device_endpoint(site_id), headers=company_member_user_auth_header)

        assert response.status_code == 200
        assert len(response.json()["items"]) == 0

    @pytest.mark.parametrize(
        "payload,auth_header_getter",
        (
            # system user creates inverter - has both type and manufacturer
            (
                samples.VALID_DEVICE_BODY,
                lambda system_user_auth_header, company_member_user_auth_header: system_user_auth_header,
            ),
            # company member creates camera - has only type
            (
                samples.VALID_DEVICE_BODY_CAMERA,
                lambda system_user_auth_header, company_member_user_auth_header: company_member_user_auth_header,
            ),
            # company member creates meter - doesn't have type and manufacturer
            (
                samples.VALID_DEVICE_BODY_METER,
                lambda system_user_auth_header, company_member_user_auth_header: company_member_user_auth_header,
            ),
        ),
    )
    def test_device_creation_success(
        self, client, site_id, system_user_auth_header, company_member_user_auth_header, payload, auth_header_getter
    ):
        """Test that with valid body device will be created and endpoint returns 201 Created status code."""
        response = client.post(
            self._generate_device_endpoint(site_id),
            json=payload,
            headers=auth_header_getter(system_user_auth_header, company_member_user_auth_header),
        )

        assert response.status_code == 201
        assert response.json()["message"] == "Device has been successfully created"
        assert response.json().get("device_id")

    def test_device_creation_with_telemetry_success(
        self,
        client,
        site_id,
        system_user_auth_header,
        company_member_user_auth_header,
        mocker,
        fs_company_config_with_site,
        telemetry_site_mapping,
    ):
        """Test that with valid body device including telemetry device and device mapping will be created and endpoint
        returns 201 Created status code."""
        mocker.patch("app.helpers.telemetry.firestore_client.service_account")
        fs_client_mock = mocker.patch("app.helpers.telemetry.firestore_client.firestore.Client")
        mocker.patch("app.helpers.telemetry.secrets_manager.service_account")
        get_fs_config_mock = fs_client_mock.return_value.collection.return_value.document.return_value.get
        get_fs_config_mock.return_value = fs_company_config_with_site
        set_fs_config_mock = fs_client_mock.return_value.collection.return_value.document.return_value.set

        payload = deepcopy(samples.VALID_DEVICE_BODY)
        payload["telemetry_device_id"] = "12sad"
        payload["telemetry_device_name"] = "Test telemetry device"

        response = client.post(
            self._generate_device_endpoint(site_id),
            json=payload,
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 201
        assert response.json()["message"] == "Device has been successfully created"
        assert get_fs_config_mock.call_count == 1
        assert set_fs_config_mock.call_count == 1

    def test_device_creation_with_default_fields_success(
        self, client, site_id, system_user_auth_header, company_member_user_auth_header, db_session
    ):
        """Test that with valid body device will be created and endpoint returns 201 Created status code."""
        response = client.post(
            self._generate_device_endpoint(site_id),
            json=samples.VALID_DEVICE_BODY_METER,
            headers=company_member_user_auth_header,
        )
        created_device = DeviceCRUD(db_session).get()[0]

        assert response.status_code == 201
        assert response.json()["message"] == "Device has been successfully created"

        assert created_device.type == DeviceTypes.other
        assert created_device.manufacturer == DeviceManufacturers.other
        assert created_device.status == DeviceStatuses.available_inventory

    @pytest.mark.parametrize(
        ("source_payload", "target_field_name", "invalid_value", "expected_msg"),
        ((samples.VALID_DEVICE_BODY, "category", "Device", samples.INVALID_DEVICE_CATEGORY_MSG),),
    )
    def test_device_creation_with_invalid_body(
        self,
        client,
        site_id,
        company_member_user_auth_header,
        source_payload,
        target_field_name,
        invalid_value,
        expected_msg,
    ):
        """Test that with invalid body (missing essential field) the device won't be created and endpoint returns
        422 Unprocessable entity.
        """
        invalid_body = deepcopy(source_payload)
        invalid_body[target_field_name] = invalid_value

        response = client.post(
            self._generate_device_endpoint(site_id), json=invalid_body, headers=company_member_user_auth_header
        )

        assert response.status_code == 422
        assert response.json()["message"] == expected_msg

    @pytest.mark.parametrize(
        "field_name,invalid_field_value,expected_msg",
        (
            ("name", "", samples.DEVICE_NAME_TOO_SHORT_ERROR_MSG),
            ("name", "a" * 101, samples.DEVICE_NAME_TOO_LONG_ERROR_MSG),
        ),
    )
    def test_device_creation_with_invalid_field_limits(
        self, client, site_id, company_member_user_auth_header, field_name, invalid_field_value, expected_msg
    ):
        """Test that device fields have correct limitations."""
        invalid_body = deepcopy(samples.VALID_DEVICE_BODY)
        invalid_body[field_name] = invalid_field_value

        response = client.post(
            self._generate_device_endpoint(site_id), json=invalid_body, headers=company_member_user_auth_header
        )

        assert response.status_code == 422
        assert response.json()["message"] == expected_msg

    def test_get_devices_search_by_name(self, client, site_id, device_id, company_member_user_auth_header):
        response = client.get(
            self._generate_device_endpoint(site_id),
            params={"search": samples.TEST_INVERTER_DEVICE_NAME},
            headers=company_member_user_auth_header,
        )
        response_json = response.json()

        assert response.status_code == 200
        assert response_json["skip"] == 0
        assert response_json["limit"] == 10

        assert len(response_json["items"]) == 1
        assert response_json["items"][0]["name"] == samples.TEST_INVERTER_DEVICE_NAME

    def test_get_device_by_id_404(self, client, site_id, device_id, company_member_user_auth_header):
        response = client.get(
            f"{self._generate_device_endpoint(site_id)}/{device_id+100}",
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 404

    @pytest.mark.parametrize(
        "device, expected_response, expected_technical_details, auth_header_getter, expected_service_details",
        (
            # test inverter getting by system user
            (
                samples.TEST_INVERTER_DEVICE_BODY,
                samples.TEST_INVERTER_DEVICE_BODY_FULL_GENERAL_INFO_RESPONSE,
                InverterTechnicalDetailsViewSchema().model_dump(),
                lambda system_user_auth_header, company_member_user_auth_header: system_user_auth_header,
                samples.INVERTER_DEVICE_SERVICE_DETAIL_RESPONSE,
            ),
            # test rack mount getting by company member
            (
                samples.TEST_RACK_DEVICE_BODY,
                samples.TEST_RACK_DEVICE_BODY_FULL_GENERAL_INFO_RESPONSE,
                RachMountTechnicalDetailsSchema().model_dump(),
                lambda system_user_auth_header, company_member_user_auth_header: company_member_user_auth_header,
                samples.DEVICE_SERVICE_DETAIL_PLACEHOLDER_RESPONSE,
            ),
            # test meter getting to validate empty fields set to 'Other' by company member
            (
                samples.TEST_METER_DEVICE_BODY,
                samples.TEST_METER_DEVICE_BODY_RESPONSE,
                MeterTechnicalDetailsSchema().model_dump(),
                lambda system_user_auth_header, company_member_user_auth_header: company_member_user_auth_header,
                samples.INVERTER_DEVICE_SERVICE_DETAIL_RESPONSE,
            ),
        ),
        indirect=["device"],
    )
    def test_get_device_by_id_success(
        self,
        client,
        site_id,
        device,
        expected_response,
        expected_technical_details,
        auth_header_getter,
        expected_service_details,
        system_user_auth_header,
        company_member_user_auth_header,
    ):
        response = client.get(
            f"{self._generate_device_endpoint(site_id)}/{device.id}",
            headers=auth_header_getter(system_user_auth_header, company_member_user_auth_header),
        )
        response_json = response.json()

        assert response.status_code == 200
        assert response_json["general_info"] == expected_response
        assert response_json["service_detail"] == expected_service_details
        # validate technical details returned corresponding to the device category
        assert response_json["technical_details"] == expected_technical_details
        assert response_json["documents"] == samples.TEST_DEVICE_DOCUMENTS_LIST
        assert response_json["telemetry_mapping"] is None

    @pytest.mark.parametrize(
        "sites,method_name",
        ((2, "get"),),
        indirect=["sites"],
    )
    def test_get_device_by_id_wrong_site(
        self,
        client,
        device_id,
        company_member_user_auth_header,
        company_member_user,
        sites,
        method_name,
        mocker,
        db_session,
    ):
        """Validate site<>device relationship is controlled"""
        logger_mock = mocker.patch("app.helpers.authorization.project_access.logger")
        site2 = sites[1]
        set_user_site_access(db_session, site2, company_member_user)
        response = client.request(
            method=method_name,
            url=f"{self._generate_device_endpoint(site2.id)}/{device_id}",
            headers=company_member_user_auth_header,
        )
        assert response.status_code == 403
        logger_mock.warning.assert_called_with(
            f"Scope mismatch! User {company_member_user.id} tried to access device {device_id} which attached to "
            "different site_id"
        )

    def test_update_device_general_info_not_found(self, client, site_id, device_id, company_member_user_auth_header):
        target_id = device_id + 2
        response = client.put(
            self._generate_device_general_info_endpoint(site_id, target_id),
            json=samples.TEST_INVERTER_DEVICE_BODY_UPDATE,
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"

    def test_update_device_general_info_403(self, client, site_id, device_id, non_system_user_auth_header):

        response = client.put(
            self._generate_device_general_info_endpoint(site_id, device_id),
            json=samples.TEST_INVERTER_DEVICE_BODY_UPDATE,
            headers=non_system_user_auth_header,
        )

        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"

    @pytest.mark.parametrize(
        "auth_header_getter",
        (
            # system user
            lambda system_user_auth_header, company_member_user_auth_header: system_user_auth_header,
            # company member user
            lambda system_user_auth_header, company_member_user_auth_header: company_member_user_auth_header,
        ),
    )
    def test_update_device_general_info_success(
        self, client, site_id, device_id, system_user_auth_header, company_member_user_auth_header, auth_header_getter
    ):
        updated_device = deepcopy(samples.TEST_INVERTER_DEVICE_BODY)
        updated_device["name"] = "New device name"
        updated_device["status"] = "Decommissioned"
        updated_device["type"] = "String"
        updated_device["manufacturer"] = "SMA"
        response = client.put(
            self._generate_device_general_info_endpoint(site_id, device_id),
            json=updated_device,
            headers=auth_header_getter(system_user_auth_header, company_member_user_auth_header),
        )

        assert response.status_code == 202
        assert response.json()["message"] == "Device has been successfully updated"

    def test_update_device_general_info_with_telemetry_success(
        self, client, site_id, device_id, company_member_user_auth_header, mocker, fs_company_config_with_site
    ):
        updated_device = deepcopy(samples.TEST_INVERTER_DEVICE_BODY)
        mocker.patch("app.helpers.telemetry.firestore_client.service_account")
        fs_client_mock = mocker.patch("app.helpers.telemetry.firestore_client.firestore.Client")
        mocker.patch("app.helpers.telemetry.secrets_manager.service_account")
        get_fs_config_mock = fs_client_mock.return_value.collection.return_value.document.return_value.get
        get_fs_config_mock.return_value = fs_company_config_with_site
        set_fs_config_mock = fs_client_mock.return_value.collection.return_value.document.return_value.set

        updated_device["name"] = "New device name"
        updated_device["status"] = "Decommissioned"
        updated_device["type"] = "String"
        updated_device["manufacturer"] = "SMA"
        updated_device["telemetry_device_id"] = "12sad"
        updated_device["telemetry_device_name"] = "Test telemetry device"

        response = client.put(
            self._generate_device_general_info_endpoint(site_id, device_id),
            json=updated_device,
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 202
        assert response.json()["message"] == "Device has been successfully updated"
        assert get_fs_config_mock.call_count == 1
        assert set_fs_config_mock.call_count == 1

    def test_update_device_telemetry_mapping_already_exist(
        self, client, site_id, device_id, company_member_user_auth_header, db_session, fs_company_config_with_site
    ):
        updated_device = deepcopy(samples.TEST_INVERTER_DEVICE_BODY)
        telemetry_mapping = {"telemetry_device_id": "12sad", "telemetry_device_name": "Test telemetry device"}

        updated_device["name"] = "New device name"
        updated_device["status"] = "Decommissioned"
        updated_device["type"] = "String"
        updated_device["manufacturer"] = "SMA"
        updated_device.update(telemetry_mapping)
        telemetry_mapping["device_id"] = device_id
        TelemetryDeviceMappingCRUD(db_session).create_item(telemetry_mapping)

        response = client.put(
            self._generate_device_general_info_endpoint(site_id, device_id),
            json=updated_device,
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 400
        assert response.json()["message"] == TelemetryMessages.device_mapping_already_exists.value

    @pytest.mark.parametrize(
        "payload_updates, expected_error_message",
        (
            # check general info fields, which are available only on the edit
            (
                {
                    "warranty_effective_date": "not-an-date",
                    "install_date": "19h-19-19",
                    "decommissioned_date": "2222-22-22",
                    "last_updated_date": "2222-12-h",
                },
                samples.DEVICE_GENERAL_INFO_INVALID_ERROR_MSG,
            ),
            # validate date, IOSP1-3446
            (
                {
                    "warranty_effective_date": "1010-10-10",
                    "install_date": "1111-11-11",
                    "decommissioned_date": "0000-00-00",
                    "last_updated_date": "0001-01-01",
                },
                samples.DEVICE_GENERAL_INFO_INVALID_DATES_ERROR_MSG,
            ),
            # ensure category<>manufacturer and category<>type relation is validated as well
            (
                {"type": "Canopy"},
                samples.INVALID_INVERTER_CATEGORY_TYPE_MSG.replace("Validation error: body.type - Value error, ", ""),
            ),
            (
                {"manufacturer": "Crossrail"},
                samples.INVALID_INVERTER_CATEGORY_MANUFACTURER_MSG.replace(
                    "Validation error: body.manufacturer - Value error, ", ""
                ),
            ),
            # check general info fields validations
            (
                {
                    "warranty_term": "not-an-date" * 20,
                    "gateway_id": "19-19-19" * 20,
                    "function_id": "2222-22-22" * 20,
                    "driver": "driver" * 20,
                },
                samples.DEVICE_TOO_LONG_GENERAL_INFO_FIELDS_ERROR_MSG,
            ),
            # check status 'Deleted on DAS' cannot be set
            ({"status": "Deleted on DAS"}, samples.PROHIBITED_DEVICE_STATUS_MSG),
        ),
    )
    def test_update_general_info_detail_invalid_payload(
        self, client, site_id, device_id, company_member_user_auth_header, payload_updates, expected_error_message
    ):
        payload = deepcopy(samples.TEST_INVERTER_DEVICE_BODY_RESPONSE)
        payload.update(payload_updates)
        update_response = client.put(
            self._generate_device_general_info_endpoint(site_id, device_id),
            json=payload,
            headers=company_member_user_auth_header,
        )
        assert update_response.status_code == 422
        assert update_response.json()["message"] == expected_error_message

    @pytest.mark.parametrize(
        "device_status",
        (
            # check device in <Decommissioned> status cannot be updated
            "decommissioned",
            # check device in <Deleted on DAS> status cannot be updated
            "deleted_on_das",
        ),
    )
    def test_update_general_info_detail_device_archived_error(
        self, client, site_id, device, company_member_user_auth_header, device_status, db_session
    ):
        # update device status
        device.status = device_status
        db_session.commit()
        payload = deepcopy(samples.TEST_INVERTER_DEVICE_BODY_UPDATE)
        payload["name"] = "New device name"

        update_response = client.put(
            self._generate_device_general_info_endpoint(site_id, device.id),
            json=payload,
            headers=company_member_user_auth_header,
        )
        assert update_response.status_code == 400
        assert update_response.json()["message"] == samples.ARCHIVED_DEVICE_UPDATE_ERR

    @pytest.mark.parametrize(
        "field_name,invalid_field_value,expected_msg",
        (
            ("asset_id", "", samples.DEVICE_ASSET_ID_TOO_SHORT_ERROR_MSG),
            ("asset_id", "1" * 101, samples.DEVICE_ASSET_ID_TOO_LONG_ERROR_MSG),
            ("model", "", samples.DEVICE_MODEL_TOO_SHORT_ERROR_MSG),
            ("model", "a" * 101, samples.DEVICE_MODEL_TOO_LONG_ERROR_MSG),
            ("serial_number", "", samples.DEVICE_SERIAL_NUMBER_TOO_SHORT_ERROR_MSG),
            ("serial_number", "a" * 101, samples.DEVICE_SERIAL_NUMBER_TOO_LONG_ERROR_MSG),
        ),
    )
    def test_update_general_info_detail_with_invalid_field_limits(
        self, client, site_id, company_member_user_auth_header, field_name, invalid_field_value, expected_msg, device
    ):
        """Test that device fields have correct limitations."""
        invalid_body = deepcopy(samples.VALID_DEVICE_BODY_WITH_STATUS)
        invalid_body[field_name] = invalid_field_value
        update_response = client.put(
            self._generate_device_general_info_endpoint(site_id, device.id),
            json=invalid_body,
            headers=company_member_user_auth_header,
        )
        assert update_response.status_code == 422
        assert update_response.json()["message"] == expected_msg

    def test_update_device_service_detail_not_found(self, client, site_id, device_id, company_member_user_auth_header):
        target_id = device_id + 2
        response = client.put(
            self._generate_device_service_details_endpoint(site_id, target_id),
            json=samples.TEST_INVERTER_DEVICE_BODY_UPDATE,
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"

    def test_update_device_service_detail_403(self, client, site_id, device_id, non_system_user_auth_header):

        response = client.put(
            self._generate_device_service_details_endpoint(site_id, device_id),
            json=samples.TEST_INVERTER_DEVICE_BODY_UPDATE,
            headers=non_system_user_auth_header,
        )

        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"

    @pytest.mark.parametrize(
        "payload, auth_header_getter",
        (
            # check fields are set, system user
            (
                {
                    "lifetime": "90 days",
                    "warranty_period": "Active",
                    "next_scheduled_service_date": "2025-09-16",
                },
                lambda system_user_auth_header, company_member_user_auth_header: system_user_auth_header,
            ),
            # check fields can be unset, company member
            ({}, lambda system_user_auth_header, company_member_user_auth_header: company_member_user_auth_header),
        ),
    )
    def test_update_device_service_detail_success(
        self,
        client,
        site_id,
        device_id,
        system_user_auth_header,
        company_member_user_auth_header,
        payload,
        auth_header_getter,
    ):
        updated_service_details = deepcopy(samples.INVERTER_DEVICE_SERVICE_DETAIL_RESPONSE)
        updated_service_details.update(payload)
        auth_header = auth_header_getter(system_user_auth_header, company_member_user_auth_header)
        update_response = client.put(
            self._generate_device_service_details_endpoint(site_id, device_id),
            json=payload,
            headers=auth_header,
        )
        get_response = client.get(
            f"{self._generate_device_endpoint(site_id)}/{device_id}",
            headers=auth_header,
        )

        assert update_response.status_code == 202
        assert update_response.json()["message"] == "Device has been successfully updated"
        assert get_response.json()["service_detail"] == updated_service_details

    @pytest.mark.parametrize(
        "payload,expected_error",
        (
            # generic fields validation
            (
                {
                    "warranty_period": "not-an-enum",
                    "next_scheduled_service_date": "not-a-date",
                    "lifetime": "30 days" * 20,
                },
                samples.DEVICE_SERVICE_DETAIL_INVALID_ERROR_MSG,
            ),
            # validate date, IOSP1-3446
            ({"next_scheduled_service_date": "0000-01-01"}, samples.DEVICE_SERVICE_DETAIL_INVALID_DATE_ERROR_MSG),
        ),
    )
    def test_update_device_service_detail_invalid_payload(
        self, client, site_id, device_id, company_member_user_auth_header, payload, expected_error
    ):
        update_response = client.put(
            self._generate_device_service_details_endpoint(site_id, device_id),
            json=payload,
            headers=company_member_user_auth_header,
        )

        assert update_response.status_code == 422
        assert update_response.json()["message"] == expected_error

    def test_update_device_technical_details_not_found(
        self, client, site_id, device_id, company_member_user_auth_header
    ):
        target_id = device_id + 2
        response = client.put(
            self._generate_device_technical_details_endpoint(site_id, target_id),
            json=samples.TEST_INVERTER_DEVICE_BODY_UPDATE,
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 404
        assert response.json()["message"] == "Not Found"

    def test_update_device_technical_details_403(self, client, site_id, device_id, non_system_user_auth_header):

        response = client.put(
            self._generate_device_technical_details_endpoint(site_id, device_id),
            json=samples.TEST_INVERTER_DEVICE_BODY_UPDATE,
            headers=non_system_user_auth_header,
        )

        assert response.status_code == 403
        assert response.json()["message"] == "Forbidden"

    @pytest.mark.parametrize(
        "payload, auth_header_getter",
        (
            # check fields are set, system user
            (
                {
                    "power": {"dc_power": 12, "ac_power": 13.45, "cec_efficiency": 0.8, "pv_modules_number": 5},
                    "communication": {"ip_address": "192.168.0.1", "port": 80, "serial_mode": "RS-485, 2 wire"},
                    "array": {"integrated_combiners": "No"},
                },
                lambda system_user_auth_header, company_member_user_auth_header: system_user_auth_header,
            ),
            # check optional fields can be unset, company member
            (
                {"power": {"cec_efficiency": 0.8, "pv_modules_number": 5}},
                lambda system_user_auth_header, company_member_user_auth_header: company_member_user_auth_header,
            ),
        ),
    )
    def test_update_device_technical_details_success(
        self,
        client,
        site_id,
        device_id,
        system_user_auth_header,
        company_member_user_auth_header,
        payload,
        auth_header_getter,
        ignore_bq_sync,
    ):
        """Test device is inverter, be aware it will use inverter schema for the testing"""
        updated_technical_details = deepcopy(InverterTechnicalDetailsViewSchema().model_dump())
        updated_technical_details = deep_update(updated_technical_details, payload)
        auth_header = auth_header_getter(system_user_auth_header, company_member_user_auth_header)
        update_response = client.put(
            self._generate_device_technical_details_endpoint(site_id, device_id),
            json={"category": "Inverter", "technical_details": payload},
            headers=auth_header,
        )
        get_response = client.get(
            f"{self._generate_device_endpoint(site_id)}/{device_id}",
            headers=auth_header,
        )

        assert update_response.status_code == 202
        assert update_response.json()["message"] == "Device has been successfully updated"
        assert get_response.json()["technical_details"] == updated_technical_details

    @pytest.mark.parametrize(
        "payload,expected_error",
        (
            (
                {
                    "category": DeviceCategories.inverter.value,
                    "technical_details": samples.INVERTER_TECHNICAL_DETAILS_INVALID_PAYLOAD,
                },
                samples.INVERTER_TECHNICAL_DETAILS_INVALID_ERR,
            ),
            (
                {
                    "category": DeviceCategories.inverter.value,
                    "technical_details": samples.INVERTER_TECHNICAL_DETAILS_MISSING_REQUIRED_FIELDS_PAYLOAD,
                },
                samples.INVERTER_TECHNICAL_DETAILS_MISSING_REQUIRED_FIELDS_ERR,
            ),
            (
                {
                    "category": DeviceCategories.module.value,
                    "technical_details": samples.MODULE_TECHNICAL_DETAILS_MISSING_REQUIRED_FIELDS_PAYLOAD,
                },
                samples.MODULE_TECHNICAL_DETAILS_MISSING_REQUIRED_FIELDS_ERR,
            ),
            (
                {
                    "category": DeviceCategories.module.value,
                    "technical_details": samples.MODULE_TECHNICAL_DETAILS_INVALID_PAYLOAD,
                },
                samples.MODULE_TECHNICAL_DETAILS_INVALID_ERR,
            ),
            (
                {
                    "category": DeviceCategories.module.value,
                    "technical_details": samples.MODULE_TECHNICAL_DETAILS_INVALID_POWER_VALUES_PAYLOAD,
                },
                samples.MODULE_TECHNICAL_DETAILS_INVALID_POWER_VALUES_ERR,
            ),
            (
                {
                    "category": DeviceCategories.meter.value,
                    "technical_details": samples.METER_TECHNICAL_DETAILS_INVALID_PAYLOAD,
                },
                samples.METER_TECHNICAL_DETAILS_INVALID_ERR,
            ),
            (
                {
                    "category": DeviceCategories.rack_mount.value,
                    "technical_details": samples.RACK_MOUNT_TECHNICAL_DETAILS_INVALID_PAYLOAD,
                },
                samples.RACK_MOUNT_TECHNICAL_DETAILS_INVALID_ERR,
            ),
            (
                {
                    "category": DeviceCategories.battery.value,
                    "technical_details": samples.BATTERY_TECHNICAL_DETAILS_INVALID_PAYLOAD,
                },
                samples.BATTERY_TECHNICAL_DETAILS_INVALID_ERR,
            ),
            # validate date, IOSP1-3446
            (
                {
                    "category": DeviceCategories.battery.value,
                    "technical_details": samples.BATTERY_TECHNICAL_DETAILS_INVALID_DATE_PAYLOAD,
                },
                samples.BATTERY_TECHNICAL_DETAILS_INVALID_DATE_ERR,
            ),
            (
                {
                    "category": DeviceCategories.camera.value,
                    "technical_details": samples.CAMERA_TECHNICAL_DETAILS_INVALID_PAYLOAD,
                },
                samples.CAMERA_TECHNICAL_DETAILS_INVALID_ERR,
            ),
            (
                {
                    "category": DeviceCategories.combiner_box.value,
                    "technical_details": samples.COMBINER_BOX_TECHNICAL_DETAILS_INVALID_PAYLOAD,
                },
                samples.COMBINER_BOX_TECHNICAL_DETAILS_INVALID_ERR,
            ),
            (
                {
                    "category": DeviceCategories.modem.value,
                    "technical_details": samples.MODEM_TECHNICAL_DETAILS_INVALID_PAYLOAD,
                },
                samples.MODEM_TECHNICAL_DETAILS_INVALID_ERR,
            ),
            (
                {
                    "category": DeviceCategories.mbod_gateway.value,
                    "technical_details": samples.MBOD_GATEWAY_TECHNICAL_DETAILS_INVALID_PAYLOAD,
                },
                samples.MBOD_GATEWAY_TECHNICAL_DETAILS_INVALID_ERR,
            ),
            (
                {
                    "category": DeviceCategories.weather_station.value,
                    "technical_details": samples.WEATHER_STATION_TECHNICAL_DETAILS_INVALID_PAYLOAD,
                },
                samples.WEATHER_STATION_TECHNICAL_DETAILS_INVALID_ERR,
            ),
            (
                {
                    "category": DeviceCategories.network_connection.value,
                    "technical_details": samples.NETWORK_CONNECTION_TECHNICAL_DETAILS_INVALID_PAYLOAD,
                },
                samples.NETWORK_CONNECTION_TECHNICAL_DETAILS_INVALID_ERR,
            ),
            (
                {
                    "category": DeviceCategories.network_gateway.value,
                    "technical_details": samples.NETWORK_GATEWAY_TECHNICAL_DETAILS_INVALID_PAYLOAD,
                },
                samples.NETWORK_GATEWAY_TECHNICAL_DETAILS_INVALID_ERR,
            ),
            (
                {
                    "category": DeviceCategories.transformer.value,
                    "technical_details": samples.TRANSFORMER_TECHNICAL_DETAILS_INVALID_PAYLOAD,
                },
                samples.TRANSFORMER_TECHNICAL_DETAILS_INVALID_ERR,
            ),
        ),
    )
    def test_update_device_technical_details_invalid_payload(
        self, client, site_id, device_id, company_member_user_auth_header, payload, expected_error
    ):
        """Validate schema for each device category"""
        response = client.put(
            self._generate_device_technical_details_endpoint(site_id, device_id),
            json=payload,
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 422
        assert response.json()["message"] == expected_error

    def test_update_device_technical_details_inconsistent_payload(
        self, client, site_id, device_id, company_member_user_auth_header, mocker
    ):
        """Validate schema from request and actual device category matches"""
        logger_mock = mocker.patch("app.routers.assets_management.devices.logger")
        payload = {
            "category": "Camera",
            "technical_details": {"communication": {"ip_address": "192.168.0.1"}},
        }
        response = client.put(
            self._generate_device_technical_details_endpoint(site_id, device_id),
            json=payload,
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 400
        assert response.json()["message"] == "Invalid technical details schema"
        logger_mock.warning.assert_called_with(
            "User tried to apply technical details of <Camera> to the <Inverter> device"
        )

    @pytest.mark.parametrize(
        "device_category,payload",
        (
            # rack mount, IOSP1-1391
            (
                DeviceCategories.rack_mount,
                {
                    "category": "Rack Mount",
                    "technical_details": {
                        "general": {"azimuth": "123.00", "racking_capacity": "123.00", "tracking": "Yes"}
                    },
                },
            ),
            # battery, IOSP1-1417
            (
                DeviceCategories.battery,
                {
                    "category": "Battery",
                    "technical_details": {
                        "report": "Yes",
                        "report_due_date": "2024-07-03",
                        "size_kw": 123,
                        "size_mwh": 123333,
                    },
                },
            ),
        ),
    )
    def test_update_device_technical_details_payload_serialization_success(
        self,
        client,
        site_id,
        device_id,
        company_member_user_auth_header,
        device_category,
        payload,
        db_session,
    ):
        """Validate technical details are properly serialized and can be stored"""
        # update device type into DB to pass the validation
        # (devices are function-scoped, so it wouldn't affect other tests)
        devices_crud = DeviceCRUD(db_session)
        devices_crud.update_by_id(device_id, {"category": device_category})

        response = client.put(
            self._generate_device_technical_details_endpoint(site_id, device_id),
            json=payload,
            headers=company_member_user_auth_header,
        )

        assert response.status_code == 202

    def test_update_device_telemetry_info_success(
        self, client, site_id, device_id, company_member_user_auth_header, mocker, telemetry_device_mapping
    ):
        """Test device is updated with information received from telemetry"""
        mocker.patch("app.helpers.telemetry.firestore_client.firestore.Client")
        mocker.patch("app.helpers.telemetry.secrets_manager.service_account")
        mocker.patch("app.helpers.cloud_function_client.service_account")
        mocker.patch("app.helpers.cloud_function_client.google.oauth2.id_token")
        mocker.patch("app.helpers.device_helper.TelemetryDeviceBigQuery")
        mock_telemetry_requests = mocker.patch("app.helpers.cloud_function_client.requests")
        mock_telemetry_requests.post.return_value = create_response(200, samples.TELEMETRY_STATIC_DEVICE_DATA_RESPONSE)
        update_response = client.put(
            self._generate_device_telemetry_details_endpoint(site_id, device_id),
            headers=company_member_user_auth_header,
        )
        get_response = client.get(
            f"{self._generate_device_endpoint(site_id)}/{device_id}",
            headers=company_member_user_auth_header,
        )

        assert update_response.status_code == 202
        assert update_response.json()["message"] == DeviceMessages.device_telemetry_info_update_success.value
        assert get_response.json()["general_info"]["name"] == "telemetry_device"
        assert get_response.json()["general_info"]["asset_id"] == "1234"

    def test_update_device_telemetry_info_no_device_data(
        self, client, site_id, device_id, company_member_user_auth_header, mocker, telemetry_device_mapping
    ):
        """Test device is updated with empty information received from telemetry"""
        mocker.patch("app.helpers.telemetry.firestore_client.firestore.Client")
        mocker.patch("app.helpers.telemetry.secrets_manager.service_account")
        mocker.patch("app.helpers.cloud_function_client.service_account")
        mocker.patch("app.helpers.cloud_function_client.google.oauth2.id_token")
        mock_telemetry_requests = mocker.patch("app.helpers.cloud_function_client.requests")
        mock_telemetry_requests.post.return_value = create_response(200, {})
        update_response = client.put(
            self._generate_device_telemetry_details_endpoint(site_id, device_id),
            headers=company_member_user_auth_header,
        )
        assert update_response.status_code == 202
        assert update_response.json()["message"] == DeviceMessages.no_telemetry_data_received.value

    def test_update_device_telemetry_info_device_not_connected(
        self,
        client,
        site_id,
        device_id,
        company_member_user_auth_header,
    ):
        """Test device telemetry details update fails with 400 if device mapping not exists"""
        update_response = client.put(
            self._generate_device_telemetry_details_endpoint(site_id, device_id),
            headers=company_member_user_auth_header,
        )

        assert update_response.status_code == 400
        assert update_response.json()["message"] == DeviceMessages.device_not_connected_to_das.value

    def test_update_device_telemetry_device_deleted_on_das(
        self,
        client,
        site_id,
        device,
        company_member_user_auth_header,
        db_session,
    ):
        """Test device telemetry details update fails with 400 if device mapping not exists"""
        device.status = DeviceStatuses.deleted_on_das
        db_session.flush()
        update_response = client.put(
            self._generate_device_telemetry_details_endpoint(site_id, device.id),
            headers=company_member_user_auth_header,
        )

        assert update_response.status_code == 400
        assert update_response.json()["message"] == DeviceMessages.device_not_connected_to_das.value

    @pytest.mark.parametrize(
        "field_name, invalid_value, expected_error",
        (
            # invalid device category
            ("category", "invalid_category", samples.TELEMETRY_INVALID_CATEGORY_ERR),
            # invalid time format
            ("last_update_ts", "wrong time", samples.TELEMETRY_INVALID_LAST_UPDATED_ERR),
        ),
    )
    def test_update_device_telemetry_invalid_bq_data(
        self,
        client,
        site_id,
        device_id,
        company_member_user_auth_header,
        mocker,
        telemetry_device_mapping,
        field_name,
        invalid_value,
        expected_error,
    ):
        """Test device is updated with ignoring invalid fields"""
        mocker.patch("app.helpers.telemetry.firestore_client.firestore.Client")
        mocker.patch("app.helpers.telemetry.secrets_manager.service_account")
        mocker.patch("app.helpers.cloud_function_client.service_account")
        mocker.patch("app.helpers.cloud_function_client.google.oauth2.id_token")
        mock_telemetry_requests = mocker.patch("app.helpers.cloud_function_client.requests")
        logger_mock = mocker.patch("app.schema.om_device.logger")
        telemetry_response = deepcopy(samples.TELEMETRY_STATIC_DEVICE_DATA_RESPONSE)
        telemetry_response[field_name] = invalid_value
        mock_telemetry_requests.post.return_value = create_response(200, telemetry_response)

        update_response = client.put(
            self._generate_device_telemetry_details_endpoint(site_id, device_id),
            headers=company_member_user_auth_header,
        )

        assert update_response.status_code == 202
        assert update_response.json()["message"] == DeviceMessages.device_telemetry_info_update_success.value
        logger_mock.warning.assert_called_with(expected_error)

    def test_update_device_telemetry_info_403(
        self,
        client,
        site_id,
        device_id,
        non_system_user_auth_header,
    ):
        """Test device telemetry details update fails with 403"""
        update_response = client.put(
            self._generate_device_telemetry_details_endpoint(site_id, device_id),
            headers=non_system_user_auth_header,
        )
        assert update_response.status_code == 403

    def test_update_device_telemetry_info_404(
        self,
        client,
        site_id,
        device_id,
        system_user_auth_header,
    ):
        """Test device telemetry details update fails with 404"""
        update_response = client.put(
            self._generate_device_telemetry_details_endpoint(site_id, 9999),
            headers=system_user_auth_header,
        )
        assert update_response.status_code == 404

    @pytest.mark.parametrize(
        "bq_response,cache_response,expected_availability_metrics,set_permission_to_operate",
        (
            # No values from BQ
            ([], None, {"mttr": None, "mtbr": None}, False),
            # BQ return data
            ([{"mtbf": 150, "mttr": 17}], None, {"mttr": 1, "mtbr": 7}, False),
            # redis data
            (None, pickle.dumps([{"mtbf": 373, "mttr": 46}]), {"mttr": 2, "mtbr": 16}, False),
            # start date retrieved as permission to operate
            ([], None, {"mttr": None, "mtbr": None}, True),
        ),
    )
    def test_get_device_by_id_with_telemetry_success(
        self,
        db_session,
        client,
        device,
        telemetry_device_mapping,
        company_member_user_auth_header,
        mocker,
        bq_response,
        cache_response,
        expected_availability_metrics,
        set_permission_to_operate,
    ):
        cache_mock = mocker.patch("app.helpers.telemetry.bigquery.base.get_cache")
        cache_mock.return_value.get.return_value = cache_response
        telemetry_bq_engine = mocker.patch("app.helpers.telemetry.bigquery.base.BigQueryReadEngine")
        telemetry_bq_engine.return_value.execute_query.return_value = bq_response

        if set_permission_to_operate:
            SiteAdditionalFieldListCRUD(db_session).create_item(
                {
                    "site_id": device.site_id,
                    "permission_to_operate": date.today(),
                }
            )

        expected_service_details = deepcopy(samples.DEVICE_SERVICE_DETAIL_PLACEHOLDER_RESPONSE)
        expected_service_details.update(expected_availability_metrics)
        response = client.get(
            f"{self._generate_device_endpoint(device.site_id)}/{device.id}", headers=company_member_user_auth_header
        )
        response_json = response.json()

        assert response.status_code == 200
        assert response_json["service_detail"] == expected_service_details
