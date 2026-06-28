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
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.crud.weather import (
    WeatherDeviceMappingCRUD,
    WeatherObservationBatchCRUD,
    WeatherProviderAccountCRUD,
    WeatherProviderCatalogCRUD,
    WeatherSourceCRUD,
    WeatherSourceProfileCRUD,
)
from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.authorization.module_based.telemetry import (
    telemetry_admin_required,
    user_has_telemetry_admin,
)
from app.helpers.authorization.project_access import (
    get_authorized_site,
    get_authorized_site_with_company_admin,
)
from app.helpers.solar_position import parse_lon_lat
from app.helpers.telemetry.audit import create_audit_log as _create_audit_log
from app.integrations.telemetry.credential_store import (
    CredentialStore,
    get_credential_store,
    is_credential_store_durable,
)
from app.integrations.weather.base import (
    WeatherCredentialError,
    WeatherProviderError,
)
from app.integrations.weather.registry import get_weather_adapter
from app.models.device import Device
from app.models.site import Site
from app.models.weather import (
    WeatherProviderAccount,
    WeatherProviderAccountStatus,
    WeatherProviderCatalog,
    WeatherProviderCredentialStatus,
    WeatherProviderSyncStatus,
    WeatherSourceProfileRole,
)
from app.schema.user import CurrentUserSchema
from app.schema.weather import (
    ExternalWeatherContextResponse,
    HistoricalImportPreviewRequest,
    HistoricalImportPreviewResponse,
    HistoricalImportRequest,
    HistoricalImportResponse,
    HistoricalProfileCreateRequest,
    ProviderImportPreviewResponse,
    ProviderImportRequest,
    ProviderImportResponse,
    ProviderPullBatchList,
    ProviderPullBatchResponse,
    WeatherDeclarationActivateRequest,
    WeatherDeclarationReReviewRequest,
    WeatherDeviceMappingDeclareRequest,
    WeatherDeviceMappingResponse,
    WeatherProfileActionRequest,
    WeatherProfileActionResponse,
    WeatherProfileResponse,
    WeatherProviderAccountCreate,
    WeatherProviderAccountList,
    WeatherProviderAccountResponse,
    WeatherProviderAccountUpdate,
    WeatherProviderEntry,
    WeatherProviderList,
    WeatherProviderTestResponse,
    WeatherReadinessResponse,
    WeatherSemanticsReconciliationResponse,
    WeatherUpstreamReEvaluateResponse,
)
from app.security.redaction import fingerprint
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
from app.services.weather.external_weather_context_service import (
    build_external_weather_context,
)
from app.services.weather.provider_import_service import (
    ProviderImportError,
    preview_provider_import,
    run_provider_import,
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
from app.settings import settings

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


# ===========================================================================
# Third-party weather provider framework (Phases A–D) — additive, CONTEXT-ONLY
# ===========================================================================
# External weather (e.g. Open-Meteo GHI/ambient) is pulled for CONTEXT and
# provenance only. These endpoints never mark an external source as physics-/
# expected-eligible, never transpose GHI->POA or convert ambient->cell, and
# never touch the WeatherResolver, the expected formula, ingestion, rollups, the
# scheduler, baselines, or reconciliation. The DB credential store from the
# telemetry stack is reused (no second secret system) with a weather-specific
# secret-name prefix so weather secrets stay distinguishable for audit / IAM.

WEATHER_SECRET_PREFIX = "ilios-weather"
_PROD_LIKE_ENV_NAMES = {"production", "prod", "staging", "stage", "live"}


def _is_production() -> bool:
    return (settings.environment_name or "").strip().lower() in _PROD_LIKE_ENV_NAMES


def _provider_utcnow() -> datetime:
    """Naive-UTC 'now' matching the weather storage convention."""
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _block_if_storage_not_durable(
    credential_store: CredentialStore, *, operation: str
) -> None:
    """Refuse to store/rotate/verify secrets on a non-durable backend in prod.

    Mirrors the telemetry v2 gate. Only fires when an operation would actually
    persist or read a secret whose durability matters; keyless flows never reach
    here. Dev/test (non-prod) is allowed to use the in-memory store.
    """
    if not _is_production():
        return
    if is_credential_store_durable(credential_store):
        return
    logger.warning(
        "weather_credential_op_blocked operation=%s reason=non_durable_backend",
        operation,
    )
    raise HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "Weather provider credential storage is not enabled for this "
        "environment. Contact an administrator.",
    )


