"""Device Inventory Reconciliation — read-only, additive (Phase A).

Answers, for a single site, the question: *does the approved documented inventory
agree with what telemetry has discovered/observed, and with the reviewer-confirmed
device mappings?* It DISCLOSES a deterministic site-level headline
(:class:`InventoryReconciliationStatus`, the G1→G8 ladder), per-equipment-class
counts, mismatch findings (each tagged with an acknowledgement policy + blocking
level), secondary flags, and recommended next actions.

Hard guarantees (Phase A):

* **Zero mutation.** This service performs NO writes/commits. It never creates,
  maps, acknowledges, converts, promotes, or deletes anything — not ``devices``,
  ``telemetry_devices_mapping``, ``telemetry_sites_mapping``, ``project_facts``,
  ``telemetry_*``, ``weather_device_mappings``, or baselines.
* **Active promoted facts are the SOLE authority** for documented counts;
  candidate facts are surfaced only as review signals (their ids are carried, but
  they never change a count).
* ``can_drive_expected`` stays FROZEN to ``{inverter, module, weather_station}``;
  this service never widens it (it only reads :func:`classify_device`).
* **Modules are NEVER compared to per-device telemetry counts** — they reconcile
  at the array/site level only. Virtual aggregates are excluded from production.
* ``recorded_provenance`` (persisted facts) is kept distinct from
  ``reconciliation_inference`` (a non-definitive assessment).
* Weather remediation is always the *governed weather-semantics workflow*; this
  service never suggests "mapping a weather device" as a substitute and never
  converts irradiance/temperature semantics.

The endpoint wrapping this service returns HTTP 200 for EVERY valid reconciliation
state; this builder therefore degrades gracefully (empty sites, missing mappings,
unreadable weather semantics) instead of raising.
"""
from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session, joinedload

from app.crud.telemetry_expected import TelemetryExpectedBaselineCRUD
from app.crud.weather import WeatherDeviceMappingCRUD
from app.models.device import DeviceCategories
from app.models.inventory_acknowledgement import (
    InventoryAckStatus,
    InventoryMismatchAcknowledgement,
)
from app.models.project_facts import FactStatus, ProjectFact
from app.models.telemetry import (
    ExternalSiteSyncStatus,
    TelemetryExternalDevice,
    TelemetryExternalSite,
    TelemetrySyncJob,
    TelemetrySyncStatus,
)
from app.models.telemetry_expected import TelemetryBaselineType
from app.schema.device_eligibility import DiagnosticBlockingLevel, severity_rank
from app.schema.inventory_reconciliation import (
    CoverageMode,
    DocumentedInventoryState,
    EquipmentClass,
    InventoryAckPolicy,
    InventoryClassCount,
    InventoryMismatch,
    InventoryReconciliationResponse,
    InventoryReconciliationStatus,
    InventoryReconciliationSummary,
    MismatchCategory,
    NextAction,
    ReconciliationInference,
    RecordedProvenance,
    WeatherDependencySubtype,
)
from app.schema.weather import _PHYSICS_USABLE_PLANES, _PHYSICS_USABLE_TEMPERATURES
from app.services.telemetry.device_classification import classify_device

logger = logging.getLogger(__name__)

# --- Reconciliation engine version -----------------------------------------
# Identifies the reconciliation rule set / signature scheme that produced a
# mismatch. A reviewer acknowledgement is bound to BOTH the exact
# ``mismatch_signature`` AND this version, so when a future rule change alters how
# signatures are computed this value MUST be bumped in lockstep — an older
# acknowledgement then no longer applies (it goes inert / "expired" at read time)
# instead of being silently reused against a different finding.
RECONCILIATION_VERSION = "inv-recon/1"

# --- Source module tag (snapshotted onto an acknowledgement row) ------------
SOURCE_MODULE = "device_inventory_reconciliation"

# --- Soft thresholds --------------------------------------------------------
# Discovery is "stale" when the provider device cache has not been re-synced
# within this window. Staleness is a SECONDARY (lowers-confidence) flag — it only
# escalates to the G4 headline when readings are ALSO not fresh.
DISCOVERY_STALE_AFTER = timedelta(days=7)
# Readings are "fresh" when a successful/partial site ingestion ended within this
# window. Fresh readings prove the telemetry inventory is live even if the device
# cache is stale, so they suppress the G4 headline.
READINGS_FRESH_WITHIN = timedelta(days=2)

# --- Inventory canonical field names ----------------------------------------
F_INVERTER_QTY = "inverter_quantity"
F_MODULE_QTY = "module_quantity"
F_INVERTER_MODEL = "inverter_model"
F_MODULE_MODEL = "module_model"
F_INVERTER_WATTAGE = "inverter_wattage"
F_MODULE_WATTAGE = "module_wattage"

# Next-step target vocabulary (the FE deep-links these; all are read-only hints).
TARGET_DATA_ROOM = "data_room"
TARGET_WEATHER_SEMANTICS = "weather_semantics"
TARGET_DEVICE_MAPPING = "device_mapping"
TARGET_DISCOVERY_SYNC = "discovery_sync"
TARGET_NONE = "none"

