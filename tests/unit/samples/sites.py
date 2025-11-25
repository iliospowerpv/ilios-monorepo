import datetime
from copy import deepcopy
from decimal import Decimal
from unittest.mock import ANY

from app.models.site import MountTypes
from app.schema.site_details import URL_PATTERN

VALID_SITE_BODY1 = {
    "company_id": 1,
    "name": "Test site 1",
    "address": "6645 1/2 E OLYMPIC BLVD LOS ANGELES CA 90022-4772",
    "city": "LLOS ANGELES",
    "state": "AK",
    "county": "Cherokee",
    "zip_code": "1234",
    "system_size_ac": 100.0,
    "system_size_dc": 200.0,
    "lon_lat_url": "41° 56’ 54.3732",
}

VALID_SITE_BODY2 = {
    "company_id": 1,
    "name": "Test site 2",
    "address": "6645 1/2 E OLYMPIC BLVD LOS ANGELES CA 90022-4772",
    "city": "LLOS ANGELES",
    "state": "GA",
    "county": "Dale",
    "zip_code": "1234",
    "system_size_ac": 100.0,
    "system_size_dc": 200.0,
    "lon_lat_url": "41° 56’ 54.3732",
}

TEST_SITE_NAME = "Windmills Farm"
TEST_SITE_ADDRESS = "833 Church Hill Road, Augusta, ME"
TEST_SITE_SYSTEM_SIZE_AC = 100.0
TEST_SITE_SYSTEM_SIZE_DC = 200.0
TEST_SITE_BODY = {
    "name": TEST_SITE_NAME,
    "address": TEST_SITE_ADDRESS,
    "city": "Augusta",
    "state": "ME",
    "county": "Kennebec",
    "zip_code": "04338",
    "system_size_ac": TEST_SITE_SYSTEM_SIZE_AC,
    "system_size_dc": TEST_SITE_SYSTEM_SIZE_DC,
    "lon_lat_url": "41° 56’ 54.3732",
    "cameras_uuids": [],
}

TEST_SITE_DAS_CONNECTION_FIELDS = {
    "das_connection_name": None,
    "telemetry_site_name": None,
}

TEST_SITE_BODY_DAS_SYSTEM_FIELDS = {"account": "DAS account", "username": "DAS username", "password": "12345678"}
TEST_SITE_BODY_JSON = deepcopy(TEST_SITE_BODY)

TEST_SITE_BODY_JSON_WITHOUT_CAMERA_DETAILS = deepcopy(TEST_SITE_BODY)
del TEST_SITE_BODY_JSON_WITHOUT_CAMERA_DETAILS["cameras_uuids"]
TEST_SITE_DETAILS_SITE_LEVEL_SECTION = {
    **deepcopy(TEST_SITE_BODY_JSON_WITHOUT_CAMERA_DETAILS),
    "address": "833 Church Hill Road, Augusta, ME",
    "city": "Augusta",
    "county": "Kennebec",
    "greenhouse_gas_offset": None,
    "incentive_program": None,
    "lon_lat_url": "41° 56’ 54.3732",
    "name": "Windmills Farm",
    "project_id": None,
    "pvsyst": None,
    "state": "ME",
    "status": None,
    "system_size_ac": 100.0,
    "system_size_dc": 200.0,
    "zip_code": "04338",
    "year_one_expected_production": None,
    "degradation_amount": None,
    "capacity_as_percent_of_total_portfolio": None,
    "das_provider": None,
    "das_account": None,
    "das_username": None,
    "das_password": None,
}

TEST_SITE_DETAILS_ASSET_OVERVIEW_SECTION = {
    "module_quantity": None,
    "inverter_quantity": None,
    "project_type": None,
    "mount_type": None,
    "battery_storage": None,
    "dc_wiring_loss": None,
    "ac_wiring_loss": None,
    "medium_voltage_loss": None,
    "mv_line_loss": None,
}

TEST_SITE_DETAILS_OWNERSHIP_SECTION = {
    "ownership_structure": None,
    "hold_co": None,
    "project_co": None,
    "guarantor": None,
    "tax_credit_fund": None,
}

TEST_SITE_DETAILS_TAX_EQUITY_SECTION = {
    "tax_equity_buyout_amount": None,
    "tax_equity_buyout_date": None,
    "tax_equity_fund": None,
    "tax_equity_pref_rate": None,
    "tax_equity_provider": None,
    "smartsheet_data_tape": None,
}

TEST_SITE_DETAILS_KEY_DATES_SECTION = {
    "mechanical_completion_date": None,
    "substantial_completion_date": None,
    "final_completion_date": None,
    "permission_to_operate": None,
    "placed_in_service_date": None,
    "financial_close_date": None,
}

TEST_SITE_DETAILS_OM_SECTION = {
    "provider": None,
    "agreement_effective_date": None,
    "o_and_m_rate": None,
    "o_and_m_escalator": None,
    "production_guarantee": None,
    "om_address": None,
    "om_contact_name": None,
    "om_contact_email": None,
    "om_contact_phone": None,
}

TEST_SITE_DETAILS_INTERCONNECTION_SECTION = {
    "iut_address": None,
    "interconnection_agreement_effective_date": None,
    "ppa_term": None,
    "ppa_effective_date": None,
    "remaining_ppa_term": None,
    "production_guarantee": None,
    "provider": None,
    "utility_rate": None,
    "iut_contact_email": None,
    "iut_contact_name": None,
    "iut_contact_phone": None,
}

TEST_SITE_DETAILS_INTERCONNECTION_SECTION_DD_POPULATED = deepcopy(TEST_SITE_DETAILS_INTERCONNECTION_SECTION)
TEST_SITE_DETAILS_INTERCONNECTION_SECTION_DD_POPULATED.update(
    {
        "interconnection_agreement_effective_date": None,
        "ppa_term": "20",
        "ppa_effective_date": "12/14/2022",
        "remaining_ppa_term": ANY,  # field won't be static, have separate test for that
    }
)

