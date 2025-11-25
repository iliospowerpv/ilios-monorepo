from copy import deepcopy

from app.models.telemetry import DASProvidersEnum

TEST_KMC_DAS_CONNECTION_PAYLOAD = {
    "name": "KMC Connection",
    "provider": DASProvidersEnum.kmc.value,
    "token": "12345AAS212",
}
TEST_AE_DAS_CONNECTION_PAYLOAD = {
    "name": "Also Energy Connection",
    "provider": DASProvidersEnum.also_energy.value,
    "username": "12345AAS212",
    "password": "12345AAS212",
}

DAS_CONNECTION_NAME_TO_SMALL_ERR = "Validation error: body.name - String should have at least 2 characters"
DAS_CONNECTION_NAME_TO_BIG_ERR = "Validation error: body.name - String should have at most 100 characters"

TEST_KMC_DAS_CONNECTION_PAYLOAD_MISSING_TOKEN_FIELD = {
    "name": "Test",
    "provider": DASProvidersEnum.kmc.value,
}
TEST_KMC_DAS_CONNECTION_PAYLOAD_EMPTY_TOKEN_FIELD = deepcopy(TEST_KMC_DAS_CONNECTION_PAYLOAD_MISSING_TOKEN_FIELD)
TEST_KMC_DAS_CONNECTION_PAYLOAD_EMPTY_TOKEN_FIELD["token"] = None

TEST_KMC_DAS_CONNECTION_PAYLOAD_EMPTY_STRING_TOKEN_FIELD = deepcopy(TEST_KMC_DAS_CONNECTION_PAYLOAD_MISSING_TOKEN_FIELD)
TEST_KMC_DAS_CONNECTION_PAYLOAD_EMPTY_STRING_TOKEN_FIELD["token"] = ""

TEST_AE_DAS_CONNECTION_PAYLOAD_MISSING_CREDS_FIELDS = deepcopy(TEST_KMC_DAS_CONNECTION_PAYLOAD_MISSING_TOKEN_FIELD)
TEST_AE_DAS_CONNECTION_PAYLOAD_MISSING_CREDS_FIELDS["provider"] = DASProvidersEnum.also_energy.value

TEST_AE_DAS_CONNECTION_PAYLOAD_MISSING_USERNAME_FIELD = deepcopy(TEST_AE_DAS_CONNECTION_PAYLOAD_MISSING_CREDS_FIELDS)
TEST_AE_DAS_CONNECTION_PAYLOAD_MISSING_USERNAME_FIELD["password"] = "test"

TEST_AE_DAS_CONNECTION_PAYLOAD_MISSING_PASSWORD_FIELD = deepcopy(TEST_AE_DAS_CONNECTION_PAYLOAD_MISSING_CREDS_FIELDS)
TEST_AE_DAS_CONNECTION_PAYLOAD_MISSING_PASSWORD_FIELD["username"] = "test"

TEST_KMC_DAS_CONNECTION_PAYLOAD_MISSING_TOKEN_ERR = (
    "Validation error: body - Value error, The field <token> is required for the KMC provider"
)

TEST_AE_DAS_CONNECTION_PAYLOAD_MISSING_CREDS_ERR = (
    "Validation error: body - Value error, The fields <username> and <password> are required "
    "for the Also Energy provider"
)

EXPECTED_CUMULATIVE_PRODUCTION_SECTION_DETAILS = {
    "cumulative_actual_kw": 4.0,
    "cumulative_actual_vs_expected": 40.0,
    "cumulative_expected_kw": 10.0,
    "cumulative_performance_index": 0.4,
}

EXPECTED_CUMULATIVE_PRODUCTION_SECTION_CACHED_DETAILS = {
    "cumulative_actual_kw": 10.0,
    "cumulative_actual_vs_expected": 91.0,
    "cumulative_expected_kw": 11.0,
    "cumulative_performance_index": 0.91,
}

TEST_BQ_ACTUAL_KW = 10.34
TEST_BQ_EXPECTED_KW = 7.55
TEST_ACTUAL_VS_EXPECTED = 137
TEST_PERFORMANCE_INDEX = 1.37