# Human-readable headline labels + explanations, keyed by status.
_STATUS_LABELS: dict[InventoryReconciliationStatus, str] = {
    InventoryReconciliationStatus.telemetry_not_connected: "Telemetry not connected",
    InventoryReconciliationStatus.documented_inventory_incomplete: (
        "Documented inventory incomplete"
    ),
    InventoryReconciliationStatus.telemetry_connected_no_devices: (
        "Telemetry connected, no devices"
    ),
    InventoryReconciliationStatus.telemetry_inventory_incomplete_or_stale: (
        "Telemetry inventory incomplete or stale"
    ),
    InventoryReconciliationStatus.needs_reconciliation: "Needs reconciliation",
    InventoryReconciliationStatus.mapping_complete_with_acknowledged_exceptions: (
        "Mapping complete (acknowledged exceptions)"
    ),
    InventoryReconciliationStatus.partially_matched: "Partially matched",
    InventoryReconciliationStatus.matched: "Matched",
}

_STATUS_EXPLANATIONS: dict[InventoryReconciliationStatus, str] = {
    InventoryReconciliationStatus.telemetry_not_connected: (
        "This project has no active telemetry connection, so no observed inventory "
        "can be compared against the approved documentation."
    ),
    InventoryReconciliationStatus.documented_inventory_incomplete: (
        "The approved documented inventory is incomplete (the inverter and/or module "
        "quantity is not a promoted assumption yet), so a reliable comparison is not "
        "possible. Promote the missing inventory terms in the Data Room."
    ),
    InventoryReconciliationStatus.telemetry_connected_no_devices: (
        "Telemetry is connected but no provider devices have been discovered and no "
        "iliOS devices are mapped, so there is nothing to reconcile yet."
    ),
    InventoryReconciliationStatus.telemetry_inventory_incomplete_or_stale: (
        "The telemetry-discovered inventory looks incomplete or out of date: an "
        "expected production device is not observed, or device discovery is stale and "
        "no fresh readings confirm the current hardware."
    ),
    InventoryReconciliationStatus.needs_reconciliation: (
        "Reconciliation is blocked by one or more findings that cannot be acknowledged "
        "away (for example a required weather-measurement dependency whose semantics "
        "are unresolved while a weather-adjusted expected baseline is active)."
    ),
    InventoryReconciliationStatus.mapping_complete_with_acknowledged_exceptions: (
        "All mappings are complete and the remaining exceptions have been acknowledged. "
        "(Acknowledgement is not available in this phase.)"
    ),
    InventoryReconciliationStatus.partially_matched: (
        "The documented and observed inventory mostly agree, but some non-blocking "
        "follow-ups remain (for example unmapped auxiliary devices or undocumented "
        "telemetry devices)."
    ),
    InventoryReconciliationStatus.matched: (
        "The approved documented inventory agrees with the telemetry-observed inventory "
        "and the reviewer-confirmed mappings. Only informational notes remain, if any."
    ),
}


# ---------------------------------------------------------------------------
# Small value coercion helpers (never fabricate — return None when unsure)
# ---------------------------------------------------------------------------
def _coerce_int(value) -> Optional[int]:
    """Best-effort integer from a JSONB fact value (int/float/leading-int string).

    Returns ``None`` (not 0) when the value cannot be read as a whole number, so a
    missing/garbled documented count never masquerades as a real zero.
    """
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value) if value.is_integer() else None
    if isinstance(value, str):
        match = re.match(r"^-?\d+", value.strip().replace(",", ""))
        return int(match.group()) if match else None
    return None


def _as_text(value) -> Optional[str]:
    """Stringify a fact value verbatim (facts may carry units, e.g. ``"340 Wp"``)."""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _unwrap(value):
    """Unwrap the ``{"v": ...}`` JSONB envelope used by ``project_facts.value``.

    ``project_facts.value`` is always stored wrapped (e.g. ``{"v": "7"}``); reading
    it raw would hand a ``dict`` to :func:`_coerce_int` / :func:`_as_text` and the
    documented count/model would silently read as missing. Mirrors the unwrap used
    by the DD reconciliation service so both views agree on the same fact value.
    """
    if isinstance(value, dict) and "v" in value:
        return value["v"]
    return value


def _equipment_class(cls) -> EquipmentClass:
    """Map a :class:`DeviceClassification` to a reconciliation equipment class.

    Order matters: the stable expected-driving categories win first, then virtual
    aggregates (so a site-performance device is never bucketed as production), then
    the broad inspection-only capabilities.
    """
    category = cls.category
    if category == DeviceCategories.inverter.value:
        return EquipmentClass.inverter
    if category == DeviceCategories.module.value:
        return EquipmentClass.module
    if cls.virtual_device:
        return EquipmentClass.virtual
    if cls.weather_source_capable:
        return EquipmentClass.weather_sensor
    if cls.production_meter_capable:
        return EquipmentClass.production_meter
    if cls.gateway_capable:
        return EquipmentClass.gateway
    if category == DeviceCategories.modem.value:
        return EquipmentClass.comms
    return EquipmentClass.other


