"""Native V2 telemetry ingestion for a single mapped site.

This service replaces the legacy GCP/BigQuery telemetry pull with a fully
in-app ingestion path: it resolves the iliOS site -> provider account -> mapped
devices, pulls normalized readings through a :class:`ReadingsAdapter`, and
upserts them into ``telemetry_readings`` idempotently.

Design guarantees (see Task spec):

* **Never wipes on failure.** Every code path only ever upserts rows. A
  provider error, an empty pull, or a persistence error leaves all previously
  stored readings, mappings and cached devices untouched. A sync-job row is
  still written for every attempt so the UI can show status + last-refreshed.
* **Idempotent.** Re-running the same window upserts on the readings dedupe
  constraint, so values are corrected in place rather than duplicated.
* **Partial-failure tolerant.** Per-device/metric provider errors are recorded
  on the result and surfaced as a ``partial`` (data written) or ``failed`` (no
  data) job, never as an exception that aborts the whole refresh.
* **Additive only.** The "Site" entity is never modified; the service reads the
  existing mapping tables and writes only to the new native-ingestion tables.

Only ``site`` scope is implemented. The signature is structured so the
follow-up scheduler/backfill task can reuse it for wider scopes.
"""
from __future__ import annotations

import logging
import secrets
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.crud.telemetry_native import TelemetryReadingCRUD, TelemetrySyncJobCRUD
from app.integrations.telemetry import (
    CredentialError,
    MappingError,
    NoData,
    ProviderUnavailable,
    RateLimited,
    ReadingsAdapter,
    get_adapter,
)
from app.integrations.telemetry.credential_store import (
    CredentialStore,
    get_credential_store,
)
from app.integrations.telemetry.models import MetricFieldSpec
from app.models.device import Device
from app.models.site import Site
from app.models.telemetry import (
    CompanyDASProvider,
    CredentialStatus,
    DASConnection,
    LastSyncStatus,
    TelemetryDeviceMapping,
    TelemetryMetricCatalog,
    TelemetryProviderCatalog,
    TelemetryReading,
    TelemetrySiteMapping,
    TelemetrySyncScope,
    TelemetrySyncStatus,
    TelemetrySyncTrigger,
)

logger = logging.getLogger(__name__)

# Cap how many provider error strings are persisted on a job's stats blob so a
# pathological run can't bloat the row. The full count is always preserved.
_MAX_PERSISTED_ERRORS = 25


class IngestionConfigError(Exception):
    """A precondition for ingestion is missing (mapping/license/catalog/etc.).

    Carries an HTTP-ish ``status_code`` so the calling endpoint can translate
    it to the right response without the service importing FastAPI. These are
    configuration problems surfaced *before* any sync job is created — no job
    row is written and nothing is mutated.
    """

    def __init__(self, detail: str, *, status_code: int = 409) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


@dataclass(frozen=True)
class _SiteIngestionContext:
    """Everything resolved up front for a single-site pull."""

    site: Site
    company_id: int
    account: DASConnection
    catalog: TelemetryProviderCatalog
    external_site_id: str
    metric_specs: tuple[MetricFieldSpec, ...]
    external_device_ids: tuple[str, ...]
    external_to_device: dict[str, int]


@dataclass
class IngestionSummary:
    """Structured outcome the endpoint maps onto ``RefreshReadingsResponse``."""

    sync_job_id: int
    correlation_id: str
    status: TelemetrySyncStatus
    site_id: int
    company_id: int
    window_start: datetime
    window_end: datetime
    provider_key: Optional[str] = None
    external_site_id: Optional[str] = None
    devices_mapped: int = 0
    devices_seen: int = 0
    targets_attempted: int = 0
    targets_with_data: int = 0
    targets_failed: int = 0
    targets_ambiguous: int = 0
    readings_received: int = 0
    readings_written: int = 0
    rate_limited: bool = False
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    error: Optional[str] = None
    errors: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Resolution helpers
# ---------------------------------------------------------------------------


def _resolve_catalog_for_account(
    db: Session, account: DASConnection
) -> Optional[TelemetryProviderCatalog]:
    """Mirror the router's account->catalog resolution (license, then enum)."""
    if account.company_provider_id:
        license_row = db.get(CompanyDASProvider, account.company_provider_id)
        if license_row and license_row.catalog_id:
            catalog = db.get(TelemetryProviderCatalog, license_row.catalog_id)
            if catalog is not None:
                return catalog
    return (
        db.query(TelemetryProviderCatalog)
        .filter(TelemetryProviderCatalog.provider_key == account.provider.name)
        .first()
    )


