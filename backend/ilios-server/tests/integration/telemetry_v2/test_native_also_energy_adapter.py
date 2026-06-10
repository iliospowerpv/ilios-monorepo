"""Unit tests for ``NativeAlsoEnergyAdapter``.

These tests inject a fake HTTP session — no real network calls. They cover
- happy-path token + sites parsing,
- HTTP 400 → ``CredentialError`` (and ``test_credentials`` returns rejected),
- 401/403 → ``CredentialError``,
- 5xx → ``ProviderUnavailable``,
- 429 → ``RateLimited`` with ``retry_after`` parsed,
- transport ``RequestException`` → ``ProviderUnavailable`` after retries,
- credential and token values are never present in log output.
"""
from __future__ import annotations

from http import HTTPStatus
from typing import Any

import pytest
import requests

from app.integrations.telemetry.base import (
    CredentialError,
    DeviceListingAdapter,
    MappingError,
    ProviderUnavailable,
    RateLimited,
)
from app.integrations.telemetry.native_also_energy_adapter import (
    NativeAlsoEnergyAdapter,
)


class _FakeResponse:
    def __init__(
        self,
        status_code: int,
        json_body: Any | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self._json = json_body
        self.headers = headers or {}

    def json(self) -> Any:
        if isinstance(self._json, Exception):
            raise self._json
        return self._json


class _FakeSession:
    """Records calls and replays a queue of responses or raises."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def _next(self):
        if not self._responses:
            raise AssertionError("No more fake responses queued")
        r = self._responses.pop(0)
        if isinstance(r, Exception):
            raise r
        return r

    def post(self, url, data=None, timeout=None):
        self.calls.append(("POST", url, data, timeout))
        return self._next()

    def get(self, url, headers=None, timeout=None):
        self.calls.append(("GET", url, headers, timeout))
        return self._next()


def _make(responses) -> NativeAlsoEnergyAdapter:
    return NativeAlsoEnergyAdapter(
        http_session=_FakeSession(responses),
        max_retries=0,
        timeout_seconds=1,
    )


# ---------------------------------------------------------------------------
# test_credentials
# ---------------------------------------------------------------------------


def test_test_credentials_rejected_on_http_400():
    adapter = _make([_FakeResponse(HTTPStatus.BAD_REQUEST, json_body={})])
    result = adapter.test_credentials({"username": "u", "password": "p"})
    assert result.success is False
    assert "rejected" in result.message.lower() or "credential" in result.message.lower()


def test_test_credentials_verified_on_http_200_with_token():
    adapter = _make(
        [_FakeResponse(HTTPStatus.OK, json_body={"access_token": "tok-secret-xyz"})]
    )
    result = adapter.test_credentials({"username": "u", "password": "p"})
    assert result.success is True
    assert result.available_sites_count is None


def test_test_credentials_unavailable_on_5xx():
    adapter = _make([_FakeResponse(HTTPStatus.SERVICE_UNAVAILABLE)])
    result = adapter.test_credentials({"username": "u", "password": "p"})
    assert result.success is False
    assert "unavailable" in result.message.lower() or "503" in result.message


def test_test_credentials_rate_limited_with_retry_after():
    adapter = _make(
        [_FakeResponse(HTTPStatus.TOO_MANY_REQUESTS, headers={"Retry-After": "30"})]
    )
    result = adapter.test_credentials({"username": "u", "password": "p"})
    assert result.success is False
    assert "rate" in result.message.lower()


def test_test_credentials_missing_field():
    adapter = _make([])  # never reached
    result = adapter.test_credentials({"username": "u"})
    assert result.success is False
    assert "missing" in result.message.lower() or "credential" in result.message.lower()


def test_test_credentials_empty_credentials():
    adapter = _make([])
    result = adapter.test_credentials({})
    assert result.success is False
    assert "credential" in result.message.lower()


def test_test_credentials_unparseable_response_is_unavailable():
    adapter = _make(
        [_FakeResponse(HTTPStatus.OK, json_body=ValueError("not json"))]
    )
    result = adapter.test_credentials({"username": "u", "password": "p"})
    assert result.success is False
    assert "unparseable" in result.message.lower() or "missing" in result.message.lower()


def test_test_credentials_response_missing_access_token():
    adapter = _make([_FakeResponse(HTTPStatus.OK, json_body={"foo": "bar"})])
    result = adapter.test_credentials({"username": "u", "password": "p"})
    assert result.success is False
    assert "access_token" in result.message.lower() or "missing" in result.message.lower()


def test_test_credentials_request_exception_after_retries():
    adapter = NativeAlsoEnergyAdapter(
        http_session=_FakeSession([requests.ConnectionError("dns down")]),
        max_retries=0,
        timeout_seconds=1,
    )
    result = adapter.test_credentials({"username": "u", "password": "p"})
    assert result.success is False


# ---------------------------------------------------------------------------
# list_sites
# ---------------------------------------------------------------------------


def test_list_sites_happy_path():
    adapter = _make(
        [
            _FakeResponse(HTTPStatus.OK, json_body={"access_token": "tok"}),
            _FakeResponse(
                HTTPStatus.OK,
                json_body={
                    "items": [
                        {"siteId": 101, "siteName": "Alpha", "extra": "x"},
                        {"siteId": 202, "siteName": "Beta"},
                    ]
                },
            ),
        ]
    )
    sites = adapter.list_sites({"username": "u", "password": "p"})
    assert [s.external_site_id for s in sites] == ["101", "202"]
    assert [s.external_site_name for s in sites] == ["Alpha", "Beta"]
    assert sites[0].raw_metadata == {"extra": "x"}


def test_list_sites_no_content_returns_empty():
    adapter = _make(
        [
            _FakeResponse(HTTPStatus.OK, json_body={"access_token": "tok"}),
            _FakeResponse(HTTPStatus.NO_CONTENT, json_body=None),
        ]
    )
    sites = adapter.list_sites({"username": "u", "password": "p"})
    assert sites == ()


def test_list_sites_credential_error_propagates():
    adapter = _make([_FakeResponse(HTTPStatus.BAD_REQUEST, json_body={})])
    with pytest.raises(CredentialError):
        adapter.list_sites({"username": "u", "password": "p"})


def test_list_sites_5xx_after_token_is_unavailable():
    adapter = _make(
        [
            _FakeResponse(HTTPStatus.OK, json_body={"access_token": "tok"}),
            _FakeResponse(HTTPStatus.BAD_GATEWAY, json_body=None),
        ]
    )
    with pytest.raises(ProviderUnavailable):
        adapter.list_sites({"username": "u", "password": "p"})


@pytest.mark.parametrize(
    "status",
    [HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN, HTTPStatus.BAD_REQUEST],
)
def test_list_sites_4xx_after_token_is_credential_error(status):
    adapter = _make(
        [
            _FakeResponse(HTTPStatus.OK, json_body={"access_token": "tok"}),
            _FakeResponse(status, json_body=None),
        ]
    )
    with pytest.raises(CredentialError):
        adapter.list_sites({"username": "u", "password": "p"})


def test_list_sites_429_after_token_is_rate_limited():
    adapter = _make(
        [
            _FakeResponse(HTTPStatus.OK, json_body={"access_token": "tok"}),
            _FakeResponse(
                HTTPStatus.TOO_MANY_REQUESTS,
                json_body=None,
                headers={"Retry-After": "12"},
            ),
        ]
    )
    with pytest.raises(RateLimited) as ei:
        adapter.list_sites({"username": "u", "password": "p"})
    assert ei.value.retry_after == 12


@pytest.mark.parametrize(
    "status",
    [HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN],
)
def test_test_credentials_rejected_on_401_403(status):
    adapter = _make([_FakeResponse(status, json_body={})])
    result = adapter.test_credentials({"username": "u", "password": "p"})
    assert result.success is False
    assert "rejected" in result.message.lower()


# ---------------------------------------------------------------------------
# list_devices
# ---------------------------------------------------------------------------


def test_list_devices_happy_path():
    adapter = _make(
        [
            _FakeResponse(HTTPStatus.OK, json_body={"access_token": "tok"}),
            _FakeResponse(
                HTTPStatus.OK,
                json_body={
                    "hardware": [
                        {"id": 11, "name": "Inverter A", "extra": "x"},
                        {"id": 22, "name": "Meter B"},
                    ]
                },
            ),
        ]
    )
    devices = adapter.list_devices({"username": "u", "password": "p"}, "4")
    assert [d.external_device_id for d in devices] == ["11", "22"]
    assert [d.external_device_name for d in devices] == ["Inverter A", "Meter B"]
    assert devices[0].raw_metadata == {"extra": "x"}


def test_list_devices_hits_site_scoped_hardware_path():
    session = _FakeSession(
        [
            _FakeResponse(HTTPStatus.OK, json_body={"access_token": "tok"}),
            _FakeResponse(HTTPStatus.OK, json_body={"hardware": []}),
        ]
    )
    adapter = NativeAlsoEnergyAdapter(http_session=session, max_retries=0, timeout_seconds=1)
    adapter.list_devices({"username": "u", "password": "p"}, "4")
    # The second call must be the site-scoped hardware GET.
    get_calls = [c for c in session.calls if c[0] == "GET"]
    assert get_calls and get_calls[-1][1].endswith("/Sites/4/Hardware")


def test_list_devices_no_content_returns_empty():
    adapter = _make(
        [
            _FakeResponse(HTTPStatus.OK, json_body={"access_token": "tok"}),
            _FakeResponse(HTTPStatus.NO_CONTENT, json_body=None),
        ]
    )
    devices = adapter.list_devices({"username": "u", "password": "p"}, "4")
    assert devices == ()


def test_list_devices_404_is_mapping_error():
    adapter = _make(
        [
            _FakeResponse(HTTPStatus.OK, json_body={"access_token": "tok"}),
            _FakeResponse(HTTPStatus.NOT_FOUND, json_body=None),
        ]
    )
    with pytest.raises(MappingError):
        adapter.list_devices({"username": "u", "password": "p"}, "4")


def test_list_devices_blank_site_id_is_mapping_error():
    adapter = _make([])  # token endpoint never reached
    with pytest.raises(MappingError):
        adapter.list_devices({"username": "u", "password": "p"}, "  ")


def test_list_devices_credential_error_propagates():
    adapter = _make([_FakeResponse(HTTPStatus.BAD_REQUEST, json_body={})])
    with pytest.raises(CredentialError):
        adapter.list_devices({"username": "u", "password": "p"}, "4")


def test_list_devices_5xx_after_token_is_unavailable():
    adapter = _make(
        [
            _FakeResponse(HTTPStatus.OK, json_body={"access_token": "tok"}),
            _FakeResponse(HTTPStatus.BAD_GATEWAY, json_body=None),
        ]
    )
    with pytest.raises(ProviderUnavailable):
        adapter.list_devices({"username": "u", "password": "p"}, "4")


@pytest.mark.parametrize(
    "status",
    [HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN, HTTPStatus.BAD_REQUEST],
)
def test_list_devices_4xx_after_token_is_credential_error(status):
    adapter = _make(
        [
            _FakeResponse(HTTPStatus.OK, json_body={"access_token": "tok"}),
            _FakeResponse(status, json_body=None),
        ]
    )
    with pytest.raises(CredentialError):
        adapter.list_devices({"username": "u", "password": "p"}, "4")


def test_list_devices_429_after_token_is_rate_limited():
    adapter = _make(
        [
            _FakeResponse(HTTPStatus.OK, json_body={"access_token": "tok"}),
            _FakeResponse(
                HTTPStatus.TOO_MANY_REQUESTS,
                json_body=None,
                headers={"Retry-After": "9"},
            ),
        ]
    )
    with pytest.raises(RateLimited) as ei:
        adapter.list_devices({"username": "u", "password": "p"}, "4")
    assert ei.value.retry_after == 9


def test_adapter_implements_device_listing_protocol():
    assert isinstance(NativeAlsoEnergyAdapter(), DeviceListingAdapter)


# ---------------------------------------------------------------------------
# Redaction
# ---------------------------------------------------------------------------


def test_credentials_and_token_never_logged(caplog):
    secret_user = "very_unique_username_xyz_aabbcc"
    secret_pass = "verylongpassword_donotleak_8b8c"
    secret_token = "totally-secret-access-token-9988-7654"
    adapter = _make(
        [_FakeResponse(HTTPStatus.OK, json_body={"access_token": secret_token})]
    )
    with caplog.at_level("INFO"):
        result = adapter.test_credentials({"username": secret_user, "password": secret_pass})
    assert result.success is True
    joined = " ".join(rec.getMessage() for rec in caplog.records)
    assert secret_user not in joined
    assert secret_pass not in joined
    assert secret_token not in joined


# ---------------------------------------------------------------------------
# Wiring sanity
# ---------------------------------------------------------------------------


def test_provider_key_is_also_energy():
    assert NativeAlsoEnergyAdapter.provider_key == "also_energy"


def test_required_fields_are_username_and_password():
    assert set(NativeAlsoEnergyAdapter.required_credential_fields) == {"username", "password"}