def _infer_origin(cls, is_mapped: bool) -> ReconciliationInference:
    """NON-definitive assessment of where a device row likely originated.

    Deliberately conservative: a provider-sourced or telemetry-mapped row is
    *assessed* (never asserted) as telemetry-derived; otherwise it is treated as a
    manually-created documentation row. This is an assessment only and must never
    let a telemetry-derived row stand in for approved documentation.
    """
    if cls.source_provider or is_mapped:
        return ReconciliationInference.telemetry_derived
    return ReconciliationInference.manually_created


def _weather_usable(db: Session, device_id: int) -> tuple[bool, bool]:
    """Read the device's declared weather semantics verbatim (never converted).

    Returns ``(has_declaration, physics_usable)``. A read failure degrades to
    ``(False, False)`` with a warning so the headline can still be produced — an
    unknown semantics read is treated as *not usable*, never optimistically POA/cell.
    """
    try:
        mapping = WeatherDeviceMappingCRUD(db).get_current_for_device(device_id)
    except Exception:  # pragma: no cover - defensive: weather read must not 500
        logger.warning(
            "inventory-reconciliation: weather semantics read failed for device %s",
            device_id,
            exc_info=True,
        )
        return (False, False)
    if mapping is None:
        return (False, False)
    usable = (
        mapping.irradiance_plane in _PHYSICS_USABLE_PLANES
        or mapping.temperature_type in _PHYSICS_USABLE_TEMPERATURES
    )
    return (True, usable)


