import type {
  ReconciliationCategory,
  ReconciliationStatus,
  ReconciliationValue,
  ReconciliationWarning
} from '../../../../../../api';

/**
 * Display ordering + labels for diligence categories. The list is the canonical
 * render order; unknown categories fall through to "Other".
 */
export const CATEGORY_ORDER: (ReconciliationCategory | string)[] = [
  'baseline_physics',
  'design_estimate',
  'weather',
  'legal_commercial',
  'equipment',
  'warranty_permit_insurance',
  'other'
];

export const CATEGORY_LABELS: Record<string, string> = {
  baseline_physics: 'Baseline Physics',
  design_estimate: 'Design Estimate',
  weather: 'Weather',
  legal_commercial: 'Legal & Commercial',
  equipment: 'Equipment',
  warranty_permit_insurance: 'Warranty, Permit & Insurance',
  other: 'Other'
};

export const categoryLabel = (category: string): string =>
  CATEGORY_LABELS[category] || category.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

export interface StatusMeta {
  label: string;
  color: 'default' | 'info' | 'primary' | 'success' | 'warning';
  description: string;
}

export const STATUS_META: Record<string, StatusMeta> = {
  missing: {
    label: 'Missing',
    color: 'default',
    description: 'No source-backed value has been captured for this field yet.'
  },
  candidate_only: {
    label: 'Candidate only',
    color: 'warning',
    description: 'A value was extracted but not yet promoted to an active assumption.'
  },
  active_fact: {
    label: 'Active fact',
    color: 'info',
    description: 'A promoted (active) project fact exists, but it is not yet on a baseline.'
  },
  in_draft_baseline: {
    label: 'In draft baseline',
    color: 'primary',
    description: 'The value is reflected on a draft baseline that is not yet active.'
  },
  in_active_baseline: {
    label: 'In active baseline',
    color: 'success',
    description: 'The value is on the active baseline that drives expected output.'
  }
};

export const statusMeta = (status: string): StatusMeta =>
  STATUS_META[status] || { label: status, color: 'default', description: 'Unrecognized status.' };

export interface WarningMeta {
  label: string;
  description: string;
}

export const WARNING_META: Record<string, WarningMeta> = {
  missing_required_for_baseline: {
    label: 'Required value missing',
    description: 'This field is required for the weather-adjusted baseline but has no source-backed value.'
  },
  fact_differs_from_legacy: {
    label: 'Differs from legacy',
    description: 'The active fact differs from the legacy site field value.'
  },
  draft_differs_from_active: {
    label: 'Draft ≠ active',
    description: 'The draft baseline value differs from the active baseline value.'
  },
  active_baseline_outdated: {
    label: 'Active baseline outdated',
    description: 'A newer fact or draft suggests the active baseline may be stale.'
  },
  design_points_missing: {
    label: 'Design points missing',
    description: 'Monthly design-estimate production points are incomplete.'
  },
  needs_review: {
    label: 'Needs review',
    description: 'A reviewer should look at this field before it is relied upon.'
  }
};

export const warningMeta = (warning: string): WarningMeta =>
  WARNING_META[warning] || { label: warning.replace(/_/g, ' '), description: 'Unrecognized warning.' };

export const PLACEHOLDER = '—';

/**
 * Format a reconciliation value column for display. Values are intentionally
 * loosely typed (the backend emits Optional[Any]); this never throws.
 */
export const formatValue = (value: ReconciliationValue | undefined): string => {
  if (value === null || value === undefined || value === '') return PLACEHOLDER;
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (typeof value === 'number') return Number.isFinite(value) ? value.toLocaleString() : PLACEHOLDER;
  return String(value);
};

export const formatConfidence = (confidence: number | null): string => {
  if (confidence === null || confidence === undefined || !Number.isFinite(confidence)) return PLACEHOLDER;
  const pct = confidence <= 1 ? confidence * 100 : confidence;
  return `${Math.round(pct)}%`;
};

export const formatDateTime = (value: string | null): string => {
  if (!value) return PLACEHOLDER;
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
};

export type { ReconciliationStatus, ReconciliationWarning };
