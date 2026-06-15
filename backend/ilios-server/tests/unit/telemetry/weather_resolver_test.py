"""Unit tests for the W1 WeatherResolver (DB-free).

These tests deliberately avoid the session-scoped TestClient/lifespan fixtures
(which hang against the live dev Backend). Pure-helper tests exercise the
provenance decision logic directly; ``resolve_window`` tests monkeypatch the read
CRUDs with in-memory fakes. The numeric-invariance test proves that routing the
weather inputs through the resolver yields byte-for-byte identical expected
numbers compared to feeding the same buckets to the pure calc core.
"""
from __future__ import annotations

import ast
import pathlib
from datetime import datetime
from types import SimpleNamespace

from app.models.weather import (
    WeatherCalibrationStatus,
    WeatherConfidence,
    WeatherIrradiancePlane,
    WeatherSourceProfileRole,
    WeatherSourceProfileStatus,
    WeatherSourceType,
    WeatherTemperatureType,
)
from app.services.telemetry import expected_service as es
from app.services.telemetry.expected_service import (
    BUCKET_SIZE_TO_HOURS,
    BaselineParams,
    BucketInput,
    OverallStatus,
    compute_expected_buckets,
    compute_site_expected,
)
from app.services.weather import weather_resolver as wr
from app.services.weather.weather_resolver import (
    BELOW_CONFIDENCE_THRESHOLD,
    CELL_TEMPERATURE_METRIC,
    IRRADIANCE_METRIC,
    MISSING_CELL_TEMPERATURE,
    MISSING_IRRADIANCE,
    PROFILE_MISSING,
    SEMANTICS_UNKNOWN,
    WEATHER_SOURCE_UNAPPROVED,
    ResolvedWeatherBucket,
    ResolvedWeatherProvenance,
    ResolvedWeatherWindow,
    WeatherResolver,
    WeatherResolverStatus,
    _confidence_rank,
    _covers_window,
    _enum_value,
    _MetricSemantics,
    _overlaps_window,
    _periods_cover_window,
    _resolve_metric_mappings,
    _select_active_profile,
    derive_weather_provenance,
)


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------
def _row(bucket_start: datetime, value: float):
    return SimpleNamespace(bucket_start=bucket_start, value=value)


def _mapping(
    *,
    id: int,
    metric: str,
    plane=WeatherIrradiancePlane.unknown,
    temp=WeatherTemperatureType.unknown,
    calibration=WeatherCalibrationStatus.unknown,
    weather_source_id=None,
    effective_from=None,
    effective_to=None,
):
    return SimpleNamespace(
        id=id,
        metric=metric,
        irradiance_plane=plane,
        temperature_type=temp,
        calibration_status=calibration,
        weather_source_id=weather_source_id,
        effective_from=effective_from,
        effective_to=effective_to,
    )


def _profile(
    *,
    id: int,
    status=WeatherSourceProfileStatus.active,
    role=WeatherSourceProfileRole.live,
    min_confidence_policy=None,
    effective_from=None,
    effective_to=None,
    external_modeled_allowed=False,
):
    return SimpleNamespace(
        id=id,
        status=status,
        role=role,
        min_confidence_policy=min_confidence_policy,
        effective_from=effective_from,
        effective_to=effective_to,
        external_modeled_allowed=external_modeled_allowed,
    )


def _source(
    *,
    id: int,
    confidence=WeatherConfidence.high,
    source_type=WeatherSourceType.on_site_calibrated_sensor,
    is_modeled=False,
    display_name="Pyranometer A",
):
    return SimpleNamespace(
        id=id,
        default_confidence=confidence,
        source_type=source_type,
        is_modeled=is_modeled,
        display_name=display_name,
    )


