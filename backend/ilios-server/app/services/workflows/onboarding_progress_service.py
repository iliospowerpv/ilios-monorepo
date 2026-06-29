"""READ-ONLY onboarding-progress rollup (Phase 3).

For each authorized project (site) this builds a small stage checklist whose every ``done`` is
derived by CALLING an existing domain service and reading its verdict verbatim — it computes no
operational truth of its own. A stage gated by a module the caller lacks is marked
``available=False`` and excluded from the completion ratio (never silently counted as done). No
writes, no commits; the wrapped endpoints remain the authoritative guards.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.schema.workflow import (
    OnboardingProgressResponse,
    OnboardingStageSchema,
    SiteOnboardingProgressSchema,
)
from app.services.workflows.onboarding_common import (
    DEFAULT_SITES,
    can_view_diligence,
    resolve_candidate_sites,
    scope_label,
)


def _telemetry_health(db_session: Session, site):
    from app.services.telemetry.health_service import compute_site_telemetry_health

    return compute_site_telemetry_health(db_session, site)


def _site_stages(db_session: Session, current_user, site) -> list[OnboardingStageSchema]:
    stages: list[OnboardingStageSchema] = []

    # 1. Project created — trivially true (we are iterating real, authorized sites).
    stages.append(
        OnboardingStageSchema(
            key="project_created",
            label="Project created",
            done=True,
            available=True,
            detail=site.name or f"Project {site.id}",
        )
    )

    # 2/3. Diligence facts ready + a baseline drafted — read from reconciliation (Diligence:view).
    if can_view_diligence(db_session, current_user, site):
        try:
            from app.services.due_diligence.reconciliation_service import (
                build_site_reconciliation,
            )

            recon = build_site_reconciliation(db_session, site)
            facts_ready = bool(recon.readiness.facts_to_draft_ready)
            drafted = (
                recon.readiness.design_estimate_baseline_id is not None
                or recon.readiness.active_baseline_available
            )
            missing = recon.readiness.missing_required_physics_fields
            stages.append(
                OnboardingStageSchema(
                    key="diligence_facts_ready",
                    label="Diligence terms promoted",
                    done=facts_ready,
                    available=True,
                    detail=(
                        None
                        if facts_ready
                        else (
                            f"Missing required fields: {', '.join(missing[:6])}"
                            if missing
                            else "Promote diligence terms in the Data Room."
                        )
                    ),
                )
            )
            stages.append(
                OnboardingStageSchema(
                    key="expected_baseline_drafted",
                    label="Expected baseline drafted",
                    done=bool(drafted),
                    available=True,
                )
            )
        except Exception:
            for key, label in (
                ("diligence_facts_ready", "Diligence terms promoted"),
                ("expected_baseline_drafted", "Expected baseline drafted"),
            ):
                stages.append(
                    OnboardingStageSchema(
                        key=key, label=label, done=False, available=False,
                        detail="Diligence readiness is temporarily unavailable.",
                    )
                )
    else:
        for key, label in (
            ("diligence_facts_ready", "Diligence terms promoted"),
            ("expected_baseline_drafted", "Expected baseline drafted"),
        ):
            stages.append(
                OnboardingStageSchema(
                    key=key, label=label, done=False, available=False,
                    detail="Requires Diligence access.",
                )
            )

    # 4. Active expected baseline — read the baseline truth-store (no recompute).
    try:
        from app.crud.telemetry_expected import TelemetryExpectedBaselineCRUD

        active = TelemetryExpectedBaselineCRUD(db_session).get_active(site.id)
        stages.append(
            OnboardingStageSchema(
                key="expected_baseline_active",
                label="Expected baseline activated",
                done=active is not None,
                available=True,
            )
        )
    except Exception:
        stages.append(
            OnboardingStageSchema(
                key="expected_baseline_active", label="Expected baseline activated",
                done=False, available=False,
                detail="Baseline status is temporarily unavailable.",
            )
        )

    # 5/6. Telemetry connected + healthy — read telemetry health (no recompute).
    try:
        health = _telemetry_health(db_session, site)
        connected = bool(health.is_connected and health.is_site_mapped)
        status_value = getattr(health.status, "value", str(health.status))
        healthy = status_value in ("HEALTHY", "WARN")
        stages.append(
            OnboardingStageSchema(
                key="telemetry_connected",
                label="Telemetry connected",
                done=connected,
                available=True,
                detail=None if connected else "No DAS connection / site mapping yet.",
            )
        )
        stages.append(
            OnboardingStageSchema(
                key="telemetry_healthy",
                label="Telemetry flowing",
                done=healthy,
                available=True,
                detail=None if healthy else f"Health: {status_value}",
            )
        )
    except Exception:
        for key, label in (
            ("telemetry_connected", "Telemetry connected"),
            ("telemetry_healthy", "Telemetry flowing"),
        ):
            stages.append(
                OnboardingStageSchema(
                    key=key, label=label, done=False, available=False,
                    detail="Telemetry health is temporarily unavailable.",
                )
            )

    return stages


def build_onboarding_progress(
    db_session: Session,
    current_user,
    *,
    site_id: Optional[int] = None,
    company_id: Optional[int] = None,
    limit: int = DEFAULT_SITES,
) -> OnboardingProgressResponse:
    sites = resolve_candidate_sites(
        db_session, current_user, site_id=site_id, company_id=company_id, limit=limit
    )
    items: list[SiteOnboardingProgressSchema] = []
    for site in sites:
        stages = _site_stages(db_session, current_user, site)
        evaluable = [s for s in stages if s.available]
        completed = sum(1 for s in evaluable if s.done)
        total = len(evaluable)
        items.append(
            SiteOnboardingProgressSchema(
                site_id=site.id,
                site_name=site.name,
                company_id=site.company_id,
                completed_stages=completed,
                total_stages=total,
                completion_rate=round(completed / total, 4) if total else 0.0,
                stages=stages,
            )
        )
    return OnboardingProgressResponse(
        generated_at=datetime.now(timezone.utc),
        scope=scope_label(site_id, company_id),
        total_sites=len(items),
        items=items,
    )
