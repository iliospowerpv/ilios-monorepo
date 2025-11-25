import logging

from app.helpers.configs.base_config_helper import BaseConfigHandler
from app.models.internal_configuration import InternalConfigurationNameEnum
from app.settings import settings

logger = logging.getLogger(__name__)


class AIParsingHandler(BaseConfigHandler):
    """Class to utilize parsing config"""

    def __init__(self, db_session):
        super().__init__(
            filename=settings.ai_parsing_config_path,
            config_name=InternalConfigurationNameEnum.ai_parsing,
            db_session=db_session,
        )

    def get_parsable_documents_list(self):
        """Get name of the agreements/documents, supported by AI to be parsed"""
        config = self.read()
        return list(config.keys()) if config else []

    def get_keys_by_document_type(self, document_type: str):
        """Return list of keys available for the specific document type"""
        config = self.read()
        return config.get(document_type, []) if config else []