TEST_SITE_DETAILS_EPC_CONTRACTOR_SECTION = {
    "provider": None,
    "agreement_effective_date": None,
    "epc_address": None,
    "epc_contact_name": None,
    "epc_contact_email": None,
    "epc_contact_phone": None,
}

TEST_SITE_DETAILS_CSM_SECTION = {
    "csm_provider": None,
    "csm_address": None,
    "csm_contact_name": None,
    "csm_contact_email": None,
    "csm_contact_phone": None,
    "csm_fee": None,
    "escalator": None,
    "escalator_effective": None,
}

TEST_SITE_DETAILS_INSURANCE_PROVIDER_SECTION = {
    "insurance_provider": None,
    "insurance_address": None,
}

TEST_SITE_DETAILS_SITE_LEASE_SECTION = {
    "landlord": None,
    "tenant": None,
    "property_size": None,
    "effective_date": None,
    "rent_commencement": None,
    "rent_amount": None,
    "rent_escalator": None,
    "rent_escalator_effective_date": None,
    "payment_due_date": None,
    "lease_payment_method": None,
    "lease_payment_frequency": None,
    "initial_term": None,
    "renewal_terms": None,
    "landlord_contact_phone": None,
}

TEST_SITE_DETAILS_VEGETATION_VENDOR_SECTION = {
    "vv_provider": None,
    "vv_address": None,
    "vv_contact_name": None,
    "vv_contact_phone": None,
    "vv_contact_email": None,
}

TEST_SITE_DETAILS_OFFTAKER_SECTION = {
    "offtaker_name": None,
    "offtaker_type": None,
    "credit_rating": None,
    "rating_agency": None,
    "date_of_rating": None,
}

TEST_SITE_DETAILS_COMPLIANCE_SECTION = {
    "entity": None,
    "bank": None,
    "report_due_date": None,
    "fiscal_year_end": None,
    "tax_return_deadline": None,
}

TEST_SITE_DETAILS_BODY_JSON = {
    "asset_overview": TEST_SITE_DETAILS_ASSET_OVERVIEW_SECTION,
    "community_solar_manager": TEST_SITE_DETAILS_CSM_SECTION,
    "epc_contractor": TEST_SITE_DETAILS_EPC_CONTRACTOR_SECTION,
    "insurance_provider": TEST_SITE_DETAILS_INSURANCE_PROVIDER_SECTION,
    "interconnection": TEST_SITE_DETAILS_INTERCONNECTION_SECTION_DD_POPULATED,
    "key_dates": TEST_SITE_DETAILS_KEY_DATES_SECTION,
    "o_and_m": TEST_SITE_DETAILS_OM_SECTION,
    "ownership": TEST_SITE_DETAILS_OWNERSHIP_SECTION,
    "site_level_details": TEST_SITE_DETAILS_SITE_LEVEL_SECTION,
    "tax_equity": TEST_SITE_DETAILS_TAX_EQUITY_SECTION,
    "site_lease": TEST_SITE_DETAILS_SITE_LEASE_SECTION,
    "vegetation_vendor": TEST_SITE_DETAILS_VEGETATION_VENDOR_SECTION,
    "offtaker": TEST_SITE_DETAILS_OFFTAKER_SECTION,
    "compliance": TEST_SITE_DETAILS_COMPLIANCE_SECTION,
}

INVALID_SITE_ZIP_CODE_MSG = "Validation error: body.zip_code - String should match pattern '^[0-9]+$'"

INVALID_SITE_ZIP_CODE_TO_LONG_MSG = (
    "Validation error: body.zip_code - Value error, zip code must be no longer than 5 digits."
)

INVALID_DAS_MSG = (
    "Validation error: body.das - Input should be 'Also Energy', 'Chint Monitoring System', 'LocusNOC', "
    "'Mana Monitoring System', 'Solarlog', 'Solarenview' or 'Sunny Portal'"
)

INVALID_STATE_FILTER_MSG = (
    "Validation error: query.state - Input should be 'AK', 'AL', 'AR', 'AZ', 'CA', 'CO', 'CT', "
    "'DC', 'DE', 'FL', 'GA', 'HI', 'IA', 'ID', 'IL', 'IN', 'KS', 'KY', 'LA', 'MA', 'MD', 'ME', "
    "'MI', 'MN', 'MO', 'MS', 'MT', 'NC', 'ND', 'NE', 'NH', 'NJ', 'NM', 'NV', 'NY', 'OH', 'OK', "
    "'OR', 'PA', 'RI', 'SC', 'SD', 'TN', 'TX', 'UT', 'VA', 'VT', 'WA', 'WI', 'WV' or 'WY'"
)

SITE_DETAILS_LONG_STRING_SAMPLE = "a" * 101

