"""
Demo telemetry data generator for projects under demo companies.

Activated by setting DEMO_TELEMETRY=true env var (auto-disabled in production).
Generates realistic solar production data using a bell-curve model with seasonal
and weather variation, plus injected demo events (inverter outage, clipping,
severe weather, degradation). Bypasses BigQuery entirely.

Cleanup steps to remove demo telemetry:
  1. Delete env var:  DEMO_TELEMETRY
  2. Run cleanup script:
     cd backend/ilios-server && python scripts/seed_demo_telemetry.py --cleanup
  This removes all demo devices, DAS connection, site mapping, and device
  mappings for demo sites.
"""
import logging
import math
import os
import random
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

_demo_site_ids_cache = None
_demo_device_ids_cache = None
_demo_site_capacities_cache = None


def _load_demo_site_ids():
    global _demo_site_ids_cache, _demo_site_capacities_cache
    if _demo_site_ids_cache is not None:
        return
    try:
        from sqlalchemy import text
        from app.db.session import SessionFactory
        db = SessionFactory()
        rows = db.execute(text(
            "SELECT s.id, s.system_size_dc "
            "FROM sites s "
            "JOIN companies c ON c.id = s.company_id "
            "WHERE c.is_demo = true AND s.is_archived = false"
        )).fetchall()
        _demo_site_ids_cache = frozenset(r[0] for r in rows)
        _demo_site_capacities_cache = {}
        for r in rows:
            raw = r[1] if r[1] and float(r[1]) > 0 else 500
            cap_kw = float(raw) * 1000 if float(raw) < 100 else float(raw)
            _demo_site_capacities_cache[r[0]] = cap_kw
        db.close()
    except Exception as e:
        logger.warning(f"Could not load demo site IDs: {e}")
        _demo_site_ids_cache = frozenset()
        _demo_site_capacities_cache = {}


def _get_demo_device_ids():
    global _demo_device_ids_cache
    if _demo_device_ids_cache is not None:
        return _demo_device_ids_cache
    _load_demo_site_ids()
    if not _demo_site_ids_cache:
        _demo_device_ids_cache = frozenset()
        return _demo_device_ids_cache
    try:
        from sqlalchemy import text
        from app.db.session import SessionFactory
        db = SessionFactory()
        placeholders = ",".join(str(sid) for sid in _demo_site_ids_cache)
        result = db.execute(text(
            f"SELECT d.id FROM devices d "
            f"JOIN telemetry_devices_mapping tm ON tm.device_id = d.id "
            f"WHERE d.site_id IN ({placeholders})"
        ))
        _demo_device_ids_cache = frozenset(r[0] for r in result.fetchall())
        db.close()
    except Exception as e:
        logger.warning(f"Could not load demo device IDs: {e}")
        _demo_device_ids_cache = frozenset()
    return _demo_device_ids_cache


def _get_site_capacity(site_id):
    _load_demo_site_ids()
    if _demo_site_capacities_cache:
        return _demo_site_capacities_cache.get(int(site_id), 500.0)
    return 500.0


def is_demo_site(site_id):
    _load_demo_site_ids()
    return int(site_id) in _demo_site_ids_cache


def is_demo_device(device_id):
    return int(device_id) in _get_demo_device_ids()


def is_demo_mode():
    if os.environ.get("DEMO_TELEMETRY", "").lower() not in ("true", "1", "yes"):
        return False
    env_name = os.environ.get("ENVIRONMENT", os.environ.get("environment_name", "development"))
    if env_name and env_name.lower() == "production":
        return False
    return True


DEMO_EVENTS = {
    "inverter_outage": {
        "month": 8, "day": 12, "start_hour": 10, "end_hour": 14,
        "multiplier": 0.0,
    },
    "clipping": {
        "month": 6, "days": [15, 16, 17, 18, 19, 20],
        "start_hour": 11, "end_hour": 14,
        "max_fraction": 0.78,
    },
    "severe_weather": {
        "month": 10, "day": 5,
        "multiplier": 0.12,
    },
    "intermittent_fault": {
        "month": 3, "day": 22,
        "fault_hours": [9, 10, 13, 14],
        "multiplier": 0.3,
    },
}


def _degradation_factor(dt, commissioning_year=2024):
    years_since = max(0, (dt.year - commissioning_year) + (dt.timetuple().tm_yday / 365.0))
    annual_degradation = 0.015
    return max(0.85, 1.0 - annual_degradation * years_since)


