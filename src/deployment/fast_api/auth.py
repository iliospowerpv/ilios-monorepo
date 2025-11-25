from fastapi import HTTPException

from src.deployment.fast_api.settings import settings


def api_key_check(api_key: str) -> str:
    """Raises 403 Forbidden if provided api key param doesn't match api key configured
    in the app settings"""
    if api_key != settings.api_key:
        raise HTTPException(403)
    return api_key
