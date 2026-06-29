"""Generic Workflow Engine orchestration.

Two-phase commit for every write step (audit §7):

    PLAN     save inputs -> validate (client + server) -> build preview (NO write)
    CONFIRM  user reviews preview -> explicit Confirm (mints/returns a confirm token)
    EXECUTE  re-check permission + idempotency -> re-diff inputs (blast-radius re-confirm)
             -> call the EXISTING endpoint via the per-workflow executor -> audit -> record id

The engine never owns business truth: it stores wizard progress only and dispatches writes to
existing endpoints/services. Governed terminals have no executor and can never auto-execute.
"""
from __future__ import annotations

import hashlib
import json
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.crud.errors import UniqueConstraintViolationError
from app.crud.workflow import WorkflowRunCRUD, WorkflowStepStateCRUD
from app.helpers.permission_guards import require_module_permission_any_company
from app.helpers.workflow_audit import create_workflow_audit_log
from app.static.permissions import PermissionsModules
from app.models.workflow import (
    WorkflowRun,
    WorkflowRunStatus,
    WorkflowStepState,
    WorkflowStepStatus,
)
from app.schema.workflow import (
    AbandonResponse,
    ExecuteRequest,
    ExecuteResponse,
    PreviewItem,
    PreviewResponse,
    SaveStepRequest,
    StartRunRequest,
    WorkflowDefinitionSchema,
    WorkflowFieldOption,
    WorkflowFieldSchema,
    WorkflowListResponse,
    WorkflowRunDetailResponse,
    WorkflowRunSchema,
    WorkflowStepSchema,
    WorkflowStepStateSchema,
)
from app.services.workflows.definitions import (
    REGISTRY,
    STEP_EXECUTE,
    WorkflowDef,
    first_step_id,
    get_definition,
    get_payload_schema,
    get_step,
    get_step_input_schema,
    resolve_options,
)
from app.services.workflows.executors import get_executor


class WorkflowEngineError(Exception):
    """A structured engine error the router renders as a JSONResponse.

    Used for cases where the FE needs structured data (per-field validation errors, the
    blast-radius re-confirm signal) that the global ``http_exception_handler`` would flatten
    to a string.
    """

    def __init__(self, status_code: int, payload: dict):
        super().__init__(payload.get("message", "Workflow error"))
        self.status_code = status_code
        self.payload = payload


# --- Helpers --------------------------------------------------------------------------


def _user_id(current_user) -> int | None:
    return getattr(current_user, "id", None)


def _has_platform_bypass(current_user) -> bool:
    return bool(getattr(current_user, "has_platform_bypass", False))


# Permission tokens understood by the engine. Each is resolved fail-closed; an unrecognized
# token is always refused, so a mis-typed definition can never silently grant access.
PERMISSION_PLATFORM_ADMIN = "platform_admin"
# Company-scoped Asset Management edit. Deliberately COMPANY-scope only (no project/site
# grants): creating a site requires edit on the TARGET company, so a project-only grant must
# not let a user start the wizard or see companies. This is the COARSE gate; the existing
# site-create endpoint stays the authoritative per-company guard at execute time.
PERMISSION_ASSETS_CREATE_SITE = "assets_management:create_site"
_KNOWN_PERMISSIONS = {PERMISSION_PLATFORM_ADMIN, PERMISSION_ASSETS_CREATE_SITE}


def _has_company_scoped_edit(current_user, db_session: Session) -> bool:
    """True if the user has Asset Management 'edit' on at least one accessible COMPANY."""
    try:
        company_ids = current_user.get_limited_companies_ids() or []
    except Exception:
        company_ids = []
    if not company_ids:
        return False
    try:
        require_module_permission_any_company(
            user_id=_user_id(current_user),
            company_ids=company_ids,
            db_session=db_session,
            module_key=PermissionsModules.assets_management.value,
            action="edit",
        )
        return True
    except HTTPException:
        return False


def _check_permission(perm: str | None, current_user, db_session: Session) -> bool:
    """Soft, never-raising permission resolution. Unknown token -> False (fail-closed)."""
    if perm is None:
        return True
    if perm == PERMISSION_PLATFORM_ADMIN:
        return _has_platform_bypass(current_user)
    if perm == PERMISSION_ASSETS_CREATE_SITE:
        return _has_platform_bypass(current_user) or _has_company_scoped_edit(current_user, db_session)
    return False