# ---------------------------------------------------------------------------
# Main builder
# ---------------------------------------------------------------------------
def build_site_inventory_reconciliation(
    db: Session, site
) -> InventoryReconciliationResponse:
    """Compute the full read-only inventory reconciliation for ``site``.

    ``site`` is an authorized ``Site`` whose ``devices`` relationship is loadable.
    The function performs only reads; it never commits. Every valid state returns a
    fully-populated response (the wrapping endpoint always answers 200).
    """
    now = datetime.utcnow()
    notes: list[str] = []

    # -- 1. Connection / site-mapping state ---------------------------------
    site_mapping = getattr(site, "telemetry_mapping", None)
    site_mapped = site_mapping is not None and bool(
        getattr(site_mapping, "is_active", False)
    )
    connection = getattr(site_mapping, "connection", None) if site_mapping else None
    if connection is None and site_mapping is not None:
        connection = getattr(site_mapping, "provider_account", None)
    connection_live = connection is not None and not getattr(
        connection, "is_archived", False
    )
    telemetry_connected = site_mapped and connection_live

    # -- 2. Discovered provider devices + discovery staleness ---------------
    discovered: list[TelemetryExternalDevice] = []
    discovery_last_synced_at: Optional[datetime] = None
    if site_mapping is not None and site_mapping.provider_account_id:
        external_site_id = str(site_mapping.telemetry_site_id)
        discovered = (
            db.query(TelemetryExternalDevice)
            .filter(
                TelemetryExternalDevice.provider_account_id
                == site_mapping.provider_account_id,
                TelemetryExternalDevice.external_site_id == external_site_id,
            )
            .all()
        )
        ext_site = (
            db.query(TelemetryExternalSite)
            .filter(
                TelemetryExternalSite.provider_account_id
                == site_mapping.provider_account_id,
                TelemetryExternalSite.external_site_id == external_site_id,
            )
            .one_or_none()
        )
        if ext_site is not None:
            discovery_last_synced_at = ext_site.last_synced_at

    present_discovered = [
        d for d in discovered if d.sync_status != ExternalSiteSyncStatus.missing
    ]
    total_discovered_devices = len(present_discovered)
    discovery_stale = (
        discovery_last_synced_at is not None
        and (now - discovery_last_synced_at) > DISCOVERY_STALE_AFTER
    )

    # -- 3. Readings freshness (per-site sync job, fallback to connection) ---
    readings_last_at: Optional[datetime] = None
    latest_job = (
        db.query(TelemetrySyncJob)
        .filter(
            TelemetrySyncJob.site_id == site.id,
            TelemetrySyncJob.status.in_(
                (TelemetrySyncStatus.succeeded, TelemetrySyncStatus.partial)
            ),
        )
        .order_by(
            TelemetrySyncJob.ended_at.desc().nullslast(),
            TelemetrySyncJob.created_at.desc(),
        )
        .first()
    )
    if latest_job is not None:
        readings_last_at = latest_job.ended_at or latest_job.created_at
    elif connection is not None:
        readings_last_at = getattr(connection, "last_success_at", None)
    readings_fresh = (
        readings_last_at is not None
        and (now - readings_last_at) <= READINGS_FRESH_WITHIN
    )

    # -- 4. Approved documented inventory (active facts ONLY) ----------------
    active_by_name: dict[str, ProjectFact] = {}
    candidates_by_name: dict[str, list[ProjectFact]] = defaultdict(list)
    facts = (
        db.query(ProjectFact)
        .options(joinedload(ProjectFact.canonical_field))
        .filter(ProjectFact.site_id == site.id)
        .all()
    )
    for fact in facts:
        canonical = fact.canonical_field
        if canonical is None:
            continue
        if fact.status == FactStatus.active.value:
            active_by_name.setdefault(canonical.name, fact)
        elif fact.status == FactStatus.candidate.value:
            candidates_by_name[canonical.name].append(fact)

    inv_qty_fact = active_by_name.get(F_INVERTER_QTY)
    mod_qty_fact = active_by_name.get(F_MODULE_QTY)
    documented_inverter_qty = (
        _coerce_int(_unwrap(inv_qty_fact.value)) if inv_qty_fact else None
    )
    documented_module_qty = (
        _coerce_int(_unwrap(mod_qty_fact.value)) if mod_qty_fact else None
    )

    has_inv_qty = inv_qty_fact is not None
    has_mod_qty = mod_qty_fact is not None
    if has_inv_qty and has_mod_qty:
        documented_inventory_state = DocumentedInventoryState.complete
    elif has_inv_qty or has_mod_qty:
        documented_inventory_state = DocumentedInventoryState.partial
    else:
        documented_inventory_state = DocumentedInventoryState.missing
    documented_inventory_incomplete = (
        documented_inventory_state != DocumentedInventoryState.complete
    )

    # -- 5. Active weather-adjusted expected baseline (weather requirement) --
    wam = TelemetryExpectedBaselineCRUD(db).get_active(
        site.id, TelemetryBaselineType.weather_adjusted_model
    )
    active_expected_baseline_id = wam.id if wam else None
    active_expected_baseline_requires_weather = wam is not None

    # -- 6. Classify iliOS devices; tally per class; collect weather sources -
    devices = list(getattr(site, "devices", []) or [])
    mapped_external_ids: set[str] = set()
    per_class_rows: dict[EquipmentClass, int] = defaultdict(int)
    per_class_mapped: dict[EquipmentClass, int] = defaultdict(int)
    unmapped_mappable: list[tuple] = []  # (device, cls, equipment_class)
    weather_sources: list[tuple] = []  # (device, is_mapped)
    mapped_device_count = 0
    observed_inverter_count = 0

    for device in devices:
        cls = classify_device(device)
        mapping = getattr(device, "telemetry_mapping", None)
        is_mapped = mapping is not None
        equip = _equipment_class(cls)
        per_class_rows[equip] += 1
        if is_mapped:
            mapped_device_count += 1
            per_class_mapped[equip] += 1
            mapped_external_ids.add(str(mapping.telemetry_device_id))
            if equip == EquipmentClass.inverter:
                observed_inverter_count += 1
        elif cls.mappable:
            unmapped_mappable.append((device, cls, equip))
        if cls.weather_source_capable:
            weather_sources.append((device, is_mapped))

    # -- 7. Weather dependency subtype (governed semantics only) ------------
    usable_weather = False
    any_weather_unknown = False
    for device, is_mapped in weather_sources:
        has_decl, usable = _weather_usable(db, device.id)
        if is_mapped and usable:
            usable_weather = True
        else:
            any_weather_unknown = True

    if wam is None:
        weather_subtype = WeatherDependencySubtype.not_applicable
    elif usable_weather:
        weather_subtype = WeatherDependencySubtype.satisfied
    elif weather_sources:
        weather_subtype = WeatherDependencySubtype.unknown_semantics
    else:
        weather_subtype = WeatherDependencySubtype.source_absent
    weather_dependency_unsatisfied = wam is not None and weather_subtype in (
        WeatherDependencySubtype.unknown_semantics,
        WeatherDependencySubtype.source_absent,
    )

    # -- 8. Emit mismatches (per the approved 9-category policy matrix) ------
    mismatches: list[InventoryMismatch] = []

    # (7) Weather expected dependency — the only Phase-A blocking finding.
    if weather_dependency_unsatisfied:
        if weather_subtype == WeatherDependencySubtype.source_absent:
            detail = (
                "A weather-adjusted expected baseline is active, but no weather-source "
                "device is present to provide the required irradiance/temperature "
                "input. Expected output cannot be trusted until a governed weather "
                "source and its semantics are established."
            )
        else:
            detail = (
                "A weather-adjusted expected baseline is active, but the site's "
                "weather-source measurement semantics are unresolved (the irradiance "
                "plane / temperature type is unknown or unmapped). The readings are "
                "never assumed to be plane-of-array or cell temperature."
            )
        mismatches.append(
            InventoryMismatch(
                mismatch_signature=f"weather_expected_dependency:weather_sensor:site:{weather_subtype.value}",
                category=MismatchCategory.weather_expected_dependency,
                equipment_class=EquipmentClass.weather_sensor,
                acknowledgement_policy=InventoryAckPolicy.not_acknowledgeable_blocking,
                blocking_level=DiagnosticBlockingLevel.blocks_calculation,
                title="Required weather-measurement dependency unresolved",
                detail=detail,
                recommended_action=(
                    "Resolve the weather-measurement semantics through the governed "
                    "weather-semantics workflow (declare the irradiance plane / "
                    "temperature type). No conversion is performed automatically."
                ),
                next_step_target=TARGET_WEATHER_SEMANTICS,
                weather_subtype=weather_subtype,
                active_fact_ids=[],
            )
        )
    elif wam is None and any_weather_unknown and weather_sources:
        # "unknown semantics + no WA" — a soft, non-blocking confidence note.
        mismatches.append(
            InventoryMismatch(
                mismatch_signature="weather_expected_dependency:weather_sensor:site:no_wa_unknown",
                category=MismatchCategory.weather_expected_dependency,
                equipment_class=EquipmentClass.weather_sensor,
                acknowledgement_policy=InventoryAckPolicy.acknowledgeable_with_required_followup,
                blocking_level=DiagnosticBlockingLevel.lowers_confidence,
                title="Weather semantics unresolved",
                detail=(
                    "A weather-source device is present with unresolved measurement "
                    "semantics. No weather-adjusted expected baseline is active, so this "
                    "is not blocking yet, but it should be resolved before one is."
                ),
                recommended_action=(
                    "Declare the weather-measurement semantics via the governed "
                    "weather-semantics workflow."
                ),
                next_step_target=TARGET_WEATHER_SEMANTICS,
                weather_subtype=WeatherDependencySubtype.unknown_semantics,
            )
        )

    # (2) Missing telemetry counterpart — a mappable iliOS device not yet mapped.
    for device, cls, equip in unmapped_mappable:
        is_production = equip in (EquipmentClass.inverter, EquipmentClass.production_meter)
        policy = (
            InventoryAckPolicy.acknowledgeable_with_required_followup
            if is_production
            else InventoryAckPolicy.acknowledgeable_non_blocking
        )
        level = (
            DiagnosticBlockingLevel.lowers_confidence
            if is_production
            else DiagnosticBlockingLevel.informational
        )
        mismatches.append(
            InventoryMismatch(
                mismatch_signature=f"missing_telemetry_counterpart:{equip.value}:device:{device.id}",
                category=MismatchCategory.missing_telemetry_counterpart,
                equipment_class=equip,
                acknowledgement_policy=policy,
                blocking_level=level,
                title="Documented device has no telemetry counterpart",
                detail=(
                    f"'{device.name or device.id}' is part of the documented inventory "
                    "and is telemetry-eligible, but it is not mapped to a provider "
                    "device, so no readings flow for it."
                ),
                recommended_action="Map this device to its provider/DAS device.",
                next_step_target=TARGET_DEVICE_MAPPING,
                device_id=device.id,
                device_name=device.name,
                recorded_provenance=RecordedProvenance(
                    has_telemetry_mapping=False,
                    source_provider=cls.source_provider,
                    external_device_type=cls.external_device_type,
                ),
                reconciliation_inference=_infer_origin(cls, False),
            )
        )

    # (3) Undocumented telemetry device — a discovered device not mapped back.
    for ext in present_discovered:
        if str(ext.external_device_id) in mapped_external_ids:
            continue
        mismatches.append(
            InventoryMismatch(
                mismatch_signature=f"undocumented_telemetry_device:other:external:{ext.external_device_id}",
                category=MismatchCategory.undocumented_telemetry_device,
                equipment_class=EquipmentClass.other,
                acknowledgement_policy=InventoryAckPolicy.acknowledgeable_non_blocking,
                blocking_level=DiagnosticBlockingLevel.informational,
                title="Telemetry device not in documented inventory",
                detail=(
                    f"The provider reports a device "
                    f"('{ext.external_device_name or ext.external_device_id}') that is "
                    "not mapped to any documented iliOS device. Confirm whether it "
                    "belongs to this project."
                ),
                recommended_action=(
                    "Review the discovered device and map it to a documented device, "
                    "or confirm it is out of scope."
                ),
                next_step_target=TARGET_DEVICE_MAPPING,
                observed_value=ext.external_device_name,
                external_device_id=str(ext.external_device_id),
                reconciliation_inference=ReconciliationInference.telemetry_derived,
            )
        )

    # (1) Quantity mismatch — documented inverter count vs observed inverters.
    #     Informational only (the binding per-device reconciliation is category 2).
    #     Modules are NEVER compared to telemetry device counts.
    if documented_inverter_qty is not None and observed_inverter_count > 0:
        if documented_inverter_qty != observed_inverter_count:
            mismatches.append(
                InventoryMismatch(
                    mismatch_signature="quantity_mismatch:inverter:site",
                    category=MismatchCategory.quantity_mismatch,
                    equipment_class=EquipmentClass.inverter,
                    acknowledgement_policy=InventoryAckPolicy.informational,
                    blocking_level=DiagnosticBlockingLevel.informational,
                    title="Documented inverter count differs from observed",
                    detail=(
                        f"The approved documentation lists {documented_inverter_qty} "
                        f"inverter(s); {observed_inverter_count} inverter(s) are "
                        "currently observed via telemetry mappings."
                    ),
                    recommended_action=(
                        "Confirm the inverter inventory and mappings; the documented "
                        "count remains authoritative."
                    ),
                    next_step_target=TARGET_DEVICE_MAPPING,
                    documented_value=str(documented_inverter_qty),
                    observed_value=str(observed_inverter_count),
                    active_fact_ids=[inv_qty_fact.id] if inv_qty_fact else [],
                    candidate_fact_ids=[
                        c.id for c in candidates_by_name.get(F_INVERTER_QTY, [])
                    ],
                )
            )

    # (4) Model / capacity mismatch — documented inverter model vs mapped rows.
    #     Sparse signal → informational; only emitted when both sides are present.
    inv_model_fact = active_by_name.get(F_INVERTER_MODEL)
    documented_inverter_model = (
        _as_text(_unwrap(inv_model_fact.value)) if inv_model_fact else None
    )
    if documented_inverter_model:
        normalized_doc = documented_inverter_model.strip().lower()
        for device in devices:
            cls = classify_device(device)
            if _equipment_class(cls) != EquipmentClass.inverter:
                continue
            if getattr(device, "telemetry_mapping", None) is None:
                continue
            device_model = (getattr(device, "model", None) or "").strip()
            if device_model and device_model.lower() != normalized_doc:
                mismatches.append(
                    InventoryMismatch(
                        mismatch_signature=f"model_capacity_mismatch:inverter:device:{device.id}",
                        category=MismatchCategory.model_capacity_mismatch,
                        equipment_class=EquipmentClass.inverter,
                        acknowledgement_policy=InventoryAckPolicy.informational,
                        blocking_level=DiagnosticBlockingLevel.informational,
                        title="Inverter model differs from documentation",
                        detail=(
                            f"'{device.name or device.id}' is recorded as model "
                            f"'{device_model}', but the approved documentation lists "
                            f"'{documented_inverter_model}'."
                        ),
                        recommended_action=(
                            "Confirm the inverter model against the source document."
                        ),
                        next_step_target=TARGET_DATA_ROOM,
                        device_id=device.id,
                        device_name=device.name,
                        documented_value=documented_inverter_model,
                        observed_value=device_model,
                        active_fact_ids=[inv_model_fact.id] if inv_model_fact else [],
                    )
                )

    # (8) Telemetry freshness — stale device discovery (secondary, non-blocking).
    if discovery_stale:
        mismatches.append(
            InventoryMismatch(
                mismatch_signature="telemetry_freshness:site:discovery_stale",
                category=MismatchCategory.telemetry_freshness,
                equipment_class=None,
                acknowledgement_policy=InventoryAckPolicy.acknowledgeable_non_blocking,
                blocking_level=DiagnosticBlockingLevel.lowers_confidence,
                title="Device discovery is stale",
                detail=(
                    "The provider device list has not been re-synced recently, so newly "
                    "added or removed hardware may not be reflected here."
                    + (
                        " Recent readings still confirm the site is live."
                        if readings_fresh
                        else ""
                    )
                ),
                recommended_action="Re-sync the provider device list to refresh discovery.",
                next_step_target=TARGET_DISCOVERY_SYNC,
            )
        )

    # -- 9. Apply reviewer acknowledgements (exact signature + version only) -
    # Read-only: we only SELECT active acknowledgements for this site whose
    # reconciliation_version matches the current engine version, then mark the
    # matching acknowledgeable mismatches. Blocking / informational mismatches
    # ignore acknowledgements entirely, so a blocking finding can never be
    # acknowledged away. No write/commit happens on this path.
    _ACKNOWLEDGEABLE_POLICIES = (
        InventoryAckPolicy.acknowledgeable_with_required_followup,
        InventoryAckPolicy.acknowledgeable_non_blocking,
    )
    acknowledged_signatures = _load_active_acknowledged_signatures(db, site.id)
    for m in mismatches:
        if (
            m.acknowledgement_policy in _ACKNOWLEDGEABLE_POLICIES
            and m.mismatch_signature in acknowledged_signatures
        ):
            m.is_acknowledged = True

    # -- 9b. Aggregate mismatch tallies (ack-aware) -------------------------
    has_blocking_mismatch = any(
        m.acknowledgement_policy == InventoryAckPolicy.not_acknowledgeable_blocking
        for m in mismatches
    )
    open_actionable_mismatch_count = sum(
        1
        for m in mismatches
        if m.acknowledgement_policy in _ACKNOWLEDGEABLE_POLICIES
        and not m.is_acknowledged
    )
    acknowledged_exception_count = sum(
        1
        for m in mismatches
        if m.acknowledgement_policy in _ACKNOWLEDGEABLE_POLICIES and m.is_acknowledged
    )
    informational_mismatch_count = sum(
        1
        for m in mismatches
        if m.acknowledgement_policy == InventoryAckPolicy.informational
    )
    mismatch_category_counts: dict[str, int] = defaultdict(int)
    for m in mismatches:
        mismatch_category_counts[m.category.value] += 1

    # -- 10. Coverage mode ---------------------------------------------------
    if mapped_device_count > 0:
        coverage_mode = CoverageMode.device_level
    elif documented_module_qty is not None:
        coverage_mode = CoverageMode.approved_aggregate
    else:
        coverage_mode = CoverageMode.none

    # -- 11. The G1->G8 ladder (first gate that matches, top-down) ----------
    expected_inverters_documented = (
        documented_inverter_qty is not None and documented_inverter_qty > 0
    )
    if not telemetry_connected:
        status = InventoryReconciliationStatus.telemetry_not_connected
    elif documented_inventory_incomplete:
        status = InventoryReconciliationStatus.documented_inventory_incomplete
    elif total_discovered_devices == 0 and mapped_device_count == 0:
        status = InventoryReconciliationStatus.telemetry_connected_no_devices
    elif (expected_inverters_documented and observed_inverter_count == 0) or (
        discovery_stale and not readings_fresh
    ):
        status = InventoryReconciliationStatus.telemetry_inventory_incomplete_or_stale
    elif has_blocking_mismatch:
        # Blocking findings can never be acknowledged away (Site-4 weather
        # dependency stays here regardless of any acknowledgement row).
        status = InventoryReconciliationStatus.needs_reconciliation
    elif open_actionable_mismatch_count > 0:
        status = InventoryReconciliationStatus.partially_matched
    elif acknowledged_exception_count > 0:
        # G6: no blocking findings, every remaining actionable mismatch is a
        # reviewer-acknowledged exception (open_actionable == 0). Reachable only
        # via the Phase-B acknowledgement write path.
        status = (
            InventoryReconciliationStatus.mapping_complete_with_acknowledged_exceptions
        )
    else:
        status = InventoryReconciliationStatus.matched

    # -- 12. Per-equipment-class counts -------------------------------------
    class_counts = _build_class_counts(
        per_class_rows=per_class_rows,
        per_class_mapped=per_class_mapped,
        documented_inverter_qty=documented_inverter_qty,
        documented_module_qty=documented_module_qty,
    )

    # -- 13. Next actions (governed, never performed here) -------------------
    next_actions = _build_next_actions(mismatches, status)

    # -- 14. Notes -----------------------------------------------------------
    if discovery_stale and discovery_last_synced_at is not None:
        notes.append(
            "Device discovery last synced "
            f"{discovery_last_synced_at.isoformat()}; treated as stale."
        )
    if documented_module_qty is not None:
        notes.append(
            "Modules are reconciled at the array/site level and are never compared to "
            "per-device telemetry counts."
        )
    if wam is None:
        notes.append(
            "No active weather-adjusted expected baseline; weather dependency is not "
            "applicable."
        )

    return InventoryReconciliationResponse(
        site_id=site.id,
        generated_at=now,
        reconciliation_version=RECONCILIATION_VERSION,
        status=status,
        status_label=_STATUS_LABELS[status],
        status_explanation=_STATUS_EXPLANATIONS[status],
        telemetry_connected=telemetry_connected,
        site_mapped=site_mapped,
        documented_inventory_state=documented_inventory_state,
        documented_inventory_incomplete=documented_inventory_incomplete,
        discovery_stale=discovery_stale,
        discovery_last_synced_at=discovery_last_synced_at,
        has_blocking_mismatch=has_blocking_mismatch,
        weather_dependency_unsatisfied=weather_dependency_unsatisfied,
        weather_dependency_subtype=weather_subtype,
        active_expected_baseline_id=active_expected_baseline_id,
        active_expected_baseline_requires_weather=active_expected_baseline_requires_weather,
        coverage_mode=coverage_mode,
        total_ilios_devices=len(devices),
        total_discovered_devices=total_discovered_devices,
        class_counts=class_counts,
        mismatch_category_counts=dict(mismatch_category_counts),
        open_actionable_mismatch_count=open_actionable_mismatch_count,
        informational_mismatch_count=informational_mismatch_count,
        acknowledged_exception_count=acknowledged_exception_count,
        mismatches=mismatches,
        next_actions=next_actions,
        notes=notes,
    )


