"""Device telemetry classification & eligibility — additive, read-only.

Single source of truth for the questions the telemetry stack keeps asking about a
device. The verdicts are intentionally layered so that *broadening what can be
mapped* never silently broadens *what drives expected performance*:

* **mappable** — may an iliOS device be linked to a DAS / provider device so its
  streams can be stored and inspected? BROAD: inverters, modules, weather stations
  AND meters, power/DAS loggers, gateways, and weather-source sensors. Drives the
  mapping-validation and eligible-devices surfaces only.
* **can_drive_expected** — does the device participate in the expected-vs-actual /
  O&M performance pipeline? STABLE = ``{inverter, module, weather_station}``. This
  set is deliberately frozen: meters/loggers/gateways become mappable for
  inspection but must NOT auto-drive expected math. Health/readiness counts key off
  this predicate (via :func:`drives_expected`) so existing sites see no change.
* **capability flags** (``telemetry_capable``, ``weather_source_capable``,
  ``production_meter_capable``, ``gateway_capable``, ``virtual_device``) — additive,
  descriptive metadata powering Path-B diagnostics and UI; they never widen
  ``can_drive_expected``.

Resolution order for every verdict: an explicit, operator-set column on the device
wins; otherwise the value is derived from ``category`` (+ ``type`` for weather
sensors) and ``device_role``. The classifier is defensive — it reads only
attributes via ``getattr`` so it is safe on any device-like object (including light
test stubs) before the Phase-2 columns are present.

Weather measurement *semantics* (irradiance plane / temperature type / calibration)
are NEVER guessed here — that lives in the W0 ``weather_device_mappings`` domain and
defaults to ``unknown``. This module only decides whether a device is *weather-source
capable*, not what its readings mean.
"""
from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Optional

from app.models.device import DeviceCategories, DeviceTypes


class DeviceRole(str, enum.Enum):
    """Finer-grained telemetry roles layered on top of ``DeviceCategories``.

    Stored as a plain string on ``Device.device_role`` (no DB enum) so the taxonomy
    can grow without a migration. ``DeviceCategories`` stays the stable, canonical
    category; the role only refines telemetry intent.
    """

    inverter = "inverter"
    module = "module"
    weather_station = "weather_station"
    irradiance_sensor = "irradiance_sensor"
    temperature_sensor = "temperature_sensor"
    reference_cell = "reference_cell"
    meter = "meter"
    production_meter = "production_meter"
    revenue_meter = "revenue_meter"
    power_logger = "power_logger"
    das_logger = "das_logger"
    gateway = "gateway"
    site_performance_virtual = "site_performance_virtual"


# --- Category sets -----------------------------------------------------------

# Categories that drive the expected-vs-actual / O&M pipeline AND the
# health/readiness counts. STABLE — never widen this in eligibility work.
EXPECTED_DRIVING_CATEGORIES = (
    DeviceCategories.inverter,
    DeviceCategories.module,
    DeviceCategories.weather_station,
)

# Backward-compatible aliases. ``TELEMETRY_ELIGIBLE_CATEGORIES`` historically meant
# "the only mappable categories"; it now names the expected-driving set so legacy
# importers keep their original behavior (the stable three).
TELEMETRY_CAPABLE_CATEGORIES = EXPECTED_DRIVING_CATEGORIES
TELEMETRY_ELIGIBLE_CATEGORIES = list(EXPECTED_DRIVING_CATEGORIES)

# Categories carrying weather signals.
WEATHER_SOURCE_CATEGORIES = (DeviceCategories.weather_station,)
# Categories representing revenue/production/power metering.
METER_CATEGORIES = (DeviceCategories.meter,)
# Categories representing gateways / DAS data loggers.
GATEWAY_CATEGORIES = (DeviceCategories.network_gateway, DeviceCategories.mbod_gateway)

# Phase-2 mappable categories: the stable three PLUS meters and gateways. Weather
# sensors live under ``weather_station`` (already here); discrete-sensor intent is
# expressed via ``device_role``.
MAPPABLE_CATEGORIES = EXPECTED_DRIVING_CATEGORIES + METER_CATEGORIES + GATEWAY_CATEGORIES

