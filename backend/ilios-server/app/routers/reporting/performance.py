import logging
from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.crud.site import SiteCRUD
from app.db.session import get_session
from app.helpers.authorization import AuthorizedUser
from app.helpers.authorization.module_based.reporting import ReportingPermissions
from app.helpers.telemetry.demo_data import (
    is_demo_mode,
    is_demo_site,
    _get_site_capacity,
    _daily_energy,
    _solar_power,
)
from app.schema.user import CurrentUserSchema
from app.static import PermissionsActions

logger = logging.getLogger(__name__)
performance_report_router = APIRouter()

MAX_DATE_RANGE_DAYS = 400


def _validate_date_param(value: str, param_name: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid {param_name} format. Expected YYYY-MM-DD.",
        )


def _validate_site_access(site_id: int, current_user: CurrentUserSchema, db_session: Session):
    limited_site_ids = current_user.get_limited_sites_ids()
    if limited_site_ids is not None and site_id not in limited_site_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have access to this site.",
        )

    site_crud = SiteCRUD(db_session)
    site = site_crud.get_by_id(site_id)
    if not site:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Site not found.",
        )
    return site


def _generate_daily_report(site_id: int, start: date, end: date):
    capacity_kw = _get_site_capacity(site_id)

    daily_data = []
    current = start
    while current <= end:
        actual_kwh, expected_kwh = _daily_energy(current, capacity_kw=capacity_kw, seed_offset=site_id)
        performance_ratio = round((actual_kwh / expected_kwh * 100), 1) if expected_kwh > 0 else 0
        daily_data.append({
            "date": current.strftime("%Y-%m-%d"),
            "actual_kwh": actual_kwh,
            "expected_kwh": expected_kwh,
            "performance_ratio": performance_ratio,
        })
        current += timedelta(days=1)

    return daily_data


def _compute_monthly_summary(daily_data):
    monthly = {}
    for entry in daily_data:
        month_key = entry["date"][:7]
        if month_key not in monthly:
            monthly[month_key] = {"actual_kwh": 0, "expected_kwh": 0, "days": 0}
        monthly[month_key]["actual_kwh"] += entry["actual_kwh"]
        monthly[month_key]["expected_kwh"] += entry["expected_kwh"]
        monthly[month_key]["days"] += 1

    result = []
    for month_key, vals in sorted(monthly.items()):
        pr = round((vals["actual_kwh"] / vals["expected_kwh"] * 100), 1) if vals["expected_kwh"] > 0 else 0
        result.append({
            "month": month_key,
            "actual_kwh": round(vals["actual_kwh"], 2),
            "expected_kwh": round(vals["expected_kwh"], 2),
            "performance_ratio": pr,
            "days": vals["days"],
        })
    return result


def _compute_summary_metrics(daily_data, capacity_kw):
    if not daily_data:
        return {}

    total_actual = sum(d["actual_kwh"] for d in daily_data)
    total_expected = sum(d["expected_kwh"] for d in daily_data)
    num_days = len(daily_data)
    total_hours = num_days * 24

    performance_ratio = round((total_actual / total_expected * 100), 1) if total_expected > 0 else 0
    capacity_factor = round((total_actual / (capacity_kw * total_hours) * 100), 1) if capacity_kw > 0 and total_hours > 0 else 0
    avg_daily_gen = round(total_actual / num_days, 2) if num_days > 0 else 0

    pr_values = [d["performance_ratio"] for d in daily_data if d["performance_ratio"] > 0]
    availability = round(len(pr_values) / num_days * 100, 1) if num_days > 0 else 0

    return {
        "total_actual_kwh": round(total_actual, 2),
        "total_expected_kwh": round(total_expected, 2),
        "total_actual_mwh": round(total_actual / 1000, 2),
        "total_expected_mwh": round(total_expected / 1000, 2),
        "performance_ratio": performance_ratio,
        "capacity_factor": capacity_factor,
        "avg_daily_generation_kwh": avg_daily_gen,
        "num_days": num_days,
        "system_capacity_kw": round(capacity_kw, 2),
        "availability": availability,
    }


@performance_report_router.get(
    "/{site_id}/performance-report/",
    description="Generate an in-app performance report for a site using telemetry data.",
)
async def get_site_performance_report(
    site_id: int,
    start_date: str = Query(..., description="Start date in YYYY-MM-DD format"),
    end_date: str = Query(..., description="End date in YYYY-MM-DD format"),
    current_user: CurrentUserSchema = Depends(
        AuthorizedUser(ReportingPermissions(PermissionsActions.view))
    ),
    db_session: Session = Depends(get_session),
):
    start = _validate_date_param(start_date, "start_date")
    end = _validate_date_param(end_date, "end_date")

    if start > end:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_date must be on or before end_date.",
        )
    if (end - start).days > MAX_DATE_RANGE_DAYS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Date range cannot exceed {MAX_DATE_RANGE_DAYS} days.",
        )

    site = _validate_site_access(site_id, current_user, db_session)

    if not (is_demo_mode() and is_demo_site(site_id)):
        return {"available": False, "message": "In-app performance report is only available for demo sites."}

    capacity_kw = _get_site_capacity(site_id)
    daily_data = _generate_daily_report(site_id, start, end)
    monthly_summary = _compute_monthly_summary(daily_data)
    summary = _compute_summary_metrics(daily_data, capacity_kw)

    return {
        "available": True,
        "site_id": site_id,
        "site_name": site.name,
        "start_date": start_date,
        "end_date": end_date,
        "summary": summary,
        "daily": daily_data,
        "monthly": monthly_summary,
    }


@performance_report_router.get(
    "/{site_id}/performance-report/check/",
    description="Check if in-app performance report is available for a site.",
)
async def check_performance_report_availability(
    site_id: int,
    current_user: CurrentUserSchema = Depends(
        AuthorizedUser(ReportingPermissions(PermissionsActions.view))
    ),
    db_session: Session = Depends(get_session),
):
    _validate_site_access(site_id, current_user, db_session)
    available = is_demo_mode() and is_demo_site(site_id)
    return {"available": available, "site_id": site_id}
