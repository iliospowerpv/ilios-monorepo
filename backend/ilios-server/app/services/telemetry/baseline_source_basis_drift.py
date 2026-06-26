"""Read-only source-basis drift / staleness resolver (Phase B4, D1-D3).

Given the single ACTIVE ``weather_adjusted_model`` baseline and the current
active ``project_facts``, this module reports — by VALUE, never by timestamp or
fact-id membership — whether each fact-backed baseline input still matches the
basis that was recorded when the active baseline was built.

It is a pure, read-only resolver: it performs no flush, no commit, no write, no
promotion, and no baseline recomputation. Every ambiguous or unrecorded case
resolves to a neutral / informational state — a value is reported as
``drifted`` ONLY when the normalized current value can be POSITIVELY shown to
differ from the recorded basis. This is what eliminates the historical Site 4
false positive (a new fact id carrying the *same* value is NOT drift) and the
"basis not recorded" misclassification.

The comparison deliberately mirrors the bridge's own ordering in
:mod:`app.services.telemetry.baseline_from_facts_service` (plain numeric
coercion first, then unit normalization for normalizable fields only) so the
resolver and the bridge can never disagree about what a value "is".
"""
from __future__ import annotations

from typing import Optional

from app.models.project_facts import ProjectFact
from app.models.telemetry_expected import TelemetryExpectedBaseline
from app.schema.reconciliation import SourceBasisDrift, SourceBasisDriftField
from app.services.telemetry import baseline_input_normalization as input_norm
from app.services.telemetry.baseline_from_facts_service import (
    FACT_FIELD_TO_COLUMN,
    _coerce_number,
    _unwrap,
)

# Baseline-level rollup vocabulary (also documented on the schema). Precedence:
# basis_unknown > drifted > source_retired > up_to_date (informational ordering,
# not a blocker escalation). ``no_fact_lineage`` never escalates the rollup.
STATE_UP_TO_DATE = "up_to_date"
STATE_DRIFTED = "drifted"
STATE_BASIS_UNKNOWN = "basis_unknown"
STATE_SOURCE_RETIRED = "source_retired"

# The four fact-backed header columns the bridge tracks (canonical == column).
_BRIDGE_COLUMNS = frozenset(FACT_FIELD_TO_COLUMN.values())


def resolve_source_basis_drift(
    baseline: Optional[TelemetryExpectedBaseline],
    active_facts: dict[str, ProjectFact],
    *,
    retired_fact_ids: frozenset[int] = frozenset(),
) -> SourceBasisDrift:
    """Return the value-based source-basis verdict for one active baseline.

    Args:
        baseline: the single ACTIVE ``weather_adjusted_model`` baseline, or
            ``None`` (→ honest empty result, never a 500).
        active_facts: ``{canonical_name -> ProjectFact}`` for ``status=active``.
        retired_fact_ids: ids of retired/superseded facts, used ONLY to decide
            ``source_retired`` when a recorded basis fact id now resolves to a
            retired fact and no active replacement exists.
    """
    # --- No active baseline → honest, empty result. ---
    if baseline is None:
        return SourceBasisDrift(
            state=STATE_BASIS_UNKNOWN,
            baseline_id=None,
            basis_captured_at=None,
            unknown_basis=True,
            drifted_fields=[],
            no_fact_lineage_fields=[],
            note=(
                "No active weather-adjusted baseline exists, so source-basis "
                "drift cannot be evaluated."
            ),
        )

    params = baseline.model_parameters_json or {}
    recorded_signature = params.get("source_fact_signature")
    recorded_field_sources = params.get("field_sources") or {}
    recorded_source_facts = params.get("source_facts") or []

    basis_captured_at = (
        getattr(baseline, "approved_at", None)
        or getattr(baseline, "active_from", None)
        or getattr(baseline, "created_at", None)
    )

    # --- Step 0: baseline-level basis presence gate (fixes Site 4 #4). ---
    # A baseline with NO recorded basis manifest at all (empty source_facts AND
    # NULL signature) cannot be attributed to any fact lineage. We report the
    # basis as unrecorded rather than fabricate drift from the typed columns.
    # ``source_project_fact_id`` alone is NOT a sufficient manifest.
    if not recorded_source_facts and recorded_signature is None:
        return SourceBasisDrift(
            state=STATE_BASIS_UNKNOWN,
            baseline_id=baseline.id,
            basis_captured_at=basis_captured_at,
            unknown_basis=True,
            drifted_fields=[],
            no_fact_lineage_fields=_reviewer_fields(recorded_field_sources),
            note=(
                "This baseline was not built from tracked facts (no recorded "
                "source basis), so source-basis drift cannot be evaluated."
            ),
        )

    recorded_basis_by_field = _recorded_basis_by_field(
        recorded_source_facts, recorded_field_sources
    )

    drifted_fields: list[SourceBasisDriftField] = []
    no_fact_lineage_fields = _reviewer_fields(recorded_field_sources)
    source_retired_any = False

    # --- Step 2: per-field value comparison (the sole authoritative path). ---
    for canonical_name, column in FACT_FIELD_TO_COLUMN.items():
        recorded = recorded_basis_by_field.get(column)
        if recorded is None:
            # Field has no recorded basis on a baseline that DOES record others:
            # individually basis_unknown — never drifted, never escalates.
            continue

        recorded_value = recorded.get("value")
        recorded_fact_id = recorded.get("fact_id")
        basis_float = _to_comparable(column, recorded_value)
        if basis_float is None:
            # Fall back to the immutable typed column only when the snapshot
            # records the field but omits an explicit comparable value.
            basis_float = _column_float(getattr(baseline, column, None))
        display_basis = recorded_value if recorded_value is not None else basis_float

        active_fact = active_facts.get(canonical_name)
        if active_fact is None:
            # No current active fact for this field. Distinguish a retired basis
            # fact (keyed off the RECORDED fact id) from plain missing lineage.
            if isinstance(recorded_fact_id, int) and recorded_fact_id in retired_fact_ids:
                source_retired_any = True
            elif column not in no_fact_lineage_fields:
                no_fact_lineage_fields.append(column)
            continue

        current_raw = _unwrap(active_fact.value)
        current_float = _to_comparable(column, current_raw)

        # Positively unequal → drift; ambiguous / uncoercible on either side →
        # neutral / informational, NEVER drift.
        if (
            basis_float is not None
            and current_float is not None
            and not input_norm.values_match(basis_float, current_float)
        ):
            drifted_fields.append(
                SourceBasisDriftField(
                    field=column,
                    basis_value=display_basis,
                    current_value=current_raw,
                    current_fact_id=active_fact.id,
                )
            )

    # --- Step 5: baseline-level rollup precedence. ---
    if drifted_fields:
        state = STATE_DRIFTED
        note = _drift_note(drifted_fields)
    elif source_retired_any:
        state = STATE_SOURCE_RETIRED
        note = (
            "A recorded source fact has been retired with no active replacement; "
            "rebuild the active baseline to re-establish its source basis."
        )
    else:
        state = STATE_UP_TO_DATE
        note = "Every recorded fact-backed input still matches the active baseline."

    return SourceBasisDrift(
        state=state,
        baseline_id=baseline.id,
        basis_captured_at=basis_captured_at,
        unknown_basis=False,
        drifted_fields=drifted_fields,
        no_fact_lineage_fields=no_fact_lineage_fields,
        note=note,
    )


