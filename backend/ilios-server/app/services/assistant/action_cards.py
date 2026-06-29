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

VALID_KINDS = ("workflow", "sequence", "resume")

_DEFAULT_REASON = {
    "workflow": "Open this guided workflow to do it yourself — the assistant can't run it for you.",
    "sequence": "Open this guided sequence to walk through the steps yourself.",
    "resume": "Pick up this in-progress run where you left off.",
}


def _deny(reason: str) -> dict:
    return {"permitted": False, "reason": reason, "action_card": None}


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
) -> dict:
    """Validate (read-only) and, if permitted, return ``{"permitted", "reason", "action_card"}``.

    Authorization is delegated to the SAME read-only checks the engine/dashboard use, threaded with
    ``current_user``. Performs zero writes/commits and never executes a workflow.
    """
    kind = (kind or "").strip().lower()
    if kind not in VALID_KINDS:
        return _deny(f"Unknown action-card kind {kind!r}.")

    card_reason = (reason or "").strip() or _DEFAULT_REASON[kind]

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
