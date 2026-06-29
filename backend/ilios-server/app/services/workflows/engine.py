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
import statistics
from uuid import uuid4

from fastapi import HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.crud.errors import UniqueConstraintViolationError
from app.crud.workflow import WorkflowRunCRUD, WorkflowStepStateCRUD
from app.helpers.permission_guards import (
    require_module_permission_any_company,
    require_module_permission_any_context,
)
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
    SequenceListResponse,
    SequencePrefillSchema,
    SequenceSchema,
    SequenceStepSchema,
    StartRunRequest,
    WorkflowDefinitionSchema,
    WorkflowFieldOption,
    WorkflowFieldSchema,
    WorkflowListResponse,
    WorkflowMetricsItemSchema,
    WorkflowMetricsResponse,
    WorkflowPrerequisiteSchema,
    WorkflowRunDetailResponse,
    WorkflowRunListResponse,
    WorkflowRunSchema,
    WorkflowRunSummarySchema,
    WorkflowStepSchema,
    WorkflowStepStateSchema,
)
from app.services.workflows.definitions import (
    REGISTRY,
    SEQUENCES,
    STEP_EXECUTE,
    WorkflowDef,
    WorkflowDefinitionError,
    first_step_id,
    get_definition,
    get_payload_schema,
    get_sequence,
    get_step,
    get_step_input_schema,
    resolve_options,
)
from app.services.workflows.executors import get_executor, get_file_executor


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
# Diligence (Data Room) edit. This is the COARSE gate for the document-upload / parse
# workflows; unlike create-site it accepts EITHER a company-level OR a project-level grant
# (a project-only user may legitimately manage a single project's data room). The existing
# upload/parse endpoints stay the authoritative per-document guard at execute time.
PERMISSION_DILIGENCE_EDIT = "diligence:edit"
_KNOWN_PERMISSIONS = {
    PERMISSION_PLATFORM_ADMIN,
    PERMISSION_ASSETS_CREATE_SITE,
    PERMISSION_DILIGENCE_EDIT,
}


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


