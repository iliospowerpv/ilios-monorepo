"""Native weather-adjusted expected-performance calculation (Phase P3.2).

This is the in-app replacement for the legacy BigQuery table function
``platform_<env>.site_power_actual_vs_expected`` (see
``backend/rea-telemetry/.../templates/platform/site_power_actual_vs_expected.sql.jinja2``).
It reads ONLY V2 PostgreSQL interval rollups + an approved baseline snapshot;
nothing here touches BigQuery, Firestore, or the rea-telemetry pipeline.

The physics is ported EXACTLY from the legacy template. Per bucket:

    dc_nameplate_kw   = module_wattage * module_quantity / 1000
    ac_nameplate_kw   = inverter_wattage * inverter_quantity
    dc_voltage_drop   = 1 - dc_loss_pct/100
    ac_voltage_drop   = 1 - (ac_loss_pct + medium_voltage_loss_pct + mv_line_loss_pct)/100
    power_tolerance   = 1 + power_tolerance_min_pct/100
    inverter_eff      = cec_efficiency_pct/100
    thermal_coeff     = thermal_coefficient_pct/100
    irradiance_factor = irradiance_wm2 / 1000
    cell_temp_c       = (cell_temperature_f - 32) / 1.8
    temperature_factor= 1 + thermal_coeff*(cell_temp_c - 25)
    age (years)       = from PTO, using the SITE-LOCAL calendar date of the bucket
    age_factor        = 1 - (yr1_frac*[age>=1] + annual_frac*[age>=2]*(age-1))
    system_derate     = power_tolerance * soiling * age_factor * dc_vd * inv_eff * ac_vd
    total_derate      = system_derate * irradiance_factor * temperature_factor
    expected_power_kw = min(dc_nameplate_kw * total_derate, ac_nameplate_kw)

Honesty contract (never fabricate):

* No baseline at all          -> overall ``baseline_not_available`` (no buckets).
* PTO null, or bucket before PTO -> bucket ``pre_pto``        (expected = NULL).
* Irradiance OR cell-temp absent for a bucket -> ``missing_inputs`` (expected = NULL,
  mirroring the legacy INNER JOIN of irradiance + cell temperature).
* Otherwise                   -> ``ok`` with a computed expected_power_kw.

Buckets are taken from the union of rollup buckets actually present in the
window (the calc never invents buckets and never zero-fills a missing input).
Actual power is independent (legacy LEFT-joins it) and may be ``None`` on an
``ok``/``missing_inputs`` bucket.

Percent-valued baseline columns are stored AS PERCENT and divided by 100 here
exactly once. Loss columns are sign-normalized to positive percent at baseline
creation (the legacy formula subtracts a positive %).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.crud.telemetry_native import TelemetrySiteRollupCRUD
from app.services.weather.weather_resolver import (
    ResolvedWeatherProvenance,
    WeatherResolver,
)

logger = logging.getLogger(__name__)

# Normalized metric keys (must match the telemetry_metric_catalog seed).
SITE_POWER_METRIC = "site_power_ac_kw"
IRRADIANCE_METRIC = "irradiance_wm2"
CELL_TEMPERATURE_METRIC = "cell_temperature_f"

# bucket_size -> hours per bucket (mirrors rollup_service._BUCKET_SIZES).
BUCKET_SIZE_TO_HOURS: dict[str, float] = {
    "15m": 0.25,
    "30m": 0.5,
    "1h": 1.0,
    "1d": 24.0,
}

# Standard test condition baselines (legacy constants).
IRRADIANCE_BASELINE_WM2 = 1000.0
CELL_TEMPERATURE_BASELINE_C = 25.0

# Physics parameters that MUST be present for a weather-adjusted calc.
REQUIRED_PHYSICS_FIELDS = (
    "module_wattage",
    "module_quantity",
    "inverter_wattage",
    "inverter_quantity",
    "thermal_coefficient_pct",
    "power_tolerance_min_pct",
    "year_1_degradation_pct",
    "annual_degradation_pct",
    "cec_efficiency_pct",
)


class BucketStatus(str, Enum):
    ok = "ok"
    missing_inputs = "missing_inputs"
    pre_pto = "pre_pto"


class OverallStatus(str, Enum):
    ok = "ok"
    baseline_not_available = "baseline_not_available"


class ExpectedState(str, Enum):
    """User-facing summary of an expected-calc result over a window.

    Additive metadata the O&M/company views expose alongside (not instead of)
    the existing ``expected_baseline_available`` boolean, so the frontend can
    tell apart fully-available, partial, and the distinct missing reasons.
    """

    available = "available"  # a baseline exists and every bucket computed (all ``ok``)
    partial = "partial"  # a baseline exists but only some buckets computed
    missing_inputs = "missing_inputs"  # baseline exists, no ``ok`` bucket; inputs absent
    pre_pto = "pre_pto"  # baseline exists, no ``ok`` bucket; window is before PTO
    baseline_not_available = "baseline_not_available"  # no approved/active baseline


@dataclass(frozen=True)
class BaselineParams:
    """Immutable physics snapshot consumed by the pure calc core.

    All ``*_pct`` values are PERCENT (divided by 100 in the calc, exactly once).
    Loss values must already be sign-normalized to positive percent.
    """

    module_wattage: float
    module_quantity: float
    inverter_wattage: float
    inverter_quantity: float
    thermal_coefficient_pct: float
    power_tolerance_min_pct: float
    year_1_degradation_pct: float
    annual_degradation_pct: float
    cec_efficiency_pct: float
    soiling_factor: float = 1.0
    dc_loss_pct: float = 0.0
    ac_loss_pct: float = 0.0
    medium_voltage_loss_pct: float = 0.0
    mv_line_loss_pct: float = 0.0
    pto_date: Optional[date] = None
    timezone: str = "UTC"

    @classmethod
    def from_baseline(cls, baseline) -> "BaselineParams":
        """Build params from a ``TelemetryExpectedBaseline`` row.

        Raises ``ValueError`` if a required physics parameter is missing — a
        weather-adjusted baseline must be fully specified before it can compute.
        """
        missing = [
            name
            for name in REQUIRED_PHYSICS_FIELDS
            if getattr(baseline, name, None) is None
        ]
        if missing:
            raise ValueError(
                f"Baseline {getattr(baseline, 'id', '?')} is missing required "
                f"physics parameters: {', '.join(missing)}"
            )

        def _f(name: str, default: Optional[float] = None) -> Optional[float]:
            value = getattr(baseline, name, None)
            return default if value is None else float(value)

        return cls(
            module_wattage=_f("module_wattage"),
            module_quantity=_f("module_quantity"),
            inverter_wattage=_f("inverter_wattage"),
            inverter_quantity=_f("inverter_quantity"),
            thermal_coefficient_pct=_f("thermal_coefficient_pct"),
            power_tolerance_min_pct=_f("power_tolerance_min_pct"),
            year_1_degradation_pct=_f("year_1_degradation_pct"),
            annual_degradation_pct=_f("annual_degradation_pct"),
            cec_efficiency_pct=_f("cec_efficiency_pct"),
            soiling_factor=_f("soiling_factor", 1.0),
            dc_loss_pct=_f("dc_loss_pct", 0.0),
            ac_loss_pct=_f("ac_loss_pct", 0.0),
            medium_voltage_loss_pct=_f("medium_voltage_loss_pct", 0.0),
            mv_line_loss_pct=_f("mv_line_loss_pct", 0.0),
            pto_date=getattr(baseline, "pto_date", None),
            timezone=getattr(baseline, "timezone", None) or "UTC",
        )


@dataclass(frozen=True)
class BucketInput:
    """One aligned rollup bucket fed to the pure calc. ``bucket_start`` is naive-UTC."""

    bucket_start: datetime
    irradiance_wm2: Optional[float]
    cell_temperature_f: Optional[float]
    actual_power_kw: Optional[float]


@dataclass
class ExpectedBucket:
    """Per-bucket calc output."""

    bucket_start: datetime
    status: BucketStatus
    expected_power_kw: Optional[float]
    expected_energy_kwh: Optional[float]
    actual_power_kw: Optional[float]
    irradiance_wm2: Optional[float]
    cell_temperature_f: Optional[float]
    age_years: Optional[int]


@dataclass
class ExpectedResult:
    """Whole-window calc result."""

    overall_status: OverallStatus
    baseline_id: Optional[int]
    baseline_type: Optional[str]
    bucket_size: str
    window_start: datetime
    window_end: datetime
    buckets: list[ExpectedBucket]
    expected_energy_kwh: Optional[float]
    actual_energy_kwh: Optional[float]
    ok_bucket_count: int
    missing_inputs_bucket_count: int
    pre_pto_bucket_count: int
    # Additive (W1): provenance describing what weather drove this computation.
    # ``None`` when no baseline was available (no weather was resolved) — the
    # field defaults at the end so existing constructors stay valid.
    weather_provenance: Optional[ResolvedWeatherProvenance] = None


# ---------------------------------------------------------------------------
# Pure calc core (no DB, fully unit-testable)
# ---------------------------------------------------------------------------


def _site_local_date(bucket_start_utc: datetime, tz_name: str) -> date:
    """Convert a naive-UTC bucket start to its calendar date in the site tz.

    Falls back to UTC (with a warning) on a missing/invalid timezone, matching
    the V2 "today" boundary helper.
    """
    try:
        tz = ZoneInfo(tz_name)
    except Exception:  # noqa: BLE001 - unknown/invalid IANA name
        logger.warning(
            "expected_calc_invalid_timezone tz=%r falling_back=UTC", tz_name
        )
        tz = timezone.utc
    aware = bucket_start_utc.replace(tzinfo=timezone.utc)
    return aware.astimezone(tz).date()


def _age_years(local_d: date, pto: date) -> int:
    """Whole-year age of the system at ``local_d`` relative to ``pto``.

    Ported from the legacy YEAR-diff minus a 1-year correction when the bucket's
    month/day precedes the PTO month/day. Only called when ``local_d >= pto``,
    so the result is always >= 0.
    """
    age = local_d.year - pto.year
    if (local_d.month, local_d.day) < (pto.month, pto.day):
        age -= 1
    return age


def _expected_power_kw(
    params: BaselineParams, irradiance_wm2: float, cell_temperature_f: float, age: int
) -> float:
    dc_nameplate_kw = params.module_wattage * params.module_quantity / 1000.0
    ac_nameplate_kw = params.inverter_wattage * params.inverter_quantity

    dc_voltage_drop = 1.0 - params.dc_loss_pct / 100.0
    ac_voltage_drop = 1.0 - (
        params.ac_loss_pct + params.medium_voltage_loss_pct + params.mv_line_loss_pct
    ) / 100.0
    power_tolerance = 1.0 + params.power_tolerance_min_pct / 100.0
    inverter_efficiency = params.cec_efficiency_pct / 100.0
    thermal_coefficient = params.thermal_coefficient_pct / 100.0
    year_1_frac = params.year_1_degradation_pct / 100.0
    annual_frac = params.annual_degradation_pct / 100.0

    age_factor = 1.0 - (
        year_1_frac * (1 if age >= 1 else 0)
        + annual_frac * ((age - 1) if age >= 2 else 0)
    )
    system_derate = (
        power_tolerance
        * params.soiling_factor
        * age_factor
        * dc_voltage_drop
        * inverter_efficiency
        * ac_voltage_drop
    )

    irradiance_factor = irradiance_wm2 / IRRADIANCE_BASELINE_WM2
    cell_temperature_c = (cell_temperature_f - 32.0) / 1.8
    temperature_factor = 1.0 + thermal_coefficient * (
        cell_temperature_c - CELL_TEMPERATURE_BASELINE_C
    )

    total_derate = system_derate * irradiance_factor * temperature_factor
    expected = dc_nameplate_kw * total_derate
    # Legacy MIN clip: expected power can never exceed AC nameplate.
    return ac_nameplate_kw if expected > ac_nameplate_kw else expected


def compute_expected_buckets(
    params: BaselineParams, buckets: list[BucketInput], bucket_hours: float
) -> list[ExpectedBucket]:
    """Pure port of the legacy physics over a list of aligned buckets."""
    results: list[ExpectedBucket] = []
    for b in buckets:
        if params.pto_date is None:
            results.append(
                ExpectedBucket(
                    bucket_start=b.bucket_start,
                    status=BucketStatus.pre_pto,
                    expected_power_kw=None,
                    expected_energy_kwh=None,
                    actual_power_kw=b.actual_power_kw,
                    irradiance_wm2=b.irradiance_wm2,
                    cell_temperature_f=b.cell_temperature_f,
                    age_years=None,
                )
            )
            continue

        local_d = _site_local_date(b.bucket_start, params.timezone)
        if local_d < params.pto_date:
            results.append(
                ExpectedBucket(
                    bucket_start=b.bucket_start,
                    status=BucketStatus.pre_pto,
                    expected_power_kw=None,
                    expected_energy_kwh=None,
                    actual_power_kw=b.actual_power_kw,
                    irradiance_wm2=b.irradiance_wm2,
                    cell_temperature_f=b.cell_temperature_f,
                    age_years=None,
                )
            )
            continue

        if b.irradiance_wm2 is None or b.cell_temperature_f is None:
            results.append(
                ExpectedBucket(
                    bucket_start=b.bucket_start,
                    status=BucketStatus.missing_inputs,
                    expected_power_kw=None,
                    expected_energy_kwh=None,
                    actual_power_kw=b.actual_power_kw,
                    irradiance_wm2=b.irradiance_wm2,
                    cell_temperature_f=b.cell_temperature_f,
                    age_years=None,
                )
            )
            continue

        age = _age_years(local_d, params.pto_date)
        power = _expected_power_kw(
            params, b.irradiance_wm2, b.cell_temperature_f, age
        )
        results.append(
            ExpectedBucket(
                bucket_start=b.bucket_start,
                status=BucketStatus.ok,
                expected_power_kw=power,
                expected_energy_kwh=power * bucket_hours,
                actual_power_kw=b.actual_power_kw,
                irradiance_wm2=b.irradiance_wm2,
                cell_temperature_f=b.cell_temperature_f,
                age_years=age,
            )
        )
    return results


# ---------------------------------------------------------------------------
# DB wrapper
# ---------------------------------------------------------------------------


def compute_site_expected(
    db: Session,
    *,
    site,
    baseline,
    start: datetime,
    end: datetime,
    bucket_size: str = "1h",
    weather_resolver: Optional[WeatherResolver] = None,
) -> ExpectedResult:
    """Compute weather-adjusted expected vs. actual for one site + window.

    ``baseline`` is a ``TelemetryExpectedBaseline`` row (or ``None``). When it is
    ``None`` the result is ``baseline_not_available`` with no buckets — the calc
    never fabricates an expected line without an approved baseline.

    The weather physics inputs (irradiance + cell temperature) are resolved
    through the read-only :class:`WeatherResolver` (W1), which reads the SAME V2
    rollups as before and returns identical values — so the expected numbers are
    unchanged — while additionally attaching ``weather_provenance``. Pass a
    ``weather_resolver`` to inject a stub in tests; it defaults to a DB-backed
    resolver bound to ``db``.
    """
    if baseline is None:
        return ExpectedResult(
            overall_status=OverallStatus.baseline_not_available,
            baseline_id=None,
            baseline_type=None,
            bucket_size=bucket_size,
            window_start=start,
            window_end=end,
            buckets=[],
            expected_energy_kwh=None,
            actual_energy_kwh=None,
            ok_bucket_count=0,
            missing_inputs_bucket_count=0,
            pre_pto_bucket_count=0,
            weather_provenance=None,
        )

    crud = TelemetrySiteRollupCRUD(db)
    power_rows = crud.get_series(
        site_id=site.id,
        normalized_metric=SITE_POWER_METRIC,
        bucket_size=bucket_size,
        start=start,
        end=end,
    )

    power_map = {r.bucket_start: float(r.value) for r in power_rows}

    # Resolve the weather physics inputs through the W1 resolver. It reads the
    # same irradiance/cell-temp rollups as the legacy direct reads and returns
    # identical float values (no transposition/conversion), so the numbers below
    # are unchanged; it additionally carries provenance.
    resolver = weather_resolver or WeatherResolver(db)
    resolved = resolver.resolve_window(
        site_id=site.id,
        start=start,
        end=end,
        bucket_size=bucket_size,
    )

    # Union of buckets actually present — never invent buckets, never zero-fill.
    bucket_starts = sorted(set(power_map) | set(resolved.buckets))
    bucket_inputs = []
    for bs in bucket_starts:
        weather = resolved.buckets.get(bs)
        bucket_inputs.append(
            BucketInput(
                bucket_start=bs,
                irradiance_wm2=weather.irradiance_poa_wm2 if weather else None,
                cell_temperature_f=weather.cell_temperature_f if weather else None,
                actual_power_kw=power_map.get(bs),
            )
        )

    bucket_hours = BUCKET_SIZE_TO_HOURS.get(bucket_size, 1.0)
    params = BaselineParams.from_baseline(baseline)
    buckets = compute_expected_buckets(params, bucket_inputs, bucket_hours)

    ok_buckets = [b for b in buckets if b.status == BucketStatus.ok]
    actual_buckets = [b for b in buckets if b.actual_power_kw is not None]
    expected_energy = (
        sum(b.expected_energy_kwh for b in ok_buckets) if ok_buckets else None
    )
    actual_energy = (
        sum(b.actual_power_kw * bucket_hours for b in actual_buckets)
        if actual_buckets
        else None
    )

    return ExpectedResult(
        overall_status=OverallStatus.ok,
        baseline_id=baseline.id,
        baseline_type=(
            baseline.baseline_type.value
            if hasattr(baseline.baseline_type, "value")
            else baseline.baseline_type
        ),
        bucket_size=bucket_size,
        window_start=start,
        window_end=end,
        buckets=buckets,
        expected_energy_kwh=expected_energy,
        actual_energy_kwh=actual_energy,
        ok_bucket_count=len(ok_buckets),
        missing_inputs_bucket_count=sum(
            1 for b in buckets if b.status == BucketStatus.missing_inputs
        ),
        pre_pto_bucket_count=sum(
            1 for b in buckets if b.status == BucketStatus.pre_pto
        ),
        weather_provenance=resolved.provenance,
    )


def derive_expected_state(result: ExpectedResult) -> ExpectedState:
    """Summarize an :class:`ExpectedResult` into a user-facing ``ExpectedState``.

    Never fabricates: a result with no approved baseline is
    ``baseline_not_available``; a baseline present but no telemetry buckets in the
    window (so nothing could be computed) is ``missing_inputs``; all buckets
    computed is ``available``; a mix is ``partial``; and when nothing computed but
    buckets exist, the dominant failure reason (missing inputs vs pre-PTO) wins.
    """
    if result.overall_status == OverallStatus.baseline_not_available:
        return ExpectedState.baseline_not_available
    total = len(result.buckets)
    if total == 0:
        # Baseline exists but the window has no rollup buckets at all (e.g. night
        # or no telemetry yet): expected could not be computed for lack of inputs.
        return ExpectedState.missing_inputs
    if result.ok_bucket_count == total:
        return ExpectedState.available
    if result.ok_bucket_count > 0:
        return ExpectedState.partial
    # No bucket computed: surface the dominant reason so the UI shows the right
    # honest N/A ("Missing inputs" vs "Pre-PTO") rather than a generic blank.
    if result.missing_inputs_bucket_count >= result.pre_pto_bucket_count:
        return ExpectedState.missing_inputs
    return ExpectedState.pre_pto