def _recorded_basis_by_field(source_facts, field_sources) -> dict[str, dict]:
    """Assemble ``column -> {"value", "fact_id"}`` from the recorded snapshot.

    ``source_facts[]`` carries the explicit per-column normalized value; the
    fact-backed ``field_sources{}`` entries carry the recorded fact id but no
    value, so they are used only to fill in a column the ``source_facts`` list
    omitted (value falls back to the typed column at compare time).
    """
    out: dict[str, dict] = {}
    for entry in source_facts or []:
        if not isinstance(entry, dict):
            continue
        column = entry.get("column")
        if not isinstance(column, str) or column not in _BRIDGE_COLUMNS:
            canonical = entry.get("canonical_name")
            column = (
                FACT_FIELD_TO_COLUMN.get(canonical)
                if isinstance(canonical, str)
                else None
            )
        if column is None or column not in _BRIDGE_COLUMNS:
            continue
        out[column] = {"value": entry.get("value"), "fact_id": entry.get("fact_id")}

    for column, src in (field_sources or {}).items():
        if column not in _BRIDGE_COLUMNS or not isinstance(src, dict):
            continue
        if src.get("source") == "reviewer_supplied":
            continue
        if column not in out:
            out[column] = {"value": src.get("value"), "fact_id": src.get("fact_id")}
    return out


def _reviewer_fields(field_sources) -> list[str]:
    """Reviewer-supplied fields (no ``fact_id``) → reported as no-fact-lineage."""
    out: list[str] = []
    for column, src in (field_sources or {}).items():
        if (
            isinstance(column, str)
            and isinstance(src, dict)
            and src.get("source") == "reviewer_supplied"
        ):
            out.append(column)
    return sorted(out)


def _to_comparable(column: str, raw) -> Optional[float]:
    """Coerce a value to ``float`` mirroring the bridge's ordering.

    Plain numeric coercion first; only when that fails (a non-numeric,
    unit-bearing string) and the field is normalizable do we ask
    :func:`input_norm.propose` for a normalized value. Returns ``None`` when no
    comparable number can be established (→ neutral, never drift).
    """
    numeric = _coerce_number(raw)
    if numeric is not None:
        return float(numeric)
    if isinstance(raw, str) and input_norm.is_normalizable_field(column):
        proposal = input_norm.propose(column, raw)
        if proposal is not None and not proposal.blocked and proposal.proposed_value is not None:
            return float(proposal.proposed_value)
    return None


def _column_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _drift_note(drifted_fields: list[SourceBasisDriftField]) -> str:
    n = len(drifted_fields)
    names = ", ".join(f.field for f in drifted_fields)
    return (
        f"{n} fact-backed input{'' if n == 1 else 's'} drifted from the recorded "
        f"basis ({names}). Rebuild the active baseline to include the latest "
        f"promoted value."
    )