TEST_SITE_DETAILS_SITE_LEVEL_SECTION_UPDATE_PAYLOAD = {
    "status": "Construction",
    "project_id": "IL-112263",
    "pvsyst": "web.link",
    "greenhouse_gas_offset": "Multiple options",
    "incentive_program": "Planned in the 1st quoter of the 2025",
    "das_provider": "KMC",
    "das_account": "Personal",
    "das_username": "TestUser",
    "das_password": "1223334444",
}
TEST_SITE_DETAILS_SITE_LEVEL_SECTION_UPDATED = deepcopy(TEST_SITE_DETAILS_SITE_LEVEL_SECTION)
TEST_SITE_DETAILS_SITE_LEVEL_SECTION_UPDATED.update(TEST_SITE_DETAILS_SITE_LEVEL_SECTION_UPDATE_PAYLOAD)
TEST_SITE_DETAILS_SITE_LEVEL_SECTION_UPDATE_PAYLOAD_INVALID = {
    "status": SITE_DETAILS_LONG_STRING_SAMPLE,
    "project_id": SITE_DETAILS_LONG_STRING_SAMPLE,
    "pvsyst": "not-a-link",
    "greenhouse_gas_offset": SITE_DETAILS_LONG_STRING_SAMPLE,
    "incentive_program": SITE_DETAILS_LONG_STRING_SAMPLE,
    "das_provider": SITE_DETAILS_LONG_STRING_SAMPLE,
    "das_account": SITE_DETAILS_LONG_STRING_SAMPLE,
    "das_username": SITE_DETAILS_LONG_STRING_SAMPLE,
    "das_password": SITE_DETAILS_LONG_STRING_SAMPLE,
}

TEST_SITE_DETAILS_SITE_LEVEL_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR = (
    "Validation error: status - Input should be 'Construction', 'Placed in Service', 'Decommissioned' or 'Sold'; "
    f"project_id - String should have at most 100 characters; pvsyst - String should match pattern '{URL_PATTERN}'; "
    f"greenhouse_gas_offset - String should have at most 100 characters; incentive_program - "
    "String should have at most 100 characters; das_provider - String should have at most 100 characters; "
    "das_account - String should have at most 100 characters; das_username - String should have at most 100 "
    "characters; das_password - String should have at most 100 characters"
)


TEST_SITE_DETAILS_ASSET_OVERVIEW_SECTION_UPDATE_PAYLOAD = {
    "battery_storage": "Yes",
    "mount_type": MountTypes.canopy.value,
    "dc_wiring_loss": 11,
    "ac_wiring_loss": -2.2,
    "medium_voltage_loss": 63,
    "mv_line_loss": -0.01,
}
TEST_SITE_DETAILS_ASSET_OVERVIEW_SECTION_UPDATED = deepcopy(TEST_SITE_DETAILS_ASSET_OVERVIEW_SECTION)
TEST_SITE_DETAILS_ASSET_OVERVIEW_SECTION_UPDATED.update(TEST_SITE_DETAILS_ASSET_OVERVIEW_SECTION_UPDATE_PAYLOAD)
TEST_SITE_DETAILS_ASSET_OVERVIEW_SECTION_UPDATE_PAYLOAD_INVALID = {
    "battery_storage": "something",
}
TEST_SITE_DETAILS_ASSET_OVERVIEW_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR = (
    "Validation error: battery_storage - Value error, Expected 'Yes' or 'No'; dc_wiring_loss - Field required; "
    "ac_wiring_loss - Field required; medium_voltage_loss - Field required; mv_line_loss - Field required"
)

TEST_SITE_DETAILS_OWNERSHIP_SECTION_UPDATE_PAYLOAD = {
    "ownership_structure": "OOO",
    "hold_co": "Test Inc.",
    "project_co": "Slow Co",
    "tax_credit_fund": "Credit fund",
}
TEST_SITE_DETAILS_OWNERSHIP_SECTION_UPDATED = deepcopy(TEST_SITE_DETAILS_OWNERSHIP_SECTION)
TEST_SITE_DETAILS_OWNERSHIP_SECTION_UPDATED.update(TEST_SITE_DETAILS_OWNERSHIP_SECTION_UPDATE_PAYLOAD)
TEST_SITE_DETAILS_OWNERSHIP_SECTION_UPDATE_PAYLOAD_INVALID = {
    "ownership_structure": SITE_DETAILS_LONG_STRING_SAMPLE,
    "hold_co": SITE_DETAILS_LONG_STRING_SAMPLE,
    "project_co": SITE_DETAILS_LONG_STRING_SAMPLE,
}
TEST_SITE_DETAILS_OWNERSHIP_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR = (
    "Validation error: ownership_structure - String should have at most 100 characters; hold_co - String should have "
    "at most 100 characters; project_co - String should have at most 100 characters"
)

TEST_SITE_DETAILS_TAX_EQUITY_SECTION_UPDATE_PAYLOAD = {
    "tax_equity_buyout_amount": 460874,
    "tax_equity_buyout_date": "2026-12-21",
    "tax_equity_fund": "AZ-REA TCF2, LLC",
    "tax_equity_pref_rate": 2.73,
    "tax_equity_provider": "AZ-REA LLC",
    "smartsheet_data_tape": "($XX.XX)",
}
TEST_SITE_DETAILS_TAX_EQUITY_SECTION_UPDATED = deepcopy(TEST_SITE_DETAILS_TAX_EQUITY_SECTION)
TEST_SITE_DETAILS_TAX_EQUITY_SECTION_UPDATED.update(TEST_SITE_DETAILS_TAX_EQUITY_SECTION_UPDATE_PAYLOAD)
TEST_SITE_DETAILS_TAX_EQUITY_SECTION_UPDATE_PAYLOAD_INVALID = {
    "tax_equity_buyout_amount": "not-a-number",
    "tax_equity_buyout_date": "not-a-date",
    "tax_equity_fund": SITE_DETAILS_LONG_STRING_SAMPLE,
    "tax_equity_pref_rate": "not-a-number",
    "tax_equity_provider": SITE_DETAILS_LONG_STRING_SAMPLE,
    "smartsheet_data_tape": SITE_DETAILS_LONG_STRING_SAMPLE,
}
TEST_SITE_DETAILS_TAX_EQUITY_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR = (
    "Validation error: tax_equity_fund - String should have at most 100 characters; tax_equity_provider - String "
    "should have at most 100 characters; tax_equity_buyout_amount - Input should be a valid number, unable to parse "
    "string as a number; tax_equity_buyout_date - Input should be a valid date or datetime, invalid character in year; "
    "tax_equity_pref_rate - Input should be a valid number, unable to parse string as a number; "
    "smartsheet_data_tape - String should have at most 100 characters"
)
TEST_SITE_DETAILS_TAX_EQUITY_SECTION_UPDATE_PAYLOAD_INVALID_DATES = {
    "tax_equity_buyout_date": "0000-01-01",
}
TEST_SITE_DETAILS_TAX_EQUITY_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR_DATES = (
    "Validation error: tax_equity_buyout_date - Value error, Year must be 1900 or greater"
)

