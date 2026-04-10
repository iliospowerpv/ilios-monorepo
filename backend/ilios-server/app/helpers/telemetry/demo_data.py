import math
import os
import random
from datetime import datetime, timedelta

DEMO_SITE_ID = 1
SITE_CAPACITY_KW = 500


def is_demo_mode():
    if os.environ.get("DEMO_TELEMETRY", "").lower() not in ("true", "1", "yes"):
        return False
    env_name = os.environ.get("ENVIRONMENT", os.environ.get("environment_name", "development"))
    if env_name and env_name.lower() == "production":
        return False
    return True


def _solar_power(dt, capacity_kw=SITE_CAPACITY_KW, seed_offset=0):
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
    weather = weather_rng.gauss(0.93, 0.08)
    weather = max(0.4, min(1.05, weather))

    noise_rng = random.Random(
        dt.year * 10000 + dt.month * 100 + dt.day + dt.hour * 60 + dt.minute + seed_offset
    )
    noise = noise_rng.gauss(1.0, 0.03)
    actual_kw = expected_kw * weather * noise
    actual_kw = max(0, actual_kw)

    return round(actual_kw, 2), round(expected_kw, 2), round(irradiance, 2)


def _daily_energy(date, capacity_kw=SITE_CAPACITY_KW, seed_offset=0):
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
        actual, expected, _ = _solar_power(dt, seed_offset=sid)
        results.append({
            "site_id": sid,
            "site_power_actual": [{"ts": str(interval_start), "value": actual}],
            "site_power_expected": [{"ts": str(interval_start), "value": expected}],
        })
    return results


def generate_site_energy_daily(site_ids, interval_start, interval_end, timezone):
    end_dt = _parse_dt(interval_end)
    results = []
    for sid in site_ids:
        actual_arr = []
        expected_arr = []
        for day_offset in range(31):
            day = (end_dt - timedelta(days=30 - day_offset)).date()
            dt = datetime(day.year, day.month, day.day)
            a, e = _daily_energy(day, seed_offset=sid)
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
        actual_arr = []
        expected_arr = []
        irradiance_arr = []
        current = start_dt
        while current < end_dt:
            a, e, irr = _solar_power(current, seed_offset=sid)
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
    per_device_capacity = SITE_CAPACITY_KW / num_devices
    results = []
    for did in device_ids:
        actual, expected, _ = _solar_power(dt, capacity_kw=per_device_capacity, seed_offset=did)
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


def get_demo_bq_data(function_name, object_ids, interval_start, interval_end, timezone):
    generator = _DEMO_GENERATORS.get(function_name)
    if generator:
        return generator(object_ids, interval_start, interval_end, timezone)
    return []


def generate_site_cumulative_data(site_ids, interval_start, interval_end, timezone):
    end_dt = _parse_dt(interval_end)
    results = []
    for sid in site_ids:
        today_a, today_e = _daily_energy(end_dt.date(), seed_offset=sid)

        seven_a, seven_e = 0.0, 0.0
        for d in range(1, 8):
            day = (end_dt - timedelta(days=d)).date()
            a, e = _daily_energy(day, seed_offset=sid)
            seven_a += a
            seven_e += e

        thirty_a, thirty_e = seven_a, seven_e
        for d in range(8, 31):
            day = (end_dt - timedelta(days=d)).date()
            a, e = _daily_energy(day, seed_offset=sid)
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
        a, e = _daily_energy(end_dt.date(), seed_offset=sid)
        total_a += a
        total_e += e
    return [{
        "company_energy_actual_today": round(total_a, 2),
        "company_energy_expected_today": round(total_e, 2),
    }]
