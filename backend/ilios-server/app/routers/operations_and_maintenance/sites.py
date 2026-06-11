"""Sites related endpoint serves O&M (Operations and Maintenance, previously - Production monitoring) module"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from humanize import precisedelta
from sqlalchemy.orm import Session

from app.crud.alert import AlertCRUD
from app.crud.device import DeviceCRUD
from app.db.session import get_session
from app.helpers.alert_helper import get_alerts_overview
from app.helpers.authorization import AuthorizedUser, OnMPermissions
from app.helpers.authorization.project_access import get_authorized_site
from app.helpers.device_helper import TELEMETRY_DEVICES_CATEGORIES, get_devices_last_reported, get_site_devices_info
from app.helpers.pagination import pagination_details
from app.helpers.query_params_validator import validate_skip_and_limit
from app.helpers.telemetry.bigquery import TelemetryDeviceBigQuery, TelemetrySiteBigQuery
from app.helpers.telemetry.legacy_flag import legacy_telemetry_enabled
from app.helpers.telemetry.sites_helper import get_production_chart_data_per_site
from app.helpers.telemetry.v2_chart_data import (
    apply_v2_actual_production,
    build_actual_vs_expected_section,
    build_past_performance_section,
    build_v2_inverter_tiles,
    site_has_v2_rollups,
)
from app.models.device import DeviceCategories
from app.models.site import Site
from app.schema.om_device import OMDeviceListPaginator
from app.schema.om_site import (
    OMSiteDeviceDashboardDataList,
    OMSiteInvertersPerformanceListSchema,
    OMSitePastPerformanceSchema,
    OMSiteSchema,
    SiteActualVSExpectedPerformanceListSchema,
    SiteDashboardActualProductionSection,
)
from app.static import DEFAULT_PAGINATION_LIMIT, DEFAULT_PAGINATION_SKIP, HTTP_404_RESPONSE, PermissionsActions
from app.static.alerts import AssetType

logger = logging.getLogger(__name__)
om_sites_router = APIRouter()


# TODO periodically check usage, potentially can be deleted, but FE still makes calls to this API
@om_sites_router.get(
    "/{site_id}",
    response_model=OMSiteSchema,
    responses={**HTTP_404_RESPONSE},
    dependencies=[Depends(AuthorizedUser(OnMPermissions(PermissionsActions.view)))],
)
async def get_by_id(
    site: Site = Depends(get_authorized_site),
):
    return site


@om_sites_router.get(
    "/{site_id}/devices",
    response_model=OMDeviceListPaginator,
    dependencies=[Depends(validate_skip_and_limit), Depends(AuthorizedUser(OnMPermissions(PermissionsActions.view)))],
)
async def get_site_devices(
    skip: int = DEFAULT_PAGINATION_SKIP,
    limit: int = DEFAULT_PAGINATION_LIMIT,
    *,
    site: Site = Depends(get_authorized_site),
    db_session: Session = Depends(get_session),
):
    total, devices = DeviceCRUD(db_session).get_site_devices(
        site.id,
        skip=skip,
        limit=limit,
    )
    devices_alerts = AlertCRUD(db_session).get_device_alerts_overview({device.id for device in devices})
    telemetry_devices_data = get_devices_last_reported(devices)
    # extend devices with additional info
    for device in devices:
        device.alerts_overview = get_alerts_overview(device.id, devices_alerts, AssetType.device)
        # define last reported as relative time when telemetry info was received for the device
        # - for mapped Inverter, Module and Weather station it's time,
        # - for non-mapped Inverter, Module and Weather station it's empty,
        # - for other devices it's N/A
        last_reported = None
        if device.category not in TELEMETRY_DEVICES_CATEGORIES:
            last_reported = "N/A"
        else:
            if not device.telemetry_mapping:
                continue
            last_reported_record = [item for item in telemetry_devices_data if item["device_id"] == device.id]
            if last_reported_record:
                last_reported_ts = last_reported_record[0]["device_last_report_ts"]
                last_reported_diff = datetime.now(timezone.utc).replace(tzinfo=None) - last_reported_ts
                # special handling for long response time
                if last_reported_diff.days >= 1:
                    last_reported = "more than 24 hours"
                else:
                    # transform diff into human-friendly relative time with minimum unit as integer minute
                    last_reported = precisedelta(last_reported_diff, minimum_unit="minutes", format="%0.0f")
        device.last_reported = last_reported

    return {"items": devices, **pagination_details(skip, limit, total)}


@om_sites_router.get(
    "/{site_id}/actual-production-chart",
    response_model=SiteDashboardActualProductionSection,
    responses={**HTTP_404_RESPONSE},
    description="Returns site actual dashboard chart with data received from telemetry",
)
async def get_actual_production_chart(
    site: Site = Depends(get_authorized_site),
    db_session: Session = Depends(get_session),
):
    # V2-first precedence: if the site has any V2 rollups, render from PostgreSQL
    # and never touch BigQuery (even if today's window is empty).
    if site_has_v2_rollups(db_session, site.id):
        apply_v2_actual_production(db_session, site)
        return site
    # Legacy (non-V2) site. The actual+expected series comes only from BigQuery;
    # gated behind the legacy flag (off by default). When off, report an honest
    # no-baseline/no-data section (None, never a fabricated 0).
    if not legacy_telemetry_enabled():
        site.expected_baseline_available = False
        site.actual_kw = None
        site.expected_kw = None
        site.cumulative_actual_kw = None
        site.cumulative_expected_kw = None
        return site
    # Legacy BigQuery path: it supplies an expected baseline, so keep the flag
    # True. Wrapped so BQ unavailability yields an empty chart instead of a 500.
    site.expected_baseline_available = True
    try:
        telemetry_details = get_production_chart_data_per_site(site.id)
        site.actual_kw, site.expected_kw, site.cumulative_actual_kw, site.cumulative_expected_kw = (
            telemetry_details.actual_kw,
            telemetry_details.expected_kw,
            telemetry_details.cumulative_actual_kw,
            telemetry_details.cumulative_expected_kw,
        )
    except Exception:  # noqa: BLE001
        logger.exception("om_actual_production_chart_bigquery_failed site_id=%s", site.id)
        site.actual_kw = 0.0
        site.expected_kw = 0.0
        site.cumulative_actual_kw = 0.0
        site.cumulative_expected_kw = 0.0
    return site


@om_sites_router.get(
    "/{site_id}/inverters-performance-chart",
    response_model=OMSiteInvertersPerformanceListSchema,
    responses={**HTTP_404_RESPONSE},
    description="Returns inverters performance chart as combination of data received from telemetry and DB info",
)
async def get_inverters_performance_chart(
    site: Site = Depends(get_authorized_site),
    db_session: Session = Depends(get_session),
):
    # filter only inverter devices
    site_inverters = [device for device in site.devices if device.category == DeviceCategories.inverter]
    # V2-first precedence: render each tile's actual from the V2 device rollups
    # with a neutral status (no per-device baseline). Never touch BigQuery.
    if site_has_v2_rollups(db_session, site.id):
        return {"data": build_v2_inverter_tiles(db_session, site_inverters)}
    # Legacy (non-V2) site. Inverter-level performance has no V2 equivalent (no
    # per-device projection) and comes only from BigQuery; gated behind the legacy
    # flag (off by default). When off, every inverter degrades to honest "N/A".
    legacy_enabled = legacy_telemetry_enabled()
    # make calls only for mapped inverters with active connection to reduce BQ interactions
    mapped_inverters_ids = [device.id for device in site_inverters if device.das_connection_active]
    telemetry_devices_data = None
    if legacy_enabled and mapped_inverters_ids:
        try:
            telemetry_devices_data = TelemetryDeviceBigQuery().get_devices_performance(mapped_inverters_ids)
        except Exception:  # noqa: BLE001
            logger.exception("om_inverters_performance_chart_bigquery_failed site_id=%s", site.id)
            telemetry_devices_data = None
    response = []
    # build response object accounting mapping status and telemetry response
    for device in site_inverters:
        # create default response object, with 0 performance
        device_response_obj = {"name": device.name, "performance": 0}
        response.append(device_response_obj)
        # return performance as N/A if device isn't mapped, or when legacy
        # telemetry is disabled (no V2 inverter-level source exists)
        if not device.das_connection_active or not legacy_enabled:
            device_response_obj["performance"] = "N/A"
            device_response_obj["actual"] = "N/A"
            device_response_obj["expected"] = "N/A"
            continue
        # find telemetry value for the mapped devices
        telemetry_performance_item_search_results = [
            telemetry_device
            for telemetry_device in (telemetry_devices_data or [])
            if telemetry_device["device_id"] == device.id
        ]
        if telemetry_performance_item_search_results:
            telemetry_performance_item = telemetry_performance_item_search_results[0]
            device_response_obj["performance"] = telemetry_performance_item["performance"]
            device_response_obj["actual"] = telemetry_performance_item["actual"]
            device_response_obj["expected"] = telemetry_performance_item["expected"]
    return {"data": response}


@om_sites_router.get(
    "/{site_id}/past-performance-chart",
    response_model=OMSitePastPerformanceSchema,
    responses={**HTTP_404_RESPONSE},
    description="Returns site past performance chart with data received from telemetry",
)
async def get_site_past_performance_chart(
    site: Site = Depends(get_authorized_site),
    db_session: Session = Depends(get_session),
):
    # V2-first precedence: daily past-performance is an actual-vs-expected ratio
    # built from the native baseline calc (empty + no-baseline flag when the site
    # has no active baseline). Never falls back to stale BigQuery.
    if site_has_v2_rollups(db_session, site.id):
        return build_past_performance_section(db_session, site)
    # Legacy (non-V2) site: past performance comes only from BigQuery; gated
    # behind the legacy flag (off by default). When off, honest empty + no baseline.
    if not legacy_telemetry_enabled():
        return {"data": {}, "expected_baseline_available": False}
    # Legacy BigQuery path (supplies an expected baseline); wrap so BQ
    # unavailability yields an empty chart instead of a 500.
    try:
        return {
            "data": TelemetrySiteBigQuery().get_site_past_performance(site.id),
            "expected_baseline_available": True,
        }
    except Exception:  # noqa: BLE001
        logger.exception("om_past_performance_chart_bigquery_failed site_id=%s", site.id)
        return {"data": {}, "expected_baseline_available": True}


@om_sites_router.get(
    "/{site_id}/actual-vs-expected-chart",
    response_model=SiteActualVSExpectedPerformanceListSchema,
    responses={**HTTP_404_RESPONSE},
    description="Returns site actual vs expected chart with data received from telemetry",
)
async def get_site_actual_vs_expected_chart(
    site: Site = Depends(get_authorized_site),
    db_session: Session = Depends(get_session),
):
    # V2-first precedence: render actual power + irradiance from PostgreSQL
    # rollups, overlaying the expected line from the native baseline calc when an
    # active baseline exists (else expected is null and the section is flagged
    # no-baseline). Never falls back to stale BigQuery.
    if site_has_v2_rollups(db_session, site.id):
        return build_actual_vs_expected_section(db_session, site)
    # Legacy (non-V2) site: the actual-vs-expected series comes only from BigQuery;
    # gated behind the legacy flag (off by default). When off, honest empty + no baseline.
    if not legacy_telemetry_enabled():
        return {"data": [], "expected_baseline_available": False}
    # Legacy BigQuery path (supplies an expected series); wrap so BQ
    # unavailability yields an empty chart.
    try:
        return {
            "data": TelemetrySiteBigQuery().get_site_actual_vs_expected_irradiance(site.id),
            "expected_baseline_available": True,
        }
    except Exception:  # noqa: BLE001
        logger.exception("om_actual_vs_expected_chart_bigquery_failed site_id=%s", site.id)
        return {"data": [], "expected_baseline_available": True}


@om_sites_router.get(
    "/{site_id}/devices-overview-section",
    response_model=OMSiteDeviceDashboardDataList,
    responses={**HTTP_404_RESPONSE},
    description="Return statistics by devices of the site",
)
async def get_site_devices_overview_section(
    site: Site = Depends(get_authorized_site),
    db_session: Session = Depends(get_session),
):
    return {"data": get_site_devices_info(site, db_session)}
