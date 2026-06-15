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

from app.crud.canonical_field import CanonicalFieldCRUD
from app.crud.telemetry_expected import TelemetryExpectedBaselineCRUD, TelemetryExpectedBaselinePointCRUD
from app.models.document import Document, DocumentKey
from app.models.file import AIParsingResult, File, FileParsingStatuses
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

# --- Per-field lifecycle statuses (most-advanced stage reached wins) -----------
S_MISSING = "missing"
S_AI_EXTRACTED_ONLY = "ai_extracted_only"
S_ACCEPTED_DOCUMENT_VALUE = "accepted_document_value"
S_CANDIDATE_ONLY = "candidate_only"
S_ACCEPTED_NOT_PROMOTED = "accepted_not_promoted"
S_ACTIVE_FACT = "active_fact"
S_IN_DRAFT_BASELINE = "in_draft_baseline"
S_IN_ACTIVE_BASELINE = "in_active_baseline"
S_SUPERSEDED = "superseded"

# --- Blocking levels (single most-severe per row; ordered most -> least) -------
B_BASELINE = "blocks_baseline"
B_EXPECTED = "blocks_expected"
B_REPORTING = "blocks_reporting"
B_LOWERS_CONFIDENCE = "lowers_confidence"
B_INFORMATIONAL = "informational"

# Short, human-readable label per status (UI chip text).
_STATUS_LABELS: dict[str, str] = {
    S_MISSING: "Missing",
    S_AI_EXTRACTED_ONLY: "AI extracted (unreviewed)",
    S_ACCEPTED_DOCUMENT_VALUE: "Accepted (no project fact)",
    S_CANDIDATE_ONLY: "Candidate (not accepted)",
    S_ACCEPTED_NOT_PROMOTED: "Accepted, not promoted",
    S_ACTIVE_FACT: "Promoted assumption",
    S_IN_DRAFT_BASELINE: "In draft baseline",
    S_IN_ACTIVE_BASELINE: "In active baseline",
    S_SUPERSEDED: "Superseded",
}

# One-sentence plain-language explanation per status.
_STATUS_EXPLANATIONS: dict[str, str] = {
    S_MISSING: "No source value has been found anywhere in the audit chain for this field.",
    S_AI_EXTRACTED_ONLY: (
        "The AI extracted a value from the document, but no reviewer has accepted it yet."
    ),
    S_ACCEPTED_DOCUMENT_VALUE: (
        "A reviewer accepted a document value, but no project fact was created from it."
    ),
    S_CANDIDATE_ONLY: (
        "A candidate fact exists from extraction, but no reviewer has accepted it yet."
    ),
    S_ACCEPTED_NOT_PROMOTED: (
        "A reviewer accepted or overrode this value, but it has not been promoted to the "
        "project's active assumptions."
    ),
    S_ACTIVE_FACT: (
        "This value is the current promoted assumption, but it is not yet on a baseline."
    ),
    S_IN_DRAFT_BASELINE: (
        "This promoted assumption is on the latest draft baseline (not yet activated)."
    ),
    S_IN_ACTIVE_BASELINE: (
        "This promoted assumption is on the active baseline driving expected output."
    ),
    S_SUPERSEDED: (
        "Only superseded (retired) values remain; there is no current active value."
    ),
}

# Ordered pipeline stages still pending to reach ``in_active_baseline``.
_MISSING_DEPENDENCIES: dict[str, list[str]] = {
    S_MISSING: ["source_value", "acceptance", "promotion", "baseline"],
    S_AI_EXTRACTED_ONLY: ["acceptance", "promotion", "baseline"],
    S_ACCEPTED_DOCUMENT_VALUE: ["project_fact", "promotion", "baseline"],
    S_CANDIDATE_ONLY: ["acceptance", "promotion", "baseline"],
    S_ACCEPTED_NOT_PROMOTED: ["promotion", "baseline"],
    S_ACTIVE_FACT: ["baseline"],
    S_IN_DRAFT_BASELINE: ["baseline_activation"],
    S_IN_ACTIVE_BASELINE: [],
    S_SUPERSEDED: ["current_value", "promotion", "baseline"],
}