def _load_metric_specs(
    db: Session, provider_key: str
) -> tuple[MetricFieldSpec, ...]:
    """Build one :class:`MetricFieldSpec` per normalized metric in the catalog.

    Catalog rows that share a ``normalized_metric`` become multiple candidate
    fields on a single spec (e.g. AlsoEnergy ``Sun``/``Sun2`` -> irradiance);
    the adapter resolves ambiguity per device. Disabled rows are skipped.
    """
    rows = (
        db.query(TelemetryMetricCatalog)
        .filter(
            TelemetryMetricCatalog.provider_key == provider_key,
            TelemetryMetricCatalog.is_enabled.is_(True),
        )
        .all()
    )
    grouped: dict[str, dict] = {}
    for row in rows:
        bucket = grouped.setdefault(
            row.normalized_metric, {"unit": row.unit, "candidates": []}
        )
        query_field = row.provider_query_field or row.provider_field_name
        bucket["candidates"].append((row.provider_field_name, query_field))
    return tuple(
        MetricFieldSpec(
            normalized_metric=metric,
            unit=data["unit"],
            candidates=tuple(data["candidates"]),
        )
        for metric, data in grouped.items()
    )


def _resolve_site_ingestion_context(
    db: Session, site_id: int
) -> _SiteIngestionContext:
    """Resolve and validate every precondition for a single-site pull.

    Raises :class:`IngestionConfigError` (no job row created) when the site is
    not ready to ingest.
    """
    site = db.get(Site, site_id)
    if site is None:
        raise IngestionConfigError("Site not found", status_code=404)

    mapping = (
        db.query(TelemetrySiteMapping)
        .filter(TelemetrySiteMapping.site_id == site_id)
        .first()
    )
    if mapping is None:
        raise IngestionConfigError(
            "This project is not mapped to a telemetry provider.",
            status_code=409,
        )

    account_id = mapping.provider_account_id or mapping.connection_id
    if not account_id:
        raise IngestionConfigError(
            "The telemetry mapping has no provider account.", status_code=409
        )
    account = db.get(DASConnection, account_id)
    if account is None:
        raise IngestionConfigError(
            "The mapped telemetry provider account no longer exists.",
            status_code=409,
        )

    external_site_id = (mapping.telemetry_site_id or "").strip()
    if not external_site_id:
        raise IngestionConfigError(
            "The telemetry mapping has no external site id.", status_code=409
        )

    catalog = _resolve_catalog_for_account(db, account)
    if catalog is None:
        raise IngestionConfigError(
            "The provider account has no catalog mapping.", status_code=409
        )

    metric_specs = _load_metric_specs(db, catalog.provider_key)
    if not metric_specs:
        raise IngestionConfigError(
            f"No telemetry metric catalog is configured for provider "
            f"'{catalog.provider_key}'.",
            status_code=409,
        )

    # Mapped devices define the pull scope. Each active device mapping under
    # this site contributes its external device id; readings are restricted to
    # these so we never pull hardware the user hasn't mapped.
    device_rows = (
        db.query(TelemetryDeviceMapping, Device)
        .join(Device, Device.id == TelemetryDeviceMapping.device_id)
        .filter(
            Device.site_id == site_id,
            TelemetryDeviceMapping.is_active.is_(True),
        )
        .all()
    )
    external_to_device: dict[str, int] = {}
    for device_mapping, device in device_rows:
        ext_id = (device_mapping.telemetry_device_id or "").strip()
        if not ext_id:
            continue
        # First active mapping wins if duplicates somehow exist.
        external_to_device.setdefault(ext_id, device.id)

    if not external_to_device:
        raise IngestionConfigError(
            "No devices are mapped for this project, so there is nothing to "
            "refresh.",
            status_code=409,
        )

    company_id = mapping.company_id or site.company_id or account.company_id

    return _SiteIngestionContext(
        site=site,
        company_id=company_id,
        account=account,
        catalog=catalog,
        external_site_id=external_site_id,
        metric_specs=metric_specs,
        external_device_ids=tuple(external_to_device.keys()),
        external_to_device=external_to_device,
    )


# ---------------------------------------------------------------------------
# Public entrypoint
# ---------------------------------------------------------------------------


