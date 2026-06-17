import React from 'react';
import Chip from '@mui/material/Chip';
import type { ChipProps } from '@mui/material/Chip';
import Tooltip from '@mui/material/Tooltip';

import type {
  DeviceEligibilityDiagnostic,
  DiagnosticBlockingLevel,
  DiagnosticIndicator
} from '../../types/telemetryV2';

/**
 * Shared, read-only telemetry device-diagnostics UI helpers.
 *
 * These are derived strictly from the Path-B eligibility-diagnostics response
 * (`DeviceEligibilityDiagnostic`). Nothing here mutates eligibility, mapping,
 * weather semantics, the resolver, or the expected math; it only renders what
 * the backend already disclosed. Honest "Unavailable" states are produced when
 * a device has no diagnostics entry — we never fabricate a status.
 */

// ---------------------------------------------------------------------------
// Category filter grouping (frontend-owned). Each group maps a UI button to a
// set of DeviceCategories VALUES; the backend filters `Device.category.in_(...)`.
// FastAPI coerces the query param by enum VALUE, so we send values (e.g.
// "Inverter"), not enum names. An empty `categories` list means "no filter".
// ---------------------------------------------------------------------------

export interface DeviceCategoryGroup {
  key: string;
  label: string;
  categories: string[];
}

export const DEVICE_CATEGORY_GROUPS: DeviceCategoryGroup[] = [
  { key: 'all', label: 'All', categories: [] },
  { key: 'inverters', label: 'Inverters', categories: ['Inverter'] },
  { key: 'production_meters', label: 'Production meters', categories: ['Meter'] },
  { key: 'weather', label: 'Weather', categories: ['Weather Station'] },
  { key: 'gateways_das', label: 'Gateways / DAS', categories: ['MBOD Gateway', 'Network Gateway'] },
  { key: 'data_captures', label: 'Data captures', categories: ['Modem', 'Network Connection', 'Combiner Box'] }
];

/** Resolve the DeviceCategories VALUES for a given group key (empty = All). */
export const categoriesForGroupKey = (key: string): string[] => {
  const group = DEVICE_CATEGORY_GROUPS.find(g => g.key === key);
  return group ? group.categories : [];
};

// ---------------------------------------------------------------------------
// Path-B blocking-level presentation (shared with EligibilityDiagnosticsPanel).
// ---------------------------------------------------------------------------

export const blockingMeta: Record<
  DiagnosticBlockingLevel,
  { label: string; color: ChipProps['color']; severity: 'error' | 'warning' | 'info' }
> = {
  blocks_calculation: { label: 'Blocks calculation', color: 'error', severity: 'error' },
  lowers_confidence: { label: 'Lowers confidence', color: 'warning', severity: 'warning' },
  informational: { label: 'Informational', color: 'default', severity: 'info' }
};

export const IndicatorChip: React.FC<{ indicator: DiagnosticIndicator }> = ({ indicator }) => {
  const meta = blockingMeta[indicator.blocking_level] ?? blockingMeta.informational;
  const tooltip = indicator.recommended_action
    ? `${indicator.explanation} — Next: ${indicator.recommended_action}`
    : indicator.explanation;
  return (
    <Tooltip title={tooltip} arrow>
      <Chip size="small" color={meta.color} variant="outlined" label={indicator.label} sx={{ mr: 0.5, mb: 0.5 }} />
    </Tooltip>
  );
};

/** Human label for what a device is eligible to do (its telemetry role). */
export const roleLabel = (device: DeviceEligibilityDiagnostic): string => {
  if (device.can_drive_expected) return 'Expected driver';
  if (device.weather_source_capable) return 'Weather source';
  if (device.production_meter_capable) return 'Meter (inspection-only)';
  if (device.gateway_capable) return 'Gateway / logger';
  if (device.virtual_device) return 'Virtual aggregation';
  if (device.mappable) return 'Mappable';
  return 'Not eligible';
};

/** Compact, verbatim weather-semantics label (never inferred or converted). */
export const weatherSemanticsLabel = (device: DeviceEligibilityDiagnostic): string | null => {
  const s = device.weather_semantics;
  if (!s) return null;
  if (!s.has_declaration) return 'Semantics undeclared';
  const parts: string[] = [];
  if (s.irradiance_plane && s.irradiance_plane !== 'unknown') parts.push(`plane: ${s.irradiance_plane}`);
  if (s.temperature_type && s.temperature_type !== 'unknown') parts.push(`temp: ${s.temperature_type}`);
  if (s.calibration_status && s.calibration_status !== 'unknown') parts.push(`cal: ${s.calibration_status}`);
  return parts.length ? parts.join(', ') : 'Semantics unknown';
};

