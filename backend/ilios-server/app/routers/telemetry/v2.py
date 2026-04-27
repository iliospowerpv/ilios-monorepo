"""Telemetry v2 API router (Phase 1 introduce).

All endpoints live under ``/api/telemetry/v2`` and operate against the new
catalog / license / provider-account model. The legacy
``/api/telemetry/...`` routes continue to function unchanged.
"""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.db.session import get_session
from app.helpers.authentication import get_current_user
from app.helpers.authorization.module_based.telemetry import (
    telemetry_admin_required,
    user_has_telemetry_admin,
)
from app.integrations.telemetry import (
    CredentialError,
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
)
from app.models.telemetry import (
    CompanyDASProvider,
    CompanyProviderStatus,
    CredentialStatus,
    DASConnection,
    DASProvidersEnum,
    ExternalSiteSyncStatus,
    LastSyncStatus,
    ProviderAccountStatus,
    TelemetryExternalSite,
    TelemetryProviderCatalog,
    TelemetrySiteMapping,
)
from app.schema.telemetry_v2 import (
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
    SyncSitesResponse,
    TestAccountResponse,
)
from app.security.redaction import fingerprint
from app.schema.user import CurrentUserSchema

logger = logging.getLogger(__name__)

telemetry_v2_router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _utcnow() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _new_run_id() -> str:
    return f"run_{secrets.token_hex(8)}"


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

    if not getattr(current_user, "is_system_user", False):
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
    if getattr(current_user, "is_system_user", False):
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
