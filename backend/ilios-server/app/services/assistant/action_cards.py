"""Propose-only action-card builder for the AI Assistant.

An "action card" is a VALIDATED DEEP LINK, never an execution. Given a workflow/sequence/run, this
module performs a READ-ONLY permission check (the same ``_can_start`` / owner-scoped run lookup the
dashboard uses) and, if the user is allowed, returns a card describing the route the USER can click
to open the relevant wizard/run in the existing workflow UI. It NEVER starts, advances, previews,
executes, or mutates anything — clicking the card later runs the normal, human-authorized engine
handshake. If the user is not permitted, NO card is produced (the assistant must say so honestly).

This is why the tool that calls it (``propose_action_card``) is legitimately read-only and passes
the guardrail name-screen: producing an inert link is not a governed action.
"""
from __future__ import annotations

import logging
from typing import Optional

from sqlalchemy.orm import Session

from app.models.workflow import WorkflowRunStatus

logger = logging.getLogger(__name__)

VALID_KINDS = ("workflow", "sequence", "resume", "open", "explain")

# ENUM of the EXISTING native read views an ``open`` card may deep-link to. The route is derived
# server-side from this enum + the (authorized) scope — a card NEVER carries a free-form/raw route,
# so the assistant (or a client) can never point a card at an arbitrary or fabricated destination.
OPEN_TARGET_VIEWS = (
    "project_overview",
    "data_room",
    "reconciliation",
    "site_finance",
    "company_finance",
)

_DEFAULT_REASON = {
    "workflow": "Open this guided workflow to do it yourself — the assistant can't run it for you.",
    "sequence": "Open this guided sequence to walk through the steps yourself.",
    "resume": "Pick up this in-progress run where you left off.",
    "open": "Jump straight to this view.",
    "explain": "Get a plain-language explanation of this page.",
}

_OPEN_VIEW_REASON = {
    "project_overview": "Open the project overview to see its key details and status.",
    "data_room": "Open the data room to review this project's documents.",
    "reconciliation": "Open the diligence reconciliation ladder for this project.",
    "site_finance": "Open this project's finance summary.",
    "company_finance": "Open the company's portfolio finance summary.",
}

_OPEN_VIEW_TITLE = {
    "project_overview": "Open project overview",
    "data_room": "Open data room",
    "reconciliation": "Open reconciliation",
    "site_finance": "Open project finance",
    "company_finance": "Open company finance",
}


def _deny(reason: str) -> dict:
    return {"permitted": False, "reason": reason, "action_card": None}


def _resolve_visible_site(db_session: Session, current_user, site_id: Optional[int]):
    """Return the caller-visible ``Site`` for ``site_id`` or ``None`` (fail-closed).

    Reuses the SAME visibility intersection (``resolve_candidate_sites``) the onboarding rollups and
    per-site assistant tools use, so an id the caller cannot see resolves to ``None`` — never a
    disclosure. Read-only.
    """
    if site_id is None:
        return None
    from app.services.workflows.onboarding_common import resolve_candidate_sites

    sites = resolve_candidate_sites(db_session, current_user, site_id=site_id, limit=1)
    return sites[0] if sites else None


def _can_view_finance(current_user) -> bool:
    """Whether the caller has Finance ``view`` (fail-closed).

    Mirrors the role-permission guard the Finance endpoints enforce
    (``AuthorizedUser([FinancePermissions(view)])``) so a finance ``open`` card is never offered to a
    caller who could not open the finance view directly. Read-only.
    """
    if getattr(current_user, "has_platform_bypass", False):
        return True
    role = getattr(current_user, "role", None)
    if not role:
        return False
    from app.static.permissions import PermissionsActions, PermissionsModules

    perms = getattr(role, "permissions", None) or {}
    module = perms.get(PermissionsModules.finance.value) or {}
    return bool(module.get(PermissionsActions.view.value))


def _authorize_company(db_session: Session, current_user, company_id: int) -> bool:
    """Whether the caller is authorized for ``company_id`` (fail-closed).

    The finance routes enforce Finance ``view`` AND ``get_authorized_company(company_id)``, so a
    finance ``open`` card must mirror BOTH or it would offer a company the caller cannot actually
    open. ``get_authorized_company`` raises on denial; we translate that into a boolean here (no
    disclosure). Read-only — it only resolves effective access.
    """
    from fastapi import HTTPException

    from app.helpers.authorization.project_access import get_authorized_company

    try:
        return get_authorized_company(company_id, current_user, db_session) is not None
    except HTTPException:
        return False
    except Exception:  # noqa: BLE001 - any authorization error fails closed
        logger.exception("action card company authorization failed for company %r", company_id)
        return False


