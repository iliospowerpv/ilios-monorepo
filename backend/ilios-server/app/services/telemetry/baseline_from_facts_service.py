"""DD V2 Phase 2 — bridge from promoted ``project_facts`` to a draft baseline.

Builds a ``draft`` :class:`TelemetryExpectedBaseline` from a site's ACTIVE /
human-promoted ``project_facts`` (the canonical, audited source of truth),
completed with reviewer-supplied physics constants that have no fact source
today. The bridge is deliberately conservative:

* It creates a ``draft`` ONLY — never ``approved`` / ``active``. The existing
  approve + activate lifecycle (and the single-active backstop) is untouched.
* It NEVER overwrites an existing active baseline.
* It NEVER fabricates a missing value. A required field with no source-backed
  fact (and no reviewer value) is reported as ``missing`` and blocks creation.
* It reads baseline-driving assumptions from ``project_facts`` ONLY — it never
  reads :class:`SiteAdditionalFieldList`. It therefore calls the legacy
  ``create_draft`` with ``site_additional=None`` so the legacy snapshot path can
  never fire. The legacy bridge stays side-by-side and is not repointed.

The diligence fact store (see :data:`FACT_FIELD_TO_COLUMN`) only captures four of
the nine :data:`REQUIRED_PHYSICS_FIELDS` (module / inverter wattage + quantity).
The remaining five datasheet constants have no canonical field, so a reviewer
supplies them on the create request; every value records its provenance
(``project_fact`` vs ``reviewer_supplied``) in ``model_parameters_json``.
"""
from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field as dc_field
from datetime import date
from typing import Optional

from sqlalchemy.orm import Session

from app.crud.project_fact import ProjectFactCRUD
from app.crud.telemetry_expected import TelemetryExpectedBaselineCRUD
from app.models.file import File
from app.models.telemetry_expected import (
    TelemetryBaselineSource,
    TelemetryBaselineStatus,
    TelemetryBaselineType,
    TelemetryExpectedBaseline,
)
from app.services.telemetry.expected_service import REQUIRED_PHYSICS_FIELDS

logger = logging.getLogger(__name__)

# Canonical field NAME (normalized) -> baseline physics column. These four are
# the ONLY ``REQUIRED_PHYSICS_FIELDS`` captured as baseline-driving project_facts
# (see ``DueDiligenceBQKeys``); the canonical names match the column names.
FACT_FIELD_TO_COLUMN: dict[str, str] = {
    "module_wattage": "module_wattage",
    "module_quantity": "module_quantity",
    "inverter_wattage": "inverter_wattage",
    "inverter_quantity": "inverter_quantity",
}

# The single fact used as the header ``source_project_fact_id`` (the full fact
# list always lives in ``model_parameters_json['source_facts']``).
PRIMARY_FACT_FIELD = "module_wattage"

# Required physics constants with NO fact source — supplied by the reviewer.
REVIEWER_REQUIRED_FIELDS: tuple[str, ...] = tuple(
    name for name in REQUIRED_PHYSICS_FIELDS if name not in FACT_FIELD_TO_COLUMN
)

# Loss columns the reviewer MAY supply. Absence is a warning, never a blocker:
# the calc defaults them to 0 %. Reviewer values are sign-normalized to positive
# percent (mirrors the legacy snapshot), as the formula subtracts a positive %.
OPTIONAL_LOSS_FIELDS: tuple[str, ...] = (
    "dc_loss_pct",
    "ac_loss_pct",
    "medium_voltage_loss_pct",
    "mv_line_loss_pct",
)

# Default name for a generated draft (``baseline_name`` is NOT NULL).
_DEFAULT_NAME_PREFIX = "Diligence facts baseline"


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class FieldUsage:
    """One resolved physics input feeding the draft."""

    field: str  # baseline physics column
    source: str  # 'project_fact' | 'reviewer_supplied'
    value: float
    canonical_name: Optional[str] = None
    fact_id: Optional[int] = None
    document_id: Optional[int] = None
    ai_confidence: Optional[float] = None


@dataclass(frozen=True)
class ReadinessResult:
    ready: bool
    fields_used: list[FieldUsage]
    missing_fields: list[str]
    warnings: list[str]
    source_fact_ids: list[int]
    source_document_ids: list[int]


