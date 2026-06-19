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
from datetime import date, datetime, timezone
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
from app.services.telemetry import baseline_input_normalization as input_norm
from app.services.telemetry.baseline_input_normalization import NormalizationProposal
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

# The authoritative set of canonical field NAMES whose promoted facts drive the
# expected/baseline math (see ``FACT_FIELD_TO_COLUMN``). Exposed as a frozen set
# so callers (e.g. the promotion freshness guard) can classify a fact as
# baseline-driving without coupling to the column-mapping dict or inventing a
# broader set. This is the ONLY canonical set that feeds the draft baseline today.
BASELINE_DRIVING_FACT_FIELDS: frozenset[str] = frozenset(FACT_FIELD_TO_COLUMN)

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
# Structured per-field readiness vocabulary
# ---------------------------------------------------------------------------
class SourceStatus:
    """Where a single baseline input currently stands (additive, descriptive)."""

    MISSING = "missing"
    ACTIVE_FACT = "active_fact"
    ACTIVE_FACT_NON_NUMERIC = "active_fact_but_non_numeric"
    NORMALIZED_CONFIRMED = "normalized_confirmed"
    REVIEWER_SUPPLIED_NEEDED = "reviewer_supplied_needed"
    REVIEWER_SUPPLIED = "reviewer_supplied"
    OPTIONAL_DEFAULT_APPLIED = "optional_default_applied"
    OPTIONAL_VALUE_SUPPLIED = "optional_value_supplied"
    PRE_PTO_EXPECTED_SUPPRESSED = "pre_pto_expected_suppressed"
    SATISFIED = "satisfied"


class BlockingLevel:
    """How severely an unmet input blocks the baseline-readiness ladder.

    Distinct from the reconciliation blocking levels on purpose — this set is
    scoped to the facts → draft-baseline action.
    """

    BLOCKS_DRAFT = "blocks_draft_baseline"
    BLOCKS_ACTIVE = "blocks_active_baseline"
    BLOCKS_EXPECTED = "blocks_expected"
    LOWERS_CONFIDENCE = "lowers_confidence"
    INFORMATIONAL = "informational"


@dataclass(frozen=True)
class _FieldMeta:
    display_label: str
    expected_type: str  # 'number' | 'count' | 'percent' | 'factor' | 'date'
    expected_unit: Optional[str]
    required: bool
    recommended_action: str
    default_value: Optional[float] = None


# Static presentation/metadata for every baseline input the panel surfaces.
FIELD_METADATA: dict[str, _FieldMeta] = {
    "module_wattage": _FieldMeta(
        "Module Wattage", "number", "W", True,
        "Promote the per-module STC wattage in the Data Room.",
    ),
    "module_quantity": _FieldMeta(
        "Module Quantity", "count", None, True,
        "Promote the module quantity in the Data Room.",
    ),
    "inverter_wattage": _FieldMeta(
        "Inverter Rating (AC)", "number", "kW", True,
        "Promote the inverter AC rating (kW) in the Data Room.",
    ),
    "inverter_quantity": _FieldMeta(
        "Inverter Quantity", "count", None, True,
        "Promote the inverter quantity in the Data Room.",
    ),
    "thermal_coefficient_pct": _FieldMeta(
        "Thermal Coefficient (Pmax)", "percent", "%/\u00b0C", True,
        "Enter the module datasheet temperature coefficient of Pmax.",
    ),
    "power_tolerance_min_pct": _FieldMeta(
        "Power Tolerance (min)", "percent", "%", True,
        "Enter the module datasheet negative power tolerance (0 if none).",
    ),
    "year_1_degradation_pct": _FieldMeta(
        "Year-1 Degradation", "percent", "%", True,
        "Enter the module datasheet first-year degradation.",
    ),
    "annual_degradation_pct": _FieldMeta(
        "Annual Degradation", "percent", "%", True,
        "Enter the module datasheet annual degradation.",
    ),
    "cec_efficiency_pct": _FieldMeta(
        "Inverter CEC Efficiency", "percent", "%", True,
        "Enter the inverter datasheet CEC weighted efficiency.",
    ),
    "dc_loss_pct": _FieldMeta(
        "DC Loss", "percent", "%", False,
        "Optional — defaults to 0% when not supplied.", 0.0,
    ),
    "ac_loss_pct": _FieldMeta(
        "AC Loss", "percent", "%", False,
        "Optional — defaults to 0% when not supplied.", 0.0,
    ),
    "medium_voltage_loss_pct": _FieldMeta(
        "Medium-Voltage Loss", "percent", "%", False,
        "Optional — defaults to 0% when not supplied.", 0.0,
    ),
    "mv_line_loss_pct": _FieldMeta(
        "MV Line Loss", "percent", "%", False,
        "Optional — defaults to 0% when not supplied.", 0.0,
    ),
    "soiling_factor": _FieldMeta(
        "Soiling Factor", "factor", None, False,
        "Optional — defaults to 1.0 (no soiling) when not supplied.", 1.0,
    ),
    "pto_date": _FieldMeta(
        "PTO Date", "date", None, False,
        "Optional — without PTO, expected production is NULL before PTO.",
    ),
}


