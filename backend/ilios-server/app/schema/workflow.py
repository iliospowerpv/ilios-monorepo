"""Workflow Engine API schemas.

These describe ONLY run/step orchestration and the serialized (read-only) workflow
definition the FE Wizard shell consumes. No business-truth payload schema lives here — write
steps validate against, and dispatch to, the EXISTING domain schemas/endpoints.
"""
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


class WorkflowDefinitionSchema(BaseModel):
    id: str
    version: str
    title: str
    description: str
    can_start: bool
    steps: list[WorkflowStepSchema]


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
    step_states: list[WorkflowStepStateSchema] = Field(default_factory=list)


class WorkflowRunDetailResponse(BaseModel):
    run: WorkflowRunSchema
    definition: WorkflowDefinitionSchema


# --- Requests ------------------------------------------------------------------------


class StartRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company_id: Optional[int] = None
    site_id: Optional[int] = None


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
