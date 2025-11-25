import copy

from app.static.companies import CompanyTypes

PHONE_PATTERN_MISMATCH_ERR = "Validation error: body.phone - String should match pattern '^[0-9]+$'"

PHONE_NUMBER_TOO_LONG_ERR = "Validation error: body.phone - String should have at most 10 characters"

PHONE_NUMBER_TOO_SHORT_ERR = "Validation error: body.phone - String should have at least 10 characters"

NAME_TOO_SHORT_ERR = "Validation error: body.name - String should have at least 2 characters"

NAME_TOO_LONG_ERR = "Validation error: body.name - String should have at most 100 characters"

ADDRESS_TOO_LONG_ERR = "Validation error: body.address - String should have at most 255 characters"

COMPANY_UNIQUE_NAME_CONSTRAINT_ERR = "This name already exists. Please try another name"

COMPANY_NAME_101_SYMBOL = (
    "This is company name with 101 symbols ------------------------------------------------------------- ."
)

COMPANY_ADDRESS_256_SYMBOLS = (
    "This is company address with 256 symbols -------------------------------------------------------------------------"
    "------------------------------------------------------------------------------------------------------------------"
    "-------------------------  ."
)

VALID_COMPANY1_BODY = {
    "name": "Nvidia Corporation",
    "email": "info@nvidia.com",
    "phone": "0123456789",
    "address": "2788 San Tomas Expressway, Santa Clara, CA",
    "company_type": CompanyTypes.operation_maintenance_contractor,
}

TEST_COMPANY_NAME2 = "Apple Inc."
VALID_COMPANY2_BODY = {
    "name": TEST_COMPANY_NAME2,
    "email": "tcook@icloud.com",
    "phone": "0123456789",
    "address": "One Apple Park Way, Cupertino, CA 95014",
    "company_type": CompanyTypes.operation_maintenance_contractor,
}

VALID_CONTRACTOR_BODY = {
    "name": "Softserve inc.",
    "email": "info@softserveinc.com",
    "phone": "0123456789",
    "address": "201 W 5th Street, Suite 1550, Austin, TX 78701",
    "company_type": "O&M Contractor",
}

TEST_COMPANY_NAME = "Green Lantern"
TEST_COMPANY_EMAIL = "sales@greenlantern.com"
TEST_COMPANY_PHONE = "1180982187"
TEST_COMPANY_ADDRESS = "719 Main Street Solar"
TEST_COMPANY_TYPE = CompanyTypes.project_site_owner
TEST_COMPANY_TYPE2 = CompanyTypes.operation_maintenance_contractor

TEST_COMPANY_PAYLOAD = {
    "name": TEST_COMPANY_NAME,
    "email": TEST_COMPANY_EMAIL,
    "phone": TEST_COMPANY_PHONE,
    "address": TEST_COMPANY_ADDRESS,
    "company_type": TEST_COMPANY_TYPE,
}
# copy payload to make company type enums JSON serializable
TEST_COMPANY_PAYLOAD_JSON = copy.deepcopy(TEST_COMPANY_PAYLOAD)
TEST_COMPANY_PAYLOAD_JSON["company_type"] = TEST_COMPANY_TYPE.value

SETUP_COMPANIES = [TEST_COMPANY_PAYLOAD, VALID_COMPANY1_BODY, VALID_COMPANY2_BODY]


COMPANY_LOSSES_FOR_A_DAY_BQ_RESPONSE_EXPECTED_BIGGER_THAN_ACTUAL = [
    {
        "company_energy_actual_today": 120,
        "company_energy_expected_today": 140,
    }
]
COMPANY_LOSSES_FOR_A_DAY_BQ_RESPONSE_EXPECTED_SMALLER_THAN_ACTUAL = [
    {
        "company_energy_actual_today": 120,
        "company_energy_expected_today": 100,
    }
]

COMPANY_LOSSES_FOR_A_DAY_BQ_RESPONSE_EXPECTED_EQUAL_ACTUAL = [
    {
        "company_energy_actual_today": 100,
        "company_energy_expected_today": 100,
    }
]
COMPANY_LOSSES_FOR_A_DAY_CHART_RESPONSE_WITH_LOSES = {"cumulative": 120.0, "expected": 140.0, "loss": 20.0}
COMPANY_LOSSES_FOR_A_DAY_CHART_RESPONSE_NO_LOSES = {"cumulative": 120.0, "expected": 100.0, "loss": 0}
COMPANY_LOSSES_FOR_A_DAY_CHART_RESPONSE_NO_LOSES_EQUAL = {"cumulative": 100.0, "expected": 100.0, "loss": 0}