# ---------------------------------------------------------------------------
# Result types
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class FieldBlocker:
    """One baseline input's true position on the readiness ladder.

    Additive/descriptive — surfaced to the actionable panel so a reviewer can see
    exactly what is usable, what needs confirmation, and what to do next. It never
    changes ``ready`` semantics on its own.
    """

    field: str
    display_label: str
    required: bool
    expected_type: str
    expected_unit: Optional[str]
    source_status: str
    blocking_level: str
    current_raw_value: Optional[str] = None
    current_normalized_value: Optional[float] = None
    default_value: Optional[float] = None
    reason: Optional[str] = None
    recommended_action: Optional[str] = None
    fact_id: Optional[int] = None
    document_id: Optional[int] = None
    ai_confidence: Optional[float] = None
    normalization: Optional[NormalizationProposal] = None


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
    field_blockers: list[FieldBlocker] = dc_field(default_factory=list)


@dataclass(frozen=True)
class _Evaluation:
    """Internal: full resolution result shared by readiness + create."""

    ready: bool
    fields_used: list[FieldUsage]
    missing_fields: list[str]
    warnings: list[str]
    source_fact_ids: list[int]
    source_document_ids: list[int]
    field_blockers: list[FieldBlocker] = dc_field(default_factory=list)
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
            field_blockers=self.field_blockers,
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
def _try_apply_normalization(
    proposal: NormalizationProposal,
    conf: Optional[dict],
    fact,
    raw,
) -> tuple[Optional[float], Optional[str]]:
    """Validate a reviewer's normalization confirmation against a fresh recompute.

    Returns ``(applied_value, None)`` when the confirmation is honored, or
    ``(None, reject_reason)`` otherwise. The server NEVER trusts the front end's
    parsed number — it applies its OWN recomputed ``proposed_value`` and only when:

    * the confirmation carries BOTH anchors and still references the current fact
      (``source_fact_id`` / ``raw_value`` are required and must match — missing or
      stale confirmations are rejected),
    * the proposal is not blocked,
    * a unit *conversion* (not a plain strip) carries an explicit
      ``allow_conversion`` flag, and
    * the reviewer's ``confirmed_value`` agrees with the server value (integrity
      cross-check — a mismatch means the inputs drifted).
    """
    if not conf:
        return None, None  # no confirmation supplied — stays missing

    conf_fact_id = conf.get("source_fact_id")
    if conf_fact_id is None:
        return None, (
            "Normalization confirmation is missing its source fact reference — "
            "re-confirm the normalization."
        )
    if conf_fact_id != fact.id:
        return None, (
            f"Confirmation references fact #{conf_fact_id}, but the active fact is "
            f"#{fact.id} — re-confirm the normalization."
        )

    conf_raw = conf.get("raw_value")
    current_raw = "" if raw is None else str(raw).strip()
    if conf_raw is None:
        return None, (
            "Normalization confirmation is missing the original fact value it was "
            "based on — re-confirm the normalization."
        )
    if str(conf_raw).strip() != current_raw:
        return None, (
            "The fact value changed since you confirmed — re-confirm the normalization."
        )

    if proposal.blocked:
        return None, proposal.reason

    if proposal.requires_conversion_confirmation and not conf.get("allow_conversion"):
        return None, (
            "A unit conversion is required — confirm the conversion explicitly to "
            "use this value."
        )

    confirmed = _coerce_number(conf.get("confirmed_value"))
    if not input_norm.values_match(confirmed, proposal.proposed_value):
        return None, (
            "The confirmed value does not match the server-computed normalized "
            f"value ({proposal.proposed_value}) — re-confirm."
        )

    return proposal.proposed_value, None