TEST_SITE_DETAILS_KEY_DATES_SECTION_UPDATE_PAYLOAD = {
    "permission_to_operate": "2025-01-07",
    "placed_in_service_date": "2020-01-04",
    "financial_close_date": "2025-01-07",
}
TEST_SITE_DETAILS_KEY_DATES_SECTION_SECTION_UPDATED = deepcopy(TEST_SITE_DETAILS_KEY_DATES_SECTION)
TEST_SITE_DETAILS_KEY_DATES_SECTION_SECTION_UPDATED.update(TEST_SITE_DETAILS_KEY_DATES_SECTION_UPDATE_PAYLOAD)
TEST_SITE_DETAILS_KEY_DATES_SECTION_UPDATE_PAYLOAD_INVALID = {
    "permission_to_operate": True,
    "placed_in_service_date": "not-a-date",
    "financial_close_date": 1,
}
TEST_SITE_DETAILS_KEY_DATES_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR = (
    "Validation error: permission_to_operate - Input should be a valid date; placed_in_service_date - Input should be "
    "a valid date or datetime, invalid character in year; financial_close_date - Datetimes provided to dates should "
    "have zero time - e.g. be exact dates"
)
TEST_SITE_DETAILS_KEY_DATES_SECTION_UPDATE_PAYLOAD_INVALID_DATES = {
    "permission_to_operate": "0000-01-01",
    "placed_in_service_date": "0101-12-21",
    "financial_close_date": "0001-10-10",
}
TEST_SITE_DETAILS_KEY_DATES_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR_DATES = (
    "Validation error: permission_to_operate - Value error, Year must be 1900 or greater; placed_in_service_date - "
    "Value error, Year must be 1900 or greater; financial_close_date - Value error, Year must be 1900 or greater"
)

TEST_SITE_DETAILS_OM_SECTION_UPDATE_PAYLOAD = {
    "om_address": "1500 19th Ave. SW Byron, MN 55920",
    "om_contact_name": "John Starks",
    "om_contact_email": "johnstarks@gmail.com",
    "om_contact_phone": "5733455671",
    "o_and_m_rate": 1,
}
TEST_SITE_DETAILS_OM_SECTION_UPDATED = deepcopy(TEST_SITE_DETAILS_OM_SECTION)
TEST_SITE_DETAILS_OM_SECTION_UPDATED.update(TEST_SITE_DETAILS_OM_SECTION_UPDATE_PAYLOAD)
TEST_SITE_DETAILS_OM_SECTION_UPDATE_PAYLOAD_INVALID = {
    "om_address": SITE_DETAILS_LONG_STRING_SAMPLE,
    "om_contact_name": SITE_DETAILS_LONG_STRING_SAMPLE,
    "om_contact_email": "not-an-email",
    "om_contact_phone": "not-a-phone",
}
TEST_SITE_DETAILS_OM_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR = (
    "Validation error: om_address - String should have at most 100 characters; om_contact_name - String should have at "
    "most 100 characters; om_contact_email - value is not a valid email address: The email address is not valid. It "
    "must have exactly one @-sign.; om_contact_phone - Value error, Expected numbers-only"
)

TEST_SITE_DETAILS_INTERCONNECTION_SECTION_UPDATE_PAYLOAD = {
    "iut_address": "60 Campanelli Drive, Braintree, MA",
    "iut_contact_email": "stanmcbride@gmail.com",
    "iut_contact_name": "Stan Mcbride",
    "iut_contact_phone": "6043455671",
    "utility_rate": "AAA",
}
TEST_SITE_DETAILS_INTERCONNECTION_SECTION_UPDATED = deepcopy(TEST_SITE_DETAILS_INTERCONNECTION_SECTION)
TEST_SITE_DETAILS_INTERCONNECTION_SECTION_UPDATED.update(TEST_SITE_DETAILS_INTERCONNECTION_SECTION_UPDATE_PAYLOAD)
TEST_SITE_DETAILS_INTERCONNECTION_SECTION_UPDATE_PAYLOAD_INVALID = {
    "iut_address": SITE_DETAILS_LONG_STRING_SAMPLE,
    "iut_contact_email": True,
    "iut_contact_name": SITE_DETAILS_LONG_STRING_SAMPLE,
    "iut_contact_phone": "11",
    "utility_rate": SITE_DETAILS_LONG_STRING_SAMPLE,
}
TEST_SITE_DETAILS_INTERCONNECTION_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR = (
    "Validation error: iut_address - String should have at most 100 characters; iut_contact_name - String should have "
    "at most 100 characters; iut_contact_email - Input should be a valid string; iut_contact_phone - Value error, Must "
    "be 10 digits; utility_rate - String should have at most 100 characters"
)

