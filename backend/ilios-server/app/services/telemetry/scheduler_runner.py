"""In-process scheduler runner for native V2 telemetry.

Automates the *same* ingestion + rollup pipeline as the manual Refresh Telemetry
action. The scheduler is only a new trigger: it calls ``run_site_refresh(...,
trigger=scheduled)`` followed by bucket-aligned rollups, exactly like the manual
endpoint, and never touches the legacy GCP/BigQuery/Firestore path.

Concurrency model
-----------------
A single daemon thread polls ``telemetry_scheduler_state`` for due rows and
claims each with an atomic DB lease (:meth:`TelemetrySchedulerStateCRUD.claim`).
The claim is the entire overlap guard: across uvicorn ``--reload`` restarts and
multiple workers, at most one run executes per (site, provider account). A
crashed run's lease self-expires after ``LEASE_SECONDS`` so the row is
reclaimable without manual intervention. The services are fully synchronous, so
a plain daemon thread (not asyncio) keeps the bridge trivial and gives a clean,
join-able shutdown.

Cursor contract
---------------
``last_successful_pull_at`` advances ONLY when the readings upsert succeeds AND
the rollup succeeds/skips. On partial/failed/config_error it is left unchanged
so the next run resumes the same gap; idempotent upserts make the overlap free.
"""
from __future__ import annotations

import logging
import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from app.crud.telemetry_native import TelemetrySchedulerStateCRUD
from app.db.session import SessionFactory
from app.integrations.telemetry.credential_store import (
    CredentialStore,
    get_credential_store,
    is_credential_store_durable,
)
from app.models.telemetry import TelemetrySyncStatus, TelemetrySyncTrigger
from app.services.telemetry.ingestion_service import (
    IngestionConfigError,
    IngestionSummary,
    run_site_refresh,
)
from app.services.telemetry.rollup_service import RollupSummary, run_rollups_for_window
from app.settings import settings

logger = logging.getLogger(__name__)

# Cadence whitelist (ISO-8601 duration -> seconds). No ISO parser dependency; the
# PUT endpoint validates against ALLOWED_CADENCES.
CADENCE_TO_SECONDS: dict[str, int] = {
    "PT15M": 15 * 60,
    "PT30M": 30 * 60,
    "PT1H": 60 * 60,
    "PT6H": 6 * 60 * 60,
    "PT24H": 24 * 60 * 60,
}
ALLOWED_CADENCES: frozenset[str] = frozenset(CADENCE_TO_SECONDS)
DEFAULT_CADENCE = "PT1H"

# How often the poll loop wakes to look for due rows.
POLL_INTERVAL_SECONDS = 60
# Lease length for a claimed row. Must comfortably exceed a single run; a crash
# self-heals once it expires.
LEASE_SECONDS = 600
# Hard clamp on a single scheduled pull window so a long-disabled site cannot
# trigger an unbounded catch-up pull. Matches the manual refresh clamp.
MAX_SCHEDULED_WINDOW = timedelta(hours=24)

# Bucket-alignment granularity for rollups (largest bucket the pipeline writes).
_ROLLUP_BUCKET = timedelta(hours=1)
_EPOCH = datetime(1970, 1, 1)

# Mirror the router's production detection without importing it (avoids a circular
# import: the router imports services, not the other way round).
_PROD_LIKE_ENV_NAMES = {"production", "prod", "staging", "stage", "live"}


def cadence_to_timedelta(cadence: str) -> timedelta:
    seconds = CADENCE_TO_SECONDS.get(cadence, CADENCE_TO_SECONDS[DEFAULT_CADENCE])
    return timedelta(seconds=seconds)


