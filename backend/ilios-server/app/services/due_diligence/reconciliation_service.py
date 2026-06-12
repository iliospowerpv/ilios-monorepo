"""DD V2 Phase 4 — READ-ONLY assumptions reconciliation aggregator.

This service answers one question for an admin/diligence reviewer: *for every
diligence-critical field, how does the source-backed value flow through the
audit chain, and where (if anywhere) does it diverge?* The chain is:

    uploaded doc -> AI-extracted value -> human accepted/overridden value
    -> active/promoted project_fact -> draft baseline -> design-estimate points
    -> active weather-adjusted baseline   (+ legacy SAFL, display-only)

It is STRICTLY READ-ONLY. It performs ZERO writes/commits, never recomputes a
baseline value (point values are read verbatim from stored rows), never creates,
approves, or activates anything, and never changes the weather-adjusted math. It
only *reads and compares* what already exists. Legacy ``SiteAdditionalFieldList``
values are surfaced for display/transition comparison ONLY and are never used to
build a V2 baseline.

The two distinct "expected" notions are kept separate end-to-end: physics
nameplate reconciles against the WEATHER-ADJUSTED baseline header columns, while
design-estimate production reconciles against the DESIGN-ESTIMATE baseline points
(monthly/annual). They are never merged into one "expected" column.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional
from zoneinfo import ZoneInfo

from sqlalchemy.orm import Session, joinedload

from app.crud.telemetry_expected import TelemetryExpectedBaselineCRUD, TelemetryExpectedBaselinePointCRUD
from app.models.project_facts import FactStatus, ProjectFact
from app.models.site import SiteAdditionalFieldList
from app.models.telemetry_expected import (
    TelemetryBaselineGranularity,
    TelemetryBaselineStatus,
    TelemetryBaselineType,
    TelemetryExpectedBaseline,
)
from app.schema.reconciliation import (
    ReconciliationReadiness,
    ReconciliationRow,
    SiteReconciliationResponse,
    TelemetryReality,
)
from app.services.telemetry import baseline_from_facts_service as facts_bridge
from app.services.telemetry import baseline_points_service as points_svc
from app.static.reconciliation_catalog import (
    ABS_COMPARE_FIELDS,
    HEADER_COLUMN,
    METADATA,
    NONE,
    OTHER,
    POINTS_ANNUAL,
    POINTS_MONTHLY,
    RECONCILIATION_CATALOG,
    SAFL_FIELD_MAP,
    CATALOG_FIELD_NAMES,
    ReconciliationField,
)

logger = logging.getLogger(__name__)

# Numeric equality tolerance — relative 1e-6 with a tiny absolute floor so two
# values that are equal up to float noise never raise a spurious mismatch.
_REL_TOL = 1e-6
_ABS_FLOOR = 1e-9

_MUTABLE_STATUSES = (TelemetryBaselineStatus.draft, TelemetryBaselineStatus.in_review)
_DESIGN_POINT_GRANULARITIES = (
    TelemetryBaselineGranularity.monthly,
    TelemetryBaselineGranularity.annual,
)

# Warning tokens (also documented on the schema).
W_MISSING_REQUIRED = "missing_required_for_baseline"
W_FACT_VS_LEGACY = "fact_differs_from_legacy"
W_DRAFT_VS_ACTIVE = "draft_differs_from_active"
W_ACTIVE_OUTDATED = "active_baseline_outdated"
W_DESIGN_POINTS_MISSING = "design_points_missing"
W_NEEDS_REVIEW = "needs_review"

# Tooltip/help targets for the UI (Path B hook) — short, not full help content.
HELP_TARGETS: dict[str, str] = {
    "ai_extracted_value": "What the AI model first read from the source document.",
    "accepted_value": "The value a reviewer accepted or overrode at the document.",
    "active_fact_value": "The current promoted assumption (active project fact).",
    "draft_baseline_value": "Value on the latest DRAFT baseline (not yet active).",
    "active_baseline_value": "Value on the ACTIVE baseline driving expected output.",
    "legacy_value": "Legacy site field — shown for comparison only, never used.",
    "status": "How far this field has progressed through the assumption pipeline.",
    "warnings": "Divergences or gaps a reviewer should resolve before activation.",
}


# ---------------------------------------------------------------------------
# Coercion / comparison helpers (mirror the Phase 2/3 conservative semantics).
# ---------------------------------------------------------------------------
def _unwrap(value):
    """Unwrap the ``{"v": ...}`` JSONB envelope used by ``project_facts.value``."""
    if isinstance(value, dict) and "v" in value:
        return value["v"]
    return value


def _coerce_number(raw) -> Optional[float]:
    """Coerce to float without guessing; non-numeric -> None."""
    if raw is None or isinstance(raw, bool):
        return None
    if isinstance(raw, (int, float, Decimal)):
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


def _coerce_date(raw) -> Optional[date]:
    """Best-effort date coercion for exact date comparison; None when not a date."""
    if isinstance(raw, datetime):
        return raw.date()
    if isinstance(raw, date):
        return raw
    if isinstance(raw, str):
        text = raw.strip()
        if not text:
            return None
        try:
            return date.fromisoformat(text[:10])
        except ValueError:
            return None
    return None


def _to_jsonable(value):
    """Render a value as a JSON-friendly primitive (never raises)."""
    if value is None:
        return None
    if isinstance(value, bool):
        return value
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if hasattr(value, "value") and not isinstance(value, (int, float, str)):
        # SQLAlchemy Enum instances expose ``.value``.
        try:
            return value.value
        except Exception:  # pragma: no cover - defensive
            return str(value)
    return value


def _to_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):  # pragma: no cover - defensive
        return None


def _differs(a, b, *, abs_compare: bool = False) -> bool:
    """True when two non-null values meaningfully differ.

    Numbers compare with a relative tolerance (loss values via magnitude when
    ``abs_compare``); dates compare exactly; everything else compares as
    case-folded, stripped strings. A None on either side is "not comparable" and
    never a mismatch.
    """
    if a is None or b is None:
        return False
    na, nb = _coerce_number(a), _coerce_number(b)
    if na is not None and nb is not None:
        if abs_compare:
            na, nb = abs(na), abs(nb)
        return abs(na - nb) > max(_REL_TOL * max(abs(na), abs(nb)), _ABS_FLOOR)
    da, db = _coerce_date(a), _coerce_date(b)
    if da is not None and db is not None:
        return da != db
    return str(a).strip().casefold() != str(b).strip().casefold()


def _as_naive_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _resolve_zone(baseline: Optional[TelemetryExpectedBaseline], site) -> ZoneInfo:
    tz_name = (
        (getattr(baseline, "timezone", None) if baseline else None)
        or getattr(site, "timezone", None)
        or "UTC"
    )
    try:
        return ZoneInfo(tz_name)
    except Exception:
        return ZoneInfo("UTC")


def _point_month(point_ts: datetime, tz: ZoneInfo) -> int:
    """Recover the calendar month a stored monthly point represents.

    Phase 3 anchors monthly points at the site-local first-of-month midnight,
    stored naive-UTC. Converting back to the same zone recovers the local month
    (robust to UTC-offset month rollover).
    """
    aware = point_ts.replace(tzinfo=timezone.utc)
    return aware.astimezone(tz).month


# ---------------------------------------------------------------------------
# Baseline loading
# ---------------------------------------------------------------------------
def _latest_non_terminal(
    db: Session, site_id: int, baseline_type: TelemetryBaselineType
) -> Optional[TelemetryExpectedBaseline]:
    return (
        db.query(TelemetryExpectedBaseline)
        .filter(
            TelemetryExpectedBaseline.site_id == site_id,
            TelemetryExpectedBaseline.baseline_type == baseline_type,
            TelemetryExpectedBaseline.status.in_(_MUTABLE_STATUSES),
        )
        .order_by(TelemetryExpectedBaseline.created_at.desc())
        .first()
    )


def _baseline_points(
    db: Session, baseline: Optional[TelemetryExpectedBaseline], site
) -> tuple[dict[int, Optional[float]], Optional[float]]:
    """Read (never recompute) a design baseline's monthly + annual point values."""
    if baseline is None:
        return {}, None
    rows = TelemetryExpectedBaselinePointCRUD(db).list_for_baseline(
        baseline.id, _DESIGN_POINT_GRANULARITIES
    )
    tz = _resolve_zone(baseline, site)
    monthly: dict[int, Optional[float]] = {}
    annual: Optional[float] = None
    for row in rows:
        if row.source_granularity == TelemetryBaselineGranularity.monthly:
            monthly[_point_month(row.point_ts, tz)] = _to_float(row.expected_energy_kwh)
        elif row.source_granularity == TelemetryBaselineGranularity.annual:
            annual = _to_float(row.expected_energy_kwh)
    return monthly, annual