def run_site_refresh(
    db: Session,
    *,
    site_id: int,
    window_start: datetime,
    window_end: datetime,
    triggered_by_user_id: Optional[int] = None,
    credential_store: Optional[CredentialStore] = None,
    trigger: TelemetrySyncTrigger = TelemetrySyncTrigger.manual,
) -> IngestionSummary:
    """Pull + persist readings for one mapped site over ``[start, end]``.

    Returns an :class:`IngestionSummary` for every outcome (success, partial,
    or provider failure). Raises :class:`IngestionConfigError` only for missing
    preconditions resolved *before* a job is created.
    """
    store = credential_store or get_credential_store()
    ctx = _resolve_site_ingestion_context(db, site_id)

    adapter = get_adapter(db, ctx.catalog.provider_key, catalog=ctx.catalog)
    if not isinstance(adapter, ReadingsAdapter):
        raise IngestionConfigError(
            f"Provider '{ctx.catalog.provider_key}' does not support readings "
            f"ingestion.",
            status_code=400,
        )

    job_crud = TelemetrySyncJobCRUD(db)
    reading_crud = TelemetryReadingCRUD(db)

    correlation_id = f"sync_{secrets.token_hex(8)}"
    job = job_crud.create_job(
        company_id=ctx.company_id,
        site_id=ctx.site.id,
        provider_account_id=ctx.account.id,
        correlation_id=correlation_id,
        window_start=window_start,
        window_end=window_end,
        scope=TelemetrySyncScope.site,
        trigger=trigger,
        triggered_by_user_id=triggered_by_user_id,
    )
    job_crud.mark_running(job.id)

    summary = IngestionSummary(
        sync_job_id=job.id,
        correlation_id=correlation_id,
        status=TelemetrySyncStatus.running,
        site_id=ctx.site.id,
        company_id=ctx.company_id,
        window_start=window_start,
        window_end=window_end,
        provider_key=ctx.catalog.provider_key,
        external_site_id=ctx.external_site_id,
        devices_mapped=len(ctx.external_device_ids),
        started_at=job.started_at,
    )

    creds = store.retrieve(ctx.account.secret_token_name)

    # --- Provider pull (session-fatal failures raise; we record + return) ---
    try:
        pull = adapter.get_readings(
            creds,
            external_site_id=ctx.external_site_id,
            metric_specs=ctx.metric_specs,
            window_start=window_start,
            window_end=window_end,
            external_device_ids=ctx.external_device_ids,
        )
    except CredentialError as exc:
        return _finish_failed(
            db,
            job_crud,
            job.id,
            summary,
            account=ctx.account,
            error=str(exc) or "Invalid telemetry credentials.",
            auth_failure=True,
        )
    except (NoData, ProviderUnavailable, RateLimited, MappingError) as exc:
        return _finish_failed(
            db,
            job_crud,
            job.id,
            summary,
            account=ctx.account,
            error=str(exc) or "Telemetry provider error.",
            auth_failure=False,
        )
    except Exception as exc:  # noqa: BLE001 — never let an adapter bug wipe data
        logger.exception(
            "telemetry_ingestion_unexpected_pull_error job_id=%s site_id=%s",
            job.id,
            site_id,
        )
        return _finish_failed(
            db,
            job_crud,
            job.id,
            summary,
            account=ctx.account,
            error=f"Unexpected error pulling telemetry: {type(exc).__name__}",
            auth_failure=False,
        )

    summary.devices_seen = pull.devices_seen
    summary.targets_attempted = pull.targets_attempted
    summary.targets_with_data = pull.targets_with_data
    summary.targets_failed = pull.targets_failed
    summary.targets_ambiguous = pull.targets_ambiguous
    summary.rate_limited = pull.rate_limited
    summary.readings_received = len(pull.readings)
    summary.errors = list(pull.errors)

    # --- Normalize -> rows ---
    rows: list[dict] = []
    for reading in pull.readings:
        ext_device_id = reading.external_device_id or None
        dedupe_key = ext_device_id or TelemetryReading.SITE_LEVEL_SENTINEL
        rows.append(
            {
                "company_id": ctx.company_id,
                "provider_account_id": ctx.account.id,
                "external_site_id": ctx.external_site_id,
                "site_id": ctx.site.id,
                "external_device_id": ext_device_id,
                "device_id": ctx.external_to_device.get(reading.external_device_id),
                "dedupe_key": dedupe_key,
                "provider_key": ctx.catalog.provider_key,
                "provider_metric": reading.provider_field,
                "normalized_metric": reading.normalized_metric,
                "metric_ts": reading.metric_ts,
                "value": reading.value,
                "unit": reading.unit,
                "quality": None,
                "sync_job_id": job.id,
            }
        )

    # --- Idempotent persist (only ever upserts; never deletes) ---
    written = 0
    try:
        written = reading_crud.upsert_readings(rows)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        logger.exception(
            "telemetry_ingestion_persist_failed job_id=%s site_id=%s", job.id, site_id
        )
        return _finish_failed(
            db,
            job_crud,
            job.id,
            summary,
            account=ctx.account,
            error=f"Failed to persist telemetry readings: {type(exc).__name__}",
            auth_failure=False,
        )

    summary.readings_written = written

    # --- Determine terminal status ---
    had_target_failures = pull.targets_failed > 0 or pull.rate_limited
    if had_target_failures:
        status = (
            TelemetrySyncStatus.partial
            if written > 0
            else TelemetrySyncStatus.failed
        )
    else:
        status = TelemetrySyncStatus.succeeded

    summary.status = status
    stats = _build_stats(summary)
    error_text = "; ".join(pull.errors[:_MAX_PERSISTED_ERRORS]) if pull.errors else None

    # Update the provider account's coarse state (used by account lists / UI).
    now = datetime.utcnow()
    if status == TelemetrySyncStatus.succeeded:
        ctx.account.credential_status = CredentialStatus.verified
        ctx.account.last_sync_status = LastSyncStatus.success
        ctx.account.last_success_at = now
        ctx.account.last_error_message = None
    elif status == TelemetrySyncStatus.partial:
        ctx.account.credential_status = CredentialStatus.verified
        ctx.account.last_sync_status = LastSyncStatus.partial
        ctx.account.last_success_at = now
        ctx.account.last_error_at = now
        ctx.account.last_error_message = error_text
    else:  # failed (no data + provider errors)
        ctx.account.last_sync_status = LastSyncStatus.failed
        ctx.account.last_error_at = now
        ctx.account.last_error_message = error_text

    job_crud.mark_finished(
        job.id,
        status=status,
        records_requested=pull.targets_attempted,
        records_received=len(pull.readings),
        records_written=written,
        stats=stats,
        last_error=error_text,
    )
    db.commit()

    finished = job_crud.get_by_id(job.id)
    if finished is not None:
        summary.started_at = finished.started_at
        summary.ended_at = finished.ended_at
    summary.error = error_text if status == TelemetrySyncStatus.failed else None
    return summary


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _build_stats(summary: IngestionSummary) -> dict:
    return {
        "provider_key": summary.provider_key,
        "external_site_id": summary.external_site_id,
        "devices_mapped": summary.devices_mapped,
        "devices_seen": summary.devices_seen,
        "targets_attempted": summary.targets_attempted,
        "targets_with_data": summary.targets_with_data,
        "targets_failed": summary.targets_failed,
        "targets_ambiguous": summary.targets_ambiguous,
        "readings_received": summary.readings_received,
        "readings_written": summary.readings_written,
        "rate_limited": summary.rate_limited,
        "error_count": len(summary.errors),
        "errors": summary.errors[:_MAX_PERSISTED_ERRORS],
    }


def _finish_failed(
    db: Session,
    job_crud: TelemetrySyncJobCRUD,
    job_id: int,
    summary: IngestionSummary,
    *,
    account: DASConnection,
    error: str,
    auth_failure: bool,
) -> IngestionSummary:
    """Mark a job failed without writing or deleting any readings.

    Used for session-fatal provider failures and persistence errors. The
    provider account's coarse state is updated so the account list reflects the
    failure, but no readings, mappings or cached devices are touched.
    """
    summary.status = TelemetrySyncStatus.failed
    summary.error = error
    if error and error not in summary.errors:
        summary.errors.append(error)

    now = datetime.utcnow()
    account.last_sync_status = LastSyncStatus.failed
    account.last_error_at = now
    account.last_error_message = error
    if auth_failure:
        account.credential_status = CredentialStatus.invalid

    job_crud.mark_finished(
        job_id,
        status=TelemetrySyncStatus.failed,
        records_requested=summary.targets_attempted,
        records_received=summary.readings_received,
        records_written=0,
        stats=_build_stats(summary),
        last_error=error,
    )
    db.commit()

    finished = job_crud.get_by_id(job_id)
    if finished is not None:
        summary.started_at = finished.started_at
        summary.ended_at = finished.ended_at
    return summary
