"""READ-ONLY AI-orchestration context envelope (Phase 3).

Bundles every authorized onboarding signal — workflow catalog, sequences, the caller's open runs,
completion metrics, onboarding progress, readiness, and next-action recommendations — into ONE
versioned, read-only envelope a FUTURE AI advisor can reason over WITHOUT being able to act. The
envelope is explicitly self-describing as non-executable (``mode="read_only_advice"`` plus a
machine-readable ``prohibited_actions`` list). This endpoint starts nothing, writes nothing, and
grants nothing — it composes the same read-only services the dashboard uses, under the same authz.
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.schema.workflow import OrchestrationContextResponse
from app.services.workflows.onboarding_common import DEFAULT_SITES

# Bump when the envelope's shape changes so consumers can pin a contract.
SCHEMA_VERSION = "workflow_orchestration_context.v1"

# Explicit, machine-readable non-execution contract. This envelope is ADVICE ONLY: a consumer
# (including an AI) must treat all of the following as forbidden — they remain the exclusive
# domain of the governed, human-authorized endpoints, never the orchestration layer.
PROHIBITED_ACTIONS = [
    "start_or_advance_workflow_run",
    "execute_workflow_step",
    "promote_project_fact",
    "approve_or_activate_expected_baseline",
    "map_or_unmap_device",
    "create_or_change_weather_declaration",
    "bypass_authorization_or_permissions",
    "write_or_mutate_any_operational_truth",
]


def build_orchestration_context(
    db_session: Session, current_user, *, limit: int = DEFAULT_SITES
) -> OrchestrationContextResponse:
    from app.services.workflows.engine import (
        compute_metrics,
        list_sequences,
        list_user_runs,
        list_workflow_definitions,
    )
    from app.services.workflows.onboarding_progress_service import (
        build_onboarding_progress,
    )
    from app.services.workflows.readiness_summary_service import build_readiness_summary
    from app.services.workflows.recommendations_service import build_recommendations

    return OrchestrationContextResponse(
        schema_version=SCHEMA_VERSION,
        mode="read_only_advice",
        generated_at=datetime.now(timezone.utc),
        actor_scope="me",
        available_workflows=list_workflow_definitions(db_session, current_user).items,
        sequences=list_sequences(db_session, current_user).items,
        runs_summary=list_user_runs(db_session, current_user).items,
        metrics=compute_metrics(db_session, current_user, scope="me"),
        progress=build_onboarding_progress(db_session, current_user, limit=limit),
        readiness=build_readiness_summary(db_session, current_user, limit=limit),
        recommendations=build_recommendations(db_session, current_user).items,
        prohibited_actions=list(PROHIBITED_ACTIONS),
    )