def _baseline_source_fact_ids(baseline: Optional[TelemetryExpectedBaseline]) -> set[int]:
    if baseline is None:
        return set()
    params = baseline.model_parameters_json or {}
    ids: set[int] = set()
    for entry in params.get("source_facts", []) or []:
        fid = entry.get("fact_id") if isinstance(entry, dict) else None
        if isinstance(fid, int):
            ids.add(fid)
    if isinstance(baseline.source_project_fact_id, int):
        ids.add(baseline.source_project_fact_id)
    return ids


# ---------------------------------------------------------------------------
# Per-field row builder
# ---------------------------------------------------------------------------
class _Ctx:
    """Loaded, read-only state shared across every row build."""

    def __init__(self, db: Session, site):
        self.db = db
        self.site = site
        site_id = site.id

        facts = (
            db.query(ProjectFact)
            .options(joinedload(ProjectFact.canonical_field))
            .filter(ProjectFact.site_id == site_id)
            .all()
        )
        self.active_by_name: dict[str, ProjectFact] = {}
        self.candidates_by_name: dict[str, list[ProjectFact]] = {}
        for fact in facts:
            canonical = fact.canonical_field
            if canonical is None:
                continue
            name = canonical.name
            if fact.status == FactStatus.active.value:
                existing = self.active_by_name.get(name)
                if existing is None or fact.id > existing.id:
                    self.active_by_name[name] = fact
            elif fact.status == FactStatus.candidate.value:
                self.candidates_by_name.setdefault(name, []).append(fact)

        self.safl: Optional[SiteAdditionalFieldList] = (
            db.query(SiteAdditionalFieldList)
            .filter(SiteAdditionalFieldList.site_id == site_id)
            .first()
        )

        crud = TelemetryExpectedBaselineCRUD(db)
        self.wam_active = crud.get_active(site_id, TelemetryBaselineType.weather_adjusted_model)
        self.wam_draft = _latest_non_terminal(
            db, site_id, TelemetryBaselineType.weather_adjusted_model
        )
        self.de_active = crud.get_active(site_id, TelemetryBaselineType.design_estimate)
        self.de_draft = _latest_non_terminal(
            db, site_id, TelemetryBaselineType.design_estimate
        )

        self.de_draft_monthly, self.de_draft_annual = _baseline_points(db, self.de_draft, site)
        self.de_active_monthly, self.de_active_annual = _baseline_points(db, self.de_active, site)

        self.wam_active_fact_ids = _baseline_source_fact_ids(self.wam_active)
        self.wam_active_created = _as_naive_utc(
            getattr(self.wam_active, "created_at", None)
        )


