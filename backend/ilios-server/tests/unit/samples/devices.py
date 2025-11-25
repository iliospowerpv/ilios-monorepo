import copy
import datetime

from app.helpers.device_helper import category_manufacturers_mapper
from app.models.device import DeviceCategories
from tests.unit.samples import enum_to_message, enum_to_str

VALID_DEVICE_BODY = {
    "name": "Basic Inverter",
    "category": "Inverter",
}

VALID_DEVICE_BODY_WITH_STATUS = copy.deepcopy(VALID_DEVICE_BODY)
VALID_DEVICE_BODY_WITH_STATUS["status"] = "Available Inventory"

INVALID_DEVICE_BODY_INVERTER = copy.deepcopy(VALID_DEVICE_BODY)

# camera has type but doesn't allow manufacturer
VALID_DEVICE_BODY_CAMERA = copy.deepcopy(VALID_DEVICE_BODY)
VALID_DEVICE_BODY_CAMERA.update({"category": "Camera"})

# meter both type and manufacturer are not allowed
VALID_DEVICE_BODY_METER = copy.deepcopy(VALID_DEVICE_BODY)
VALID_DEVICE_BODY_METER.update({"category": "Meter"})

TEST_INVERTER_DEVICE_NAME = "Base Inverter Device"
TEST_RACK_DEVICE_NAME = "Mount Rack Device"
TEST_INVERTER_DEVICE_ASSET_ID = "1344ASASD12"
TEST_RACK_DEVICE_ASSET_ID = "12345AID"
TEST_INVERTER_DEVICE_TYPE = "Micro Inverter"
TEST_INVERTER_DEVICE_CATEGORY = "Inverter"

DEVICE_NON_REQUIRED_FIELDS = {
    "warranty_effective_date": None,
    "warranty_term": None,
    "gateway_id": None,
    "function_id": None,
    "driver": None,
    "install_date": None,
    "decommissioned_date": None,
    "last_updated_date": None,
}
TEST_INVERTER_DEVICE_BODY = {
    "status": "available_inventory",
    "asset_id": TEST_INVERTER_DEVICE_ASSET_ID,
    "name": TEST_INVERTER_DEVICE_NAME,
    "category": "inverter",
    "type": "micro_inverter",
    "manufacturer": "chint_power_systems",
    "model": "11ADSA2341",
    "serial_number": "12435225ASE",
}

TEST_RACK_DEVICE_BODY = {
    "status": "available_inventory",
    "asset_id": TEST_RACK_DEVICE_ASSET_ID,
    "name": TEST_RACK_DEVICE_NAME,
    "category": "rack_mount",
    "type": "canopy",
    "manufacturer": "sungrow",
    "model": "11B32",
    "serial_number": "12345321SN",
}

TEST_METER_DEVICE_BODY = copy.deepcopy(VALID_DEVICE_BODY_METER)
TEST_METER_DEVICE_BODY.update(
    {
        "category": "meter",
        "status": "available_inventory",
    }
)

TEST_MODULE_DEVICE_BODY = copy.deepcopy(TEST_METER_DEVICE_BODY)
TEST_MODULE_DEVICE_BODY.update(
    {
        "category": "module",
    }
)

TEST_INVERTER_DEVICE_BODY_UPDATE = {
    "status": "Decommissioned",
    "asset_id": "1344ADSASD12",
    "name": TEST_INVERTER_DEVICE_NAME,
    "category": "inverter",
    "type": "String",
    "manufacturer": "SMA",
    "model": "11ADSA2341",
    "serial_number": "12435225ASE",
}

TEST_DEVICE_DOCUMENTS_LIST = [{"category": "Warranty", "items": []}, {"category": "Specifications", "items": []}]

