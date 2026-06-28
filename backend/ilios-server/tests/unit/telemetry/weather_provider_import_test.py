"""Third-party weather provider import (Phases C/D) — DB-free unit tests.

These tests lock in the CONTEXT-ONLY contract of the provider import pipeline and
the external-weather context surface:

* External weather is NEVER expected-/physics-eligible: ``expected_eligible_capable``
  is frozen ``False`` and ``physics_usable_rows`` is always 0 (ghi/ambient/unknown
  semantics are stored verbatim, never transposed to poa/cell).
* The pipeline NEVER fabricates a value: a missing reading is the absence of a row,
  an invalid provider row is SKIPPED (and honestly downgrades the run to ``partial``),
  and a failed/empty pull is recorded with an honest ``failed``/``partial`` status.
* It is gap-only + idempotent: a fully-covered window spends zero provider calls,
  and an overlapping re-pull inserts nothing.
* The Redis-backed rate limiter fails OPEN on infra error / no declared limit and
  blocks once the declared quota is exhausted.

They deliberately avoid the session-scoped TestClient/lifespan fixtures (which hang
against the live dev Backend): the CRUDs the services touch are monkeypatched with
in-memory fakes, mirroring ``weather_resolver_test.py``.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from app.integrations.weather.base import (
    WeatherCredentialError,
    WeatherMappingError,
    WeatherProviderUnavailable,
    WeatherRateLimited,
)
from app.integrations.weather.models import (
    NormalizedWeatherRow,
    RateLimitSpec,
    WeatherProviderCapabilities,
    WeatherPullResult,
)
from app.models.weather import (
    WeatherConfidence,
    WeatherObservationBatchKind,
    WeatherProviderPullStatus,
    WeatherSourceType,
)
from app.schema.weather import ProviderImportRequest
from app.services.weather import external_weather_context_service as ewcs
from app.services.weather import provider_import_service as pis
from app.services.weather.provider_import_service import (
    ProviderRateLimiter,
    plan_chunks,
    preview_provider_import,
    resolve_metrics,
    run_provider_import,
    _normalize_provider_row,
)

_T0 = datetime(2026, 6, 1, 0, 0, 0)
_T1 = datetime(2026, 6, 1, 1, 0, 0)
_T2 = datetime(2026, 6, 1, 2, 0, 0)
_T3 = datetime(2026, 6, 1, 3, 0, 0)


# ---------------------------------------------------------------------------
# Fixtures / fakes
# ---------------------------------------------------------------------------
def _caps(
    metrics=("ghi_irradiance", "air_temperature"),
    *,
    rpm=None,
    rpd=None,
    max_history_days=None,
    is_modeled=True,
    plane="ghi",
    temp="ambient",
    licensing="public_domain",
) -> WeatherProviderCapabilities:
    return WeatherProviderCapabilities(
        supports_historical=True,
        supports_forecast=False,
        metrics=frozenset(metrics),
        native_plane=plane,
        native_temperature_type=temp,
        is_modeled=is_modeled,
        max_history_days=max_history_days,
        rate_limit=RateLimitSpec(requests_per_minute=rpm, requests_per_day=rpd),
        licensing_class=licensing,
    )


def _prow(
    ts,
    metric="ghi_irradiance",
    value=500.0,
    *,
    plane="ghi",
    temp="unknown",
    unit="W/m²",
    is_modeled=True,
    confidence="unknown",
) -> NormalizedWeatherRow:
    return NormalizedWeatherRow(
        obs_ts=ts,
        metric=metric,
        value=value,
        unit=unit,
        irradiance_plane=plane,
        temperature_type=temp,
        is_modeled=is_modeled,
        confidence=confidence,
    )


def _pull(rows, *, partial=False, warnings=(), errors=()) -> WeatherPullResult:
    return WeatherPullResult(
        rows=tuple(rows),
        partial=partial,
        warnings=tuple(warnings),
        errors=tuple(errors),
        request_hash="a" * 64,
        response_hash="b" * 64,
        api_version="test-v1",
    )


class FakeAdapter:
    """Adapter whose ``get_observations`` returns a queued result/exception per call."""

    def __init__(self, *, caps=None, results=None):
        self._caps = caps or _caps()
        self._results = list(results) if results is not None else None
        self.calls: list[tuple[datetime, datetime]] = []

    def capabilities(self):
        return self._caps

    def get_observations(
        self,
        credentials,
        *,
        latitude,
        longitude,
        window_start,
        window_end,
        requested_metrics,
        granularity="hourly",
    ):
        self.calls.append((window_start, window_end))
        if self._results is None:
            return _pull([_prow(window_start)])
        idx = min(len(self.calls) - 1, len(self._results) - 1)
        item = self._results[idx]
        if isinstance(item, Exception):
            raise item
        return item


class FakeObsCRUD:
    def __init__(self, *, existing=None, upsert_inserted=None):
        self._existing = list(existing or [])
        self._upsert_inserted = upsert_inserted
        self.upserted: list[dict] = []

    def get_window(self, site_id, *, start, end, metrics, weather_source_id=None):
        metric_set = set(metrics)
        out = []
        for o in self._existing:
            if o["metric"] not in metric_set:
                continue
            if (
                weather_source_id is not None
                and o.get("weather_source_id") != weather_source_id
            ):
                continue
            if start <= o["obs_ts"] <= end:
                out.append(SimpleNamespace(**o))
        return out

    def upsert(self, rows):
        rows = list(rows)
        self.upserted.extend(rows)
        if self._upsert_inserted is not None:
            return self._upsert_inserted
        return len(rows)


class FakeSourceCRUD:
    def __init__(self, *, sources=None, created_id=99):
        self._sources = list(sources or [])
        self._created_id = created_id
        self.create_calls = 0

    def list_for_site(self, site_id, **kw):
        return list(self._sources)

    def create(self, **kwargs):
        self.create_calls += 1
        obj = SimpleNamespace(id=self._created_id, **kwargs)
        self._sources.append(obj)
        return obj


class FakeBatchCRUD:
    def __init__(self):
        self.created: list[SimpleNamespace] = []

    def create(self, **kwargs):
        obj = SimpleNamespace(id=len(self.created) + 1, created_at=_T0, **kwargs)
        self.created.append(obj)
        return obj

    def list_provider_pulls_for_site(self, site_id, *, limit=100):
        return list(reversed(self.created))[:limit]


def _site():
    return SimpleNamespace(id=1, company_id=1)


def _catalog():
    return SimpleNamespace(display_name="Open-Meteo", licensing_class="public_domain")


def _req(*, start=_T0, end=_T3, metrics=None, granularity="hourly", account_id=None):
    return ProviderImportRequest(
        provider_key="open_meteo",
        account_id=account_id,
        window_start=start,
        window_end=end,
        metrics=metrics,
        granularity=granularity,
    )


def _ext_source(**kw):
    base = dict(
        id=20,
        source_type=WeatherSourceType.external_modeled_provider,
        provider_key="open_meteo",
        display_name="Open-Meteo",
        is_modeled=True,
        default_confidence=WeatherConfidence.unknown,
        licensing_note=None,
        active=True,
    )
    base.update(kw)
    return SimpleNamespace(**base)


def _patch_run_cruds(monkeypatch, *, obs, src, batch):
    monkeypatch.setattr(pis, "WeatherObservationCRUD", lambda db: obs)
    monkeypatch.setattr(pis, "WeatherSourceCRUD", lambda db: src)
    monkeypatch.setattr(pis, "WeatherObservationBatchCRUD", lambda db: batch)


# ---------------------------------------------------------------------------
# Pure planning helpers
# ---------------------------------------------------------------------------
def test_resolve_metrics_defaults_to_advertised_set():
    caps = _caps(metrics=("ghi_irradiance", "air_temperature"))
    assert resolve_metrics(caps, None) == ["air_temperature", "ghi_irradiance"]


def test_resolve_metrics_drops_unadvertised_request():
    caps = _caps(metrics=("ghi_irradiance",))
    # "wind" is not advertised -> dropped; only the advertised metric survives.
    assert resolve_metrics(caps, ["ghi_irradiance", "wind"]) == ["ghi_irradiance"]


def test_plan_chunks_splits_long_window():
    chunks, clamped = plan_chunks(
        datetime(2026, 1, 1), datetime(2026, 3, 1), max_chunk_days=31
    )
    assert clamped is None
    assert len(chunks) == 2
    # Chunks abut and cover the whole window with no overlap/gap.
    assert chunks[0][0] == datetime(2026, 1, 1)
    assert chunks[0][1] == chunks[1][0]
    assert chunks[-1][1] == datetime(2026, 3, 1)


def test_plan_chunks_clamps_to_max_history():
    now = datetime(2026, 6, 30)
    chunks, clamped = plan_chunks(
        datetime(2026, 1, 1),
        datetime(2026, 6, 25),
        max_history_days=10,
        provider_now=now,
    )
    assert clamped == now - timedelta(days=10)  # horizon = 2026-06-20
    assert chunks  # window_end (06-25) is past the horizon, so there is work
    assert chunks[0][0] == clamped  # start pulled forward to the archive horizon


def test_plan_chunks_empty_when_window_nonpositive():
    chunks, clamped = plan_chunks(datetime(2026, 6, 1), datetime(2026, 6, 1))
    assert chunks == []


# ---------------------------------------------------------------------------
# Row normalization — never convert, never fabricate
# ---------------------------------------------------------------------------
def test_normalize_preserves_ghi_ambient_semantics_never_poa_cell():
    obs, warn = _normalize_provider_row(
        _prow(_T0, "ghi_irradiance", 500.0, plane="ghi", temp="unknown")
    )
    assert warn is None
    assert obs is not None
    assert obs.irradiance_plane == "ghi"
    assert obs.irradiance_plane != "poa"
    obs2, _ = _normalize_provider_row(
        _prow(_T0, "air_temperature", 20.0, plane="unknown", temp="ambient")
    )
    assert obs2.temperature_type == "ambient"
    assert obs2.temperature_type not in ("cell", "module", "modeled_cell")


def test_normalize_skips_non_finite_value_with_warning():
    obs, warn = _normalize_provider_row(_prow(_T0, value=float("nan")))
    assert obs is None
    assert warn and "skipped invalid" in warn


def test_normalize_rejects_unknown_enum_semantics():
    # A bogus plane string is rejected (skipped), never silently coerced to poa.
    obs, warn = _normalize_provider_row(_prow(_T0, plane="not_a_real_plane"))
    assert obs is None
    assert warn and "irradiance_plane" in warn


# ---------------------------------------------------------------------------
# Rate limiter — fail OPEN, block on exhausted quota
# ---------------------------------------------------------------------------
class FakeRedis:
    def __init__(self, counts=None, *, raise_on=None):
        self.counts = dict(counts or {})
        self.raise_on = raise_on

    def get(self, key):
        if self.raise_on == "get":
            raise RuntimeError("redis down")
        return self.counts.get(key)

    def incr(self, key):
        self.counts[key] = int(self.counts.get(key, 0)) + 1

    def expire(self, key, ttl):
        pass


def test_rate_limiter_fails_open_with_no_client():
    limiter = ProviderRateLimiter(use_default_cache=False)
    allowed, retry = limiter.consume(
        provider_key="open_meteo", account_key="keyless", rpm=5, rpd=100
    )
    assert allowed is True
    assert retry is None


def test_rate_limiter_no_limits_is_noop():
    # A keyless/free provider declares no quota -> always allowed, never touches cache.
    limiter = ProviderRateLimiter(FakeRedis(raise_on="get"))
    allowed, _ = limiter.consume(
        provider_key="open_meteo", account_key="keyless", rpm=None, rpd=None
    )
    assert allowed is True


def test_rate_limiter_blocks_when_minute_quota_exhausted():
    now = datetime(2026, 6, 1, 12, 0, 0, tzinfo=timezone.utc)
    mkey, _dkey = ProviderRateLimiter._keys("open_meteo", "keyless", now)
    limiter = ProviderRateLimiter(FakeRedis({mkey: 5}))
    allowed, retry = limiter.consume(
        provider_key="open_meteo", account_key="keyless", rpm=5, rpd=None, now=now
    )
    assert allowed is False
    assert retry is not None and retry > 0


def test_rate_limiter_fails_open_on_redis_error():
    limiter = ProviderRateLimiter(FakeRedis(raise_on="get"))
    allowed, _ = limiter.consume(
        provider_key="open_meteo", account_key="keyless", rpm=5, rpd=100
    )
    assert allowed is True  # cache outage must never block a legitimate pull


# ---------------------------------------------------------------------------
# Preview — writes nothing, context-only verdict
# ---------------------------------------------------------------------------
def test_preview_is_context_only_and_writes_nothing(monkeypatch):
    obs, src, batch = FakeObsCRUD(), FakeSourceCRUD(sources=[]), FakeBatchCRUD()
    _patch_run_cruds(monkeypatch, obs=obs, src=src, batch=batch)
    adapter = FakeAdapter(caps=_caps())

    resp = preview_provider_import(
        None,
        site=_site(),
        catalog=_catalog(),
        adapter=adapter,
        coordinates=(42.0, -71.0),
        request=_req(),
        rate_limiter=ProviderRateLimiter(use_default_cache=False),
    )

    assert resp.context_only is True
    assert resp.expected_eligible_capable is False
    assert "context_only_not_expected_eligible" in resp.warnings
    assert resp.estimated_provider_calls == resp.chunk_count == 1
    # Dry-run: never calls the provider, never creates a source/batch.
    assert adapter.calls == []
    assert src.create_calls == 0
    assert batch.created == []
    assert obs.upserted == []


# ---------------------------------------------------------------------------
# Run — persistence, gap-fill, idempotency, honest status
# ---------------------------------------------------------------------------
def test_run_persists_context_only_rows_never_physics_usable(monkeypatch):
    obs = FakeObsCRUD(existing=[])
    src = FakeSourceCRUD(sources=[_ext_source()])
    batch = FakeBatchCRUD()
    _patch_run_cruds(monkeypatch, obs=obs, src=src, batch=batch)
    adapter = FakeAdapter(
        results=[
            _pull(
                [
                    _prow(_T0, "ghi_irradiance", 500.0, plane="ghi"),
                    _prow(_T1, "ghi_irradiance", 800.0, plane="ghi"),
                    _prow(
                        _T0,
                        "air_temperature",
                        21.0,
                        plane="unknown",
                        temp="ambient",
                        unit="°C",
                    ),
                ]
            )
        ]
    )

    resp = run_provider_import(
        None,
        site=_site(),
        catalog=_catalog(),
        adapter=adapter,
        credentials={},
        coordinates=(42.0, -71.0),
        request=_req(),
    )

    assert resp.pull_status == WeatherProviderPullStatus.succeeded.value
    assert resp.rows_inserted == 3
    assert resp.expected_eligible_capable is False
    assert resp.context_only is True
    # The whole point: ghi/ambient are stored verbatim but never physics-usable.
    assert resp.physics_usable_rows == 0
    assert resp.weather_source_id == 20  # reused existing external source
    assert src.create_calls == 0
    assert batch.created[0].row_count == 3
    assert batch.created[0].pull_status == WeatherProviderPullStatus.succeeded


def test_run_creates_external_modeled_source_when_absent(monkeypatch):
    obs = FakeObsCRUD(existing=[])
    src = FakeSourceCRUD(sources=[], created_id=77)
    batch = FakeBatchCRUD()
    _patch_run_cruds(monkeypatch, obs=obs, src=src, batch=batch)
    adapter = FakeAdapter(results=[_pull([_prow(_T0)])])

    resp = run_provider_import(
        None,
        site=_site(),
        catalog=_catalog(),
        adapter=adapter,
        credentials={},
        coordinates=(42.0, -71.0),
        request=_req(),
    )
    assert src.create_calls == 1
    assert resp.weather_source_id == 77
    # The created source is explicitly the external-modeled provider type.
    created = src._sources[-1]
    assert created.source_type == WeatherSourceType.external_modeled_provider


def test_run_skips_fully_covered_chunk_spending_no_provider_call(monkeypatch):
    # All 4 hourly slots x 2 metrics already stored for source 20 -> 0 provider calls.
    existing = [
        {"metric": m, "obs_ts": ts, "weather_source_id": 20}
        for m in ("ghi_irradiance", "air_temperature")
        for ts in (_T0, _T1, _T2, _T3)
    ]
    obs = FakeObsCRUD(existing=existing)
    src = FakeSourceCRUD(sources=[_ext_source()])
    batch = FakeBatchCRUD()
    _patch_run_cruds(monkeypatch, obs=obs, src=src, batch=batch)
    adapter = FakeAdapter(results=[_pull([_prow(_T0)])])

    resp = run_provider_import(
        None,
        site=_site(),
        catalog=_catalog(),
        adapter=adapter,
        credentials={},
        coordinates=(42.0, -71.0),
        request=_req(),
    )

    assert adapter.calls == []  # gap-fill spent no metered call
    assert resp.chunks_skipped == 1
    assert resp.rows_inserted == 0
    assert resp.pull_status == WeatherProviderPullStatus.succeeded.value


def test_run_idempotent_rerun_inserts_zero(monkeypatch):
    # Provider returns rows, but every dedupe_key already exists -> 0 inserted.
    obs = FakeObsCRUD(existing=[], upsert_inserted=0)
    src = FakeSourceCRUD(sources=[_ext_source()])
    batch = FakeBatchCRUD()
    _patch_run_cruds(monkeypatch, obs=obs, src=src, batch=batch)
    adapter = FakeAdapter(
        results=[_pull([_prow(_T0), _prow(_T1)])]
    )

    resp = run_provider_import(
        None,
        site=_site(),
        catalog=_catalog(),
        adapter=adapter,
        credentials={},
        coordinates=(42.0, -71.0),
        request=_req(),
    )
    assert resp.rows_pulled == 2
    assert resp.rows_inserted == 0
    assert resp.rows_duplicate == 2
    assert "idempotent_duplicates_skipped" in resp.warnings


def test_run_skipped_invalid_row_downgrades_to_partial_without_fabrication(monkeypatch):
    obs = FakeObsCRUD(existing=[])
    src = FakeSourceCRUD(sources=[_ext_source()])
    batch = FakeBatchCRUD()
    _patch_run_cruds(monkeypatch, obs=obs, src=src, batch=batch)
    adapter = FakeAdapter(
        results=[
            _pull(
                [
                    _prow(_T0, "ghi_irradiance", 500.0),
                    _prow(_T1, "ghi_irradiance", float("inf")),  # invalid -> skipped
                ]
            )
        ]
    )

    resp = run_provider_import(
        None,
        site=_site(),
        catalog=_catalog(),
        adapter=adapter,
        credentials={},
        coordinates=(42.0, -71.0),
        request=_req(),
    )
    assert resp.pull_status == WeatherProviderPullStatus.partial.value
    assert resp.rows_inserted == 1  # only the valid row; nothing fabricated
    assert batch.created[0].row_count == 1


def test_run_partial_when_one_chunk_fails(monkeypatch):
    obs = FakeObsCRUD(existing=[])
    src = FakeSourceCRUD(sources=[_ext_source()])
    batch = FakeBatchCRUD()
    _patch_run_cruds(monkeypatch, obs=obs, src=src, batch=batch)
    adapter = FakeAdapter(
        results=[
            _pull([_prow(_T0, "ghi_irradiance", 500.0)]),
            WeatherProviderUnavailable("provider down"),
        ]
    )
    # 40-day window with default 31-day chunk -> two chunks.
    resp = run_provider_import(
        None,
        site=_site(),
        catalog=_catalog(),
        adapter=adapter,
        credentials={},
        coordinates=(42.0, -71.0),
        request=_req(start=_T0, end=_T0 + timedelta(days=40)),
    )
    assert resp.pull_status == WeatherProviderPullStatus.partial.value
    assert resp.rows_inserted == 1
    assert resp.errors  # the failed chunk is recorded honestly
    assert batch.created[0].row_count == 1


def test_run_total_failure_is_failed_status_zero_rows(monkeypatch):
    obs = FakeObsCRUD(existing=[])
    src = FakeSourceCRUD(sources=[_ext_source()])
    batch = FakeBatchCRUD()
    _patch_run_cruds(monkeypatch, obs=obs, src=src, batch=batch)
    adapter = FakeAdapter(results=[WeatherMappingError("bad request")])

    resp = run_provider_import(
        None,
        site=_site(),
        catalog=_catalog(),
        adapter=adapter,
        credentials={},
        coordinates=(42.0, -71.0),
        request=_req(),
    )
    assert resp.pull_status == WeatherProviderPullStatus.failed.value
    assert resp.rows_inserted == 0
    assert obs.upserted == []  # nothing written on a total failure


def test_run_credential_error_is_failed_and_stops(monkeypatch):
    obs = FakeObsCRUD(existing=[])
    src = FakeSourceCRUD(sources=[_ext_source()])
    batch = FakeBatchCRUD()
    _patch_run_cruds(monkeypatch, obs=obs, src=src, batch=batch)
    adapter = FakeAdapter(results=[WeatherCredentialError("rejected")])

    resp = run_provider_import(
        None,
        site=_site(),
        catalog=_catalog(),
        adapter=adapter,
        credentials={"api_key": "x"},
        coordinates=(42.0, -71.0),
        request=_req(start=_T0, end=_T0 + timedelta(days=40)),
    )
    assert resp.pull_status == WeatherProviderPullStatus.failed.value
    assert len(adapter.calls) == 1  # stopped after the first chunk's rejection


def test_run_rate_limited_stops_before_calling_provider(monkeypatch):
    obs = FakeObsCRUD(existing=[])
    src = FakeSourceCRUD(sources=[_ext_source()])
    batch = FakeBatchCRUD()
    _patch_run_cruds(monkeypatch, obs=obs, src=src, batch=batch)
    adapter = FakeAdapter(results=[_pull([_prow(_T0)])])

    class DenyLimiter:
        def remaining(self, **kw):
            return (0, None)

        def consume(self, **kw):
            return (False, 30)

    resp = run_provider_import(
        None,
        site=_site(),
        catalog=_catalog(),
        adapter=adapter,
        credentials={},
        coordinates=(42.0, -71.0),
        request=_req(),
        rate_limiter=DenyLimiter(),
    )
    assert resp.rate_limited is True
    assert adapter.calls == []  # never spent a call once the limiter denied
    assert resp.pull_status == WeatherProviderPullStatus.failed.value


def test_run_provider_429_marks_rate_limited(monkeypatch):
    obs = FakeObsCRUD(existing=[])
    src = FakeSourceCRUD(sources=[_ext_source()])
    batch = FakeBatchCRUD()
    _patch_run_cruds(monkeypatch, obs=obs, src=src, batch=batch)
    adapter = FakeAdapter(results=[WeatherRateLimited("slow down", retry_after=42)])

    resp = run_provider_import(
        None,
        site=_site(),
        catalog=_catalog(),
        adapter=adapter,
        credentials={},
        coordinates=(42.0, -71.0),
        request=_req(),
    )
    assert resp.rate_limited is True
    assert resp.pull_status == WeatherProviderPullStatus.failed.value


# ---------------------------------------------------------------------------
# Phase D / D1 — external-weather CONTEXT aggregation (read-only)
# ---------------------------------------------------------------------------
def test_external_context_reports_only_external_sources_context_only(monkeypatch):
    ext = _ext_source(id=20)
    on_site = SimpleNamespace(
        id=21,
        source_type=WeatherSourceType.on_site_calibrated_sensor,
        provider_key=None,
        display_name="Pyranometer A",
        is_modeled=False,
        default_confidence=WeatherConfidence.high,
        licensing_note=None,
        active=True,
    )

    class FakeSrc:
        def list_for_site(self, sid):
            return [ext, on_site]

    captured = {}

    class FakeObs:
        def summarize_by_source_metric(self, sid, *, source_ids=None):
            captured["source_ids"] = list(source_ids) if source_ids is not None else None
            return [(20, "ghi_irradiance", 24, _T0, _T3)]

    class FakeBatch:
        def list_provider_pulls_for_site(self, sid, *, limit=50):
            return [
                SimpleNamespace(
                    id=5,
                    site_id=1,
                    weather_source_id=20,
                    account_id=None,
                    batch_kind=WeatherObservationBatchKind.provider_pull,
                    pull_status=WeatherProviderPullStatus.succeeded,
                    period_start=_T0,
                    period_end=_T3,
                    row_count=24,
                    provider_api_version="test-v1",
                    error_summary=None,
                    created_at=_T0,
                )
            ]

    monkeypatch.setattr(ewcs, "WeatherSourceCRUD", lambda db: FakeSrc())
    monkeypatch.setattr(ewcs, "WeatherObservationCRUD", lambda db: FakeObs())
    monkeypatch.setattr(ewcs, "WeatherObservationBatchCRUD", lambda db: FakeBatch())

    resp = ewcs.build_external_weather_context(None, site=_site())

    # Only the external source is summarized (the on-site sensor is excluded).
    assert captured["source_ids"] == [20]
    assert resp.source_count == 1
    assert resp.sources[0].weather_source_id == 20
    assert resp.expected_eligible_capable is False
    assert resp.context_only is True
    assert resp.total_observation_count == 24
    assert resp.last_pull is not None and resp.last_pull.id == 5
    assert resp.sources[0].metrics[0].metric == "ghi_irradiance"


def test_external_context_never_fabricates_when_empty(monkeypatch):
    ext = _ext_source(id=20)

    class FakeSrc:
        def list_for_site(self, sid):
            return [ext]

    class FakeObs:
        def summarize_by_source_metric(self, sid, *, source_ids=None):
            return []  # no stored observations

    class FakeBatch:
        def list_provider_pulls_for_site(self, sid, *, limit=50):
            return []

    monkeypatch.setattr(ewcs, "WeatherSourceCRUD", lambda db: FakeSrc())
    monkeypatch.setattr(ewcs, "WeatherObservationCRUD", lambda db: FakeObs())
    monkeypatch.setattr(ewcs, "WeatherObservationBatchCRUD", lambda db: FakeBatch())

    resp = ewcs.build_external_weather_context(None, site=_site())

    # The source still appears (it exists) but coverage is honestly empty, not 0-filled.
    assert resp.source_count == 1
    assert resp.total_observation_count == 0
    assert resp.sources[0].observation_count == 0
    assert resp.sources[0].metrics == []
    assert resp.last_pull is None
