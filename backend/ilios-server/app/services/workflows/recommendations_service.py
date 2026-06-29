"""READ-ONLY next-action recommendations (Phase 3).

Deterministic, rule-based ranking of which EXISTING workflow/sequence the caller might run next,
derived from: their open runs, the per-site onboarding gaps (from the read-only progress rollup),
and each workflow's own start permission. Every item is a LINK/HINT only — nothing is auto-started
and nothing here promotes facts, approves/activates baselines, maps devices, or declares weather
semantics (those governed actions are intentionally never recommended as automatable). No writes.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models.workflow import WorkflowRunStatus
from app.schema.workflow import RecommendationSchema, RecommendationsResponse
from app.services.workflows.onboarding_progress_service import build_onboarding_progress

MAX_RECOMMENDATIONS = 10


def _can_start_workflow(db_session: Session, current_user, workflow_id: str) -> bool:
    from app.services.workflows.definitions import get_definition
    from app.services.workflows.engine import _can_start

    wf = get_definition(workflow_id)
    if wf is None:
        return False
    try:
        return bool(_can_start(wf, current_user, db_session))
    except Exception:
        return False


def build_recommendations(
    db_session: Session, current_user, *, limit: int = MAX_RECOMMENDATIONS
) -> RecommendationsResponse:
    from app.services.workflows.engine import list_sequences, list_user_runs

    cap = max(1, min(int(limit or MAX_RECOMMENDATIONS), MAX_RECOMMENDATIONS))
    recs: list[RecommendationSchema] = []

    sequences = {s.id: s for s in list_sequences(db_session, current_user).items}

    # --- Resume open runs (highest priority — finish what you started) ----------------
    runs = list_user_runs(db_session, current_user).items
    open_runs = [
        r
        for r in runs
        if r.status not in (WorkflowRunStatus.completed, WorkflowRunStatus.abandoned)
    ]
    for r in open_runs[:3]:
        recs.append(
            RecommendationSchema(
                kind="workflow",
                workflow_id=r.workflow_id,
                title=f"Resume: {r.workflow_title or r.workflow_id}",
                reason="You have an in-progress run — pick up where you left off.",
                priority=10,
                target_site_id=r.site_id,
                target_company_id=r.company_id,
                route=f"/workflows/runs/{r.id}",
            )
        )

    # --- Per-site gaps from the read-only progress rollup -----------------------------
    progress = build_onboarding_progress(db_session, current_user, limit=50)

    if not progress.items:
        seq = sequences.get("onboarding")
        if seq is not None and seq.can_start:
            recs.append(
                RecommendationSchema(
                    kind="sequence",
                    sequence_id="onboarding",
                    title=seq.title,
                    reason="No projects yet — start by onboarding a company and its first project.",
                    priority=20,
                    route="/workflows/sequences/onboarding",
                )
            )
    else:
        upload_ok = _can_start_workflow(db_session, current_user, "document_upload")
        # Gate per-site upload recommendations on the TARGET site's Diligence ``edit`` (not the
        # ``view`` that makes the progress stage merely evaluable). The upload workflow itself
        # requires Diligence ``edit``, so recommending it for a view-only project would be a
        # dead-end card. None == platform-bypass == every site is editable.
        from app.services.workflows.definitions import _diligence_editable_site_ids

        editable = _diligence_editable_site_ids(db_session, current_user)
        for item in progress.items:
            stage = next(
                (
                    s
                    for s in item.stages
                    if s.key == "diligence_facts_ready" and s.available and not s.done
                ),
                None,
            )
            site_editable = editable is None or item.site_id in editable
            if stage is not None and upload_ok and site_editable:
                recs.append(
                    RecommendationSchema(
                        kind="workflow",
                        workflow_id="document_upload",
                        title=f"Add a document to {item.site_name or f'Project {item.site_id}'}",
                        reason="This project has no promoted diligence terms yet — upload a document to begin.",
                        priority=30,
                        target_site_id=item.site_id,
                        target_company_id=item.company_id,
                        route=f"/workflows/start/document_upload?site_id={item.site_id}",
                    )
                )

    # --- Invite a teammate (lower priority, once at least one project exists) ----------
    if progress.items and _can_start_workflow(db_session, current_user, "invite_user"):
        first = progress.items[0]
        recs.append(
            RecommendationSchema(
                kind="workflow",
                workflow_id="invite_user",
                title="Invite a teammate",
                reason="Bring a collaborator into your portfolio.",
                priority=50,
                target_company_id=first.company_id,
                route="/workflows/start/invite_user",
            )
        )

    recs.sort(key=lambda r: (r.priority, r.target_site_id or 0))
    return RecommendationsResponse(
        generated_at=datetime.now(timezone.utc),
        scope="me",
        items=recs[:cap],
    )
