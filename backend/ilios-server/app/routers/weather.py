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

from app.crud.weather import (
    WeatherDeviceMappingCRUD,
    WeatherSourceCRUD,
    WeatherSourceProfileCRUD,
)
from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.authorization.module_based.telemetry import telemetry_admin_required
from app.helpers.authorization.project_access import (
    get_authorized_site,
    get_authorized_site_with_company_admin,
)
from app.helpers.telemetry.audit import create_audit_log as _create_audit_log
from app.models.device import Device
from app.models.site import Site
from app.models.weather import WeatherSourceProfileRole
from app.schema.user import CurrentUserSchema
from app.schema.weather import (
    HistoricalImportPreviewRequest,
    HistoricalImportPreviewResponse,
    HistoricalImportRequest,
    HistoricalImportResponse,
    HistoricalProfileCreateRequest,
    WeatherDeclarationActivateRequest,
    WeatherDeclarationReReviewRequest,
    WeatherDeviceMappingDeclareRequest,
    WeatherDeviceMappingResponse,
    WeatherProfileActionRequest,
    WeatherProfileActionResponse,
    WeatherProfileResponse,
    WeatherReadinessResponse,
    WeatherSemanticsReconciliationResponse,
    WeatherUpstreamReEvaluateResponse,
)
from app.services.telemetry.device_classification import classify_device
from app.services.weather.declaration_service import (
    DeclarationServiceError,
    activate_declaration,
    create_declaration,
    mark_needs_re_review,
)
from app.services.weather.historical_weather_import_service import (
    WeatherImportValidationError,
    preview_import,
    run_historical_import,
)
from app.services.weather.semantics_reconciliation_service import (
    build_site_semantics_reconciliation,
)
from app.services.weather.upstream_change_detector import (
    apply_re_review,
    detect_site,
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


# ---------------------------------------------------------------------------
# Weather device semantics (declare what a device's weather stream MEANS)
# ---------------------------------------------------------------------------


@weather_router.get(
    "/sites/{site_id}/device-mappings",
    response_model=list[WeatherDeviceMappingResponse],
    summary="List declared weather measurement semantics for a site's devices",
)
def list_weather_device_mappings(
    site: Annotated[Site, Depends(get_authorized_site)],
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
) -> list[WeatherDeviceMappingResponse]:
    """List every declared weather device mapping for a site (read-only).

    Returns the full append-only declaration history (oldest first). The current
    semantics for a device/metric are the latest row; nothing is converted — a row
    discloses ``physics_usable_*`` purely from its declared plane/temperature.
    """
    _enforce_company_visibility(current_user, site.company_id)
    mappings = WeatherDeviceMappingCRUD(db).list_for_site(site.id)
    return [WeatherDeviceMappingResponse.from_model(m) for m in mappings]


@weather_router.post(
    "/sites/{site_id}/device-mappings",
    response_model=WeatherDeviceMappingResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Declare measurement semantics for a weather-source device stream",
    dependencies=[Depends(telemetry_admin_required)],
)
def declare_weather_device_mapping(
    payload: WeatherDeviceMappingDeclareRequest,
    request: Request,
    site: Annotated[Site, Depends(get_authorized_site_with_company_admin)],
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
) -> WeatherDeviceMappingResponse:
    """Declare what a device's weather stream MEANS (plane / temperature / calibration).

    Semantics are NEVER guessed: they default to ``unknown`` and only this explicit
    declaration sets POA / cell / etc. W0/W2 performs NO conversion — declaring GHI
    does not transpose it to POA. The target device must be weather-source capable;
    a NEW effective-dated mapping row is appended so history is never rewritten. This
    does NOT change WeatherResolver source priority, expected math, or ingestion.
    """
    _enforce_company_visibility(current_user, site.company_id)

    device = (
        db.query(Device)
        .filter(Device.id == payload.device_id, Device.site_id == site.id)
        .one_or_none()
    )
    if device is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Device {payload.device_id} not found on this project/site",
        )

    if not classify_device(device).weather_source_capable:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            (
                f"Device {payload.device_id} is not weather-source capable; assign a "
                "weather role/capability to the device before declaring weather "
                "semantics. Semantics are never inferred from a non-weather device."
            ),
        )

    if payload.weather_source_id is not None:
        source = WeatherSourceCRUD(db).get_visible_to_site(
            site_id=site.id, source_id=payload.weather_source_id
        )
        if source is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"weather_source_id {payload.weather_source_id} not found or not "
                "accessible from this project/site",
            )

    try:
        mapping = create_declaration(
            db,
            site=site,
            device=device,
            payload=payload,
            actor_id=getattr(current_user, "id", None),
        )
    except DeclarationServiceError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc

    try:
        _create_audit_log(
            request,
            db,
            "weather_device_mapping_declare",
            (
                f"Declared weather semantics for device {device.id} on project/site "
                f"{site.id} (metric {payload.metric}, plane "
                f"{WeatherDeviceMappingResponse._ev(mapping.irradiance_plane)}, temp "
                f"{WeatherDeviceMappingResponse._ev(mapping.temperature_type)})"
            ),
            is_success=True,
        )
    except Exception:  # noqa: BLE001
        logger.warning(
            "weather_device_mapping_declare_audit_failed site_id=%s", site.id
        )

    return WeatherDeviceMappingResponse.from_model(mapping)


