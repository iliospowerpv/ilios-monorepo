import re
from typing import Self

from flask import Request
from pydantic import BaseModel, ConfigDict, Field, model_validator
from pydantic_core import PydanticCustomError

from . import secret_manager
from .constants import SECRET_ID_PATTERN
from .enums import DataProvider, PlatformEnvironment


class BaseParams(BaseModel):
    model_config = ConfigDict(frozen=True)


class BaseRequestParams(BaseParams):

    @classmethod
    def from_request(cls, request: Request) -> Self:
        return cls.model_validate_json(request.data)


class BaseDataProviderRequestParams(BaseRequestParams):
    data_provider: DataProvider


class BaseDataProviderTokenRequestParams(BaseDataProviderRequestParams):
    token: str


class BaseDataProviderTokenSecretIdRequestParams(BaseDataProviderRequestParams):
    token_secret_id: str = Field(pattern=SECRET_ID_PATTERN)

    _token: str

    @model_validator(mode="after")
    def access_token_secret(self) -> Self:
        match: re.Match = re.match(SECRET_ID_PATTERN, self.token_secret_id)

        try:
            self._token = secret_manager.access_secret(**match.groupdict())
        except Exception as error:
            raise PydanticCustomError(
                "access_token_secret_error",
                "Failed to access token secret: {error}",
                {"error": repr(error)},
            )

        return self

    @property
    def token(self) -> str:
        return self._token


class VerifyTokenServiceRequestParams(BaseDataProviderTokenRequestParams):
    pass


class RetrieveSitesServiceRequestParams(BaseDataProviderTokenSecretIdRequestParams):
    pass


class RetrieveDevicesServiceRequestParams(BaseDataProviderTokenSecretIdRequestParams):
    site_id: str


class RetrieveDeviceInfoServiceRequestParams(BaseDataProviderTokenSecretIdRequestParams):
    site_id: str
    device_id: str


class PlatformParams(BaseParams):
    environment: PlatformEnvironment
    company_id: int
    site_id: int
    device_id: int


class FetchTelemetryDataJobRequestParams(BaseDataProviderTokenSecretIdRequestParams):
    site_id: str
    device_id: str
    platform: PlatformParams
