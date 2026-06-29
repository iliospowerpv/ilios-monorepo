"""Workflow Engine API schemas.

These describe ONLY run/step orchestration and the serialized (read-only) workflow
definition the FE Wizard shell consumes. No business-truth payload schema lives here — write
steps validate against, and dispatch to, the EXISTING domain schemas/endpoints.
"""
from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from app.models.workflow import WorkflowRunStatus, WorkflowStepStatus


# --- Serialized definition (FE Wizard shell consumes this) ---------------------------


class WorkflowFieldOption(BaseModel):
    label: str
    value: str


class WorkflowFieldSchema(BaseModel):
    name: str
    label: str
    type: str
    required: bool
    options: Optional[list[WorkflowFieldOption]] = None
    placeholder: Optional[str] = None
    help: Optional[str] = None
    max_length: Optional[int] = None
    pattern: Optional[str] = None


class WorkflowStepSchema(BaseModel):
    id: str
    title: str
    kind: str
    confirmation: str
    governed: bool
    help: Optional[str] = None
    inputs: list[WorkflowFieldSchema] = Field(default_factory=list)
    # When set, this EXECUTE step expects a file part under this field name and must be run via
    # the multipart execute-file route (the FE renders a file input for it). None = JSON step.
    multipart_file_field: Optional[str] = None


class WorkflowPrerequisiteSchema(BaseModel):
    """A declarative, read-only dependency advertised by a workflow.

    ``met`` is evaluated per-caller (user-scoped, fail-closed). It is purely informational —
    it powers the dashboard's "blocked" affordance and does NOT replace authorization
    (``can_start``), which stays a separate permission decision.
    """

    key: str
    label: str
    met: bool
    unmet_message: str


class WorkflowDefinitionSchema(BaseModel):
    id: str
    version: str
    title: str
    description: str
    can_start: bool
    # Additive discovery metadata (powers the dashboard + orchestrator). Presentational only.
    category: str = "General"
    icon: Optional[str] = None
    suggested_next: list[str] = Field(default_factory=list)
    landing_route_template: Optional[str] = None
    sequence_eligible: bool = True
    steps: list[WorkflowStepSchema]
    # Declarative prerequisites + the first unmet message (None when all met / none declared).
    prerequisites: list[WorkflowPrerequisiteSchema] = Field(default_factory=list)
    blocked_reason: Optional[str] = None


class WorkflowListResponse(BaseModel):
    items: list[WorkflowDefinitionSchema]


# --- Runs / step states --------------------------------------------------------------


class WorkflowStepStateSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    step_id: str
    inputs: Optional[dict] = None
    validation_status: WorkflowStepStatus
    validation_errors: Optional[dict] = None
    executed: bool
    result_entity_type: Optional[str] = None
    result_entity_id: Optional[int] = None


class WorkflowRunSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    workflow_id: str
    workflow_version: str
    status: WorkflowRunStatus
    current_step: Optional[str] = None
    company_id: Optional[int] = None
    site_id: Optional[int] = None
    parent_run_id: Optional[int] = None
    sequence_id: Optional[str] = None
    sequence_step_index: Optional[int] = None
    step_states: list[WorkflowStepStateSchema] = Field(default_factory=list)


class WorkflowRunDetailResponse(BaseModel):
    run: WorkflowRunSchema
    definition: WorkflowDefinitionSchema


# --- Requests ------------------------------------------------------------------------


class StartRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: Optional[int] = None
    site_id: Optional[int] = None
    # Orchestration lineage (optional). Set by the onboarding orchestrator to chain this run
    # to the prior one; the engine validates parent ownership + sequence/step integrity.
    parent_run_id: Optional[int] = None
    sequence_id: Optional[str] = None
    sequence_step_index: Optional[int] = None


class SaveStepRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    inputs: dict = Field(default_factory=dict)


class ExecuteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Token minted by the preview step over the exact inputs reviewed. Execute recomputes it
    # from the current inputs; a mismatch forces a blast-radius re-confirm. A client (incl.
    # the AI) cannot execute without first calling preview to obtain this token.
    confirm_token: str
    idempotency_key: Optional[str] = None


# --- Responses -----------------------------------------------------------------------


class PreviewItem(BaseModel):
    label: str
    value: Optional[str] = None


class PreviewResponse(BaseModel):
    step_id: str
    confirmation: str
    summary: list[PreviewItem]
    warnings: list[str] = Field(default_factory=list)
    confirm_token: str


class ExecuteResponse(BaseModel):
    step_id: str
    executed: bool
    entity_type: Optional[str] = None
    entity_id: Optional[int] = None
    run_status: WorkflowRunStatus
    message: str


class AbandonResponse(BaseModel):
    run_id: int
    run_status: WorkflowRunStatus
    message: str


# --- Run summaries (Workflow Dashboard list) -----------------------------------------


class WorkflowRunSummarySchema(BaseModel):
    """Compact, owner-scoped run row for the dashboard. Never carries another user's inputs."""

    id: int
    workflow_id: str
    workflow_version: str
    workflow_title: Optional[str] = None
    status: WorkflowRunStatus
    current_step: Optional[str] = None
    company_id: Optional[int] = None
    site_id: Optional[int] = None
    parent_run_id: Optional[int] = None
    sequence_id: Optional[str] = None
    sequence_step_index: Optional[int] = None
    result_entity_type: Optional[str] = None
    result_entity_id: Optional[int] = None
    landing_route_template: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class WorkflowRunListResponse(BaseModel):
    items: list[WorkflowRunSummarySchema] = Field(default_factory=list)


# --- Sequences (orchestrator catalog) ------------------------------------------------