def _patch_resolver(
    monkeypatch,
    *,
    irr_rows=(),
    cell_rows=(),
    mappings=(),
    profiles=(),
    sources=(),
    calls=None,
):
    """Monkeypatch the read CRUDs the resolver uses with in-memory fakes."""
    source_by_id = {s.id: s for s in sources}
    calls = calls if calls is not None else []

    class FakeRollupCRUD:
        def __init__(self, db):  # noqa: D107
            pass

        def get_series(self, *, site_id, normalized_metric, bucket_size, start, end):
            calls.append("get_series")
            if normalized_metric == IRRADIANCE_METRIC:
                return list(irr_rows)
            if normalized_metric == CELL_TEMPERATURE_METRIC:
                return list(cell_rows)
            return []

    class FakeMappingCRUD:
        def __init__(self, db):  # noqa: D107
            pass

        def list_for_site(self, site_id):
            calls.append("list_for_site")
            return list(mappings)

    class FakeProfileCRUD:
        def __init__(self, db):  # noqa: D107
            pass

        def list_for_site(self, site_id):
            calls.append("list_for_site")
            return list(profiles)

    class FakeSourceCRUD:
        def __init__(self, db):  # noqa: D107
            pass

        def get(self, source_id):
            calls.append("get")
            return source_by_id.get(source_id)

    monkeypatch.setattr(wr, "TelemetrySiteRollupCRUD", FakeRollupCRUD)
    monkeypatch.setattr(wr, "WeatherDeviceMappingCRUD", FakeMappingCRUD)
    monkeypatch.setattr(wr, "WeatherSourceProfileCRUD", FakeProfileCRUD)
    monkeypatch.setattr(wr, "WeatherSourceCRUD", FakeSourceCRUD)
    return calls


_T0 = datetime(2026, 6, 1, 0, 0, 0)
_T1 = datetime(2026, 6, 1, 1, 0, 0)
_T2 = datetime(2026, 6, 1, 2, 0, 0)
_WIN_START = datetime(2026, 6, 1, 0, 0, 0)
_WIN_END = datetime(2026, 6, 1, 23, 0, 0)


# ---------------------------------------------------------------------------
# Tiny pure helpers
# ---------------------------------------------------------------------------
def test_enum_value_handles_enum_str_and_none():
    assert _enum_value(WeatherIrradiancePlane.poa) == "poa"
    assert _enum_value("poa") == "poa"
    assert _enum_value(None) is None


def test_window_coverage_and_overlap():
    # Open-ended bounds always cover/overlap.
    assert _covers_window(None, None, _WIN_START, _WIN_END)
    assert _overlaps_window(None, None, _WIN_START, _WIN_END)
    # Fully covering.
    assert _covers_window(datetime(2026, 1, 1), datetime(2026, 12, 31), _WIN_START, _WIN_END)
    # Starts mid-window: overlaps but does not cover.
    assert not _covers_window(datetime(2026, 6, 1, 6), None, _WIN_START, _WIN_END)
    assert _overlaps_window(datetime(2026, 6, 1, 6), None, _WIN_START, _WIN_END)
    # Entirely before the window: neither.
    assert not _overlaps_window(datetime(2025, 1, 1), datetime(2025, 2, 1), _WIN_START, _WIN_END)


def test_confidence_rank_ordering():
    assert _confidence_rank("unknown") == 0
    assert _confidence_rank("low") < _confidence_rank("medium") < _confidence_rank("high")
    assert _confidence_rank(None) == 0


# ---------------------------------------------------------------------------
# Mapping semantics selection
# ---------------------------------------------------------------------------
def test_resolve_metric_mappings_single_declared_value():
    mappings = [
        _mapping(id=1, metric=IRRADIANCE_METRIC, plane=WeatherIrradiancePlane.poa),
    ]
    sem = _resolve_metric_mappings(
        mappings, metric=IRRADIANCE_METRIC, attr="irradiance_plane", start=_WIN_START, end=_WIN_END
    )
    assert sem.value == "poa"
    assert sem.conflict is False
    assert sem.chosen is mappings[0]


def test_resolve_metric_mappings_conflict_is_unknown():
    mappings = [
        _mapping(id=1, metric=IRRADIANCE_METRIC, plane=WeatherIrradiancePlane.poa),
        _mapping(id=2, metric=IRRADIANCE_METRIC, plane=WeatherIrradiancePlane.ghi),
    ]
    sem = _resolve_metric_mappings(
        mappings, metric=IRRADIANCE_METRIC, attr="irradiance_plane", start=_WIN_START, end=_WIN_END
    )
    assert sem.value == "unknown"
    assert sem.conflict is True


