"""Per-workflow execute dispatchers.

Each executor is a THIN dispatcher: it validates the run's collected inputs against the
EXISTING domain schema and invokes the EXISTING endpoint/service that the manual UI uses
today, returning ``(entity_type, entity_id)``. Executors contain NO bespoke business logic
and create NO new operational-truth path. Governed terminals (fact promotion, baseline
approve/activate, device mapping, weather declaration) have NO executor here by design — the
engine may at most navigate the user to the existing manual UI.

Two registries exist:
  * EXECUTORS — JSON-only write steps. Signature ``(db_session, current_user, inputs, *,
    background_tasks=None)``. The trailing keyword is accepted uniformly so the engine can pass
    a real BackgroundTasks through; executors that don't need it simply ignore it.
  * FILE_EXECUTORS — write steps that also receive a real uploaded file (multipart). Signature
    ``(db_session, current_user, inputs, *, file, background_tasks)``. The file NEVER touches
    the run's JSONB inputs; it is streamed straight into the existing upload endpoint.
"""
from __future__ import annotations

from typing import Awaitable, Callable, Optional

from fastapi import UploadFile
from sqlalchemy.orm import Session


async def _execute_add_company(
    db_session: Session, current_user, inputs: dict, *, background_tasks=None
) -> tuple[str, int]:
    """Create a company by invoking the EXISTING company-create endpoint verbatim.

    Reuses the same permission guard, the same ``CompanyCRUD.create_item``, the same
    company-admin membership grant, and the same commit as the manual "Add Company" path — no
    duplicated or parallel mutation logic. Imported lazily to avoid any router import-order
    coupling.
    """
    from app.routers.assets_management.companies import create_company as create_company_endpoint
    from app.schema.company import CreateCompanySchema

    payload = CreateCompanySchema(**inputs)
    result = await create_company_endpoint(
        payload=payload, current_user=current_user, db_session=db_session
    )
    return ("company", result.id)


async def _execute_add_site(
    db_session: Session, current_user, inputs: dict, *, background_tasks=None
) -> tuple[str, int]:
    """Create a site/project by invoking the EXISTING site-create endpoint verbatim.

    Reuses the same company-scoped ``assets_management:edit`` guard, the same
    ``SiteCRUD.create_item`` + default section/board/document scaffolding, the same
    user-project membership grant, and the same commit as the manual "Add Project" path — no
    duplicated or parallel mutation logic. Imported lazily to avoid router import-order
    coupling. The endpoint returns a dict (``{"code", "message", "id"}``).
    """
    from app.routers.assets_management.sites import create as create_site_endpoint
    from app.schema.site import CreateSiteSchema

    payload = CreateSiteSchema(**inputs)
    result = await create_site_endpoint(
        site=payload, current_user=current_user, db_session=db_session
    )
    return ("site", result["id"])


async def _execute_invite_user(
    db_session: Session, current_user, inputs: dict, *, background_tasks=None
) -> tuple[str, int]:
    """Invite a user: create-or-reuse the account, then grant company membership.

    A SINGLE thin executor that reuses the EXISTING create-user endpoint (POST /users/) and the
    EXISTING add-company-member endpoint (POST /workspace/companies/{id}/members). Idempotent:
    an already-existing email is reused (not duplicated) and an already-present membership is a
    no-op, so re-running after a partial failure converges. The collected targets are mapped
    onto the existing ``CreateUserSchema`` + ``UserCompanyAccessCreate`` domain schemas, which
    perform the authoritative validation. Imported lazily to avoid router import-order coupling.

    The new user's ``role_id``/``parent_company_id`` are set to None/company_id respectively:
    the workflow grants COMPANY membership (the modern multi-company access model) rather than
    the legacy single-role-per-user fields, exactly as the manual invite + add-member path does.
    """
    from fastapi import HTTPException

    from app.crud.user import UserCRUD
    from app.crud.user_company_access import UserCompanyAccessCRUD
    from app.routers.users import create_user as create_user_endpoint
    from app.routers.workspace.workspace import add_company_member as add_company_member_endpoint
    from app.schema.user import CreateUserSchema
    from app.schema.user_company_access import CompanyRoleEnum, UserCompanyAccessCreate

    email = inputs["email"]
    company_id = int(inputs["company_id"])
    role = CompanyRoleEnum(inputs["role"]) if not isinstance(inputs["role"], CompanyRoleEnum) else inputs["role"]

    user_crud = UserCRUD(db_session)
    existing = user_crud.get_by_email(email)
    if existing is not None:
        user_id = existing.id
    else:
        user_payload = CreateUserSchema(
            email=email,
            first_name=inputs["first_name"],
            last_name=inputs["last_name"],
            phone=inputs["phone"],
            parent_company_id=company_id,
            role_id=None,
            sites_ids=[],
        )
        try:
            result = await create_user_endpoint(
                payload=user_payload, current_user=current_user, db_session=db_session
            )
        except HTTPException as exc:
            # Idempotency race: the email was created concurrently. Re-read instead of failing.
            if exc.status_code == 400:
                again = user_crud.get_by_email(email)
                if again is None:
                    raise
                result = {"id": again.id}
            else:
                raise
        user_id = result["id"] if isinstance(result, dict) else result.id

    access_crud = UserCompanyAccessCRUD(db_session)
    if access_crud.get_by_user_and_company(user_id, company_id) is None:
        membership_payload = UserCompanyAccessCreate(
            user_id=user_id, company_id=company_id, role=role
        )
        try:
            await add_company_member_endpoint(
                company_id=company_id,
                payload=membership_payload,
                current_user=current_user,
                db_session=db_session,
            )
        except HTTPException as exc:
            # "Already a member" is idempotent; any other error (e.g. 403) propagates.
            if exc.status_code != 400:
                raise

    return ("user", user_id)


