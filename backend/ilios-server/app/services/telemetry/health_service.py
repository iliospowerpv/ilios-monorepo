"""Shared, read-only telemetry-health computation.

This is the single source of truth for a site's telemetry health verdict. The
``GET /sites/{site_id}/health`` route is a thin wrapper over it, and the V2
performance-context aggregator projects the SAME verdict verbatim (it never
re-derives freshness with its own threshold). Keeping one implementation is what
lets the performance-context ``telemetry_quality.freshness_state`` stay provably
consistent with the health endpoint.

Performs ZERO writes/commits. V2-only precedence is preserved: a site backed by
native V2 ingestion (any PostgreSQL readings or rollups) resolves its health
entirely from PostgreSQL and never calls BigQuery; BigQuery is consulted ONLY for
legacy (non-V2) sites with no native signal at all, and only when the legacy flag
is enabled.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.crud.telemetry_native import (
    TelemetryReadingCRUD,
    TelemetrySchedulerStateCRUD,
)
from app.helpers.telemetry.bigquery.device import TelemetryDeviceBigQuery
from app.helpers.telemetry.legacy_flag import legacy_telemetry_enabled
from app.helpers.telemetry.v2_chart_data import site_has_v2_rollups
from app.models.site import Site
from app.schema.telemetry import TelemetryHealthResponse, TelemetryHealthStatus
from app.services.telemetry.device_classification import drives_expected

logger = logging.getLogger(__name__)


def resolve_expected_interval(
    db_session: Session, site_id: int
) -> tuple[int | None, str]:
    """Expected data interval derived from the site's scheduler cadence.

    Reads ``telemetry_scheduler_state`` so a cadence change is reflected with no
    code change. Resolves the site's CURRENT mapped account first (never a
    site-only "first row wins" lookup), then the exact scheduler row.

    Returns ``(minutes, label)``:
      * no scheduler row            -> ``(None, "Not scheduled")``
      * row present but disabled     -> ``(None, "Manual refresh only")``
      * enabled with known cadence   -> ``(n, "{n} min")``
    """
    # Lazy import: scheduler_runner pulls the ingestion/rollup services, which we
    # do not want at module import time.
    from app.services.telemetry.scheduler_runner import (
        CADENCE_TO_SECONDS,
        resolve_current_account,
    )

    account_id = resolve_current_account(db_session, site_id)
    state = None
    if account_id is not None:
        state = TelemetrySchedulerStateCRUD(db_session).get_by_site_account(
            site_id, account_id
        )
    if state is None:
        return None, "Not scheduled"
    if not state.enabled:
        return None, "Manual refresh only"
    seconds = CADENCE_TO_SECONDS.get(state.cadence)
    if not seconds:
        return None, "Not scheduled"
    minutes = seconds // 60
    return minutes, f"{minutes} min"


def compute_site_telemetry_health(
    db_session: Session, site: Site
) -> TelemetryHealthResponse:
    """Resolve a site's telemetry health (read-only, no writes).

    V2-only precedence: a site backed by native V2 ingestion (any PostgreSQL
    readings or rollups) resolves its health entirely from PostgreSQL and never
    calls BigQuery, so BigQuery can never make a V2 site appear healthier,
    staler, or broken. BigQuery is consulted ONLY for legacy (non-V2) sites that
    have no native signal at all.
    """
    is_connected = site.das_connection is not None
    is_site_mapped = site.telemetry_mapping is not None

    if not is_connected or not is_site_mapped:
        # An unconfigured site has no provider account, hence no scheduler row;
        # skip the cadence lookup and report the unscheduled defaults directly.
        return TelemetryHealthResponse(
            status=TelemetryHealthStatus.not_configured,
            last_data_at=None,
            data_delay_minutes=None,
            last_error=None,
            mapped_device_count=0,
            expected_interval_minutes=None,
            expected_interval_label="Not scheduled",
            is_connected=is_connected,
            is_site_mapped=is_site_mapped,
        )

    # Expected interval is derived from the live scheduler cadence (DB-driven), so
    # a cadence change is reflected with no code change.
    interval_minutes, interval_label = resolve_expected_interval(db_session, site.id)

    # Get mapped devices. Health keys off the STABLE expected-driving set
    # (drives_expected), NOT the broad mappable set — so expanding eligibility to
    # meters/loggers/gateways never changes a site's health status.
    mapped_devices = [
        device
        for device in site.devices
        if device.telemetry_mapping is not None and drives_expected(device)
    ]
    mapped_device_count = len(mapped_devices)

    if mapped_device_count == 0:
        return TelemetryHealthResponse(
            status=TelemetryHealthStatus.no_data,
            last_data_at=None,
            data_delay_minutes=None,
            last_error=None,
            mapped_device_count=0,
            expected_interval_minutes=interval_minutes,
            expected_interval_label=interval_label,
            is_connected=is_connected,
            is_site_mapped=is_site_mapped,
        )

    # Resolve "last data at". Native V2 ingestion (manual refresh + scheduler)
    # writes readings straight to PostgreSQL; the latest native reading IS the
    # last-data signal for a V2 site. Timestamps are normalized to UTC for the
    # delay calculation (native readings are stored naive-UTC).
    last_data_at: datetime | None = None
    bq_error: str | None = None

    v2_last_ts = TelemetryReadingCRUD(db_session).latest_metric_ts(site.id)
    if v2_last_ts is not None and v2_last_ts.tzinfo is None:
        v2_last_ts = v2_last_ts.replace(tzinfo=timezone.utc)

    # A site is "V2-backed" if it has any native readings OR any rollups. Such a
    # site is served from PostgreSQL alone — BigQuery is never called.
    is_v2_backed = v2_last_ts is not None or site_has_v2_rollups(db_session, site.id)

    if is_v2_backed:
        last_data_at = v2_last_ts
    elif legacy_telemetry_enabled():
        # Legacy (non-V2) site: fall back to BigQuery's last-report timestamp. A
        # BigQuery failure is caught and surfaced only because there is no native
        # signal to rely on for this site. Gated behind the legacy flag (off by
        # default) so a decommissioned BigQuery is never queried; when off, a
        # non-V2 site reports an honest no_data state below instead of an error.
        device_ids = [device.id for device in mapped_devices]
        try:
            bq_client = TelemetryDeviceBigQuery()
            site_tz = getattr(site, "timezone", None) or "UTC"
            last_reported_data = bq_client.get_device_last_reported(device_ids, site_tz)
            if last_reported_data:
                for device_data in last_reported_data:
                    if device_data and device_data.get("last_report_ts"):
                        ts = device_data["last_report_ts"]
                        if isinstance(ts, str):
                            ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                        if ts.tzinfo is None:
                            ts = ts.replace(tzinfo=timezone.utc)
                        if last_data_at is None or ts > last_data_at:
                            last_data_at = ts
        except Exception as e:  # noqa: BLE001
            bq_error = str(e)
            logger.warning(
                f"Telemetry health: BigQuery last-report lookup failed: {e}"
            )

    # Calculate health status from the resolved timestamp.
    now = datetime.now(timezone.utc)
    data_delay_minutes = None
    if last_data_at is not None:
        data_delay = now - last_data_at
        data_delay_minutes = int(data_delay.total_seconds() / 60)
        if data_delay_minutes <= 30:
            health_status = TelemetryHealthStatus.healthy
        elif data_delay_minutes <= 120:
            health_status = TelemetryHealthStatus.warn
        else:
            health_status = TelemetryHealthStatus.error
    elif bq_error is not None:
        # Legacy site with no native readings AND BigQuery errored: surface it.
        health_status = TelemetryHealthStatus.error
    else:
        # No data anywhere: an explicit no-data state, not a hidden fallback.
        health_status = TelemetryHealthStatus.no_data

    return TelemetryHealthResponse(
        status=health_status,
        last_data_at=last_data_at,
        data_delay_minutes=data_delay_minutes,
        last_error=bq_error if last_data_at is None else None,
        mapped_device_count=mapped_device_count,
        expected_interval_minutes=interval_minutes,
        expected_interval_label=interval_label,
        is_connected=is_connected,
        is_site_mapped=is_site_mapped,
    )