def _load_active_acknowledged_signatures(db: Session, site_id: int) -> set[str]:
    """Return mismatch signatures with an ACTIVE acknowledgement for this site.

    Read-only (SELECT only). Restricted to ``status == acknowledged`` rows whose
    ``reconciliation_version`` equals the current engine version, so an
    acknowledgement recorded under a different rule set never applies to a freshly
    computed mismatch.
    """
    rows = (
        db.query(InventoryMismatchAcknowledgement.mismatch_signature)
        .filter(
            InventoryMismatchAcknowledgement.site_id == site_id,
            InventoryMismatchAcknowledgement.status
            == InventoryAckStatus.acknowledged,
            InventoryMismatchAcknowledgement.reconciliation_version
            == RECONCILIATION_VERSION,
        )
        .all()
    )
    return {row[0] for row in rows}


def _build_class_counts(
    *,
    per_class_rows: dict,
    per_class_mapped: dict,
    documented_inverter_qty: Optional[int],
    documented_module_qty: Optional[int],
) -> list[InventoryClassCount]:
    """Build per-equipment-class count rows for every class that has data.

    ``documented_count`` comes only from active facts (inverter/module). For
    modules ``discovered_count`` is always ``None`` (never compared to telemetry).
    """
    documented_by_class = {
        EquipmentClass.inverter: documented_inverter_qty,
        EquipmentClass.module: documented_module_qty,
    }
    out: list[InventoryClassCount] = []
    classes = set(per_class_rows) | {
        c for c, v in documented_by_class.items() if v is not None
    }
    for equip in EquipmentClass:
        if equip not in classes:
            continue
        rows = per_class_rows.get(equip, 0)
        mapped = per_class_mapped.get(equip, 0)
        documented = documented_by_class.get(equip)

        if equip == EquipmentClass.module:
            out.append(
                InventoryClassCount(
                    equipment_class=equip,
                    documented_count=documented,
                    ilios_row_count=rows,
                    discovered_count=None,
                    mapped_count=mapped,
                    unmapped_documented_count=0,
                    undocumented_telemetry_count=0,
                    reconciliation_basis="approved_aggregate",
                    note=(
                        "Modules are reconciled at the array/site level; per-device "
                        "telemetry comparison does not apply."
                    ),
                )
            )
            continue

        if equip in (EquipmentClass.comms, EquipmentClass.virtual, EquipmentClass.other):
            basis = "not_reconciled"
        else:
            basis = "device_level"
        out.append(
            InventoryClassCount(
                equipment_class=equip,
                documented_count=documented,
                ilios_row_count=rows,
                discovered_count=mapped,
                mapped_count=mapped,
                unmapped_documented_count=max(rows - mapped, 0),
                undocumented_telemetry_count=0,
                reconciliation_basis=basis,
            )
        )
    return out