TEST_SITE_DETAILS_EPC_CONTRACTOR_SECTION_UPDATE_PAYLOAD = {
    "epc_address": "1503 Country Club Rd SE, Byron, MN 55920",
    "epc_contact_name": "Collin Drake",
    "epc_contact_email": "collindr@gmail.com",
    "epc_contact_phone": "6043455671",
}
TEST_SITE_DETAILS_EPC_CONTRACTOR_SECTION_UPDATED = deepcopy(TEST_SITE_DETAILS_EPC_CONTRACTOR_SECTION)
TEST_SITE_DETAILS_EPC_CONTRACTOR_SECTION_UPDATED.update(TEST_SITE_DETAILS_EPC_CONTRACTOR_SECTION_UPDATE_PAYLOAD)
TEST_SITE_DETAILS_EPC_CONTRACTOR_SECTION_UPDATE_PAYLOAD_INVALID = {
    "epc_address": SITE_DETAILS_LONG_STRING_SAMPLE,
    "epc_contact_name": SITE_DETAILS_LONG_STRING_SAMPLE,
    "epc_contact_email": SITE_DETAILS_LONG_STRING_SAMPLE,
    "epc_contact_phone": SITE_DETAILS_LONG_STRING_SAMPLE,
}
TEST_SITE_DETAILS_EPC_CONTRACTOR_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR = (
    "Validation error: epc_address - String should have at most 100 characters; epc_contact_name - String should have "
    "at most 100 characters; epc_contact_email - value is not a valid email address: The email address is not valid. "
    "It must have exactly one @-sign.; epc_contact_phone - Value error, Expected numbers-only"
)

TEST_SITE_DETAILS_CSM_SECTION_UPDATE_PAYLOAD = {
    "csm_provider": "PowerMarket",
    "csm_address": "21 Alpha Road, Chelmsford, MA 01824",
    "csm_contact_name": "Collin Snow",
    "csm_contact_email": "collinsnow@gmail.com",
    "csm_contact_phone": "6043455671",
    "csm_fee": 24.45,
    "escalator": 35.45,
    "escalator_effective": "2024-05-12",
}
TEST_SITE_DETAILS_CSM_SECTION_UPDATED = deepcopy(TEST_SITE_DETAILS_CSM_SECTION)
TEST_SITE_DETAILS_CSM_SECTION_UPDATED.update(TEST_SITE_DETAILS_CSM_SECTION_UPDATE_PAYLOAD)
TEST_SITE_DETAILS_CSM_SECTION_UPDATE_PAYLOAD_INVALID = {
    "csm_provider": SITE_DETAILS_LONG_STRING_SAMPLE,
    "csm_address": SITE_DETAILS_LONG_STRING_SAMPLE,
    "csm_contact_name": SITE_DETAILS_LONG_STRING_SAMPLE,
    "csm_contact_email": SITE_DETAILS_LONG_STRING_SAMPLE,
    "csm_contact_phone": SITE_DETAILS_LONG_STRING_SAMPLE,
    "csm_fee": "not-a-number",
    "escalator": "not-a-number",
    "escalator_effective": "not-a-date",
}
TEST_SITE_DETAILS_CSM_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR = (
    "Validation error: csm_provider - String should have at most 100 characters; csm_address - String should have at "
    "most 100 characters; csm_contact_name - String should have at most 100 characters; csm_contact_email - value is "
    "not a valid email address: The email address is not valid. It must have exactly one @-sign.; csm_contact_phone - "
    "Value error, Expected numbers-only; csm_fee - Input should be a valid number, unable to parse string as a number; "
    "escalator - Input should be a valid number, unable to parse string as a number; escalator_effective - Input "
    "should be a valid date or datetime, invalid character in year"
)
TEST_SITE_DETAILS_CSM_SECTION_UPDATE_PAYLOAD_INVALID_DATES = {
    "escalator_effective": "0001-10-10",
}
TEST_SITE_DETAILS_CSM_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR_DATES = (
    "Validation error: escalator_effective - Value error, Year must be 1900 or greater"
)

TEST_SITE_DETAILS_INSURANCE_PROVIDER_SECTION_UPDATE_PAYLOAD = {
    "insurance_provider": "Chubb Insurance",
    "insurance_address": "100 Enterprise Ave, Gardiner, ME 04345",
}
TEST_SITE_DETAILS_INSURANCE_PROVIDER_SECTION_UPDATED = deepcopy(TEST_SITE_DETAILS_INSURANCE_PROVIDER_SECTION)
TEST_SITE_DETAILS_INSURANCE_PROVIDER_SECTION_UPDATED.update(TEST_SITE_DETAILS_INSURANCE_PROVIDER_SECTION_UPDATE_PAYLOAD)
TEST_SITE_DETAILS_INSURANCE_PROVIDER_SECTION_UPDATE_PAYLOAD_INVALID = {
    "insurance_provider": SITE_DETAILS_LONG_STRING_SAMPLE,
    "insurance_address": SITE_DETAILS_LONG_STRING_SAMPLE,
}
TEST_SITE_DETAILS_INSURANCE_PROVIDER_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR = (
    "Validation error: insurance_provider - String should have at most 100 characters; insurance_address - String "
    "should have at most 100 characters"
)

TEST_SITE_DETAILS_SITE_LEASE_SECTION_UPDATE_PAYLOAD = {
    "payment_due_date": "2025-05-12",
    "lease_payment_method": "Check",
    "lease_payment_frequency": "Monthly",
    "landlord_contact_phone": "6045685678",
}
TEST_SITE_DETAILS_SITE_LEASE_SECTION_UPDATED = deepcopy(TEST_SITE_DETAILS_SITE_LEASE_SECTION)
TEST_SITE_DETAILS_SITE_LEASE_SECTION_UPDATED.update(TEST_SITE_DETAILS_SITE_LEASE_SECTION_UPDATE_PAYLOAD)
TEST_SITE_DETAILS_SITE_LEASE_SECTION_UPDATE_PAYLOAD_INVALID = {
    "rent_escalator": SITE_DETAILS_LONG_STRING_SAMPLE,
    "payment_due_date": SITE_DETAILS_LONG_STRING_SAMPLE,
    "lease_payment_method": SITE_DETAILS_LONG_STRING_SAMPLE,
    "lease_payment_frequency": SITE_DETAILS_LONG_STRING_SAMPLE,
    "landlord_contact_phone": SITE_DETAILS_LONG_STRING_SAMPLE,
}
TEST_SITE_DETAILS_SITE_LEASE_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR = (
    "Validation error: payment_due_date - Input should be a valid date or datetime, invalid character in year; "
    "lease_payment_method - Input should be 'Check', 'Credit Card' or 'Wire'; lease_payment_frequency - "
    "Input should be 'Monthly', 'Quarterly', 'Semi Annual' or 'Annual'; landlord_contact_phone - Value error, "
    "Expected numbers-only"
)