def _require_catalog_provider(
    db: Session, provider_key: str, *, must_be_enabled: bool
) -> WeatherProviderCatalog:
    catalog = WeatherProviderCatalogCRUD(db).get_by_key(provider_key)
    if catalog is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            f"Weather provider '{provider_key}' is not in the catalog",
        )
    if must_be_enabled and not catalog.is_enabled:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Weather provider '{provider_key}' is disabled",
        )
    return catalog


def _provider_licensing_class(catalog: WeatherProviderCatalog) -> str:
    caps = catalog.capabilities_json or {}
    raw = catalog.licensing_class or caps.get("licensing_class") or ""
    return str(raw).strip().lower()


def _stored_credential_fingerprint(
    credential_store: CredentialStore, secret_name: Optional[str]
) -> Optional[str]:
    """Best-effort non-reversible fingerprint of a stored credential (admin-only).

    Never returns or logs the secret value. Returns ``None`` when there is no
    secret or the lookup fails.
    """
    if not secret_name:
        return None
    try:
        stored = credential_store.retrieve(secret_name) or {}
    except Exception:  # noqa: BLE001
        logger.warning("weather_credential_fingerprint_lookup_failed")
        return None
    first = next((value for value in stored.values() if value), None)
    return fingerprint(first) if first else None


@weather_router.get(
    "/providers",
    response_model=WeatherProviderList,
    summary="List weather providers with capabilities + licensing (read-only)",
)
def list_weather_providers(
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    include_disabled: bool = Query(
        False,
        description=(
            "Include seeded-but-disabled providers (for admins enabling a provider)."
        ),
    ),
) -> WeatherProviderList:
    """Read-only catalog of registered third-party weather providers.

    Every entry exposes ``expected_eligible_capable=False`` explicitly: external
    weather is CONTEXT-ONLY in Phases A–D and is never physics-/expected-eligible.
    Visible to any authenticated user; this is a descriptive catalog only.
    """
    del current_user  # any authenticated user may read the descriptive catalog
    rows = WeatherProviderCatalogCRUD(db).list_all(enabled_only=not include_disabled)
    return WeatherProviderList(
        items=[WeatherProviderEntry.from_model(row) for row in rows]
    )


@weather_router.get(
    "/companies/{company_id}/weather-provider-accounts",
    response_model=WeatherProviderAccountList,
    summary="List a company's weather provider accounts (read-only)",
)
def list_weather_provider_accounts(
    company_id: int,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    credential_store: Annotated[CredentialStore, Depends(get_credential_store)],
    include_archived: bool = Query(False),
) -> WeatherProviderAccountList:
    """List provider accounts for a company (company-visibility enforced).

    Credential fingerprints are surfaced only to telemetry admins; non-admins see
    the account metadata without any credential-derived field. The secret VALUE
    and ``secret_name`` are NEVER returned to anyone.
    """
    _enforce_company_visibility(current_user, company_id)
    is_admin = user_has_telemetry_admin(current_user)
    accounts = WeatherProviderAccountCRUD(db).list_for_company(
        company_id, include_archived=include_archived
    )
    items = [
        WeatherProviderAccountResponse.from_model(
            account,
            credential_fingerprint=(
                _stored_credential_fingerprint(credential_store, account.secret_name)
                if is_admin
                else None
            ),
        )
        for account in accounts
    ]
    return WeatherProviderAccountList(items=items)


