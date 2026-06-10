"""Telemetry v2 API router (Phase 1 introduce).

All endpoints live under ``/api/telemetry/v2`` and operate against the new
catalog / license / provider-account model. The legacy
``/api/telemetry/...`` routes continue to function unchanged.
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timedelta, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.db.session import SessionFactory, get_session
from app.helpers.authentication import get_current_user
from app.helpers.authorization import AuthorizedUser, SettingsPermissions
from app.helpers.authorization.module_based.telemetry import (
    telemetry_admin_required,
    user_has_telemetry_admin,
)
from app.helpers.authorization.project_access import (
    get_authorized_site_with_company_admin,
)
from app.integrations.telemetry import (
    CredentialError,
    DeviceListingAdapter,
    MappingError,
    NoData,
    ProviderUnavailable,
    RateLimited,
    get_adapter,
)
from app.integrations.telemetry.credential_store import (
    V2_SECRET_PREFIX,
    CredentialStore,
    get_credential_store,
    is_credential_store_durable,
)
from app.settings import settings
from app.models.telemetry import (
    CompanyDASProvider,
    CompanyProviderStatus,
    CredentialStatus,
    DASConnection,
    DASProvidersEnum,
    ExternalSiteSyncStatus,
    LastSyncStatus,
    ProviderAccountStatus,
    TelemetryDeviceMapping,
    TelemetryExternalDevice,
    TelemetryExternalSite,
    TelemetryProviderCatalog,
    TelemetrySiteMapping,
    TelemetrySyncStatus,
    TelemetrySyncTrigger,
)
from app.models.site import Site
from app.static import PermissionsActions
from app.schema.telemetry_v2 import (
    DeviceMappingBulkRequest,
    DeviceMappingBulkResponse,
    ExternalDeviceList,
    ExternalDeviceResponse,
    ExternalSiteList,
    ExternalSiteResponse,
    LicenseCreateRequest,
    LicensedProviderList,
    LicensedProviderResponse,
    ProviderAccountCreateRequest,
    ProviderAccountList,
    ProviderAccountResponse,
    ProviderAccountUpdateRequest,
    ProviderCatalogEntry,
    ProviderCatalogList,
    RefreshReadingsRequest,
    RefreshReadingsResponse,
    BackfillChunkResult,
    BackfillReadingsRequest,
    BackfillReadingsResponse,
    CompanySchedulerStatusList,
    SchedulerStateResponse,
    SchedulerUpdateRequest,
    SiteMappingCreateRequest,
    SiteMappingResponse,
    SyncDevicesResponse,
    SyncSitesResponse,
    TestAccountResponse,
)
from app.security.redaction import fingerprint
from app.schema.user import CurrentUserSchema
from app.crud.telemetry_native import TelemetrySchedulerStateCRUD
from app.services.telemetry.ingestion_service import (
    IngestionConfigError,
    run_site_refresh,
)
from app.services.telemetry.rollup_service import run_rollups_for_window
from app.services.telemetry.scheduler_runner import (
    ALLOWED_CADENCES,
    DEFAULT_CADENCE,
    floor_to_hour,
    run_ingestion_with_rollup,
)

logger = logging.getLogger(__name__)

telemetry_v2_router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _new_run_id() -> str:
    return f"run_{secrets.token_hex(8)}"


PROD_LIKE_ENV_NAMES = {"production", "prod", "staging", "stage", "live"}


def _is_production() -> bool:
    return (settings.environment_name or "").strip().lower() in PROD_LIKE_ENV_NAMES


def _block_if_storage_not_durable(
    credential_store: CredentialStore,
    *,
    operation: str,
) -> None:
    """Refuse credential writes/tests when the store would lose them.

    Policy:

    - In production with the in-memory backend: always block. Accepting
      credentials we cannot persist would be silent data loss.
    - In dev/non-production: allow. Local development uses in-memory by
      design; the boot warning is enough.

    Returns 503 (Service Unavailable) with a user-facing, secret-free
    message. The exception detail is what the frontend renders verbatim.
    """
    if not _is_production():
        return
    if is_credential_store_durable(credential_store):
        return
    logger.warning(
        "telemetry_v2_credential_op_blocked operation=%s reason=in_memory_backend",
        operation,
    )
    raise HTTPException(
        status.HTTP_503_SERVICE_UNAVAILABLE,
        "Telemetry credential storage is not enabled for production. "
        "Contact an administrator.",
    )


def _provider_key_to_enum(provider_key: str) -> DASProvidersEnum:
    try:
        return DASProvidersEnum[provider_key]
    except KeyError as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unknown provider_key '{provider_key}'",
        ) from exc


def _safe_stored_fingerprint(
    credential_store: CredentialStore, secret_token_name: Optional[str]
) -> Optional[str]:
    """Best-effort fingerprint of currently-stored credentials.

    Returns ``None`` when the secret cannot be retrieved or is empty.
    Errors are swallowed to keep list/detail reads cheap and resilient
    when the credential backend is transiently unavailable.
    """
    if not secret_token_name:
        return None
    try:
        stored = credential_store.retrieve(secret_token_name) or {}
    except Exception:  # noqa: BLE001
        logger.warning(
            "telemetry_v2_fingerprint_lookup_failed secret_name=%s",
            secret_token_name,
        )
        return None
    first_value = next((v for v in stored.values() if v), None)
    return fingerprint(first_value) if first_value else None


def _account_to_response(
    account: DASConnection,
    catalog: Optional[TelemetryProviderCatalog],
    credential_fingerprint: Optional[str] = None,
    external_site_count: int = 0,
    active_mapping_count: int = 0,
) -> ProviderAccountResponse:
    provider_key = catalog.provider_key if catalog else account.provider.name
    display_name = catalog.display_name if catalog else account.provider.value
    return ProviderAccountResponse(
        id=account.id,
        company_id=account.company_id,
        name=account.name,
        provider_key=provider_key,
        display_name=display_name,
        external_account_label=account.external_account_label,
        status=account.status,
        credential_status=account.credential_status,
        last_sync_status=account.last_sync_status,
        last_success_at=account.last_success_at,
        last_error_at=account.last_error_at,
        last_error_message=account.last_error_message,
        is_archived=account.is_archived,
        archived_at=account.archived_at,
        created_at=account.created_at,
        updated_at=account.updated_at,
        credentials_fingerprint=credential_fingerprint,
        external_site_count=external_site_count,
        active_mapping_count=active_mapping_count,
    )


def _count_external_sites(db: Session, account_id: int) -> int:
    """Return the count of external sites for an account.

    Tenant scoping is the caller's responsibility — this helper must only be
    invoked after the account has already been resolved to the caller's
    company. Returns 0 on any unexpected error so we never leak a partial
    or cross-tenant value into the response.
    """
    try:
        return (
            db.query(func.count(TelemetryExternalSite.id))
            .filter(TelemetryExternalSite.provider_account_id == account_id)
            .scalar()
            or 0
        )
    except Exception:  # noqa: BLE001
        logger.warning(
            "telemetry_v2_external_site_count_failed account_id=%s", account_id
        )
        return 0


def _count_active_mappings(db: Session, account_id: int) -> int:
    """Return the count of active site mappings for an account.

    Inactive (``is_active=False``) mappings are excluded by definition.
    Tenant scoping is the caller's responsibility. Device mappings live
    underneath site mappings and are not double-counted here.
    """
    try:
        return (
            db.query(func.count(TelemetrySiteMapping.id))
            .filter(
                TelemetrySiteMapping.provider_account_id == account_id,
                TelemetrySiteMapping.is_active.is_(True),
            )
            .scalar()
            or 0
        )
    except Exception:  # noqa: BLE001
        logger.warning(
            "telemetry_v2_active_mapping_count_failed account_id=%s", account_id
        )
        return 0


def _batch_external_site_counts(
    db: Session, account_ids: list[int]
) -> dict[int, int]:
    """Batch-count external sites for many accounts in one query."""
    if not account_ids:
        return {}
    try:
        rows = (
            db.query(
                TelemetryExternalSite.provider_account_id,
                func.count(TelemetryExternalSite.id),
            )
            .filter(TelemetryExternalSite.provider_account_id.in_(account_ids))
            .group_by(TelemetryExternalSite.provider_account_id)
            .all()
        )
        return {pid: int(c) for pid, c in rows}
    except Exception:  # noqa: BLE001
        logger.warning(
            "telemetry_v2_external_site_count_batch_failed n=%s", len(account_ids)
        )
        return {}


def _batch_active_mapping_counts(
    db: Session, account_ids: list[int]
) -> dict[int, int]:
    """Batch-count active site mappings for many accounts in one query."""
    if not account_ids:
        return {}
    try:
        rows = (
            db.query(
                TelemetrySiteMapping.provider_account_id,
                func.count(TelemetrySiteMapping.id),
            )
            .filter(
                TelemetrySiteMapping.provider_account_id.in_(account_ids),
                TelemetrySiteMapping.is_active.is_(True),
            )
            .group_by(TelemetrySiteMapping.provider_account_id)
            .all()
        )
        return {pid: int(c) for pid, c in rows}
    except Exception:  # noqa: BLE001
        logger.warning(
            "telemetry_v2_active_mapping_count_batch_failed n=%s", len(account_ids)
        )
        return {}


def _require_account_for_company(
    db: Session, company_id: int, account_id: int
) -> tuple[DASConnection, Optional[TelemetryProviderCatalog]]:
    """Fetch a provider account scoped to ``company_id``.

    Cross-tenant requests return 404 (not 403) to avoid leaking the existence
    of accounts outside the caller's company.
    """
    account = (
        db.query(DASConnection)
        .filter(DASConnection.id == account_id, DASConnection.company_id == company_id)
        .first()
    )
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Provider account not found")
    catalog = _resolve_catalog_for_account(db, account)
    return account, catalog


def _require_account(
    db: Session, account_id: int, current_user: CurrentUserSchema
) -> tuple[DASConnection, Optional[TelemetryProviderCatalog]]:
    """Fetch a provider account scoped to companies the user can access."""
    account = db.get(DASConnection, account_id)
    if account is None or account.is_archived:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Provider account not found")

    if not getattr(current_user, "has_platform_bypass", False):
        accessible = set(getattr(current_user, "get_limited_companies_ids", lambda: [])() or [])
        if accessible and account.company_id not in accessible:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Provider account not found")

    return account, _resolve_catalog_for_account(db, account)


def _resolve_catalog_for_account(
    db: Session, account: DASConnection
) -> Optional[TelemetryProviderCatalog]:
    if account.company_provider_id:
        license_row = db.get(CompanyDASProvider, account.company_provider_id)
        if license_row and license_row.catalog_id:
            return db.get(TelemetryProviderCatalog, license_row.catalog_id)
    return (
        db.query(TelemetryProviderCatalog)
        .filter(TelemetryProviderCatalog.provider_key == account.provider.name)
        .first()
    )


def _ensure_license(
    db: Session, company_id: int, provider_key: str
) -> tuple[CompanyDASProvider, TelemetryProviderCatalog]:
    catalog = (
        db.query(TelemetryProviderCatalog)
        .filter(TelemetryProviderCatalog.provider_key == provider_key)
        .first()
    )
    if catalog is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Provider '{provider_key}' is not in the catalog")
    if not catalog.is_enabled:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Provider '{provider_key}' is disabled")

    license_row = (
        db.query(CompanyDASProvider)
        .filter(
            CompanyDASProvider.company_id == company_id,
            CompanyDASProvider.catalog_id == catalog.id,
        )
        .first()
    )
    if license_row is None:
        # Backwards compat: license may exist via legacy enum column only.
        provider_enum = _provider_key_to_enum(provider_key)
        license_row = (
            db.query(CompanyDASProvider)
            .filter(
                CompanyDASProvider.company_id == company_id,
                CompanyDASProvider.provider == provider_enum,
            )
            .first()
        )
    if license_row is None:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"Company {company_id} is not licensed for provider '{provider_key}'",
        )
    if license_row.status == CompanyProviderStatus.suspended:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            f"License for provider '{provider_key}' is suspended",
        )
    return license_row, catalog


# ---------------------------------------------------------------------------
# Catalog
# ---------------------------------------------------------------------------


@telemetry_v2_router.get(
    "/v2/catalog",
    response_model=ProviderCatalogList,
    summary="List telemetry provider catalog (v2)",
)
def list_catalog(
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],  # noqa: ARG001
) -> ProviderCatalogList:
    rows = (
        db.query(TelemetryProviderCatalog)
        .order_by(TelemetryProviderCatalog.display_name)
        .all()
    )
    return ProviderCatalogList(
        items=[ProviderCatalogEntry.model_validate(row) for row in rows]
    )


# ---------------------------------------------------------------------------
# Licenses (company ↔ catalog)
# ---------------------------------------------------------------------------


@telemetry_v2_router.get(
    "/v2/companies/{company_id}/licensed-providers",
    response_model=LicensedProviderList,
    summary="List licensed providers for a company",
)
def list_licensed_providers(
    company_id: int,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
) -> LicensedProviderList:
    _enforce_company_visibility(current_user, company_id)
    rows = (
        db.query(CompanyDASProvider)
        .options(joinedload(CompanyDASProvider.catalog))
        .filter(CompanyDASProvider.company_id == company_id)
        .order_by(CompanyDASProvider.id)
        .all()
    )
    counts = dict(
        db.query(DASConnection.company_provider_id, func.count(DASConnection.id))
        .filter(
            DASConnection.company_id == company_id,
            DASConnection.is_archived.is_(False),
        )
        .group_by(DASConnection.company_provider_id)
        .all()
    )
    items: list[LicensedProviderResponse] = []
    for row in rows:
        catalog = row.catalog
        provider_key = catalog.provider_key if catalog else row.provider.name
        display_name = catalog.display_name if catalog else row.provider.value
        items.append(
            LicensedProviderResponse(
                id=row.id,
                company_id=row.company_id,
                provider_key=provider_key,
                display_name=display_name,
                status=row.status,
                notes=row.notes,
                account_count=counts.get(row.id, 0),
                created_at=row.created_at,
                updated_at=row.updated_at,
            )
        )
    return LicensedProviderList(items=items)


@telemetry_v2_router.post(
    "/v2/companies/{company_id}/licensed-providers",
    response_model=LicensedProviderResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Grant a provider license to a company",
    dependencies=[Depends(telemetry_admin_required)],
)
def create_license(
    company_id: int,
    payload: LicenseCreateRequest,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
) -> LicensedProviderResponse:
    _enforce_company_visibility(current_user, company_id)
    catalog = (
        db.query(TelemetryProviderCatalog)
        .filter(TelemetryProviderCatalog.provider_key == payload.provider_key)
        .first()
    )
    if catalog is None or not catalog.is_enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown or disabled provider")

    existing = (
        db.query(CompanyDASProvider)
        .filter(
            CompanyDASProvider.company_id == company_id,
            CompanyDASProvider.catalog_id == catalog.id,
        )
        .first()
    )
    if existing:
        existing.status = CompanyProviderStatus.active
        if payload.notes is not None:
            existing.notes = payload.notes
        db.commit()
        db.refresh(existing)
        license_row = existing
    else:
        license_row = CompanyDASProvider(
            company_id=company_id,
            provider=_provider_key_to_enum(payload.provider_key),
            catalog_id=catalog.id,
            status=CompanyProviderStatus.active,
            notes=payload.notes,
        )
        db.add(license_row)
        db.commit()
        db.refresh(license_row)

    return LicensedProviderResponse(
        id=license_row.id,
        company_id=company_id,
        provider_key=catalog.provider_key,
        display_name=catalog.display_name,
        status=license_row.status,
        notes=license_row.notes,
        account_count=0,
        created_at=license_row.created_at,
        updated_at=license_row.updated_at,
    )


@telemetry_v2_router.delete(
    "/v2/companies/{company_id}/licensed-providers/{license_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Revoke a provider license (refused if accounts exist)",
    dependencies=[Depends(telemetry_admin_required)],
)
def delete_license(
    company_id: int,
    license_id: int,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
) -> None:
    _enforce_company_visibility(current_user, company_id)
    license_row = (
        db.query(CompanyDASProvider)
        .filter(
            CompanyDASProvider.id == license_id,
            CompanyDASProvider.company_id == company_id,
        )
        .first()
    )
    if license_row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "License not found")

    accounts = (
        db.query(func.count(DASConnection.id))
        .filter(DASConnection.company_provider_id == license_row.id)
        .scalar()
    )
    if accounts and accounts > 0:
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            f"Cannot revoke license while {accounts} provider account(s) reference it",
        )

    db.delete(license_row)
    db.commit()


# ---------------------------------------------------------------------------
# Provider accounts
# ---------------------------------------------------------------------------


def _enforce_company_visibility(current_user: CurrentUserSchema, company_id: int) -> None:
    if getattr(current_user, "has_platform_bypass", False):
        return
    accessible = set(getattr(current_user, "get_limited_companies_ids", lambda: [])() or [])
    if accessible and company_id not in accessible:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Company not found")


@telemetry_v2_router.get(
    "/v2/companies/{company_id}/provider-accounts",
    response_model=ProviderAccountList,
    summary="List provider accounts for a company",
)
def list_provider_accounts(
    company_id: int,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    credential_store: Annotated[CredentialStore, Depends(get_credential_store)],
    include_archived: bool = False,
) -> ProviderAccountList:
    _enforce_company_visibility(current_user, company_id)
    query = db.query(DASConnection).filter(DASConnection.company_id == company_id)
    if not include_archived:
        query = query.filter(DASConnection.is_archived.is_(False))
    rows = query.order_by(DASConnection.id).all()

    by_id: dict[int, TelemetryProviderCatalog] = {}
    for row in rows:
        catalog = _resolve_catalog_for_account(db, row)
        if catalog is not None:
            by_id[row.id] = catalog

    account_ids = [row.id for row in rows]
    site_counts = _batch_external_site_counts(db, account_ids)
    mapping_counts = _batch_active_mapping_counts(db, account_ids)

    is_admin = user_has_telemetry_admin(current_user)
    return ProviderAccountList(
        items=[
            _account_to_response(
                row,
                by_id.get(row.id),
                credential_fingerprint=(
                    _safe_stored_fingerprint(credential_store, row.secret_token_name)
                    if is_admin
                    else None
                ),
                external_site_count=site_counts.get(row.id, 0),
                active_mapping_count=mapping_counts.get(row.id, 0),
            )
            for row in rows
        ]
    )


@telemetry_v2_router.post(
    "/v2/companies/{company_id}/provider-accounts",
    response_model=ProviderAccountResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a provider account",
    dependencies=[Depends(telemetry_admin_required)],
)
def create_provider_account(
    company_id: int,
    payload: ProviderAccountCreateRequest,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    credential_store: Annotated[CredentialStore, Depends(get_credential_store)],
) -> ProviderAccountResponse:
    _enforce_company_visibility(current_user, company_id)
    _block_if_storage_not_durable(credential_store, operation="create_account")
    license_row, catalog = _ensure_license(db, company_id, payload.provider_key)

    secret_name = credential_store.store(
        payload.external_account_label or payload.name,
        payload.credentials.fields,
        company_id=company_id,
    )
    logger.info(
        "telemetry_v2_account_created company_id=%s actor=%s secret_name=%s",
        company_id,
        getattr(current_user, "id", None),
        secret_name,
    )

    account = DASConnection(
        company_id=company_id,
        name=payload.name,
        provider=_provider_key_to_enum(payload.provider_key),
        secret_token_name=secret_name,
        owner_type="company",
        company_provider_id=license_row.id,
        status=ProviderAccountStatus.active,
        credential_status=CredentialStatus.unverified,
        last_sync_status=LastSyncStatus.never,
        external_account_label=payload.external_account_label,
        created_by_user_id=getattr(current_user, "id", None),
    )
    db.add(account)
    try:
        db.commit()
        db.refresh(account)
    except Exception:
        # Compensating cleanup: the secret was already written to durable
        # storage but the DB row could not be persisted. Without this the
        # secret would be orphaned. Best-effort delete; surface the
        # original DB error to the caller.
        db.rollback()
        try:
            credential_store.delete(secret_name)
        except Exception:  # noqa: BLE001
            logger.warning(
                "telemetry_v2_orphan_secret_cleanup_failed secret_name=%s",
                secret_name,
            )
        raise

    return _account_to_response(
        account,
        catalog,
        credential_fingerprint=fingerprint(
            next(iter(payload.credentials.fields.values()), None)
        ),
        external_site_count=_count_external_sites(db, account.id),
        active_mapping_count=_count_active_mappings(db, account.id),
    )


@telemetry_v2_router.get(
    "/v2/companies/{company_id}/provider-accounts/{account_id}",
    response_model=ProviderAccountResponse,
    summary="Get a single provider account",
)
def get_provider_account(
    company_id: int,
    account_id: int,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    credential_store: Annotated[CredentialStore, Depends(get_credential_store)],
) -> ProviderAccountResponse:
    _enforce_company_visibility(current_user, company_id)
    account, catalog = _require_account_for_company(db, company_id, account_id)
    credential_fingerprint = (
        _safe_stored_fingerprint(credential_store, account.secret_token_name)
        if user_has_telemetry_admin(current_user)
        else None
    )
    return _account_to_response(
        account,
        catalog,
        credential_fingerprint=credential_fingerprint,
        external_site_count=_count_external_sites(db, account.id),
        active_mapping_count=_count_active_mappings(db, account.id),
    )


@telemetry_v2_router.patch(
    "/v2/companies/{company_id}/provider-accounts/{account_id}",
    response_model=ProviderAccountResponse,
    summary="Update a provider account (optionally rotate credentials)",
    dependencies=[Depends(telemetry_admin_required)],
)
def update_provider_account(
    company_id: int,
    account_id: int,
    payload: ProviderAccountUpdateRequest,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    credential_store: Annotated[CredentialStore, Depends(get_credential_store)],
) -> ProviderAccountResponse:
    _enforce_company_visibility(current_user, company_id)
    account, catalog = _require_account_for_company(db, company_id, account_id)
    rotated_fp: Optional[str] = None

    if payload.name is not None:
        account.name = payload.name
    if payload.external_account_label is not None:
        account.external_account_label = payload.external_account_label
    if payload.status is not None:
        account.status = payload.status
        if payload.status == ProviderAccountStatus.archived:
            account.is_archived = True
            account.archived_at = _utcnow()

    minted_new_secret: Optional[str] = None
    if payload.credentials is not None and payload.credentials.fields:
        # Block silent loss: only gate when we are actually about to write
        # credentials. Renaming/archiving is allowed even on a non-durable
        # store so operators can still clean up.
        _block_if_storage_not_durable(credential_store, operation="rotate_credentials")
        # Rotate in place: same secret resource, new version. Old
        # versions stay accessible for audit / rollback. We never
        # destroy the previous credential set.
        if account.secret_token_name and account.secret_token_name.startswith(
            V2_SECRET_PREFIX
        ):
            # NOTE: rotate-in-place adds a new version to the existing
            # secret. If the subsequent DB commit fails we cannot undo
            # the version (and shouldn't — versions are the audit
            # trail). The old version remains accessible by version
            # number for rollback. credential_status will be re-derived
            # by the next /test call, so the metadata heals itself.
            credential_store.rotate(
                account.secret_token_name, payload.credentials.fields
            )
            new_secret = account.secret_token_name
        else:
            # Account was created before durable storage existed (or
            # under the placeholder backend). Mint a fresh durable
            # secret instead of mutating the legacy reference.
            new_secret = credential_store.store(
                account.external_account_label or account.name,
                payload.credentials.fields,
                company_id=company_id,
            )
            minted_new_secret = new_secret
        account.secret_token_name = new_secret
        account.credential_status = CredentialStatus.unverified
        rotated_fp = fingerprint(next(iter(payload.credentials.fields.values()), None))
        logger.info(
            "telemetry_v2_account_credentials_rotated account_id=%s actor=%s secret_name=%s",
            account_id,
            getattr(current_user, "id", None),
            new_secret,
        )

    try:
        db.commit()
        db.refresh(account)
    except Exception:
        db.rollback()
        # Compensating cleanup applies only to the mint-new fallback;
        # rotated-in-place secrets are versioned and intentionally kept.
        if minted_new_secret is not None:
            try:
                credential_store.delete(minted_new_secret)
            except Exception:  # noqa: BLE001
                logger.warning(
                    "telemetry_v2_orphan_secret_cleanup_failed secret_name=%s",
                    minted_new_secret,
                )
        raise
    return _account_to_response(
        account,
        catalog,
        credential_fingerprint=rotated_fp,
        external_site_count=_count_external_sites(db, account.id),
        active_mapping_count=_count_active_mappings(db, account.id),
    )


@telemetry_v2_router.delete(
    "/v2/companies/{company_id}/provider-accounts/{account_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    summary="Archive a provider account (soft delete)",
    dependencies=[Depends(telemetry_admin_required)],
)
def delete_provider_account(
    company_id: int,
    account_id: int,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    credential_store: Annotated[CredentialStore, Depends(get_credential_store)],  # noqa: ARG001
) -> None:
    _enforce_company_visibility(current_user, company_id)
    account, _ = _require_account_for_company(db, company_id, account_id)
    account.is_archived = True
    account.status = ProviderAccountStatus.archived
    account.archived_at = _utcnow()
    db.commit()
    # Safe deletion policy: archive is reversible. The underlying secret
    # is intentionally retained so that restoring the account brings the
    # credentials back without operator intervention. Permanent secret
    # purge (if ever introduced) must be a separate, explicit endpoint.
    logger.info(
        "telemetry_v2_account_archived account_id=%s actor=%s secret_name=%s (secret retained)",
        account_id,
        getattr(current_user, "id", None),
        account.secret_token_name,
    )


# ---------------------------------------------------------------------------
# Test + sync sites
# ---------------------------------------------------------------------------


@telemetry_v2_router.post(
    "/v2/provider-accounts/{account_id}/test",
    response_model=TestAccountResponse,
    summary="Test stored credentials for a provider account",
    dependencies=[Depends(telemetry_admin_required)],
)
def test_provider_account(
    account_id: int,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    credential_store: Annotated[CredentialStore, Depends(get_credential_store)],
) -> TestAccountResponse:
    account, catalog = _require_account(db, account_id, current_user)
    if catalog is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Provider account has no catalog mapping")
    # Block test if we're on the in-memory backend in production: we'd be
    # validating credentials that may have been silently lost on the last
    # restart, producing a misleading red/green result.
    _block_if_storage_not_durable(credential_store, operation="test_credentials")

    creds = credential_store.retrieve(account.secret_token_name)
    adapter = get_adapter(db, catalog.provider_key, catalog=catalog)
    try:
        result = adapter.test_credentials(creds)
    except CredentialError as exc:
        account.credential_status = CredentialStatus.invalid
        account.last_error_at = _utcnow()
        account.last_error_message = str(exc)
        db.commit()
        return TestAccountResponse(
            success=False,
            message=str(exc) or "Invalid credentials",
            credential_status=CredentialStatus.invalid,
        )

    if result.success:
        account.credential_status = CredentialStatus.verified
        account.last_success_at = _utcnow()
        account.last_error_message = None
    else:
        account.credential_status = CredentialStatus.invalid
        account.last_error_at = _utcnow()
        account.last_error_message = result.message
    db.commit()
    return TestAccountResponse(
        success=result.success,
        message=result.message,
        credential_status=account.credential_status,
        available_sites_count=result.available_sites_count,
    )


@telemetry_v2_router.post(
    "/v2/provider-accounts/{account_id}/sync-sites",
    response_model=SyncSitesResponse,
    summary="Pull external site list and update provenance",
    dependencies=[Depends(telemetry_admin_required)],
)
def sync_provider_account_sites(
    account_id: int,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    credential_store: Annotated[CredentialStore, Depends(get_credential_store)],
) -> SyncSitesResponse:
    account, catalog = _require_account(db, account_id, current_user)
    if catalog is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Provider account has no catalog mapping")
    # Same rationale as test_provider_account: sync needs to retrieve and
    # re-present credentials to the provider. On a non-durable backend in
    # production those credentials may already have been silently lost.
    _block_if_storage_not_durable(credential_store, operation="sync_sites")

    creds = credential_store.retrieve(account.secret_token_name)
    adapter = get_adapter(db, catalog.provider_key, catalog=catalog)
    run_id = _new_run_id()
    now = _utcnow()

    try:
        records = list(adapter.list_sites(creds))
    except CredentialError as exc:
        account.credential_status = CredentialStatus.invalid
        account.last_sync_status = LastSyncStatus.failed
        account.last_error_at = now
        account.last_error_message = str(exc)
        db.commit()
        return SyncSitesResponse(
            sync_run_id=run_id,
            last_sync_status=LastSyncStatus.failed,
            seen_count=0,
            new_count=0,
            missing_count=0,
            error=str(exc) or "Invalid credentials",
        )
    except (NoData, ProviderUnavailable, RateLimited, MappingError) as exc:
        account.last_sync_status = LastSyncStatus.failed
        account.last_error_at = now
        account.last_error_message = str(exc)
        db.commit()
        return SyncSitesResponse(
            sync_run_id=run_id,
            last_sync_status=LastSyncStatus.failed,
            seen_count=0,
            new_count=0,
            missing_count=0,
            error=str(exc) or "Provider error",
        )

    existing = {
        row.external_site_id: row
        for row in db.query(TelemetryExternalSite)
        .filter(TelemetryExternalSite.provider_account_id == account.id)
        .all()
    }
    seen_ids: set[str] = set()
    new_count = 0
    for record in records:
        ext_id = str(record.external_site_id)
        seen_ids.add(ext_id)
        if ext_id in existing:
            row = existing[ext_id]
            row.external_site_name = record.external_site_name or row.external_site_name
            row.raw_metadata = record.raw_metadata or row.raw_metadata
            row.last_seen_at = now
            row.last_synced_at = now
            row.last_sync_run_id = run_id
            row.sync_status = ExternalSiteSyncStatus.seen
            row.last_sync_error = None
        else:
            db.add(
                TelemetryExternalSite(
                    provider_account_id=account.id,
                    external_site_id=ext_id,
                    external_site_name=record.external_site_name,
                    raw_metadata=record.raw_metadata or None,
                    first_seen_at=now,
                    last_seen_at=now,
                    last_synced_at=now,
                    last_sync_run_id=run_id,
                    sync_status=ExternalSiteSyncStatus.seen,
                )
            )
            new_count += 1

    missing_count = 0
    for ext_id, row in existing.items():
        if ext_id not in seen_ids:
            row.sync_status = ExternalSiteSyncStatus.missing
            row.last_synced_at = now
            row.last_sync_run_id = run_id
            missing_count += 1

    if records:
        account.credential_status = CredentialStatus.verified
        account.last_success_at = now
        account.last_sync_status = (
            LastSyncStatus.partial if missing_count else LastSyncStatus.success
        )
        account.last_error_message = None
    else:
        account.last_sync_status = LastSyncStatus.partial
    db.commit()

    return SyncSitesResponse(
        sync_run_id=run_id,
        last_sync_status=account.last_sync_status,
        seen_count=len(seen_ids),
        new_count=new_count,
        missing_count=missing_count,
    )


@telemetry_v2_router.get(
    "/v2/companies/{company_id}/provider-accounts/credential-audit",
    summary=(
        "List provider accounts whose stored credentials are missing "
        "(typically because they were entered before a durable backend was "
        "configured and were lost on restart)."
    ),
    dependencies=[Depends(telemetry_admin_required)],
)
def credential_audit(
    company_id: int,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    credential_store: Annotated[CredentialStore, Depends(get_credential_store)],
) -> dict:
    """Diagnose provider accounts that need credential re-entry.

    For every non-archived account on ``company_id``, attempts to read the
    credential payload from the active store. Empty payloads mean either:

    - the account was created under the in-memory backend and the worker
      has restarted since (credentials lost), or
    - the secret resource has been manually deleted in GCP.

    No credential values are returned; only the account id, name, and a
    boolean ``has_stored_credentials`` flag.

    The endpoint is read-only. Operators clear the bad state by clicking
    ``Update Credentials`` in the UI (or PATCHing the account with a new
    ``credentials.fields`` payload), which mints a fresh secret on the
    durable backend.
    """
    _enforce_company_visibility(current_user, company_id)
    rows = (
        db.query(DASConnection)
        .filter(
            DASConnection.company_id == company_id,
            DASConnection.is_archived.is_(False),
        )
        .order_by(DASConnection.id)
        .all()
    )
    durable = is_credential_store_durable(credential_store)
    items: list[dict] = []
    missing_count = 0
    for row in rows:
        try:
            stored = credential_store.retrieve(row.secret_token_name)
        except Exception:  # noqa: BLE001
            stored = {}
        has_creds = bool(stored)
        if not has_creds:
            missing_count += 1
        items.append(
            {
                "id": row.id,
                "name": row.name,
                "credential_status": row.credential_status.value
                if row.credential_status
                else None,
                "has_stored_credentials": has_creds,
                "needs_reentry": not has_creds,
            }
        )
    return {
        "company_id": company_id,
        "credential_backend_durable": durable,
        "missing_credentials_count": missing_count,
        "items": items,
    }


@telemetry_v2_router.get(
    "/v2/provider-accounts/{account_id}/external-sites",
    response_model=ExternalSiteList,
    summary="List external sites for a provider account",
)
def list_external_sites(
    account_id: int,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
) -> ExternalSiteList:
    account, _ = _require_account(db, account_id, current_user)
    rows = (
        db.query(TelemetryExternalSite)
        .filter(TelemetryExternalSite.provider_account_id == account.id)
        .order_by(TelemetryExternalSite.external_site_name.asc().nullslast(),
                  TelemetryExternalSite.external_site_id.asc())
        .all()
    )
    return ExternalSiteList(
        items=[ExternalSiteResponse.model_validate(row) for row in rows],
        last_sync_run_id=rows[0].last_sync_run_id if rows else None,
        last_sync_status=account.last_sync_status,
        last_success_at=account.last_success_at,
    )


# ---------------------------------------------------------------------------
# Site mapping (project <-> external site) -- DB-only, no legacy GCP/Firestore
# ---------------------------------------------------------------------------


@telemetry_v2_router.put(
    "/v2/sites/{site_id}/mapping",
    response_model=SiteMappingResponse,
    summary="Create or update a project/site telemetry mapping (V2, DB-only)",
    dependencies=[Depends(AuthorizedUser(SettingsPermissions(PermissionsActions.edit)))],
)
def upsert_site_mapping(
    payload: SiteMappingCreateRequest,
    request: Request,
    site: Annotated[Site, Depends(get_authorized_site_with_company_admin)],
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
) -> SiteMappingResponse:
    """Persist a project/site -> external-site mapping directly in iliOS.

    This is the V2 (DB-backed) save path. It deliberately does **not** call the
    external provider and does **not** touch any GCP / Firestore pipeline:

    - The external site must already exist in the iliOS sync cache
      (``telemetry_external_sites``); the display name is read from there
      instead of making a live provider call.
    - GCP is only ever used for durable credential storage (Secret Manager),
      never as part of this mapping save.
    - The write is additive and scoped to ``{company_id, provider_account_id,
      external_site_id, site_id, created_by, timestamps}``. Existing mappings
      are upserted in place; nothing is wiped on any downstream/provider error,
      because no such call is made here.
    """
    # 1. Resolve + authorize the provider account (scoped to the caller's companies).
    account, _ = _require_account(db, payload.provider_account_id, current_user)

    # 2. The provider account must belong to the same company as the project/site.
    if account.company_id != site.company_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Provider account does not belong to this project's company.",
        )

    # 3. The external site must already be in the iliOS cache. We never make a
    #    live provider call here; if it is missing the user must sync first.
    external = (
        db.query(TelemetryExternalSite)
        .filter(
            TelemetryExternalSite.provider_account_id == account.id,
            TelemetryExternalSite.external_site_id == payload.external_site_id,
        )
        .first()
    )
    if external is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Selected site is not in the synced site cache for this connection. "
            "Sync sites for the connection and try again.",
        )

    site_name = external.external_site_name or external.external_site_id
    mapping_role = (payload.mapping_role or "primary").strip() or "primary"
    now = _utcnow()

    # 4. Upsert the mapping. ``site_id`` is unique, so there is at most one row.
    mapping = (
        db.query(TelemetrySiteMapping)
        .filter(TelemetrySiteMapping.site_id == site.id)
        .first()
    )
    created = mapping is None
    if mapping is None:
        mapping = TelemetrySiteMapping(
            site_id=site.id,
            company_id=site.company_id,
            connection_id=account.id,
            provider_account_id=account.id,
            telemetry_site_id=external.external_site_id,
            telemetry_site_name=site_name,
            mapping_role=mapping_role,
            is_active=True,
            created_by_user_id=getattr(current_user, "id", None),
        )
        db.add(mapping)
    else:
        mapping.company_id = site.company_id
        mapping.connection_id = account.id
        mapping.provider_account_id = account.id
        mapping.telemetry_site_id = external.external_site_id
        mapping.telemetry_site_name = site_name
        mapping.mapping_role = mapping_role
        mapping.is_active = True
        mapping.updated_at = now

    db.commit()
    db.refresh(mapping)

    logger.info(
        "telemetry_v2_site_mapping_saved site_id=%s account_id=%s external_site_id=%s created=%s",
        site.id,
        account.id,
        external.external_site_id,
        created,
    )

    # Best-effort audit trail; never blocks or rolls back the saved mapping.
    try:
        from app.routers.telemetry.telemetry import _create_audit_log

        _create_audit_log(
            request,
            db,
            "telemetry_v2_site_mapping_saved" if created else "telemetry_v2_site_mapping_updated",
            (
                f"Mapped project/site {site.id} to external site "
                f"{external.external_site_id} via provider account {account.id}"
            ),
        )
    except Exception:  # noqa: BLE001
        logger.warning("telemetry_v2_site_mapping_audit_failed site_id=%s", site.id)

    return SiteMappingResponse.model_validate(mapping)


# ---------------------------------------------------------------------------
# External devices (per-site hardware sync cache) -- DB-backed, V2
# ---------------------------------------------------------------------------


def _require_external_site(
    db: Session, account: DASConnection, external_site_id: str
) -> TelemetryExternalSite:
    """Return the synced external-site row or raise 404.

    Device sync/listing is always scoped to an already-synced site; if the site
    has never been synced for this account we 404 rather than make a live call.
    """
    row = (
        db.query(TelemetryExternalSite)
        .filter(
            TelemetryExternalSite.provider_account_id == account.id,
            TelemetryExternalSite.external_site_id == external_site_id,
        )
        .first()
    )
    if row is None:
        raise HTTPException(
            status.HTTP_404_NOT_FOUND,
            "Selected site is not in the synced site cache for this connection. "
            "Sync sites for the connection and try again.",
        )
    return row


@telemetry_v2_router.get(
    "/v2/provider-accounts/{account_id}/external-sites/{external_site_id}/devices",
    response_model=ExternalDeviceList,
    summary="List synced external devices for one site (cache-only, no live call)",
)
def list_external_devices(
    account_id: int,
    external_site_id: str,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
) -> ExternalDeviceList:
    """Return the cached device list for ``external_site_id``.

    This is intentionally **cache-only**: opening the Device Mapping step never
    makes a live provider call. If the cache is empty the caller should trigger
    an explicit ``sync-devices``. The site must already be in the synced site
    cache for this account.
    """
    account, _ = _require_account(db, account_id, current_user)
    _require_external_site(db, account, external_site_id)

    rows = (
        db.query(TelemetryExternalDevice)
        .filter(
            TelemetryExternalDevice.provider_account_id == account.id,
            TelemetryExternalDevice.external_site_id == external_site_id,
        )
        .order_by(
            TelemetryExternalDevice.external_device_name.asc().nullslast(),
            TelemetryExternalDevice.external_device_id.asc(),
        )
        .all()
    )
    return ExternalDeviceList(
        items=[ExternalDeviceResponse.model_validate(row) for row in rows],
        last_sync_run_id=rows[0].last_sync_run_id if rows else None,
        last_sync_status=account.last_sync_status,
        last_success_at=account.last_success_at,
    )


@telemetry_v2_router.post(
    "/v2/provider-accounts/{account_id}/external-sites/{external_site_id}/sync-devices",
    response_model=SyncDevicesResponse,
    summary="Pull the device list for one site and update the device cache",
    dependencies=[Depends(telemetry_admin_required)],
)
def sync_provider_account_devices(
    account_id: int,
    external_site_id: str,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    credential_store: Annotated[CredentialStore, Depends(get_credential_store)],
) -> SyncDevicesResponse:
    """Refresh the cached device list for a single external site.

    Mirrors ``sync-sites`` one level down. It makes a live provider call (only
    when explicitly invoked), upserts ``telemetry_external_devices`` keyed on
    ``{provider_account_id, external_site_id, external_device_id}`` and marks
    rows no longer reported as ``missing``. Existing rows and mappings are
    **never** wiped on a provider/sync failure — failures return early with an
    error and the cache is left untouched.
    """
    account, catalog = _require_account(db, account_id, current_user)
    if catalog is None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Provider account has no catalog mapping")
    _require_external_site(db, account, external_site_id)

    # Same rationale as sync_sites: device sync must retrieve and re-present
    # credentials to the provider, so block on a non-durable store in prod.
    _block_if_storage_not_durable(credential_store, operation="sync_devices")

    adapter = get_adapter(db, catalog.provider_key, catalog=catalog)
    if not isinstance(adapter, DeviceListingAdapter):
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Provider '{catalog.provider_key}' does not support device listing.",
        )

    creds = credential_store.retrieve(account.secret_token_name)
    run_id = _new_run_id()
    now = _utcnow()

    try:
        records = list(adapter.list_devices(creds, external_site_id))
    except CredentialError as exc:
        account.credential_status = CredentialStatus.invalid
        account.last_error_at = now
        account.last_error_message = str(exc)
        db.commit()
        return SyncDevicesResponse(
            sync_run_id=run_id,
            last_sync_status=LastSyncStatus.failed,
            seen_count=0,
            new_count=0,
            missing_count=0,
            error=str(exc) or "Invalid credentials",
        )
    except (NoData, ProviderUnavailable, RateLimited, MappingError) as exc:
        # Do not flip account credential status (these are not auth failures)
        # and do not touch the cache. Surface the error to the caller only.
        return SyncDevicesResponse(
            sync_run_id=run_id,
            last_sync_status=LastSyncStatus.failed,
            seen_count=0,
            new_count=0,
            missing_count=0,
            error=str(exc) or "Provider error",
        )

    existing = {
        row.external_device_id: row
        for row in db.query(TelemetryExternalDevice)
        .filter(
            TelemetryExternalDevice.provider_account_id == account.id,
            TelemetryExternalDevice.external_site_id == external_site_id,
        )
        .all()
    }
    seen_ids: set[str] = set()
    new_count = 0
    for record in records:
        ext_id = str(record.external_device_id)
        seen_ids.add(ext_id)
        if ext_id in existing:
            row = existing[ext_id]
            row.external_device_name = record.external_device_name or row.external_device_name
            row.raw_metadata = record.raw_metadata or row.raw_metadata
            row.last_seen_at = now
            row.last_synced_at = now
            row.last_sync_run_id = run_id
            row.sync_status = ExternalSiteSyncStatus.seen
            row.last_sync_error = None
        else:
            db.add(
                TelemetryExternalDevice(
                    provider_account_id=account.id,
                    external_site_id=external_site_id,
                    external_device_id=ext_id,
                    external_device_name=record.external_device_name,
                    raw_metadata=record.raw_metadata or None,
                    first_seen_at=now,
                    last_seen_at=now,
                    last_synced_at=now,
                    last_sync_run_id=run_id,
                    sync_status=ExternalSiteSyncStatus.seen,
                )
            )
            new_count += 1

    missing_count = 0
    for ext_id, row in existing.items():
        if ext_id not in seen_ids:
            row.sync_status = ExternalSiteSyncStatus.missing
            row.last_synced_at = now
            row.last_sync_run_id = run_id
            missing_count += 1

    db.commit()

    return SyncDevicesResponse(
        sync_run_id=run_id,
        last_sync_status=(
            LastSyncStatus.partial if missing_count else LastSyncStatus.success
        ),
        seen_count=len(seen_ids),
        new_count=new_count,
        missing_count=missing_count,
    )


# ---------------------------------------------------------------------------
# Device mapping (project device <-> external device) -- DB-only
# ---------------------------------------------------------------------------


@telemetry_v2_router.post(
    "/v2/sites/{site_id}/device-mappings",
    response_model=DeviceMappingBulkResponse,
    summary="Bulk map project devices to external devices (V2, DB-only)",
    dependencies=[Depends(AuthorizedUser(SettingsPermissions(PermissionsActions.edit)))],
)
def bulk_upsert_device_mappings(
    payload: DeviceMappingBulkRequest,
    request: Request,
    site: Annotated[Site, Depends(get_authorized_site_with_company_admin)],
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
) -> DeviceMappingBulkResponse:
    """Persist iliOS device -> external device mappings directly in iliOS.

    This is the V2 (DB-backed) device save path. Like the site-mapping save it
    deliberately does **not** call the provider and does **not** touch any GCP /
    Firestore pipeline:

    - Each external device must already exist in the iliOS device cache
      (``telemetry_external_devices``); the display name is read from there
      because ``telemetry_devices_mapping.telemetry_device_name`` is NOT NULL.
    - Each iliOS device must belong to this project/site and be
      telemetry-eligible.
    - Mappings are upserted on ``device_id`` (unique). Per-row failures are
      collected and reported; nothing is wiped because no provider call is made.
    """
    # Single source of truth for eligibility lives in the v1 router module.
    from app.routers.telemetry.telemetry import (
        TELEMETRY_ELIGIBLE_CATEGORIES,
        _create_audit_log,
    )

    # 1. Resolve + authorize the provider account (scoped to caller's companies).
    account, _ = _require_account(db, payload.provider_account_id, current_user)

    # 2. The provider account must belong to the same company as the site.
    if account.company_id != site.company_id:
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "Provider account does not belong to this project's company.",
        )

    # 3. The external site must already be in the synced site cache.
    _require_external_site(db, account, payload.external_site_id)

    site_device_ids = {device.id for device in site.devices}
    # Cache lookup for the device names (NOT NULL on the mapping row).
    device_cache = {
        row.external_device_id: row
        for row in db.query(TelemetryExternalDevice)
        .filter(
            TelemetryExternalDevice.provider_account_id == account.id,
            TelemetryExternalDevice.external_site_id == payload.external_site_id,
        )
        .all()
    }

    successful = 0
    failed = 0
    errors: list[str] = []

    for item in payload.mappings:
        device = next((d for d in site.devices if d.id == item.device_id), None)
        if item.device_id not in site_device_ids or device is None:
            errors.append(f"Device {item.device_id} does not belong to this project")
            failed += 1
            continue
        if device.category not in TELEMETRY_ELIGIBLE_CATEGORIES:
            errors.append(
                f"Device {item.device_id} is not telemetry-eligible "
                f"(category: {device.category.value if device.category else None})"
            )
            failed += 1
            continue

        cache_row = device_cache.get(item.external_device_id)
        if cache_row is None:
            errors.append(
                f"Device {item.device_id}: external device {item.external_device_id} "
                "is not in the synced device cache. Sync devices and try again."
            )
            failed += 1
            continue

        device_name = cache_row.external_device_name or cache_row.external_device_id
        device_role = (item.device_role or "primary").strip() or "primary"

        mapping = (
            db.query(TelemetryDeviceMapping)
            .filter(TelemetryDeviceMapping.device_id == item.device_id)
            .first()
        )
        if mapping is None:
            mapping = TelemetryDeviceMapping(
                device_id=item.device_id,
                telemetry_device_id=item.external_device_id,
                telemetry_device_name=device_name,
                provider_account_id=account.id,
                device_role=device_role,
                is_active=True,
            )
            db.add(mapping)
        else:
            mapping.telemetry_device_id = item.external_device_id
            mapping.telemetry_device_name = device_name
            mapping.provider_account_id = account.id
            mapping.device_role = device_role
            mapping.is_active = True
            mapping.updated_at = _utcnow()
        successful += 1

    db.commit()

    logger.info(
        "telemetry_v2_device_mappings_saved site_id=%s account_id=%s external_site_id=%s successful=%s failed=%s",
        site.id,
        account.id,
        payload.external_site_id,
        successful,
        failed,
    )

    # Best-effort audit trail; never blocks or rolls back the saved mappings.
    try:
        _create_audit_log(
            request,
            db,
            "telemetry_v2_device_mappings_saved",
            (
                f"Bulk-mapped {successful} device(s) on project/site {site.id} to "
                f"external site {payload.external_site_id} via provider account {account.id} "
                f"({failed} failed)"
            ),
            is_success=(failed == 0),
        )
    except Exception:  # noqa: BLE001
        logger.warning("telemetry_v2_device_mappings_audit_failed site_id=%s", site.id)

    return DeviceMappingBulkResponse(
        successful_count=successful,
        failed_count=failed,
        errors=errors if errors else None,
    )


# ---------------------------------------------------------------------------
# Native readings ingestion -- manual single-site refresh (V2)
# ---------------------------------------------------------------------------

# A manual refresh is bounded so it can never trigger an unbounded provider
# pull. Omitting the window refreshes the most recent 24h.
_MAX_REFRESH_WINDOW = timedelta(hours=24)
_DEFAULT_REFRESH_WINDOW = timedelta(hours=24)


def _coerce_naive_utc(dt: datetime) -> datetime:
    """Normalize a request timestamp to UTC-naive (the storage convention).

    tz-aware inputs are converted to UTC then stripped; naive inputs are
    assumed to already be UTC.
    """
    if dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


@telemetry_v2_router.post(
    "/v2/sites/{site_id}/refresh-readings",
    response_model=RefreshReadingsResponse,
    summary="Manually refresh native telemetry readings for one mapped site",
    dependencies=[Depends(telemetry_admin_required)],
)
def refresh_site_readings(
    payload: RefreshReadingsRequest,
    request: Request,
    site: Annotated[Site, Depends(get_authorized_site_with_company_admin)],
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    credential_store: Annotated[CredentialStore, Depends(get_credential_store)],
) -> RefreshReadingsResponse:
    """Pull + persist native telemetry readings for one mapped project/site.

    This is the in-app replacement for the legacy GCP/BigQuery pull. It pulls
    readings for the site's mapped devices over a bounded window through the
    provider adapter, upserts them idempotently into ``telemetry_readings``,
    then computes derived interval rollups. No BigQuery / Firestore / Cloud
    Function is involved; GCP is only ever the durable credential store.

    Safety contract:

    - **Never wipes on failure.** Every persistence path only upserts. A
      provider or rollup failure leaves all previously stored readings,
      mappings and cached devices untouched, and still records a sync-job row.
    - **Idempotent.** Re-running the same window corrects values in place.
    - **Bounded.** The window is clamped to a maximum span so a manual refresh
      cannot trigger an unbounded pull.
    - **Additive only.** The "Site" entity is never modified.
    """
    # Authorization: the site dependency restricts to the caller's companies and
    # company-admin scope; telemetry_admin_required gates the action. Enforce
    # company visibility explicitly as defense in depth before doing any work.
    _enforce_company_visibility(current_user, site.company_id)

    # In production, a manual refresh re-presents stored credentials to the
    # provider; refuse if the credential store cannot durably hold them.
    _block_if_storage_not_durable(credential_store, operation="refresh_readings")

    # Resolve + bound the pull window (default: most recent 24h).
    window_end = _coerce_naive_utc(payload.window_end) if payload.window_end else _utcnow()
    if payload.window_start:
        window_start = _coerce_naive_utc(payload.window_start)
    else:
        window_start = window_end - _DEFAULT_REFRESH_WINDOW

    if window_end <= window_start:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "window_end must be after window_start.",
        )
    if window_end - window_start > _MAX_REFRESH_WINDOW:
        # Clamp rather than reject so a too-wide request still does useful work.
        window_start = window_end - _MAX_REFRESH_WINDOW

    # Ingest. Missing preconditions (no mapping/devices/catalog) surface as a
    # typed config error mapped to the right HTTP status; no job is created.
    try:
        summary = run_site_refresh(
            db,
            site_id=site.id,
            window_start=window_start,
            window_end=window_end,
            triggered_by_user_id=getattr(current_user, "id", None),
            credential_store=credential_store,
        )
    except IngestionConfigError as exc:
        raise HTTPException(exc.status_code, exc.detail)

    # Derived rollups run after the readings commit and are failure-isolated:
    # a rollup error never undoes committed readings nor fails the refresh.
    # The rollup window_start is floored to the top of the hour (mirroring the
    # scheduler/backfill path) so the boundary bucket is recomputed from the full
    # hour of persisted readings rather than only the partial requested slice.
    rollup = run_rollups_for_window(
        db,
        site_id=site.id,
        company_id=summary.company_id,
        window_start=floor_to_hour(window_start),
        window_end=window_end,
        bucket_sizes=("1h",),
        sync_job_id=summary.sync_job_id,
    )
    if rollup.status == "failed":
        logger.warning(
            "telemetry_v2_refresh_rollup_failed site_id=%s job_id=%s error=%s",
            site.id,
            summary.sync_job_id,
            rollup.error,
        )

    logger.info(
        "telemetry_v2_refresh_readings site_id=%s job_id=%s status=%s "
        "received=%s written=%s targets_failed=%s rollup_status=%s",
        site.id,
        summary.sync_job_id,
        summary.status.value,
        summary.readings_received,
        summary.readings_written,
        summary.targets_failed,
        rollup.status,
    )

    # Best-effort audit trail; never blocks or rolls back the refresh.
    try:
        from app.routers.telemetry.telemetry import _create_audit_log

        _create_audit_log(
            request,
            db,
            "telemetry_v2_refresh_readings",
            (
                f"Refreshed telemetry for project/site {site.id} "
                f"(job {summary.sync_job_id}, status {summary.status.value}, "
                f"{summary.readings_written} readings written)"
            ),
            is_success=(summary.status.value != "failed"),
        )
    except Exception:  # noqa: BLE001
        logger.warning(
            "telemetry_v2_refresh_readings_audit_failed site_id=%s", site.id
        )

    return RefreshReadingsResponse(
        sync_job_id=summary.sync_job_id,
        correlation_id=summary.correlation_id,
        status=summary.status,
        site_id=summary.site_id,
        company_id=summary.company_id,
        provider_key=summary.provider_key,
        external_site_id=summary.external_site_id,
        window_start=summary.window_start,
        window_end=summary.window_end,
        devices_mapped=summary.devices_mapped,
        devices_seen=summary.devices_seen,
        targets_attempted=summary.targets_attempted,
        targets_with_data=summary.targets_with_data,
        targets_failed=summary.targets_failed,
        targets_ambiguous=summary.targets_ambiguous,
        readings_received=summary.readings_received,
        readings_written=summary.readings_written,
        rate_limited=summary.rate_limited,
        started_at=summary.started_at,
        ended_at=summary.ended_at,
        error=summary.error,
        errors=summary.errors,
    )


# ---------------------------------------------------------------------------
# Scheduler control + status (Task #38)
# ---------------------------------------------------------------------------


def _resolve_scheduler_account(db: Session, site_id: int) -> Optional[int]:
    """Resolve the provider account id backing a site's telemetry mapping.

    Mirrors the ingestion service: ``provider_account_id`` first, then the
    legacy ``connection_id``. Returns ``None`` when the site has no mapping.
    """
    mapping = (
        db.query(TelemetrySiteMapping)
        .filter(TelemetrySiteMapping.site_id == site_id)
        .first()
    )
    if mapping is None:
        return None
    return mapping.provider_account_id or mapping.connection_id


def _scheduler_state_to_response(state) -> SchedulerStateResponse:
    return SchedulerStateResponse(
        site_id=state.site_id,
        provider_account_id=state.provider_account_id,
        company_id=state.company_id,
        enabled=state.enabled,
        cadence=state.cadence or DEFAULT_CADENCE,
        next_due_at=state.next_due_at,
        last_run_at=state.last_run_at,
        last_status=state.last_status,
        last_error=state.last_error,
        last_successful_pull_at=state.last_successful_pull_at,
        last_sync_job_id=state.last_sync_job_id,
        locked_until=state.locked_until,
    )


@telemetry_v2_router.get(
    "/v2/sites/{site_id}/scheduler",
    response_model=SchedulerStateResponse,
    summary="Get the native telemetry scheduler state for one site",
    dependencies=[Depends(telemetry_admin_required)],
)
def get_site_scheduler(
    site: Annotated[Site, Depends(get_authorized_site_with_company_admin)],
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
) -> SchedulerStateResponse:
    """Return the scheduler row for a site, or synthesized disabled defaults.

    Resolves the site's CURRENT mapped account and returns that exact row — never
    a site-only "first row wins" lookup — so a row left behind by a prior account
    remap can't masquerade as the live scheduler state.
    """
    _enforce_company_visibility(current_user, site.company_id)
    account_id = _resolve_scheduler_account(db, site.id)
    state = (
        TelemetrySchedulerStateCRUD(db).get_by_site_account(site.id, account_id)
        if account_id is not None
        else None
    )
    if state is not None:
        return _scheduler_state_to_response(state)
    return SchedulerStateResponse(
        site_id=site.id,
        provider_account_id=account_id,
        company_id=site.company_id,
        enabled=False,
        cadence=DEFAULT_CADENCE,
    )


@telemetry_v2_router.put(
    "/v2/sites/{site_id}/scheduler",
    response_model=SchedulerStateResponse,
    summary="Enable/disable or set cadence for a site's telemetry scheduler",
    dependencies=[Depends(telemetry_admin_required)],
)
def update_site_scheduler(
    payload: SchedulerUpdateRequest,
    request: Request,
    site: Annotated[Site, Depends(get_authorized_site_with_company_admin)],
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
) -> SchedulerStateResponse:
    """Lazily upsert the scheduler row for a site.

    Enabling re-arms the cursor (``next_due_at = now``) so the next poll runs
    promptly; disabling leaves the cursor untouched. Cadence is validated
    against the server whitelist. The runner thread is gated independently by
    ``telemetry_scheduler_enabled`` — toggling here records intent regardless.
    """
    _enforce_company_visibility(current_user, site.company_id)

    if payload.cadence is not None and payload.cadence not in ALLOWED_CADENCES:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            (
                f"Unsupported cadence '{payload.cadence}'. Allowed values: "
                f"{', '.join(sorted(ALLOWED_CADENCES))}."
            ),
        )

    account_id = _resolve_scheduler_account(db, site.id)
    if account_id is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            (
                "Site is not mapped to a telemetry provider account; configure "
                "telemetry before enabling the scheduler."
            ),
        )

    kwargs = dict(
        site_id=site.id,
        provider_account_id=account_id,
        company_id=site.company_id,
        enabled=payload.enabled,
        cadence=payload.cadence,
    )
    if payload.enabled is True:
        kwargs["next_due_at"] = _utcnow()

    state = TelemetrySchedulerStateCRUD(db).upsert_config(**kwargs)

    try:
        from app.routers.telemetry.telemetry import _create_audit_log

        _create_audit_log(
            request,
            db,
            "telemetry_v2_scheduler_update",
            (
                f"Updated telemetry scheduler for project/site {site.id} "
                f"(enabled={state.enabled}, cadence={state.cadence})"
            ),
            is_success=True,
        )
    except Exception:  # noqa: BLE001
        logger.warning(
            "telemetry_v2_scheduler_update_audit_failed site_id=%s", site.id
        )

    return _scheduler_state_to_response(state)


@telemetry_v2_router.get(
    "/v2/companies/{company_id}/scheduler/status",
    response_model=CompanySchedulerStatusList,
    summary="Scheduler status across a company's mapped telemetry sites",
    dependencies=[Depends(telemetry_admin_required)],
)
def company_scheduler_status(
    company_id: int,
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
) -> CompanySchedulerStatusList:
    """List per-site scheduler state for every mapped site in a company.

    Sites that are mapped but have no scheduler row yet are returned with
    synthesized disabled defaults so the company view is complete.
    """
    _enforce_company_visibility(current_user, company_id)

    mappings = (
        db.query(TelemetrySiteMapping)
        .join(Site, Site.id == TelemetrySiteMapping.site_id)
        .filter(
            Site.company_id == company_id,
            TelemetrySiteMapping.is_active.is_(True),
        )
        .all()
    )
    site_ids = [m.site_id for m in mappings]
    index = TelemetrySchedulerStateCRUD(db).index_by_site_account(site_ids)

    items: list[SchedulerStateResponse] = []
    for mapping in mappings:
        # Match each site to its CURRENT mapped account, so a stale row from a
        # prior account is never reported as this site's live scheduler state.
        account_id = mapping.provider_account_id or mapping.connection_id
        state = index.get((mapping.site_id, account_id))
        if state is not None:
            items.append(_scheduler_state_to_response(state))
        else:
            items.append(
                SchedulerStateResponse(
                    site_id=mapping.site_id,
                    provider_account_id=account_id,
                    company_id=company_id,
                    enabled=False,
                    cadence=DEFAULT_CADENCE,
                )
            )
    return CompanySchedulerStatusList(company_id=company_id, items=items)


# ---------------------------------------------------------------------------
# Bounded historical backfill (Task #38)
# ---------------------------------------------------------------------------

_BACKFILL_PRESETS = {"7d": timedelta(days=7), "30d": timedelta(days=30)}
_MAX_BACKFILL_WINDOW = timedelta(days=30)
_BACKFILL_CHUNK = timedelta(hours=24)
# Generous lease so a long multi-chunk backfill holds the lock for its whole
# run. If it ever overruns, idempotent upserts make the overlap harmless and the
# token-guarded release prevents clobbering a newer run.
_BACKFILL_LEASE_SECONDS = 3600


@telemetry_v2_router.post(
    "/v2/sites/{site_id}/backfill-readings",
    response_model=BackfillReadingsResponse,
    summary="Bounded historical backfill of native telemetry readings",
    dependencies=[Depends(telemetry_admin_required)],
)
def backfill_site_readings(
    payload: BackfillReadingsRequest,
    request: Request,
    site: Annotated[Site, Depends(get_authorized_site_with_company_admin)],
    db: Annotated[Session, Depends(get_session)],
    current_user: Annotated[CurrentUserSchema, Depends(get_current_user)],
    credential_store: Annotated[CredentialStore, Depends(get_credential_store)],
) -> BackfillReadingsResponse:
    """Backfill native readings for one mapped site over a bounded window.

    Same safety contract as the manual refresh (never wipes, idempotent,
    additive-only, GCP only as credential store), with these backfill specifics:

    - **Bounded.** Total span capped at 30 days; inverted/oversized -> 422.
    - **Chunked.** Processed as 24h chunks oldest->newest, with bucket-aligned
      rollups per chunk; stops on the first failed chunk and returns ``partial``.
    - **Serialized.** Claims the *same* per-site lease lock as the scheduler, so
      a backfill and a scheduled run can never overlap (-> 409 when held).
    - **Cursor-safe.** NEVER advances ``last_successful_pull_at`` or
      ``next_due_at`` — a backfill of old data must not move the live cursor.
    """
    _enforce_company_visibility(current_user, site.company_id)
    _block_if_storage_not_durable(credential_store, operation="backfill_readings")

    # Resolve the window from a preset or explicit bounds.
    window_end = (
        _coerce_naive_utc(payload.window_end) if payload.window_end else _utcnow()
    )
    if payload.preset is not None:
        if payload.preset not in _BACKFILL_PRESETS:
            raise HTTPException(
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                (
                    f"Unsupported preset '{payload.preset}'. Allowed: "
                    f"{', '.join(sorted(_BACKFILL_PRESETS))}."
                ),
            )
        window_start = window_end - _BACKFILL_PRESETS[payload.preset]
    elif payload.window_start is not None:
        window_start = _coerce_naive_utc(payload.window_start)
    else:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "Provide a preset ('7d'/'30d') or an explicit window_start.",
        )

    if window_end <= window_start:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "window_end must be after window_start.",
        )
    if window_end - window_start > _MAX_BACKFILL_WINDOW:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            (
                "Backfill window exceeds the maximum of "
                f"{_MAX_BACKFILL_WINDOW.days} days."
            ),
        )

    # Resolve the provider account and lazily ensure a scheduler row to hold the
    # lock (a site may be backfilled without ever enabling the scheduler).
    account_id = _resolve_scheduler_account(db, site.id)
    if account_id is None:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "Site is not mapped to a telemetry provider account.",
        )

    crud = TelemetrySchedulerStateCRUD(db)
    state = crud.ensure_state(
        site_id=site.id,
        provider_account_id=account_id,
        company_id=site.company_id,
    )

    token = secrets.token_hex(16)
    if not crud.claim(
        state.id,
        token=token,
        lease_seconds=_BACKFILL_LEASE_SECONDS,
        require_enabled=False,
    ):
        raise HTTPException(
            status.HTTP_409_CONFLICT,
            (
                "A telemetry ingestion run is already in progress for this "
                "site. Try again once it completes."
            ),
        )

    chunks: list[BackfillChunkResult] = []
    chunks_succeeded = 0
    chunks_failed = 0
    total_received = 0
    total_written = 0
    saw_partial = False
    overall_status = "succeeded"
    overall_error: Optional[str] = None

    try:
        chunk_start = window_start
        while chunk_start < window_end:
            chunk_end = min(chunk_start + _BACKFILL_CHUNK, window_end)
            try:
                result = run_ingestion_with_rollup(
                    db,
                    site_id=site.id,
                    window_start=chunk_start,
                    window_end=chunk_end,
                    trigger=TelemetrySyncTrigger.backfill,
                    triggered_by_user_id=getattr(current_user, "id", None),
                    credential_store=credential_store,
                )
            except IngestionConfigError as exc:
                chunks.append(
                    BackfillChunkResult(
                        window_start=chunk_start,
                        window_end=chunk_end,
                        status="config_error",
                        error=exc.detail,
                    )
                )
                chunks_failed += 1
                overall_status = "partial" if chunks_succeeded else "failed"
                overall_error = exc.detail
                break

            summary = result.summary
            rollup = result.rollup
            total_received += summary.readings_received
            total_written += summary.readings_written
            chunks.append(
                BackfillChunkResult(
                    window_start=chunk_start,
                    window_end=chunk_end,
                    sync_job_id=summary.sync_job_id,
                    status=summary.status.value,
                    readings_received=summary.readings_received,
                    readings_written=summary.readings_written,
                    rollup_status=rollup.status,
                    error=summary.error,
                )
            )

            if summary.status == TelemetrySyncStatus.failed:
                chunks_failed += 1
                overall_status = "partial" if chunks_succeeded else "failed"
                overall_error = summary.error
                break

            chunks_succeeded += 1
            # Readings landed but the rollup for this chunk failed: the chunk
            # still counts as succeeded (readings are durable), but the overall
            # backfill is partial — mirrors the scheduler's partial semantics.
            if (
                summary.status == TelemetrySyncStatus.partial
                or rollup.status == "failed"
            ):
                saw_partial = True
            chunk_start = chunk_end
        else:
            overall_status = "partial" if saw_partial else "succeeded"
    finally:
        # Release the lock WITHOUT advancing the cursor or next_due_at: a
        # historical backfill must never move the live scheduled cursor. The
        # token guard makes this a no-op if our lease already expired and the
        # row was re-claimed.
        #
        # Use a FRESH session: an unexpected error may have left the request
        # session (db) in a broken transaction, which would make the release
        # itself fail and strand the lock until the lease self-expires. Mirrors
        # the scheduler runner's _release_after_error pattern.
        last_job_id = next(
            (c.sync_job_id for c in reversed(chunks) if c.sync_job_id is not None),
            None,
        )
        release_session = SessionFactory()
        try:
            TelemetrySchedulerStateCRUD(release_session).finish_run(
                state.id,
                token=token,
                last_run_at=_utcnow(),
                last_status=f"bf_{overall_status}"[:16],
                last_error=overall_error,
                last_sync_job_id=last_job_id,
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "telemetry_v2_backfill_release_failed site_id=%s state_id=%s",
                site.id,
                state.id,
            )
        finally:
            release_session.close()

    logger.info(
        "telemetry_v2_backfill site_id=%s status=%s chunks=%s ok=%s failed=%s "
        "received=%s written=%s",
        site.id,
        overall_status,
        len(chunks),
        chunks_succeeded,
        chunks_failed,
        total_received,
        total_written,
    )

    try:
        from app.routers.telemetry.telemetry import _create_audit_log

        _create_audit_log(
            request,
            db,
            "telemetry_v2_backfill_readings",
            (
                f"Backfilled telemetry for project/site {site.id} "
                f"(status {overall_status}, {chunks_succeeded} chunk(s) ok, "
                f"{total_written} readings written)"
            ),
            is_success=(overall_status != "failed"),
        )
    except Exception:  # noqa: BLE001
        logger.warning(
            "telemetry_v2_backfill_readings_audit_failed site_id=%s", site.id
        )

    return BackfillReadingsResponse(
        site_id=site.id,
        company_id=site.company_id,
        status=overall_status,
        requested_window_start=window_start,
        requested_window_end=window_end,
        chunks_total=len(chunks),
        chunks_succeeded=chunks_succeeded,
        chunks_failed=chunks_failed,
        readings_received=total_received,
        readings_written=total_written,
        chunks=chunks,
        error=overall_error,
    )
