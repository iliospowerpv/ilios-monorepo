from os import remove

import pytest

from app.helpers.configs.base_config_helper import BaseConfigHandler
from app.models.internal_configuration import InternalConfigurationNameEnum
from app.settings import settings


@pytest.fixture(scope="function")
def set_test_ai_parsing_config():
    prev_config_path = settings.ai_parsing_config_path

    settings.ai_parsing_config_path = "tests/unit/samples/test_ai_parsing_config.json"
    yield

    settings.ai_parsing_config_path = prev_config_path


@pytest.fixture(scope="function")
def unset_ai_parsing_config(db_session):
    filename = "unexisting.json"
    prev_config_path = settings.ai_parsing_config_path

    settings.ai_parsing_config_path = filename
    yield

    settings.ai_parsing_config_path = prev_config_path

    # In case if file was created, make sure it's deleted
    file_handler = BaseConfigHandler(filename, InternalConfigurationNameEnum.ai_parsing, db_session)
    try:
        remove(file_handler._gen_file_path())
    except FileNotFoundError:
        pass
