"""KMC adapter — single API token credential."""
from __future__ import annotations

from .cloud_function_adapter import CloudFunctionAdapter


class KmcAdapter(CloudFunctionAdapter):
    provider_key = "kmc"
    required_credential_fields = ("token",)

    def encode_credentials(self, credentials: dict[str, str]) -> dict[str, str]:
        return {"auth_scheme": "bearer", "token": credentials.get("token", "")}