# Tooltip/help targets for the UI (Path B hook) — short, not full help content.
HELP_TARGETS: dict[str, str] = {
    "ai_extracted_value": "What the AI model first read from the source document.",
    "accepted_value": "The value a reviewer accepted or overrode at the document.",
    "active_fact_value": "The current promoted assumption (active project fact).",
    "draft_baseline_value": "Value on the latest DRAFT baseline (not yet active).",
    "active_baseline_value": "Value on the ACTIVE baseline driving expected output.",
    "legacy_value": "Legacy site field — shown for comparison only, never used.",
    "status": "How far this field has progressed through the assumption pipeline.",
    "status_label": "Plain-language name for the field's current pipeline stage.",
    "required_action": "The single next step to advance this value through the chain.",
    "blocking_level": (
        "What this field's gaps currently block: the baseline, expected output, "
        "reporting, confidence, or nothing (informational)."
    ),
    "missing_dependencies": "Pipeline stages still pending before this value is live.",
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


class _PointSet:
    """Read-only design baseline point values + their row ids, by period."""

    __slots__ = ("monthly", "annual", "monthly_ids", "annual_id")

    def __init__(self):
        self.monthly: dict[int, Optional[float]] = {}
        self.annual: Optional[float] = None
        self.monthly_ids: dict[int, int] = {}
        self.annual_id: Optional[int] = None


def _baseline_points(
    db: Session, baseline: Optional[TelemetryExpectedBaseline], site
) -> _PointSet:
    """Read (never recompute) a design baseline's monthly + annual point values."""
    ps = _PointSet()
    if baseline is None:
        return ps
    rows = TelemetryExpectedBaselinePointCRUD(db).list_for_baseline(
        baseline.id, _DESIGN_POINT_GRANULARITIES
    )
    tz = _resolve_zone(baseline, site)
    for row in rows:
        if row.source_granularity == TelemetryBaselineGranularity.monthly:
            month = _point_month(row.point_ts, tz)
            ps.monthly[month] = _to_float(row.expected_energy_kwh)
            ps.monthly_ids[month] = row.id
        elif row.source_granularity == TelemetryBaselineGranularity.annual:
            ps.annual = _to_float(row.expected_energy_kwh)
            ps.annual_id = row.id
    return ps


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
        self.retired_by_name: dict[str, list[ProjectFact]] = {}
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
            elif fact.status == FactStatus.retired.value:
                self.retired_by_name.setdefault(name, []).append(fact)

        # --- Document chain: site -> documents -> files -> keys + parse runs ----
        # Bulk-loaded ONCE and reduced in Python so row building never queries the
        # DB. Used ONLY for fields with no fact (the accepted_document_value and
        # ai_extracted_only edge states) and for alias/navigation context; a key or
        # run that does not resolve to a reconciled canonical field is ignored
        # (never inferred into a catalog row).
        self.file_to_document: dict[int, int] = {}
        self.keys_by_canonical: dict[str, list[DocumentKey]] = {}
        self.aliases_by_canonical: dict[str, set[str]] = {}
        self.ai_values_by_canonical: dict[str, dict] = {}

        doc_ids = [
            row.id
            for row in db.query(Document.id)
            .filter(Document.site_id == site_id, Document.is_archived.is_(False))
            .all()
        ]
        file_ids: list[int] = []
        if doc_ids:
            for fid, did in (
                db.query(File.id, File.document_id)
                .filter(File.document_id.in_(doc_ids))
                .all()
            ):
                self.file_to_document[fid] = did
                file_ids.append(fid)

            for key in (
                db.query(DocumentKey)
                .filter(DocumentKey.document_id.in_(doc_ids))
                .all()
            ):
                canon = _resolve_key_canonical(key)
                if canon is None:
                    continue
                if key.name:
                    self.aliases_by_canonical.setdefault(canon, set()).add(key.name)
                self.keys_by_canonical.setdefault(canon, []).append(key)

        if file_ids:
            # Ascending id so a later (newer) run overwrites an older one per field.
            for run in (
                db.query(AIParsingResult)
                .filter(
                    AIParsingResult.file_id.in_(file_ids),
                    AIParsingResult.status == FileParsingStatuses.completed,
                )
                .order_by(AIParsingResult.id.asc())
                .all()
            ):
                for field_key, data in _iter_run_fields(getattr(run, "parsed_result", None)):
                    if data.get("value") is None:
                        continue
                    self.ai_values_by_canonical[field_key] = {
                        "value": data.get("value"),
                        "confidence": data.get("confidence"),
                        "evidence": data.get("evidence"),
                        "run_id": run.id,
                        "file_id": run.file_id,
                    }

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

        self.de_draft_points = _baseline_points(db, self.de_draft, site)
        self.de_active_points = _baseline_points(db, self.de_active, site)

        self.wam_active_fact_ids = _baseline_source_fact_ids(self.wam_active)
        self.wam_active_created = _as_naive_utc(
            getattr(self.wam_active, "created_at", None)
        )


def _candidate_value(candidates: list[ProjectFact]) -> Optional[ProjectFact]:
    """Pick the candidate that represents the most-advanced rung on the ladder.

    Acceptance/override is a higher rung than an untouched candidate, so an
    accepted (or overridden) candidate must win over a newer unaccepted one —
    otherwise an older-accepted + newer-unaccepted pair would wrongly read as
    ``candidate_only`` and surface the unaccepted value. Within the same
    lifecycle tier the newest id wins. Mirrors ``_best_key``'s ranking.
    """
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda f: (1 if _is_accepted_candidate(f) else 0, f.id),
    )


