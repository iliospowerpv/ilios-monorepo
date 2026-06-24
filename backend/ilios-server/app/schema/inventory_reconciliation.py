"""Read-only Device Inventory Reconciliation schemas (additive, Phase A).

These power a strictly READ-ONLY, site-level audit that compares the *approved
documented inventory* (active/promoted ``project_facts`` for inventory canonical
fields) against the *telemetry-discovered / observed inventory* (discovered
provider devices + the iliOS ``devices`` rows and their reviewer-confirmed
telemetry mappings).

The view DISCLOSES each site's position on a deterministic status ladder
(``InventoryReconciliationStatus`` G1->G8), the mismatches that drive it (each
tagged with an acknowledgement policy + blocking level), per-equipment-class
counts, and recommended next actions. It NEVER mutates devices, mappings, facts,
weather semantics, baselines, telemetry, or the Site entity, and it NEVER
auto-maps, auto-creates, auto-acknowledges, or converts weather semantics.

Two provenance axes are kept deliberately distinct:

* :class:`RecordedProvenance` — facts *persisted* on the device/mapping
  (``source_provider``, ``external_device_type``, whether a mapping exists). Read
  verbatim, never inferred.
* :class:`ReconciliationInference` — a NON-definitive *assessment* of where a
  device row likely originated, derived from available signals. Never
  authoritative; it must never let a telemetry-derived row masquerade as approved
  documentation.

The authority for documented *counts* is always the active fact (e.g.
``inverter_quantity``); device rows are per-item carriers for item-level mapping.
"""
from __future__ import annotations

import enum
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.schema.device_eligibility import DiagnosticBlockingLevel

__all__ = [
    "InventoryReconciliationStatus",
    "InventoryAckPolicy",
    "EquipmentClass",
    "MismatchCategory",
    "ReconciliationInference",
    "DocumentedInventoryState",
    "CoverageMode",
    "WeatherDependencySubtype",
    "RecordedProvenance",
    "InventoryClassCount",
    "InventoryMismatch",
    "NextAction",
    "InventoryReconciliationSummary",
    "InventoryReconciliationSummaryItem",
    "InventoryReconciliationSummaryBatchResponse",
    "InventoryReconciliationResponse",
]


class InventoryReconciliationStatus(str, enum.Enum):
    """Deterministic site-level headline — the FIRST gate that matches, top-down.

    Secondary flags on the response are computed independently and always
    attached, so a headline never hides a co-existing problem.
    """

    telemetry_not_connected = "telemetry_not_connected"  # G1
    documented_inventory_incomplete = "documented_inventory_incomplete"  # G2
    telemetry_connected_no_devices = "telemetry_connected_no_devices"  # G3
    telemetry_inventory_incomplete_or_stale = "telemetry_inventory_incomplete_or_stale"  # G4
    needs_reconciliation = "needs_reconciliation"  # G5
    mapping_complete_with_acknowledged_exceptions = (
        "mapping_complete_with_acknowledged_exceptions"  # G6 (unreachable in Phase A)
    )
    partially_matched = "partially_matched"  # G7
    matched = "matched"  # G8


class InventoryAckPolicy(str, enum.Enum):
    """How a mismatch may (or may not) be acknowledged away.

    ``not_acknowledgeable_blocking`` keeps the site at ``needs_reconciliation``
    even if someone tries to acknowledge it (G5 wins over G6). Acknowledgement
    only ever moves *with-followup* / *non-blocking* items. Phase A has no write
    path, so nothing is acknowledged yet (honest).
    """

    not_acknowledgeable_blocking = "not_acknowledgeable_blocking"
    acknowledgeable_with_required_followup = "acknowledgeable_with_required_followup"
    acknowledgeable_non_blocking = "acknowledgeable_non_blocking"
    informational = "informational"


class EquipmentClass(str, enum.Enum):
    """Reconciliation equipment classes. Modules are counted but NEVER compared to
    per-device telemetry counts (array/site-level only). ``virtual`` aggregates are
    excluded from production completeness."""

    inverter = "inverter"
    module = "module"
    production_meter = "production_meter"
    weather_sensor = "weather_sensor"
    gateway = "gateway"  # gateway / data logger / UPS / network device
    comms = "comms"  # modem / cellular
    virtual = "virtual"  # site-performance aggregate
    other = "other"


class MismatchCategory(str, enum.Enum):
    """The nine mismatch categories of the approved severity x policy matrix."""

    quantity_mismatch = "quantity_mismatch"  # 1
    missing_telemetry_counterpart = "missing_telemetry_counterpart"  # 2
    undocumented_telemetry_device = "undocumented_telemetry_device"  # 3
    model_capacity_mismatch = "model_capacity_mismatch"  # 4
    cardinality_exception = "cardinality_exception"  # 5
    device_role_mismatch = "device_role_mismatch"  # 6
    weather_expected_dependency = "weather_expected_dependency"  # 7
    telemetry_freshness = "telemetry_freshness"  # 8
    design_as_built_version = "design_as_built_version"  # 9


class ReconciliationInference(str, enum.Enum):
    """NON-definitive assessment of where a device row likely originated.

    Distinct from :class:`RecordedProvenance` (persisted facts). Never
    authoritative — a telemetry-derived row must never masquerade as approved
    documentation.
    """

    telemetry_derived = "telemetry_derived"
    design_derived = "design_derived"
    as_built_commissioning_derived = "as_built_commissioning_derived"
    manually_created = "manually_created"
    legacy_unknown = "legacy_unknown"


class DocumentedInventoryState(str, enum.Enum):
    """Presence of the two anchor documented-inventory facts."""

    complete = "complete"  # both inverter_quantity AND module_quantity active facts
    partial = "partial"  # exactly one present
    missing = "missing"  # neither present