@weather_router.post(
    "/sites/{site_id}/device-mappings/{mapping_id}/activate",
    response_model=WeatherDeviceMappingResponse,
    summary="Activate a draft weather-semantics declaration (atomic supersede)",
    dependencies=[Depends(telemetry_admin_required)],
)
def activate_weather_device_mapping(
    mapping_id: int,
    payload: WeatherDeclarationActivateRequest,
    request: Request,
    site: Annotated[Site, Depends(get_authorized_site_with_company_admin)],
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
) -> WeatherDeviceMappingResponse:
    """Activate an existing draft declaration (``draft -> active``).

    Runs full governance validation (basis evidence completeness) and, when the
    draft carries a ``supersedes_mapping_id``, atomically flips the prior active
    row to ``superseded`` in the SAME transaction (single-active is enforced). This
    NEVER infers semantics and NEVER touches the resolver/expected math, ingestion,
    rollups, the scheduler, baselines, or O&M — it only records that a governed
    declaration is now in force. A structured 409 is returned for an illegal
    transition or a single-active conflict; 422 for an incomplete basis.
    """
    _enforce_company_visibility(current_user, site.company_id)

    try:
        mapping = activate_declaration(
            db,
            site=site,
            mapping_id=mapping_id,
            actor_id=getattr(current_user, "id", None),
            rationale=payload.rationale,
        )
    except DeclarationServiceError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc

    try:
        _create_audit_log(
            request,
            db,
            "weather_device_mapping_activate",
            (
                f"Activated weather declaration {mapping.id} for device "
                f"{mapping.device_id} on project/site {site.id} "
                f"(metric {mapping.metric}, basis "
                f"{WeatherDeviceMappingResponse._ev(mapping.declaration_basis)})"
            ),
            is_success=True,
        )
    except Exception:  # noqa: BLE001
        logger.warning(
            "weather_device_mapping_activate_audit_failed site_id=%s", site.id
        )

    return WeatherDeviceMappingResponse.from_model(mapping)


@weather_router.post(
    "/sites/{site_id}/device-mappings/{mapping_id}/re-review",
    response_model=WeatherDeviceMappingResponse,
    summary="Flag an active weather declaration as needing re-review",
    dependencies=[Depends(telemetry_admin_required)],
)
def flag_weather_device_mapping_re_review(
    mapping_id: int,
    payload: WeatherDeclarationReReviewRequest,
    request: Request,
    site: Annotated[Site, Depends(get_authorized_site_with_company_admin)],
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
) -> WeatherDeviceMappingResponse:
    """Manually raise the monotonic ``needs_re_review`` flag on an ACTIVE declaration.

    ``needs_re_review`` is a boolean flag (NOT a status) and is NEVER auto-cleared —
    it clears only when a NEW activated declaration supersedes this row. This is a
    Layer-1 governance signal: it changes no semantics and no expected/baseline. A
    re-flag of an already-flagged row is rejected (409) rather than re-stamped.
    """
    _enforce_company_visibility(current_user, site.company_id)

    try:
        mapping = mark_needs_re_review(
            db,
            site=site,
            mapping_id=mapping_id,
            actor_id=getattr(current_user, "id", None),
            reason=payload.reason,
        )
    except DeclarationServiceError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc

    try:
        _create_audit_log(
            request,
            db,
            "weather_device_mapping_re_review",
            (
                f"Flagged weather declaration {mapping.id} for re-review on "
                f"project/site {site.id} (metric {mapping.metric})"
            ),
            is_success=True,
        )
    except Exception:  # noqa: BLE001
        logger.warning(
            "weather_device_mapping_re_review_audit_failed site_id=%s", site.id
        )

    return WeatherDeviceMappingResponse.from_model(mapping)


@weather_router.get(
    "/sites/{site_id}/devices/{device_id}/device-mappings",
    response_model=list[WeatherDeviceMappingResponse],
    summary="Declaration history/lineage for a device (append-only, oldest-first)",
)
def list_weather_device_mapping_history(
    device_id: int,
    site: Annotated[Site, Depends(get_authorized_site)],
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
) -> list[WeatherDeviceMappingResponse]:
    """Full append-only declaration history for one device (oldest-first, read-only).

    Visible to any user authorized for the site (asset-view + company-visibility);
    reads never require admin. Each row discloses its governed lifecycle
    (draft/active/superseded, basis, evidence, re-review flag) and its DERIVED
    eligibility verdict (recomputed live). Nothing is converted into a value.
    """
    _enforce_company_visibility(current_user, site.company_id)

    device = (
        db.query(Device)
        .filter(Device.id == device_id, Device.site_id == site.id)
        .one_or_none()
    )
    if device is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Device {device_id} not found on this project/site",
        )

    mappings = WeatherDeviceMappingCRUD(db).list_for_device(device_id)
    return [WeatherDeviceMappingResponse.from_model(m) for m in mappings]


