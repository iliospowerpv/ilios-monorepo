"""Endpoint-level coverage for the read-only V2 performance-context route.

These exercise the FastAPI layer of
``GET /api/telemetry/v2/sites/{site_id}/performance-context`` end-to-end via the
TestClient, with the cross-tenant authorization dependency
(``get_authorized_site``) and the read-only session dependency overridden so no
real database is required. The per-bucket composition seams are monkeypatched
(exactly as the service unit suite does), which lets these tests assert two
things the unit suite cannot:

* **Auth / cross-tenant** — a site the caller cannot see surfaces as a ``404``
  (the route never composes a body for an unauthorized site).
* **Period-effective parity (§11)** — the ``expected_*`` the endpoint serves is
  the VERBATIM output of ``compute_site_expected_period_effective``; the route
  re-derives no formula, so a known expected bucket flows through unchanged.

Everything here is read-only; the overridden session is a spy that fails the
test if any mutating method is ever touched.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import app.services.telemetry.performance_context_service as svc
from app.db.session import get_session
from app.helpers.authorization.project_access import get_authorized_site
from app.main import app
from app.schema.weather import (
    WeatherSemanticsReconciliationResponse,
    WeatherSemanticsReconciliationRow,
)
from app.services.telemetry.expected_service import (
    BucketStatus,
    ExpectedBucket,
    ExpectedResult,
    OverallStatus,
)

_T0 = datetime(2026, 6, 20, 0, 0, 0)


class _NoWriteSession:
    """A session stand-in that raises if any mutating method is touched."""

    def __getattr__(self, name):
        if name in {"add", "commit", "flush", "delete", "execute", "merge"}:
            raise AssertionError(f"endpoint must not call session.{name}")
        raise AttributeError(name)


class _RollupRow:
    def __init__(self, bucket_start, value, *, unit="kW", agg="avg"):
        self.bucket_start = bucket_start
        self.value = value
        self.unit = unit
        self.agg = agg
        self.sample_count = 12
        self.completeness = 1.0


def _fake_rollup_crud(rows_by_metric):
    class _Fake:
        def __init__(self, _db):
            pass

        def get_series(self, *, site_id, normalized_metric, bucket_size, start, end):
            return rows_by_metric.get(normalized_metric, [])

        def latest_bucket_start(self, _site_id):
            return None

    return _Fake


def _fake_reading_crud(latest_ts):
    class _Fake:
        def __init__(self, _db):
            pass

        def latest_metric_ts(self, _site_id):
            return latest_ts

    return _Fake


def _fake_recon():
    return WeatherSemanticsReconciliationResponse(
        site_id=1,
        generated_at=_T0,
        total_weather_capable_devices=0,
        has_weather_source=False,
        has_active_weather_profile=False,
        eligible_count=0,
        needs_re_review_count=0,
        devices=[],
    )


def _fake_diagnostics():
    return SimpleNamespace(
        total_devices=1,
        mappable_count=1,
        mapped_count=1,
        unmapped_eligible_count=0,
        expected_driving_count=1,
        weather_source_count=0,
        weather_unknown_semantics_count=0,
    )


def _expected_result(expected_power_kw):
    bucket = ExpectedBucket(
        bucket_start=_T0,
        status=BucketStatus.ok,
        expected_power_kw=expected_power_kw,
        expected_energy_kwh=expected_power_kw,
        actual_power_kw=None,
        irradiance_wm2=None,
        cell_temperature_f=None,
        age_years=None,
        baseline_id=57,
    )
    return ExpectedResult(
        overall_status=OverallStatus.ok,
        baseline_id=57,
        baseline_type="weather_adjusted_model",
        bucket_size="1h",
        window_start=_T0,
        window_end=_T0 + timedelta(hours=1),
        buckets=[bucket],
        expected_energy_kwh=None,
        actual_energy_kwh=None,
        ok_bucket_count=1,
        missing_inputs_bucket_count=0,
        pre_pto_bucket_count=0,
        baseline_selection_mode="period_effective",
    )


@pytest.fixture
def _patched_seams(monkeypatch):
    """Patch the composition seams; the expected calc returns a known 42.0 kW."""
    monkeypatch.setattr(
        svc, "_active_baseline",
        lambda *_a, **_k: SimpleNamespace(id=57, baseline_type="weather_adjusted_model"),
    )
    monkeypatch.setattr(
        svc, "_evaluate_active_baseline", lambda *_a, **_k: (False, None)
    )
    monkeypatch.setattr(
        svc,
        "compute_site_expected_period_effective",
        lambda *_a, **_k: _expected_result(42.0),
    )
    monkeypatch.setattr(
        svc, "compute_site_eligibility_diagnostics", lambda *_a, **_k: _fake_diagnostics()
    )
    monkeypatch.setattr(
        svc, "build_site_semantics_reconciliation", lambda *_a, **_k: _fake_recon()
    )
    monkeypatch.setattr(
        svc,
        "TelemetrySiteRollupCRUD",
        _fake_rollup_crud({svc.SITE_POWER_METRIC: [_RollupRow(_T0, 40.0)]}),
    )
    monkeypatch.setattr(
        svc, "TelemetryReadingCRUD", _fake_reading_crud(datetime.utcnow())
    )
    monkeypatch.setattr(
        svc,
        "compute_site_telemetry_health",
        lambda *_a, **_k: SimpleNamespace(
            status=__import__(
                "app.schema.telemetry", fromlist=["TelemetryHealthStatus"]
            ).TelemetryHealthStatus.healthy,
            last_data_at=datetime.utcnow(),
            data_delay_minutes=1,
        ),
    )


def _override_session():
    yield _NoWriteSession()


@pytest.fixture(autouse=True)
def _clean_overrides():
    app.dependency_overrides[get_session] = _override_session
    yield
    app.dependency_overrides.pop(get_session, None)
    app.dependency_overrides.pop(get_authorized_site, None)


_URL = "/api/telemetry/v2/sites/1/performance-context"
_PARAMS = {"from": "2026-06-20T00:00:00", "to": "2026-06-20T01:00:00", "bucket": "1h"}


def test_cross_tenant_site_returns_404():
    """A site the caller cannot see fails closed with 404 — no body composed."""

    def _deny():
        raise HTTPException(status_code=404, detail="Site not found")

    app.dependency_overrides[get_authorized_site] = _deny
    client = TestClient(app)
    resp = client.get(_URL, params=_PARAMS)
    assert resp.status_code == 404


def test_envelope_shape_and_period_effective_parity(_patched_seams):
    """Happy path: canonical envelope + the expected value is the verbatim
    period-effective calc output (no re-derivation by the endpoint)."""
    app.dependency_overrides[get_authorized_site] = lambda: SimpleNamespace(
        id=1, timezone="America/New_York"
    )
    client = TestClient(app)
    resp = client.get(_URL, params=_PARAMS)
    assert resp.status_code == 200
    body = resp.json()

    # canonical top-level envelope fields
    assert body["site_id"] == 1
    assert body["site_timezone"] == "America/New_York"
    assert body["window"]["start"] == "2026-06-20T00:00:00"
    assert body["window"]["end"] == "2026-06-20T01:00:00"
    assert "naive-UTC" in body["window"]["tz_note"]

    # period-effective parity: the expected the endpoint serves is verbatim
    bucket = body["series"][0]
    assert bucket["expected_kw"] == 42.0
    assert bucket["baseline_id"] == 57
    assert bucket["source_provenance"]["baseline_selection_mode"] == "period_effective"
    # actual flows through from the rollup verbatim; never zero-filled or faked
    assert bucket["actual_kw"] == 40.0


def test_invalid_temp_unit_returns_422():
    """temp_unit validation happens at the route before any composition."""
    app.dependency_overrides[get_authorized_site] = lambda: SimpleNamespace(
        id=1, timezone="UTC"
    )
    client = TestClient(app)
    resp = client.get(_URL, params={**_PARAMS, "temp_unit": "K"})
    assert resp.status_code == 422


def test_today_1d_non_utc_site_rejected():
    """``window=today`` + ``bucket=1d`` on a non-UTC site is rejected (422):
    the site-local day start does not align to the UTC-anchored 1d grid, so a
    1d bucket over 'today' would be empty/misaligned. The guard fires before
    any composition (no patched seams required)."""
    app.dependency_overrides[get_authorized_site] = lambda: SimpleNamespace(
        id=1, timezone="America/New_York"
    )
    client = TestClient(app)
    resp = client.get(_URL, params={"window": "today", "bucket": "1d"})
    assert resp.status_code == 422
    assert "bucket=1d is not supported with window=today" in resp.text


def test_today_1d_utc_site_allowed(_patched_seams):
    """``window=today`` + ``bucket=1d`` on a UTC site is allowed: local midnight
    IS UTC midnight, so the window start lands on the 1d grid and composition
    proceeds normally (200)."""
    app.dependency_overrides[get_authorized_site] = lambda: SimpleNamespace(
        id=1, timezone="UTC"
    )
    client = TestClient(app)
    resp = client.get(_URL, params={"window": "today", "bucket": "1d"})
    assert resp.status_code == 200