def _open_route(target_view: str, site_id: Optional[int], company_id: Optional[int]) -> str:
    """Derive the EXISTING FE route for an ``open`` target_view + authorized scope. Never free-form."""
    if target_view == "project_overview":
        return f"/project-hub/projects/{site_id}"
    if target_view == "data_room":
        return f"/project-hub/{site_id}/data-room"
    if target_view == "reconciliation":
        return f"/reconciliation?site_id={site_id}"
    if target_view == "site_finance":
        qs = f"?company_id={company_id}" if company_id is not None else ""
        return f"/finance/sites/{site_id}/summary{qs}"
    # company_finance
    return f"/finance/summary?company_id={company_id}"


def _open_card_dict(target_view: str, reason: str, route: str, site_id, company_id) -> dict:
    return {
        "permitted": True,
        "reason": None,
        "action_card": {
            "kind": "open",
            "title": _OPEN_VIEW_TITLE[target_view],
            "reason": reason,
            "route": route,
            "workflow_id": None,
            "sequence_id": None,
            "run_id": None,
            "target_site_id": site_id,
            "target_company_id": company_id,
            "target_view": target_view,
            "prompt": None,
            "requires_user_action": True,
        },
    }


def _build_open_card(
    db_session: Session,
    current_user,
    *,
    target_view: str,
    site_id: Optional[int],
    company_id: Optional[int],
    reason: str,
) -> dict:
    """Validate (read-only) an ``open`` card against the destination's OWN read permission.

    Fail-closed: an unknown target_view, a missing required scope, an unauthorized site, or a missing
    module read permission all yield ``_deny`` (no card). The route is derived server-side from the
    enum + authorized scope, never from caller-supplied text. Zero writes/commits/executions.
    """
    if target_view not in OPEN_TARGET_VIEWS:
        return _deny(f"Unknown open target_view {target_view!r}.")
    card_reason = (reason or "").strip() or _OPEN_VIEW_REASON[target_view]

    if target_view == "company_finance":
        if company_id is None:
            return _deny("company_id is required to open company finance.")
        # Company finance enforces Finance view AND get_authorized_company — mirror BOTH.
        if not _can_view_finance(current_user):
            return _deny("You don't have permission to view finance.")
        if not _authorize_company(db_session, current_user, company_id):
            return _deny("You don't have access to that company.")
        route = _open_route("company_finance", None, company_id)
        return _open_card_dict("company_finance", card_reason, route, None, company_id)

    # Every other open view is project(site)-scoped.
    if site_id is None:
        return _deny(f"site_id is required to open {target_view}.")
    site = _resolve_visible_site(db_session, current_user, site_id)
    if site is None:
        return _deny("You don't have access to that project.")
    # The site's OWN company is authoritative. The site-finance route requires the query company_id to
    # equal site.company_id, so we derive it from the site (never trust a mismatched caller value) —
    # this makes the route's company == site.company by construction.
    resolved_company_id = getattr(site, "company_id", None)

    if target_view in ("reconciliation", "data_room"):
        # The reconciliation ladder AND the data room (DD documents/files) both require Diligence
        # view server-side, so the deep-link card mirrors that exact guard (fail-closed).
        from app.services.workflows.onboarding_common import can_view_diligence

        if not can_view_diligence(db_session, current_user, site):
            return _deny("You don't have permission to view diligence for this project.")
    elif target_view == "site_finance":
        # Site finance enforces Finance view AND get_authorized_company (plus site == company). We
        # already resolved a visible site and pinned company to site.company_id, so authorize that
        # company too — fail-closed if the caller can't open it.
        if not _can_view_finance(current_user):
            return _deny("You don't have permission to view finance.")
        if resolved_company_id is None or not _authorize_company(
            db_session, current_user, resolved_company_id
        ):
            return _deny("You don't have access to that company.")

    route = _open_route(target_view, site.id, resolved_company_id)
    return _open_card_dict(target_view, card_reason, route, site.id, resolved_company_id)


def _wf_route(workflow_id: str, site_id: Optional[int], company_id: Optional[int]) -> str:
    params = []
    if site_id is not None:
        params.append(f"site_id={site_id}")
    if company_id is not None:
        params.append(f"company_id={company_id}")
    qs = ("?" + "&".join(params)) if params else ""
    return f"/workflows/start/{workflow_id}{qs}"