def _has_diligence_edit_any(current_user, db_session: Session) -> bool:
    """True if the user has Diligence 'edit' via ANY company-level OR project-level grant.

    Uses the any-context guard so a project-only user (no company grant) can still start the
    data-room workflows for a project they can edit. Read-only and never-raising.
    """
    try:
        company_ids = current_user.get_limited_companies_ids() or []
    except Exception:
        company_ids = []
    try:
        site_ids = current_user.get_limited_sites_ids() or []
    except Exception:
        site_ids = []
    if not company_ids and not site_ids:
        return False
    try:
        require_module_permission_any_context(
            user_id=_user_id(current_user),
            company_ids=company_ids,
            site_ids=site_ids,
            db_session=db_session,
            module_key=PermissionsModules.diligence.value,
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
    if perm == PERMISSION_DILIGENCE_EDIT:
        return _has_platform_bypass(current_user) or _has_diligence_edit_any(current_user, db_session)
    return False


# --- Prerequisite evaluators (read-only, user-scoped, NOT authorization) --------------
#
# A prerequisite is advisory guidance, NOT a gate: it tells the user what to do first. Each
# evaluator is a pure read scoped to the CURRENT user's accessible entities. Unknown keys and
# any error fail closed (treated as unmet) — never raising and never granting access.


def _eval_has_accessible_project(current_user, db_session: Session) -> bool:
    """True if the user has Diligence ``edit`` on at least one non-archived project (site).

    Scoped to the Diligence-edit set (NOT mere site visibility) so the "blocked" affordance is
    honest: a user who can merely see a project but cannot manage its Data Room must NOT be told
    they have an accessible project for an upload/parse workflow. Mirrors the option resolvers.
    """
    from app.models.site import Site
    from app.services.workflows.definitions import _diligence_editable_site_ids

    editable = _diligence_editable_site_ids(db_session, current_user)
    if editable is None:  # platform-bypass = all
        return db_session.query(Site.id).filter(Site.is_archived.is_(False)).first() is not None
    return len(editable) > 0


def _eval_has_uploaded_file(current_user, db_session: Session) -> bool:
    """True if at least one non-deleted file exists in a project the user has Diligence ``edit`` on.

    Same Diligence-edit scoping as the project evaluator — a file in a merely-visible project the
    user cannot manage must not satisfy the prerequisite.
    """
    from app.models.document import Document
    from app.models.file import File
    from app.models.site import Site
    from app.services.workflows.definitions import _diligence_editable_site_ids

    query = (
        db_session.query(File.id)
        .join(Document, File.document_id == Document.id)
        .join(Site, Document.site_id == Site.id)
        .filter(File.deleted.is_(False), Site.is_archived.is_(False))
    )
    editable = _diligence_editable_site_ids(db_session, current_user)
    if editable is not None:  # non-bypass: restrict to Diligence-editable sites
        if not editable:
            return False
        query = query.filter(Site.id.in_(list(editable)))
    return query.first() is not None


# evaluator_key -> pure-read evaluator. Keys are validated against every WorkflowDef's
# prerequisites at import time (below) so a typo'd key fails loudly at startup.
PREREQUISITE_EVALUATORS = {
    "has_accessible_project": _eval_has_accessible_project,
    "has_uploaded_file": _eval_has_uploaded_file,
}


def _evaluate_prerequisite(pr, current_user, db_session: Session | None) -> bool:
    """Resolve a single prerequisite to met/unmet, fail-closed (unmet) on any problem."""
    if db_session is None or current_user is None:
        return False
    evaluator = PREREQUISITE_EVALUATORS.get(pr.evaluator_key)
    if evaluator is None:
        return False
    try:
        return bool(evaluator(current_user, db_session))
    except Exception:
        return False


# Fail loudly at import if any definition references an unknown evaluator_key — a typo must be a
# startup error, not a silently-always-unmet prerequisite.
for _wf in REGISTRY.values():
    for _pr in _wf.prerequisites:
        if _pr.evaluator_key not in PREREQUISITE_EVALUATORS:
            raise WorkflowDefinitionError(
                f"workflow '{_wf.id}' prerequisite '{_pr.key}' references unknown "
                f"evaluator_key '{_pr.evaluator_key}'"
            )


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
    wf: WorkflowDef,
    can_start: bool,
    db_session: Session | None = None,
    current_user=None,
    context: dict | None = None,
) -> WorkflowDefinitionSchema:
    """Serialize a definition for the FE.

    ``context`` is the run's already-collected inputs; it lets cascading select fields
    (``project_documents`` -> needs ``site_id``, ``document_files`` -> needs ``document_id``)
    resolve their options against the user's earlier choices. It is None for the catalog/start
    listing (no run yet), where cascading sources correctly resolve to empty until a parent is
    chosen. Prerequisites are evaluated read-only here and surfaced as ``blocked_reason`` (the
    first unmet message) without affecting ``can_start`` (authorization stays separate).
    """
    steps: list[WorkflowStepSchema] = []
    for step in wf.steps:
        fields: list[WorkflowFieldSchema] = []
        for fld in step.inputs:
            opts = resolve_options(fld.options_source, db_session, current_user, context)
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
                multipart_file_field=step.multipart_file_field,
            )
        )

    prerequisites: list[WorkflowPrerequisiteSchema] = []
    blocked_reason: str | None = None
    for pr in wf.prerequisites:
        met = _evaluate_prerequisite(pr, current_user, db_session)
        prerequisites.append(
            WorkflowPrerequisiteSchema(
                key=pr.key, label=pr.label, met=met, unmet_message=pr.unmet_message
            )
        )
        if not met and blocked_reason is None:
            blocked_reason = pr.unmet_message

    return WorkflowDefinitionSchema(
        id=wf.id,
        version=wf.version,
        title=wf.title,
        description=wf.description,
        can_start=can_start,
        category=wf.category,
        icon=wf.icon,
        suggested_next=list(wf.suggested_next),
        landing_route_template=wf.landing_route_template,
        sequence_eligible=wf.sequence_eligible,
        steps=steps,
        prerequisites=prerequisites,
        blocked_reason=blocked_reason,
    )


