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

from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy import func, or_, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud.base_crud import BaseCRUD
from app.models.telemetry import (
    TelemetryDeviceIntervalRollup,
    TelemetryReading,
    TelemetrySchedulerState,
    TelemetrySiteIntervalRollup,
    TelemetrySyncJob,
    TelemetrySyncScope,
    TelemetrySyncStatus,
    TelemetrySyncTrigger,
)

# Sentinel so ``finish_run`` can distinguish "leave this column unchanged" from
# "set it to NULL". Scheduled runs always advance ``next_due_at`` and may set the
# cursor; backfill must leave both untouched.
_UNSET: object = object()

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

    def list_for_site(self, site_id: int, *, limit: int = 20) -> list[TelemetrySyncJob]:
        """Most-recent-first ingestion attempts for a site (read-only).

        Used by the V2 read API to surface a "last refreshed"/last-sync-status
        view without inspecting raw readings. Ordered by id desc so the newest
        attempt is first.
        """
        return (
            self.db_session.query(TelemetrySyncJob)
            .filter(TelemetrySyncJob.site_id == site_id)
            .order_by(TelemetrySyncJob.id.desc())
            .limit(limit)
            .all()
        )


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

    def latest_metric_ts(self, site_id: int) -> Optional[datetime]:
        """Newest raw reading timestamp for a site (read-only).

        Drives the "data as of" freshness indicator. Returns None when the site
        has no readings yet.
        """
        return (
            self.db_session.query(func.max(TelemetryReading.metric_ts))
            .filter(TelemetryReading.site_id == site_id)
            .scalar()
        )

    def latest_metric_ts_per_device(self, site_id: int) -> dict[int, datetime]:
        """Newest raw reading timestamp per device for a site (read-only).

        Drives the V2 "not responding" recency check: the freshest reading is a
        better liveness signal than the (laggier) hourly rollups. Only rows with
        a non-null ``device_id`` are considered (site-level metrics are skipped).
        Returns ``{device_id: latest_metric_ts}``; devices with no readings are
        simply absent from the map.
        """
        rows = (
            self.db_session.query(
                TelemetryReading.device_id,
                func.max(TelemetryReading.metric_ts),
            )
            .filter(
                TelemetryReading.site_id == site_id,
                TelemetryReading.device_id.isnot(None),
            )
            .group_by(TelemetryReading.device_id)
            .all()
        )
        return {device_id: latest_ts for device_id, latest_ts in rows}


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

    def has_rollups(self, site_id: int) -> bool:
        """True if ANY site rollup exists for the site (window-agnostic).

        This is the V2-vs-BigQuery precedence switch for O&M charts: presence of
        any rollup means the site is V2-backed, so a chart must read V2 (even if
        the requested window happens to be empty) and never fall back to stale
        BigQuery.
        """
        return (
            self.db_session.query(TelemetrySiteIntervalRollup.id)
            .filter(TelemetrySiteIntervalRollup.site_id == site_id)
            .first()
            is not None
        )

    def get_series(
        self,
        *,
        site_id: int,
        normalized_metric: str,
        bucket_size: str,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> list[TelemetrySiteIntervalRollup]:
        """Ascending site rollup rows for one metric + bucket size (read-only)."""
        query = self.db_session.query(TelemetrySiteIntervalRollup).filter(
            TelemetrySiteIntervalRollup.site_id == site_id,
            TelemetrySiteIntervalRollup.normalized_metric == normalized_metric,
            TelemetrySiteIntervalRollup.bucket_size == bucket_size,
        )
        if start is not None:
            query = query.filter(TelemetrySiteIntervalRollup.bucket_start >= start)
        if end is not None:
            query = query.filter(TelemetrySiteIntervalRollup.bucket_start <= end)
        return query.order_by(TelemetrySiteIntervalRollup.bucket_start.asc()).all()

    def get_latest_per_metric(
        self, site_id: int, *, bucket_size: Optional[str] = None
    ) -> list[TelemetrySiteIntervalRollup]:
        """Latest row per normalized metric for a site (Postgres DISTINCT ON)."""
        query = self.db_session.query(TelemetrySiteIntervalRollup).filter(
            TelemetrySiteIntervalRollup.site_id == site_id
        )
        if bucket_size is not None:
            query = query.filter(TelemetrySiteIntervalRollup.bucket_size == bucket_size)
        return (
            query.distinct(TelemetrySiteIntervalRollup.normalized_metric)
            .order_by(
                TelemetrySiteIntervalRollup.normalized_metric.asc(),
                TelemetrySiteIntervalRollup.bucket_start.desc(),
            )
            .all()
        )

    def latest_bucket_start(self, site_id: int) -> Optional[datetime]:
        """Newest rollup bucket_start for a site, or None."""
        return (
            self.db_session.query(func.max(TelemetrySiteIntervalRollup.bucket_start))
            .filter(TelemetrySiteIntervalRollup.site_id == site_id)
            .scalar()
        )


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

    def get_series(
        self,
        *,
        site_id: int,
        normalized_metric: str,
        bucket_size: str,
        device_id: Optional[int] = None,
        start: Optional[datetime] = None,
        end: Optional[datetime] = None,
    ) -> list[TelemetryDeviceIntervalRollup]:
        """Device rollup rows ordered by device, then bucket_start (read-only).

        Pass ``device_id`` to scope to a single device; otherwise returns every
        mapped device's rows for the metric so the caller can group them.
        """
        query = self.db_session.query(TelemetryDeviceIntervalRollup).filter(
            TelemetryDeviceIntervalRollup.site_id == site_id,
            TelemetryDeviceIntervalRollup.normalized_metric == normalized_metric,
            TelemetryDeviceIntervalRollup.bucket_size == bucket_size,
        )
        if device_id is not None:
            query = query.filter(TelemetryDeviceIntervalRollup.device_id == device_id)
        if start is not None:
            query = query.filter(TelemetryDeviceIntervalRollup.bucket_start >= start)
        if end is not None:
            query = query.filter(TelemetryDeviceIntervalRollup.bucket_start <= end)
        return query.order_by(
            TelemetryDeviceIntervalRollup.device_id.asc(),
            TelemetryDeviceIntervalRollup.bucket_start.asc(),
        ).all()

    def list_device_ids(
        self,
        site_id: int,
        *,
        normalized_metric: Optional[str] = None,
        bucket_size: Optional[str] = None,
    ) -> list[int]:
        """Distinct device ids that have rollups for a site (read-only)."""
        query = self.db_session.query(TelemetryDeviceIntervalRollup.device_id).filter(
            TelemetryDeviceIntervalRollup.site_id == site_id
        )
        if normalized_metric is not None:
            query = query.filter(
                TelemetryDeviceIntervalRollup.normalized_metric == normalized_metric
            )
        if bucket_size is not None:
            query = query.filter(
                TelemetryDeviceIntervalRollup.bucket_size == bucket_size
            )
        return [row[0] for row in query.distinct().all()]

    def get_latest_per_device(
        self, site_id: int, *, normalized_metric: str, bucket_size: str
    ) -> list[TelemetryDeviceIntervalRollup]:
        """Latest rollup row per device for one metric + bucket size (read-only).

        Postgres ``DISTINCT ON (device_id)`` keeping the newest ``bucket_start``
        per device (mirrors :meth:`TelemetrySiteRollupCRUD.get_latest_per_metric`).
        Used to populate the V2 inverter tiles' latest actual value.
        """
        return (
            self.db_session.query(TelemetryDeviceIntervalRollup)
            .filter(
                TelemetryDeviceIntervalRollup.site_id == site_id,
                TelemetryDeviceIntervalRollup.normalized_metric == normalized_metric,
                TelemetryDeviceIntervalRollup.bucket_size == bucket_size,
            )
            .distinct(TelemetryDeviceIntervalRollup.device_id)
            .order_by(
                TelemetryDeviceIntervalRollup.device_id.asc(),
                TelemetryDeviceIntervalRollup.bucket_start.desc(),
            )
            .all()
        )


class TelemetrySchedulerStateCRUD(BaseCRUD):
    """Scheduling/automation state + lease-based overlap lock.

    Shared by the in-process scheduler runner and the bounded backfill endpoint.
    The lock primitive (:meth:`claim` / :meth:`finish_run`) guarantees that at
    most one run executes for a given (site, provider account) at a time, even
    across uvicorn ``--reload`` restarts and multiple workers, because the claim
    is a single atomic conditional UPDATE.
    """

    def __init__(self, db_session: Session):
        super().__init__(model=TelemetrySchedulerState, db_session=db_session)

    def get_by_site_account(
        self, site_id: int, provider_account_id: int
    ) -> Optional[TelemetrySchedulerState]:
        """Fetch the row for an EXACT (site, provider account) pair.

        Control and status reads must always go through here (after resolving the
        site's *current* mapped account) — never a site-only "first row wins"
        selector — so a row left behind by a prior account remap is never treated
        as the live one.
        """
        return (
            self.db_session.query(TelemetrySchedulerState)
            .filter(
                TelemetrySchedulerState.site_id == site_id,
                TelemetrySchedulerState.provider_account_id == provider_account_id,
            )
            .first()
        )

    def index_by_site_account(
        self, site_ids: list[int]
    ) -> dict[tuple[int, int], TelemetrySchedulerState]:
        """Return all rows for the given sites keyed by (site_id, account_id).

        The caller resolves each site's current mapped account and looks up the
        exact pair, so stale rows for prior accounts are simply not matched.
        """
        if not site_ids:
            return {}
        rows = (
            self.db_session.query(TelemetrySchedulerState)
            .filter(TelemetrySchedulerState.site_id.in_(site_ids))
            .all()
        )
        return {(row.site_id, row.provider_account_id): row for row in rows}

    def ensure_state(
        self, *, site_id: int, provider_account_id: int, company_id: int
    ) -> TelemetrySchedulerState:
        """Lazily create a disabled scheduler row if one does not yet exist."""
        state = self.get_by_site_account(site_id, provider_account_id)
        if state is not None:
            return state
        state = TelemetrySchedulerState(
            site_id=site_id,
            provider_account_id=provider_account_id,
            company_id=company_id,
            enabled=False,
            cadence="PT1H",
        )
        self.db_session.add(state)
        try:
            self.db_session.commit()
        except IntegrityError:
            # A concurrent first-time enable/backfill won the unique
            # (site_id, provider_account_id) race; fall back to the row it
            # created instead of surfacing a 500.
            self.db_session.rollback()
            existing = self.get_by_site_account(site_id, provider_account_id)
            if existing is None:
                raise
            return existing
        self.db_session.refresh(state)
        return state

    def upsert_config(
        self,
        *,
        site_id: int,
        provider_account_id: int,
        company_id: int,
        enabled: Optional[bool] = None,
        cadence: Optional[str] = None,
        next_due_at: object = _UNSET,
    ) -> TelemetrySchedulerState:
        """Create-or-update the enable flag / cadence (the PUT path).

        ``next_due_at`` is left untouched unless explicitly provided so callers
        can decide scheduling semantics (e.g. set it to "now" on enable).
        """
        state = self.ensure_state(
            site_id=site_id,
            provider_account_id=provider_account_id,
            company_id=company_id,
        )
        if cadence is not None:
            state.cadence = cadence
        if enabled is not None:
            state.enabled = enabled
        if next_due_at is not _UNSET:
            state.next_due_at = next_due_at  # type: ignore[assignment]
        # One active scheduler per site: disable any sibling rows for this site
        # that belong to a different (stale) provider account. After an account
        # remap this prevents a leftover enabled row from running in parallel
        # with the current account's row (two locks => double execution).
        self.db_session.query(TelemetrySchedulerState).filter(
            TelemetrySchedulerState.site_id == site_id,
            TelemetrySchedulerState.provider_account_id != provider_account_id,
            TelemetrySchedulerState.enabled.is_(True),
        ).update(
            {
                TelemetrySchedulerState.enabled: False,
                TelemetrySchedulerState.updated_at: datetime.utcnow(),
            },
            synchronize_session=False,
        )
        self.db_session.commit()
        self.db_session.refresh(state)
        return state

    def list_due(
        self, *, now: Optional[datetime] = None, limit: int = 50
    ) -> list[TelemetrySchedulerState]:
        """Enabled rows that are due and not currently locked (advisory select).

        The authoritative overlap guard is :meth:`claim`; this is just a cheap
        candidate filter for the poll loop.
        """
        now = now or datetime.utcnow()
        return (
            self.db_session.query(TelemetrySchedulerState)
            .filter(
                TelemetrySchedulerState.enabled.is_(True),
                or_(
                    TelemetrySchedulerState.next_due_at.is_(None),
                    TelemetrySchedulerState.next_due_at <= now,
                ),
                or_(
                    TelemetrySchedulerState.locked_until.is_(None),
                    TelemetrySchedulerState.locked_until < now,
                ),
            )
            .order_by(TelemetrySchedulerState.id.asc())
            .limit(limit)
            .all()
        )

    def claim(
        self,
        state_id: int,
        *,
        token: str,
        lease_seconds: int,
        require_enabled: bool = False,
        now: Optional[datetime] = None,
    ) -> bool:
        """Atomically claim the lock. Returns True only for the single winner.

        The conditional UPDATE (``locked_until IS NULL OR locked_until < now``)
        is the entire overlap-prevention mechanism — two concurrent callers race
        on the same row and exactly one gets ``rowcount == 1``. Committed in its
        own short transaction before any provider work begins.
        """
        now = now or datetime.utcnow()
        lease_until = now + timedelta(seconds=lease_seconds)
        conditions = [
            TelemetrySchedulerState.id == state_id,
            or_(
                TelemetrySchedulerState.locked_until.is_(None),
                TelemetrySchedulerState.locked_until < now,
            ),
        ]
        if require_enabled:
            conditions.append(TelemetrySchedulerState.enabled.is_(True))
        stmt = (
            update(TelemetrySchedulerState)
            .where(*conditions)
            .values(lock_token=token, locked_until=lease_until, updated_at=now)
            .execution_options(synchronize_session=False)
        )
        result = self.db_session.execute(stmt)
        self.db_session.commit()
        return (result.rowcount or 0) == 1

    def finish_run(
        self,
        state_id: int,
        *,
        token: str,
        last_run_at: datetime,
        last_status: str,
        last_error: Optional[str] = None,
        last_sync_job_id: Optional[int] = None,
        next_due_at: object = _UNSET,
        last_successful_pull_at: object = _UNSET,
        enabled: object = _UNSET,
        now: Optional[datetime] = None,
    ) -> bool:
        """Record results and release the lock — but only if we still hold it.

        The ``lock_token == token`` guard means a run whose lease already expired
        (and was re-claimed by another worker) becomes a no-op here, so it can
        never clobber the newer run's cursor or lock. ``next_due_at`` and
        ``last_successful_pull_at`` stay unchanged unless explicitly passed, which
        is how backfill avoids advancing the scheduled cursor or the cadence.
        """
        now = now or datetime.utcnow()
        values: dict = {
            "last_run_at": last_run_at,
            "last_status": last_status,
            "last_error": last_error,
            "lock_token": None,
            "locked_until": None,
            "updated_at": now,
        }
        if last_sync_job_id is not None:
            values["last_sync_job_id"] = last_sync_job_id
        if next_due_at is not _UNSET:
            values["next_due_at"] = next_due_at
        if last_successful_pull_at is not _UNSET:
            values["last_successful_pull_at"] = last_successful_pull_at
        if enabled is not _UNSET:
            values["enabled"] = enabled
        stmt = (
            update(TelemetrySchedulerState)
            .where(
                TelemetrySchedulerState.id == state_id,
                TelemetrySchedulerState.lock_token == token,
            )
            .values(**values)
            .execution_options(synchronize_session=False)
        )
        result = self.db_session.execute(stmt)
        self.db_session.commit()
        return (result.rowcount or 0) == 1