def floor_to_hour(ts: datetime) -> datetime:
    """Floor ``ts`` to the top of its hour, epoch-anchored (matches rollups)."""
    secs = _ROLLUP_BUCKET.total_seconds()
    elapsed = (ts - _EPOCH).total_seconds()
    return _EPOCH + timedelta(seconds=(elapsed // secs) * secs)


def compute_scheduled_window(
    *,
    now: datetime,
    last_successful_pull_at: Optional[datetime],
    cadence: str,
) -> tuple[datetime, datetime]:
    """Resolve the readings window for a scheduled pull.

    ``end = now``; ``start = last_successful_pull_at`` if set else
    ``now - cadence``; the span is clamped to ``MAX_SCHEDULED_WINDOW``.
    """
    window_end = now
    if last_successful_pull_at is not None:
        window_start = last_successful_pull_at
    else:
        window_start = now - cadence_to_timedelta(cadence)
    if window_start >= window_end:
        # Defensive: a future cursor (clock skew) -> pull one cadence's worth.
        window_start = window_end - cadence_to_timedelta(cadence)
    if window_end - window_start > MAX_SCHEDULED_WINDOW:
        window_start = window_end - MAX_SCHEDULED_WINDOW
    return window_start, window_end


@dataclass
class IngestionRunResult:
    summary: IngestionSummary
    rollup: RollupSummary


def run_ingestion_with_rollup(
    db: Session,
    *,
    site_id: int,
    window_start: datetime,
    window_end: datetime,
    trigger: TelemetrySyncTrigger,
    triggered_by_user_id: Optional[int] = None,
    credential_store: Optional[CredentialStore] = None,
) -> IngestionRunResult:
    """Run the shared ingestion + bucket-aligned rollup pipeline.

    CRITICAL: the rollup window's start is floored to the hour so a mid-bucket
    ``window_start`` cannot recompute (and corrupt) the boundary bucket from only
    the new window's readings. ``run_rollups_for_window`` re-scans the full
    boundary hour from already-persisted readings; its upserts are idempotent, so
    the recomputed boundary value is stable across adjacent windows.

    Raises :class:`IngestionConfigError` (no job row created) when preconditions
    are missing; callers translate that into the right status / HTTP code.
    """
    summary = run_site_refresh(
        db,
        site_id=site_id,
        window_start=window_start,
        window_end=window_end,
        triggered_by_user_id=triggered_by_user_id,
        credential_store=credential_store,
        trigger=trigger,
    )
    rollup = run_rollups_for_window(
        db,
        site_id=site_id,
        company_id=summary.company_id,
        window_start=floor_to_hour(window_start),
        window_end=window_end,
        bucket_sizes=("1h",),
        sync_job_id=summary.sync_job_id,
    )
    return IngestionRunResult(summary=summary, rollup=rollup)


def cursor_should_advance(summary: IngestionSummary, rollup: RollupSummary) -> bool:
    """True only when both the readings upsert and the rollup are clean.

    ``succeeded`` (no per-target failures) AND rollup ``succeeded``/``skipped``.
    ``partial`` never advances the cursor.
    """
    return (
        summary.status == TelemetrySyncStatus.succeeded
        and rollup.status in ("succeeded", "skipped")
    )


def scheduler_should_run() -> tuple[bool, str]:
    """Gate for starting the runner. Returns ``(should_run, reason)``."""
    if not getattr(settings, "telemetry_scheduler_enabled", False):
        return False, "telemetry_scheduler_enabled is false"
    if not getattr(settings, "telemetry_v2_enabled", False):
        return False, "telemetry_v2_enabled is false"
    env = (settings.environment_name or "").strip().lower()
    if env in _PROD_LIKE_ENV_NAMES and not is_credential_store_durable(
        get_credential_store()
    ):
        return False, "credential store is not durable in production"
    return True, "enabled"


class TelemetrySchedulerRunner:
    """Daemon-thread poll loop that claims and runs due scheduler rows."""

    def __init__(
        self,
        *,
        poll_interval_seconds: int = POLL_INTERVAL_SECONDS,
        lease_seconds: int = LEASE_SECONDS,
    ) -> None:
        self._poll_interval = poll_interval_seconds
        self._lease_seconds = lease_seconds
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    @staticmethod
    def _new_token() -> str:
        return secrets.token_hex(16)

    def start(self) -> None:
        if self._thread is not None and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, name="telemetry-scheduler", daemon=True
        )
        self._thread.start()
        logger.info(
            "telemetry_scheduler_started poll=%ss lease=%ss",
            self._poll_interval,
            self._lease_seconds,
        )

    def stop(self, timeout: float = 10.0) -> None:
        self._stop.set()
        thread = self._thread
        if thread is not None:
            thread.join(timeout=timeout)
        self._thread = None
        logger.info("telemetry_scheduler_stopped")

    # -- internals ---------------------------------------------------------

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._tick()
            except Exception:  # noqa: BLE001 — a tick failure must not kill the loop
                logger.exception("telemetry_scheduler_tick_failed")
            # Sleep until the next poll, waking immediately on shutdown.
            self._stop.wait(self._poll_interval)

    def _tick(self) -> None:
        session = SessionFactory()
        try:
            due_ids = [s.id for s in TelemetrySchedulerStateCRUD(session).list_due()]
        finally:
            session.close()
        for state_id in due_ids:
            if self._stop.is_set():
                break
            self._claim_and_run(state_id)

    def _claim_and_run(self, state_id: int) -> None:
        token = self._new_token()
        # Claim in its own short transaction, committed before any provider work.
        claim_session = SessionFactory()
        try:
            claimed = TelemetrySchedulerStateCRUD(claim_session).claim(
                state_id,
                token=token,
                lease_seconds=self._lease_seconds,
                require_enabled=True,
            )
        finally:
            claim_session.close()
        if not claimed:
            return  # another worker won, or the row was disabled in between
        self._execute(state_id, token)

    def _execute(self, state_id: int, token: str) -> None:
        now = datetime.utcnow()
        session = SessionFactory()
        try:
            crud = TelemetrySchedulerStateCRUD(session)
            state = crud.get_by_id(state_id)
            if state is None:
                return
            cadence = state.cadence or DEFAULT_CADENCE
            next_due_at = now + cadence_to_timedelta(cadence)
            window_start, window_end = compute_scheduled_window(
                now=now,
                last_successful_pull_at=state.last_successful_pull_at,
                cadence=cadence,
            )
            try:
                result = run_ingestion_with_rollup(
                    session,
                    site_id=state.site_id,
                    window_start=window_start,
                    window_end=window_end,
                    trigger=TelemetrySyncTrigger.scheduled,
                )
            except IngestionConfigError as exc:
                crud.finish_run(
                    state_id,
                    token=token,
                    last_run_at=now,
                    last_status="config_error",
                    last_error=exc.detail,
                    next_due_at=next_due_at,
                )
                logger.warning(
                    "telemetry_scheduler_config_error site_id=%s detail=%s",
                    state.site_id,
                    exc.detail,
                )
                return

            summary = result.summary
            rollup = result.rollup
            advance = cursor_should_advance(summary, rollup)
            cursor_kwargs = (
                {"last_successful_pull_at": window_end} if advance else {}
            )
            crud.finish_run(
                state_id,
                token=token,
                last_run_at=now,
                last_status=summary.status.value,
                last_error=summary.error,
                last_sync_job_id=summary.sync_job_id,
                next_due_at=next_due_at,
                **cursor_kwargs,
            )
            logger.info(
                "telemetry_scheduler_run site_id=%s job_id=%s status=%s rollup=%s "
                "received=%s written=%s cursor_advanced=%s",
                state.site_id,
                summary.sync_job_id,
                summary.status.value,
                rollup.status,
                summary.readings_received,
                summary.readings_written,
                advance,
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "telemetry_scheduler_execute_failed state_id=%s", state_id
            )
            self._release_after_error(state_id, token)
        finally:
            session.close()

    def _release_after_error(self, state_id: int, token: str) -> None:
        """Release the lock after an unexpected error so the row isn't stuck.

        Uses a fresh session because the run's session may be in a broken
        transaction. Token-guarded, so it no-ops if the lease was already
        re-claimed elsewhere.
        """
        now = datetime.utcnow()
        rel = SessionFactory()
        try:
            TelemetrySchedulerStateCRUD(rel).finish_run(
                state_id,
                token=token,
                last_run_at=now,
                last_status="failed",
                last_error="scheduler run error (see logs)",
                next_due_at=now + timedelta(seconds=self._poll_interval),
            )
        except Exception:  # noqa: BLE001
            logger.exception(
                "telemetry_scheduler_release_failed state_id=%s", state_id
            )
        finally:
            rel.close()