TEST_INVERTER_DEVICE_BODY_RESPONSE = copy.deepcopy(TEST_INVERTER_DEVICE_BODY)
TEST_INVERTER_DEVICE_BODY_RESPONSE.update(
    {
        "status": "Available Inventory",
        "category": "Inverter",
        "type": "Micro Inverter",
        "manufacturer": "Chint Power Systems",
        "das_connection_status": "Not Connected",
    }
)
TEST_INVERTER_DEVICE_BODY_FULL_GENERAL_INFO_RESPONSE = copy.deepcopy(TEST_INVERTER_DEVICE_BODY_RESPONSE)
TEST_INVERTER_DEVICE_BODY_FULL_GENERAL_INFO_RESPONSE.update(DEVICE_NON_REQUIRED_FIELDS)

TEST_RACK_DEVICE_BODY_RESPONSE = copy.deepcopy(TEST_RACK_DEVICE_BODY)
TEST_RACK_DEVICE_BODY_RESPONSE.update(
    {
        "status": "Available Inventory",
        "category": "Rack Mount",
        "type": "Canopy",
        "manufacturer": "Sungrow",
        "das_connection_status": "Not Connected",
    }
)

TEST_RACK_DEVICE_BODY_FULL_GENERAL_INFO_RESPONSE = copy.deepcopy(TEST_RACK_DEVICE_BODY_RESPONSE)
TEST_RACK_DEVICE_BODY_FULL_GENERAL_INFO_RESPONSE.update(DEVICE_NON_REQUIRED_FIELDS)

TEST_METER_DEVICE_BODY_RESPONSE = copy.deepcopy(VALID_DEVICE_BODY_METER)
TEST_METER_DEVICE_BODY_RESPONSE.update(
    {
        "das_connection_status": "Not Connected",
        "status": "Available Inventory",
        "type": None,
        "asset_id": None,
        "manufacturer": None,
        "model": None,
        "serial_number": None,
    }
)
TEST_METER_DEVICE_BODY_RESPONSE.update(DEVICE_NON_REQUIRED_FIELDS)

DEVICE_SERVICE_DETAIL_EDITABLE_FIELDS = {
    "lifetime": None,
    "warranty_period": None,
    "next_scheduled_service_date": None,
}

DEVICE_SERVICE_DETAIL_PLACEHOLDER_RESPONSE = DEVICE_SERVICE_DETAIL_EDITABLE_FIELDS | {
    "test_interval": "TBD",
    "failure_rate": "TBD",
    "mtbr": "N/A",
    "mttr": "N/A",
    "availability": "TBD",
    "open_repair_tickets_count": "TBD",
}

INVERTER_DEVICE_SERVICE_DETAIL_RESPONSE = copy.deepcopy(DEVICE_SERVICE_DETAIL_PLACEHOLDER_RESPONSE)
INVERTER_DEVICE_SERVICE_DETAIL_RESPONSE.update({"mttr": None, "mtbr": None})

PROHIBITED_DEVICE_STATUS_MSG = (
    "Validation error: body.status - Value error, Cannot set device status to <Deleted on DAS>, it's for internal usage"
)
ARCHIVED_DEVICE_UPDATE_ERR = "Update of devices in statuses 'Decommissioned' or 'Deleted on DAS' is prohibited"

INVALID_DEVICE_CATEGORY_MSG = f"Validation error: body.category - Input should be {enum_to_message(DeviceCategories)}"

INVALID_INVERTER_CATEGORY_TYPE_MSG = (
    "Validation error: body.type - Value error, There is no 'Canopy' type in 'Inverter' category. Input should be: "
    "'String', 'Micro Inverter', 'Power Optimizers'"
)

INVALID_INVERTER_CATEGORY_MANUFACTURER_MSG = (
    "Validation error: body.manufacturer - Value error, There is no 'Crossrail' manufacturer in 'Inverter' category. "
    f"Input should be: {enum_to_str(category_manufacturers_mapper[DeviceCategories.inverter])}"
)

DEVICE_ASSET_ID_TOO_SHORT_ERROR_MSG = "Validation error: body.asset_id - String should have at least 2 characters"