def _candidate_value(candidates: list[ProjectFact]) -> Optional[ProjectFact]:
    if not candidates:
        return None
    return max(candidates, key=lambda f: f.id)


def _fact_time(fact: ProjectFact) -> Optional[datetime]:
    return _as_naive_utc(fact.promoted_at or fact.updated_at)


def _baseline_driving(entry: Optional[ReconciliationField]) -> bool:
    if entry is None:
        return False
    return entry.baseline_target in (HEADER_COLUMN, POINTS_MONTHLY, POINTS_ANNUAL)


def _build_row(
    ctx: _Ctx,
    *,
    canonical_name: str,
    display_label: str,
    category: str,
    entry: Optional[ReconciliationField],
) -> ReconciliationRow:
    baseline_target = entry.baseline_target if entry else NONE
    active_fact = ctx.active_by_name.get(canonical_name)
    candidates = ctx.candidates_by_name.get(canonical_name, [])
    primary = active_fact or _candidate_value(candidates)

    # --- Provenance / values from the primary fact ---
    ai_raw = _unwrap(primary.ai_extracted_value) if primary else None
    accepted_raw = _unwrap(primary.value) if primary else None
    active_raw = _unwrap(active_fact.value) if active_fact else None

    evidence = (primary.evidence or {}) if (primary and primary.evidence) else {}

    # --- Baseline values (read verbatim; never recomputed) ---
    draft_raw = None
    active_baseline_raw = None
    if baseline_target == HEADER_COLUMN:
        draft_raw = getattr(ctx.wam_draft, canonical_name, None) if ctx.wam_draft else None
        active_baseline_raw = (
            getattr(ctx.wam_active, canonical_name, None) if ctx.wam_active else None
        )
    elif baseline_target == POINTS_MONTHLY and entry and entry.month:
        draft_raw = ctx.de_draft_monthly.get(entry.month)
        active_baseline_raw = ctx.de_active_monthly.get(entry.month)
    elif baseline_target == POINTS_ANNUAL:
        draft_raw = ctx.de_draft_annual
        active_baseline_raw = ctx.de_active_annual

    # --- Legacy SAFL (display/comparison only) ---
    safl_attr = SAFL_FIELD_MAP.get(canonical_name)
    legacy_raw = getattr(ctx.safl, safl_attr, None) if (ctx.safl and safl_attr) else None
    abs_compare = canonical_name in ABS_COMPARE_FIELDS

    # --- Status ladder (most-advanced stage reached wins) ---
    # Presence is checked against the field's RELEVANT baseline: physics nameplate
    # against the weather-adjusted baseline (header columns), design-estimate
    # production against the design-estimate baseline (points). The two are never
    # crossed — a stored design point must not depend on a weather-adjusted draft.
    if baseline_target == HEADER_COLUMN:
        draft_baseline = ctx.wam_draft
        active_baseline = ctx.wam_active
    elif baseline_target in (POINTS_MONTHLY, POINTS_ANNUAL):
        draft_baseline = ctx.de_draft
        active_baseline = ctx.de_active
    else:
        draft_baseline = None
        active_baseline = None
    present_in_active = _present_in_baseline(
        baseline_target, active_baseline, active_baseline_raw, is_active=True
    )
    present_in_draft = _present_in_baseline(
        baseline_target, draft_baseline, draft_raw, is_active=False
    )
    if active_fact and present_in_active:
        status = "in_active_baseline"
    elif active_fact and present_in_draft:
        status = "in_draft_baseline"
    elif active_fact:
        status = "active_fact"
    elif primary:
        status = "candidate_only"
    else:
        status = "missing"

    # --- Warnings (orthogonal to status) ---
    warnings: list[str] = []
    required = bool(entry and entry.required_for_baseline)
    if required and active_fact is None:
        warnings.append(W_MISSING_REQUIRED)
    if _differs(active_raw, legacy_raw, abs_compare=abs_compare):
        warnings.append(W_FACT_VS_LEGACY)
    if _differs(draft_raw, active_baseline_raw):
        warnings.append(W_DRAFT_VS_ACTIVE)
    if (
        baseline_target == HEADER_COLUMN
        and active_fact is not None
        and ctx.wam_active is not None
    ):
        ft = _fact_time(active_fact)
        if active_fact.id not in ctx.wam_active_fact_ids or (
            ft is not None
            and ctx.wam_active_created is not None
            and ft > ctx.wam_active_created
        ):
            warnings.append(W_ACTIVE_OUTDATED)
    if baseline_target in (POINTS_MONTHLY, POINTS_ANNUAL) and active_fact is not None:
        design_baseline = ctx.de_draft or ctx.de_active
        if design_baseline is not None and draft_raw is None and active_baseline_raw is None:
            warnings.append(W_DESIGN_POINTS_MISSING)
    if candidates and _baseline_driving(entry):
        warnings.append(W_NEEDS_REVIEW)
    elif (
        active_fact is not None
        and active_fact.overridden_at is not None
        and not (active_fact.override_notes or "").strip()
        and _baseline_driving(entry)
    ):
        warnings.append(W_NEEDS_REVIEW)

    return ReconciliationRow(
        canonical_field=canonical_name,
        display_label=display_label,
        category=category,
        baseline_target=baseline_target,
        status=status,
        ai_extracted_value=_to_jsonable(ai_raw),
        accepted_value=_to_jsonable(accepted_raw),
        active_fact_value=_to_jsonable(active_raw),
        draft_baseline_value=_to_jsonable(draft_raw),
        active_baseline_value=_to_jsonable(active_baseline_raw),
        legacy_value=_to_jsonable(legacy_raw),
        fact_id=primary.id if primary else None,
        source_file_id=primary.source_file_id if primary else None,
        source_document_type=primary.source_document_type if primary else None,
        source_run_id=primary.source_run_id if primary else None,
        evidence_page=evidence.get("page"),
        evidence_snippet=evidence.get("snippet"),
        confidence=(float(primary.ai_confidence) if (primary and primary.ai_confidence is not None) else None),
        effective_from=active_fact.effective_from if active_fact else None,
        effective_to=active_fact.effective_to if active_fact else None,
        supersedes_fact_id=active_fact.supersedes_fact_id if active_fact else None,
        candidate_count=len(candidates),
        required_for_baseline=required,
        warnings=warnings,
    )


