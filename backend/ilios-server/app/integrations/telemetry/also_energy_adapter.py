"""Also Energy adapter — credentials are username + password, sent as basic auth."""
from __future__ import annotations

import base64

from .cloud_function_adapter import CloudFunctionAdapter


class AlsoEnergyAdapter(CloudFunctionAdapter):
    provider_key = "also_energy"
    required_credential_fields = ("username", "password")

    def encode_credentials(self, credentials: dict[str, str]) -> dict[str, str]:
        username = credentials.get("username", "")
        password = credentials.get("password", "")
        token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
        return {"auth_scheme": "basic", "token": token}