TEST_SITE_DETAILS_VEGETATION_VENDOR_SECTION_UPDATE_PAYLOAD = {
    "vv_provider": "Acme Corporation",
    "vv_address": "5445 N 27th St, Milwaukee, WI",
    "vv_contact_name": "John Doe",
    "vv_contact_phone": "5551234567",
    "vv_contact_email": "john.doe@acmecorp.com",
}
TEST_SITE_DETAILS_VEGETATION_VENDOR_SECTION_UPDATED = deepcopy(TEST_SITE_DETAILS_VEGETATION_VENDOR_SECTION)
TEST_SITE_DETAILS_VEGETATION_VENDOR_SECTION_UPDATED.update(TEST_SITE_DETAILS_VEGETATION_VENDOR_SECTION_UPDATE_PAYLOAD)
TEST_SITE_DETAILS_VEGETATION_VENDOR_SECTION_UPDATE_PAYLOAD_INVALID = {
    "vv_provider": SITE_DETAILS_LONG_STRING_SAMPLE,
    "vv_address": SITE_DETAILS_LONG_STRING_SAMPLE,
    "vv_contact_name": SITE_DETAILS_LONG_STRING_SAMPLE,
    "vv_contact_phone": SITE_DETAILS_LONG_STRING_SAMPLE,
    "vv_contact_email": SITE_DETAILS_LONG_STRING_SAMPLE,
}
TEST_SITE_DETAILS_VEGETATION_VENDOR_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR = (
    "Validation error: vv_provider - String should have at most 100 characters; vv_address - String should have at "
    "most 100 characters; vv_contact_name - String should have at most 100 characters; vv_contact_phone - Value error, "
    "Expected numbers-only; vv_contact_email - value is not a valid email address: The email address is not valid. It "
    "must have exactly one @-sign."
)

TEST_SITE_DETAILS_OFFTAKER_SECTION_UPDATE_PAYLOAD = {
    "offtaker_name": "Sunshine Energy",
    "offtaker_type": "Community Solar",
    "credit_rating": "BB+",
    "rating_agency": "Standard & Poor’s",
    "date_of_rating": "2024-01-07",
}
TEST_SITE_DETAILS_OFFTAKER_SECTION_UPDATED = deepcopy(TEST_SITE_DETAILS_OFFTAKER_SECTION)
TEST_SITE_DETAILS_OFFTAKER_SECTION_UPDATED.update(TEST_SITE_DETAILS_OFFTAKER_SECTION_UPDATE_PAYLOAD)
TEST_SITE_DETAILS_OFFTAKER_SECTION_UPDATE_PAYLOAD_INVALID = {
    "offtaker_name": SITE_DETAILS_LONG_STRING_SAMPLE,
    "offtaker_type": SITE_DETAILS_LONG_STRING_SAMPLE,
    "credit_rating": SITE_DETAILS_LONG_STRING_SAMPLE,
    "rating_agency": SITE_DETAILS_LONG_STRING_SAMPLE,
    "date_of_rating": 22.5,
}
TEST_SITE_DETAILS_OFFTAKER_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR = (
    "Validation error: offtaker_name - String should have at most 100 characters; offtaker_type - Input should be "
    "'Community Solar', 'Individual' or 'Utility Provider'; credit_rating - String should have at most 100 "
    "characters; rating_agency - String should have at most 100 characters; date_of_rating - Datetimes provided to "
    "dates should have zero time - e.g. be exact dates"
)
TEST_SITE_DETAILS_OFFTAKER_SECTION_UPDATE_PAYLOAD_INVALID_DATES = {
    "date_of_rating": "0001-01-01",
}
TEST_SITE_DETAILS_OFFTAKER_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR_DATES = (
    "Validation error: date_of_rating - Value error, Year must be 1900 or greater"
)

TEST_SITE_DETAILS_COMPLIANCE_SECTION_UPDATE_PAYLOAD = {
    "entity": "Global Compliance Services",
    "bank": "Regulatory Bank Corp.",
    "report_due_date": "2024-08-15",
    "fiscal_year_end": "2024-12-31",
    "tax_return_deadline": "2025-04-30",
}