def test_resolve_metric_mappings_partial_coverage_is_unknown():
    # POA mapping only covers the second half of the window -> must NOT verify the
    # whole window; value stays unknown but the mapping is still surfaced.
    mappings = [
        _mapping(
            id=1,
            metric=IRRADIANCE_METRIC,
            plane=WeatherIrradiancePlane.poa,
            effective_from=datetime(2026, 6, 1, 12),  # starts mid-window
        ),
    ]
    sem = _resolve_metric_mappings(
        mappings, metric=IRRADIANCE_METRIC, attr="irradiance_plane", start=_WIN_START, end=_WIN_END
    )
    assert sem.value == "unknown"
    assert sem.conflict is False
    assert sem.chosen is mappings[0]  # context retained


def test_resolve_metric_mappings_poa_plus_unknown_overlap_is_unknown():
    # A POA mapping covering the whole window AND a coexisting unknown-plane
    # mapping -> ambiguous at the site-rollup level, so stay unknown.
    mappings = [
        _mapping(id=1, metric=IRRADIANCE_METRIC, plane=WeatherIrradiancePlane.poa),
        _mapping(id=2, metric=IRRADIANCE_METRIC, plane=WeatherIrradiancePlane.unknown),
    ]
    sem = _resolve_metric_mappings(
        mappings, metric=IRRADIANCE_METRIC, attr="irradiance_plane", start=_WIN_START, end=_WIN_END
    )
    assert sem.value == "unknown"
    assert sem.conflict is False


def test_resolve_metric_mappings_two_periods_jointly_cover_window():
    # Two POA mappings whose periods abut to jointly cover the window -> verified.
    mappings = [
        _mapping(
            id=1,
            metric=IRRADIANCE_METRIC,
            plane=WeatherIrradiancePlane.poa,
            effective_to=datetime(2026, 6, 1, 12),
        ),
        _mapping(
            id=2,
            metric=IRRADIANCE_METRIC,
            plane=WeatherIrradiancePlane.poa,
            effective_from=datetime(2026, 6, 1, 12),
        ),
    ]
    sem = _resolve_metric_mappings(
        mappings, metric=IRRADIANCE_METRIC, attr="irradiance_plane", start=_WIN_START, end=_WIN_END
    )
    assert sem.value == "poa"


def test_periods_cover_window_detects_gap():
    assert _periods_cover_window([(None, None)], _WIN_START, _WIN_END)
    # Gap between the two periods.
    assert not _periods_cover_window(
        [
            (None, datetime(2026, 6, 1, 6)),
            (datetime(2026, 6, 1, 12), None),
        ],
        _WIN_START,
        _WIN_END,
    )
    assert not _periods_cover_window([], _WIN_START, _WIN_END)


def test_resolve_metric_mappings_ignores_non_overlapping_and_other_metrics():
    mappings = [
        _mapping(
            id=1,
            metric=IRRADIANCE_METRIC,
            plane=WeatherIrradiancePlane.poa,
            effective_from=datetime(2025, 1, 1),
            effective_to=datetime(2025, 2, 1),  # before window
        ),
        _mapping(id=2, metric=CELL_TEMPERATURE_METRIC, temp=WeatherTemperatureType.cell),
    ]
    sem = _resolve_metric_mappings(
        mappings, metric=IRRADIANCE_METRIC, attr="irradiance_plane", start=_WIN_START, end=_WIN_END
    )
    assert sem.value == "unknown"
    assert sem.chosen is None


# ---------------------------------------------------------------------------
# Profile selection
# ---------------------------------------------------------------------------
def test_select_active_profile_prefers_full_cover():
    profiles = [
        _profile(id=1),  # open-ended active, covers
    ]
    chosen, partial, unapproved = _select_active_profile(profiles, _WIN_START, _WIN_END)
    assert chosen is profiles[0]
    assert partial is False
    assert unapproved is False


def test_select_active_profile_partial_window_flagged():
    profiles = [
        _profile(id=1, effective_from=datetime(2026, 6, 1, 6)),  # starts mid-window
    ]
    chosen, partial, unapproved = _select_active_profile(profiles, _WIN_START, _WIN_END)
    assert chosen is profiles[0]
    assert partial is True


def test_select_active_profile_none_when_no_active():
    profiles = [_profile(id=1, status=WeatherSourceProfileStatus.draft)]
    chosen, partial, unapproved = _select_active_profile(profiles, _WIN_START, _WIN_END)
    assert chosen is None
    assert unapproved is True


