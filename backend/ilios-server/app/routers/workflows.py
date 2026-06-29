"""Native Workflow Engine HTTP surface.

Generic orchestration endpoints for guided wizards. Every write step goes through a
two-phase preview -> confirm -> execute: the engine dispatches to EXISTING domain endpoints
and never owns business truth. Structured engine errors (per-field validation, blast-radius
re-confirm) are rendered as JSONResponse so the FE receives them unflattened.
"""
import logging
from typing import Annotated, Optional

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    File,
    Form,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.models.workflow import WorkflowRunStatus
from app.schema.user import CurrentUserSchema
from app.schema.workflow import (
    AbandonResponse,
    ExecuteRequest,
    ExecuteResponse,
    OnboardingProgressResponse,
    OrchestrationContextResponse,
    PreviewResponse,
    ReadinessSummaryResponse,
    RecommendationsResponse,
    SaveStepRequest,
    SequenceListResponse,
    StartRunRequest,
    WorkflowListResponse,
    WorkflowMetricsResponse,
    WorkflowRunDetailResponse,
    WorkflowRunListResponse,
    WorkflowStepStateSchema,
)
from app.services.workflows import engine
from app.services.workflows.engine import WorkflowEngineError
from app.services.workflows.onboarding_progress_service import (
    build_onboarding_progress,
)
from app.services.workflows.orchestration_context_service import (
    build_orchestration_context,
)
from app.services.workflows.readiness_summary_service import build_readiness_summary
from app.services.workflows.recommendations_service import build_recommendations

logger = logging.getLogger(__name__)
workflows_router = APIRouter()