DEVICE_ASSET_ID_TOO_LONG_ERROR_MSG = "Validation error: body.asset_id - String should have at most 100 characters"

DEVICE_NAME_TOO_SHORT_ERROR_MSG = "Validation error: body.name - String should have at least 2 characters"

DEVICE_NAME_TOO_LONG_ERROR_MSG = "Validation error: body.name - String should have at most 100 characters"

DEVICE_MODEL_TOO_SHORT_ERROR_MSG = "Validation error: body.model - String should have at least 2 characters"

DEVICE_MODEL_TOO_LONG_ERROR_MSG = "Validation error: body.model - String should have at most 100 characters"

DEVICE_SERIAL_NUMBER_TOO_SHORT_ERROR_MSG = (
    "Validation error: body.serial_number - String should have at least 2 characters"
)

DEVICE_SERIAL_NUMBER_TOO_LONG_ERROR_MSG = (
    "Validation error: body.serial_number - String should have at most 100 characters"
)

DEVICE_GENERAL_INFO_INVALID_ERROR_MSG = (
    "Validation error: body.warranty_effective_date - Input should be a valid date or datetime, "
    "invalid character in year; body.install_date - Input should be a valid date or datetime, input is too short; "
    "body.decommissioned_date - Input should be a valid date or datetime, month value is outside expected range "
    "of 1-12; body.last_updated_date - Input should be a valid date or datetime, input is too short"
)
DEVICE_GENERAL_INFO_INVALID_DATES_ERROR_MSG = (
    "Validation error: body.warranty_effective_date - Value error, Year must be 1900 or greater; body.install_date - "
    "Value error, Year must be 1900 or greater; body.decommissioned_date - Value error, Year must be 1900 or greater; "
    "body.last_updated_date - Value error, Year must be 1900 or greater"
)
DEVICE_SERVICE_DETAIL_INVALID_ERROR_MSG = (
    "Validation error: body.lifetime - String should have at most 100 characters; "
    "body.warranty_period - Input should be 'Active' or 'End of Life'; "
    "body.next_scheduled_service_date - Input should be a valid date or datetime, invalid character in year"
)
DEVICE_SERVICE_DETAIL_INVALID_DATE_ERROR_MSG = (
    "Validation error: body.next_scheduled_service_date - Value error, Year must be 1900 or greater"
)

DEVICE_TOO_LONG_GENERAL_INFO_FIELDS_ERROR_MSG = (
    "Validation error: body.warranty_term - String should have at most 100 characters; body.gateway_id - "
    "String should have at most 100 characters; body.function_id - String should have at most 100 characters; "
    "body.driver - String should have at most 100 characters"
)

