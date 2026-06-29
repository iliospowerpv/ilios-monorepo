"""Native Workflow Engine HTTP surface.

Generic orchestration endpoints for guided wizards. Every write step goes through a
two-phase preview -> confirm -> execute: the engine dispatches to EXISTING domain endpoints
and never owns business truth. Structured engine errors (per-field validation, blast-radius
re-confirm) are rendered as JSONResponse so the FE receives them unflattened.
"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.schema.user import CurrentUserSchema
from app.schema.workflow import (
    AbandonResponse,
    ExecuteRequest,
    ExecuteResponse,
    PreviewResponse,
    SaveStepRequest,
    StartRunRequest,
    WorkflowListResponse,
    WorkflowRunDetailResponse,
    WorkflowStepStateSchema,
)
from app.services.workflows import engine
from app.services.workflows.engine import WorkflowEngineError

logger = logging.getLogger(__name__)
workflows_router = APIRouter()


@workflows_router.get("", response_model=WorkflowListResponse)
def list_workflows(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    """List the workflow definitions the current user is permitted to start."""
    return engine.list_workflow_definitions(db_session, current_user)


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
    db_session: Session = Depends(get_session),
):
    """Execute a confirmed write step via the EXISTING endpoint (idempotent, audited)."""
    try:
        return await engine.execute_step(db_session, current_user, run_id, step_id, payload)
    except WorkflowEngineError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.payload)


@workflows_router.post("/runs/{run_id}/abandon", response_model=AbandonResponse)
def abandon_run(
    run_id: int,
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    db_session: Session = Depends(get_session),
):
    """Abandon (cancel) an active run."""
    return engine.abandon_run(db_session, current_user, run_id)