def _can_start(wf: WorkflowDef, current_user, db_session: Session) -> bool:
    """Best-effort entry-permission check (never raises)."""
    return _check_permission(wf.entry_permission, current_user, db_session)


def _ensure_permission(perm: str | None, current_user, db_session: Session) -> None:
    """Authoritative, fail-closed permission check; unknown tokens are refused."""
    if perm is None:
        return
    if perm not in _KNOWN_PERMISSIONS:
        raise HTTPException(status_code=403, detail=f"Unknown permission requirement: {perm}")
    if not _check_permission(perm, current_user, db_session):
        raise HTTPException(status_code=403, detail="You don't have permission to perform this action.")


def _format_errors(exc: ValidationError) -> dict:
    out: dict = {}
    for err in exc.errors():
        loc = ".".join(str(p) for p in err.get("loc", ())) or "_"
        out[loc] = err.get("msg", "Invalid value")
    return out


def _stringify(value) -> str:
    if hasattr(value, "value"):  # enum
        return str(value.value)
    return str(value)


def _confirm_token(run_id: int, step_id: str, inputs: dict) -> str:
    canonical = json.dumps(inputs, sort_keys=True, default=str)
    return hashlib.sha256(f"{run_id}:{step_id}:{canonical}".encode()).hexdigest()


def _collect_inputs(wf: WorkflowDef, step_crud: WorkflowStepStateCRUD, run_id: int) -> dict:
    """Merge inputs from all COLLECT steps of the run, in definition order."""
    merged: dict = {}
    for step in wf.steps:
        if step.kind == STEP_EXECUTE:
            continue
        state = step_crud.get_run_step(run_id, step.id)
        if state and state.inputs:
            merged.update(state.inputs)
    return merged


def _build_summary(wf: WorkflowDef, data: dict) -> list[PreviewItem]:
    items: list[PreviewItem] = []
    for step in wf.steps:
        for fld in step.inputs:
            if fld.name in data:
                val = data[fld.name]
                items.append(
                    PreviewItem(label=fld.label, value=_stringify(val) if val is not None else None)
                )
    return items


def _summary_dict(wf: WorkflowDef, data: dict) -> dict:
    out: dict = {}
    for step in wf.steps:
        for fld in step.inputs:
            if fld.name in data and data[fld.name] is not None:
                out[fld.name] = _stringify(data[fld.name])
    return out


def _build_warnings(db_session: Session, workflow_id: str, data: dict) -> list[str]:
    """Read-only, best-effort warnings surfaced in the preview (no side effect)."""
    warnings: list[str] = []
    if workflow_id == "add_company":
        name = data.get("name")
        if name:
            try:
                from app.crud.company import CompanyCRUD

                if CompanyCRUD(db_session).get_by_name(name):
                    warnings.append(
                        f"A company named '{name}' already exists — creation will fail."
                    )
            except Exception:  # warnings must never break preview
                pass
    elif workflow_id == "add_site":
        # Sites have NO natural uniqueness, so this is an advisory (non-blocking) warning:
        # a same-name project already exists in the chosen company. Creation still proceeds.
        name = data.get("name")
        company_id = data.get("company_id")
        if name and company_id is not None:
            try:
                from app.models.site import Site

                exists = (
                    db_session.query(Site.id)
                    .filter(Site.name == name, Site.company_id == company_id)
                    .first()
                )
                if exists:
                    warnings.append(
                        f"A project named '{name}' already exists in this company."
                    )
            except Exception:  # warnings must never break preview
                pass
    return warnings


