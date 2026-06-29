"""READ-ONLY readiness summary (Phase 3).

Per authorized project (site), consolidates FOUR existing read-only services into one envelope:
telemetry health, due-diligence reconciliation readiness, device-eligibility diagnostics, and
expected-baseline existence. Each dimension is its own section that degrades INDEPENDENTLY: a
section the caller may not see (e.g. Diligence without Diligence:view) or that errors becomes
``available=False`` with a reason, so one denied/failing dimension never fails the whole summary.
No verdict is recomputed — every value is read verbatim from the wrapped service. No writes.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.schema.workflow import (
    ReadinessSectionSchema,
    ReadinessSummaryResponse,
    SiteReadinessSchema,
)
from app.services.workflows.onboarding_common import (
    DEFAULT_SITES,
    can_view_diligence,
    resolve_candidate_sites,
    scope_label,
)


def _iso(value) -> Optional[str]:
    try:
        return value.isoformat() if value is not None else None
    except Exception:
        return None


def _telemetry_health_section(db_session: Session, site) -> ReadinessSectionSchema:
    try:
        from app.services.telemetry.health_service import compute_site_telemetry_health

        health = compute_site_telemetry_health(db_session, site)
        status = getattr(health.status, "value", str(health.status))
        return ReadinessSectionSchema(
            available=True,
            status=status,
            summary=(
                f"{health.mapped_device_count} mapped device(s); "
                f"{'connected' if health.is_connected and health.is_site_mapped else 'not connected'}"
            ),
            data={
                "status": status,
                "mapped_device_count": health.mapped_device_count,
                "last_data_at": _iso(health.last_data_at),
                "data_delay_minutes": health.data_delay_minutes,
                "is_connected": health.is_connected,
                "is_site_mapped": health.is_site_mapped,
            },
        )
    except Exception:
        return ReadinessSectionSchema(available=False, reason="unavailable")


def _reconciliation_section(db_session: Session, current_user, site) -> ReadinessSectionSchema:
    if not can_view_diligence(db_session, current_user, site):
        return ReadinessSectionSchema(available=False, reason="permission_denied")
    try:
        from app.services.due_diligence.reconciliation_service import (
            build_site_reconciliation,
        )

        recon = build_site_reconciliation(db_session, site)
        r = recon.readiness
        ready = bool(r.facts_to_draft_ready)
        return ReadinessSectionSchema(
            available=True,
            status="ready" if ready else "blocked",
            summary=(
                "Facts ready to draft a baseline."
                if ready
                else (
                    f"Missing {len(r.missing_required_physics_fields)} required field(s)."
                    if r.missing_required_physics_fields
                    else "Diligence terms not yet promoted."
                )
            ),
            data={
                "facts_to_draft_ready": r.facts_to_draft_ready,
                "missing_required_physics_fields": r.missing_required_physics_fields,
                "active_baseline_available": r.active_baseline_available,
                "active_baseline_id": r.active_baseline_id,
            },
        )
    except Exception:
        return ReadinessSectionSchema(available=False, reason="unavailable")


def _eligibility_section(db_session: Session, site) -> ReadinessSectionSchema:
    try:
        from app.services.telemetry.device_eligibility_diagnostics_service import (
            compute_site_eligibility_diagnostics,
        )

        diag = compute_site_eligibility_diagnostics(db_session, site=site)
        return ReadinessSectionSchema(
            available=True,
            status=(
                "drivers_present" if diag.expected_driving_count > 0 else "no_drivers"
            ),
            summary=(
                f"{diag.mapped_count}/{diag.mappable_count} mappable device(s) mapped; "
                f"{diag.expected_driving_count} drive expected"
            ),
            data={
                "total_devices": diag.total_devices,
                "mappable_count": diag.mappable_count,
                "mapped_count": diag.mapped_count,
                "expected_driving_count": diag.expected_driving_count,
                "unmapped_eligible_count": diag.unmapped_eligible_count,
                "weather_unknown_semantics_count": diag.weather_unknown_semantics_count,
            },
        )
    except Exception:
        return ReadinessSectionSchema(available=False, reason="unavailable")


def _expected_baseline_section(db_session: Session, site) -> ReadinessSectionSchema:
    try:
        from app.crud.telemetry_expected import TelemetryExpectedBaselineCRUD

        crud = TelemetryExpectedBaselineCRUD(db_session)
        active = crud.get_active(site.id)
        all_baselines = crud.list_for_site(site.id)
        draft_exists = any(
            getattr(b.status, "value", str(b.status)) != "active" for b in all_baselines
        )
        status = "active" if active is not None else ("draft" if draft_exists else "none")
        return ReadinessSectionSchema(
            available=True,
            status=status,
            summary={
                "active": "Live expected baseline active.",
                "draft": "A baseline exists but is not yet active.",
                "none": "No expected baseline yet.",
            }[status],
            data={
                "active_baseline_exists": active is not None,
                "active_baseline_id": active.id if active is not None else None,
                "draft_baseline_exists": draft_exists,
            },
        )
    except Exception:
        return ReadinessSectionSchema(available=False, reason="unavailable")


def build_readiness_summary(
    db_session: Session,
    current_user,
    *,
    site_id: Optional[int] = None,
    company_id: Optional[int] = None,
    limit: int = DEFAULT_SITES,
) -> ReadinessSummaryResponse:
    sites = resolve_candidate_sites(
        db_session, current_user, site_id=site_id, company_id=company_id, limit=limit
    )
    items: list[SiteReadinessSchema] = []
    for site in sites:
        items.append(
            SiteReadinessSchema(
                site_id=site.id,
                site_name=site.name,
                company_id=site.company_id,
                telemetry_health=_telemetry_health_section(db_session, site),
                reconciliation=_reconciliation_section(db_session, current_user, site),
                device_eligibility=_eligibility_section(db_session, site),
                expected_baseline=_expected_baseline_section(db_session, site),
            )
        )
    return ReadinessSummaryResponse(
        generated_at=datetime.now(timezone.utc),
        scope=scope_label(site_id, company_id),
        total_sites=len(items),
        items=items,
    )