@weather_router.post(
    "/companies/{company_id}/weather-provider-accounts",
    response_model=WeatherProviderAccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a weather provider account (durability + licensing gated)",
    dependencies=[Depends(telemetry_admin_required)],
)
def create_weather_provider_account(
    company_id: int,
    payload: WeatherProviderAccountCreate,
    request: Request,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    credential_store: Annotated[CredentialStore, Depends(get_credential_store)],
) -> WeatherProviderAccountResponse:
    """Create a per-company provider account.

    Keyless providers (e.g. Open-Meteo) need no credentials and are marked
    ``verified`` immediately. Keyed providers store credentials ONLY in the
    durable credential store (never the DB); a non-durable backend in production
    is refused. Commercial-licensed providers require ``licensing_acknowledged``.
    On any commit failure a freshly-minted secret is best-effort deleted so no
    orphan secret survives.
    """
    _enforce_company_visibility(current_user, company_id)
    catalog = _require_catalog_provider(db, payload.provider_key, must_be_enabled=True)

    requires_credentials = bool(catalog.config_schema)
    creds = dict(payload.credentials.fields) if payload.credentials else {}

    if (
        _provider_licensing_class(catalog) == "commercial"
        and not payload.licensing_acknowledged
    ):
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "This provider is commercially licensed; licensing must be "
            "acknowledged before creating an account.",
        )
    if requires_credentials and not creds:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"Weather provider '{payload.provider_key}' requires credentials.",
        )

    secret_name: Optional[str] = None
    if creds:
        _block_if_storage_not_durable(credential_store, operation="create_account")
        secret_name = credential_store.store(
            payload.external_account_label or payload.display_name,
            creds,
            company_id=company_id,
            name_prefix=WEATHER_SECRET_PREFIX,
        )

    acknowledged = bool(payload.licensing_acknowledged)
    account = WeatherProviderAccount(
        company_id=company_id,
        provider_key=payload.provider_key,
        display_name=payload.display_name,
        secret_name=secret_name,
        external_account_label=payload.external_account_label,
        status=WeatherProviderAccountStatus.active,
        credential_status=(
            WeatherProviderCredentialStatus.verified
            if not creds and not requires_credentials
            else WeatherProviderCredentialStatus.unverified
        ),
        last_sync_status=WeatherProviderSyncStatus.never,
        licensing_acknowledged_by=(
            getattr(current_user, "id", None) if acknowledged else None
        ),
        licensing_acknowledged_at=_provider_utcnow() if acknowledged else None,
        created_by_user_id=getattr(current_user, "id", None),
    )
    db.add(account)
    try:
        db.commit()
        db.refresh(account)
    except Exception:
        db.rollback()
        if secret_name:
            try:
                credential_store.delete(secret_name)
            except Exception:  # noqa: BLE001
                logger.warning("weather_orphan_secret_cleanup_failed")
        raise

    try:
        _create_audit_log(
            request,
            db,
            "weather_provider_account_create",
            (
                f"Created weather provider account {account.id} "
                f"({account.provider_key}) for company {company_id}"
            ),
            is_success=True,
        )
    except Exception:  # noqa: BLE001
        logger.warning("weather_provider_account_create_audit_failed")

    return WeatherProviderAccountResponse.from_model(
        account,
        credential_fingerprint=(
            fingerprint(next(iter(creds.values()), None)) if creds else None
        ),
    )


@weather_router.patch(
    "/companies/{company_id}/weather-provider-accounts/{account_id}",
    response_model=WeatherProviderAccountResponse,
    summary="Update / pause / archive / rotate a weather provider account",
    dependencies=[Depends(telemetry_admin_required)],
)
def update_weather_provider_account(
    company_id: int,
    account_id: int,
    payload: WeatherProviderAccountUpdate,
    request: Request,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    credential_store: Annotated[CredentialStore, Depends(get_credential_store)],
) -> WeatherProviderAccountResponse:
    """Mutate account metadata, lifecycle status, licensing, or rotate credentials.

    Archiving (``status=archived``) is a soft-delete (``is_archived``); accounts
    are never hard-deleted so batch provenance stays resolvable. Rotating
    credentials re-keys in place when possible (else mints a new weather secret)
    and resets ``credential_status`` to ``unverified``. A non-durable backend in
    production refuses credential rotation.
    """
    _enforce_company_visibility(current_user, company_id)
    account = WeatherProviderAccountCRUD(db).get_for_company(
        company_id=company_id, account_id=account_id
    )
    if account is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Weather provider account not found"
        )

    if payload.display_name is not None:
        account.display_name = payload.display_name
    if payload.external_account_label is not None:
        account.external_account_label = payload.external_account_label
    if payload.status is not None:
        account.status = payload.status
        if payload.status == WeatherProviderAccountStatus.archived:
            account.is_archived = True
            account.archived_at = _provider_utcnow()
        elif (
            account.is_archived
            and payload.status == WeatherProviderAccountStatus.active
        ):
            account.is_archived = False
            account.archived_at = None
    if payload.licensing_acknowledged is not None:
        if (
            payload.licensing_acknowledged
            and account.licensing_acknowledged_at is None
        ):
            account.licensing_acknowledged_at = _provider_utcnow()
            account.licensing_acknowledged_by = getattr(current_user, "id", None)
        elif not payload.licensing_acknowledged:
            account.licensing_acknowledged_at = None
            account.licensing_acknowledged_by = None

    rotated_fingerprint: Optional[str] = None
    minted_secret: Optional[str] = None
    if payload.credentials is not None and payload.credentials.fields:
        new_fields = dict(payload.credentials.fields)
        _block_if_storage_not_durable(
            credential_store, operation="rotate_credentials"
        )
        if account.secret_name and account.secret_name.startswith(
            WEATHER_SECRET_PREFIX
        ):
            credential_store.rotate(account.secret_name, new_fields)
        else:
            minted_secret = credential_store.store(
                account.external_account_label or account.display_name,
                new_fields,
                company_id=company_id,
                name_prefix=WEATHER_SECRET_PREFIX,
            )
            account.secret_name = minted_secret
        account.credential_status = WeatherProviderCredentialStatus.unverified
        rotated_fingerprint = fingerprint(next(iter(new_fields.values()), None))

    try:
        db.commit()
        db.refresh(account)
    except Exception:
        db.rollback()
        if minted_secret:
            try:
                credential_store.delete(minted_secret)
            except Exception:  # noqa: BLE001
                logger.warning("weather_orphan_secret_cleanup_failed")
        raise

    try:
        _create_audit_log(
            request,
            db,
            "weather_provider_account_update",
            f"Updated weather provider account {account.id} for company {company_id}",
            is_success=True,
        )
    except Exception:  # noqa: BLE001
        logger.warning("weather_provider_account_update_audit_failed")

    return WeatherProviderAccountResponse.from_model(
        account,
        credential_fingerprint=(
            rotated_fingerprint
            if rotated_fingerprint is not None
            else _stored_credential_fingerprint(credential_store, account.secret_name)
            if user_has_telemetry_admin(current_user)
            else None
        ),
    )


