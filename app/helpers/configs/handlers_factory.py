from sqlalchemy.orm import Session

from ...models.internal_configuration import InternalConfigurationNameEnum
from .agreement_names_helper import AgreementNamesMappingHandler
from .ai_parsing_helper import AIParsingHandler
from .co_terminus_helper import CoTerminusHandler


class ConfigHandlerFactory:

    @staticmethod
    def get_instance(config_type: InternalConfigurationNameEnum, db_session: Session):
        available_instances = {
            InternalConfigurationNameEnum.ai_parsing: AIParsingHandler,
            InternalConfigurationNameEnum.agreement_names: AgreementNamesMappingHandler,
            InternalConfigurationNameEnum.co_terminus: CoTerminusHandler,
        }
        instance = available_instances.get(config_type)
        return instance(db_session)