@weather_router.get(
    "/sites/{site_id}/device-mappings/upstream-changes",
    response_model=WeatherUpstreamReEvaluateResponse,
    summary="Preview upstream-change / stale status for a site's declarations",
)
def preview_weather_upstream_changes(
    site: Annotated[Site, Depends(get_authorized_site)],
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
) -> WeatherUpstreamReEvaluateResponse:
    """READ-ONLY preview of upstream drift across a site's ACTIVE declarations.

    For each active governed declaration this recomputes the device's current
    upstream identity and compares it to the fingerprint snapshot taken at
    declaration time, reporting which declarations have drifted (``diverged``) and
    which WOULD be flagged for re-review (``would_flag``) by the admin re-evaluate
    action. It performs NO writes/commits and never alters semantics, expected, or
    baselines. Visible to any user authorized for the site (asset-view +
    company-visibility); reads never require admin.
    """
    _enforce_company_visibility(current_user, site.company_id)
    report = detect_site(db, site=site)
    return WeatherUpstreamReEvaluateResponse.from_report(report)


@weather_router.post(
    "/sites/{site_id}/device-mappings/re-evaluate",
    response_model=WeatherUpstreamReEvaluateResponse,
    summary="Re-evaluate upstream drift and flag stale declarations for re-review",
    dependencies=[Depends(telemetry_admin_required)],
)
def re_evaluate_weather_upstream_changes(
    request: Request,
    site: Annotated[Site, Depends(get_authorized_site_with_company_admin)],
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
) -> WeatherUpstreamReEvaluateResponse:
    """Admin re-evaluation: raise the monotonic ``needs_re_review`` flag on drifted rows.

    For every ACTIVE declaration whose device upstream identity diverged from its
    declaration-time fingerprint AND that is not already flagged, this raises the
    monotonic ``needs_re_review`` flag (+ ``re_review_reason`` + a ``needs_re_review``
    ledger entry) — exactly the change the WS.1 append-only guard permits on an
    active row. Already-flagged rows are SKIPPED so the action is idempotent. It
    NEVER creates/activates/supersedes/clears a declaration, never edits semantics,
    and never touches expected/baselines/``expected_weather_provenance``. The flag
    clears only when a NEW activated declaration supersedes the row (WS.2).
    """
    _enforce_company_visibility(current_user, site.company_id)
    report = apply_re_review(
        db, site=site, actor_id=getattr(current_user, "id", None)
    )

    try:
        _create_audit_log(
            request,
            db,
            "weather_device_mapping_re_evaluate",
            (
                f"Re-evaluated upstream drift on project/site {site.id}: "
                f"{report.newly_flagged_count} declaration(s) newly flagged for "
                f"re-review ({report.diverged_count} diverged of "
                f"{report.total_active} active)"
            ),
            is_success=True,
        )
    except Exception:  # noqa: BLE001
        logger.warning(
            "weather_device_mapping_re_evaluate_audit_failed site_id=%s", site.id
        )

    return WeatherUpstreamReEvaluateResponse.from_report(report)


@weather_router.get(
    "/sites/{site_id}/semantics-reconciliation",
    response_model=WeatherSemanticsReconciliationResponse,
    summary="Read-only governed weather-semantics reconciliation (9-state taxonomy)",
)
def get_weather_semantics_reconciliation(
    site: Annotated[Site, Depends(get_authorized_site)],
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
) -> WeatherSemanticsReconciliationResponse:
    """READ-ONLY 9-state weather-semantics reconciliation for a project/site.

    For every weather-source-capable device this discloses its position in the
    governed taxonomy — the declaration-axis states (from the live eligibility
    verdict); for undeclared semantics, an OBSERVED device (telemetry-mapped and/or
    producing readings) is the dedicated state 1
    (``observed_weather_device_no_governed_declaration``) while an unobserved device
    takes the source/profile overlay (states 7-9) — plus deduped site-level counts
    (states, blocking levels, eligible, needs-re-review).
    It performs NO writes/commits, never infers or converts semantics (declaring
    nothing leaves the value ``unknown``), never promotes or activates anything,
    and never touches the WeatherResolver, the expected formula, ingestion,
    rollups, the scheduler, baselines, ``expected_weather_provenance``, or O&M.
    Visible to any user authorized for the site (asset-view + company-visibility);
    reads never require admin.
    """
    _enforce_company_visibility(current_user, site.company_id)
    return build_site_semantics_reconciliation(db, site)