def _build_next_actions(
    mismatches: list[InventoryMismatch],
    status: InventoryReconciliationStatus,
) -> list[NextAction]:
    """Group mismatches into governed next steps (Phase A never performs them)."""
    by_target: dict[str, list[InventoryMismatch]] = defaultdict(list)
    for m in mismatches:
        if m.next_step_target:
            by_target[m.next_step_target].append(m)

    titles = {
        TARGET_WEATHER_SEMANTICS: "Resolve weather-measurement semantics",
        TARGET_DEVICE_MAPPING: "Review device mappings",
        TARGET_DATA_ROOM: "Verify documentation in the Data Room",
        TARGET_DISCOVERY_SYNC: "Re-sync provider device discovery",
    }
    details = {
        TARGET_WEATHER_SEMANTICS: (
            "Declare the irradiance plane / temperature type for the site's weather "
            "source via the governed weather-semantics workflow. No conversion is "
            "performed automatically."
        ),
        TARGET_DEVICE_MAPPING: (
            "Map documented devices to their provider devices and review any "
            "telemetry devices that are not yet in the documented inventory."
        ),
        TARGET_DATA_ROOM: (
            "Confirm the affected equipment terms against the source documents in the "
            "Data Room."
        ),
        TARGET_DISCOVERY_SYNC: (
            "Re-sync the provider device list so newly added or removed hardware is "
            "reflected in discovery."
        ),
    }
    # Order by the most severe blocking level present in each target's mismatches.
    actions: list[NextAction] = []
    for target, group in by_target.items():
        level = min(
            (m.blocking_level for m in group),
            key=severity_rank,
            default=DiagnosticBlockingLevel.informational,
        )
        actions.append(
            NextAction(
                title=titles.get(target, "Review reconciliation finding"),
                detail=details.get(target, "Review the related reconciliation findings."),
                blocking_level=level,
                target=target,
                related_mismatch_signatures=[m.mismatch_signature for m in group],
            )
        )
    actions.sort(key=lambda a: severity_rank(a.blocking_level))
    return actions


def build_inventory_reconciliation_summary(
    db: Session, site
) -> InventoryReconciliationSummary:
    """Compact headline used to populate the Due-Diligence ``telemetry_reality`` block.

    Delegates to :func:`build_site_inventory_reconciliation` (same read-only path)
    and projects the headline fields, so the DD reconciliation view and the
    telemetry inventory-reconciliation endpoint can never disagree.
    """
    full = build_site_inventory_reconciliation(db, site)
    return InventoryReconciliationSummary(
        status=full.status,
        status_label=full.status_label,
        status_explanation=full.status_explanation,
        has_blocking_mismatch=full.has_blocking_mismatch,
        weather_dependency_unsatisfied=full.weather_dependency_unsatisfied,
        open_actionable_mismatch_count=full.open_actionable_mismatch_count,
        informational_mismatch_count=full.informational_mismatch_count,
    )