async def _execute_parse_document(
    db_session: Session, current_user, inputs: dict, *, background_tasks=None
) -> tuple[str, int]:
    """Trigger in-app AI parsing on an uploaded file via the EXISTING parsing endpoint.

    The engine never performs AI work; this executor only resolves the authorized target file
    (project -> document -> file, reusing the SAME authorization dependencies the manual UI uses)
    and dispatches to ``trigger_file_parsing``. That endpoint schedules the parse via the passed
    BackgroundTasks and returns the new run id (HTTP 202 semantics). The honest result is the
    ``ai_parsing_run`` id the user can track in the Data Room — not a synthetic "done".
    """
    from fastapi import BackgroundTasks

    from app.helpers.authorization.project_access import (
        get_authorized_document,
        get_authorized_file,
        get_authorized_site,
    )
    from app.routers.due_diligence.files_parsing import trigger_file_parsing

    site_id = int(inputs["site_id"])
    document_id = int(inputs["document_id"])
    file_id = int(inputs["file_id"])

    site = get_authorized_site(site_id=site_id, current_user=current_user, db_session=db_session)
    document = get_authorized_document(
        document_id=document_id, site=site, current_user=current_user, db_session=db_session
    )
    target_file = get_authorized_file(
        file_id=file_id, document=document, current_user=current_user, db_session=db_session
    )

    if background_tasks is None:
        background_tasks = BackgroundTasks()
    result = await trigger_file_parsing(
        background_tasks=background_tasks,
        current_user=current_user,
        file=target_file,
        db_session=db_session,
    )
    run_id = result["run_id"] if isinstance(result, dict) else result.run_id
    return ("ai_parsing_run", run_id)


async def _execute_document_upload(
    db_session: Session, current_user, inputs: dict, *, file: UploadFile, background_tasks
) -> tuple[str, int]:
    """Upload a file into a project's data room via the EXISTING upload endpoint verbatim.

    The JSON targets (site_id/document_id) come from the collected inputs; the file bytes arrive
    as a real multipart UploadFile (never persisted in JSONB). Resolves the authorized document
    using the SAME authorization dependency the manual UI uses, then calls ``upload_file`` — the
    same versioning, storage, and ChatBot-sync background task. Returns the new file's id.
    """
    from app.helpers.authorization.project_access import (
        get_authorized_document,
        get_authorized_site,
    )
    from app.routers.due_diligence.files import upload_file as upload_file_endpoint

    site_id = int(inputs["site_id"])
    document_id = int(inputs["document_id"])

    site = get_authorized_site(site_id=site_id, current_user=current_user, db_session=db_session)
    document = get_authorized_document(
        document_id=document_id, site=site, current_user=current_user, db_session=db_session
    )
    result = await upload_file_endpoint(
        site_id=site_id,
        document_id=document_id,
        file=file,
        current_user=current_user,
        background_tasks=background_tasks,
        document=document,
        db_session=db_session,
    )
    new_id = result.get("id") if isinstance(result, dict) else getattr(result, "id", None)
    return ("file", new_id)


# workflow_id -> executor. Only JSON-only write workflows appear here.
EXECUTORS: dict[str, Callable[..., Awaitable[tuple[str, int]]]] = {
    "add_company": _execute_add_company,
    "add_site": _execute_add_site,
    "invite_user": _execute_invite_user,
    "parse_document": _execute_parse_document,
}

# workflow_id -> file executor. Only multipart write workflows (those whose execute step sets
# multipart_file_field) appear here; these receive the real UploadFile in addition to inputs.
FILE_EXECUTORS: dict[str, Callable[..., Awaitable[tuple[str, int]]]] = {
    "document_upload": _execute_document_upload,
}


def get_executor(workflow_id: str) -> Optional[Callable[..., Awaitable[tuple[str, int]]]]:
    return EXECUTORS.get(workflow_id)


def get_file_executor(workflow_id: str) -> Optional[Callable[..., Awaitable[tuple[str, int]]]]:
    return FILE_EXECUTORS.get(workflow_id)
