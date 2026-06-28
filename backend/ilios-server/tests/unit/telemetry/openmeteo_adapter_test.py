"""Open-Meteo weather provider adapter — Phase A unit tests.

These are pure / fixture-driven (no live HTTP, no DB writes). They lock in the
context-only contract:

* GHI irradiance is tagged ``plane="ghi"`` and NEVER ``poa``;
* ambient temperature is tagged ``temperature_type="ambient"`` and NEVER cell;
* every emitted row is ``is_modeled=True`` with ``confidence="unknown"``;
* a ``None`` reading is SKIPPED (a missing reading is the absence of a row);
* the adapter's declared ``expected_eligible_capable`` is FROZEN to ``False``;
* provider HTTP errors map onto the structured exception taxonomy.
"""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from app.integrations.weather.base import (
    WeatherCredentialError,
    WeatherMappingError,
    WeatherProviderAdapter,
    WeatherProviderUnavailable,
    WeatherRateLimited,
)
from app.integrations.weather.openmeteo_adapter import OpenMeteoAdapter

_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "weather"
    / "openmeteo_archive_sample.json"
)


def _payload() -> dict:
    return json.loads(_FIXTURE.read_text())


def _all_variables() -> set[str]:
    return {"shortwave_radiation", "temperature_2m"}


def test_adapter_satisfies_protocol():
    assert isinstance(OpenMeteoAdapter(), WeatherProviderAdapter)


def test_capabilities_are_context_only():
    caps = OpenMeteoAdapter().capabilities()
    # The whole point: external weather can never become physics-eligible here.
    assert caps.expected_eligible_capable is False
    assert caps.native_plane == "ghi"
    assert caps.native_temperature_type == "ambient"
    assert caps.is_modeled is True
    assert "ghi_irradiance" in caps.metrics
    assert "air_temperature" in caps.metrics
    # No POA / cell anywhere in the declared semantics.
    assert "poa" not in caps.native_plane
    assert caps.native_temperature_type != "cell"


def test_parse_ghi_is_ghi_never_poa():
    rows = OpenMeteoAdapter().parse_response(
        _payload(), requested_variables=_all_variables()
    )
    ghi_rows = [r for r in rows if r.metric == "ghi_irradiance"]
    # 4 timestamps, all shortwave values present (incl. 0.0 which is REAL data).
    assert len(ghi_rows) == 4
    for r in ghi_rows:
        assert r.irradiance_plane == "ghi"
        assert r.irradiance_plane != "poa"
        assert r.temperature_type == "unknown"
        assert r.is_modeled is True
        assert r.confidence == "unknown"
        assert r.unit == "W/m²"


def test_parse_temperature_is_ambient_never_cell_and_skips_null():
    rows = OpenMeteoAdapter().parse_response(
        _payload(), requested_variables=_all_variables()
    )
    temp_rows = [r for r in rows if r.metric == "air_temperature"]
    # 4 timestamps but the 4th temperature_2m value is null -> SKIPPED.
    assert len(temp_rows) == 3
    for r in temp_rows:
        assert r.temperature_type == "ambient"
        assert r.temperature_type not in ("cell", "module", "modeled_cell")
        assert r.irradiance_plane == "unknown"
        assert r.is_modeled is True


def test_no_row_is_ever_poa_or_cell():
    rows = OpenMeteoAdapter().parse_response(
        _payload(), requested_variables=_all_variables()
    )
    assert rows
    assert all(r.irradiance_plane != "poa" for r in rows)
    assert all(
        r.temperature_type not in ("cell", "module", "modeled_cell") for r in rows
    )


def test_zero_irradiance_is_preserved_not_dropped():
    # 0.0 at night is a real measurement; only None is a missing reading.
    rows = OpenMeteoAdapter().parse_response(
        _payload(), requested_variables={"shortwave_radiation"}
    )
    zero_rows = [r for r in rows if r.value == 0.0]
    assert len(zero_rows) == 2


def test_window_filtering_is_inclusive_of_bounds():
    rows = OpenMeteoAdapter().parse_response(
        _payload(),
        requested_variables={"shortwave_radiation"},
        window_start=datetime(2024, 6, 1, 1, 0),
        window_end=datetime(2024, 6, 1, 2, 0),
    )
    ts = sorted(r.obs_ts for r in rows)
    assert ts == [datetime(2024, 6, 1, 1, 0), datetime(2024, 6, 1, 2, 0)]


def test_get_observations_with_fake_fetcher_sets_provenance_hashes():
    body = _FIXTURE.read_bytes()
    captured = {}

    def fetcher(url: str):
        captured["url"] = url
        return 200, body

    result = OpenMeteoAdapter(fetcher=fetcher).get_observations(
        {},
        latitude=42.36,
        longitude=-71.06,
        window_start=datetime(2024, 6, 1, 0, 0),
        window_end=datetime(2024, 6, 1, 3, 0),
        requested_metrics=["ghi_irradiance", "air_temperature"],
    )
    assert result.rows
    assert result.request_hash and len(result.request_hash) == 64
    assert result.response_hash and len(result.response_hash) == 64
    assert result.api_version == "open-meteo-archive-v1"
    assert result.partial is False
    # URL is keyless and carries no secret material.
    assert "archive-api.open-meteo.com" in captured["url"]
    assert "apikey" not in captured["url"].lower()


def test_unsupported_metric_is_warned_not_fabricated():
    def fetcher(url: str):  # pragma: no cover - should not be called
        raise AssertionError("must not fetch when no supported metric requested")

    result = OpenMeteoAdapter(fetcher=fetcher).get_observations(
        {},
        latitude=1.0,
        longitude=2.0,
        window_start=datetime(2024, 6, 1, 0, 0),
        window_end=datetime(2024, 6, 1, 3, 0),
        requested_metrics=["wind_gust_unsupported"],
    )
    assert result.rows == ()
    assert result.partial is True
    assert any("Unsupported metric" in w for w in result.warnings)


@pytest.mark.parametrize(
    "status,exc",
    [
        (403, WeatherCredentialError),
        (401, WeatherCredentialError),
        (429, WeatherRateLimited),
        (400, WeatherMappingError),
        (500, WeatherProviderUnavailable),
    ],
)
def test_http_errors_map_to_structured_exceptions(status, exc):
    def fetcher(url: str):
        return status, b'{"reason":"boom"}'

    with pytest.raises(exc):
        OpenMeteoAdapter(fetcher=fetcher).get_observations(
            {},
            latitude=1.0,
            longitude=2.0,
            window_start=datetime(2024, 6, 1, 0, 0),
            window_end=datetime(2024, 6, 1, 1, 0),
            requested_metrics=["ghi_irradiance"],
        )
