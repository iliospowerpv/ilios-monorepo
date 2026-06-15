"""W2 weather API router — native historical weather import + lifecycle.

All endpoints live under ``/api/weather`` and operate exclusively against the
native PostgreSQL W0 weather domain (``weather_observations`` /
``weather_observation_batches`` / ``weather_source_profiles`` /
``weather_source_approvals``). There is NO BigQuery / Firestore / legacy /
external-provider / secret access anywhere in this surface.

Authorization model (mirrors the telemetry v2 router):

* **Writes** (import preview, import, profile create, profile actions) require
  ``telemetry_admin_required`` AND a site the caller can administer
  (``get_authorized_site_with_company_admin``), with an explicit
  company-visibility check as defense in depth.
* **Reads** (historical readiness) are visible to any user authorized for the
  site (``get_authorized_site``).
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.crud.weather import WeatherSourceCRUD, WeatherSourceProfileCRUD
from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.authorization.module_based.telemetry import telemetry_admin_required
from app.helpers.authorization.project_access import (
    get_authorized_site,
    get_authorized_site_with_company_admin,
)
from app.helpers.telemetry.audit import create_audit_log as _create_audit_log
from app.models.site import Site
from app.models.weather import WeatherSourceProfileRole
from app.schema.user import CurrentUserSchema
from app.schema.weather import (
    HistoricalImportPreviewRequest,
    HistoricalImportPreviewResponse,
    HistoricalImportRequest,
    HistoricalImportResponse,
    HistoricalProfileCreateRequest,
    WeatherProfileActionRequest,
    WeatherProfileActionResponse,
    WeatherProfileResponse,
    WeatherReadinessResponse,
)
from app.services.weather.historical_weather_import_service import (
    WeatherImportValidationError,
    preview_import,
    run_historical_import,
)
from app.services.weather.weather_profile_service import (
    WeatherProfileActionError,
    apply_profile_action,
    create_historical_profile,
)
from app.services.weather.weather_readiness_service import compute_weather_readiness

logger = logging.getLogger(__name__)

weather_router = APIRouter()


def _enforce_company_visibility(current_user: CurrentUserSchema, company_id: int) -> None:
    """Defense-in-depth company scoping (mirrors the telemetry v2 router).

    The authorized-site dependency already restricts to sites the caller can
    reach, but we re-check the resolved site's company against the caller's
    accessible companies before doing any work.
    """
    if getattr(current_user, "has_platform_bypass", False):
        return
    accessible = set(getattr(current_user, "get_limited_companies_ids", lambda: [])() or [])
    if accessible and company_id not in accessible:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")


def _coerce_naive_utc(value: datetime) -> datetime:
    """Normalize a (possibly tz-aware) datetime to the naive-UTC convention.

    Observations and rollups are stored naive-UTC; readiness windows must be
    compared in the same frame. A tz-aware input is converted to UTC then has
    its tzinfo stripped; a naive input is assumed already-UTC and returned as-is.
    """
    if value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


# ---------------------------------------------------------------------------
# Historical import (writes — telemetry-admin + company-admin gated)
# ---------------------------------------------------------------------------


@weather_router.post(
    "/sites/{site_id}/historical-import/preview",
    response_model=HistoricalImportPreviewResponse,
    summary="Dry-run validate + summarize historical weather rows (no writes)",
    dependencies=[Depends(telemetry_admin_required)],
)
def preview_historical_import(
    payload: HistoricalImportPreviewRequest,
    site: Annotated[Site, Depends(get_authorized_site_with_company_admin)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
) -> HistoricalImportPreviewResponse:
    """Validate + summarize import rows WITHOUT writing anything.

    Every row is validated; structured per-row errors are returned alongside a
    summary of physics-usable vs stored-not-usable and modeled counts. Nothing
    is persisted and no source/batch is created.
    """
    _enforce_company_visibility(current_user, site.company_id)
    return preview_import(payload.rows)


@weather_router.post(
    "/sites/{site_id}/historical-import",
    response_model=HistoricalImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Import historical weather observations (all-or-nothing, idempotent)",
    dependencies=[Depends(telemetry_admin_required)],
)
def import_historical_weather(
    payload: HistoricalImportRequest,
    request: Request,
    site: Annotated[Site, Depends(get_authorized_site_with_company_admin)],
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
) -> HistoricalImportResponse:
    """Import historical weather into the native W0 tables.

    Contract (enforced by the import service):

    - **All-or-nothing.** Validation runs before any write; a single invalid row
      raises and nothing is persisted.
    - **Idempotent.** Re-importing the same window inserts nothing.
    - **Never coerced.** GHI / ambient / unknown rows are stored verbatim and
      reported as stored-not-usable; nothing is converted to POA/cell.
    """
    _enforce_company_visibility(current_user, site.company_id)

    try:
        result = run_historical_import(
            db,
            site_id=site.id,
            request=payload,
            imported_by=getattr(current_user, "id", None),
        )
    except WeatherImportValidationError as exc:
        # All-or-nothing guarantee: nothing was written. Surface every row error.
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": str(exc),
                "errors": [e.model_dump() for e in exc.errors],
            },
        )
    except ValueError as exc:
        # Unknown referenced weather_source_id (no inline source supplied).
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    logger.info(
        "weather_historical_import site_id=%s batch_id=%s received=%s valid=%s "
        "inserted=%s duplicate=%s usable=%s stored_not_usable=%s modeled=%s",
        site.id,
        result.batch_id,
        result.rows_received,
        result.rows_valid,
        result.rows_inserted,
        result.rows_duplicate,
        result.physics_usable_rows,
        result.stored_not_usable_rows,
        result.modeled_rows,
    )

    # Best-effort audit trail; never blocks or rolls back the import.
    try:
        _create_audit_log(
            request,
            db,
            "weather_historical_import",
            (
                f"Imported historical weather for project/site {site.id} "
                f"(batch {result.batch_id}, {result.rows_inserted} inserted, "
                f"{result.rows_duplicate} duplicate)"
            ),
            is_success=True,
        )
    except Exception:  # noqa: BLE001
        logger.warning("weather_historical_import_audit_failed site_id=%s", site.id)

    return result


# ---------------------------------------------------------------------------
# Historical readiness (read — visible to authorized site users)
# ---------------------------------------------------------------------------


@weather_router.get(
    "/sites/{site_id}/historical-readiness",
    response_model=WeatherReadinessResponse,
    summary="Coverage / readiness of historical weather for an expected-replay window",
)
def get_historical_readiness(
    start: Annotated[datetime, Query(description="Window start (UTC).")],
    end: Annotated[datetime, Query(description="Window end (UTC).")],
    site: Annotated[Site, Depends(get_authorized_site)],
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    bucket_size: Annotated[str, Query(description="15m | 30m | 1h | 1d")] = "1h",
) -> WeatherReadinessResponse:
    """Report historical-weather replay readiness for a window (read-only).

    Reports per-bucket usable POA / cell-temperature coverage, coverage gaps,
    unknown-semantics, modeled disclosure, and whether an active historical
    profile governs the window — together with explicit blocking reasons and
    indicator specs. Computes nothing physics-wise and writes nothing.
    """
    _enforce_company_visibility(current_user, site.company_id)

    window_start = _coerce_naive_utc(start)
    window_end = _coerce_naive_utc(end)
    if window_end <= window_start:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "end must be after start.",
        )

    return compute_weather_readiness(
        db,
        site_id=site.id,
        start=window_start,
        end=window_end,
        bucket_size=bucket_size,
    )


# ---------------------------------------------------------------------------
# Historical profile lifecycle (writes — telemetry-admin + company-admin gated)
# ---------------------------------------------------------------------------


@weather_router.post(
    "/sites/{site_id}/historical-profiles",
    response_model=WeatherProfileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a DRAFT historical weather source profile (never auto-activated)",
    dependencies=[Depends(telemetry_admin_required)],
)
def create_historical_weather_profile(
    payload: HistoricalProfileCreateRequest,
    request: Request,
    site: Annotated[Site, Depends(get_authorized_site_with_company_admin)],
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
) -> WeatherProfileResponse:
    """Create a new DRAFT historical profile row.

    The profile is created in ``draft`` status and is NEVER auto-activated — it
    only governs resolution once explicitly approved (``status=active``) via the
    actions endpoint.
    """
    _enforce_company_visibility(current_user, site.company_id)

    if payload.role != WeatherSourceProfileRole.historical:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "This endpoint only creates historical-role profiles.",
        )

    source = WeatherSourceCRUD(db).get_visible_to_site(
        site_id=site.id, source_id=payload.weather_source_id
    )
    if source is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"weather_source_id {payload.weather_source_id} not found "
            f"or not accessible from this project/site",
        )

    profile = create_historical_profile(db, site_id=site.id, request=payload)

    try:
        _create_audit_log(
            request,
            db,
            "weather_historical_profile_create",
            (
                f"Created draft historical weather profile {profile.id} "
                f"for project/site {site.id}"
            ),
            is_success=True,
        )
    except Exception:  # noqa: BLE001
        logger.warning(
            "weather_historical_profile_create_audit_failed site_id=%s", site.id
        )

    return WeatherProfileResponse.from_model(profile)


@weather_router.post(
    "/sites/{site_id}/historical-profiles/{profile_id}/actions",
    response_model=WeatherProfileActionResponse,
    summary="Apply an approval-lifecycle action to a historical weather profile",
    dependencies=[Depends(telemetry_admin_required)],
)
def apply_historical_profile_action(
    profile_id: int,
    payload: WeatherProfileActionRequest,
    request: Request,
    site: Annotated[Site, Depends(get_authorized_site_with_company_admin)],
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
) -> WeatherProfileActionResponse:
    """Apply ``approve`` / ``reject`` / ``revoke`` / ``supersede`` to a profile.

    ``approve`` transitions the profile to ``active`` (so the existing resolver
    profile selection picks it up); every action appends an immutable
    approval-ledger entry and only touches the lifecycle fields, never policy.
    """
    _enforce_company_visibility(current_user, site.company_id)

    # Pre-validate existence + site ownership so a missing/cross-site profile is
    # a clean 404 (never leaking another site's profiles).
    profile = WeatherSourceProfileCRUD(db).get(profile_id)
    if profile is None or profile.site_id != site.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Profile not found")

    try:
        updated, approval = apply_profile_action(
            db,
            site_id=site.id,
            profile_id=profile_id,
            action=payload.action,
            approved_by=getattr(current_user, "id", None),
            rationale=payload.rationale,
        )
    except WeatherProfileActionError as exc:
        # Reaching here means an unknown action (existence/site already checked).
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_ENTITY, str(exc))

    try:
        _create_audit_log(
            request,
            db,
            "weather_historical_profile_action",
            (
                f"Applied '{payload.action}' to historical weather profile "
                f"{profile_id} for project/site {site.id} "
                f"(status {WeatherProfileResponse._ev(updated.status)})"
            ),
            is_success=True,
        )
    except Exception:  # noqa: BLE001
        logger.warning(
            "weather_historical_profile_action_audit_failed site_id=%s", site.id
        )

    return WeatherProfileActionResponse(
        profile=WeatherProfileResponse.from_model(updated),
        approval_id=approval.id,
        action=payload.action,
        status=WeatherProfileResponse._ev(updated.status),
    )
