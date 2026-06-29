"""Shared, READ-ONLY helpers for the Phase 3 guided-onboarding aggregation services.

Everything here is read-only and authz-scoped. Candidate sites are resolved against the
caller's VISIBLE site set (the same entity access the underlying read endpoints enforce via
``get_authorized_site``), capped, and optionally narrowed to one site/company. Per-section
module checks (e.g. Diligence ``view``) mirror the exact guards on the wrapped endpoints so
the rollups can never disclose more than the caller could read directly. No writes, no commits.
"""
from __future__ import annotations

from typing import Optional

from sqlalchemy.orm import Session

from app.models.site import Site
from app.services.workflows.definitions import _user_accessible_site_ids

# Hard cap so a portfolio-wide rollup can never fan out unbounded.
MAX_SITES = 100
DEFAULT_SITES = 25


def resolve_candidate_sites(
    db_session: Session,
    current_user,
    *,
    site_id: Optional[int] = None,
    company_id: Optional[int] = None,
    limit: int = DEFAULT_SITES,
) -> list[Site]:
    """Authorized, non-archived sites for the caller, capped at ``limit`` (<= MAX_SITES).

    Scoped to the caller's visible set (None == platform-bypass == all). An explicit
    ``site_id``/``company_id`` is INTERSECTED with that visibility, so passing an id the caller
    cannot see yields an empty result (fail-closed) rather than a disclosure. Visibility is the
    same entity access ``get_authorized_site`` resolves for these read endpoints, so we avoid an
    N+1 re-authorization while staying exactly as tight as the underlying endpoints.
    """
    cap = max(1, min(int(limit or DEFAULT_SITES), MAX_SITES))
    visible = _user_accessible_site_ids(current_user)  # None == bypass (all)

    query = db_session.query(Site).filter(Site.is_archived.is_(False))
    if visible is not None:
        if not visible:
            return []
        query = query.filter(Site.id.in_(list(visible)))
    if site_id is not None:
        query = query.filter(Site.id == site_id)
    elif company_id is not None:
        query = query.filter(Site.company_id == company_id)
    return query.order_by(Site.name).limit(cap).all()


def can_view_diligence(db_session: Session, current_user, site: Site) -> bool:
    """Whether the caller has Diligence ``view`` on ``site`` (fail-closed).

    Mirrors the reconciliation endpoint's guard so the readiness/progress rollups never surface
    Diligence-derived verdicts to a caller who could not open the reconciliation view directly.
    """
    if getattr(current_user, "has_platform_bypass", False):
        return True
    company_id = getattr(site, "company_id", None)
    user_id = getattr(current_user, "id", None)
    if company_id is None or user_id is None:
        return False
    from app.helpers.permission_guards import require_module_permission
    from app.static.permissions import PermissionsModules

    try:
        require_module_permission(
            user_id=user_id,
            company_id=company_id,
            db_session=db_session,
            module_key=PermissionsModules.diligence.value,
            action="view",
            project_id=site.id,
        )
        return True
    except Exception:
        return False


def scope_label(site_id: Optional[int], company_id: Optional[int]) -> str:
    if site_id is not None:
        return "site"
    if company_id is not None:
        return "company"
    return "me"