INVERTER_TECHNICAL_DETAILS_INVALID_PAYLOAD = {
    "power": {
        "dc_power": "not-float",
        "dc_max_input": "not-float",
        "ac_power": "not-float",
        "ac_max_output": "not-float",
        "standby_power": "not-float",
        "rated_output": "not-float",
        "cec_efficiency": "not-float",
        "pv_modules_number": "not-float",
    },
    "communication": {"ip_address": "not-ip-address", "port": 1.1, "serial_mode": "A" * 101, "baud": "not-float"},
    "array": {
        "number_of_strings": "not-float",
        "modules_per_string": "not-float",
        "integrated_combiners": "invalid-dropdown-option",
        "yearly_degradation": "not-float",
        "derate": "not-float",
    },
    "module": {
        "watts_per_module": "not-float",
        "mpp_voltage": "not-float",
        "mpp_current": "not-float",
        "mpp_watts": "not-float",
        "temperature_coefficient": "not-float",
    },
}
INVERTER_TECHNICAL_DETAILS_INVALID_ERR = (
    "Validation error: body.technical_details.power.dc_power - Input should be a valid number, unable to parse "
    "string as a number; body.technical_details.power.dc_max_input - Input should be a valid number, unable to parse "
    "string as a number; body.technical_details.power.ac_power - Input should be a valid number, unable to parse "
    "string as a number; body.technical_details.power.ac_max_output - Input should be a valid number, unable to parse "
    "string as a number; body.technical_details.power.standby_power - Input should be a valid number, unable to parse "
    "string as a number; body.technical_details.power.rated_output - Input should be a valid number, unable to parse "
    "string as a number; body.technical_details.power.cec_efficiency - Input should be a valid number, unable to parse "
    "string as a number; body.technical_details.power.pv_modules_number - Input should be a valid number, unable to "
    "parse string as a number; body.technical_details.communication.ip_address - value is not a valid IPv4 or IPv6 "
    "address; body.technical_details.communication.port - Input should be a valid integer, got a number with a "
    "fractional part; body.technical_details.communication.serial_mode - String should have at most 100 characters; "
    "body.technical_details.communication.baud - Input should be a valid number, unable to parse string as a number; "
    "body.technical_details.array.number_of_strings - Input should be a valid number, unable to parse string "
    "as a number; body.technical_details.array.modules_per_string - Input should be a valid number, unable to parse "
    "string as a number; body.technical_details.array.integrated_combiners - Input should be 'Yes' or 'No'; "
    "body.technical_details.array.yearly_degradation - Input should be a valid number, unable to parse string "
    "as a number; body.technical_details.array.derate - Input should be a valid number, unable to parse string "
    "as a number; body.technical_details.module.watts_per_module - Input should be a valid number, unable to parse "
    "string as a number; body.technical_details.module.mpp_voltage - Input should be a valid number, unable to parse "
    "string as a number; body.technical_details.module.mpp_current - Input should be a valid number, unable to parse "
    "string as a number; body.technical_details.module.mpp_watts - Input should be a valid number, unable to parse "
    "string as a number; body.technical_details.module.temperature_coefficient - Input should be a valid number, "
    "unable to parse string as a number"
)
INVERTER_TECHNICAL_DETAILS_MISSING_REQUIRED_FIELDS_PAYLOAD = {"power": {}}
INVERTER_TECHNICAL_DETAILS_MISSING_REQUIRED_FIELDS_ERR = (
    "Validation error: body.technical_details.power.cec_efficiency - Field required; "
    "body.technical_details.power.pv_modules_number - Field required"
)

MODULE_TECHNICAL_DETAILS_MISSING_REQUIRED_FIELDS_PAYLOAD = {"power": {}}
MODULE_TECHNICAL_DETAILS_MISSING_REQUIRED_FIELDS_ERR = (
    "Validation error: body.technical_details.power.max_power_tolerance - Field required; "
    "body.technical_details.power.min_power_tolerance - Field required; "
    "body.technical_details.power.power_thermal_coefficient - Field required; "
    "body.technical_details.power.year_1_degradation - Field required; "
    "body.technical_details.power.annual_degradation - Field required"
)
MODULE_TECHNICAL_DETAILS_INVALID_PAYLOAD = {
    "module_specs": {
        "weight": "not-float",
        "module_kw": False,
        "solar_cells_per_module": "not-float",
        "solar_cell_type": "A" * 101,
        "glass_type": "B" * 101,
        "cable_and_connector": "C" * 101,
        "frame": "D" * 101,
    },
    "power": {
        "system_voltage": "not-float",
        "power_output": True,
        "mpp_voltage": False,
        "mpp_current": "not-float",
        "mpp_watts": False,
        "temperature_coefficient": True,
        "watts_per_module": "not-float",
        "max_power_tolerance": False,
        "min_power_tolerance": "not-float",
        "power_thermal_coefficient": None,
        "year_1_degradation": [None, None],
        "annual_degradation": {"not": "float"},
    },
}
MODULE_TECHNICAL_DETAILS_INVALID_ERR = (
    "Validation error: body.technical_details.module_specs.weight - Input should be a valid number, unable to parse "
    "string as a number; body.technical_details.module_specs.solar_cells_per_module - Input should be a valid number, "
    "unable to parse string as a number; body.technical_details.module_specs.solar_cell_type - String should have "
    "at most 100 characters; body.technical_details.module_specs.glass_type - String should have at most "
    "100 characters; body.technical_details.module_specs.cable_and_connector - String should have at most "
    "100 characters; body.technical_details.module_specs.frame - String should have at most 100 characters; "
    "body.technical_details.power.system_voltage - Input should be a valid number, unable to parse string as a number; "
    "body.technical_details.power.mpp_current - Input should be a valid number, unable to parse string as a number; "
    "body.technical_details.power.watts_per_module - Input should be a valid number, unable to parse string as "
    "a number; body.technical_details.power.min_power_tolerance - Input should be a valid number, unable to parse "
    "string as a number; body.technical_details.power.power_thermal_coefficient - Input should be a valid number; "
    "body.technical_details.power.year_1_degradation - Input should be a valid number; "
    "body.technical_details.power.annual_degradation - Input should be a valid number"
)

