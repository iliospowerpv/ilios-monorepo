"""Unit tests for adapter HTTP error → structured exception mapping.

No real network calls. We inject a fake HTTP client that raises exceptions
shaped like the legacy CloudFunctionTelemetryClient errors.
"""
from types import SimpleNamespace

import pytest

from app.integrations.telemetry.also_energy_adapter import AlsoEnergyAdapter
from app.integrations.telemetry.base import (
    CredentialError,
    NoData,
    ProviderUnavailable,
    RateLimited,
)
from app.integrations.telemetry.cloud_function_adapter import CloudFunctionAdapter


class FakeClient:
    """Test double that raises a single exception on .invoke()."""

    def __init__(self, exc):
        self._exc = exc

    def invoke(self, payload):  # noqa: ARG002
        raise self._exc


def _http_error(status_code: int, body: str = "", headers: dict | None = None):
    response = SimpleNamespace(status_code=status_code, text=body, headers=headers or {})
    err = RuntimeError(f"HTTP {status_code}")
    err.status_code = status_code
    err.response = response
    return err


def _make_adapter(http_error):
    return AlsoEnergyAdapter(http_client=FakeClient(http_error))


class TestAdapterErrorMapping:
    def test_401_maps_to_credential_error(self):
        adapter = _make_adapter(_http_error(401, body="Unauthorized"))
        with pytest.raises(CredentialError) as exc_info:
            adapter.list_sites({"token": "x"})
        assert exc_info.value.provider_key == "also_energy"

    def test_403_maps_to_credential_error(self):
        adapter = _make_adapter(_http_error(403, body="Forbidden"))
        with pytest.raises(CredentialError):
            adapter.list_sites({"token": "x"})

    def test_404_with_BinData_maps_to_no_data(self):
        adapter = _make_adapter(
            _http_error(404, body='{"error":"BinData not found"}')
        )
        with pytest.raises(NoData):
            adapter.list_sites({"token": "x"})

    def test_404_without_BinData_maps_to_provider_unavailable(self):
        adapter = _make_adapter(_http_error(404, body="not found"))
        with pytest.raises(ProviderUnavailable):
            adapter.list_sites({"token": "x"})

    def test_429_maps_to_rate_limited_with_retry_after(self):
        adapter = _make_adapter(
            _http_error(429, body="too many", headers={"Retry-After": "30"})
        )
        with pytest.raises(RateLimited) as exc_info:
            adapter.list_sites({"token": "x"})
        assert exc_info.value.retry_after == 30

    def test_5xx_maps_to_provider_unavailable(self):
        adapter = _make_adapter(_http_error(503, body="upstream"))
        with pytest.raises(ProviderUnavailable):
            adapter.list_sites({"token": "x"})

    def test_unknown_status_maps_to_provider_unavailable(self):
        adapter = _make_adapter(_http_error(0))  # no status_code path
        with pytest.raises(ProviderUnavailable):
            adapter.list_sites({"token": "x"})


class TestRequiredCredentialFields:
    def test_missing_field_raises_credential_error(self):
        adapter = _make_adapter(_http_error(200))  # never reached
        with pytest.raises(CredentialError) as exc_info:
            adapter.list_sites({})  # token missing
        assert "token" in str(exc_info.value).lower() or exc_info.value.provider_key


class TestTestCredentialsConvertsExceptionsToTestResult:
    def test_credential_error_returns_failure(self):
        adapter = _make_adapter(_http_error(401))
        result = adapter.test_credentials({"token": "x"})
        assert result.success is False
        assert "credential" in result.message.lower() or "rejected" in result.message.lower()

    def test_provider_unavailable_returns_failure(self):
        adapter = _make_adapter(_http_error(503))
        result = adapter.test_credentials({"token": "x"})
        assert result.success is False

    def test_success_returns_site_count(self):
        class OkClient:
            def invoke(self, payload):  # noqa: ARG002
                return {"sites": [{"id": "s1"}, {"id": "s2"}]}

        adapter = AlsoEnergyAdapter(http_client=OkClient())
        result = adapter.test_credentials({"token": "x"})
        assert result.success is True
        assert result.available_sites_count == 2


class TestPayloadRedactionInLogs:
    def test_invoke_redacts_credentials_in_log(self, caplog):
        adapter = _make_adapter(_http_error(503))
        with caplog.at_level("INFO"):
            with pytest.raises(ProviderUnavailable):
                adapter.list_sites({"token": "supersecret_value_1234"})
        joined = " ".join(rec.getMessage() for rec in caplog.records)
        assert "supersecret_value_1234" not in joined


class TestBaseClassNotInstantiableWithoutKey:
    def test_base_adapter_has_empty_provider_key(self):
        # CloudFunctionAdapter is the base; concrete subclasses set provider_key.
        assert CloudFunctionAdapter.provider_key == ""
        assert AlsoEnergyAdapter.provider_key == "also_energy"