@dataclass(frozen=True)
class _Evaluation:
    """Internal: full resolution result shared by readiness + create."""

    ready: bool
    fields_used: list[FieldUsage]
    missing_fields: list[str]
    warnings: list[str]
    source_fact_ids: list[int]
    source_document_ids: list[int]
    # create-only artefacts
    column_values: dict = dc_field(default_factory=dict)
    field_sources: dict = dc_field(default_factory=dict)
    source_facts: list = dc_field(default_factory=list)
    ai_confidence_json: dict = dc_field(default_factory=dict)
    primary_fact_id: Optional[int] = None
    header_document_id: Optional[int] = None
    signature: str = ""

    def readiness(self) -> ReadinessResult:
        return ReadinessResult(
            ready=self.ready,
            fields_used=self.fields_used,
            missing_fields=self.missing_fields,
            warnings=self.warnings,
            source_fact_ids=self.source_fact_ids,
            source_document_ids=self.source_document_ids,
        )


@dataclass(frozen=True)
class CreateDraftResult:
    readiness: ReadinessResult
    baseline: Optional[TelemetryExpectedBaseline]
    created: bool  # True if a new row was inserted; False if an existing draft was reused
    idempotent_existing: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _unwrap(value):
    """Unwrap the ``{"v": ...}`` JSONB envelope used by ``project_facts.value``."""
    if isinstance(value, dict) and "v" in value:
        return value["v"]
    return value