def serialize_definition(
    wf: WorkflowDef, can_start: bool, db_session: Session | None = None, current_user=None
) -> WorkflowDefinitionSchema:
    steps: list[WorkflowStepSchema] = []
    for step in wf.steps:
        fields: list[WorkflowFieldSchema] = []
        for fld in step.inputs:
            opts = resolve_options(fld.options_source, db_session, current_user)
            fields.append(
                WorkflowFieldSchema(
                    name=fld.name,
                    label=fld.label,
                    type=fld.type,
                    required=fld.required,
                    options=[WorkflowFieldOption(**o) for o in opts] if opts is not None else None,
                    placeholder=fld.placeholder,
                    help=fld.help,
                    max_length=fld.max_length,
                    pattern=fld.pattern,
                )
            )
        steps.append(
            WorkflowStepSchema(
                id=step.id,
                title=step.title,
                kind=step.kind,
                confirmation=step.confirmation,
                governed=step.governed,
                help=step.help,
                inputs=fields,
            )
        )
    return WorkflowDefinitionSchema(
        id=wf.id,
        version=wf.version,
        title=wf.title,
        description=wf.description,
        can_start=can_start,
        steps=steps,
    )


def _run_detail(
    wf: WorkflowDef, run: WorkflowRun, db_session: Session, current_user
) -> WorkflowRunDetailResponse:
    return WorkflowRunDetailResponse(
        run=WorkflowRunSchema.model_validate(run),
        definition=serialize_definition(
            wf, _can_start(wf, current_user, db_session), db_session, current_user
        ),
    )


def _get_run_owned(db_session: Session, current_user, run_id: int) -> WorkflowRun:
    run = WorkflowRunCRUD(db_session).get_for_user(run_id, _user_id(current_user))
    if run is None:
        raise HTTPException(status_code=404, detail="Workflow run not found.")
    return run


def _get_active_run(db_session: Session, current_user, run_id: int) -> WorkflowRun:
    run = _get_run_owned(db_session, current_user, run_id)
    if run.status != WorkflowRunStatus.active:
        raise HTTPException(status_code=409, detail="This workflow run is no longer active.")
    return run


def _definition_for_run(run: WorkflowRun) -> WorkflowDef:
    wf = get_definition(run.workflow_id)
    if wf is None:
        raise HTTPException(status_code=409, detail="This workflow definition is no longer available.")
    return wf


# --- Public engine operations ---------------------------------------------------------


def list_workflow_definitions(db_session: Session, current_user) -> WorkflowListResponse:
    items = [
        serialize_definition(wf, True, db_session, current_user)
        for wf in REGISTRY.values()
        if _can_start(wf, current_user, db_session)
    ]
    return WorkflowListResponse(items=items)