MODULE_TECHNICAL_DETAILS_INVALID_POWER_VALUES_PAYLOAD = {
    "power": {
        "max_power_tolerance": -2,
        "min_power_tolerance": 5,
        "power_thermal_coefficient": 1,
        "year_1_degradation": 2,
        "annual_degradation": 3,
    }
}
MODULE_TECHNICAL_DETAILS_INVALID_POWER_VALUES_ERR = (
    "Validation error: body.technical_details.power.max_power_tolerance - Input should be greater than or equal to 0; "
    "body.technical_details.power.min_power_tolerance - Input should be less than or equal to 0"
)

METER_TECHNICAL_DETAILS_INVALID_PAYLOAD = {
    "general": {"capacity": "not-float", "inverters": "not-float"},
    "communication": {"ip_address": 12, "unit_id": 12.23},
    "scale_factor": {"power": False, "energy": True, "swap_delivered_received": "A" * 101, "gross_energy": "B" * 101},
    "sample_date": {"kw": "not-float", "kwh_net": True, "kwh_received": False, "kwh_delivered": "not-float"},
    "data_range": {"max_power": "not-float", "max_voltage": False, "max_current_per_phase": True, "ac": "C" * 101},
}
METER_TECHNICAL_DETAILS_INVALID_ERR = (
    "Validation error: body.technical_details.general.capacity - Input should be a valid number, unable to parse "
    "string as a number; body.technical_details.general.inverters - Input should be a valid number, unable to parse "
    "string as a number; body.technical_details.communication.unit_id - Input should be a valid integer, got a number "
    "with a fractional part; body.technical_details.scale_factor.swap_delivered_received - String should have at most "
    "100 characters; body.technical_details.scale_factor.gross_energy - String should have at most 100 characters; "
    "body.technical_details.sample_date.kw - Input should be a valid number, unable to parse string as a number; "
    "body.technical_details.sample_date.kwh_delivered - Input should be a valid number, unable to parse string "
    "as a number; body.technical_details.data_range.max_power - Input should be a valid number, unable to parse string "
    "as a number; body.technical_details.data_range.ac - String should have at most 100 characters"
)

RACK_MOUNT_TECHNICAL_DETAILS_INVALID_PAYLOAD = {
    "general": {"racking_capacity": True, "azimuth": "not-float", "tracking": False}
}
RACK_MOUNT_TECHNICAL_DETAILS_INVALID_ERR = (
    "Validation error: body.technical_details.general.azimuth - Input should be a valid number, unable to parse string "
    "as a number; body.technical_details.general.tracking - Input should be 'Yes' or 'No'"
)