# --- Role sets ---------------------------------------------------------------

WEATHER_SOURCE_ROLES = frozenset(
    {
        DeviceRole.weather_station.value,
        DeviceRole.irradiance_sensor.value,
        DeviceRole.temperature_sensor.value,
        DeviceRole.reference_cell.value,
    }
)
METER_ROLES = frozenset(
    {
        DeviceRole.meter.value,
        DeviceRole.production_meter.value,
        DeviceRole.revenue_meter.value,
        DeviceRole.power_logger.value,
    }
)
GATEWAY_ROLES = frozenset(
    {
        DeviceRole.gateway.value,
        DeviceRole.das_logger.value,
    }
)
EXPECTED_DRIVING_ROLES = frozenset(
    {
        DeviceRole.inverter.value,
        DeviceRole.module.value,
        DeviceRole.weather_station.value,
    }
)
# Any recognized role makes a device mappable, even if its raw category would not
# (e.g. an operator tagging a network_connection device as a power_logger).
MAPPABLE_ROLES = (
    WEATHER_SOURCE_ROLES
    | METER_ROLES
    | GATEWAY_ROLES
    | {
        DeviceRole.inverter.value,
        DeviceRole.module.value,
        DeviceRole.site_performance_virtual.value,
    }
)


@dataclass(frozen=True)
class DeviceClassification:
    """Read-only verdict describing a device's telemetry role & capabilities."""

    category: Optional[str]
    device_role: Optional[str]
    visible: bool
    mappable: bool
    telemetry_capable: bool
    weather_source_capable: bool
    production_meter_capable: bool
    gateway_capable: bool
    virtual_device: bool
    can_drive_expected: bool
    mapped_status: str
    source_provider: Optional[str]
    external_device_type: Optional[str]
    eligibility_reason: Optional[str]
    ineligibility_reason: Optional[str]


def _category_value(category) -> Optional[str]:
    if category is None:
        return None
    if isinstance(category, str):
        return category
    return getattr(category, "value", None)


def _type_value(device_type) -> Optional[str]:
    if device_type is None:
        return None
    if isinstance(device_type, str):
        return device_type
    return getattr(device_type, "value", None)


def _resolve_bool(device, attr: str, derived: bool) -> bool:
    """Explicit, operator-set column wins; otherwise use the derived value."""
    value = getattr(device, attr, None)
    return derived if value is None else bool(value)


def _default_role(category, device_type) -> Optional[str]:
    """Derive a telemetry role from category (+ type for weather sensors)."""
    if category == DeviceCategories.inverter:
        return DeviceRole.inverter.value
    if category == DeviceCategories.module:
        return DeviceRole.module.value
    if category == DeviceCategories.weather_station:
        if device_type == DeviceTypes.irradiance:
            return DeviceRole.irradiance_sensor.value
        if device_type == DeviceTypes.temperature:
            return DeviceRole.temperature_sensor.value
        return DeviceRole.weather_station.value
    if category == DeviceCategories.meter:
        return DeviceRole.meter.value
    if category in GATEWAY_CATEGORIES:
        return DeviceRole.gateway.value
    return None