def build_action_card(
    db_session: Session,
    current_user,
    *,
    kind: str,
    workflow_id: Optional[str] = None,
    sequence_id: Optional[str] = None,
    run_id: Optional[int] = None,
    site_id: Optional[int] = None,
    company_id: Optional[int] = None,
    reason: Optional[str] = None,
    target_view: Optional[str] = None,
    prompt: Optional[str] = None,
    current_route: Optional[str] = None,
    title: Optional[str] = None,
) -> dict:
    """Validate (read-only) and, if permitted, return ``{"permitted", "reason", "action_card"}``.

    Authorization is delegated to the SAME read-only checks the engine/dashboard/read endpoints use,
    threaded with ``current_user``. Performs zero writes/commits and never executes a workflow.

    Navigator kinds:
    - ``open``: needs ``target_view`` (an ``OPEN_TARGET_VIEWS`` member) + the scope it requires
      (``site_id`` for project views, ``company_id`` for company finance). Gated fail-closed by the
      destination's own read permission; the route is derived server-side (never free-form).
    - ``explain``: needs ``prompt`` (a canned read-only question). ``current_route`` is recorded as
      the page being explained. No permission gate beyond assistant access — it only re-prompts the
      read-only chat.
    """
    kind = (kind or "").strip().lower()
    if kind not in VALID_KINDS:
        return _deny(f"Unknown action-card kind {kind!r}.")

    card_reason = (reason or "").strip() or _DEFAULT_REASON[kind]

    if kind == "open":
        return _build_open_card(
            db_session,
            current_user,
            target_view=(target_view or "").strip(),
            site_id=site_id,
            company_id=company_id,
            reason=(reason or "").strip(),
        )

    if kind == "explain":
        explain_prompt = (prompt or "").strip()
        if not explain_prompt:
            return _deny("prompt is required for an explain card.")
        return {
            "permitted": True,
            "reason": None,
            "action_card": {
                "kind": "explain",
                "title": (title or "").strip() or "Explain this page",
                "reason": card_reason,
                # The current page is recorded for context; clicking re-prompts the chat, not nav.
                "route": (current_route or "").strip() or "/",
                "workflow_id": None,
                "sequence_id": None,
                "run_id": None,
                "target_site_id": site_id,
                "target_company_id": company_id,
                "target_view": None,
                "prompt": explain_prompt,
                "requires_user_action": True,
            },
        }

    if kind == "workflow":
        if not workflow_id:
            return _deny("workflow_id is required for a workflow card.")
        from app.services.workflows.definitions import get_definition
        from app.services.workflows.engine import _can_start

        wf = get_definition(workflow_id)
        if wf is None:
            return _deny(f"Unknown workflow {workflow_id!r}.")
        try:
            allowed = bool(_can_start(wf, current_user, db_session))
        except Exception:  # noqa: BLE001 - fail closed
            logger.exception("action card _can_start failed for workflow %r", workflow_id)
            allowed = False
        if not allowed:
            return _deny("You don't have permission to start this workflow.")
        return {
            "permitted": True,
            "reason": None,
            "action_card": {
                "kind": "workflow",
                "title": getattr(wf, "title", None) or workflow_id,
                "reason": card_reason,
                "route": _wf_route(workflow_id, site_id, company_id),
                "workflow_id": workflow_id,
                "sequence_id": None,
                "run_id": None,
                "target_site_id": site_id,
                "target_company_id": company_id,
                "requires_user_action": True,
            },
        }

    if kind == "sequence":
        if not sequence_id:
            return _deny("sequence_id is required for a sequence card.")
        from app.services.workflows.engine import list_sequences

        seq = next(
            (s for s in list_sequences(db_session, current_user).items if s.id == sequence_id),
            None,
        )
        if seq is None:
            return _deny(f"Unknown sequence {sequence_id!r}.")
        if not seq.can_start:
            return _deny("You don't have permission to start this sequence.")
        return {
            "permitted": True,
            "reason": None,
            "action_card": {
                "kind": "sequence",
                "title": seq.title,
                "reason": card_reason,
                "route": f"/workflows/sequences/{sequence_id}",
                "workflow_id": None,
                "sequence_id": sequence_id,
                "run_id": None,
                "target_site_id": site_id,
                "target_company_id": company_id,
                "requires_user_action": True,
            },
        }

    # kind == "resume"
    if run_id is None:
        return _deny("run_id is required for a resume card.")
    from app.services.workflows.engine import list_user_runs

    # list_user_runs is owner-scoped, so a run the caller doesn't own simply won't appear.
    run = next((r for r in list_user_runs(db_session, current_user).items if r.id == run_id), None)
    if run is None:
        return _deny("That run doesn't exist or isn't yours to resume.")
    if run.status in (WorkflowRunStatus.completed, WorkflowRunStatus.abandoned):
        return _deny("That run is already closed — there's nothing to resume.")
    return {
        "permitted": True,
        "reason": None,
        "action_card": {
            "kind": "resume",
            "title": f"Resume: {run.workflow_title or run.workflow_id}",
            "reason": card_reason,
            "route": f"/workflows/runs/{run_id}",
            "workflow_id": run.workflow_id,
            "sequence_id": run.sequence_id,
            "run_id": run_id,
            "target_site_id": run.site_id,
            "target_company_id": run.company_id,
            "requires_user_action": True,
        },
    }