class SequencePrefillSchema(BaseModel):
    """Declarative, best-effort cross-step prefill hint for the FE sequence runner.

    Copies the entity id created by an earlier sequence step (``from_step_index`` ->
    its ``result_entity_id``) into this step's collect field ``target_field``. Carries NO
    executable logic and grants NO access — the runner applies it best-effort and the
    underlying workflow still validates + authorizes its own inputs at execute time.
    """

    target_field: str
    from_step_index: int


class SequenceStepSchema(BaseModel):
    workflow_id: str
    title: str
    description: str
    can_start: bool
    prefill: list[SequencePrefillSchema] = Field(default_factory=list)


class SequenceSchema(BaseModel):
    id: str
    title: str
    description: str
    category: str
    icon: Optional[str] = None
    can_start: bool
    steps: list[SequenceStepSchema] = Field(default_factory=list)


class SequenceListResponse(BaseModel):
    items: list[SequenceSchema] = Field(default_factory=list)


# --- Completion metrics (read-only aggregation) --------------------------------------


class WorkflowMetricsItemSchema(BaseModel):
    """Per-workflow rollup. Rates are fractions in [0, 1] over CLOSED runs (completed+abandoned)."""

    workflow_id: str
    title: str
    total: int
    completed: int
    abandoned: int
    in_progress: int
    completion_rate: float
    abandonment_rate: float
    avg_duration_seconds: Optional[float] = None
    median_duration_seconds: Optional[float] = None


class WorkflowMetricsResponse(BaseModel):
    """Read-only completion metrics. ``scope`` is 'me' (own runs) or 'all' (platform-bypass)."""

    scope: str
    total_runs: int
    completed_runs: int
    abandoned_runs: int
    in_progress_runs: int
    completion_rate: float
    abandonment_rate: float
    avg_duration_seconds: Optional[float] = None
    median_duration_seconds: Optional[float] = None
    by_workflow: list[WorkflowMetricsItemSchema] = Field(default_factory=list)


# --- Phase 3: Guided onboarding (READ-ONLY aggregation) ------------------------------
#
# Everything below is a READ-ONLY rollup assembled by CALLING existing domain services and
# reading their verdicts verbatim — it computes no operational truth of its own, performs no
# writes, and the underlying endpoints remain the authoritative guards. The shapes are small,
# stable booleans/statuses suitable both for the dashboard and for a future read-only AI advisor.


class OnboardingStageSchema(BaseModel):
    """One stage of a project's onboarding checklist. ``done`` is derived by reading an existing
    service's verdict; ``available`` is False when the caller lacks the module to evaluate it."""

    key: str
    label: str
    done: bool
    available: bool = True
    detail: Optional[str] = None


class SiteOnboardingProgressSchema(BaseModel):
    site_id: int
    site_name: Optional[str] = None
    company_id: Optional[int] = None
    completed_stages: int
    total_stages: int
    completion_rate: float  # fraction in [0, 1] over EVALUABLE stages
    stages: list[OnboardingStageSchema] = Field(default_factory=list)


class OnboardingProgressResponse(BaseModel):
    generated_at: datetime
    scope: str  # "site" | "company" | "me"
    total_sites: int
    items: list[SiteOnboardingProgressSchema] = Field(default_factory=list)


class ReadinessSectionSchema(BaseModel):
    """One readiness dimension for a site, wrapping an existing service. ``available`` is False
    (with ``reason="permission_denied"``/``"unavailable"``) when the caller may not see it or the
    underlying service could not be read — the section degrades, the summary never errors."""

    available: bool
    reason: Optional[str] = None
    status: Optional[str] = None
    summary: Optional[str] = None
    data: Optional[dict] = None


class SiteReadinessSchema(BaseModel):
    site_id: int
    site_name: Optional[str] = None
    company_id: Optional[int] = None
    telemetry_health: ReadinessSectionSchema
    reconciliation: ReadinessSectionSchema
    device_eligibility: ReadinessSectionSchema
    expected_baseline: ReadinessSectionSchema


class ReadinessSummaryResponse(BaseModel):
    generated_at: datetime
    scope: str  # "site" | "company" | "me"
    total_sites: int
    items: list[SiteReadinessSchema] = Field(default_factory=list)


class RecommendationSchema(BaseModel):
    """A single deterministic, READ-ONLY next-action hint. It is a link/suggestion only — never
    auto-started, and it never promotes, approves, maps devices, or declares semantics."""

    kind: str  # "workflow" | "sequence"
    workflow_id: Optional[str] = None
    sequence_id: Optional[str] = None
    title: str
    reason: str
    priority: int  # lower = more important
    target_site_id: Optional[int] = None
    target_company_id: Optional[int] = None
    blocked: bool = False
    blocked_reason: Optional[str] = None
    route: Optional[str] = None


class RecommendationsResponse(BaseModel):
    generated_at: datetime
    scope: str
    items: list[RecommendationSchema] = Field(default_factory=list)


class OrchestrationContextResponse(BaseModel):
    """A versioned, READ-ONLY envelope bundling every authorized onboarding signal in one place
    so a FUTURE AI advisor can reason over it WITHOUT being able to act. ``mode`` and
    ``prohibited_actions`` are explicit, machine-readable non-execution markers; this endpoint
    starts nothing, writes nothing, and grants nothing."""

    schema_version: str
    mode: str  # always "read_only_advice"
    generated_at: datetime
    actor_scope: str
    available_workflows: list[WorkflowDefinitionSchema] = Field(default_factory=list)
    sequences: list[SequenceSchema] = Field(default_factory=list)
    runs_summary: list[WorkflowRunSummarySchema] = Field(default_factory=list)
    metrics: WorkflowMetricsResponse
    progress: OnboardingProgressResponse
    readiness: ReadinessSummaryResponse
    recommendations: list[RecommendationSchema] = Field(default_factory=list)
    prohibited_actions: list[str] = Field(default_factory=list)
