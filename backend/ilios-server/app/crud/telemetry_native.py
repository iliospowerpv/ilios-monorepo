"""CRUD for the native V2 telemetry ingestion tables.

Covers the two tables written during a manual refresh:

* ``telemetry_sync_jobs`` — one row per ingestion attempt (mirrors
  ``finance_sync_runs``: queued -> running -> succeeded/partial/failed).
* ``telemetry_readings`` — the normalized source-of-truth readings, upserted
  idempotently so re-pulling the same window never creates duplicates and
  never deletes anything.

Rollup tables are written by the rollup service and have their own CRUD.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.crud.base_crud import BaseCRUD
from app.models.telemetry import (
    TelemetryDeviceIntervalRollup,
    TelemetryReading,
    TelemetrySiteIntervalRollup,
    TelemetrySyncJob,
    TelemetrySyncScope,
    TelemetrySyncStatus,
    TelemetrySyncTrigger,
)

# Keep a single ON CONFLICT statement from growing unbounded for wide windows.
_UPSERT_CHUNK_SIZE = 1000


class TelemetrySyncJobCRUD(BaseCRUD):
    """Lifecycle operations for a single ingestion attempt."""

    def __init__(self, db_session: Session):
        super().__init__(model=TelemetrySyncJob, db_session=db_session)

    def create_job(
        self,
        *,
        company_id: int,
        site_id: Optional[int],
        provider_account_id: Optional[int],
        correlation_id: str,
        window_start: Optional[datetime],
        window_end: Optional[datetime],
        scope: TelemetrySyncScope = TelemetrySyncScope.site,
        trigger: TelemetrySyncTrigger = TelemetrySyncTrigger.manual,
        triggered_by_user_id: Optional[int] = None,
    ) -> TelemetrySyncJob:
        job = TelemetrySyncJob(
            company_id=company_id,
            site_id=site_id,
            provider_account_id=provider_account_id,
            scope=scope,
            status=TelemetrySyncStatus.queued,
            trigger=trigger,
            window_start=window_start,
            window_end=window_end,
            correlation_id=correlation_id,
            triggered_by_user_id=triggered_by_user_id,
        )
        self.db_session.add(job)
        self.db_session.commit()
        self.db_session.refresh(job)
        return job

    def mark_running(self, job_id: int) -> Optional[TelemetrySyncJob]:
        job = self.get_by_id(job_id)
        if not job:
            return None
        job.status = TelemetrySyncStatus.running
        job.started_at = datetime.utcnow()
        self.db_session.commit()
        self.db_session.refresh(job)
        return job

    def mark_finished(
        self,
        job_id: int,
        *,
        status: TelemetrySyncStatus,
        records_requested: int = 0,
        records_received: int = 0,
        records_written: int = 0,
        stats: Optional[dict] = None,
        last_error: Optional[str] = None,
    ) -> Optional[TelemetrySyncJob]:
        job = self.get_by_id(job_id)
        if not job:
            return None
        now = datetime.utcnow()
        job.status = status
        job.ended_at = now
        job.records_requested = records_requested
        job.records_received = records_received
        job.records_written = records_written
        if stats is not None:
            job.stats_json = stats
        job.last_error = last_error
        job.updated_at = now
        self.db_session.commit()
        self.db_session.refresh(job)
        return job


class TelemetryReadingCRUD(BaseCRUD):
    """Idempotent upsert + reads for normalized telemetry readings."""

    def __init__(self, db_session: Session):
        super().__init__(model=TelemetryReading, db_session=db_session)

    def upsert_readings(self, rows: list[dict]) -> int:
        """Idempotently upsert normalized readings. Returns rows affected.

        Conflict target is the ``uq_telemetry_readings_dedupe`` constraint
        ``(provider_account_id, dedupe_key, provider_metric, metric_ts)``. A
        re-pull of the same window updates the value in place rather than
        inserting a duplicate, and never deletes anything.

        Each dict must carry every NOT NULL column: ``company_id``,
        ``external_site_id``, ``site_id``, ``dedupe_key``, ``provider_key``,
        ``provider_metric``, ``normalized_metric``, ``metric_ts``, ``value``.
        Optional: ``provider_account_id``, ``external_device_id``,
        ``device_id``, ``unit``, ``quality``, ``sync_job_id``.
        """
        if not rows:
            return 0

        affected = 0
        for start in range(0, len(rows), _UPSERT_CHUNK_SIZE):
            chunk = rows[start : start + _UPSERT_CHUNK_SIZE]
            stmt = pg_insert(TelemetryReading).values(chunk)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_telemetry_readings_dedupe",
                set_={
                    "value": stmt.excluded.value,
                    "unit": stmt.excluded.unit,
                    "quality": stmt.excluded.quality,
                    "device_id": stmt.excluded.device_id,
                    "normalized_metric": stmt.excluded.normalized_metric,
                    "provider_key": stmt.excluded.provider_key,
                    "external_site_id": stmt.excluded.external_site_id,
                    "sync_job_id": stmt.excluded.sync_job_id,
                },
            )
            result = self.db_session.execute(stmt)
            affected += result.rowcount or 0
        self.db_session.flush()
        return affected

    def count_for_site(self, site_id: int) -> int:
        return (
            self.db_session.query(TelemetryReading)
            .filter(TelemetryReading.site_id == site_id)
            .count()
        )


class TelemetrySiteRollupCRUD(BaseCRUD):
    """Idempotent upsert for per-site interval rollups."""

    def __init__(self, db_session: Session):
        super().__init__(model=TelemetrySiteIntervalRollup, db_session=db_session)

    def upsert_rollups(self, rows: list[dict]) -> int:
        """Upsert on ``uq_telemetry_site_rollup``.

        Re-running a refresh recomputes the same
        ``(site_id, bucket_start, bucket_size, normalized_metric)`` row in place
        rather than duplicating. Never deletes.
        """
        if not rows:
            return 0
        affected = 0
        for start in range(0, len(rows), _UPSERT_CHUNK_SIZE):
            chunk = rows[start : start + _UPSERT_CHUNK_SIZE]
            stmt = pg_insert(TelemetrySiteIntervalRollup).values(chunk)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_telemetry_site_rollup",
                set_={
                    "company_id": stmt.excluded.company_id,
                    "agg": stmt.excluded.agg,
                    "value": stmt.excluded.value,
                    "unit": stmt.excluded.unit,
                    "sample_count": stmt.excluded.sample_count,
                    "completeness": stmt.excluded.completeness,
                    "calculated_at": stmt.excluded.calculated_at,
                },
            )
            result = self.db_session.execute(stmt)
            affected += result.rowcount or 0
        self.db_session.flush()
        return affected


class TelemetryDeviceRollupCRUD(BaseCRUD):
    """Idempotent upsert for per-device interval rollups."""

    def __init__(self, db_session: Session):
        super().__init__(model=TelemetryDeviceIntervalRollup, db_session=db_session)

    def upsert_rollups(self, rows: list[dict]) -> int:
        """Upsert on ``uq_telemetry_device_rollup``. Never deletes."""
        if not rows:
            return 0
        affected = 0
        for start in range(0, len(rows), _UPSERT_CHUNK_SIZE):
            chunk = rows[start : start + _UPSERT_CHUNK_SIZE]
            stmt = pg_insert(TelemetryDeviceIntervalRollup).values(chunk)
            stmt = stmt.on_conflict_do_update(
                constraint="uq_telemetry_device_rollup",
                set_={
                    "site_id": stmt.excluded.site_id,
                    "company_id": stmt.excluded.company_id,
                    "agg": stmt.excluded.agg,
                    "value": stmt.excluded.value,
                    "unit": stmt.excluded.unit,
                    "sample_count": stmt.excluded.sample_count,
                    "completeness": stmt.excluded.completeness,
                    "calculated_at": stmt.excluded.calculated_at,
                },
            )
            result = self.db_session.execute(stmt)
            affected += result.rowcount or 0
        self.db_session.flush()
        return affected
