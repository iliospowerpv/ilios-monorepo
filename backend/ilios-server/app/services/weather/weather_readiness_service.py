"""W2 readiness — can a window be honestly replayed from historical weather?

Given a site + window + bucket size, this service reports how much *physics-usable*
historical weather (POA irradiance + cell/module/modeled_cell temperature) exists
over the rollup bucket grid, what is missing, and whether an approved historical
profile governs the window. It is READ-ONLY and additive: it computes coverage
without changing the expected math, the resolver, telemetry, or O&M.

The denominator is the epoch-anchored expected-bucket grid (the same grid the
rollups/expected calc use), so ``coverage_pct`` is an honest fraction rather than
a guess. Non-usable observations (GHI/ambient/unknown) are disclosed as
"unknown semantics present", never converted or counted as usable.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.crud.weather import WeatherObservationCRUD, WeatherSourceProfileCRUD
from app.models.weather import WeatherConfidence, WeatherSourceProfileRole
from app.schema.weather import WeatherGapRange, WeatherReadinessResponse
from app.services.weather.bucketing import (
    bucket_observations,
    expected_bucket_starts,
    min_confidence,
)
from app.services.weather.weather_resolver import (
    CELL_TEMPERATURE_METRIC,
    IRRADIANCE_METRIC,
    _enum_value,
    _select_active_profile,
)

# Default coverage floor for declaring a window replay-ready. Full coverage is
# the conservative/honest default; callers may relax it per use case.
DEFAULT_MIN_COVERAGE_PCT = 1.0

# Blocking-reason / indicator keys (glossary keys the FE renders as "why" tips).
REASON_PROFILE_MISSING = "historical_profile_missing"
REASON_PROFILE_UNAPPROVED = "historical_profile_unapproved"
REASON_PROFILE_PARTIAL = "historical_profile_partial_window"
REASON_NO_USABLE_IRRADIANCE = "no_usable_irradiance"
REASON_NO_USABLE_CELL_TEMPERATURE = "no_usable_cell_temperature"
REASON_INSUFFICIENT_COVERAGE = "insufficient_coverage"
REASON_NO_EXPECTED_BUCKETS = "no_expected_buckets"

IND_UNKNOWN_SEMANTICS_PRESENT = "unknown_semantics_present"
IND_MODELED_WEATHER_PRESENT = "modeled_weather_present"
IND_COVERAGE_GAPS_PRESENT = "coverage_gaps_present"
IND_READY_FOR_REPLAY = "ready_for_expected_replay"


def _select_active_historical_profile(profiles: list, start: datetime, end: datetime):
    """Pick the governing ACTIVE ``role=historical`` profile for the window.

    Filters to historical-role profiles first, then reuses the resolver's
    selection (prefers a covering active profile, else an overlapping one flagged
    partial). Returns ``(profile_or_None, partial, has_unapproved_historical)``.
    """
    historical = [
        p
        for p in profiles
        if _enum_value(p.role) == WeatherSourceProfileRole.historical.value
    ]
    return _select_active_profile(historical, start, end)


def compute_weather_readiness(
    db: Session,
    *,
    site_id: int,
    start: datetime,
    end: datetime,
    bucket_size: str = "1h",
    min_coverage_pct: float = DEFAULT_MIN_COVERAGE_PCT,
) -> WeatherReadinessResponse:
    """Compute historical-weather replay readiness for a site window (read-only)."""
    profiles = WeatherSourceProfileCRUD(db).list_for_site(site_id)
    active_profile, partial_window, has_unapproved = _select_active_historical_profile(
        profiles, start, end
    )

    # When a profile governs the window, scope to its source; otherwise report on
    # all historical observations available for the site.
    source_id = active_profile.weather_source_id if active_profile else None
    observations = WeatherObservationCRUD(db).get_window(
        site_id,
        start=start,
        end=end,
        metrics=[IRRADIANCE_METRIC, CELL_TEMPERATURE_METRIC],
        weather_source_id=source_id,
    )

    bucketed = bucket_observations(
        observations,
        bucket_size=bucket_size,
        irradiance_metric=IRRADIANCE_METRIC,
        cell_temperature_metric=CELL_TEMPERATURE_METRIC,
    )

    grid = expected_bucket_starts(start, end, bucket_size)
    total = len(grid)

    irr_usable = 0
    temp_usable = 0
    both_usable = 0
    unknown_semantics = 0
    modeled_usable = 0
    confidence_summary: dict[str, int] = {}
    gap_flags: list[bool] = []  # True = this grid bucket is a replay gap

    for bs in grid:
        agg = bucketed.buckets.get(bs)
        has_irr = agg is not None and agg.irradiance_poa_wm2 is not None
        has_temp = agg is not None and agg.cell_temperature_f is not None
        if has_irr:
            irr_usable += 1
        if has_temp:
            temp_usable += 1
        if has_irr and has_temp:
            both_usable += 1
        gap_flags.append(not (has_irr and has_temp))

        if agg is not None and (
            agg.had_unusable_irradiance or agg.had_unusable_cell_temperature
        ):
            unknown_semantics += 1

        modeled = (has_irr and agg.irradiance_modeled) or (
            has_temp and agg.cell_temperature_modeled
        )
        if modeled:
            modeled_usable += 1

        if has_irr or has_temp:
            band = min_confidence(
                [
                    agg.irradiance_confidence if has_irr else None,
                    agg.cell_temperature_confidence if has_temp else None,
                ]
            ) or WeatherConfidence.unknown.value
            confidence_summary[band] = confidence_summary.get(band, 0) + 1

    missing_irr = total - irr_usable
    missing_temp = total - temp_usable

    def _pct(n: int) -> float:
        return round(n / total, 4) if total else 0.0

    coverage_pct = _pct(both_usable)
    gap_ranges = _build_gap_ranges(grid, gap_flags, bucket_size)

    # Blocking reasons → not replay-ready unless all clear.
    blocking: list[str] = []
    if active_profile is None:
        blocking.append(REASON_PROFILE_MISSING)
    elif partial_window:
        blocking.append(REASON_PROFILE_PARTIAL)
    if total == 0:
        blocking.append(REASON_NO_EXPECTED_BUCKETS)
    if irr_usable == 0:
        blocking.append(REASON_NO_USABLE_IRRADIANCE)
    if temp_usable == 0:
        blocking.append(REASON_NO_USABLE_CELL_TEMPERATURE)
    if total > 0 and coverage_pct < min_coverage_pct:
        blocking.append(REASON_INSUFFICIENT_COVERAGE)

    ready = not blocking

    indicators = list(blocking)
    if active_profile is None and has_unapproved:
        indicators.append(REASON_PROFILE_UNAPPROVED)
    if unknown_semantics > 0:
        indicators.append(IND_UNKNOWN_SEMANTICS_PRESENT)
    if modeled_usable > 0:
        indicators.append(IND_MODELED_WEATHER_PRESENT)
    if gap_ranges:
        indicators.append(IND_COVERAGE_GAPS_PRESENT)
    if ready:
        indicators.append(IND_READY_FOR_REPLAY)

    warnings: list[str] = []
    if partial_window:
        warnings.append(REASON_PROFILE_PARTIAL)

    return WeatherReadinessResponse(
        site_id=site_id,
        window_start=start,
        window_end=end,
        bucket_size=bucket_size,
        role=WeatherSourceProfileRole.historical.value,
        has_active_historical_profile=active_profile is not None,
        profile_id=active_profile.id if active_profile else None,
        profile_partial_window=partial_window,
        total_expected_buckets=total,
        irradiance_usable_buckets=irr_usable,
        cell_temperature_usable_buckets=temp_usable,
        both_usable_buckets=both_usable,
        missing_irradiance_buckets=missing_irr,
        missing_cell_temperature_buckets=missing_temp,
        unknown_semantics_buckets=unknown_semantics,
        coverage_pct=coverage_pct,
        irradiance_coverage_pct=_pct(irr_usable),
        cell_temperature_coverage_pct=_pct(temp_usable),
        modeled_usable_buckets=modeled_usable,
        confidence_summary=confidence_summary,
        gap_ranges=gap_ranges,
        ready_for_expected_replay=ready,
        blocking_reasons=_dedupe(blocking),
        indicators=_dedupe(indicators),
        warnings=_dedupe(warnings),
    )


def _build_gap_ranges(
    grid: list[datetime], gap_flags: list[bool], bucket_size: str
) -> list[WeatherGapRange]:
    """Collapse consecutive replay-gap buckets into contiguous ranges.

    A "gap" bucket is one that cannot produce an expected value because it is
    missing at least one usable physics input. ``end`` is the exclusive end of
    the run (last gap bucket start + one bucket width).
    """
    from app.services.weather.bucketing import BUCKET_SIZES

    size = BUCKET_SIZES[bucket_size]
    ranges: list[WeatherGapRange] = []
    run_start_idx: Optional[int] = None
    for i, is_gap in enumerate(gap_flags):
        if is_gap and run_start_idx is None:
            run_start_idx = i
        if (not is_gap or i == len(gap_flags) - 1) and run_start_idx is not None:
            last_idx = i if is_gap else i - 1
            ranges.append(
                WeatherGapRange(
                    start=grid[run_start_idx],
                    end=grid[last_idx] + size,
                    bucket_count=last_idx - run_start_idx + 1,
                )
            )
            run_start_idx = None
    return ranges


def _dedupe(items: list[str]) -> list[str]:
    seen: dict[str, None] = {}
    for it in items:
        seen.setdefault(it, None)
    return list(seen.keys())