@weather_router.post(
    "/companies/{company_id}/weather-provider-accounts/{account_id}/test",
    response_model=WeatherProviderTestResponse,
    summary="Verify a weather provider account's stored credentials",
    dependencies=[Depends(telemetry_admin_required)],
)
def test_weather_provider_account(
    company_id: int,
    account_id: int,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    credential_store: Annotated[CredentialStore, Depends(get_credential_store)],
) -> WeatherProviderTestResponse:
    """Test reachability/credentials for an account via its provider adapter.

    Keyless providers report 'no credentials required' and verify trivially. A
    credential rejection flips ``credential_status`` to ``invalid``; a transport
    failure is reported WITHOUT changing the credential status (the credentials
    may still be valid). The secret value is never returned or logged.
    """
    _enforce_company_visibility(current_user, company_id)
    account = WeatherProviderAccountCRUD(db).get_for_company(
        company_id=company_id, account_id=account_id
    )
    if account is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND, "Weather provider account not found"
        )

    catalog = _require_catalog_provider(db, account.provider_key, must_be_enabled=True)
    if account.secret_name:
        _block_if_storage_not_durable(credential_store, operation="test_credentials")

    try:
        adapter = get_weather_adapter(db, account.provider_key, catalog=catalog)
    except WeatherProviderError as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            str(exc) or "Weather provider is disabled or unavailable",
        ) from exc

    try:
        creds = (
            credential_store.retrieve(account.secret_name)
            if account.secret_name
            else {}
        )
        result = adapter.test_credentials(creds)
    except WeatherCredentialError as exc:
        account.credential_status = WeatherProviderCredentialStatus.invalid
        account.last_error_at = _provider_utcnow()
        account.last_error_message = str(exc)[:1000]
        db.commit()
        return WeatherProviderTestResponse(
            success=False,
            message=str(exc) or "Credentials were rejected by the provider.",
            credential_status=WeatherProviderCredentialStatus.invalid.value,
        )
    except WeatherProviderError as exc:
        account.last_error_at = _provider_utcnow()
        account.last_error_message = str(exc)[:1000]
        prior_status = account.credential_status
        db.commit()
        return WeatherProviderTestResponse(
            success=False,
            message=str(exc) or "Weather provider is currently unavailable.",
            credential_status=(
                prior_status.value
                if hasattr(prior_status, "value")
                else str(prior_status)
            ),
        )

    if result.success:
        account.credential_status = WeatherProviderCredentialStatus.verified
        account.last_success_at = _provider_utcnow()
        account.last_error_message = None
    else:
        account.credential_status = WeatherProviderCredentialStatus.invalid
        account.last_error_at = _provider_utcnow()
        account.last_error_message = (result.message or "")[:1000] or None
    final_status = account.credential_status
    db.commit()

    return WeatherProviderTestResponse(
        success=result.success,
        message=result.message,
        credential_status=(
            final_status.value
            if hasattr(final_status, "value")
            else str(final_status)
        ),
    )