def _fact_time(fact: ProjectFact) -> Optional[datetime]:
    return _as_naive_utc(fact.promoted_at or fact.updated_at)


def _baseline_driving(entry: Optional[ReconciliationField]) -> bool:
    if entry is None:
        return False
    return entry.baseline_target in (HEADER_COLUMN, POINTS_MONTHLY, POINTS_ANNUAL)


# ---------------------------------------------------------------------------
# Document-chain helpers (keys + parse runs) — used only for fact-less fields.
# ---------------------------------------------------------------------------
def _resolve_key_canonical(key: DocumentKey) -> Optional[str]:
    """Resolve a DocumentKey to its canonical field name without a DB lookup.

    Prefers the canonical name persisted on the key at accept time; falls back to
    normalizing the key's display name with the same rule the canonical-field
    resolver uses. Returns None when neither yields a name.
    """
    stored = (getattr(key, "canonical_field", None) or "").strip()
    if stored:
        return stored
    name = (getattr(key, "name", None) or "").strip()
    if not name:
        return None
    normalized = CanonicalFieldCRUD.normalize_key_name(name)
    return normalized or None


def _iter_run_fields(parsed):
    """Yield ``(field_key, {value, confidence, evidence})`` for both parse shapes.

    Format A: dict keyed by snake_case field_key -> {value, confidence, evidence}.
    Format B: {"fields": [{field_key, value, evidence, confidence}, ...]}.
    Mirrors ``ProjectFactsService._find_field_in_run`` semantics.
    """
    if not isinstance(parsed, dict):
        return
    fields = parsed.get("fields")
    if isinstance(fields, list):
        for field in fields:
            if isinstance(field, dict) and field.get("field_key"):
                evidence = field.get("evidence")
                yield field["field_key"], {
                    "value": field.get("value"),
                    "confidence": field.get("confidence"),
                    "evidence": evidence if isinstance(evidence, dict) else None,
                }
        return
    for field_key, entry in parsed.items():
        if isinstance(entry, dict) and "value" in entry:
            evidence = entry.get("evidence")
            yield field_key, {
                "value": entry.get("value"),
                "confidence": entry.get("confidence"),
                "evidence": evidence if isinstance(evidence, dict) else None,
            }