def classify_device(device) -> DeviceClassification:
    """Classify a device-like object (anything exposing ``.category``).

    Eligibility is broad (``mappable``); the expected/O&M gate
    (``can_drive_expected``) stays restricted to the stable three categories and is
    NEVER widened by a role or capability override — that protects the expected math
    and the health/readiness counts from eligibility changes.
    """
    category = getattr(device, "category", None)
    device_type = getattr(device, "type", None)
    category_value = _category_value(category)

    # Resolve the role: explicit column wins, else derive from category/type.
    explicit_role = getattr(device, "device_role", None)
    explicit_role = explicit_role.strip() if isinstance(explicit_role, str) and explicit_role.strip() else None
    resolved_role = explicit_role or _default_role(category, device_type)

    # Capability flags — derived, then overridden by an explicit column if set.
    weather_source_capable = _resolve_bool(
        device,
        "weather_source_capable",
        category in WEATHER_SOURCE_CATEGORIES or (resolved_role in WEATHER_SOURCE_ROLES),
    )
    production_meter_capable = _resolve_bool(
        device,
        "production_meter_capable",
        category in METER_CATEGORIES or (resolved_role in METER_ROLES),
    )
    gateway_capable = _resolve_bool(
        device,
        "gateway_capable",
        category in GATEWAY_CATEGORIES or (resolved_role in GATEWAY_ROLES),
    )
    virtual_device = _resolve_bool(
        device,
        "virtual_device",
        resolved_role == DeviceRole.site_performance_virtual.value,
    )

    # Mappability: by category, by recognized role, or by an explicit capability.
    mappable = (
        category in MAPPABLE_CATEGORIES
        or (resolved_role in MAPPABLE_ROLES)
        or weather_source_capable
        or production_meter_capable
        or gateway_capable
        or virtual_device
    )

    # The expected/O&M gate stays frozen to the stable categories — role and
    # capability overrides deliberately do NOT widen it.
    can_drive_expected = category in EXPECTED_DRIVING_CATEGORIES

    # Descriptive "emits ingestible telemetry streams" — true for mappable physical
    # devices, false for purely-virtual aggregation targets, override allowed.
    telemetry_capable = _resolve_bool(device, "telemetry_capable", mappable and not virtual_device)

    # Mapped status (derived from the telemetry mapping relationship if loaded).
    has_mapping = getattr(device, "telemetry_mapping", None) is not None
    if has_mapping:
        mapped_status = "mapped"
    elif mappable:
        mapped_status = "unmapped_eligible"
    else:
        mapped_status = "ineligible"

    eligibility_reason, ineligibility_reason = _reasons(
        device, category_value, resolved_role, mappable, can_drive_expected
    )

    return DeviceClassification(
        category=category_value,
        device_role=resolved_role,
        visible=True,
        mappable=mappable,
        telemetry_capable=telemetry_capable,
        weather_source_capable=weather_source_capable,
        production_meter_capable=production_meter_capable,
        gateway_capable=gateway_capable,
        virtual_device=virtual_device,
        can_drive_expected=can_drive_expected,
        mapped_status=mapped_status,
        source_provider=getattr(device, "source_provider", None),
        external_device_type=getattr(device, "external_device_type", None),
        eligibility_reason=eligibility_reason,
        ineligibility_reason=ineligibility_reason,
    )


def _reasons(device, category_value, resolved_role, mappable, can_drive_expected):
    """Build the human-readable eligibility narrative (explicit column wins)."""
    explicit_eligible = getattr(device, "eligibility_reason", None)
    explicit_ineligible = getattr(device, "ineligibility_reason", None)
    label = resolved_role or category_value

    if mappable:
        if explicit_eligible:
            return explicit_eligible, None
        if can_drive_expected:
            reason = f"'{label}' is telemetry-eligible and drives expected performance."
        else:
            reason = (
                f"'{label}' is mappable for telemetry inspection but does not drive "
                "expected performance."
            )
        return reason, None

    if explicit_ineligible:
        return None, explicit_ineligible
    if not category_value:
        return None, "Device has no category."
    return None, f"Category '{category_value}' is not a telemetry-eligible device type."


def is_mappable(device) -> bool:
    """True iff the device may be mapped to a provider/DAS device (broad)."""
    return classify_device(device).mappable


def drives_expected(device) -> bool:
    """True iff the device participates in expected/O&M + health/readiness counts.

    STABLE: the original ``{inverter, module, weather_station}`` set. Use this — not
    :func:`is_mappable` — wherever eligibility changes must NOT alter behavior.
    """
    return classify_device(device).can_drive_expected


def is_telemetry_capable(device) -> bool:
    """Descriptive: device emits ingestible telemetry streams (broad).

    NOTE: this is metadata for diagnostics/UI. It is intentionally NOT the gate for
    expected/health — use :func:`drives_expected` for that.
    """
    return classify_device(device).telemetry_capable