# ---------------------------------------------------------------------------
# Provenance derivation (the safety-critical decision logic)
# ---------------------------------------------------------------------------
def _poa_sem(**kw):
    return _MetricSemantics(value=WeatherIrradiancePlane.poa.value, conflict=False, **kw)


def _cell_sem(**kw):
    return _MetricSemantics(value=WeatherTemperatureType.cell.value, conflict=False, **kw)


def _unknown_sem():
    return _MetricSemantics(chosen=None, value="unknown", conflict=False)


def test_derive_verified_uses_mapped_source_confidence():
    src = _source(id=10, confidence=WeatherConfidence.high)
    prov = derive_weather_provenance(
        irr_sem=_poa_sem(chosen=_mapping(id=1, metric=IRRADIANCE_METRIC, calibration=WeatherCalibrationStatus.calibrated, weather_source_id=10)),
        temp_sem=_cell_sem(chosen=_mapping(id=2, metric=CELL_TEMPERATURE_METRIC, weather_source_id=10)),
        active_profile=_profile(id=5),
        profile_partial_window=False,
        has_unapproved_profile=False,
        value_source=src,
        has_irradiance=True,
        has_cell_temperature=True,
    )
    assert prov.status == WeatherResolverStatus.semantics_verified.value
    assert prov.irradiance_plane == "poa"
    assert prov.temperature_type == "cell"
    assert prov.confidence == "high"
    assert prov.calibration_status == "calibrated"
    assert prov.profile_id == 5
    assert SEMANTICS_UNKNOWN not in prov.missing_inputs


def test_derive_unknown_plane_is_not_promoted_to_poa():
    prov = derive_weather_provenance(
        irr_sem=_unknown_sem(),
        temp_sem=_cell_sem(chosen=_mapping(id=2, metric=CELL_TEMPERATURE_METRIC)),
        active_profile=None,
        profile_partial_window=False,
        has_unapproved_profile=False,
        value_source=None,
        has_irradiance=True,
        has_cell_temperature=True,
    )
    assert prov.status == WeatherResolverStatus.legacy_das_unverified.value
    assert prov.irradiance_plane == "unknown"
    assert prov.confidence == "unknown"
    assert SEMANTICS_UNKNOWN in prov.missing_inputs
    assert "legacy_das_unverified" in prov.warnings


def test_derive_unknown_temperature_is_not_promoted():
    prov = derive_weather_provenance(
        irr_sem=_poa_sem(chosen=_mapping(id=1, metric=IRRADIANCE_METRIC)),
        temp_sem=_unknown_sem(),
        active_profile=None,
        profile_partial_window=False,
        has_unapproved_profile=False,
        value_source=None,
        has_irradiance=True,
        has_cell_temperature=True,
    )
    assert prov.status == WeatherResolverStatus.legacy_das_unverified.value
    assert prov.temperature_type == "unknown"


def test_derive_ambient_temperature_is_not_cell_usable():
    prov = derive_weather_provenance(
        irr_sem=_poa_sem(chosen=_mapping(id=1, metric=IRRADIANCE_METRIC)),
        temp_sem=_MetricSemantics(chosen=None, value=WeatherTemperatureType.ambient.value, conflict=False),
        active_profile=None,
        profile_partial_window=False,
        has_unapproved_profile=False,
        value_source=None,
        has_irradiance=True,
        has_cell_temperature=True,
    )
    assert prov.status == WeatherResolverStatus.legacy_das_unverified.value
    assert prov.temperature_type == "unknown"


def test_derive_missing_series_keys():
    prov = derive_weather_provenance(
        irr_sem=_unknown_sem(),
        temp_sem=_cell_sem(chosen=None),
        active_profile=None,
        profile_partial_window=False,
        has_unapproved_profile=False,
        value_source=None,
        has_irradiance=False,
        has_cell_temperature=True,
    )
    assert MISSING_IRRADIANCE in prov.missing_inputs
    assert MISSING_CELL_TEMPERATURE not in prov.missing_inputs


def test_derive_no_weather_when_both_series_absent():
    prov = derive_weather_provenance(
        irr_sem=_unknown_sem(),
        temp_sem=_unknown_sem(),
        active_profile=None,
        profile_partial_window=False,
        has_unapproved_profile=False,
        value_source=None,
        has_irradiance=False,
        has_cell_temperature=False,
    )
    assert prov.status == WeatherResolverStatus.no_weather.value
    assert MISSING_IRRADIANCE in prov.missing_inputs
    assert MISSING_CELL_TEMPERATURE in prov.missing_inputs