def _effective_key_value(key: DocumentKey):
    """The value a reviewer accepted on a key: override value if present, else value."""
    if getattr(key, "override_value", None) not in (None, ""):
        return key.override_value
    return getattr(key, "value", None)


def _best_key(keys: list[DocumentKey]) -> Optional[DocumentKey]:
    """Pick the most decision-bearing key: overridden first, then latest by id."""
    if not keys:
        return None
    return max(keys, key=lambda k: (1 if getattr(k, "overridden_at", None) else 0, k.id))


def _is_accepted_candidate(fact: ProjectFact) -> bool:
    """A candidate is 'accepted' once a reviewer accepted or overrode it."""
    return fact.accepted_at is not None or fact.overridden_at is not None


def _stable_key(value) -> str:
    """Comparable key for distinct-value detection (numbers/dates normalized)."""
    num = _coerce_number(value)
    if num is not None:
        return f"n:{num:.9g}"
    dt = _coerce_date(value)
    if dt is not None:
        return f"d:{dt.isoformat()}"
    return f"s:{str(value).strip().casefold()}"


# ---------------------------------------------------------------------------
# Status presentation helpers (label / explanation / action / dependencies).
# ---------------------------------------------------------------------------
def _required_action(status: str, *, required: bool, status_ctx: dict) -> Optional[str]:
    if status == S_MISSING:
        return (
            "No source value found — extract or enter this value, then accept and "
            "promote it."
            if required
            else None
        )
    if status == S_ACTIVE_FACT:
        if status_ctx.get("driving") and not status_ctx.get("has_relevant_active_baseline"):
            return "Create and activate a baseline to put this assumption into effect."
        return None
    if status == S_IN_DRAFT_BASELINE:
        return "Activate the draft baseline to make this assumption live."
    if status == S_IN_ACTIVE_BASELINE:
        if status_ctx.get("active_outdated"):
            return "Rebuild the active baseline to include the latest promoted value."
        return None
    return {
        S_AI_EXTRACTED_ONLY: "Review and accept this value in Due Diligence, then promote it.",
        S_ACCEPTED_DOCUMENT_VALUE: (
            "Re-accept this value in Due Diligence so a project fact is created, then "
            "promote it."
        ),
        S_CANDIDATE_ONLY: "Accept this value in Due Diligence, then promote it to project assumptions.",
        S_ACCEPTED_NOT_PROMOTED: "Promote this accepted value to the project's active assumptions.",
        S_SUPERSEDED: "Accept and promote a current value to replace the superseded one.",
    }.get(status)


