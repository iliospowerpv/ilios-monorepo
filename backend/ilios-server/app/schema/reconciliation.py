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
            "Per-field lifecycle (first match wins): missing, candidate_only, "
            "active_fact, in_draft_baseline, in_active_baseline."
        )
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
    source_file_id: Optional[int] = None
    source_document_type: Optional[str] = None
    source_run_id: Optional[int] = Field(None, description="AI parsing run id.")
    evidence_page: Optional[int] = None
    evidence_snippet: Optional[str] = None
    confidence: Optional[float] = Field(None, description="AI extraction confidence.")
    effective_from: Optional[datetime] = None
    effective_to: Optional[datetime] = None

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


class TelemetryReality(BaseModel):
    """Placeholder for telemetry-discovered deployed reality.

    Device-level reconciliation is intentionally out of scope for this sprint;
    this block reserves the shape without making any false claims.
    """

    available: bool = Field(False, description="Always False this sprint.")
    note: str = Field(
        "Telemetry-discovered device/capacity reconciliation is not implemented yet."
    )
    last_reading_at: Optional[datetime] = None


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
