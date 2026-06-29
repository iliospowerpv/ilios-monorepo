"""Per-workflow execute dispatchers.

Each executor is a THIN dispatcher: it validates the run's collected inputs against the
EXISTING domain schema and invokes the EXISTING endpoint/service that the manual UI uses
today, returning ``(entity_type, entity_id)``. Executors contain NO bespoke business logic
and create NO new operational-truth path. Governed terminals (fact promotion, baseline
approve/activate, device mapping, weather declaration) have NO executor here by design — the
engine may at most navigate the user to the existing manual UI.
"""
from __future__ import annotations

from typing import Awaitable, Callable, Optional

from sqlalchemy.orm import Session


async def _execute_add_company(db_session: Session, current_user, inputs: dict) -> tuple[str, int]:
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


async def _execute_add_site(db_session: Session, current_user, inputs: dict) -> tuple[str, int]:
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


# workflow_id -> executor. Only workflows that have a write (execute) step appear here.
EXECUTORS: dict[str, Callable[[Session, object, dict], Awaitable[tuple[str, int]]]] = {
    "add_company": _execute_add_company,
    "add_site": _execute_add_site,
}


def get_executor(
    workflow_id: str,
) -> Optional[Callable[[Session, object, dict], Awaitable[tuple[str, int]]]]:
    return EXECUTORS.get(workflow_id)