TEST_SITE_DETAILS_COMPLIANCE_SECTION_UPDATED = deepcopy(TEST_SITE_DETAILS_COMPLIANCE_SECTION)
TEST_SITE_DETAILS_COMPLIANCE_SECTION_UPDATED.update(TEST_SITE_DETAILS_COMPLIANCE_SECTION_UPDATE_PAYLOAD)
TEST_SITE_DETAILS_COMPLIANCE_SECTION_UPDATE_PAYLOAD_INVALID = {
    "entity": SITE_DETAILS_LONG_STRING_SAMPLE,
    "bank": SITE_DETAILS_LONG_STRING_SAMPLE,
    "report_due_date": SITE_DETAILS_LONG_STRING_SAMPLE,
    "fiscal_year_end": SITE_DETAILS_LONG_STRING_SAMPLE,
    "tax_return_deadline": SITE_DETAILS_LONG_STRING_SAMPLE,
}
TEST_SITE_DETAILS_COMPLIANCE_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR = (
    "Validation error: entity - String should have at most 100 characters; bank - String should have at most 100 "
    "characters; report_due_date - Input should be a valid date or datetime, invalid character in year; "
    "fiscal_year_end - Input should be a valid date or datetime, invalid character in year; tax_return_deadline - "
    "Input should be a valid date or datetime, invalid character in year"
)
TEST_SITE_DETAILS_COMPLIANCE_SECTION_UPDATE_PAYLOAD_INVALID_DATES = {
    "report_due_date": "0000-01-01",
    "fiscal_year_end": "0001-10-10",
    "tax_return_deadline": "1899-12-31",
}
TEST_SITE_DETAILS_COMPLIANCE_SECTION_UPDATE_PAYLOAD_VALIDATION_ERROR_DATES = (
    "Validation error: report_due_date - Value error, Year must be 1900 or greater; fiscal_year_end - Value error, "
    "Year must be 1900 or greater; tax_return_deadline - Value error, Year must be 1900 or greater"
)

SITE_DETAILS_UPDATE_INVALID_SECTION_NAME_ERROR = (
    "Invalid <section_name> value, must be one of: site_level_details, asset_overview, ownership, tax_equity, "
    "key_dates, o_and_m, interconnection, epc_contractor, community_solar_manager, insurance_provider, site_lease, "
    "vegetation_vendor, offtaker, compliance"
)

SITE_DASHBOARD_BIGQUERY_RESPONSE = [
    {
        "company_id": 8,
        "site_id": 268,
        "site_power_actual": [{"value": 10.341, "ts": datetime.datetime(2024, 12, 9, 13, 15)}],
        "site_power_expected": [{"value": 7.551, "ts": datetime.datetime(2024, 12, 9, 13, 15)}],
    }
]

SITE_ACTUAL_PRODUCTION_TODAY_BIGQUERY_RESPONSE = [
    {
        "site_power_actual": [
            {"value": 1, "ts": datetime.datetime(2024, 12, 9, 13, 15)},
            {"value": 3, "ts": datetime.datetime(2024, 12, 9, 13, 15)},
        ],
        "site_power_expected": [
            {"value": 6, "ts": datetime.datetime(2024, 12, 9, 13, 15)},
            {"value": 4, "ts": datetime.datetime(2024, 12, 9, 13, 15)},
        ],
    }
]

TELEMETRY_SITE_PAST_PERFORMANCE_RESPONSE = [
    {
        "site_id": 55,
        "site_energy_actual": [
            {"value": Decimal("4337.67825"), "ts": datetime.datetime(2024, 12, 12, 0, 0)},
            {"value": Decimal("6062.02405"), "ts": datetime.datetime(2024, 12, 13, 0, 0)},
            {"value": Decimal("6580.1817"), "ts": datetime.datetime(2024, 12, 14, 0, 0)},
            {"value": Decimal("6951.1047"), "ts": datetime.datetime(2024, 12, 15, 0, 0)},
            {"value": Decimal("2521.9281875"), "ts": datetime.datetime(2024, 12, 16, 0, 0)},
            {"value": Decimal("4228.549975"), "ts": datetime.datetime(2024, 12, 17, 0, 0)},
            {"value": Decimal("990.74685"), "ts": datetime.datetime(2024, 12, 18, 0, 0)},
        ],
        "site_energy_expected": [
            {"value": None, "ts": datetime.datetime(2024, 12, 12, 0, 0)},
            {"value": None, "ts": datetime.datetime(2024, 12, 13, 0, 0)},
            {"value": None, "ts": datetime.datetime(2024, 12, 14, 0, 0)},
            {"value": None, "ts": datetime.datetime(2024, 12, 15, 0, 0)},
            {"value": None, "ts": datetime.datetime(2024, 12, 16, 0, 0)},
            {"value": Decimal("5228.549975"), "ts": datetime.datetime(2024, 12, 17, 0, 0)},
            {"value": Decimal("1050"), "ts": datetime.datetime(2024, 12, 18, 0, 0)},
        ],
    }
]

SITE_PAST_PERFORMANCE_RESPONSE = {
    "2024-12-12T00:00:00": 0,
    "2024-12-13T00:00:00": 0,
    "2024-12-14T00:00:00": 0,
    "2024-12-15T00:00:00": 0,
    "2024-12-16T00:00:00": 0,
    "2024-12-17T00:00:00": 81,
    "2024-12-18T00:00:00": 94,
}

