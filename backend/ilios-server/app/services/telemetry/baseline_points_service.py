"""DD V2 Phase 3 — design-estimate baseline POINTS producer.

Builds :class:`TelemetryExpectedBaselinePoint` rows (monthly + annual granularity)
from a site's ACTIVE / human-promoted PVsyst design-estimate ``project_facts`` and
attaches them to an EXISTING ``draft`` / ``in_review`` ``design_estimate`` baseline.
The producer is deliberately conservative and never blurs the two distinct
"expected" notions the model documents:

* It writes ``design_estimate`` points ONLY (monthly + annual today; the wide point
  table is hourly/interval ready, but those granularities are NOT produced here).
* It NEVER touches the weather-adjusted model. That curve is computed on read from
  the header physics snapshot + live telemetry and never consults this table, so
  adding design points cannot perturb the live actual-vs-expected calc.
* It NEVER fabricates a missing month and NEVER distributes an annual total into
  months — absent months are simply not produced (a warning is surfaced).
* It NEVER auto-converts units. PVsyst monthly/annual production facts carry no
  unit in their field name; the value is stored as-extracted into
  ``expected_energy_kwh`` (assumed kWh, ``unit_verified=False``) with a plausibility
  warning when the magnitude looks like MWh.
* It NEVER mutates an ``approved`` / ``active`` / ``superseded`` baseline (the
  endpoint guards the status); a rebuild deletes + re-inserts a baseline's
  monthly/annual points in one transaction so a failure can never leave the
  baseline with half its curve.

GHI insolation (kWh/m²/period) does not match the instantaneous ``irradiance_wm2``
column, and the single-value point row cannot represent P50/P90 scenarios; those
are recorded in the header ``model_parameters_json["design_points"]`` provenance
block instead, with a ``schema_expansion_recommended`` hint.
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field as dc_field
from datetime import datetime, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session

from app.crud.project_fact import ProjectFactCRUD
from app.crud.telemetry_expected import TelemetryExpectedBaselinePointCRUD
from app.models.file import File
from app.models.telemetry_expected import (
    TelemetryBaselineGranularity,
    TelemetryBaselineStatus,
    TelemetryBaselineType,
    TelemetryExpectedBaseline,
    TelemetryExpectedBaselinePoint,
)

logger = logging.getLogger(__name__)

# Statuses on which a design-estimate curve may be (re)built. Approved / active /
# superseded baselines are immutable — their curve is frozen at activation.
_MUTABLE_STATUSES = (
    TelemetryBaselineStatus.draft,
    TelemetryBaselineStatus.in_review,
)

# Short token stamped on every produced point (``calculation_method`` is a
# String(64); richer provenance lives in the header design_points block).
CALCULATION_METHOD = "design_estimate_facts_v1"

# Canonical project_fact NAME (normalized: lowercase, non-alphanumeric stripped,
# whitespace -> underscore) -> calendar month. PVsyst "Year 1" is a typical-year
# estimate, so these names carry no calendar year and no unit suffix.
MONTHLY_PRODUCTION_FIELDS: dict[str, int] = {
    "january_estimated_production_year_1": 1,
    "february_estimated_production_year_1": 2,
    "march_estimated_production_year_1": 3,
    "april_estimated_production_year_1": 4,
    "may_estimated_production_year_1": 5,
    "june_estimated_production_year_1": 6,
    "july_estimated_production_year_1": 7,
    "august_estimated_production_year_1": 8,
    "september_estimated_production_year_1": 9,
    "october_estimated_production_year_1": 10,
    "november_estimated_production_year_1": 11,
    "december_estimated_production_year_1": 12,
}
ANNUAL_PRODUCTION_FIELD = "estimated_production_year_1"

# GHI insolation (kWh/m²/period) — metadata only, NEVER written to a point.
MONTHLY_GHI_FIELDS: dict[str, int] = {
    "january_estimated_ghi_irradiance_per_meter_squared": 1,
    "february_estimated_ghi_irradiance_per_meter_squared": 2,
    "march_estimated_ghi_irradiance_per_meter_squared": 3,
    "april_estimated_ghi_irradiance_per_meter_squared": 4,
    "may_estimated_ghi_irradiance_per_meter_squared": 5,
    "june_estimated_ghi_irradiance_per_meter_squared": 6,
    "july_estimated_ghi_irradiance_per_meter_squared": 7,
    "august_estimated_ghi_irradiance_per_meter_squared": 8,
    "september_estimated_ghi_irradiance_per_meter_squared": 9,
    "october_estimated_ghi_irradiance_per_meter_squared": 10,
    "november_estimated_ghi_irradiance_per_meter_squared": 11,
    "december_estimated_ghi_irradiance_per_meter_squared": 12,
}
ANNUAL_GHI_FIELD = "annual_estimated_ghi_irradiance_per_meter_squared"

# Scenario fields — metadata only (the unique point key cannot hold P50 and P90
# for the same period). ``statistical_standard`` may be a non-numeric label.
P50_FIELD = "p50_mwh"
P90_FIELD = "p90_mwh"
STATISTICAL_STANDARD_FIELD = "statistical_standard_p50_or_p90"

# Below this specific yield (annual_kwh / dc_kw) the production values almost
# certainly arrived in MWh (typical solar yield is ~800-2500 kWh/kWp).
_MWH_SPECIFIC_YIELD_THRESHOLD = 50.0

# All canonical names this producer reads.
_ALL_FIELD_NAMES: frozenset[str] = frozenset(
    set(MONTHLY_PRODUCTION_FIELDS)
    | {ANNUAL_PRODUCTION_FIELD}
    | set(MONTHLY_GHI_FIELDS)
    | {ANNUAL_GHI_FIELD, P50_FIELD, P90_FIELD, STATISTICAL_STANDARD_FIELD}
)


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class MonthPointPlan:
    """One resolved monthly production point ready to persist."""

    month: int
    canonical_name: str
    value: float
    fact_id: int
    document_id: Optional[int] = None
    ai_confidence: Optional[float] = None


@dataclass(frozen=True)
class AnnualPointPlan:
    """The resolved annual production point ready to persist."""

    value: float
    fact_id: int
    document_id: Optional[int] = None
    ai_confidence: Optional[float] = None


@dataclass(frozen=True)
class PointsReadiness:
    ready: bool
    has_design_data: bool
    baseline_id: int
    baseline_type: str
    parsed_months: list[int]
    annual_value: Optional[float]
    reference_year: Optional[int]
    reference_year_source: Optional[str]
    missing_fields: list[str]
    parse_errors: list[dict]
    warnings: list[str]
    scenarios: Optional[dict]
    schema_expansion_recommended: bool
    source_fact_ids: list[int]
    source_document_ids: list[int]


@dataclass(frozen=True)
class _Evaluation:
    """Internal resolution shared by readiness + generate."""

    ready: bool
    has_design_data: bool
    baseline_id: int
    baseline_type: str
    monthly_plans: dict  # month -> MonthPointPlan
    annual_plan: Optional[AnnualPointPlan]
    reference_year: Optional[int]
    reference_year_source: Optional[str]
    missing_fields: list[str]
    parse_errors: list[dict]
    warnings: list[str]
    scenarios: dict  # raw scenario provenance (may be empty)
    ghi: dict  # raw ghi provenance (may be empty)
    source_fact_ids: list[int]
    source_document_ids: list[int]

    @property
    def schema_expansion_recommended(self) -> bool:
        return bool(self.scenarios or self.ghi)

    @property
    def parsed_months(self) -> list[int]:
        return sorted(self.monthly_plans)

    @property
    def annual_value(self) -> Optional[float]:
        return None if self.annual_plan is None else self.annual_plan.value

    def readiness(self) -> PointsReadiness:
        return PointsReadiness(
            ready=self.ready,
            has_design_data=self.has_design_data,
            baseline_id=self.baseline_id,
            baseline_type=self.baseline_type,
            parsed_months=self.parsed_months,
            annual_value=self.annual_value,
            reference_year=self.reference_year,
            reference_year_source=self.reference_year_source,
            missing_fields=list(self.missing_fields),
            parse_errors=list(self.parse_errors),
            warnings=list(self.warnings),
            scenarios=self.scenarios or None,
            schema_expansion_recommended=self.schema_expansion_recommended,
            source_fact_ids=list(self.source_fact_ids),
            source_document_ids=list(self.source_document_ids),
        )


@dataclass(frozen=True)
class GeneratePointsResult:
    readiness: PointsReadiness
    wrote: bool
    points_created: int
    points_deleted: int
    monthly_points: int
    annual_points: int


# ---------------------------------------------------------------------------
# Helpers (mirror the Phase 2 bridge's conservative coercion)
# ---------------------------------------------------------------------------
def _unwrap(value):
    """Unwrap the ``{"v": ...}`` JSONB envelope used by ``project_facts.value``."""
    if isinstance(value, dict) and "v" in value:
        return value["v"]
    return value


def _coerce_number(raw) -> Optional[float]:
    """Coerce a fact value to ``float``; return ``None`` when not numeric.

    Never guesses: a non-numeric value yields ``None``.
    """
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    if isinstance(raw, str):
        stripped = raw.strip().replace(",", "")
        if not stripped:
            return None
        try:
            return float(stripped)
        except ValueError:
            return None
    return None


def _confidence(fact) -> Optional[float]:
    return float(fact.ai_confidence) if fact.ai_confidence is not None else None


def _doc_id_for_file(db: Session, file_id: Optional[int]) -> Optional[int]:
    if file_id is None:
        return None
    row = db.query(File.document_id).filter(File.id == file_id).one_or_none()
    return None if row is None else row[0]


def _parse_production(raw) -> tuple[Optional[float], Optional[str]]:
    """Validate a PRESENT production fact value.

    A fact that exists must carry a usable, non-negative, finite number. Anything
    else is a hard parse error (the caller surfaces a 422) — production estimates
    are never guessed or coerced into a fabricated default. Absent facts are
    handled by the caller as "partial", not as an error.
    """
    num = _coerce_number(raw)
    if num is None:
        return None, "value is not numeric or is empty"
    if not math.isfinite(num):
        return None, "value is not finite"
    if num < 0:
        return None, "value is negative"
    return num, None


def _raw_for_error(raw):
    return raw if isinstance(raw, (int, float, str, bool)) or raw is None else str(raw)


def _resolve_facts(db: Session, site_id: int) -> dict:
    """``{canonical_name: fact}`` for the design-estimate fields we read.

    Only active facts whose canonical name is one we consume are returned; if a
    field has duplicate active facts (should not happen) the highest id wins.
    """
    resolved: dict = {}
    for fact in ProjectFactCRUD(db).get_active_facts_for_site(site_id):
        canonical = fact.canonical_field
        if canonical is None or canonical.name not in _ALL_FIELD_NAMES:
            continue
        existing = resolved.get(canonical.name)
        if existing is not None and existing.id >= fact.id:
            continue
        resolved[canonical.name] = fact
    return resolved


def _resolve_timezone(baseline: TelemetryExpectedBaseline, site) -> tuple[ZoneInfo, str]:
    """Site-local zone for the production day boundary.

    Precedence: the baseline's snapshot ``timezone`` -> the site's ``timezone`` ->
    UTC (with a warning), mirroring ``_site_local_day_start_utc``. Telemetry points
    are stored naive-UTC, so the resolved zone only fixes which UTC instant the
    site-local first-of-month midnight maps to.
    """
    tz_name = getattr(baseline, "timezone", None) or getattr(site, "timezone", None) or "UTC"
    try:
        return ZoneInfo(tz_name), tz_name
    except Exception:
        logger.warning(
            "design_points_invalid_timezone baseline_id=%s tz=%r falling_back=UTC",
            getattr(baseline, "id", None),
            tz_name,
        )
        return ZoneInfo("UTC"), "UTC"


def _site_local_midnight_naive_utc(year: int, month: int, day: int, tz: ZoneInfo) -> datetime:
    """Naive-UTC instant of a site-local midnight (matches stored readings)."""
    local_midnight = datetime(year, month, day, 0, 0, 0, tzinfo=tz)
    return local_midnight.astimezone(timezone.utc).replace(tzinfo=None)


def _reference_year(baseline: TelemetryExpectedBaseline, tz: ZoneInfo) -> tuple[Optional[int], Optional[str]]:
    """Calendar year that anchors the typical-year design curve.

    Precedence: ``pto_date.year`` (the year the plant produces) else the
    site-local year of ``created_at``. Drafts never have ``active_from`` (it is
    stamped at activation), so it is intentionally not consulted.
    """
    pto = getattr(baseline, "pto_date", None)
    if pto is not None:
        return pto.year, "pto_date"
    created = getattr(baseline, "created_at", None)
    if created is not None:
        # created_at is stored naive-UTC; render it in the site zone for the year.
        aware = created.replace(tzinfo=timezone.utc)
        return aware.astimezone(tz).year, "created_at"
    return None, None


# ---------------------------------------------------------------------------
# Core evaluation
# ---------------------------------------------------------------------------
def _evaluate(db: Session, site, baseline: TelemetryExpectedBaseline) -> _Evaluation:
    facts = _resolve_facts(db, baseline.site_id)

    warnings: list[str] = []
    parse_errors: list[dict] = []
    missing_fields: list[str] = []
    monthly_plans: dict = {}
    source_fact_ids: list[int] = []
    doc_ids: set = set()

    tz, _tz_name = _resolve_timezone(baseline, site)
    reference_year, reference_year_source = _reference_year(baseline, tz)

    # 1) Monthly production. Absent month = partial (not an error); present but
    #    unparseable = a hard parse error that blocks the whole write.
    for canonical_name, month in MONTHLY_PRODUCTION_FIELDS.items():
        fact = facts.get(canonical_name)
        if fact is None:
            continue
        raw = _unwrap(fact.value)
        value, err = _parse_production(raw)
        document_id = _doc_id_for_file(db, fact.source_file_id)
        if err is not None:
            parse_errors.append(
                {
                    "field": canonical_name,
                    "month": month,
                    "fact_id": fact.id,
                    "raw_value": _raw_for_error(raw),
                    "error": err,
                }
            )
            continue
        monthly_plans[month] = MonthPointPlan(
            month=month,
            canonical_name=canonical_name,
            value=value,
            fact_id=fact.id,
            document_id=document_id,
            ai_confidence=_confidence(fact),
        )
        source_fact_ids.append(fact.id)
        if document_id is not None:
            doc_ids.add(document_id)

    # 2) Annual production (only when the fact exists — never summed from months).
    annual_plan: Optional[AnnualPointPlan] = None
    annual_fact = facts.get(ANNUAL_PRODUCTION_FIELD)
    if annual_fact is not None:
        raw = _unwrap(annual_fact.value)
        value, err = _parse_production(raw)
        document_id = _doc_id_for_file(db, annual_fact.source_file_id)
        if err is not None:
            parse_errors.append(
                {
                    "field": ANNUAL_PRODUCTION_FIELD,
                    "fact_id": annual_fact.id,
                    "raw_value": _raw_for_error(raw),
                    "error": err,
                }
            )
        else:
            annual_plan = AnnualPointPlan(
                value=value,
                fact_id=annual_fact.id,
                document_id=document_id,
                ai_confidence=_confidence(annual_fact),
            )
            source_fact_ids.append(annual_fact.id)
            if document_id is not None:
                doc_ids.add(document_id)

    has_design_data = bool(monthly_plans) or annual_plan is not None

    # No production facts at all -> honest "no design data" signal (not an error).
    if not has_design_data and not parse_errors:
        missing_fields = [*MONTHLY_PRODUCTION_FIELDS, ANNUAL_PRODUCTION_FIELD]

    # Partial-months warning — absent months are NEVER fabricated/distributed.
    if monthly_plans and len(monthly_plans) < 12:
        absent = [
            name
            for name, month in MONTHLY_PRODUCTION_FIELDS.items()
            if month not in monthly_plans
        ]
        warnings.append(
            f"Only {len(monthly_plans)} of 12 monthly production months are present; "
            f"absent months are not fabricated or back-filled: {', '.join(absent)}."
        )

    if reference_year is None:
        warnings.append(
            "No reference year could be derived (no pto_date or created_at); points "
            "cannot be anchored."
        )

    # 3) Scenarios + GHI — metadata only (never points, never irradiance_wm2).
    scenarios = _collect_scenarios(facts)
    ghi = _collect_ghi(db, facts)

    # 4) Unit plausibility (warn only; values are never auto-converted).
    warnings.extend(_unit_warnings(baseline, monthly_plans, annual_plan, scenarios))

    if has_design_data:
        warnings.append(
            "Production values are stored as-extracted into expected_energy_kwh "
            "(assumed unit kWh, unit_verified=false); units are never auto-converted."
        )

    ready = has_design_data and not parse_errors and reference_year is not None

    return _Evaluation(
        ready=ready,
        has_design_data=has_design_data,
        baseline_id=baseline.id,
        baseline_type=baseline.baseline_type.value,
        monthly_plans=monthly_plans,
        annual_plan=annual_plan,
        reference_year=reference_year,
        reference_year_source=reference_year_source,
        missing_fields=missing_fields,
        parse_errors=parse_errors,
        warnings=warnings,
        scenarios=scenarios,
        ghi=ghi,
        source_fact_ids=sorted(set(source_fact_ids)),
        source_document_ids=sorted(doc_ids),
    )


def _collect_scenarios(facts: dict) -> dict:
    """P50/P90 (MWh) + statistical-standard label — header metadata only."""
    out: dict = {}
    for key, name in (("p50_mwh", P50_FIELD), ("p90_mwh", P90_FIELD)):
        fact = facts.get(name)
        if fact is None:
            continue
        raw = _unwrap(fact.value)
        num = _coerce_number(raw)
        out[key] = {
            "value": num,
            "raw_value": _raw_for_error(raw),
            "unit": "mwh",
            "fact_id": fact.id,
        }
    std = facts.get(STATISTICAL_STANDARD_FIELD)
    if std is not None:
        raw = _unwrap(std.value)
        # statistical_standard is a label (e.g. "P50"/"P90") — keep it raw.
        out["statistical_standard"] = {
            "value": None if raw is None else str(raw),
            "fact_id": std.id,
        }
    return out


def _collect_ghi(db: Session, facts: dict) -> dict:
    """Monthly/annual GHI insolation (kWh/m²) — header metadata only."""
    out: dict = {}
    monthly: dict = {}
    for canonical_name, month in MONTHLY_GHI_FIELDS.items():
        fact = facts.get(canonical_name)
        if fact is None:
            continue
        raw = _unwrap(fact.value)
        monthly[str(month)] = {
            "value": _coerce_number(raw),
            "raw_value": _raw_for_error(raw),
            "fact_id": fact.id,
        }
    if monthly:
        out["monthly"] = monthly
    annual = facts.get(ANNUAL_GHI_FIELD)
    if annual is not None:
        raw = _unwrap(annual.value)
        out["annual"] = {
            "value": _coerce_number(raw),
            "raw_value": _raw_for_error(raw),
            "fact_id": annual.id,
        }
    if out:
        out["unit"] = "kwh_per_m2"
        out["note"] = (
            "GHI insolation is not instantaneous irradiance; it is recorded here "
            "and never written to a point's irradiance_wm2 column."
        )
    return out


def _unit_warnings(
    baseline: TelemetryExpectedBaseline,
    monthly_plans: dict,
    annual_plan: Optional[AnnualPointPlan],
    scenarios: dict,
) -> list[str]:
    warnings: list[str] = []
    # Annual magnitude to test (the annual fact, else the sum of present months).
    total = None
    if annual_plan is not None:
        total = annual_plan.value
    elif monthly_plans:
        total = sum(plan.value for plan in monthly_plans.values())
    if total is None:
        return warnings

    dc_kw = getattr(baseline, "system_size_dc_kw", None)
    if dc_kw is not None:
        try:
            dc_kw_f = float(dc_kw)
        except (TypeError, ValueError):
            dc_kw_f = 0.0
        if dc_kw_f > 0:
            specific_yield = total / dc_kw_f
            if specific_yield < _MWH_SPECIFIC_YIELD_THRESHOLD:
                warnings.append(
                    f"Annual production specific yield is {specific_yield:.1f} kWh/kWp "
                    f"(< {_MWH_SPECIFIC_YIELD_THRESHOLD:.0f}); values may be in MWh. They "
                    "are stored as-extracted (kWh assumed) and never auto-converted."
                )

    p50 = (scenarios.get("p50_mwh") or {}).get("value")
    if p50 is not None and p50 > 0 and abs(total - p50) <= 0.05 * p50:
        warnings.append(
            f"Annual production ({total}) is within ~5% of P50 ({p50} MWh); the "
            "production values may be in MWh — stored as-extracted, never converted."
        )
    return warnings


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def evaluate_points_readiness(
    db: Session, site, baseline: TelemetryExpectedBaseline
) -> PointsReadiness:
    """Report (read-only) whether promoted facts can produce design points."""
    return _evaluate(db, site, baseline).readiness()


def generate_design_points(
    db: Session, site, baseline: TelemetryExpectedBaseline
) -> GeneratePointsResult:
    """Delete + rebuild this baseline's monthly/annual design points.

    Writes nothing unless the evaluation is ``ready`` (the caller surfaces a 422
    for ``no_design_data`` / malformed). When ready, the previous monthly/annual
    points are deleted, the fresh points inserted, and the header design-points
    provenance block updated — all in ONE transaction, so a failure can never
    leave the baseline with a half-rebuilt curve. Hourly/interval points (if any)
    are untouched.

    Defense-in-depth: even though the endpoint already guards the baseline type
    and status, the service refuses to write onto a non-``design_estimate`` or an
    immutable (``approved`` / ``active`` / ``superseded``) baseline so a future
    direct caller can never corrupt a frozen curve.
    """
    if baseline.baseline_type != TelemetryBaselineType.design_estimate:
        raise ValueError(
            "Design-estimate points may only be produced on a design_estimate "
            f"baseline (got '{baseline.baseline_type.value}')."
        )
    if baseline.status not in _MUTABLE_STATUSES:
        raise ValueError(
            f"Cannot generate design points on a '{baseline.status.value}' baseline; "
            "only draft or in_review baselines are mutable."
        )
    evaluation = _evaluate(db, site, baseline)
    if not evaluation.ready:
        return GeneratePointsResult(
            readiness=evaluation.readiness(),
            wrote=False,
            points_created=0,
            points_deleted=0,
            monthly_points=0,
            annual_points=0,
        )

    tz, tz_name = _resolve_timezone(baseline, site)
    ref_year = evaluation.reference_year

    new_points: list[TelemetryExpectedBaselinePoint] = []
    for month in sorted(evaluation.monthly_plans):
        plan = evaluation.monthly_plans[month]
        new_points.append(
            TelemetryExpectedBaselinePoint(
                baseline_id=baseline.id,
                site_id=baseline.site_id,
                device_id=None,
                point_ts=_site_local_midnight_naive_utc(ref_year, month, 1, tz),
                interval_minutes=None,
                expected_energy_kwh=plan.value,
                expected_power_kw=None,
                irradiance_wm2=None,
                source_granularity=TelemetryBaselineGranularity.monthly,
                calculation_method=CALCULATION_METHOD,
            )
        )
    if evaluation.annual_plan is not None:
        new_points.append(
            TelemetryExpectedBaselinePoint(
                baseline_id=baseline.id,
                site_id=baseline.site_id,
                device_id=None,
                point_ts=_site_local_midnight_naive_utc(ref_year, 1, 1, tz),
                interval_minutes=None,
                expected_energy_kwh=evaluation.annual_plan.value,
                expected_power_kw=None,
                irradiance_wm2=None,
                source_granularity=TelemetryBaselineGranularity.annual,
                calculation_method=CALCULATION_METHOD,
            )
        )

    monthly_count = sum(
        1 for p in new_points if p.source_granularity == TelemetryBaselineGranularity.monthly
    )
    annual_count = sum(
        1 for p in new_points if p.source_granularity == TelemetryBaselineGranularity.annual
    )

    points_crud = TelemetryExpectedBaselinePointCRUD(db)
    try:
        deleted = points_crud.delete_design_points(baseline.id)
        db.add_all(new_points)
        baseline.model_parameters_json = _merge_design_points_block(
            baseline.model_parameters_json,
            evaluation,
            tz_name=tz_name,
            monthly_count=monthly_count,
            annual_count=annual_count,
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception(
            "design_points_generate_failed baseline_id=%s site_id=%s",
            baseline.id,
            baseline.site_id,
        )
        raise

    logger.info(
        "design_points_generated baseline_id=%s site_id=%s monthly=%s annual=%s deleted=%s",
        baseline.id,
        baseline.site_id,
        monthly_count,
        annual_count,
        deleted,
    )
    return GeneratePointsResult(
        readiness=evaluation.readiness(),
        wrote=True,
        points_created=len(new_points),
        points_deleted=deleted,
        monthly_points=monthly_count,
        annual_points=annual_count,
    )


def _merge_design_points_block(
    existing_params: Optional[dict],
    evaluation: _Evaluation,
    *,
    tz_name: str,
    monthly_count: int,
    annual_count: int,
) -> dict:
    """Return a NEW model_parameters_json with the design_points provenance block.

    Reassigned (not mutated in place) so SQLAlchemy reliably flags the JSONB
    column dirty. Carries full per-field provenance, the unit assumption, the
    reference year, scenarios/GHI (which the point schema cannot represent), and
    every warning so the audit trail is self-describing.
    """
    params = dict(existing_params or {})
    monthly_provenance = {
        str(month): {
            "fact_id": plan.fact_id,
            "document_id": plan.document_id,
            "ai_confidence": plan.ai_confidence,
            "value": plan.value,
            "canonical_name": plan.canonical_name,
        }
        for month, plan in sorted(evaluation.monthly_plans.items())
    }
    annual_provenance = None
    if evaluation.annual_plan is not None:
        annual_provenance = {
            "fact_id": evaluation.annual_plan.fact_id,
            "document_id": evaluation.annual_plan.document_id,
            "ai_confidence": evaluation.annual_plan.ai_confidence,
            "value": evaluation.annual_plan.value,
            "canonical_name": ANNUAL_PRODUCTION_FIELD,
        }
    params["design_points"] = {
        "calculation_method": CALCULATION_METHOD,
        "assumed_unit": "kwh",
        "unit_verified": False,
        "reference_year": evaluation.reference_year,
        "reference_year_source": evaluation.reference_year_source,
        "timezone": tz_name,
        "generated_at": datetime.utcnow().isoformat() + "Z",
        "monthly_points": monthly_count,
        "annual_points": annual_count,
        "monthly": monthly_provenance,
        "annual": annual_provenance,
        "ghi": evaluation.ghi or None,
        "scenarios": evaluation.scenarios or None,
        "schema_expansion_recommended": evaluation.schema_expansion_recommended,
        "schema_expansion_note": (
            "P50/P90 scenarios and GHI insolation cannot be represented by the "
            "single-value point schema; they are recorded here for forward "
            "compatibility."
            if evaluation.schema_expansion_recommended
            else None
        ),
        "source_fact_ids": list(evaluation.source_fact_ids),
        "source_document_ids": list(evaluation.source_document_ids),
        "warnings": list(evaluation.warnings),
    }
    return params