def _apply_demo_events(dt, actual_kw, expected_kw, site_id):
    seed_shift = site_id % 5

    evt = DEMO_EVENTS["inverter_outage"]
    adjusted_day = evt["day"] + seed_shift
    if dt.month == evt["month"] and dt.day == adjusted_day:
        if evt["start_hour"] <= dt.hour < evt["end_hour"]:
            return actual_kw * evt["multiplier"], expected_kw

    evt = DEMO_EVENTS["clipping"]
    adjusted_days = [d + seed_shift for d in evt["days"]]
    if dt.month == evt["month"] and dt.day in adjusted_days:
        if evt["start_hour"] <= dt.hour < evt["end_hour"]:
            cap = _get_site_capacity(site_id) * evt["max_fraction"]
            return min(actual_kw, cap), expected_kw

    evt = DEMO_EVENTS["severe_weather"]
    adjusted_day = evt["day"] + seed_shift
    if dt.month == evt["month"] and dt.day == adjusted_day:
        return actual_kw * evt["multiplier"], expected_kw

    evt = DEMO_EVENTS["intermittent_fault"]
    adjusted_day = evt["day"] + seed_shift
    if dt.month == evt["month"] and dt.day == adjusted_day:
        if dt.hour in evt["fault_hours"]:
            return actual_kw * evt["multiplier"], expected_kw

    return actual_kw, expected_kw


def _solar_power(dt, capacity_kw=500, seed_offset=0):
    rng = random.Random(dt.year * 10000 + dt.month * 100 + dt.day + seed_offset)

    day_of_year = dt.timetuple().tm_yday
    seasonal_factor = 0.5 + 0.5 * math.sin(2 * math.pi * (day_of_year - 80) / 365)

    sunrise = 6.0 - seasonal_factor
    sunset = 18.0 + 2 * seasonal_factor

    hour = dt.hour + dt.minute / 60.0
    if hour < sunrise or hour > sunset:
        return 0.0, 0.0, 0.0

    solar_position = math.sin(math.pi * (hour - sunrise) / (sunset - sunrise))
    solar_position = max(0, solar_position)

    peak_irradiance = 600 + 400 * seasonal_factor
    irradiance = peak_irradiance * solar_position

    expected_kw = capacity_kw * solar_position * (0.7 + 0.3 * seasonal_factor)

    weather_rng = random.Random(dt.year * 10000 + dt.month * 100 + dt.day + seed_offset + 42)
    cloud_cover = weather_rng.gauss(0.93, 0.08)
    cloud_cover = max(0.4, min(1.05, cloud_cover))

    if weather_rng.random() < 0.15:
        cloud_cover *= random.Random(
            dt.year * 10000 + dt.month * 100 + dt.day + dt.hour + seed_offset + 99
        ).uniform(0.6, 0.9)

    noise_rng = random.Random(
        dt.year * 10000 + dt.month * 100 + dt.day + dt.hour * 60 + dt.minute + seed_offset
    )
    noise = noise_rng.gauss(1.0, 0.03)
    actual_kw = expected_kw * cloud_cover * noise
    actual_kw = max(0, actual_kw)

    degradation = _degradation_factor(dt)
    actual_kw *= degradation

    actual_kw, expected_kw = _apply_demo_events(dt, actual_kw, expected_kw, seed_offset)

    return round(actual_kw, 2), round(expected_kw, 2), round(irradiance, 2)


def _daily_energy(date, capacity_kw=500, seed_offset=0):
    actual_total = 0.0
    expected_total = 0.0
    for hour in range(24):
        dt = datetime(date.year, date.month, date.day, hour, 30)
        a, e, _ = _solar_power(dt, capacity_kw, seed_offset)
        actual_total += a
        expected_total += e
    return round(actual_total, 2), round(expected_total, 2)