def test_derive_profile_missing_and_unapproved():
    prov = derive_weather_provenance(
        irr_sem=_poa_sem(chosen=_mapping(id=1, metric=IRRADIANCE_METRIC)),
        temp_sem=_cell_sem(chosen=_mapping(id=2, metric=CELL_TEMPERATURE_METRIC)),
        active_profile=None,
        profile_partial_window=False,
        has_unapproved_profile=True,
        value_source=None,
        has_irradiance=True,
        has_cell_temperature=True,
    )
    assert PROFILE_MISSING in prov.missing_inputs
    assert WEATHER_SOURCE_UNAPPROVED in prov.missing_inputs
    assert prov.profile_id is None


def test_derive_below_confidence_threshold():
    src = _source(id=10, confidence=WeatherConfidence.medium)
    prov = derive_weather_provenance(
        irr_sem=_poa_sem(chosen=_mapping(id=1, metric=IRRADIANCE_METRIC, weather_source_id=10)),
        temp_sem=_cell_sem(chosen=_mapping(id=2, metric=CELL_TEMPERATURE_METRIC, weather_source_id=10)),
        active_profile=_profile(id=5, min_confidence_policy=WeatherConfidence.high),
        profile_partial_window=False,
        has_unapproved_profile=False,
        value_source=src,
        has_irradiance=True,
        has_cell_temperature=True,
    )
    assert prov.confidence == "medium"
    assert prov.min_confidence_policy == "high"
    assert BELOW_CONFIDENCE_THRESHOLD in prov.missing_inputs


# ---------------------------------------------------------------------------
# resolve_window (in-memory fakes)
# ---------------------------------------------------------------------------
def test_resolve_window_returns_existing_das_values(monkeypatch):
    _patch_resolver(
        monkeypatch,
        irr_rows=[_row(_T0, 500.0), _row(_T1, 800.0)],
        cell_rows=[_row(_T0, 95.0), _row(_T1, 104.0)],
    )
    window = WeatherResolver(db=None).resolve_window(
        site_id=1, start=_WIN_START, end=_WIN_END, bucket_size="1h"
    )
    assert set(window.buckets) == {_T0, _T1}
    assert window.buckets[_T0].irradiance_poa_wm2 == 500.0
    assert window.buckets[_T1].cell_temperature_f == 104.0
    # No mapping/profile => unverified but values present.
    assert window.provenance.status == WeatherResolverStatus.legacy_das_unverified.value


def test_resolve_window_verified_end_to_end(monkeypatch):
    src = _source(id=10, confidence=WeatherConfidence.high)
    _patch_resolver(
        monkeypatch,
        irr_rows=[_row(_T0, 600.0)],
        cell_rows=[_row(_T0, 100.0)],
        mappings=[
            _mapping(id=1, metric=IRRADIANCE_METRIC, plane=WeatherIrradiancePlane.poa, weather_source_id=10),
            _mapping(id=2, metric=CELL_TEMPERATURE_METRIC, temp=WeatherTemperatureType.cell, weather_source_id=10),
        ],
        profiles=[_profile(id=5, min_confidence_policy=WeatherConfidence.low)],
        sources=[src],
    )
    window = WeatherResolver(db=None).resolve_window(
        site_id=1, start=_WIN_START, end=_WIN_END, bucket_size="1h"
    )
    prov = window.provenance
    assert prov.status == WeatherResolverStatus.semantics_verified.value
    assert prov.irradiance_plane == "poa"
    assert prov.temperature_type == "cell"
    assert prov.confidence == "high"
    assert prov.weather_source_id == 10
    assert prov.profile_id == 5
    assert prov.source_type == WeatherSourceType.on_site_calibrated_sensor.value


