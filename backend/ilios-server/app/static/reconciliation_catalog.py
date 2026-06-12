"""DD V2 Phase 4 — static catalog for the assumptions reconciliation view.

This module is the single, conservative source of truth for the *baseline-driving
and diligence-critical* fields surfaced by the read-only reconciliation endpoint
(:mod:`app.services.due_diligence.reconciliation_service`). It enumerates the
fields whose values can be traced through the audit chain

    document -> AI value -> accepted/overridden value -> promoted project_fact
    -> baseline draft -> design-estimate points -> active weather-adjusted baseline

It is deliberately STATIC: it never triggers, creates, or mutates a baseline or a
fact. It only declares *which* canonical fields to reconcile, what to label them,
which category they belong to, and where (if anywhere) their value lands in a
baseline. Fields the canonical store may carry that are NOT in this catalog are
still surfaced by the service as catch-all rows (category :data:`OTHER`,
``baseline_target`` :data:`NONE`); the catalog never promises a legal/warranty
taxonomy the underlying data cannot support.

The canonical names below are the NORMALIZED names (lowercase snake_case) used by
``canonical_fields.name`` and by the Phase 2/3 producer field maps
(:mod:`app.services.telemetry.baseline_from_facts_service` and
:mod:`app.services.telemetry.baseline_points_service`). A unit test asserts they
match those producers verbatim so the catalog can never silently drift.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

# ---------------------------------------------------------------------------
# Category — the diligence grouping a field belongs to. Conservative: only
# categories the data can actually support are used by the static catalog; the
# service tags catch-all facts as ``OTHER``.
# ---------------------------------------------------------------------------
BASELINE_PHYSICS = "baseline_physics"
DESIGN_ESTIMATE = "design_estimate"
WEATHER = "weather"
LEGAL_COMMERCIAL = "legal_commercial"
EQUIPMENT = "equipment"
WARRANTY_PERMIT_INSURANCE = "warranty_permit_insurance"
OTHER = "other"

# ---------------------------------------------------------------------------
# Baseline target — where (if anywhere) a field's value is stored on a baseline.
# These must never be collapsed: physics nameplate lands on the weather-adjusted
# baseline HEADER columns, while design-estimate production lands on the
# design-estimate baseline POINTS (monthly/annual). Metadata fields (GHI, P50/P90)
# have no single-value home and live only in the header design_points block.
# ---------------------------------------------------------------------------
HEADER_COLUMN = "header_column"  # -> weather_adjusted_model header column
POINTS_MONTHLY = "points_monthly"  # -> design_estimate monthly point
POINTS_ANNUAL = "points_annual"  # -> design_estimate annual point
METADATA = "metadata"  # -> header design_points block only
NONE = "none"  # not represented on any baseline

# Which baseline_type a target reconciles against (keeps the two "expected"
# notions separate — see telemetry-expected-baseline-design memory).
HEADER_BASELINE_TYPE = "weather_adjusted_model"
POINTS_BASELINE_TYPE = "design_estimate"


@dataclass(frozen=True)
class ReconciliationField:
    """One catalog field to reconcile across the audit chain."""

    canonical_name: str  # normalized canonical_fields.name
    display_label: str
    category: str
    baseline_target: str
    # 1-12 for a monthly production point; None otherwise.
    month: Optional[int] = None
    # True for fields whose absence blocks the weather-adjusted baseline.
    required_for_baseline: bool = False


_MONTH_LABELS = (
    "January",
    "February",
    "March",
    "April",
    "May",
    "June",
    "July",
    "August",
    "September",
    "October",
    "November",
    "December",
)


def _monthly_production_fields() -> list[ReconciliationField]:
    fields: list[ReconciliationField] = []
    for idx, label in enumerate(_MONTH_LABELS, start=1):
        fields.append(
            ReconciliationField(
                canonical_name=f"{label.lower()}_estimated_production_year_1",
                display_label=f"{label} Estimated Production (Year 1)",
                category=DESIGN_ESTIMATE,
                baseline_target=POINTS_MONTHLY,
                month=idx,
            )
        )
    return fields


def _monthly_ghi_fields() -> list[ReconciliationField]:
    fields: list[ReconciliationField] = []
    for label in _MONTH_LABELS:
        fields.append(
            ReconciliationField(
                canonical_name=(
                    f"{label.lower()}_estimated_ghi_irradiance_per_meter_squared"
                ),
                display_label=f"{label} Estimated GHI Irradiance (kWh/m²)",
                category=WEATHER,
                baseline_target=METADATA,
            )
        )
    return fields


# Physics nameplate — the four baseline-driving facts captured today. They land
# on the weather-adjusted baseline header and block the calc when absent.
_PHYSICS_FIELDS: list[ReconciliationField] = [
    ReconciliationField(
        "module_wattage", "Module Wattage", BASELINE_PHYSICS, HEADER_COLUMN,
        required_for_baseline=True,
    ),
    ReconciliationField(
        "module_quantity", "Module Quantity", BASELINE_PHYSICS, HEADER_COLUMN,
        required_for_baseline=True,
    ),
    ReconciliationField(
        "inverter_wattage", "Inverter Wattage", BASELINE_PHYSICS, HEADER_COLUMN,
        required_for_baseline=True,
    ),
    ReconciliationField(
        "inverter_quantity", "Inverter Quantity", BASELINE_PHYSICS, HEADER_COLUMN,
        required_for_baseline=True,
    ),
]

# Design-estimate production scenarios — metadata only (a single-value point row
# cannot hold P50 and P90 for the same period).
_SCENARIO_FIELDS: list[ReconciliationField] = [
    ReconciliationField("p50_mwh", "P50 Annual Production (MWh)", DESIGN_ESTIMATE, METADATA),
    ReconciliationField("p90_mwh", "P90 Annual Production (MWh)", DESIGN_ESTIMATE, METADATA),
    ReconciliationField(
        "statistical_standard_p50_or_p90",
        "Statistical Standard (P50/P90)",
        DESIGN_ESTIMATE,
        METADATA,
    ),
]

_ANNUAL_FIELDS: list[ReconciliationField] = [
    ReconciliationField(
        "estimated_production_year_1",
        "Annual Estimated Production (Year 1)",
        DESIGN_ESTIMATE,
        POINTS_ANNUAL,
    ),
    ReconciliationField(
        "annual_estimated_ghi_irradiance_per_meter_squared",
        "Annual Estimated GHI Irradiance (kWh/m²)",
        WEATHER,
        METADATA,
    ),
]

# Ordered catalog: physics, then monthly + annual production, then GHI + scenarios.
RECONCILIATION_CATALOG: tuple[ReconciliationField, ...] = tuple(
    _PHYSICS_FIELDS
    + _monthly_production_fields()
    + [_ANNUAL_FIELDS[0]]
    + _monthly_ghi_fields()
    + [_ANNUAL_FIELDS[1]]
    + _SCENARIO_FIELDS
)

# Fast lookup + membership set for the service / catch-all dedupe.
CATALOG_BY_NAME: dict[str, ReconciliationField] = {
    f.canonical_name: f for f in RECONCILIATION_CATALOG
}
CATALOG_FIELD_NAMES: frozenset[str] = frozenset(CATALOG_BY_NAME)

# Canonical field name -> SiteAdditionalFieldList attribute, for DISPLAY-ONLY
# legacy comparison. Loss percentages are mixed-sign in legacy data, so the
# service compares them via abs() (mirroring create_draft's normalization).
# Legacy values are NEVER used to build a V2 baseline — comparison only.
SAFL_FIELD_MAP: dict[str, str] = {
    "dc_loss_pct": "dc_wiring_loss",
    "ac_loss_pct": "ac_wiring_loss",
    "medium_voltage_loss_pct": "medium_voltage_loss",
    "mv_line_loss_pct": "mv_line_loss",
    "pto_date": "permission_to_operate",
    "permission_to_operate": "permission_to_operate",
    "placed_in_service_date": "placed_in_service_date",
    "financial_close_date": "financial_close_date",
    "battery_storage": "battery_storage",
    "mount_type": "mount_type",
}

# Loss canonical names whose legacy comparison must be done on magnitude only.
ABS_COMPARE_FIELDS: frozenset[str] = frozenset(
    {"dc_loss_pct", "ac_loss_pct", "medium_voltage_loss_pct", "mv_line_loss_pct"}
)