class CoverageMode(str, enum.Enum):
    """How device-level reconciliation coverage is expressed for the site."""

    device_level = "device_level"  # per-device mapping reconciled
    approved_aggregate = "approved_aggregate"  # declared site/array-level aggregate
    undeclared_aggregate = "undeclared_aggregate"
    none = "none"


class WeatherDependencySubtype(str, enum.Enum):
    """Status of the site's weather dependency relative to an active WA expected."""

    not_applicable = "not_applicable"  # no active weather-adjusted expected baseline
    satisfied = "satisfied"  # weather semantics declared + usable
    unknown_semantics = "unknown_semantics"  # mapped weather source, semantics unknown
    source_absent = "source_absent"  # WA expected active but no weather source mapped


class RecordedProvenance(BaseModel):
    """Persisted facts read verbatim from the device + its telemetry mapping.

    Never inferred. Kept distinct from :class:`ReconciliationInference`.
    """

    has_telemetry_mapping: bool
    source_provider: Optional[str] = None
    external_device_type: Optional[str] = None
    external_device_id: Optional[str] = None


class InventoryClassCount(BaseModel):
    """Per-equipment-class count summary.

    ``documented_count`` is the approved fact count (None when the class is not
    documented as a count, e.g. meters/weather/gateways). ``discovered_count`` is
    None for classes where per-device discovery does not apply (e.g. modules).
    """

    equipment_class: EquipmentClass
    documented_count: Optional[int] = None
    ilios_row_count: int = 0
    discovered_count: Optional[int] = None
    mapped_count: int = 0
    unmapped_documented_count: int = 0
    undocumented_telemetry_count: int = 0
    reconciliation_basis: str
    note: Optional[str] = None


class InventoryMismatch(BaseModel):
    """One reconciliation finding with its acknowledgement policy + provenance."""

    mismatch_signature: str
    category: MismatchCategory
    equipment_class: Optional[EquipmentClass] = None
    acknowledgement_policy: InventoryAckPolicy
    blocking_level: DiagnosticBlockingLevel
    title: str
    detail: str
    recommended_action: Optional[str] = None
    next_step_target: Optional[str] = None
    # Device side (per-item carrier).
    device_id: Optional[int] = None
    device_name: Optional[str] = None
    recorded_provenance: Optional[RecordedProvenance] = None
    reconciliation_inference: Optional[ReconciliationInference] = None
    # Compared values (text — facts may carry units).
    documented_value: Optional[str] = None
    observed_value: Optional[str] = None
    weather_subtype: Optional[WeatherDependencySubtype] = None
    coverage_mode: Optional[CoverageMode] = None
    # Read-only provenance / audit identifiers.
    active_fact_ids: list[int] = []
    candidate_fact_ids: list[int] = []
    external_device_id: Optional[str] = None
    # Acknowledgement (Phase A: always unacknowledged; reserved for Phase B/C).
    is_acknowledged: bool = False


class NextAction(BaseModel):
    """A recommended, governed next step. Phase A never performs it."""

    title: str
    detail: str
    blocking_level: DiagnosticBlockingLevel
    target: Optional[str] = None  # data_room / weather_semantics / device_mapping / discovery_sync / none
    related_mismatch_signatures: list[str] = []


class InventoryReconciliationSummary(BaseModel):
    """Compact headline used to populate the DD ``telemetry_reality`` block."""

    status: InventoryReconciliationStatus
    status_label: str
    status_explanation: str
    has_blocking_mismatch: bool
    weather_dependency_unsatisfied: bool
    open_actionable_mismatch_count: int
    informational_mismatch_count: int


class InventoryReconciliationSummaryItem(BaseModel):
    """One site's compact reconciliation summary, keyed by ``site_id``.

    Used by the batch summaries endpoint so list/card surfaces can render a
    read-only status chip per site with a SINGLE request. Only sites the caller
    is authorized to view are included; everything else is simply omitted (the
    chip then renders an honest "Status unavailable", never a fabricated match).
    """

    site_id: int
    summary: InventoryReconciliationSummary


class InventoryReconciliationSummaryBatchResponse(BaseModel):
    """Batch of compact reconciliation summaries for a set of sites (read-only)."""

    summaries: list[InventoryReconciliationSummaryItem] = []


class InventoryReconciliationResponse(BaseModel):
    """Full site-level inventory reconciliation payload (read-only)."""

    site_id: int
    generated_at: datetime
    # Reconciliation engine/rule version that produced these mismatches. An
    # acknowledgement is bound to this version (plus the exact signature), so a
    # future rule change that bumps this value never silently reuses an old ack.
    reconciliation_version: str

    # Headline.
    status: InventoryReconciliationStatus
    status_label: str
    status_explanation: str

    # Secondary flags (always emitted).
    telemetry_connected: bool
    site_mapped: bool
    documented_inventory_state: DocumentedInventoryState
    documented_inventory_incomplete: bool
    discovery_stale: bool
    discovery_last_synced_at: Optional[datetime] = None
    has_blocking_mismatch: bool
    weather_dependency_unsatisfied: bool
    weather_dependency_subtype: WeatherDependencySubtype
    active_expected_baseline_id: Optional[int] = None
    active_expected_baseline_requires_weather: bool
    coverage_mode: CoverageMode

    # Counts.
    total_ilios_devices: int
    total_discovered_devices: int
    class_counts: list[InventoryClassCount] = []
    mismatch_category_counts: dict[str, int] = {}
    open_actionable_mismatch_count: int = 0
    informational_mismatch_count: int = 0
    acknowledged_exception_count: int = 0  # always 0 in Phase A (no write path)

    mismatches: list[InventoryMismatch] = []
    next_actions: list[NextAction] = []
    notes: list[str] = []