def _run_detail(
    wf: WorkflowDef, run: WorkflowRun, db_session: Session, current_user
) -> WorkflowRunDetailResponse:
    # Thread the run's already-collected inputs so cascading option sources resolve correctly.
    step_crud = WorkflowStepStateCRUD(db_session)
    context = _collect_inputs(wf, step_crud, run.id)
    return WorkflowRunDetailResponse(
        run=WorkflowRunSchema.model_validate(run),
        definition=serialize_definition(
            wf, _can_start(wf, current_user, db_session), db_session, current_user, context
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


# Hard ceiling on a dashboard run listing so the response is always bounded.
_MAX_RUN_LIST_LIMIT = 200


def _run_summary(run: WorkflowRun) -> WorkflowRunSummarySchema:
    """Build a compact dashboard row, enriching with registry title/landing + result entity.

    The result entity (id/type) is read from the run's executed step state — the run row
    itself never stores business truth.
    """
    wf = get_definition(run.workflow_id)
    executed = next((s for s in run.step_states if s.executed), None)
    return WorkflowRunSummarySchema(
        id=run.id,
        workflow_id=run.workflow_id,
        workflow_version=run.workflow_version,
        workflow_title=wf.title if wf is not None else None,
        status=run.status,
        current_step=run.current_step,
        company_id=run.company_id,
        site_id=run.site_id,
        parent_run_id=run.parent_run_id,
        sequence_id=run.sequence_id,
        sequence_step_index=run.sequence_step_index,
        result_entity_type=executed.result_entity_type if executed else None,
        result_entity_id=executed.result_entity_id if executed else None,
        landing_route_template=wf.landing_route_template if wf is not None else None,
        created_at=run.created_at,
        updated_at=run.updated_at,
    )


def list_user_runs(
    db_session: Session,
    current_user,
    *,
    statuses: list[WorkflowRunStatus] | None = None,
    workflow_id: str | None = None,
    sequence_id: str | None = None,
    limit: int = 100,
) -> WorkflowRunListResponse:
    """Owner-scoped list of the CURRENT user's runs (never another user's) for the dashboard."""
    capped = max(1, min(limit, _MAX_RUN_LIST_LIMIT))
    runs = WorkflowRunCRUD(db_session).list_for_user(
        _user_id(current_user),
        statuses=statuses,
        workflow_id=workflow_id,
        sequence_id=sequence_id,
        limit=capped,
    )
    return WorkflowRunListResponse(items=[_run_summary(r) for r in runs])


def list_sequences(db_session: Session, current_user) -> SequenceListResponse:
    """List declarative orchestrator sequences with per-step start permission for this user.

    Read-only: a sequence is purely a chaining hint. ``can_start`` (overall) reflects whether
    the user may start the FIRST step; per-step ``can_start`` reflects each underlying
    workflow's own entry permission (resolved fail-closed, never raising).
    """
    items: list[SequenceSchema] = []
    for seq in SEQUENCES.values():
        steps: list[SequenceStepSchema] = []
        first_can_start = False
        for idx, step in enumerate(seq.steps):
            wf = get_definition(step.workflow_id)
            can_start = bool(wf is not None and _can_start(wf, current_user, db_session))
            if idx == 0:
                first_can_start = can_start
            steps.append(
                SequenceStepSchema(
                    workflow_id=step.workflow_id,
                    title=step.title,
                    description=step.description,
                    can_start=can_start,
                    prefill=[
                        SequencePrefillSchema(
                            target_field=h.target_field,
                            from_step_index=h.from_step_index,
                        )
                        for h in step.prefill
                    ],
                )
            )
        items.append(
            SequenceSchema(
                id=seq.id,
                title=seq.title,
                description=seq.description,
                category=seq.category,
                icon=seq.icon,
                can_start=first_can_start,
                steps=steps,
            )
        )
    return SequenceListResponse(items=items)


def start_run(
    db_session: Session, current_user, workflow_id: str, req: StartRunRequest
) -> WorkflowRunDetailResponse:
    wf = get_definition(workflow_id)
    if wf is None:
        raise HTTPException(status_code=404, detail="Unknown workflow.")
    _ensure_permission(wf.entry_permission, current_user, db_session)

    # --- Orchestration lineage (optional, fail-closed validation) ---------------------
    # Lineage NEVER changes how this run executes — it only records the chain so the
    # orchestrator/dashboard can resume and audit. All three fields are validated before
    # they are persisted so a malformed/forged chain can't be stored.
    parent_run_id = req.parent_run_id
    sequence_id = req.sequence_id
    sequence_step_index = req.sequence_step_index

    if parent_run_id is not None:
        # The parent MUST be a run owned by THIS user — no cross-user chaining.
        parent = WorkflowRunCRUD(db_session).get_for_user(
            parent_run_id, _user_id(current_user)
        )
        if parent is None:
            raise HTTPException(status_code=404, detail="Parent workflow run not found.")

    if sequence_id is not None:
        seq = get_sequence(sequence_id)
        if seq is None:
            raise HTTPException(status_code=400, detail="Unknown workflow sequence.")
        if sequence_step_index is not None:
            if not (0 <= sequence_step_index < len(seq.steps)):
                raise HTTPException(status_code=400, detail="Invalid sequence step index.")
            if seq.steps[sequence_step_index].workflow_id != wf.id:
                raise HTTPException(
                    status_code=400,
                    detail="This workflow does not match that step of the sequence.",
                )
    elif sequence_step_index is not None:
        # A step index without a sequence is meaningless — refuse rather than store junk.
        raise HTTPException(
            status_code=400, detail="sequence_step_index requires sequence_id."
        )

    run = WorkflowRunCRUD(db_session).create_item(
        {
            "workflow_id": wf.id,
            "workflow_version": wf.version,
            "user_id": _user_id(current_user),
            "company_id": req.company_id,
            "site_id": req.site_id,
            "parent_run_id": parent_run_id,
            "sequence_id": sequence_id,
            "sequence_step_index": sequence_step_index,
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
    # Orchestration-level audit (additive, best-effort): distinguish STARTING a sequence
    # from ADVANCING within it. The per-workflow audit above stays authoritative.
    if sequence_id is not None:
        is_first = parent_run_id is None and (sequence_step_index in (None, 0))
        create_workflow_audit_log(
            db_session,
            user_id=_user_id(current_user),
            action=f"workflow.sequence.{sequence_id}.{'started' if is_first else 'advanced'}",
            details={
                "run_id": run.id,
                "sequence_id": sequence_id,
                "sequence_step_index": sequence_step_index,
                "parent_run_id": parent_run_id,
                "workflow_id": wf.id,
                "outcome": "started" if is_first else "advanced",
            },
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


async def _execute_core(
    db_session: Session,
    current_user,
    run_id: int,
    step_id: str,
    req: ExecuteRequest,
    *,
    file=None,
    background_tasks=None,
) -> ExecuteResponse:
    """Shared two-phase EXECUTE used by both the JSON and multipart routes.

    The ONLY difference between the two entry points is how the executor is dispatched: a step
    declaring ``multipart_file_field`` runs via a FILE_EXECUTOR (receiving the real UploadFile)
    and must be reached through the multipart route; every other write step runs via the JSON
    EXECUTOR. Permission re-check, idempotency, blast-radius re-confirm, payload validation,
    audit, step-state recording, and sequence accounting are identical for both.
    """
    run = _get_active_run(db_session, current_user, run_id)
    wf = _definition_for_run(run)
    step = get_step(wf, step_id)
    if step is None:
        raise HTTPException(status_code=404, detail="Unknown step.")
    if step.kind != STEP_EXECUTE:
        raise HTTPException(status_code=400, detail="This step cannot be executed.")

    # File-part contract: a multipart step requires a file and must use the file route; a
    # non-multipart step never accepts one. Enforced up front so the two routes can't be misused.
    needs_file = step.multipart_file_field is not None
    if needs_file and file is None:
        raise HTTPException(
            status_code=400,
            detail="This step requires a file upload; use the file-upload route.",
        )
    if not needs_file and file is not None:
        raise HTTPException(
            status_code=400, detail="This step does not accept a file upload."
        )

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

    # Resolve the right executor for the step kind. A multipart step uses a FILE_EXECUTOR
    # (handed the real UploadFile); every other write step uses the JSON EXECUTOR. Both receive
    # background_tasks so endpoints that schedule async follow-ups (parsing, ChatBot sync) work
    # exactly as in the manual UI; when absent (e.g. unit tests) a throwaway one is created.
    from fastapi import BackgroundTasks

    bg = background_tasks if background_tasks is not None else BackgroundTasks()

    # Dispatch to the EXISTING endpoint/service.
    try:
        if needs_file:
            file_executor = get_file_executor(run.workflow_id)
            if file_executor is None:
                raise HTTPException(
                    status_code=500, detail="This workflow has no file executor configured."
                )
            entity_type, entity_id = await file_executor(
                db_session, current_user, exec_inputs, file=file, background_tasks=bg
            )
        else:
            executor = get_executor(run.workflow_id)
            if executor is None:
                raise HTTPException(
                    status_code=500, detail="This workflow has no executor configured."
                )
            entity_type, entity_id = await executor(
                db_session, current_user, exec_inputs, background_tasks=bg
            )
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
            409, {"code": "conflict", "message": "A record with these details already exists."}
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

    # Orchestration-level audit (additive, best-effort): if this run belongs to a sequence,
    # record whether it completed the WHOLE sequence (last step) or just this step. The
    # per-workflow execute audit above remains the authoritative success record.
    if run.sequence_id:
        seq = get_sequence(run.sequence_id)
        is_last = (
            seq is not None
            and run.sequence_step_index is not None
            and run.sequence_step_index >= len(seq.steps) - 1
        )
        create_workflow_audit_log(
            db_session,
            user_id=_user_id(current_user),
            action=f"workflow.sequence.{run.sequence_id}.{'completed' if is_last else 'step_completed'}",
            details={
                "run_id": run_id,
                "sequence_id": run.sequence_id,
                "sequence_step_index": run.sequence_step_index,
                "entity_type": entity_type,
                "entity_id": entity_id,
                "outcome": "completed" if is_last else "step_completed",
            },
            is_success=True,
        )

    return ExecuteResponse(
        step_id=step_id,
        executed=True,
        entity_type=entity_type,
        entity_id=entity_id,
        run_status=WorkflowRunStatus.completed,
        message=wf.success_message or "Created successfully.",
    )


async def execute_step(
    db_session: Session,
    current_user,
    run_id: int,
    step_id: str,
    req: ExecuteRequest,
    *,
    background_tasks=None,
) -> ExecuteResponse:
    """JSON execute entry point (unchanged signature). Rejects steps that require a file."""
    return await _execute_core(
        db_session,
        current_user,
        run_id,
        step_id,
        req,
        file=None,
        background_tasks=background_tasks,
    )


async def execute_file_step(
    db_session: Session,
    current_user,
    run_id: int,
    step_id: str,
    req: ExecuteRequest,
    file,
    *,
    background_tasks=None,
) -> ExecuteResponse:
    """Multipart execute entry point for steps declaring ``multipart_file_field``.

    Shares the entire perm/idempotency/reconfirm/audit pipeline with ``execute_step``; the file is
    passed straight to the FILE_EXECUTOR which hands it to the existing upload endpoint/service.
    """
    return await _execute_core(
        db_session,
        current_user,
        run_id,
        step_id,
        req,
        file=file,
        background_tasks=background_tasks,
    )


def _has_metrics_all_access(current_user, db_session: Session) -> bool:
    """Platform-bypass (super admin) may view org-wide metrics; everyone else is scope=me only."""
    try:
        return bool(_has_platform_bypass(current_user))
    except Exception:
        return False


def compute_metrics(
    db_session: Session, current_user, *, scope: str = "me"
) -> WorkflowMetricsResponse:
    """Read-only completion metrics aggregated from ``workflow_runs``.

    ``scope="me"`` covers only the caller's own runs; ``scope="all"`` (platform-bypass only,
    else 403) covers every run. Pure read: no writes, no run mutation. Durations are computed
    for completed runs as ``updated_at - created_at`` (seconds); rates are fractions in [0, 1].
    """
    if scope not in ("me", "all"):
        raise HTTPException(status_code=400, detail="Unknown metrics scope.")
    if scope == "all" and not _has_metrics_all_access(current_user, db_session):
        raise HTTPException(
            status_code=403, detail="You do not have access to organization-wide metrics."
        )

    query = db_session.query(WorkflowRun)
    if scope == "me":
        query = query.filter(WorkflowRun.user_id == _user_id(current_user))
    runs = query.all()

    by_workflow: dict[str, dict] = {}

    def _bucket(workflow_id: str) -> dict:
        b = by_workflow.get(workflow_id)
        if b is None:
            b = {
                "total": 0,
                "completed": 0,
                "abandoned": 0,
                "in_progress": 0,
                "durations": [],
            }
            by_workflow[workflow_id] = b
        return b

    total = completed = abandoned = in_progress = 0
    all_durations: list[float] = []

    for run in runs:
        b = _bucket(run.workflow_id)
        b["total"] += 1
        total += 1
        if run.status == WorkflowRunStatus.completed:
            b["completed"] += 1
            completed += 1
            try:
                if run.created_at is not None and run.updated_at is not None:
                    secs = (run.updated_at - run.created_at).total_seconds()
                    if secs >= 0:
                        b["durations"].append(secs)
                        all_durations.append(secs)
            except Exception:
                pass
        elif run.status == WorkflowRunStatus.abandoned:
            b["abandoned"] += 1
            abandoned += 1
        else:
            b["in_progress"] += 1
            in_progress += 1

    def _rate(numer: int, denom: int) -> float:
        return round(numer / denom, 4) if denom else 0.0

    def _avg(values: list[float]) -> float | None:
        return round(statistics.fmean(values), 2) if values else None

    def _median(values: list[float]) -> float | None:
        return round(statistics.median(values), 2) if values else None

    def _item(workflow_id: str, b: dict) -> WorkflowMetricsItemSchema:
        wf = REGISTRY.get(workflow_id)
        closed = b["completed"] + b["abandoned"]
        return WorkflowMetricsItemSchema(
            workflow_id=workflow_id,
            title=wf.title if wf is not None else workflow_id,
            total=b["total"],
            completed=b["completed"],
            abandoned=b["abandoned"],
            in_progress=b["in_progress"],
            completion_rate=_rate(b["completed"], closed),
            abandonment_rate=_rate(b["abandoned"], closed),
            avg_duration_seconds=_avg(b["durations"]),
            median_duration_seconds=_median(b["durations"]),
        )

    closed_total = completed + abandoned
    items = [_item(wid, b) for wid, b in sorted(by_workflow.items())]

    return WorkflowMetricsResponse(
        scope=scope,
        total_runs=total,
        completed_runs=completed,
        abandoned_runs=abandoned,
        in_progress_runs=in_progress,
        completion_rate=_rate(completed, closed_total),
        abandonment_rate=_rate(abandoned, closed_total),
        avg_duration_seconds=_avg(all_durations),
        median_duration_seconds=_median(all_durations),
        by_workflow=items,
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