def _present_in_baseline(
    baseline_target: str,
    baseline: Optional[TelemetryExpectedBaseline],
    value,
    *,
    is_active: bool,
) -> bool:
    """Whether the field's value is actually represented on the given baseline."""
    if baseline is None:
        return False
    if baseline_target in (METADATA, NONE):
        return False
    return value is not None


# ---------------------------------------------------------------------------
# Readiness block
# ---------------------------------------------------------------------------
def _build_readiness(ctx: _Ctx) -> ReconciliationReadiness:
    site = ctx.site
    facts_readiness = facts_bridge.evaluate_readiness(
        ctx.db, site.id, TelemetryBaselineType.weather_adjusted_model
    )

    design_baseline = ctx.de_draft or ctx.de_active
    design_ready: Optional[bool] = None
    present_months: list[int] = []
    design_missing: list[str] = []
    parse_errors: list[str] = []
    if design_baseline is not None:
        pr = points_svc.evaluate_points_readiness(ctx.db, site, design_baseline)
        design_ready = pr.ready
        present_months = pr.parsed_months
        design_missing = pr.missing_fields
        parse_errors = [
            f"{e.get('field')}: {e.get('error')}" for e in (pr.parse_errors or [])
        ]

    return ReconciliationReadiness(
        facts_to_draft_ready=facts_readiness.ready,
        missing_required_physics_fields=facts_readiness.missing_fields,
        facts_to_draft_warnings=facts_readiness.warnings,
        active_baseline_available=ctx.wam_active is not None,
        active_baseline_id=getattr(ctx.wam_active, "id", None),
        active_baseline_created_at=getattr(ctx.wam_active, "created_at", None),
        design_estimate_baseline_id=getattr(design_baseline, "id", None),
        design_estimate_baseline_status=(
            design_baseline.status.value if design_baseline else None
        ),
        design_points_ready=design_ready,
        design_points_present_months=present_months,
        design_points_missing=design_missing,
        design_points_parse_errors=parse_errors,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def build_site_reconciliation(db: Session, site) -> SiteReconciliationResponse:
    """Build the full read-only reconciliation payload for a site/project.

    Performs only reads and comparisons — no writes, no commits, no baseline
    recomputation. Safe to call on any site, including one with no facts or
    baselines (every block degrades to honest empties/N/A, never a 500).
    """
    ctx = _Ctx(db, site)

    rows: list[ReconciliationRow] = []

    # 1) Catalog rows (baseline-driving + diligence-critical), in catalog order.
    for entry in RECONCILIATION_CATALOG:
        rows.append(
            _build_row(
                ctx,
                canonical_name=entry.canonical_name,
                display_label=entry.display_label,
                category=entry.category,
                entry=entry,
            )
        )

    # 2) Catch-all rows: any other active/candidate fact the catalog doesn't name.
    extra_names = sorted(
        (set(ctx.active_by_name) | set(ctx.candidates_by_name)) - set(CATALOG_FIELD_NAMES)
    )
    for name in extra_names:
        fact = ctx.active_by_name.get(name) or _candidate_value(
            ctx.candidates_by_name.get(name, [])
        )
        display = name
        if fact is not None and fact.canonical_field is not None:
            display = fact.canonical_field.display_name or name
        rows.append(
            _build_row(
                ctx,
                canonical_name=name,
                display_label=display,
                category=OTHER,
                entry=None,
            )
        )

    readiness = _build_readiness(ctx)

    # Schema-expansion hint: GHI / P50 / P90 facts exist that a single-value
    # point/row cannot fully represent.
    metadata_names = {
        e.canonical_name for e in RECONCILIATION_CATALOG if e.baseline_target == METADATA
    }
    schema_expansion = any(
        n in ctx.active_by_name or n in ctx.candidates_by_name for n in metadata_names
    )

    return SiteReconciliationResponse(
        site_id=site.id,
        generated_at=datetime.utcnow(),
        rows=rows,
        readiness=readiness,
        telemetry_reality=TelemetryReality(),
        help_targets=HELP_TARGETS,
        schema_expansion_recommended=schema_expansion,
    )