def test_resolve_window_partial_mapping_stays_unverified(monkeypatch):
    # POA + cell mappings exist but only cover the back half of the window ->
    # values still pass through unchanged, but provenance must NOT be verified.
    src = _source(id=10, confidence=WeatherConfidence.high)
    _patch_resolver(
        monkeypatch,
        irr_rows=[_row(_T0, 600.0)],
        cell_rows=[_row(_T0, 100.0)],
        mappings=[
            _mapping(
                id=1,
                metric=IRRADIANCE_METRIC,
                plane=WeatherIrradiancePlane.poa,
                weather_source_id=10,
                effective_from=datetime(2026, 6, 1, 12),
            ),
            _mapping(
                id=2,
                metric=CELL_TEMPERATURE_METRIC,
                temp=WeatherTemperatureType.cell,
                weather_source_id=10,
                effective_from=datetime(2026, 6, 1, 12),
            ),
        ],
        profiles=[_profile(id=5)],
        sources=[src],
    )
    window = WeatherResolver(db=None).resolve_window(
        site_id=1, start=_WIN_START, end=_WIN_END, bucket_size="1h"
    )
    # Values are unchanged (numbers never depend on provenance).
    assert window.buckets[_T0].irradiance_poa_wm2 == 600.0
    assert window.buckets[_T0].cell_temperature_f == 100.0
    # But provenance is honest: unverified, semantics unknown, confidence unknown.
    prov = window.provenance
    assert prov.status == WeatherResolverStatus.legacy_das_unverified.value
    assert prov.irradiance_plane == "unknown"
    assert prov.temperature_type == "unknown"
    assert prov.confidence == "unknown"
    assert SEMANTICS_UNKNOWN in prov.missing_inputs


def test_resolve_window_uses_only_read_methods(monkeypatch):
    calls: list[str] = []
    _patch_resolver(
        monkeypatch,
        irr_rows=[_row(_T0, 600.0)],
        cell_rows=[_row(_T0, 100.0)],
        calls=calls,
    )

    class _ExplodingSession:
        def __getattr__(self, name):
            raise AssertionError(f"resolver touched session.{name} (must be read-only)")

    WeatherResolver(db=_ExplodingSession()).resolve_window(
        site_id=1, start=_WIN_START, end=_WIN_END, bucket_size="1h"
    )
    assert set(calls) <= {"get_series", "list_for_site", "get"}


# ---------------------------------------------------------------------------
# Numeric invariance — the heart of the W1 contract
# ---------------------------------------------------------------------------
def _baseline():
    return SimpleNamespace(
        id=42,
        baseline_type="weather_adjusted",
        module_wattage=400.0,
        module_quantity=1000.0,
        inverter_wattage=300000.0,
        inverter_quantity=1.0,
        thermal_coefficient_pct=-0.35,
        power_tolerance_min_pct=0.0,
        year_1_degradation_pct=2.0,
        annual_degradation_pct=0.5,
        cec_efficiency_pct=98.0,
        soiling_factor=1.0,
        dc_loss_pct=2.0,
        ac_loss_pct=1.0,
        medium_voltage_loss_pct=0.0,
        mv_line_loss_pct=0.0,
        pto_date=datetime(2024, 1, 1).date(),
        timezone="UTC",
    )


class _FakeResolver:
    def __init__(self, window):
        self._window = window

    def resolve_window(self, *, site_id, start, end, bucket_size):
        return self._window