@workflows_router.get("", response_model=WorkflowListResponse)
def list_workflows(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    """List the workflow definitions the current user is permitted to start."""
    return engine.list_workflow_definitions(db_session, current_user)


@workflows_router.get("/runs", response_model=WorkflowRunListResponse)
def list_runs(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
    status_filter: Annotated[Optional[list[str]], Query(alias="status")] = None,
    workflow_id: Annotated[Optional[str], Query()] = None,
    sequence_id: Annotated[Optional[str], Query()] = None,
    limit: Annotated[int, Query(ge=1, le=200)] = 100,
):
    """List the CURRENT user's runs (owner-scoped) for the Workflow Dashboard.

    Registered BEFORE ``/runs/{run_id}`` so the literal ``/runs`` path is never captured as a
    run id. ``status`` may be repeated (e.g. ``?status=active&status=completed``); unknown
    values are ignored. Always scoped to the caller — one user can never list another's runs.
    """
    statuses: Optional[list[WorkflowRunStatus]] = None
    if status_filter:
        parsed: list[WorkflowRunStatus] = []
        for raw in status_filter:
            try:
                parsed.append(WorkflowRunStatus(raw))
            except ValueError:
                continue
        statuses = parsed or None
    return engine.list_user_runs(
        db_session,
        current_user,
        statuses=statuses,
        workflow_id=workflow_id,
        sequence_id=sequence_id,
        limit=limit,
    )


@workflows_router.get("/sequences", response_model=SequenceListResponse)
def list_sequences(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    """List declarative orchestrator sequences (with per-step start permission for the user)."""
    return engine.list_sequences(db_session, current_user)


# --- Phase 3: guided onboarding (READ-ONLY aggregation) ------------------------------
#
# These GETs are pure, owner/permission-scoped read aggregations that CALL existing domain
# services and read their verdicts verbatim. They perform NO writes, emit NO audit events
# (no state change), and never start/advance a workflow. Each is registered ahead of the
# dynamic ``/{workflow_id}/...`` paths so their literal prefixes are never captured as ids.


@workflows_router.get(
    "/onboarding/progress", response_model=OnboardingProgressResponse
)
def onboarding_progress(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
    company_id: Annotated[Optional[int], Query()] = None,
    site_id: Annotated[Optional[int], Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
):
    """Per-project onboarding stage checklist, derived only from existing service verdicts.

    Scoped to the caller's visible sites (optionally narrowed to one ``site_id``/``company_id``)
    and capped at ``limit``. A stage the caller lacks the module to evaluate is reported as
    ``available=false`` and excluded from the completion ratio — never silently counted as done.
    """
    return build_onboarding_progress(
        db_session, current_user, site_id=site_id, company_id=company_id, limit=limit
    )


@workflows_router.get(
    "/onboarding/readiness", response_model=ReadinessSummaryResponse
)
def onboarding_readiness(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
    company_id: Annotated[Optional[int], Query()] = None,
    site_id: Annotated[Optional[int], Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
):
    """Per-project readiness summary consolidating telemetry health, reconciliation, device
    eligibility and expected-baseline existence. Each dimension degrades independently
    (``available=false`` with a reason) so a denied/failing section never fails the summary."""
    return build_readiness_summary(
        db_session, current_user, site_id=site_id, company_id=company_id, limit=limit
    )


@workflows_router.get("/recommendations", response_model=RecommendationsResponse)
def workflow_recommendations(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
    limit: Annotated[int, Query(ge=1, le=10)] = 10,
):
    """Deterministic, READ-ONLY next-action hints (which existing workflow/sequence to run next).

    Each item is a link/suggestion only — nothing is auto-started, and governed actions
    (fact promotion, baseline activation, device mapping, weather declaration) are never
    recommended as automatable. Scoped to workflows the caller is permitted to start."""
    return build_recommendations(db_session, current_user, limit=limit)


@workflows_router.get(
    "/orchestration/context", response_model=OrchestrationContextResponse
)
def orchestration_context(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
):
    """Versioned, READ-ONLY envelope bundling every authorized onboarding signal for a future
    AI advisor to reason over WITHOUT being able to act. ``mode="read_only_advice"`` and the
    ``prohibited_actions`` list are explicit non-execution markers: this endpoint starts
    nothing, writes nothing, and grants nothing."""
    return build_orchestration_context(db_session, current_user, limit=limit)


@workflows_router.post(
    "/{workflow_id}/runs",
    response_model=WorkflowRunDetailResponse,
    status_code=status.HTTP_201_CREATED,
)
def start_run(
    workflow_id: str,
    payload: StartRunRequest,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    """Start a new run of a workflow (entry-permission enforced, fail-closed)."""
    return engine.start_run(db_session, current_user, workflow_id, payload)


@workflows_router.get("/runs/{run_id}", response_model=WorkflowRunDetailResponse)
def get_run(
    run_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    """Fetch a run (owner-scoped) with its definition for save/resume/review."""
    return engine.get_run(db_session, current_user, run_id)


@workflows_router.patch(
    "/runs/{run_id}/steps/{step_id}", response_model=WorkflowStepStateSchema
)
def save_step(
    run_id: int,
    step_id: str,
    payload: SaveStepRequest,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    """Persist a step's collected inputs and server-validate them (no side effect)."""
    return engine.save_step(db_session, current_user, run_id, step_id, payload)


@workflows_router.post(
    "/runs/{run_id}/steps/{step_id}/preview", response_model=PreviewResponse
)
def preview_step(
    run_id: int,
    step_id: str,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    """Build a read-only preview + confirm token for a write step (no mutation)."""
    try:
        return engine.preview_step(db_session, current_user, run_id, step_id)
    except WorkflowEngineError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.payload)


@workflows_router.post(
    "/runs/{run_id}/steps/{step_id}/execute", response_model=ExecuteResponse
)
async def execute_step(
    run_id: int,
    step_id: str,
    payload: ExecuteRequest,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    background_tasks: BackgroundTasks,
    db_session: Session = Depends(get_session),
):
    """Execute a confirmed write step via the EXISTING endpoint (idempotent, audited).

    ``background_tasks`` is the real FastAPI instance so executors that schedule async
    follow-ups (e.g. ChatBot sync after add_site) behave exactly as the manual UI does.
    """
    try:
        return await engine.execute_step(
            db_session,
            current_user,
            run_id,
            step_id,
            payload,
            background_tasks=background_tasks,
        )
    except WorkflowEngineError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.payload)


@workflows_router.post(
    "/runs/{run_id}/steps/{step_id}/execute-file", response_model=ExecuteResponse
)
async def execute_file_step(
    run_id: int,
    step_id: str,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    background_tasks: BackgroundTasks,
    confirm_token: Annotated[str, Form()],
    file: Annotated[UploadFile, File()],
    idempotency_key: Annotated[Optional[str], Form()] = None,
    db_session: Session = Depends(get_session),
):
    """Execute a confirmed multipart (file-upload) write step via the EXISTING upload endpoint.

    Mirrors ``execute_step`` but accepts the file part for steps declaring
    ``multipart_file_field``. The confirm token + optional idempotency key arrive as form fields
    (not JSON) since the body is multipart; the engine reconstructs an ``ExecuteRequest`` and runs
    the identical perm/idempotency/reconfirm/audit pipeline before handing the file to the
    existing upload service. Bytes are NEVER persisted in run state.
    """
    payload = ExecuteRequest(confirm_token=confirm_token, idempotency_key=idempotency_key)
    try:
        return await engine.execute_file_step(
            db_session,
            current_user,
            run_id,
            step_id,
            payload,
            file,
            background_tasks=background_tasks,
        )
    except WorkflowEngineError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.payload)


@workflows_router.get("/metrics", response_model=WorkflowMetricsResponse)
def get_metrics(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
    scope: Annotated[str, Query()] = "me",
):
    """Read-only workflow completion metrics. ``scope=me`` (default) is owner-scoped; ``scope=all``
    requires platform-bypass (else 403). Pure aggregation over ``workflow_runs`` — no mutation."""
    return engine.compute_metrics(db_session, current_user, scope=scope)


@workflows_router.post("/runs/{run_id}/abandon", response_model=AbandonResponse)
def abandon_run(
    run_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    """Abandon (cancel) an active run."""
    return engine.abandon_run(db_session, current_user, run_id)
