import copy
from unittest.mock import MagicMock


def fill_string_template(template_str, **params):
    return template_str.format(**params)


def conditional_bq_side_effect(*args, **kwargs):  # noqa: U100
    query_response_object = MagicMock()
    result_value = None

    if args and args[0].startswith("SELECT * FROM"):
        result_value = [
            {"some": "value", "estimated_generation": [1.1, 2.2, 3.3, 4.4, 5.5, 6.6, 7.0, 8.0, 9.0, 10.0, 11.1, 12.8]}
        ]
    query_response_object.result.return_value = result_value
    return query_response_object


BQ_SELECT_DEVICE_STATEMENT_TEMPLATE = "SELECT * FROM `{table_name}` WHERE site_id={site_id} AND device_id={device_id}"
BQ_SELECT_SITE_STATEMENT_TEMPLATE = "SELECT * FROM `{table_name}` WHERE site_id={site_id}"

INVERTER_TECHNICAL_DETAILS_BQ_REQUIRED_FIELDS_PAYLOAD = {"power": {"cec_efficiency": 0.8, "pv_modules_number": 5}}
BQ_INSERT_INVERTER_DEVICE_DETAILS_STATEMENT_TEMPLATE = (
    "INSERT INTO `{table_name}` (cec_efficiency, number_of_pv_modules_per_inverter, site_id, device_id, "
    "device_category) VALUES (@cec_efficiency, @number_of_pv_modules_per_inverter, @site_id, @device_id, "
    "@device_category)"
)
BQ_UPDATE_INVERTER_DEVICE_DETAILS_STATEMENT_TEMPLATE = (
    "UPDATE `{table_name}` SET cec_efficiency = @update_cec_efficiency, number_of_pv_modules_per_inverter = "
    "@update_number_of_pv_modules_per_inverter WHERE site_id={site_id} AND device_id={device_id}"
)


MODULE_TECHNICAL_DETAILS_BQ_REQUIRED_FIELDS_PAYLOAD = {
    "power": {
        "max_power_tolerance": 3,
        "min_power_tolerance": -3,
        "power_thermal_coefficient": 0.97,
        "year_1_degradation": 2,
        "annual_degradation": 0.06,
    }
}
BQ_INSERT_MODULE_DEVICE_DETAILS_STATEMENT_TEMPLATE = (
    "INSERT INTO `{table_name}` (thermal_coefficient_of_power, power_tolerance_min, power_tolerance_max, "
    "year_1_degradation, annual_degradation, site_id, device_id, device_category) VALUES "
    "(@thermal_coefficient_of_power, @power_tolerance_min, @power_tolerance_max, @year_1_degradation, "
    "@annual_degradation, @site_id, @device_id, @device_category)"
)
BQ_UPDATE_MODULE_DEVICE_DETAILS_STATEMENT_TEMPLATE = (
    "UPDATE `{table_name}` SET thermal_coefficient_of_power = @update_thermal_coefficient_of_power, "
    "power_tolerance_min = @update_power_tolerance_min, power_tolerance_max = @update_power_tolerance_max, "
    "year_1_degradation = @update_year_1_degradation, annual_degradation = @update_annual_degradation WHERE "
    "site_id={site_id} AND device_id={device_id}"
)

SITE_ASSET_OVERVIEW_CARD_BQ_REQUIRED_FIELDS_PAYLOAD = {
    "dc_wiring_loss": 11,
    "ac_wiring_loss": -2.2,
    "medium_voltage_loss": 63,
    "mv_line_loss": -0.01,
}
BQ_INSERT_SITE_ASSET_OVERVIEW_CARD_DETAILS_STATEMENT_TEMPLATE = (
    "INSERT INTO `{table_name}` (dc_ohmic_wiring_loss, ac_ohmic_wiring_loss, medium_voltage_transfo_loss, "
    "mv_line_ohmic_loss, site_id) VALUES (@dc_ohmic_wiring_loss, @ac_ohmic_wiring_loss, @medium_voltage_transfo_loss, "
    "@mv_line_ohmic_loss, @site_id)"
)
BQ_UPDATE_SITE_ASSET_OVERVIEW_CARD_DETAILS_STATEMENT_TEMPLATE = (
    "UPDATE `{table_name}` SET dc_ohmic_wiring_loss = @update_dc_ohmic_wiring_loss, ac_ohmic_wiring_loss = "
    "@update_ac_ohmic_wiring_loss, medium_voltage_transfo_loss = @update_medium_voltage_transfo_loss, "
    "mv_line_ohmic_loss = @update_mv_line_ohmic_loss WHERE site_id={site_id}"
)

SITE_KEY_DATES_CARD_BQ_REQUIRED_FIELDS_PAYLOAD = {"permission_to_operate": "2029-10-01"}
BQ_INSERT_SITE_KEY_DATES_CARD_DETAILS_STATEMENT_TEMPLATE = (
    "INSERT INTO `{table_name}` (permission_to_operate, site_id) VALUES (@permission_to_operate, @site_id)"
)
BQ_UPDATE_SITE_KEY_DATES_CARD_DETAILS_STATEMENT_TEMPLATE = (
    "UPDATE `{table_name}` SET permission_to_operate = @update_permission_to_operate WHERE site_id={site_id}"
)

BQ_INSERT_DD_KEY_DETAILS_STATEMENT_TEMPLATE = (
    "INSERT INTO `{table_name}` ({key_name}, site_id) VALUES (@{key_name}, @site_id)"
)
BQ_UPDATE_DD_KEY_DETAILS_STATEMENT_TEMPLATE = (
    "UPDATE `{table_name}` SET {key_name} = @update_{key_name} WHERE site_id={site_id}"
)

ESTIMATED_GENERATION_PAYLOAD = [0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]


def generate_estimated_generation_payload(position, value):
    """Update payload to set value on specific place"""
    res = copy.deepcopy(ESTIMATED_GENERATION_PAYLOAD)
    res[position] = value
    return res
