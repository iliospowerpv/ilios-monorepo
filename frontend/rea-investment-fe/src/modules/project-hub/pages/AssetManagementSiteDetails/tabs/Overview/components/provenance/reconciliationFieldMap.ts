import type { ReconciliationRow, ReconciliationValue } from '../../../../../../../../api';

/**
 * Phase 3 — LIVE provenance for protected Overview fields.
 *
 * This module is intentionally pure (no React) so the field → reconciliation
 * mapping and the display value-precedence logic can be unit-tested in isolation
 * and reused by the context provider and the `ProtectedField` component.
 *
 * It performs NO writes, NO fetches and NO backend calls. It only translates a
 * read-only `SiteReconciliationResponse.rows` array (already fetched by the
 * provider) into the row that backs a given Overview field, and decides which
 * value to display under the documented precedence.
 */

/**
 * Maps each protected Overview field key to the candidate reconciliation
 * identifiers it may resolve to. Lookups try, in order: the canonical_field of a
 * row, then any alias the backend reports in `aliases_matched`. Because the
 * resolver also checks aliases, a wrong/extra canonical guess simply fails to
 * match and the field degrades gracefully to its static label — it never throws
 * or shows a wrong row.
 *
 * The first candidate is the backend's expected canonical_field; the trailing
 * candidates are defensive aliases (including the Overview key itself) so the
 * mapping is resilient to backend canonicalization differences.
 */
export const OVERVIEW_FIELD_TO_RECON: Record<string, string[]> = {
  // Asset Overview — baseline-driving ohmic losses
  dc_wiring_loss: ['dc_loss_pct', 'dc_wiring_loss', 'dc_ohmic_loss', 'dc_ohmic_wiring_loss'],
  ac_wiring_loss: ['ac_loss_pct', 'ac_wiring_loss', 'ac_ohmic_loss', 'ac_ohmic_wiring_loss'],
  medium_voltage_loss: ['medium_voltage_loss_pct', 'medium_voltage_loss', 'mv_transfo_loss', 'medium_voltage_transfo_loss'],
  mv_line_loss: ['mv_line_loss_pct', 'mv_line_loss', 'mv_line_ohmic_loss'],

  // Asset Overview — source (Data Room) descriptive fields
  module_quantity: ['module_quantity', 'modules_quantity', 'number_of_modules'],
  inverter_quantity: ['inverter_quantity', 'inverters_quantity', 'number_of_inverters'],
  project_type: ['project_type', 'system_type'],

  // Key Dates
  permission_to_operate: ['pto_date', 'permission_to_operate', 'pto'],

  // Site Level Details
  system_size_dc: ['system_size_dc', 'system_size_dc_kw', 'dc_system_size', 'system_size_kw_dc'],
  system_size_ac: ['system_size_ac', 'system_size_ac_kw', 'ac_system_size', 'system_size_kw_ac'],
  year_one_expected_production: [
    'estimated_production_year_1',
    'year_one_expected_production',
    'year_1_expected_production',
    'estimated_generation',
    'expected_production_year_1'
  ],
  degradation_amount: ['degradation_amount', 'degradation_rate', 'annual_degradation', 'degradation']
};

const normalizeKey = (value: string): string => value.trim().toLowerCase();

/**
 * Builds a case-insensitive lookup keyed by every row's canonical_field and each
 * of its matched aliases. Earlier rows win on key collisions, mirroring the
 * order the backend returns rows in. Pure and side-effect free.
 */
export const buildReconciliationIndex = (
  rows: readonly ReconciliationRow[] | null | undefined
): Map<string, ReconciliationRow> => {
  const index = new Map<string, ReconciliationRow>();
  if (!rows) return index;

  for (const row of rows) {
    const keys: string[] = [];
    if (row.canonical_field) keys.push(row.canonical_field);
    if (Array.isArray(row.aliases_matched)) keys.push(...row.aliases_matched);

    for (const key of keys) {
      if (!key) continue;
      const norm = normalizeKey(key);
      if (!index.has(norm)) index.set(norm, row);
    }
  }

  return index;
};

/**
 * Resolves the reconciliation row backing an Overview field, trying each mapped
 * candidate (and finally the raw field name) against the index. Returns
 * `undefined` when no row matches — the caller then degrades to the static label.
 */
export const resolveReconciliationRow = (
  index: Map<string, ReconciliationRow>,
  field: string
): ReconciliationRow | undefined => {
  const candidates = OVERVIEW_FIELD_TO_RECON[field] ?? [field];
  for (const candidate of candidates) {
    const hit = index.get(normalizeKey(candidate));
    if (hit) return hit;
  }
  return index.get(normalizeKey(field));
};

/** Where the displayed value came from, in precedence order. */
export type ProtectedValueSource = 'active_fact' | 'accepted' | 'ai_extracted' | 'legacy' | 'fallback';

/**
 * Human-readable qualifier captions shown beneath a value when the displayed
 * value is NOT the current active project truth. `active_fact` (the truth) and
 * the card `fallback` carry no qualifier.
 */
export const PROTECTED_VALUE_QUALIFIERS: Record<ProtectedValueSource, string | null> = {
  active_fact: null,
  accepted: 'Accepted, not promoted',
  ai_extracted: 'Review required',
  legacy: 'Legacy / display-only — not active project truth',
  fallback: null
};

export interface ResolvedProtectedValue {
  value: ReconciliationValue | undefined;
  source: ProtectedValueSource;
  qualifier: string | null;
}

/**
 * A value is "present" when it is not null, undefined, or an empty/whitespace
 * string. Crucially `0` and `false` ARE present, so a 0% loss or a falsey flag
 * displays correctly rather than being skipped by a truthiness check.
 */
const isPresent = (value: ReconciliationValue | undefined): boolean => {
  if (value === null || value === undefined) return false;
  if (typeof value === 'string' && value.trim() === '') return false;
  return true;
};

/**
 * Picks the value to DISPLAY for a protected field under the documented
 * precedence:
 *   active_fact_value → accepted_value → ai_extracted_value → legacy_value → fallback
 *
 * `fallback` is the card's own current value, so when the user cannot view
 * reconciliation, no row matches, or a matched row carries none of the precedence
 * values, the field shows EXACTLY what it shows today (zero regression). It never
 * blanks out an existing value.
 */
export const resolveProtectedValue = (
  row: ReconciliationRow | undefined,
  fallback: ReconciliationValue | undefined,
  canView: boolean
): ResolvedProtectedValue => {
  if (!canView || !row) {
    return { value: fallback, source: 'fallback', qualifier: null };
  }
  if (isPresent(row.active_fact_value)) {
    return { value: row.active_fact_value, source: 'active_fact', qualifier: PROTECTED_VALUE_QUALIFIERS.active_fact };
  }
  if (isPresent(row.accepted_value)) {
    return { value: row.accepted_value, source: 'accepted', qualifier: PROTECTED_VALUE_QUALIFIERS.accepted };
  }
  if (isPresent(row.ai_extracted_value)) {
    return { value: row.ai_extracted_value, source: 'ai_extracted', qualifier: PROTECTED_VALUE_QUALIFIERS.ai_extracted };
  }
  if (isPresent(row.legacy_value)) {
    return { value: row.legacy_value, source: 'legacy', qualifier: PROTECTED_VALUE_QUALIFIERS.legacy };
  }
  return { value: fallback, source: 'fallback', qualifier: null };
};