def _blocking_level(
    status: str,
    warnings: list[str],
    *,
    required: bool,
    active_fact: Optional[ProjectFact],
    entry: Optional[ReconciliationField],
    has_value: bool,
) -> Optional[str]:
    """The single most-severe impact of this row's gaps (most -> least)."""
    if required and active_fact is None:
        return B_BASELINE
    is_points = bool(entry and entry.baseline_target in (POINTS_MONTHLY, POINTS_ANNUAL))
    if is_points and ((active_fact is None and has_value) or W_DESIGN_POINTS_MISSING in warnings):
        return B_EXPECTED
    if W_ACTIVE_OUTDATED in warnings or W_DRAFT_VS_ACTIVE in warnings:
        return B_REPORTING
    if W_NEEDS_REVIEW in warnings:
        return B_LOWERS_CONFIDENCE
    if status == S_SUPERSEDED or W_FACT_VS_LEGACY in warnings:
        return B_INFORMATIONAL
    return None


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
    retired = ctx.retired_by_name.get(canonical_name, [])
    candidate_primary = _candidate_value(candidates)
    candidate_accepted = candidate_primary is not None and _is_accepted_candidate(
        candidate_primary
    )
    primary = active_fact or candidate_primary  # the fact backing the row, if any

    # Document-chain fallbacks are consulted ONLY when no fact exists, so a fact
    # always wins over a bare key/run (which is what the ladder demands).
    matched_key: Optional[DocumentKey] = None
    ai_extract: Optional[dict] = None
    if primary is None:
        matched_key = _best_key(ctx.keys_by_canonical.get(canonical_name, []))
        ai_extract = ctx.ai_values_by_canonical.get(canonical_name)

    # --- Provenance / values (fact -> accepted key -> AI run, in that order) ---
    if primary is not None:
        ai_raw = _unwrap(primary.ai_extracted_value)
        accepted_raw = _unwrap(primary.value)
    else:
        ai_raw = ai_extract.get("value") if ai_extract else None
        accepted_raw = _effective_key_value(matched_key) if matched_key else None
    active_raw = _unwrap(active_fact.value) if active_fact else None

    if primary is not None and primary.evidence:
        evidence = primary.evidence or {}
    elif ai_extract is not None and isinstance(ai_extract.get("evidence"), dict):
        evidence = ai_extract["evidence"]
    else:
        evidence = {}

    if primary is not None:
        confidence = (
            float(primary.ai_confidence) if primary.ai_confidence is not None else None
        )
    elif ai_extract is not None:
        confidence = _to_float(ai_extract.get("confidence"))
    else:
        confidence = None

    # --- Baseline values (read verbatim; never recomputed) ---
    draft_raw = None
    active_baseline_raw = None
    if baseline_target == HEADER_COLUMN:
        draft_raw = getattr(ctx.wam_draft, canonical_name, None) if ctx.wam_draft else None
        active_baseline_raw = (
            getattr(ctx.wam_active, canonical_name, None) if ctx.wam_active else None
        )
    elif baseline_target == POINTS_MONTHLY and entry and entry.month:
        draft_raw = ctx.de_draft_points.monthly.get(entry.month)
        active_baseline_raw = ctx.de_active_points.monthly.get(entry.month)
    elif baseline_target == POINTS_ANNUAL:
        draft_raw = ctx.de_draft_points.annual
        active_baseline_raw = ctx.de_active_points.annual

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
        status = S_IN_ACTIVE_BASELINE
    elif active_fact and present_in_draft:
        status = S_IN_DRAFT_BASELINE
    elif active_fact:
        status = S_ACTIVE_FACT
    elif candidate_primary and candidate_accepted:
        status = S_ACCEPTED_NOT_PROMOTED
    elif candidate_primary:
        status = S_CANDIDATE_ONLY
    elif matched_key is not None:
        status = S_ACCEPTED_DOCUMENT_VALUE
    elif ai_extract is not None:
        status = S_AI_EXTRACTED_ONLY
    elif retired:
        status = S_SUPERSEDED
    else:
        status = S_MISSING

    has_value = primary is not None or matched_key is not None or ai_extract is not None

    # --- Warnings (orthogonal to status) ---
    # The "missing required" warning fires ONLY when the value is truly absent
    # everywhere in the chain. When the value exists but is merely unpromoted
    # (candidate/accepted/ai), the gap is carried by ``blocking_level`` +
    # ``required_action`` instead — never as a misleading "Requires Value".
    warnings: list[str] = []
    required = bool(entry and entry.required_for_baseline)
    if required and status == S_MISSING:
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

    # ``needs_review`` is reserved for a GENUINE conflict a human must resolve —
    # not for the ordinary "one accepted value awaiting promotion" case. Equal
    # sibling candidates are merely counted (candidate_count), never flagged.
    needs_review = False
    if active_fact is not None and candidates:
        for cand in candidates:
            if _differs(_unwrap(cand.value), active_raw):
                needs_review = True  # (a) a competing candidate disagrees with active
                break
    if not needs_review and active_fact is None and len(candidates) > 1:
        distinct = {
            _stable_key(_unwrap(cand.value))
            for cand in candidates
            if _is_accepted_candidate(cand)
        }
        if len(distinct) > 1:  # (b) multiple distinct accepted candidates conflict
            needs_review = True
    if (
        not needs_review
        and _baseline_driving(entry)
        and primary is not None
        and primary.overridden_at is not None
        and not (primary.override_notes or "").strip()
    ):
        needs_review = True  # (c) baseline-driving override with no rationale
    if needs_review:
        warnings.append(W_NEEDS_REVIEW)

    # --- Presentation: label / explanation / action / blocking level ---
    status_ctx = {
        "driving": _baseline_driving(entry),
        "has_relevant_active_baseline": active_baseline is not None,
        "active_outdated": W_ACTIVE_OUTDATED in warnings,
    }
    status_label = _STATUS_LABELS.get(status)
    status_explanation = _STATUS_EXPLANATIONS.get(status)
    required_action = _required_action(status, required=required, status_ctx=status_ctx)
    blocking_level = _blocking_level(
        status,
        warnings,
        required=required,
        active_fact=active_fact,
        entry=entry,
        has_value=has_value,
    )
    missing_dependencies = list(_MISSING_DEPENDENCIES.get(status, []))

    # --- Navigation handles (read-only deep-link hints) ---
    if primary is not None:
        source_file_id = primary.source_file_id
        ai_run_id = primary.source_run_id
        document_key_id = primary.source_document_key_id
    elif matched_key is not None:
        source_file_id = matched_key.file_id
        ai_run_id = ai_extract.get("run_id") if ai_extract else None
        document_key_id = matched_key.id
    elif ai_extract is not None:
        source_file_id = ai_extract.get("file_id")
        ai_run_id = ai_extract.get("run_id")
        document_key_id = None
    else:
        source_file_id = None
        ai_run_id = None
        document_key_id = None

    document_id = (
        ctx.file_to_document.get(source_file_id) if source_file_id is not None else None
    )
    if document_id is None and matched_key is not None:
        document_id = matched_key.document_id

    baseline_id = None
    baseline_point_id = None
    if status == S_IN_ACTIVE_BASELINE:
        baseline_id = getattr(active_baseline, "id", None)
        pts = ctx.de_active_points
    elif status == S_IN_DRAFT_BASELINE:
        baseline_id = getattr(draft_baseline, "id", None)
        pts = ctx.de_draft_points
    else:
        pts = None
    if pts is not None:
        if baseline_target == POINTS_MONTHLY and entry and entry.month:
            baseline_point_id = pts.monthly_ids.get(entry.month)
        elif baseline_target == POINTS_ANNUAL:
            baseline_point_id = pts.annual_id

    aliases_matched = sorted(ctx.aliases_by_canonical.get(canonical_name, set()))

    return ReconciliationRow(
        canonical_field=canonical_name,
        display_label=display_label,
        category=category,
        baseline_target=baseline_target,
        status=status,
        status_label=status_label,
        status_explanation=status_explanation,
        required_action=required_action,
        blocking_level=blocking_level,
        missing_dependencies=missing_dependencies,
        ai_extracted_value=_to_jsonable(ai_raw),
        accepted_value=_to_jsonable(accepted_raw),
        active_fact_value=_to_jsonable(active_raw),
        draft_baseline_value=_to_jsonable(draft_raw),
        active_baseline_value=_to_jsonable(active_baseline_raw),
        legacy_value=_to_jsonable(legacy_raw),
        fact_id=primary.id if primary else None,
        project_fact_id=primary.id if primary else None,
        source_file_id=source_file_id,
        source_document_type=primary.source_document_type if primary else None,
        source_run_id=ai_run_id,
        evidence_page=evidence.get("page"),
        evidence_snippet=evidence.get("snippet"),
        confidence=confidence,
        effective_from=active_fact.effective_from if active_fact else None,
        effective_to=active_fact.effective_to if active_fact else None,
        document_id=document_id,
        document_version_id=source_file_id,
        ai_run_id=ai_run_id,
        document_key_id=document_key_id,
        baseline_id=baseline_id,
        baseline_point_id=baseline_point_id,
        aliases_matched=aliases_matched,
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