def start_run(
    db_session: Session, current_user, workflow_id: str, req: StartRunRequest
) -> WorkflowRunDetailResponse:
    wf = get_definition(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Unknown workflow.")
    _ensure_permission(wf.entry_permission, current_user, db_session)

    run = WorkflowRunCRUD(db_session).create_item(
        {
            "workflow_id": wf.id,
            "workflow_version": wf.version,
            "user_id": _user_id(current_user),
            "company_id": req.company_id,
            "site_id": req.site_id,
            "status": WorkflowRunStatus.active,
            "current_step": first_step_id(wf),
            "resume_token": uuid4().hex,
        }
    )
    create_workflow_audit_log(
        db_session,
        user_id=_user_id(current_user),
        action=f"workflow.{wf.id}.start",
        details={"run_id": run.id, "workflow_id": wf.id, "version": wf.version, "outcome": "started"},
        is_success=True,
    )
    return _run_detail(wf, run, db_session, current_user)


def get_run(db_session: Session, current_user, run_id: int) -> WorkflowRunDetailResponse:
    run = _get_run_owned(db_session, current_user, run_id)
    wf = _definition_for_run(run)
    return _run_detail(wf, run, db_session, current_user)


def save_step(
    db_session: Session, current_user, run_id: int, step_id: str, req: SaveStepRequest
) -> WorkflowStepStateSchema:
    run = _get_active_run(db_session, current_user, run_id)
    wf = _definition_for_run(run)
    step = get_step(wf, step_id)
    if step is None:
        raise HTTPException(status_code=404, detail="Unknown step.")

    validation_status = WorkflowStepStatus.pending
    validation_errors: dict | None = None
    schema = get_step_input_schema(run.workflow_id, step_id)
    if schema is not None:
        try:
            schema(**req.inputs)
            validation_status = WorkflowStepStatus.valid
        except ValidationError as exc:
            validation_status = WorkflowStepStatus.invalid
            validation_errors = _format_errors(exc)

    step_crud = WorkflowStepStateCRUD(db_session)
    state = step_crud.get_run_step(run_id, step_id)
    if state is not None:
        state.inputs = req.inputs
        state.validation_status = validation_status
        state.validation_errors = validation_errors
    else:
        state = WorkflowStepState(
            run_id=run_id,
            step_id=step_id,
            inputs=req.inputs,
            validation_status=validation_status,
            validation_errors=validation_errors,
        )
        db_session.add(state)
    run.current_step = step_id
    db_session.commit()
    db_session.refresh(state)
    return WorkflowStepStateSchema.model_validate(state)


def preview_step(
    db_session: Session, current_user, run_id: int, step_id: str
) -> PreviewResponse:
    run = _get_active_run(db_session, current_user, run_id)
    wf = _definition_for_run(run)
    step = get_step(wf, step_id)
    if step is None:
        raise HTTPException(status_code=404, detail="Unknown step.")
    if step.kind != STEP_EXECUTE:
        raise HTTPException(status_code=400, detail="This step has nothing to preview.")
    _ensure_permission(step.required_permission, current_user, db_session)

    step_crud = WorkflowStepStateCRUD(db_session)
    merged = _collect_inputs(wf, step_crud, run_id)

    payload_schema = get_payload_schema(run.workflow_id)
    if payload_schema is not None:
        try:
            data = payload_schema(**merged).model_dump(mode="json")
        except ValidationError as exc:
            raise WorkflowEngineError(
                422,
                {
                    "message": "Some required details are missing or invalid.",
                    "errors": _format_errors(exc),
                },
            )
    else:
        data = merged

    return PreviewResponse(
        step_id=step_id,
        confirmation=step.confirmation,
        summary=_build_summary(wf, data),
        warnings=_build_warnings(db_session, run.workflow_id, data),
        confirm_token=_confirm_token(run_id, step_id, merged),
    )


async def execute_step(
    db_session: Session, current_user, run_id: int, step_id: str, req: ExecuteRequest
) -> ExecuteResponse:
    run = _get_active_run(db_session, current_user, run_id)
    wf = _definition_for_run(run)
    step = get_step(wf, step_id)
    if step is None:
        raise HTTPException(status_code=404, detail="Unknown step.")
    if step.kind != STEP_EXECUTE:
        raise HTTPException(status_code=400, detail="This step cannot be executed.")

    audit_action = step.audit_action or f"workflow.{run.workflow_id}.{step_id}.execute"
    base_details = {"run_id": run_id, "step_id": step_id, "workflow_id": run.workflow_id}

    # Authoritative permission re-check (fail-closed); audit the refusal for security review.
    try:
        _ensure_permission(step.required_permission, current_user, db_session)
    except HTTPException:
        create_workflow_audit_log(
            db_session,
            user_id=_user_id(current_user),
            action=audit_action,
            details={**base_details, "outcome": "refused_permission"},
            is_success=False,
            governed=step.governed,
        )
        raise

    step_crud = WorkflowStepStateCRUD(db_session)

    # Idempotency: this step already executed -> return prior result (no double write).
    existing = step_crud.get_run_step(run_id, step_id)
    if existing is not None and existing.executed:
        return ExecuteResponse(
            step_id=step_id,
            executed=True,
            entity_type=existing.result_entity_type,
            entity_id=existing.result_entity_id,
            run_status=run.status,
            message="This step was already completed.",
        )
    # Idempotency: same key already used by a completed step -> return that result.
    if req.idempotency_key:
        prior = step_crud.get_by_idempotency_key(req.idempotency_key)
        if prior is not None and prior.executed:
            return ExecuteResponse(
                step_id=step_id,
                executed=True,
                entity_type=prior.result_entity_type,
                entity_id=prior.result_entity_id,
                run_status=run.status,
                message="This step was already completed.",
            )

    merged = _collect_inputs(wf, step_crud, run_id)

    # Blast-radius re-confirm: the confirm token must match the reviewed inputs.
    if req.confirm_token != _confirm_token(run_id, step_id, merged):
        raise WorkflowEngineError(
            409,
            {
                "code": "reconfirm_required",
                "message": "The details changed since you reviewed them. Please review and confirm again.",
            },
        )

    # Validate the payload against the EXISTING domain schema (fail-closed).
    payload_schema = get_payload_schema(run.workflow_id)
    if payload_schema is not None:
        try:
            exec_inputs = payload_schema(**merged).model_dump(mode="json")
        except ValidationError as exc:
            raise WorkflowEngineError(
                422,
                {
                    "message": "Some required details are missing or invalid.",
                    "errors": _format_errors(exc),
                },
            )
    else:
        exec_inputs = merged

    executor = get_executor(run.workflow_id)
    if executor is None:
        raise HTTPException(status_code=500, detail="This workflow has no executor configured.")

    # Dispatch to the EXISTING endpoint/service.
    try:
        entity_type, entity_id = await executor(db_session, current_user, exec_inputs)
    except UniqueConstraintViolationError:
        db_session.rollback()
        create_workflow_audit_log(
            db_session,
            user_id=_user_id(current_user),
            action=audit_action,
            details={**base_details, "outcome": "conflict_unique"},
            is_success=False,
            governed=step.governed,
        )
        raise WorkflowEngineError(
            409, {"code": "conflict", "message": "A company with these details already exists."}
        )
    except HTTPException as http_exc:
        db_session.rollback()
        # A 403 from the EXISTING endpoint is an authoritative per-entity permission refusal
        # (e.g. the coarse engine gate passed but the user lacks edit on the SELECTED company).
        # Record it distinctly for security traceability; re-raise unchanged.
        outcome = (
            "endpoint_refused_permission" if http_exc.status_code == 403 else "endpoint_error"
        )
        create_workflow_audit_log(
            db_session,
            user_id=_user_id(current_user),
            action=audit_action,
            details={**base_details, "outcome": outcome},
            is_success=False,
            governed=step.governed,
        )
        raise

    # Success audit links run/step -> produced entity for end-to-end traceability.
    audit_id = create_workflow_audit_log(
        db_session,
        user_id=_user_id(current_user),
        action=audit_action,
        details={
            **base_details,
            "entity_type": entity_type,
            "entity_id": entity_id,
            "summary": _summary_dict(wf, exec_inputs),
            "outcome": "executed",
        },
        is_success=True,
        governed=step.governed,
    )

    # Record execution result on the step state (re-fetch in case commit expired it).
    state = step_crud.get_run_step(run_id, step_id)
    if state is not None:
        state.executed = True
        state.idempotency_key = req.idempotency_key
        state.result_entity_type = entity_type
        state.result_entity_id = entity_id
        state.audit_log_id = audit_id
        state.validation_status = WorkflowStepStatus.valid
    else:
        state = WorkflowStepState(
            run_id=run_id,
            step_id=step_id,
            validation_status=WorkflowStepStatus.valid,
            executed=True,
            idempotency_key=req.idempotency_key,
            result_entity_type=entity_type,
            result_entity_id=entity_id,
            audit_log_id=audit_id,
        )
        db_session.add(state)

    run = step_crud.db_session.get(WorkflowRun, run_id)
    run.status = WorkflowRunStatus.completed
    run.current_step = step_id
    db_session.commit()

    return ExecuteResponse(
        step_id=step_id,
        executed=True,
        entity_type=entity_type,
        entity_id=entity_id,
        run_status=WorkflowRunStatus.completed,
        message=wf.success_message or "Created successfully.",
    )


def abandon_run(db_session: Session, current_user, run_id: int) -> AbandonResponse:
    run = _get_run_owned(db_session, current_user, run_id)
    if run.status in (WorkflowRunStatus.completed, WorkflowRunStatus.abandoned):
        return AbandonResponse(
            run_id=run.id, run_status=run.status, message="This run is already closed."
        )
    run.status = WorkflowRunStatus.abandoned
    db_session.commit()
    create_workflow_audit_log(
        db_session,
        user_id=_user_id(current_user),
        action=f"workflow.{run.workflow_id}.abandon",
        details={"run_id": run.id, "workflow_id": run.workflow_id, "outcome": "abandoned"},
        is_success=True,
    )
    return AbandonResponse(
        run_id=run.id, run_status=WorkflowRunStatus.abandoned, message="Workflow run abandoned."
    )