def _parse_dt(s):
    import re
    raw = str(s)
    raw = re.sub(r"[+-]\d{2}:\d{2}$", "", raw)
    raw = raw.replace("Z", "")
    for fmt in ("%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw.strip(), fmt)
        except ValueError:
            continue
    return datetime.now()


def generate_site_power_actual_vs_expected(site_ids, interval_start, interval_end, timezone):
    dt = _parse_dt(interval_start)
    results = []
    for sid in site_ids:
        cap = _get_site_capacity(sid)
        actual, expected, _ = _solar_power(dt, capacity_kw=cap, seed_offset=sid)
        results.append({
            "site_id": sid,
            "site_power_actual": [{"ts": str(interval_start), "value": actual}],
            "site_power_expected": [{"ts": str(interval_start), "value": expected}],
        })
    return results


def generate_site_energy_daily(site_ids, interval_start, interval_end, timezone):
    start_dt = _parse_dt(interval_start)
    end_dt = _parse_dt(interval_end)
    num_days = max(1, (end_dt.date() - start_dt.date()).days + 1)
    results = []
    for sid in site_ids:
        cap = _get_site_capacity(sid)
        actual_arr = []
        expected_arr = []
        for day_offset in range(num_days):
            day = (start_dt + timedelta(days=day_offset)).date()
            dt = datetime(day.year, day.month, day.day)
            a, e = _daily_energy(day, capacity_kw=cap, seed_offset=sid)
            ts = dt.strftime("%Y-%m-%dT%H:%M:%S")
            actual_arr.append({"ts": ts, "value": a})
            expected_arr.append({"ts": ts, "value": e})
        results.append({
            "site_id": sid,
            "site_energy_actual": actual_arr,
            "site_energy_expected": expected_arr,
        })
    return results


def generate_site_power_and_irradiance(site_ids, interval_start, interval_end, timezone):
    start_dt = _parse_dt(interval_start)
    end_dt = _parse_dt(interval_end)
    results = []
    for sid in site_ids:
        cap = _get_site_capacity(sid)
        actual_arr = []
        expected_arr = []
        irradiance_arr = []
        current = start_dt
        while current < end_dt:
            a, e, irr = _solar_power(current, capacity_kw=cap, seed_offset=sid)
            ts = current.strftime("%Y-%m-%dT%H:%M:%S")
            actual_arr.append({"ts": ts, "value": a})
            expected_arr.append({"ts": ts, "value": e})
            irradiance_arr.append({"ts": ts, "value": irr})
            current += timedelta(hours=1)
        results.append({
            "site_id": sid,
            "site_power_actual": actual_arr,
            "site_power_expected": expected_arr,
            "site_irradiance": irradiance_arr,
        })
    return results


def generate_device_power(device_ids, interval_start, interval_end, timezone):
    dt = _parse_dt(interval_start)
    num_devices = max(len(device_ids), 1)
    avg_capacity = 500 / num_devices
    results = []
    for did in device_ids:
        actual, expected, _ = _solar_power(dt, capacity_kw=avg_capacity, seed_offset=did)
        results.append({
            "device_id": did,
            "device_power_actual": [{"ts": str(interval_start), "value": actual}],
            "device_power_expected": [{"ts": str(interval_start), "value": expected}],
        })
    return results


def generate_device_last_reported(device_ids, interval_start, interval_end, timezone):
    now = datetime.utcnow()
    results = []
    for did in device_ids:
        rng = random.Random(did + now.hour)
        last_report = now - timedelta(minutes=rng.randint(2, 10))
        results.append({
            "device_id": did,
            "last_report_ts": last_report,
            "device_last_report_ts": last_report,
        })
    return results


def generate_device_availability(device_ids, interval_start, interval_end, timezone):
    results = []
    for did in device_ids:
        rng = random.Random(did + 999)
        mtbf_hours = round(rng.uniform(300, 800), 2)
        mttr_hours = round(rng.uniform(0.5, 4.0), 2)
        results.append({
            "device_id": did,
            "mtbf": mtbf_hours,
            "mttr": mttr_hours,
        })
    return results


_DEMO_GENERATORS = {
    "site_power_actual_vs_expected": generate_site_power_actual_vs_expected,
    "site_energy_actual_vs_expected_daily": generate_site_energy_daily,
    "site_power_actual_vs_expected_and_irradiance": generate_site_power_and_irradiance,
    "device_power_actual_vs_expected": generate_device_power,
    "device_last_report_ts": generate_device_last_reported,
    "device_availability_metrics": generate_device_availability,
}


def get_demo_bq_data(function_name, object_id_name, object_ids, interval_start, interval_end, timezone):
    if object_id_name == "site_id":
        scoped_ids = [oid for oid in object_ids if is_demo_site(oid)]
    elif object_id_name == "device_id":
        scoped_ids = [oid for oid in object_ids if is_demo_device(oid)]
    else:
        scoped_ids = object_ids

    if not scoped_ids:
        return []

    generator = _DEMO_GENERATORS.get(function_name)
    if generator:
        return generator(scoped_ids, interval_start, interval_end, timezone)
    return []


def generate_site_cumulative_data(site_ids, interval_start, interval_end, timezone):
    end_dt = _parse_dt(interval_end)
    results = []
    for sid in site_ids:
        cap = _get_site_capacity(sid)
        today_a, today_e = _daily_energy(end_dt.date(), capacity_kw=cap, seed_offset=sid)

        seven_a, seven_e = 0.0, 0.0
        for d in range(1, 8):
            day = (end_dt - timedelta(days=d)).date()
            a, e = _daily_energy(day, capacity_kw=cap, seed_offset=sid)
            seven_a += a
            seven_e += e

        thirty_a, thirty_e = seven_a, seven_e
        for d in range(8, 31):
            day = (end_dt - timedelta(days=d)).date()
            a, e = _daily_energy(day, capacity_kw=cap, seed_offset=sid)
            thirty_a += a
            thirty_e += e

        results.append({
            "site_id": sid,
            "site_energy_actual_today": round(today_a, 2),
            "site_energy_expected_today": round(today_e, 2),
            "site_energy_actual_last_7_days": round(seven_a, 2),
            "site_energy_expected_last_7_days": round(seven_e, 2),
            "site_energy_actual_last_30_days": round(thirty_a, 2),
            "site_energy_expected_last_30_days": round(thirty_e, 2),
        })
    return results


def generate_company_cumulative_today(site_ids, interval_start, interval_end, timezone):
    end_dt = _parse_dt(interval_end)
    total_a, total_e = 0.0, 0.0
    for sid in site_ids:
        cap = _get_site_capacity(sid)
        a, e = _daily_energy(end_dt.date(), capacity_kw=cap, seed_offset=sid)
        total_a += a
        total_e += e
    return [{
        "company_energy_actual_today": round(total_a, 2),
        "company_energy_expected_today": round(total_e, 2),
    }]
