import logging

from app.helpers.configs.base_config_helper import BaseConfigHandler
from app.models.internal_configuration import InternalConfigurationNameEnum
from app.settings import settings
from app.static.co_terminus_checks import CoTerminusComparisonStatuses

logger = logging.getLogger(__name__)


class CoTerminusHandler(BaseConfigHandler):
    """Class to utilize co-terminus config"""

    def __init__(self, db_session):
        super().__init__(
            filename=settings.co_terminus_config_path,
            config_name=InternalConfigurationNameEnum.co_terminus,
            db_session=db_session,
        )

    @staticmethod
    def define_comparison_status(values):
        """If at least one of the values is none - return N/A status.
        Otherwise, lowercase items and check if they are consistent"""
        # Set status as N/A if:
        # 1. Value is None
        # 2. Value is an empty string
        # 2. Value is a string populated with spaces only
        if any((value is None or (isinstance(value, str) and value.isspace()) or value == "") for value in values):
            return CoTerminusComparisonStatuses.na.value
        values = [str(value).lower() for value in values]
        if all(value == values[0] for value in values):
            return CoTerminusComparisonStatuses.equal.value
        return CoTerminusComparisonStatuses.pending.value

    def filter_against_config(self, data):
        """Filter out co-terminus results according to the latest config"""
        config = self.read()
        filtered_data = []

        for item in data:
            key_name = item["name"]
            # check if key is in config, otherwise ignore it
            if key_name not in config:
                continue
            # get list of key sources from the current config
            key_sources = {source: value for source, value in item["sources"].items() if source in config[key_name]}
            # check if key sources exists, otherwise ignore the full key
            if not key_sources:
                continue

            filtered_data.append({"name": key_name, "sources": key_sources, "status": item["status"]})

        return filtered_data
