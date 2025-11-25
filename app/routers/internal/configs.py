"""Read/write config json files by the config type"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.helpers.authentication import api_key_check
from app.helpers.configs.handlers_factory import ConfigHandlerFactory
from app.models.internal_configuration import InternalConfigurationNameEnum
from app.static.responses import HTTP_404_RESPONSE

logger = logging.getLogger(__name__)
internal_configs_router = APIRouter()


@internal_configs_router.get(
    "/configs",
    dependencies=[Depends(api_key_check)],
    status_code=status.HTTP_200_OK,
    responses={**HTTP_404_RESPONSE},
    description=f"""Get config file content by its type: {InternalConfigurationNameEnum.string_values()}.
    \nIf it returns 'null' - where is no config by the specified type.
    \nMore details: [README.md](https://github.com/GH-50513/ilios-server/tree/develop/configs#the-configs-folder)""",
)
async def retrieve_config(config_type: InternalConfigurationNameEnum, db_session: Session = Depends(get_session)):
    config_handler = ConfigHandlerFactory.get_instance(config_type, db_session)
    return config_handler.read()


@internal_configs_router.put(
    "/configs",
    dependencies=[Depends(api_key_check)],
    status_code=status.HTTP_200_OK,
    responses={**HTTP_404_RESPONSE},
    description=f"""Save config into DB by its name: {InternalConfigurationNameEnum.string_values()}.
    \nExpect json-like formatting as an input.
    \nMore details: [README.md](https://github.com/GH-50513/ilios-server/tree/develop/configs#the-configs-folder)""",
)
async def overwrite_config(
    config_type: InternalConfigurationNameEnum, payload: Dict[str, Any], db_session: Session = Depends(get_session)
):
    config_handler = ConfigHandlerFactory.get_instance(config_type, db_session)
    config_handler.store(payload)
    return {"code": status.HTTP_200_OK, "message": f"Updated the '{config_type.value}' config"}