# ---------------------------------------------------------------------------
# Provider import (Phase C) — preview / run / batch history. CONTEXT-ONLY.
#
# A provider pull stores the provider's honest measurement semantics verbatim
# and converts NOTHING (no GHI->POA, no ambient->cell). It never marks an
# external source physics-/expected-eligible, never touches the WeatherResolver,
# the expected formula, ingestion, rollups, the scheduler, baselines, or
# reconciliation, and never fabricates a value. Writes require telemetry-admin +
# company-admin on the site; the batches feed is visible to any authorized user.
# ---------------------------------------------------------------------------
def _resolve_site_coordinates(site: Site) -> tuple[float, float]:
    """Resolve a site's (lat, lon). Raises 422 when no usable coordinates exist."""
    coords = parse_lon_lat(getattr(site, "lon_lat_url", None))
    if coords is None:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "This project/site has no valid coordinates configured; a weather "
            "provider pull cannot run without a latitude/longitude.",
        )
    return coords


def _resolve_provider_pull_context(
    db: Session,
    *,
    site: Site,
    request_body: ProviderImportRequest,
    credential_store: CredentialStore,
    read_credentials: bool,
) -> tuple[WeatherProviderCatalog, Optional[WeatherProviderAccount], dict[str, str]]:
    """Resolve catalog + (optional) account + credentials for a provider pull.

    Enforces catalog enablement, account ownership/lifecycle, commercial-licensing
    acknowledgement, and (only when a secret is actually read) the durable-storage
    gate. ``read_credentials=False`` (preview) validates everything but never
    touches the secret store. Returns ``(catalog, account_or_None, credentials)``.
    """
    catalog = _require_catalog_provider(
        db, request_body.provider_key, must_be_enabled=True
    )
    licensing_class = _provider_licensing_class(catalog)
    requires_credentials = bool(catalog.config_schema)

    account: Optional[WeatherProviderAccount] = None
    credentials: dict[str, str] = {}

    if request_body.account_id is not None:
        account = WeatherProviderAccountCRUD(db).get_for_company(
            company_id=site.company_id, account_id=request_body.account_id
        )
        if account is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND, "Weather provider account not found"
            )
        if account.provider_key != request_body.provider_key:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "Account does not belong to the requested provider.",
            )
        if (
            account.is_archived
            or account.status != WeatherProviderAccountStatus.active
        ):
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "Weather provider account is not active.",
            )
        if licensing_class == "commercial" and account.licensing_acknowledged_at is None:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "This provider is commercially licensed; licensing must be "
                "acknowledged on the account before pulling weather.",
            )
        if read_credentials and account.secret_name:
            _block_if_storage_not_durable(
                credential_store, operation="provider_import"
            )
            credentials = credential_store.retrieve(account.secret_name) or {}
    else:
        if requires_credentials:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                f"Weather provider '{request_body.provider_key}' requires an "
                "account with credentials.",
            )
        if licensing_class == "commercial":
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                "This provider is commercially licensed and requires an "
                "account with acknowledged licensing.",
            )

    return catalog, account, credentials


@weather_router.post(
    "/sites/{site_id}/provider-import/preview",
    response_model=ProviderImportPreviewResponse,
    summary="Preview a third-party weather provider pull (dry-run; writes nothing)",
    dependencies=[Depends(telemetry_admin_required)],
)
def preview_weather_provider_import(
    site_id: int,
    payload: ProviderImportRequest,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    credential_store: Annotated[CredentialStore, Depends(get_credential_store)],
    site: Annotated[Site, Depends(get_authorized_site_with_company_admin)],
) -> ProviderImportPreviewResponse:
    """Dry-run plan for a provider pull. Writes NOTHING and calls no provider.

    Surfaces the resolved metrics, chunk plan, gap-fill (so the operator sees the
    real metered cost), remaining rate-limit quota, and the explicit context-only
    verdict before any pull is committed.
    """
    _enforce_company_visibility(current_user, site.company_id)
    coordinates = _resolve_site_coordinates(site)
    catalog, _account, _creds = _resolve_provider_pull_context(
        db,
        site=site,
        request_body=payload,
        credential_store=credential_store,
        read_credentials=False,
    )
    try:
        adapter = get_weather_adapter(db, payload.provider_key, catalog=catalog)
    except WeatherProviderError as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            str(exc) or "Weather provider is disabled or unavailable",
        ) from exc
    try:
        return preview_provider_import(
            db,
            site=site,
            catalog=catalog,
            adapter=adapter,
            coordinates=coordinates,
            request=payload,
        )
    except ProviderImportError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc


@weather_router.post(
    "/sites/{site_id}/provider-import",
    response_model=ProviderImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Pull third-party weather for a site (context-only; gap-fill + idempotent)",
    dependencies=[Depends(telemetry_admin_required)],
)
def run_weather_provider_import(
    site_id: int,
    payload: ProviderImportRequest,
    request: Request,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    credential_store: Annotated[CredentialStore, Depends(get_credential_store)],
    site: Annotated[Site, Depends(get_authorized_site_with_company_admin)],
) -> ProviderImportResponse:
    """Pull a bounded window from a registered provider and persist it natively.

    CONTEXT-ONLY: stored observations carry honest semantics and are never
    converted or made expected-eligible. Gap-fill skips windows already stored and
    idempotent upsert means an overlapping re-pull inserts nothing. The pull is
    best-effort: per-chunk failures are recorded and the batch reports an honest
    succeeded/partial/failed status.
    """
    _enforce_company_visibility(current_user, site.company_id)
    coordinates = _resolve_site_coordinates(site)
    catalog, account, credentials = _resolve_provider_pull_context(
        db,
        site=site,
        request_body=payload,
        credential_store=credential_store,
        read_credentials=True,
    )
    try:
        adapter = get_weather_adapter(db, payload.provider_key, catalog=catalog)
    except WeatherProviderError as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            str(exc) or "Weather provider is disabled or unavailable",
        ) from exc

    try:
        result = run_provider_import(
            db,
            site=site,
            catalog=catalog,
            adapter=adapter,
            credentials=credentials,
            coordinates=coordinates,
            request=payload,
            account_id=account.id if account is not None else None,
            imported_by=getattr(current_user, "id", None),
        )
    except ProviderImportError as exc:
        raise HTTPException(exc.status_code, exc.detail) from exc

    try:
        _create_audit_log(
            request,
            db,
            "weather_provider_import",
            (
                f"Weather provider pull ({payload.provider_key}) for site "
                f"{site.id}: status={result.pull_status}, "
                f"rows_inserted={result.rows_inserted}, batch={result.batch_id}"
            ),
            is_success=result.pull_status != "failed",
        )
    except Exception:  # noqa: BLE001
        logger.warning("weather_provider_import_audit_failed")

    return result


@weather_router.get(
    "/sites/{site_id}/provider-import/batches",
    response_model=ProviderPullBatchList,
    summary="List a site's third-party provider pull provenance (read-only)",
)
def list_weather_provider_import_batches(
    site_id: int,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    site: Annotated[Site, Depends(get_authorized_site)],
    limit: int = Query(100, ge=1, le=500),
) -> ProviderPullBatchList:
    """Newest-first provider-pull provenance for a site (no secrets surfaced).

    Each row reports which account, the pull status, the window, row count, the
    provider api version, and a non-secret error summary. Visible to any user
    authorized for the site.
    """
    _enforce_company_visibility(current_user, site.company_id)
    batches = WeatherObservationBatchCRUD(db).list_provider_pulls_for_site(
        site.id, limit=limit
    )
    return ProviderPullBatchList(
        items=[ProviderPullBatchResponse.from_model(batch) for batch in batches]
    )


@weather_router.get(
    "/sites/{site_id}/external-weather-context",
    response_model=ExternalWeatherContextResponse,
    summary="Read-only external weather context for a site (not expected-eligible)",
)
def get_site_external_weather_context(
    site_id: int,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    site: Annotated[Site, Depends(get_authorized_site)],
) -> ExternalWeatherContextResponse:
    """Audit/provenance view of a site's imported external (modeled) weather.

    Pure read: it aggregates already-stored external sources, their per-metric
    coverage windows, and recent provider-pull provenance. It NEVER calls or
    alters ``compute_weather_readiness`` and carries an explicit context-only
    banner — external weather is never expected-eligible and is never converted
    to plane-of-array irradiance or cell temperature. Visible to any user
    authorized for the site.
    """
    _enforce_company_visibility(current_user, site.company_id)
    return build_external_weather_context(db, site=site)
