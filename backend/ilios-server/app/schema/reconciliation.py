"""DD V2 Phase 4 — schemas for the read-only assumptions reconciliation view.

The response is a structured, machine-readable audit of how source-backed
diligence facts map into current assumptions and baseline drafts. It is produced
by :mod:`app.services.due_diligence.reconciliation_service` and is strictly
read-only — nothing here writes, creates, approves, or activates anything.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field


class ReconciliationRow(BaseModel):
    canonical_field: str = Field(description="Normalized canonical field name.")
    display_label: str = Field(description="Human-readable field label.")
    category: str = Field(
        description=(
            "Diligence grouping: baseline_physics, design_estimate, weather, "
            "legal_commercial, equipment, warranty_permit_insurance, or other."
        )
    )
    baseline_target: str = Field(
        description=(
            "Where the value lands on a baseline: header_column, points_monthly, "
            "points_annual, metadata, or none."
        )
    )
    status: str = Field(
        description=(
            "Per-field lifecycle, most-advanced stage wins. One of: missing, "
            "ai_extracted_only, accepted_document_value, candidate_only, "
            "accepted_not_promoted, active_fact, in_draft_baseline, "
            "in_active_baseline, superseded."
        )
    )
    status_label: Optional[str] = Field(
        None, description="Short human-readable label for ``status`` (UI display)."
    )
    status_explanation: Optional[str] = Field(
        None,
        description="One-sentence plain-language explanation of where this value sits "
        "in the audit chain.",
    )
    required_action: Optional[str] = Field(
        None,
        description="The single next step a reviewer should take to advance this value "
        "(e.g. accept in Due Diligence, promote to project assumptions). None when no "
        "action is needed.",
    )
    blocking_level: Optional[str] = Field(
        None,
        description=(
            "Single most-severe impact of this row's gaps, or None when nothing is "
            "blocked. One of: blocks_baseline, blocks_expected, blocks_reporting, "
            "lowers_confidence, informational."
        ),
    )
    missing_dependencies: list[str] = Field(
        default_factory=list,
        description="Ordered pipeline stages still pending to reach in_active_baseline "
        "(e.g. acceptance, promotion, baseline, baseline_activation).",
    )

    ai_extracted_value: Optional[Any] = Field(
        None, description="Raw AI-extracted value, before any human decision."
    )
    accepted_value: Optional[Any] = Field(
        None, description="Human accepted/overridden document value."
    )
    active_fact_value: Optional[Any] = Field(
        None, description="Current active/promoted project_fact value, if any."
    )
    draft_baseline_value: Optional[Any] = Field(
        None,
        description=(
            "Value on the relevant DRAFT baseline (weather-adjusted header for "
            "physics; design-estimate point for production); never recomputed."
        ),
    )
    active_baseline_value: Optional[Any] = Field(
        None, description="Value on the relevant ACTIVE baseline, if present."
    )
    legacy_value: Optional[Any] = Field(
        None,
        description=(
            "Legacy SiteAdditionalFieldList value (display/transition only; never "
            "used to build a V2 baseline)."
        ),
    )

    # Provenance
    fact_id: Optional[int] = Field(None, description="Source project_fact id.")
    project_fact_id: Optional[int] = Field(
        None, description="Project fact id (alias of fact_id, clearer name for the UI)."
    )
    source_file_id: Optional[int] = None
    source_document_type: Optional[str] = None
    source_run_id: Optional[int] = Field(None, description="AI parsing run id.")
    evidence_page: Optional[int] = None
    evidence_snippet: Optional[str] = None
    confidence: Optional[float] = Field(None, description="AI extraction confidence.")
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None

    # Navigation handles (read-only deep links the UI can resolve to existing routes).
    document_id: Optional[int] = Field(
        None, description="Owning Document id for the source value, if known."
    )
    document_version_id: Optional[int] = Field(
        None, description="Source File (document version) id, if known."
    )
    ai_run_id: Optional[int] = Field(
        None, description="AI parsing run id behind the value (alias of source_run_id)."
    )
    document_key_id: Optional[int] = Field(
        None, description="DocumentKey id the accepted value was recorded under, if any."
    )
    baseline_id: Optional[int] = Field(
        None, description="Baseline id this value currently lives on (active or draft)."
    )
    baseline_point_id: Optional[int] = Field(
        None, description="Design-estimate baseline point id, for points targets only."
    )
    aliases_matched: list[str] = Field(
        default_factory=list,
        description="Distinct document key/extraction names that resolved to this "
        "canonical field.",
    )

    # Supersession / review context
    supersedes_fact_id: Optional[int] = Field(
        None, description="Prior fact this active fact replaced (history pointer)."
    )
    candidate_count: int = Field(
        0, description="Number of candidate (unpromoted) facts for this field."
    )
    required_for_baseline: bool = Field(
        False, description="Absence blocks the weather-adjusted baseline."
    )

    warnings: list[str] = Field(
        default_factory=list,
        description=(
            "Any of: missing_required_for_baseline, fact_differs_from_legacy, "
            "draft_differs_from_active, active_baseline_outdated, "
            "design_points_missing, needs_review."
        ),
    )

    # --- Additive, read-only parse-state indicators (Phase 1) ---------------
    # These are purely informational signals derived from the source document
    # version's parse lifecycle. They NEVER feed status/blocking_level/
    # needs_review/missing_dependencies/baseline logic and are populated ONLY for
    # rows that already carry a source document version (document_version_id).
    # Each is None when there is no source file or the signal does not apply.
    source_document_uploaded_not_parsed: Optional[bool] = Field(
        None,
        description="Source document version exists but has never been parsed.",
    )
    parse_failed: Optional[bool] = Field(
        None,
        description="The most recent parse attempt on the source document version failed.",
    )
    parsed_no_usable_fields: Optional[bool] = Field(
        None,
        description="Source document version parsed but produced no reviewable fields.",
    )
    source_document_not_current_version: Optional[bool] = Field(
        None,
        description="The source document version is not marked as the current version.",
    )
    source_document_type_lacks_operational_schema: Optional[bool] = Field(
        None,
        description="The source document type's active schema is the generic contractual "
        "stub (no specialized/operational fields).",
    )


class SourceBasisDriftField(BaseModel):
    """One fact-backed baseline column whose value drifted from its recorded basis."""

    field: str = Field(
        description="Baseline column whose current value differs from its recorded basis."
    )
    basis_value: Optional[Any] = Field(
        default=None,
        description="Value recorded as the source basis when the active baseline was built.",
    )
    current_value: Optional[Any] = Field(
        default=None,
        description="Current active-fact value that positively differs from the recorded basis.",
    )
    current_fact_id: Optional[int] = Field(
        default=None, description="Active project_fact id supplying the current value."
    )


class SourceBasisDrift(BaseModel):
    """Read-only, value-based source-basis verdict for the ACTIVE baseline (Phase B4).

    ``state`` rolls up per-field comparisons with precedence
    ``basis_unknown > drifted > source_retired > up_to_date`` (informational
    ordering, not a blocker escalation). ``basis_unknown`` is neutral — it means
    the baseline carries no recorded fact lineage, NOT that the source changed.
    """

    state: str = Field(
        description="up_to_date | drifted | basis_unknown | source_retired."
    )
    baseline_id: Optional[int] = None
    basis_captured_at: Optional[datetime] = Field(
        default=None,
        description="Informational only (approved_at/active_from/created_at); never a drift trigger.",
    )
    unknown_basis: bool = Field(
        default=False,
        description="True when the baseline has no recorded fact lineage at all.",
    )
    drifted_fields: list[SourceBasisDriftField] = Field(default_factory=list)
    no_fact_lineage_fields: list[str] = Field(
        default_factory=list,
        description="Reviewer-supplied / no-live-counterpart fields; informational, never drift.",
    )
    note: str = Field(
        default="",
        description="Honest, human-readable summary of the baseline's source-basis state.",
    )


class ReconciliationReadiness(BaseModel):
    facts_to_draft_ready: bool = Field(
        description="Whether promoted facts + reviewer constants can form a draft."
    )
    missing_required_physics_fields: list[str] = Field(
        default_factory=list,
        description="Required physics fields with no source-backed value.",
    )
    facts_to_draft_warnings: list[str] = Field(default_factory=list)

    active_baseline_available: bool = Field(
        description="A weather-adjusted ACTIVE baseline exists."
    )
    active_baseline_id: Optional[int] = None
    active_baseline_created_at: Optional[datetime] = None

    design_estimate_baseline_id: Optional[int] = Field(
        None, description="The draft (preferred) or active design-estimate baseline."
    )
    design_estimate_baseline_status: Optional[str] = None
    design_points_ready: Optional[bool] = Field(
        None, description="None when no design-estimate baseline exists."
    )
    design_points_present_months: list[int] = Field(default_factory=list)
    design_points_missing: list[str] = Field(default_factory=list)
    design_points_parse_errors: list[str] = Field(default_factory=list)

    source_basis_drift: Optional[SourceBasisDrift] = Field(
        default=None,
        description=(
            "Read-only value-based source-basis verdict for the active baseline "
            "(Phase B4). Additive and nullable for back-compat."
        ),
    )


class TelemetryReality(BaseModel):
    """Telemetry-discovered deployed reality (headline summary).

    The detailed device-inventory reconciliation lives at its own read-only
    endpoint (``/api/telemetry/v2/sites/{id}/inventory-reconciliation``); this
    block carries the compact headline so the DD reconciliation view and the
    telemetry view can never disagree. The original ``available`` / ``note`` /
    ``last_reading_at`` fields are retained (additive change only); the new summary
    fields are all optional and default to ``None`` so any caller that cannot
    compute them stays honest.
    """

    available: bool = Field(
        False,
        description=(
            "True once telemetry is connected for the site (i.e. an inventory "
            "headline beyond 'telemetry not connected' is available)."
        ),
    )
    note: str = Field(
        "Telemetry-discovered device/capacity reconciliation is not implemented yet."
    )
    last_reading_at: Optional[datetime] = None

    # --- Additive inventory-reconciliation headline (all optional) ----------
    status: Optional[str] = Field(
        None, description="Inventory reconciliation headline (G1->G8 ladder value)."
    )
    status_label: Optional[str] = None
    status_explanation: Optional[str] = None
    has_blocking_mismatch: Optional[bool] = None
    weather_dependency_unsatisfied: Optional[bool] = None
    open_actionable_mismatch_count: Optional[int] = None
    informational_mismatch_count: Optional[int] = None


class SiteReconciliationResponse(BaseModel):
    site_id: int
    generated_at: datetime
    rows: list[ReconciliationRow]
    readiness: ReconciliationReadiness
    telemetry_reality: TelemetryReality
    help_targets: dict[str, str] = Field(
        default_factory=dict,
        description="Tooltip/help text keyed by concept for the UI (Path B hook).",
    )
    schema_expansion_recommended: bool = Field(
        False,
        description=(
            "True when fields exist that the single-value point/row shape cannot "
            "fully represent (GHI, P50/P90)."
        ),
    )