def test_compute_site_expected_numbers_identical_to_pure_core(monkeypatch):
    power_rows = [_row(_T0, 250.0), _row(_T1, 280.0), _row(_T2, 0.0)]

    class FakePowerCRUD:
        def __init__(self, db):
            pass

        def get_series(self, *, site_id, normalized_metric, bucket_size, start, end):
            if normalized_metric == es.SITE_POWER_METRIC:
                return power_rows
            return []

    monkeypatch.setattr(es, "TelemetrySiteRollupCRUD", FakePowerCRUD)

    # Resolver returns weather for two of the three power buckets (T2 has no weather).
    buckets = {
        _T0: ResolvedWeatherBucket(_T0, 500.0, 95.0),
        _T1: ResolvedWeatherBucket(_T1, 800.0, 104.0),
    }
    provenance = ResolvedWeatherProvenance(
        status="legacy_das_unverified",
        source_type="das_provider_stream",
        source_label="x",
        is_modeled=False,
        confidence="unknown",
        irradiance_plane="unknown",
        temperature_type="unknown",
        calibration_status="unknown",
    )
    window = ResolvedWeatherWindow(buckets=buckets, provenance=provenance)
    baseline = _baseline()
    site = SimpleNamespace(id=1)

    result = compute_site_expected(
        db=None,
        site=site,
        baseline=baseline,
        start=_WIN_START,
        end=_WIN_END,
        bucket_size="1h",
        weather_resolver=_FakeResolver(window),
    )

    # Independently compute over the identical union of buckets/values.
    power_map = {r.bucket_start: float(r.value) for r in power_rows}
    bucket_starts = sorted(set(power_map) | set(buckets))
    inputs = [
        BucketInput(
            bucket_start=bs,
            irradiance_wm2=buckets[bs].irradiance_poa_wm2 if bs in buckets else None,
            cell_temperature_f=buckets[bs].cell_temperature_f if bs in buckets else None,
            actual_power_kw=power_map.get(bs),
        )
        for bs in bucket_starts
    ]
    expected = compute_expected_buckets(
        BaselineParams.from_baseline(baseline), inputs, BUCKET_SIZE_TO_HOURS["1h"]
    )

    assert result.overall_status == OverallStatus.ok
    assert [b.bucket_start for b in result.buckets] == [b.bucket_start for b in expected]
    for got, exp in zip(result.buckets, expected):
        assert got.status == exp.status
        assert got.expected_power_kw == exp.expected_power_kw
        assert got.expected_energy_kwh == exp.expected_energy_kwh
        assert got.actual_power_kw == exp.actual_power_kw
        assert got.irradiance_wm2 == exp.irradiance_wm2
        assert got.cell_temperature_f == exp.cell_temperature_f
    # Provenance is attached, not influencing the numbers.
    assert result.weather_provenance is provenance


def test_compute_site_expected_defaults_to_db_resolver(monkeypatch):
    """When no resolver is injected, a DB-backed WeatherResolver is constructed."""
    power_rows = [_row(_T0, 250.0)]

    class FakePowerCRUD:
        def __init__(self, db):
            pass

        def get_series(self, *, site_id, normalized_metric, bucket_size, start, end):
            if normalized_metric == es.SITE_POWER_METRIC:
                return power_rows
            return []

    monkeypatch.setattr(es, "TelemetrySiteRollupCRUD", FakePowerCRUD)

    sentinel_provenance = ResolvedWeatherProvenance(
        status="legacy_das_unverified",
        source_type="das_provider_stream",
        source_label="x",
        is_modeled=False,
        confidence="unknown",
        irradiance_plane="unknown",
        temperature_type="unknown",
        calibration_status="unknown",
    )
    constructed = {}

    class FakeResolverClass:
        def __init__(self, db):
            constructed["db"] = db

        def resolve_window(self, *, site_id, start, end, bucket_size):
            return ResolvedWeatherWindow(
                buckets={_T0: ResolvedWeatherBucket(_T0, 500.0, 95.0)},
                provenance=sentinel_provenance,
            )

    monkeypatch.setattr(es, "WeatherResolver", FakeResolverClass)

    result = compute_site_expected(
        db="DB_HANDLE",
        site=SimpleNamespace(id=1),
        baseline=_baseline(),
        start=_WIN_START,
        end=_WIN_END,
        bucket_size="1h",
    )
    assert constructed["db"] == "DB_HANDLE"
    assert result.weather_provenance is sentinel_provenance


def test_baseline_none_has_no_weather_provenance(monkeypatch):
    result = compute_site_expected(
        db=None,
        site=SimpleNamespace(id=1),
        baseline=None,
        start=_WIN_START,
        end=_WIN_END,
        bucket_size="1h",
    )
    assert result.overall_status == OverallStatus.baseline_not_available
    assert result.weather_provenance is None


# ---------------------------------------------------------------------------
# Static guarantees: no external/BigQuery/Firestore/secret dependencies
# ---------------------------------------------------------------------------
def test_resolver_module_has_no_external_dependencies():
    """Inspect ACTUAL import statements (not docstring prose) for forbidden deps."""
    tree = ast.parse(pathlib.Path(wr.__file__).read_text())
    imported: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            imported.append(node.module or "")
    blob = " ".join(imported).lower()
    for forbidden in (
        "bigquery",
        "firestore",
        "google",
        "secretmanager",
        "requests",
        "httpx",
        "boto3",
        "legacy",
    ):
        assert forbidden not in blob, f"resolver must not import {forbidden!r}"