def _evaluate(
    db: Session,
    site_id: int,
    baseline_type: TelemetryBaselineType,
    reviewer_values: Optional[dict] = None,
    applied_by_user_id: Optional[int] = None,
) -> _Evaluation:
    reviewer_values = reviewer_values or {}
    normalizations = reviewer_values.get("normalizations") or {}

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
    field_blockers: list[FieldBlocker] = []

    def _record_fact_field(
        canonical_name, column, fact, value, document_id, confidence, source, extra
    ):
        nonlocal primary_fact_id
        fields_used.append(
            FieldUsage(
                field=column,
                source=source,
                value=value,
                canonical_name=canonical_name,
                fact_id=fact.id,
                document_id=document_id,
                ai_confidence=confidence,
            )
        )
        warnings.extend(_unit_warnings(column, value))
        column_values[column] = value
        fs = {
            "source": source,
            "fact_id": fact.id,
            "document_id": document_id,
            "ai_confidence": confidence,
        }
        if extra:
            fs.update(extra)
        field_sources[column] = fs
        source_facts.append(
            {
                "canonical_name": canonical_name,
                "column": column,
                "fact_id": fact.id,
                "value": value,
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

    # 1) Fact-backed required fields (module / inverter wattage + quantity).
    for canonical_name, column in FACT_FIELD_TO_COLUMN.items():
        meta = FIELD_METADATA[column]
        entry = facts.get(canonical_name)
        if entry is None:
            missing_fields.append(column)
            field_blockers.append(
                FieldBlocker(
                    field=column,
                    display_label=meta.display_label,
                    required=True,
                    expected_type=meta.expected_type,
                    expected_unit=meta.expected_unit,
                    source_status=SourceStatus.MISSING,
                    blocking_level=BlockingLevel.BLOCKS_DRAFT,
                    reason="No active promoted fact for this field.",
                    recommended_action=meta.recommended_action,
                )
            )
            continue

        fact, numeric, raw = entry
        document_id = _doc_id_for_file(db, fact.source_file_id)
        confidence = (
            float(fact.ai_confidence) if fact.ai_confidence is not None else None
        )
        raw_str = None if raw is None else str(raw)

        if numeric is not None:
            _record_fact_field(
                canonical_name, column, fact, numeric,
                document_id, confidence, "project_fact", None,
            )
            field_blockers.append(
                FieldBlocker(
                    field=column,
                    display_label=meta.display_label,
                    required=True,
                    expected_type=meta.expected_type,
                    expected_unit=meta.expected_unit,
                    source_status=SourceStatus.ACTIVE_FACT,
                    blocking_level=BlockingLevel.INFORMATIONAL,
                    current_raw_value=raw_str,
                    current_normalized_value=numeric,
                    fact_id=fact.id,
                    document_id=document_id,
                    ai_confidence=confidence,
                )
            )
            continue

        # Non-numeric fact. Quantities are unitless counts — never normalized.
        if not input_norm.is_normalizable_field(column):
            missing_fields.append(column)
            warnings.append(
                f"{column}: active fact #{fact.id} value {raw!r} is not numeric — "
                "treated as missing (never guessed)."
            )
            field_blockers.append(
                FieldBlocker(
                    field=column,
                    display_label=meta.display_label,
                    required=True,
                    expected_type=meta.expected_type,
                    expected_unit=meta.expected_unit,
                    source_status=SourceStatus.ACTIVE_FACT_NON_NUMERIC,
                    blocking_level=BlockingLevel.BLOCKS_DRAFT,
                    current_raw_value=raw_str,
                    reason=f"Active fact value {raw!r} is not a number.",
                    recommended_action=meta.recommended_action,
                    fact_id=fact.id,
                    document_id=document_id,
                    ai_confidence=confidence,
                )
            )
            continue

        # Unit-bearing physics field: propose a normalization, apply ONLY on a
        # valid reviewer confirmation (never silently).
        proposal = input_norm.propose(column, raw)
        applied_value, reject_reason = _try_apply_normalization(
            proposal, normalizations.get(column), fact, raw
        )
        if applied_value is not None:
            _record_fact_field(
                canonical_name, column, fact, applied_value,
                document_id, confidence, "project_fact_normalized",
                {
                    "normalization": {
                        "raw_value": proposal.raw_value,
                        "normalized_value": applied_value,
                        "from_unit": proposal.from_unit,
                        "to_unit": proposal.target_unit,
                        "method": proposal.method,
                        "factor": proposal.factor,
                        "confirmed_by_user_id": applied_by_user_id,
                        "confirmed_at": datetime.now(timezone.utc).isoformat(),
                    }
                },
            )
            field_blockers.append(
                FieldBlocker(
                    field=column,
                    display_label=meta.display_label,
                    required=True,
                    expected_type=meta.expected_type,
                    expected_unit=meta.expected_unit,
                    source_status=SourceStatus.NORMALIZED_CONFIRMED,
                    blocking_level=BlockingLevel.INFORMATIONAL,
                    current_raw_value=raw_str,
                    current_normalized_value=applied_value,
                    fact_id=fact.id,
                    document_id=document_id,
                    ai_confidence=confidence,
                    normalization=proposal,
                )
            )
            continue

        # Not applied — stays missing (confirmation absent, blocked, or rejected).
        missing_fields.append(column)
        warnings.append(
            f"{column}: active fact #{fact.id} value {raw!r} is not numeric — "
            "treated as missing (never guessed)."
        )
        field_blockers.append(
            FieldBlocker(
                field=column,
                display_label=meta.display_label,
                required=True,
                expected_type=meta.expected_type,
                expected_unit=meta.expected_unit,
                source_status=SourceStatus.ACTIVE_FACT_NON_NUMERIC,
                blocking_level=BlockingLevel.BLOCKS_DRAFT,
                current_raw_value=raw_str,
                reason=reject_reason or proposal.reason,
                recommended_action=(
                    "Confirm the proposed unit normalization to use this value."
                    if not proposal.blocked
                    else meta.recommended_action
                ),
                fact_id=fact.id,
                document_id=document_id,
                ai_confidence=confidence,
                normalization=proposal,
            )
        )

    # 2) Reviewer-supplied required datasheet constants (no fact source exists).
    for column in REVIEWER_REQUIRED_FIELDS:
        meta = FIELD_METADATA[column]
        numeric = _coerce_number(reviewer_values.get(column))
        if numeric is None:
            missing_fields.append(column)
            field_blockers.append(
                FieldBlocker(
                    field=column,
                    display_label=meta.display_label,
                    required=True,
                    expected_type=meta.expected_type,
                    expected_unit=meta.expected_unit,
                    source_status=SourceStatus.REVIEWER_SUPPLIED_NEEDED,
                    blocking_level=BlockingLevel.BLOCKS_DRAFT,
                    reason="No fact source exists for this datasheet constant.",
                    recommended_action=meta.recommended_action,
                )
            )
            continue
        fields_used.append(
            FieldUsage(field=column, source="reviewer_supplied", value=numeric)
        )
        column_values[column] = numeric
        field_sources[column] = {"source": "reviewer_supplied"}
        field_blockers.append(
            FieldBlocker(
                field=column,
                display_label=meta.display_label,
                required=True,
                expected_type=meta.expected_type,
                expected_unit=meta.expected_unit,
                source_status=SourceStatus.REVIEWER_SUPPLIED,
                blocking_level=BlockingLevel.INFORMATIONAL,
                current_normalized_value=numeric,
            )
        )

    # 3) Optional supplemental inputs — absence is informational, never a blocker.
    missing_optional: list[str] = []
    for column in OPTIONAL_LOSS_FIELDS:
        meta = FIELD_METADATA[column]
        numeric = _coerce_number(reviewer_values.get(column))
        if numeric is None:
            missing_optional.append(column)
            field_blockers.append(
                FieldBlocker(
                    field=column,
                    display_label=meta.display_label,
                    required=False,
                    expected_type=meta.expected_type,
                    expected_unit=meta.expected_unit,
                    source_status=SourceStatus.OPTIONAL_DEFAULT_APPLIED,
                    blocking_level=BlockingLevel.INFORMATIONAL,
                    default_value=meta.default_value,
                    reason="No reviewer value — the calc applies the 0% default.",
                    recommended_action=meta.recommended_action,
                )
            )
            continue
        normalized = abs(numeric)
        column_values[column] = normalized
        field_sources[column] = {"source": "reviewer_supplied"}
        fields_used.append(
            FieldUsage(field=column, source="reviewer_supplied", value=normalized)
        )
        field_blockers.append(
            FieldBlocker(
                field=column,
                display_label=meta.display_label,
                required=False,
                expected_type=meta.expected_type,
                expected_unit=meta.expected_unit,
                source_status=SourceStatus.OPTIONAL_VALUE_SUPPLIED,
                blocking_level=BlockingLevel.INFORMATIONAL,
                current_normalized_value=normalized,
            )
        )
    if missing_optional:
        warnings.append(
            "No reviewer value for "
            + ", ".join(missing_optional)
            + " — the calc applies a 0% default for these losses."
        )

    soiling_meta = FIELD_METADATA["soiling_factor"]
    soiling = _coerce_number(reviewer_values.get("soiling_factor"))
    if soiling is not None:
        column_values["soiling_factor"] = soiling
        field_sources["soiling_factor"] = {"source": "reviewer_supplied"}
        fields_used.append(
            FieldUsage(field="soiling_factor", source="reviewer_supplied", value=soiling)
        )
        field_blockers.append(
            FieldBlocker(
                field="soiling_factor",
                display_label=soiling_meta.display_label,
                required=False,
                expected_type=soiling_meta.expected_type,
                expected_unit=soiling_meta.expected_unit,
                source_status=SourceStatus.OPTIONAL_VALUE_SUPPLIED,
                blocking_level=BlockingLevel.INFORMATIONAL,
                current_normalized_value=soiling,
            )
        )
    else:
        warnings.append(
            "No soiling_factor supplied — the calc applies the 1.0 (no-soiling) default."
        )
        field_blockers.append(
            FieldBlocker(
                field="soiling_factor",
                display_label=soiling_meta.display_label,
                required=False,
                expected_type=soiling_meta.expected_type,
                expected_unit=soiling_meta.expected_unit,
                source_status=SourceStatus.OPTIONAL_DEFAULT_APPLIED,
                blocking_level=BlockingLevel.INFORMATIONAL,
                default_value=soiling_meta.default_value,
                reason="No soiling_factor — the calc applies the 1.0 (no-soiling) default.",
                recommended_action=soiling_meta.recommended_action,
            )
        )

    pto_meta = FIELD_METADATA["pto_date"]
    pto = reviewer_values.get("pto_date")
    if isinstance(pto, date):
        column_values["pto_date"] = pto
        field_sources["pto_date"] = {"source": "reviewer_supplied"}
        field_blockers.append(
            FieldBlocker(
                field="pto_date",
                display_label=pto_meta.display_label,
                required=False,
                expected_type=pto_meta.expected_type,
                expected_unit=pto_meta.expected_unit,
                source_status=SourceStatus.SATISFIED,
                blocking_level=BlockingLevel.INFORMATIONAL,
                current_raw_value=str(pto),
            )
        )
    else:
        warnings.append(
            "No PTO date supplied — expected production is NULL before PTO "
            "(honest pre-PTO handling, never fabricated)."
        )
        field_blockers.append(
            FieldBlocker(
                field="pto_date",
                display_label=pto_meta.display_label,
                required=False,
                expected_type=pto_meta.expected_type,
                expected_unit=pto_meta.expected_unit,
                source_status=SourceStatus.PRE_PTO_EXPECTED_SUPPRESSED,
                blocking_level=BlockingLevel.BLOCKS_EXPECTED,
                reason="No PTO date — expected production is NULL before PTO.",
                recommended_action=pto_meta.recommended_action,
            )
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
        field_blockers=field_blockers,
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
    evaluation = _evaluate(
        db,
        site_id,
        baseline_type,
        reviewer_values,
        applied_by_user_id=created_by_user_id,
    )
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
