"""DD V2 Phase 4 — read-only assumptions reconciliation endpoint.

Surfaces, for a single project/site, how source-backed diligence facts flow
through the audit chain (document -> AI value -> accepted/overridden ->
active project_fact -> draft baseline -> design-estimate points -> active
weather-adjusted baseline) alongside legacy SiteAdditionalFieldList values
(display-only) and a telemetry-reality placeholder.

The endpoint is strictly READ-ONLY: it never recomputes a baseline, never
creates/approves/activates anything, and never mutates facts or baselines.
"""
import logging
from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.authorization.project_access import get_authorized_site
from app.helpers.permission_guards import require_module_permission
from app.models.site import Site
from app.schema.reconciliation import SiteReconciliationResponse
from app.schema.user import CurrentUserSchema
from app.services.due_diligence.reconciliation_service import build_site_reconciliation
from app.static import HTTP_403_RESPONSE, HTTP_404_RESPONSE

logger = logging.getLogger(__name__)
reconciliation_router = APIRouter()


@reconciliation_router.get(
    "/reconciliation",
    response_model=SiteReconciliationResponse,
    responses={**HTTP_403_RESPONSE, **HTTP_404_RESPONSE},
    description=(
        "Read-only reconciliation of source-backed assumptions across the audit "
        "chain (facts -> draft/active baselines + design points), with legacy "
        "values for comparison only. Recomputes and mutates nothing."
    ),
)
async def get_site_reconciliation(
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    site: Site = Depends(get_authorized_site),
    db_session: Session = Depends(get_session),
) -> SiteReconciliationResponse:
    require_module_permission(
        user_id=current_user.id,
        company_id=site.company_id,
        project_id=site.id,
        db_session=db_session,
        module_key="Diligence",
        action="view",
    )
    return build_site_reconciliation(db_session, site)
