from app.models.internal_configuration import InternalConfigurationNameEnum
from tests.unit.samples import enum_to_message

CONFIG_MISSING_QUERY_ERR = "Validation error: query.config_type - Field required"
CONFIG_MISSING_QUERY_AND_BODY_ERR = "Validation error: query.config_type - Field required; body - Field required"
CONFIG_INVALID_QUERY_GET_ERR = (
    f"Validation error: query.config_type - Input should be {enum_to_message(InternalConfigurationNameEnum)}"
)
CONFIG_INVALID_QUERY_PUT_ERR = f"Validation error: query.config_type - Input should be {enum_to_message(InternalConfigurationNameEnum)}; body - Field required"
