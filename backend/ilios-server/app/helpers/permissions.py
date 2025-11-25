"""Utilities to handle permissions structure"""

import json
import logging

from app.settings import settings

logger = logging.getLogger(__name__)


def get_default_permissions():
    """Retrieve permissions from the json template"""
    try:
        with open(settings.permissions_template_path, "r") as default_permissions_file:
            return json.load(default_permissions_file)
    except FileNotFoundError as exc:
        logger.error(f"Cannot read the file: {str(exc)}")
    except json.decoder.JSONDecodeError as exc:
        logger.error(f"Cannot decode the file: {str(exc)}")
