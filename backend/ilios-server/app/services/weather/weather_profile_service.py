"""W2 weather source profile lifecycle helpers.

Profiles govern WHICH weather source drives a site over an effective window. W0
defines them as versioned-by-new-row with an explicit approval lifecycle and no
auto-activation; this service is the small write seam that creates draft profiles
and applies approval actions, recording an immutable ledger entry for each.

Lifecycle mapping:

* ``approve``   → status ``active`` (so the existing, UNCHANGED resolver
  ``_select_active_profile`` picks it up) + stamp ``approved_by``/``approved_at``.
* ``reject``    → status ``rejected``.
* ``revoke``    → status ``superseded`` (withdraw a previously active profile).
* ``supersede`` → status ``superseded`` (replaced by a newer profile row).

Only the lifecycle fields are ever mutated; any policy change must be a NEW
profile row. No external/provider/secret/BigQuery/Firestore access.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.crud.weather import (
    WeatherSourceApprovalCRUD,
    WeatherSourceCRUD,
    WeatherSourceProfileCRUD,
)
from app.models.weather import (
    WeatherApprovalAction,
    WeatherApprovalTargetType,
    WeatherSourceProfile,
    WeatherSourceProfileStatus,
)
from app.schema.weather import HistoricalProfileCreateRequest

# action string → (ledger action, resulting profile status, stamps approval?)
_ACTION_MAP: dict[str, tuple[WeatherApprovalAction, WeatherSourceProfileStatus, bool]] = {
    "approve": (
        WeatherApprovalAction.approve,
        WeatherSourceProfileStatus.active,
        True,
    ),
    "reject": (
        WeatherApprovalAction.reject,
        WeatherSourceProfileStatus.rejected,
        False,
    ),
    "revoke": (
        WeatherApprovalAction.revoke,
        WeatherSourceProfileStatus.superseded,
        False,
    ),
    "supersede": (
        WeatherApprovalAction.supersede,
        WeatherSourceProfileStatus.superseded,
        False,
    ),
}


class WeatherProfileActionError(Exception):
    """Raised for an unknown action, missing profile, or cross-site profile."""


def create_historical_profile(
    db: Session,
    *,
    site_id: int,
    request: HistoricalProfileCreateRequest,
) -> WeatherSourceProfile:
    """Create a DRAFT weather source profile (new row, never auto-activated).

    Defense-in-depth: the referenced source must be visible to ``site_id`` (site-
    scoped to this site, company-scoped to its company, or global). A source
    bound to another site/company raises ``ValueError`` so a profile can never be
    created against another tenant's weather source — even for non-router callers.
    """
    source = WeatherSourceCRUD(db).get_visible_to_site(
        site_id=site_id, source_id=request.weather_source_id
    )
    if source is None:
        raise ValueError(
            f"weather_source_id {request.weather_source_id} not found "
            f"or not accessible from site {site_id}"
        )
    return WeatherSourceProfileCRUD(db).create(
        site_id=site_id,
        role=request.role,
        weather_source_id=request.weather_source_id,
        priority=request.priority,
        effective_from=request.effective_from,
        effective_to=request.effective_to,
        fallback_allowed=request.fallback_allowed,
        external_modeled_allowed=request.external_modeled_allowed,
        min_confidence_policy=request.min_confidence_policy,
        status=WeatherSourceProfileStatus.draft,
        notes=request.notes,
    )


def apply_profile_action(
    db: Session,
    *,
    site_id: int,
    profile_id: int,
    action: str,
    approved_by: Optional[int] = None,
    rationale: Optional[str] = None,
    now: Optional[datetime] = None,
) -> tuple[WeatherSourceProfile, object]:
    """Apply an approval-lifecycle action to a profile + append a ledger entry.

    Returns ``(updated_profile, approval_entry)``. Raises
    :class:`WeatherProfileActionError` for an unknown action, an unknown profile,
    or a profile that belongs to another site.
    """
    normalized = (action or "").strip().lower()
    mapping = _ACTION_MAP.get(normalized)
    if mapping is None:
        raise WeatherProfileActionError(f"unknown action: {action!r}")
    ledger_action, new_status, stamps_approval = mapping

    profile_crud = WeatherSourceProfileCRUD(db)
    profile = profile_crud.get(profile_id)
    if profile is None:
        raise WeatherProfileActionError(f"profile {profile_id} not found")
    if profile.site_id != site_id:
        raise WeatherProfileActionError(
            f"profile {profile_id} does not belong to site {site_id}"
        )

    stamp_at = now or datetime.utcnow()
    updated = profile_crud.set_lifecycle_status(
        profile_id,
        status=new_status,
        approved_by=approved_by if stamps_approval else None,
        approved_at=stamp_at if stamps_approval else None,
    )

    approval = WeatherSourceApprovalCRUD(db).record(
        site_id=site_id,
        target_type=WeatherApprovalTargetType.profile,
        target_id=profile_id,
        action=ledger_action,
        approved_by=approved_by,
        approved_at=stamp_at,
        rationale=rationale,
    )
    return updated, approval