// ---------------------------------------------------------------------------
// Grid chip derivation. Each returns an honest "Unavailable" chip when the
// device has no diagnostics entry (e.g. diagnostics still loading or the device
// is absent from the response) — we never fabricate Mapped/eligible.
// ---------------------------------------------------------------------------

export interface DerivedChip {
  label: string;
  color: ChipProps['color'];
  variant: ChipProps['variant'];
}

export const UNAVAILABLE_CHIP: DerivedChip = { label: 'Unavailable', color: 'default', variant: 'outlined' };

/** Eligibility / role chip for the PH Devices grid. */
export const deriveEligibilityChip = (diag?: DeviceEligibilityDiagnostic): DerivedChip => {
  if (!diag) return UNAVAILABLE_CHIP;
  const color: ChipProps['color'] = diag.can_drive_expected ? 'primary' : diag.mappable ? 'info' : 'default';
  return { label: roleLabel(diag), color, variant: 'outlined' };
};

/**
 * V2 telemetry status / liveness chip, derived from `mapped_status`:
 *  - mapped            -> "Mapped" (telemetry mapping row exists)
 *  - unmapped_eligible -> "Missing telemetry" (mappable but not mapped yet)
 *  - ineligible        -> "Not mappable"
 */
export const deriveTelemetryStatusChip = (diag?: DeviceEligibilityDiagnostic): DerivedChip => {
  if (!diag) return UNAVAILABLE_CHIP;
  switch (diag.mapped_status) {
    case 'mapped':
      return { label: 'Mapped', color: 'success', variant: 'filled' };
    case 'unmapped_eligible':
      return { label: 'Missing telemetry', color: 'warning', variant: 'outlined' };
    case 'ineligible':
      return { label: 'Not mappable', color: 'default', variant: 'outlined' };
    default:
      return UNAVAILABLE_CHIP;
  }
};

// ---------------------------------------------------------------------------
// Safe CSV export (exports ALL matching rows, not just the current page).
// ---------------------------------------------------------------------------

export interface DeviceCsvRow {
  id: number;
  asset_id?: string | null;
  name?: string | null;
  category?: string | null;
  status?: string | null;
  das_connection_status?: string | null;
  manufacturer?: string | null;
  capacity?: number | null;
  type?: string | null;
  model?: string | null;
  serial_number?: string | null;
}

interface CsvColumn {
  header: string;
  value: (row: DeviceCsvRow, diag?: DeviceEligibilityDiagnostic) => string;
}

const stringifyCell = (value: unknown): string => {
  if (value === null || value === undefined) return '';
  return String(value);
};

export const DEVICE_CSV_COLUMNS: CsvColumn[] = [
  { header: 'Asset ID', value: row => stringifyCell(row.asset_id) },
  { header: 'Device Name', value: row => stringifyCell(row.name) },
  { header: 'Category', value: row => stringifyCell(row.category) },
  { header: 'Device Status', value: row => stringifyCell(row.status) },
  { header: 'Connection Status', value: row => stringifyCell(row.das_connection_status) },
  { header: 'Manufacturer', value: row => stringifyCell(row.manufacturer) },
  { header: 'Capacity', value: row => (typeof row.capacity === 'number' ? String(row.capacity) : '') },
  { header: 'Device Type', value: row => stringifyCell(row.type) },
  { header: 'Model', value: row => stringifyCell(row.model) },
  { header: 'Serial Number', value: row => stringifyCell(row.serial_number) },
  { header: 'Eligibility', value: (_row, diag) => deriveEligibilityChip(diag).label },
  { header: 'Telemetry Status', value: (_row, diag) => deriveTelemetryStatusChip(diag).label }
];

/** RFC-4180-ish escaping: quote fields containing comma, quote, or newline. */
export const escapeCsvField = (field: string): string => {
  if (/[",\n\r]/.test(field)) {
    return `"${field.replace(/"/g, '""')}"`;
  }
  return field;
};

/**
 * Build a CSV string for the given devices, merging in each device's Path-B
 * diagnostics (Eligibility + Telemetry Status). Devices absent from `diagMap`
 * render an honest "Unavailable" for the diagnostics columns.
 */
export const buildDevicesCsv = (devices: DeviceCsvRow[], diagMap: Map<number, DeviceEligibilityDiagnostic>): string => {
  const header = DEVICE_CSV_COLUMNS.map(col => escapeCsvField(col.header)).join(',');
  const rows = devices.map(device => {
    const diag = diagMap.get(device.id);
    return DEVICE_CSV_COLUMNS.map(col => escapeCsvField(col.value(device, diag))).join(',');
  });
  return [header, ...rows].join('\n');
};
