"""Native observed-weather condition derivation (read-only, query-free).

:func:`derive_site_condition` is the SINGLE place that maps an already-observed
telemetry irradiance reading (plus solar geometry + freshness) into an
:class:`~app.schema.telemetry_v2.ObservedCondition` for the cosmetic weather
indicator. It performs NO database query and NO network call — every input is
passed in by the caller — so the single-site performance-context path and the
batched site-list path produce identical results by construction.

Hard invariants (mirrored in tests):

* ``null`` != ``0``: a missing irradiance yields ``state="unavailable"``; it is
  never coerced to ``0``. A genuine *measured* ``0`` is classified by solar
  geometry / local time (night vs low-light), never dropped and never "sunny".
* The strings "rain"/"rainy" are NEVER emitted. The wettest honest state is
  ``overcast_unknown`` -> "...precipitation (undetermined)".
* "POA"/"cell" wording is allowed ONLY when ``plane_governed`` is true; this
  service never puts POA wording in a label and conveys governance via
  ``confidence`` (calibrated vs uncalibrated). It NEVER asserts a plane itself.
* It never drives the expected model, a baseline, or the WeatherResolver.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional, Tuple
from zoneinfo import ZoneInfo

from app.helpers.solar_position import (
    clear_sky_ghi,
    solar_elevation_deg,
    solar_zenith_cos,
)
from app.schema.telemetry_v2 import ObservedCondition, ObservedTemperature

# --- Tier A clearness-index thresholds (kt = observed / clear-sky GHI) --------
KT_SUNNY = 0.75
KT_PARTLY = 0.40
KT_CLOUDY = 0.15
# Sun elevation (deg) below which we call it dawn/dusk low-light rather than
# dividing observed irradiance by a tiny, unreliable clear-sky denominator.
LOW_LIGHT_ELEVATION_DEG = 5.0

# --- Tier B raw-irradiance bands (W/m^2), used only when coords are unknown ---
IRR_STRONG = 600.0
IRR_MODERATE = 150.0
IRR_DARK = 5.0
# Local-hour night band for Tier B (no solar geometry available): [20:00, 05:00).
NIGHT_HOUR_START = 20
NIGHT_HOUR_END = 5


def _light_level(irr: Optional[float]) -> Optional[str]:
    """Map an observed irradiance to a coarse light-level band (``None`` if no irr)."""
    if irr is None:
        return None
    if irr >= IRR_STRONG:
        return "strong"
    if irr >= IRR_MODERATE:
        return "moderate"
    if irr > IRR_DARK:
        return "low"
    return "dark"


def _to_site_local(ts_utc: datetime, tz_name: str) -> datetime:
    """Convert a naive-UTC instant to the site's local naive wall-clock time.

    Falls back to the original instant when the IANA name is missing/invalid (the
    indicator is cosmetic; an unknown tz never raises).
    """
    try:
        tz = ZoneInfo(tz_name)
    except Exception:  # noqa: BLE001 - any unknown/invalid IANA name
        return ts_utc
    aware = ts_utc.replace(tzinfo=timezone.utc) if ts_utc.tzinfo is None else ts_utc
    return aware.astimezone(tz).replace(tzinfo=None)


def _convert_temp(value_f: float, unit: str) -> float:
    """Convert a Fahrenheit reading to the requested output unit (``F``/``C``)."""
    if unit == "C":
        return (value_f - 32.0) / 1.8
    return value_f


def _unavailable(*, tier: str, freshness: str) -> ObservedCondition:
    data_quality = freshness if freshness in ("fresh", "stale", "no_data") else "no_data"
    return ObservedCondition(
        state="unavailable",
        label="Observed weather unavailable",
        confidence="unavailable",
        tier=tier,  # type: ignore[arg-type]
        data_quality=data_quality,  # type: ignore[arg-type]
    )


def derive_site_condition(
    *,
    latest_irradiance_wm2: Optional[float],
    latest_irradiance_at_utc: Optional[datetime],
    freshness_state: str,
    timezone_name: str = "UTC",
    coordinates: Optional[Tuple[float, float]] = None,
    plane_governed: bool = False,
    latest_temperature_f: Optional[float] = None,
    temperature_unit: str = "F",
    temperature_type: Optional[str] = None,
) -> ObservedCondition:
    """Derive an :class:`ObservedCondition` from already-observed inputs.

    Args:
        latest_irradiance_wm2: Latest NON-NULL observed irradiance (W/m^2) in the
            window, or ``None`` when there is none (-> ``unavailable``; never 0).
        latest_irradiance_at_utc: That reading's naive-UTC bucket start.
        freshness_state: ``fresh`` / ``stale`` / ``no_data`` (``no_data`` ->
            ``unavailable``).
        timezone_name: Site IANA tz, used only for the local-time night band and
            the ``as_of_site_local`` display field.
        coordinates: ``(lat, lon)`` -> Tier A (solar geometry); ``None`` ->
            Tier B (coarse raw-irradiance bands).
        plane_governed: ``True`` only when the irradiance plane is GOVERNED POA;
            flips Tier A confidence to ``observed_calibrated``. Never invents POA.
        latest_temperature_f: Optional latest temperature (F) to attach.
        temperature_unit: Output unit for the attached temperature (``F``/``C``).
        temperature_type: GOVERNED ``temperature_type`` only (else ``None``).
    """
    tier = "A" if coordinates is not None else "B"

    # --- Step 1: availability gate (runs first) -------------------------------
    if freshness_state == "no_data" or latest_irradiance_wm2 is None:
        return _unavailable(tier=tier, freshness=freshness_state)

    irr = latest_irradiance_wm2
    as_of_local = (
        _to_site_local(latest_irradiance_at_utc, timezone_name)
        if latest_irradiance_at_utc is not None
        else None
    )

    # --- Step 2 / 2': classification ------------------------------------------
    if coordinates is not None:
        lat, lon = coordinates
        when = latest_irradiance_at_utc or datetime.utcnow()
        cos_zenith = solar_zenith_cos(lat, lon, when)
        elevation = solar_elevation_deg(cos_zenith)
        if cos_zenith <= 0:
            state, label = "nighttime", "Nighttime"
        elif elevation < LOW_LIGHT_ELEVATION_DEG:
            state, label = "low_light", "Low light (dawn/dusk)"
        else:
            ghi_cs = clear_sky_ghi(cos_zenith)
            kt = (irr / ghi_cs) if ghi_cs > 0 else 0.0
            if kt >= KT_SUNNY:
                state, label = "sunny", "Sunny / clear (observed)"
            elif kt >= KT_PARTLY:
                state, label = "partly_cloudy", "Partly cloudy (observed)"
            elif kt >= KT_CLOUDY:
                state, label = "cloudy", "Cloudy / overcast (observed)"
            else:
                state, label = (
                    "overcast_unknown",
                    "Overcast / precipitation (undetermined)",
                )
        confidence = "observed_calibrated" if plane_governed else "observed_uncalibrated"
    else:
        local = as_of_local or _to_site_local(datetime.utcnow(), timezone_name)
        is_night = local.hour >= NIGHT_HOUR_START or local.hour < NIGHT_HOUR_END
        if irr <= IRR_DARK and is_night:
            state, label = "nighttime", "Nighttime"
        elif irr <= IRR_DARK:
            state, label = "low_light", "Low light / dark (undetermined)"
        elif irr >= IRR_STRONG:
            state, label = "sunny", "Strong sunlight (observed)"
        elif irr >= IRR_MODERATE:
            state, label = "partly_cloudy", "Moderate light (observed)"
        else:
            state, label = "cloudy", "Low light / overcast (observed)"
        confidence = "coarse"

    # --- Step 3: staleness overlay (both tiers) -------------------------------
    data_quality = freshness_state if freshness_state in ("fresh", "stale") else "fresh"
    if freshness_state == "stale":
        confidence = "coarse"
        data_quality = "stale"
        if as_of_local is not None:
            label = f"{label} (last seen {as_of_local:%Y-%m-%d %H:%M})"

    # --- Step 4: light level + temperature ------------------------------------
    light_level = _light_level(irr)
    temperature: Optional[ObservedTemperature] = None
    if latest_temperature_f is not None:
        unit = "C" if temperature_unit == "C" else "F"
        temperature = ObservedTemperature(
            value=_convert_temp(latest_temperature_f, unit),
            unit=unit,  # type: ignore[arg-type]
            type=temperature_type,
        )

    return ObservedCondition(
        state=state,  # type: ignore[arg-type]
        label=label,
        light_level=light_level,  # type: ignore[arg-type]
        observed_irradiance_wm2=irr,
        plane_governed=plane_governed,
        temperature=temperature,
        confidence=confidence,  # type: ignore[arg-type]
        tier=tier,  # type: ignore[arg-type]
        as_of_utc=latest_irradiance_at_utc,
        as_of_site_local=as_of_local,
        data_quality=data_quality,  # type: ignore[arg-type]
    )
