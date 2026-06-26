"""Pure-Python solar geometry + clear-sky helpers for the native observed-weather
indicator.

NO external dependency and NO network. This module computes an approximate solar
zenith (NOAA solar-position approximation) and the Haurwitz clear-sky GHI model,
and tolerantly parses a site's stored coordinate string. It is used ONLY to
classify an already-observed irradiance reading into a cosmetic "observed light
level"; it never drives the expected model, a baseline, or any physics calc.
"""
from __future__ import annotations

import math
import re
from datetime import datetime
from typing import Optional, Tuple

# Haurwitz clear-sky GHI model coefficients (W/m^2).
_HAURWITZ_A = 1098.0
_HAURWITZ_B = 0.057


def solar_zenith_cos(lat_deg: float, lon_deg: float, when_utc: datetime) -> float:
    """Cosine of the solar zenith angle at ``(lat, lon)`` for a UTC instant.

    Uses the NOAA solar-position approximation (well within a degree for this
    cosmetic purpose). ``when_utc`` is treated as naive-UTC. The result is clamped
    to ``[-1, 1]``; ``<= 0`` means the sun is at/below the horizon (night).
    """
    day_of_year = when_utc.timetuple().tm_yday
    hour = when_utc.hour + when_utc.minute / 60.0 + when_utc.second / 3600.0
    gamma = 2.0 * math.pi / 365.0 * (day_of_year - 1 + (hour - 12.0) / 24.0)

    decl = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.00148 * math.sin(3 * gamma)
    )
    eqtime = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.040849 * math.sin(2 * gamma)
    )
    # True solar time (minutes). The timezone offset term is 0 because ``when_utc``
    # is already UTC (the standard formula uses ``+ 4*lon - 60*tz_hours``).
    time_offset = eqtime + 4.0 * lon_deg
    tst = hour * 60.0 + time_offset
    hour_angle = tst / 4.0 - 180.0  # degrees

    lat = math.radians(lat_deg)
    ha = math.radians(hour_angle)
    cos_zenith = (
        math.sin(lat) * math.sin(decl)
        + math.cos(lat) * math.cos(decl) * math.cos(ha)
    )
    return max(-1.0, min(1.0, cos_zenith))


def solar_elevation_deg(cos_zenith: float) -> float:
    """Solar elevation angle in degrees from the zenith cosine."""
    cos_zenith = max(-1.0, min(1.0, cos_zenith))
    zenith = math.degrees(math.acos(cos_zenith))
    return 90.0 - zenith


def clear_sky_ghi(cos_zenith: float) -> float:
    """Haurwitz clear-sky GHI (W/m^2) from the zenith cosine.

    Returns ``0.0`` when the sun is at/below the horizon (``cos_zenith <= 0``) and
    is never negative. This is a coarse clear-sky ceiling used only to form a
    clearness ratio for the cosmetic indicator.
    """
    if cos_zenith <= 0:
        return 0.0
    return _HAURWITZ_A * cos_zenith * math.exp(-_HAURWITZ_B / cos_zenith)


# First two signed decimals anywhere in the string (handles bare "lat, lon" as
# well as a URL that happens to contain a coordinate pair).
_COORD_RE = re.compile(r"-?\d{1,3}(?:\.\d+)?")


def parse_lon_lat(value: Optional[str]) -> Optional[Tuple[float, float]]:
    """Tolerantly parse a stored coordinate string into ``(lat, lon)``.

    The ``sites.lon_lat_url`` column historically stores a bare ``"lat, lon"``
    pair (e.g. ``"42.60545, -72.04823"``), despite the URL-implying name. This
    parser extracts the FIRST two signed decimals and validates ranges: latitude
    in ``[-90, 90]`` and longitude in ``[-180, 180]``. If the first number is out
    of latitude range but the second is in range, the pair is treated as
    ``lon, lat`` and swapped. Anything that does not yield a valid in-range pair
    returns ``None`` (the honest Tier B fallback) — it never guesses.
    """
    if not value or not isinstance(value, str):
        return None
    nums = _COORD_RE.findall(value)
    if len(nums) < 2:
        return None
    try:
        a = float(nums[0])
        b = float(nums[1])
    except ValueError:
        return None

    def _valid(lat: float, lon: float) -> bool:
        return -90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0

    if _valid(a, b):
        return (a, b)
    if _valid(b, a):
        return (b, a)
    return None