TELEMETRY_SITE_ACTUAL_VS_EXPECTED_IRRADIANCE_FOR_1_DAY = [
    {
        "site_id": 55,
        "site_power_actual": [
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 0, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 1, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 2, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 3, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 4, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 5, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 6, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 7, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 8, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 9, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 10, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 11, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 12, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 13, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 14, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 15, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 16, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 17, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 18, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 19, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 20, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 21, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 22, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 23, 0)},
        ],
        "site_power_expected": [
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 0, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 1, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 2, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 3, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 4, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 5, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 6, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 7, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 8, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 9, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 10, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 11, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 12, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 13, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 14, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 15, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 16, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 17, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 18, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 19, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 20, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 21, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 22, 0)},
            {"value": None, "ts": datetime.datetime(2025, 1, 12, 23, 0)},
        ],
        "site_irradiance": [
            {"value": Decimal("0"), "ts": datetime.datetime(2025, 1, 12, 0, 0)},
            {"value": Decimal("0"), "ts": datetime.datetime(2025, 1, 12, 1, 0)},
            {"value": Decimal("0"), "ts": datetime.datetime(2025, 1, 12, 2, 0)},
            {"value": Decimal("0"), "ts": datetime.datetime(2025, 1, 12, 3, 0)},
            {"value": Decimal("0"), "ts": datetime.datetime(2025, 1, 12, 4, 0)},
            {"value": Decimal("0"), "ts": datetime.datetime(2025, 1, 12, 5, 0)},
            {"value": Decimal("0"), "ts": datetime.datetime(2025, 1, 12, 6, 0)},
            {"value": Decimal("0"), "ts": datetime.datetime(2025, 1, 12, 7, 0)},
            {"value": Decimal("0"), "ts": datetime.datetime(2025, 1, 12, 8, 0)},
            {"value": Decimal("0"), "ts": datetime.datetime(2025, 1, 12, 9, 0)},
            {"value": Decimal("0"), "ts": datetime.datetime(2025, 1, 12, 10, 0)},
            {"value": Decimal("0"), "ts": datetime.datetime(2025, 1, 12, 11, 0)},
            {"value": Decimal("5.616666667"), "ts": datetime.datetime(2025, 1, 12, 12, 0)},
            {"value": Decimal("20.483333333"), "ts": datetime.datetime(2025, 1, 12, 13, 0)},
            {"value": Decimal("82.983333333"), "ts": datetime.datetime(2025, 1, 12, 14, 0)},
            {"value": Decimal("167.783333333"), "ts": datetime.datetime(2025, 1, 12, 15, 0)},
            {"value": Decimal("370.083333333"), "ts": datetime.datetime(2025, 1, 12, 16, 0)},
            {"value": Decimal("443.203389831"), "ts": datetime.datetime(2025, 1, 12, 17, 0)},
            {"value": Decimal("333.355932203"), "ts": datetime.datetime(2025, 1, 12, 18, 0)},
            {"value": Decimal("217.169491525"), "ts": datetime.datetime(2025, 1, 12, 19, 0)},
            {"value": Decimal("90.216666667"), "ts": datetime.datetime(2025, 1, 12, 20, 0)},
            {"value": Decimal("9.483333333"), "ts": datetime.datetime(2025, 1, 12, 21, 0)},
            {"value": Decimal("0"), "ts": datetime.datetime(2025, 1, 12, 22, 0)},
            {"value": Decimal("0"), "ts": datetime.datetime(2025, 1, 12, 23, 0)},
        ],
    }
]


SITE_ACTUAL_VS_EXPECTED_RESPONSE = [
    {"period": "2025-01-12T00:00:00", "actual": 0, "expected": 0, "irradiance": 0},
    {"period": "2025-01-12T01:00:00", "actual": 0, "expected": 0, "irradiance": 0},
    {"period": "2025-01-12T02:00:00", "actual": 0, "expected": 0, "irradiance": 0},
    {"period": "2025-01-12T03:00:00", "actual": 0, "expected": 0, "irradiance": 0},
    {"period": "2025-01-12T04:00:00", "actual": 0, "expected": 0, "irradiance": 0},
    {"period": "2025-01-12T05:00:00", "actual": 0, "expected": 0, "irradiance": 0},
    {"period": "2025-01-12T06:00:00", "actual": 0, "expected": 0, "irradiance": 0},
    {"period": "2025-01-12T07:00:00", "actual": 0, "expected": 0, "irradiance": 0},
    {"period": "2025-01-12T08:00:00", "actual": 0, "expected": 0, "irradiance": 0},
    {"period": "2025-01-12T09:00:00", "actual": 0, "expected": 0, "irradiance": 0},
    {"period": "2025-01-12T10:00:00", "actual": 0, "expected": 0, "irradiance": 0},
    {"period": "2025-01-12T11:00:00", "actual": 0, "expected": 0, "irradiance": 0},
    {"period": "2025-01-12T12:00:00", "actual": 0, "expected": 0, "irradiance": 5.616666667},
    {"period": "2025-01-12T13:00:00", "actual": 0, "expected": 0, "irradiance": 20.483333333},
    {"period": "2025-01-12T14:00:00", "actual": 0, "expected": 0, "irradiance": 82.983333333},
    {"period": "2025-01-12T15:00:00", "actual": 0, "expected": 0, "irradiance": 167.783333333},
    {"period": "2025-01-12T16:00:00", "actual": 0, "expected": 0, "irradiance": 370.083333333},
    {"period": "2025-01-12T17:00:00", "actual": 0, "expected": 0, "irradiance": 443.203389831},
    {"period": "2025-01-12T18:00:00", "actual": 0, "expected": 0, "irradiance": 333.355932203},
    {"period": "2025-01-12T19:00:00", "actual": 0, "expected": 0, "irradiance": 217.169491525},
    {"period": "2025-01-12T20:00:00", "actual": 0, "expected": 0, "irradiance": 90.216666667},
    {"period": "2025-01-12T21:00:00", "actual": 0, "expected": 0, "irradiance": 9.483333333},
    {"period": "2025-01-12T22:00:00", "actual": 0, "expected": 0, "irradiance": 0},
    {"period": "2025-01-12T23:00:00", "actual": 0, "expected": 0, "irradiance": 0},
]

TELEMETRY_SITE_CUMULATIVE_ENERGY_RESPONSE = [
    {
        "site_energy_actual_today": 120,
        "site_energy_expected_today": 140,
        "site_energy_actual_last_7_days": 1123,
        "site_energy_expected_last_7_days": 1137,
        "site_energy_actual_last_30_days": 6789,
        "site_energy_expected_last_30_days": 7000,
    }
]

SITE_TODAY_CUMULATIVE_BQ_RESPONSE = [
    {
        "company_energy_actual_today": 4,
        "company_energy_expected_today": 10,
    }
]

SITE_TODAY_CUMULATIVE_CACHED_RESPONSE = {
    "cumulative_actual_today": 10,
    "cumulative_expected_today": 11,
}