BATTERY_TECHNICAL_DETAILS_INVALID_PAYLOAD = {
    "size_kw": "None",
    "size_mwh": False,
    "report": False,
    "report_due_date": "not-a-date",
}
BATTERY_TECHNICAL_DETAILS_INVALID_ERR = (
    "Validation error: body.technical_details.size_kw - Input should be a valid number, unable to parse string "
    "as a number; body.technical_details.report - Input should be 'Yes' or 'No'; "
    "body.technical_details.report_due_date - Input should be a valid date or datetime, invalid character in year"
)
BATTERY_TECHNICAL_DETAILS_INVALID_DATE_PAYLOAD = {
    "report_due_date": "0001-01-01",
}
BATTERY_TECHNICAL_DETAILS_INVALID_DATE_ERR = (
    "Validation error: body.technical_details.report_due_date - Value error, Year must be 1900 or greater"
)

CAMERA_TECHNICAL_DETAILS_INVALID_PAYLOAD = {"communication": {"ip_address": "1111.2222.3333.4444"}}
CAMERA_TECHNICAL_DETAILS_INVALID_ERR = (
    "Validation error: body.technical_details.communication.ip_address - value is not a valid IPv4 or IPv6 address"
)

COMBINER_BOX_TECHNICAL_DETAILS_INVALID_PAYLOAD = {
    "enclosure_type": "N" * 101,
    "dimensions": "D" * 101,
    "weight": True,
    "max_output": True,
    "input_circuits_max_count": "None",
}
COMBINER_BOX_TECHNICAL_DETAILS_INVALID_ERR = (
    "Validation error: body.technical_details.enclosure_type - String should have at most 100 characters; "
    "body.technical_details.dimensions - String should have at most 100 characters; "
    "body.technical_details.input_circuits_max_count - Input should be a valid number, unable to parse string "
    "as a number"
)

MODEM_TECHNICAL_DETAILS_INVALID_PAYLOAD = {
    "communication": {"ip_address": "not-ip-address", "port": "wrong int", "serial_mode": 11.222, "baud": "not-float"},
}
MODEM_TECHNICAL_DETAILS_INVALID_ERR = (
    "Validation error: body.technical_details.communication.ip_address - value is not a valid IPv4 or IPv6 address; "
    "body.technical_details.communication.port - Input should be a valid integer, unable to parse string as an integer; "
    "body.technical_details.communication.serial_mode - Input should be a valid string; "
    "body.technical_details.communication.baud - Input should be a valid number, unable to parse string as a number"
)

MBOD_GATEWAY_TECHNICAL_DETAILS_INVALID_PAYLOAD = copy.deepcopy(CAMERA_TECHNICAL_DETAILS_INVALID_PAYLOAD)
MBOD_GATEWAY_TECHNICAL_DETAILS_INVALID_ERR = CAMERA_TECHNICAL_DETAILS_INVALID_ERR