def _coerce_number(raw) -> Optional[float]:
    """Coerce a fact value to ``float``; return ``None`` when not numeric.

    Never guesses: a non-numeric value yields ``None`` (reported as missing).
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


def _abs_or_none(value):
    return None if value is None else abs(value)


def _doc_id_for_file(db: Session, file_id: Optional[int]) -> Optional[int]:
    if file_id is None:
        return None
    row = db.query(File.document_id).filter(File.id == file_id).one_or_none()
    return None if row is None else row[0]


def _resolve_active_facts(db: Session, site_id: int) -> dict:
    """``{canonical_name: (fact, numeric_value, raw_value)}`` for baseline facts.

    Only active facts whose canonical name maps to a baseline physics column are
    returned. If duplicate active facts exist for one field (should not happen),
    the highest id (most recent) wins.
    """
    resolved: dict = {}
    for fact in ProjectFactCRUD(db).get_active_facts_for_site(site_id):
        canonical = fact.canonical_field
        if canonical is None:
            continue
        name = canonical.name
        if name not in FACT_FIELD_TO_COLUMN:
            continue
        existing = resolved.get(name)
        if existing is not None and existing[0].id >= fact.id:
            continue
        raw = _unwrap(fact.value)
        resolved[name] = (fact, _coerce_number(raw), raw)
    return resolved


def _unit_warnings(column: str, value: float) -> list[str]:
    """Plausibility warnings for the W-vs-kW unit hazard (never auto-converts)."""
    warnings: list[str] = []
    if column == "module_wattage" and value < 50:
        warnings.append(
            f"module_wattage={value} looks low for watts (modules are typically "
            "250-900 W) — verify units; values are never auto-converted."
        )
    if column == "inverter_wattage" and value > 1000:
        warnings.append(
            f"inverter_wattage={value} looks high for kilowatts (the calc treats "
            "inverter_wattage as kW) — verify units; values are never auto-converted."
        )
    return warnings


# ---------------------------------------------------------------------------
# Core evaluation
# ---------------------------------------------------------------------------
def _evaluate(
    db: Session,
    site_id: int,
    baseline_type: TelemetryBaselineType,
    reviewer_values: Optional[dict] = None,
) -> _Evaluation:
    reviewer_values = reviewer_values or {}

    facts = _resolve_active_facts(db, site_id)

    fields_used: list[FieldUsage] = []
    missing_fields: list[str] = []
    warnings: list[str] = []
    column_values: dict = {}
    field_sources: dict = {}
    source_facts: list = []
    ai_confidence_json: dict = {}
    source_fact_ids: list[int] = []
    source_document_ids: list[int] = []
    primary_fact_id: Optional[int] = None
    fact_doc_ids: set = set()

    # 1) Fact-backed required fields (module / inverter wattage + quantity).
    for canonical_name, column in FACT_FIELD_TO_COLUMN.items():
        entry = facts.get(canonical_name)
        if entry is None:
            missing_fields.append(column)
            continue
        fact, numeric, raw = entry
        if numeric is None:
            missing_fields.append(column)
            warnings.append(
                f"{column}: active fact #{fact.id} value {raw!r} is not numeric — "
                "treated as missing (never guessed)."
            )
            continue
        document_id = _doc_id_for_file(db, fact.source_file_id)
        confidence = (
            float(fact.ai_confidence) if fact.ai_confidence is not None else None
        )
        fields_used.append(
            FieldUsage(
                field=column,
                source="project_fact",
                value=numeric,
                canonical_name=canonical_name,
                fact_id=fact.id,
                document_id=document_id,
                ai_confidence=confidence,
            )
        )
        warnings.extend(_unit_warnings(column, numeric))
        column_values[column] = numeric
        field_sources[column] = {
            "source": "project_fact",
            "fact_id": fact.id,
            "document_id": document_id,
            "ai_confidence": confidence,
        }
        source_facts.append(
            {
                "canonical_name": canonical_name,
                "column": column,
                "fact_id": fact.id,
                "value": numeric,
                "document_id": document_id,
                "ai_confidence": confidence,
            }
        )
        if confidence is not None:
            ai_confidence_json[canonical_name] = confidence
        source_fact_ids.append(fact.id)
        if document_id is not None:
            fact_doc_ids.add(document_id)
        if canonical_name == PRIMARY_FACT_FIELD:
            primary_fact_id = fact.id

    # 2) Reviewer-supplied required datasheet constants (no fact source exists).
    for column in REVIEWER_REQUIRED_FIELDS:
        supplied = reviewer_values.get(column)
        numeric = _coerce_number(supplied)
        if numeric is None:
            missing_fields.append(column)
            continue
        fields_used.append(
            FieldUsage(field=column, source="reviewer_supplied", value=numeric)
        )
        column_values[column] = numeric
        field_sources[column] = {"source": "reviewer_supplied"}

    # 3) Optional supplemental inputs — absence is a warning, never a blocker.
    missing_optional: list[str] = []
    for column in OPTIONAL_LOSS_FIELDS:
        numeric = _coerce_number(reviewer_values.get(column))
        if numeric is None:
            missing_optional.append(column)
            continue
        normalized = abs(numeric)
        column_values[column] = normalized
        field_sources[column] = {"source": "reviewer_supplied"}
        fields_used.append(
            FieldUsage(field=column, source="reviewer_supplied", value=normalized)
        )
    if missing_optional:
        warnings.append(
            "No reviewer value for "
            + ", ".join(missing_optional)
            + " — the calc applies a 0% default for these losses."
        )

    soiling = _coerce_number(reviewer_values.get("soiling_factor"))
    if soiling is not None:
        column_values["soiling_factor"] = soiling
        field_sources["soiling_factor"] = {"source": "reviewer_supplied"}
        fields_used.append(
            FieldUsage(field="soiling_factor", source="reviewer_supplied", value=soiling)
        )
    else:
        warnings.append(
            "No soiling_factor supplied — the calc applies the 1.0 (no-soiling) default."
        )

    pto = reviewer_values.get("pto_date")
    if isinstance(pto, date):
        column_values["pto_date"] = pto
        field_sources["pto_date"] = {"source": "reviewer_supplied"}
    else:
        warnings.append(
            "No PTO date supplied — expected production is NULL before PTO "
            "(honest pre-PTO handling, never fabricated)."
        )

    source_document_ids = sorted(fact_doc_ids)
    header_document_id = source_document_ids[0] if len(fact_doc_ids) == 1 else None

    ready = len(missing_fields) == 0

    signature = _signature(baseline_type, source_facts, reviewer_values)

    return _Evaluation(
        ready=ready,
        fields_used=fields_used,
        missing_fields=missing_fields,
        warnings=warnings,
        source_fact_ids=sorted(set(source_fact_ids)),
        source_document_ids=source_document_ids,
        column_values=column_values,
        field_sources=field_sources,
        source_facts=source_facts,
        ai_confidence_json=ai_confidence_json,
        primary_fact_id=primary_fact_id,
        header_document_id=header_document_id,
        signature=signature,
    )


def _signature(
    baseline_type: TelemetryBaselineType,
    source_facts: list,
    reviewer_values: dict,
) -> str:
    """Deterministic dedupe key over the contributing facts ∪ reviewer payload.

    Two creates collapse to one draft only when BOTH the fact values and the
    reviewer-supplied values are identical (so changed constants force a new
    draft, not a wrong dedupe).
    """
    fact_part = {f["canonical_name"]: f["value"] for f in source_facts}
    reviewer_part = {
        key: value
        for key, value in sorted(reviewer_values.items())
        if value is not None
    }
    payload = {
        "baseline_type": baseline_type.value,
        "facts": fact_part,
        "reviewer": reviewer_part,
    }
    encoded = json.dumps(payload, sort_keys=True, default=str).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _next_version(
    db: Session, site_id: int, baseline_type: TelemetryBaselineType
) -> int:
    rows = (
        db.query(TelemetryExpectedBaseline.version)
        .filter(
            TelemetryExpectedBaseline.site_id == site_id,
            TelemetryExpectedBaseline.baseline_type == baseline_type,
        )
        .all()
    )
    versions = [row[0] for row in rows if row[0] is not None]
    return (max(versions) + 1) if versions else 1


def _find_idempotent_draft(
    db: Session,
    site_id: int,
    baseline_type: TelemetryBaselineType,
    signature: str,
) -> Optional[TelemetryExpectedBaseline]:
    """An existing ``draft`` diligence baseline with the same signature, if any.

    Scoped to ``draft`` only — approved/active baselines are never short-circuited
    (a matching signature there still yields a brand-new draft).
    """
    drafts = (
        db.query(TelemetryExpectedBaseline)
        .filter(
            TelemetryExpectedBaseline.site_id == site_id,
            TelemetryExpectedBaseline.baseline_type == baseline_type,
            TelemetryExpectedBaseline.status == TelemetryBaselineStatus.draft,
            TelemetryExpectedBaseline.source_type
            == TelemetryBaselineSource.diligence_ai_parse,
        )
        .all()
    )
    for draft in drafts:
        params = draft.model_parameters_json or {}
        if params.get("source_fact_signature") == signature:
            return draft
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def evaluate_readiness(
    db: Session,
    site_id: int,
    baseline_type: TelemetryBaselineType = TelemetryBaselineType.weather_adjusted_model,
) -> ReadinessResult:
    """Report whether promoted facts can produce a draft (facts only, no payload).

    Always reports the FULL required physics set: module / inverter fields come
    from facts; the reviewer-only datasheet constants are always ``missing`` here
    (they are supplied on the create request), so ``ready`` is True only when no
    required field is outstanding.
    """
    return _evaluate(db, site_id, baseline_type, reviewer_values=None).readiness()


def create_draft_from_facts(
    db: Session,
    *,
    company_id: int,
    site_id: int,
    site_timezone: Optional[str],
    baseline_type: TelemetryBaselineType = TelemetryBaselineType.weather_adjusted_model,
    reviewer_values: Optional[dict] = None,
    baseline_name: Optional[str] = None,
    reason: Optional[str] = None,
    created_by_user_id: Optional[int] = None,
) -> CreateDraftResult:
    """Create a ``draft`` baseline from promoted facts ∪ reviewer constants.

    Returns a not-ready result (no row created) when any required physics field
    is missing — the caller surfaces a 422 ``review_required``. When ready: an
    existing draft with the same signature is returned unchanged (idempotent);
    otherwise a new draft is inserted at ``version = max(version)+1``.
    """
    reviewer_values = reviewer_values or {}
    evaluation = _evaluate(db, site_id, baseline_type, reviewer_values)
    if not evaluation.ready:
        return CreateDraftResult(
            readiness=evaluation.readiness(),
            baseline=None,
            created=False,
            idempotent_existing=False,
        )

    existing = _find_idempotent_draft(
        db, site_id, baseline_type, evaluation.signature
    )
    if existing is not None:
        logger.info(
            "baseline_from_facts idempotent hit site_id=%s baseline_id=%s",
            site_id,
            existing.id,
        )
        return CreateDraftResult(
            readiness=evaluation.readiness(),
            baseline=existing,
            created=False,
            idempotent_existing=True,
        )

    version = _next_version(db, site_id, baseline_type)
    name = baseline_name or f"{_DEFAULT_NAME_PREFIX} v{version}"

    loss_assumptions = {
        column: evaluation.column_values[column]
        for column in OPTIONAL_LOSS_FIELDS
        if column in evaluation.column_values
    }
    if "soiling_factor" in evaluation.column_values:
        loss_assumptions["soiling_factor"] = evaluation.column_values["soiling_factor"]

    model_parameters = {
        "source": "diligence_ai_parse_bridge",
        "created_from": "promoted_project_facts",
        "source_fact_signature": evaluation.signature,
        "version": version,
        "field_sources": evaluation.field_sources,
        "source_facts": evaluation.source_facts,
        "warnings": evaluation.warnings,
    }

    payload: dict = {
        "baseline_name": name,
        "baseline_type": baseline_type,
        "source_type": TelemetryBaselineSource.diligence_ai_parse,
        "source_project_fact_id": evaluation.primary_fact_id,
        "source_document_id": evaluation.header_document_id,
        "model_parameters_json": model_parameters,
        "ai_confidence_json": evaluation.ai_confidence_json or None,
        "loss_assumptions_json": loss_assumptions or None,
    }
    if reason:
        payload["notes"] = reason
    payload.update(evaluation.column_values)

    baseline = TelemetryExpectedBaselineCRUD(db).create_draft(
        company_id=company_id,
        site_id=site_id,
        payload=payload,
        site_additional=None,  # NEVER read SiteAdditionalFieldList for this bridge.
        site_timezone=site_timezone,
        created_by_user_id=created_by_user_id,
        version=version,
    )
    logger.info(
        "baseline_from_facts created site_id=%s baseline_id=%s version=%s",
        site_id,
        baseline.id,
        version,
    )
    return CreateDraftResult(
        readiness=evaluation.readiness(),
        baseline=baseline,
        created=True,
        idempotent_existing=False,
    )
