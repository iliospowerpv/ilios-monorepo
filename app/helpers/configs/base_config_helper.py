import json
import logging
from os import path

from app.crud.internal_configuration import InternalConfigurationCRUD

logger = logging.getLogger(__name__)


class BaseConfigHandler:
    """Class to read/write JSON file by specific path"""

    def __init__(self, filename, config_name, db_session):
        self.filename = filename
        self.config_name = config_name
        self.config_crud = InternalConfigurationCRUD(db_session)

    def _gen_file_path(self):
        """Get absolute path of file, starting of the project root directory"""
        return path.join(path.dirname(path.abspath(__file__)), "../../../", self.filename)

    def _read_from_file(self):
        """Retrieve payload of the file"""
        file_path = self._gen_file_path()
        try:
            with open(file_path, "r") as f:
                file_content = json.load(f)
            return file_content
        except FileNotFoundError:
            logger.warning(f"There is no config stored at path {file_path}")

    def _read_from_db(self):
        config = self.config_crud.get_by_name(self.config_name.value)
        if config:
            return config.payload
        logger.debug(f"There is no DB config stored for the config name {self.config_name.value}")

    def read(self):
        """Try to read config either from the DB or from the file"""
        config = self._read_from_db()
        if config:
            return config
        return self._read_from_file()

    def store(self, payload):
        """Save config into DB"""
        existing_config = self.config_crud.get_by_name(self.config_name.value)
        update_payload = {"payload": payload}
        if not existing_config:
            update_payload["name"] = self.config_name
            self.config_crud.create_item(update_payload)
            logger.debug(f"Created the config: {self.config_name.value}")
            return
        self.config_crud.update_by_id(existing_config.id, update_payload)
        logger.debug(f"Updated the config: {self.config_name.value}")