WEATHER_STATION_TECHNICAL_DETAILS_INVALID_PAYLOAD = {
    "sensors": {
        "wind": False,
        "humidity": True,
        "barometer": 123,
        "snow_depth": 1.11,
        "normal_incidence_pyrheliometer": "wrong",
        "rain": "wrong",
        "temperature": "wrong",
        "irradiance": "wrong",
    },
    "temperature_sensors": {
        "ambient_temperature": True,
        "panel_temperature1": 123,
        "panel_temperature2": "wrong",
        "min_temperature": "not-float",
        "max_temperature": "not-float",
    },
    "pyranometer_sensors": {
        "reference": True,
        "azimuth_and_tilt": 123,
        "azimuth": "not-float",
        "tilt": "not-float",
        "tracking": "T" * 101,
        "pyranometer": 12.123,
    },
    "monthly_insolation": {
        "january": "not-float",
        "february": "not-float",
        "march": "not-float",
        "april": "not-float",
        "may": "not-float",
        "june": "not-float",
        "july": "not-float",
        "august": "not-float",
        "september": "not-float",
        "october": "not-float",
        "november": "not-float",
        "december": "not-float",
        "insolation_reference": "I" * 101,
        "interpolate_daily_insolation": False,
    },
}
WEATHER_STATION_TECHNICAL_DETAILS_INVALID_PAYLOAD.update(MODEM_TECHNICAL_DETAILS_INVALID_PAYLOAD)
WEATHER_STATION_TECHNICAL_DETAILS_INVALID_ERR = (
    "Validation error: body.technical_details.communication.ip_address - value is not a valid IPv4 or IPv6 address; "
    "body.technical_details.communication.port - Input should be a valid integer, unable to parse string as an integer; "
    "body.technical_details.communication.serial_mode - Input should be a valid string; "
    "body.technical_details.communication.baud - Input should be a valid number, unable to parse string as a number; "
    "body.technical_details.sensors.wind - Input should be 'Yes' or 'No'; body.technical_details.sensors.humidity - "
    "Input should be 'Yes' or 'No'; body.technical_details.sensors.barometer - Input should be 'Yes' or 'No'; "
    "body.technical_details.sensors.snow_depth - Input should be 'Yes' or 'No'; "
    "body.technical_details.sensors.normal_incidence_pyrheliometer - Input should be 'Yes' or 'No'; "
    "body.technical_details.sensors.rain - Input should be 'Yes' or 'No'; body.technical_details.sensors.temperature - "
    "Input should be 'Yes' or 'No'; body.technical_details.sensors.irradiance - Input should be 'Yes' or 'No'; "
    "body.technical_details.temperature_sensors.ambient_temperature - Input should be 'Yes' or 'No'; "
    "body.technical_details.temperature_sensors.panel_temperature1 - Input should be 'Yes' or 'No'; "
    "body.technical_details.temperature_sensors.panel_temperature2 - Input should be 'Yes' or 'No'; "
    "body.technical_details.temperature_sensors.min_temperature - Input should be a valid number, unable to parse "
    "string as a number; body.technical_details.temperature_sensors.max_temperature - Input should be a valid number, "
    "unable to parse string as a number; body.technical_details.pyranometer_sensors.reference - Input should be 'Yes' "
    "or 'No'; body.technical_details.pyranometer_sensors.azimuth_and_tilt - Input should be 'Yes' or 'No'; "
    "body.technical_details.pyranometer_sensors.azimuth - Input should be a valid number, unable to parse string "
    "as a number; body.technical_details.pyranometer_sensors.tilt - Input should be a valid number, unable to parse "
    "string as a number; body.technical_details.pyranometer_sensors.tracking - String should have at most "
    "100 characters; body.technical_details.pyranometer_sensors.pyranometer - Input should be a valid string; "
    "body.technical_details.monthly_insolation.january - Input should be a valid number, unable to parse string "
    "as a number; body.technical_details.monthly_insolation.february - Input should be a valid number, unable to parse "
    "string as a number; body.technical_details.monthly_insolation.march - Input should be a valid number, unable "
    "to parse string as a number; body.technical_details.monthly_insolation.april - Input should be a valid number, "
    "unable to parse string as a number; body.technical_details.monthly_insolation.may - Input should be "
    "a valid number, unable to parse string as a number; body.technical_details.monthly_insolation.june - Input "
    "should be a valid number, unable to parse string as a number; body.technical_details.monthly_insolation.july - "
    "Input should be a valid number, unable to parse string as a number; "
    "body.technical_details.monthly_insolation.august - Input should be a valid number, unable to parse string "
    "as a number; body.technical_details.monthly_insolation.september - Input should be a valid number, unable "
    "to parse string as a number; body.technical_details.monthly_insolation.october - Input should be a valid number, "
    "unable to parse string as a number; body.technical_details.monthly_insolation.november - Input should be "
    "a valid number, unable to parse string as a number; body.technical_details.monthly_insolation.december - Input "
    "should be a valid number, unable to parse string as a number; "
    "body.technical_details.monthly_insolation.insolation_reference - String should have at most 100 characters; "
    "body.technical_details.monthly_insolation.interpolate_daily_insolation - Input should be 'Yes' or 'No'"
)

