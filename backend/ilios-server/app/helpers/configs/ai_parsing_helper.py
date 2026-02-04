import logging

from app.helpers.configs.base_config_helper import BaseConfigHandler
from app.models.internal_configuration import InternalConfigurationNameEnum
from app.settings import settings

logger = logging.getLogger(__name__)


class AIParsingHandler(BaseConfigHandler):
    """Class to utilize parsing config with registry fallback"""

    def __init__(self, db_session):
        super().__init__(
            filename=settings.ai_parsing_config_path,
            config_name=InternalConfigurationNameEnum.ai_parsing,
            db_session=db_session,
        )
        self._db_session = db_session

    def get_parsable_documents_list(self):
        """Get name of the agreements/documents, supported by AI to be parsed.
        
        Registry is authoritative. Fallback to config only if ALLOW_CONFIG_FALLBACK=True.
        """
        from app.services.extraction_pipeline_service import ExtractionPipelineService
        try:
            service = ExtractionPipelineService(self._db_session)
            registry_types = service.get_parsable_document_types()
            if registry_types:
                return registry_types
        except Exception as e:
            logger.warning(f"Registry lookup failed: {e}")
            if not settings.allow_config_fallback:
                return []

        if settings.allow_config_fallback:
            logger.info("Config fallback enabled, using ai_parsing_config.json")
            config = self.read()
            return list(config.keys()) if config else []
        return []

    def get_keys_by_document_type(self, document_type: str):
        """Return list of keys available for the specific document type.
        
        Registry is authoritative. Fallback to config only if ALLOW_CONFIG_FALLBACK=True.
        """
        from app.services.extraction_pipeline_service import ExtractionPipelineService
        try:
            service = ExtractionPipelineService(self._db_session)
            config = service.get_extraction_config(document_type)
            if config and config.get("fields"):
                return [f["display_name"] for f in config["fields"]]
        except Exception as e:
            logger.warning(f"Registry lookup failed: {e}")
            if not settings.allow_config_fallback:
                return []

        if settings.allow_config_fallback:
            logger.info("Config fallback enabled, using ai_parsing_config.json")
            config = self.read()
            return config.get(document_type, []) if config else []
        return []

    def get_extraction_config(self, document_type: str):
        """Get full extraction configuration from registry.
        
        Returns None if document type not found in registry.
        """
        from app.services.extraction_pipeline_service import ExtractionPipelineService
        try:
            service = ExtractionPipelineService(self._db_session)
            return service.get_extraction_config(document_type)
        except Exception as e:
            logger.warning(f"Failed to get extraction config from registry: {e}")
            return None
