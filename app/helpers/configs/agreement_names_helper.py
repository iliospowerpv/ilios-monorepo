import logging

from app.helpers.configs.base_config_helper import BaseConfigHandler
from app.models.internal_configuration import InternalConfigurationNameEnum
from app.settings import settings
from app.static.default_site_documents_enum import SiteDocumentsEnum

logger = logging.getLogger(__name__)


class AgreementNamesMappingHandler(BaseConfigHandler):
    """Class to utilize agreement names mapping config"""

    def __init__(self, db_session):
        super().__init__(
            filename=settings.agreement_names_mapping_config_path,
            config_name=InternalConfigurationNameEnum.agreement_names,
            db_session=db_session,
        )

    def get_pipeline_agreement_name(self, platform_document_name: SiteDocumentsEnum):
        """Get pipeline agreement name from the config file"""
        config = self.read()
        return config.get(platform_document_name.value) if config else None