NETWORK_CONNECTION_TECHNICAL_DETAILS_INVALID_PAYLOAD = {"provider": "None" * 100, "account_number": 12.333}
NETWORK_CONNECTION_TECHNICAL_DETAILS_INVALID_ERR = (
    "Validation error: body.technical_details.provider - String should have at most 100 characters; "
    "body.technical_details.account_number - Input should be a valid string"
)

NETWORK_GATEWAY_TECHNICAL_DETAILS_INVALID_PAYLOAD = copy.deepcopy(CAMERA_TECHNICAL_DETAILS_INVALID_PAYLOAD)
NETWORK_GATEWAY_TECHNICAL_DETAILS_INVALID_ERR = CAMERA_TECHNICAL_DETAILS_INVALID_ERR

TRANSFORMER_TECHNICAL_DETAILS_INVALID_PAYLOAD = {
    "type": "T" * 101,
    "rating": "R" * 101,
    "frequency": "F" * 101,
    "voltage": "not-float",
    "phase": 11.22,
    "volts": "not-float",
}
TRANSFORMER_TECHNICAL_DETAILS_INVALID_ERR = (
    "Validation error: body.technical_details.type - String should have at most 100 characters; "
    "body.technical_details.rating - String should have at most 100 characters; body.technical_details.frequency - "
    "String should have at most 100 characters; body.technical_details.voltage - Input should be a valid number, "
    "unable to parse string as a number; body.technical_details.phase - Input should be a valid string; "
    "body.technical_details.volts - Input should be a valid number, unable to parse string as a number"
)

TELEMETRY_STATIC_DEVICE_DATA_RESPONSE = {
    "id": "1234",
    "name": "telemetry_device",
    "category": None,
    "serial_number": None,
    "gateway_id": None,
    "function_id": None,
    "driver": None,
    "last_update_ts": "2024-12-13T15:03:42.814484+00:00",
}

AVAILABLE_DEVICE_CATEGORIES = ", ".join([d.value for d in DeviceCategories])
TELEMETRY_INVALID_CATEGORY_ERR = (
    "Received invalid `category`=invalid_category from BigQuery - ignoring this field. "
    f"Validation error: Input should be one of '{AVAILABLE_DEVICE_CATEGORIES}'"
)
TELEMETRY_INVALID_CATEGORY_TYPE_ERR = (
    "Received invalid `device_type`=DeviceTypes.canopy from BigQuery - ignoring this field. "
    "Validation error: 422: There is no 'Canopy' type in 'Inverter' category. Input should be: "
    "'String', 'Micro Inverter', 'Power Optimizers'"
)
TELEMETRY_INVALID_LAST_UPDATED_ERR = (
    "Received invalid `last_updated_date`=wrong time from BigQuery - ignoring this field. "
    "Invalid isoformat string: 'wrong time'"
)

DEVICES_PERFORMANCE_DASHBOARD_BIGQUERY_RESPONSE = [
    {
        "device_id": 1,
        "device_power_actual": [{"value": 39.936, "ts": datetime.datetime(2024, 12, 9, 13, 15)}],
        "device_power_expected": [{"value": 42, "ts": datetime.datetime(2024, 12, 9, 13, 15)}],
    }
]

DEVICE_PERFORMANCE_CHART_RESPONSE_NOT_MAPPED = {
    "data": [{"name": TEST_INVERTER_DEVICE_NAME, "performance": "N/A", "actual": "N/A", "expected": "N/A"}]
}
DEVICE_PERFORMANCE_CHART_RESPONSE_MAPPED_NO_BQ_DATA = {
    "data": [{"name": TEST_INVERTER_DEVICE_NAME, "performance": 0, "actual": 0, "expected": 0}]
}
# depends on DEVICES_PERFORMANCE_DASHBOARD_BIGQUERY_RESPONSE metrics
DEVICE_PERFORMANCE_CHART_RESPONSE_MAPPED = {
    "data": [{"name": TEST_INVERTER_DEVICE_NAME, "performance": 95, "actual": 39.94, "expected": 42}]
}
