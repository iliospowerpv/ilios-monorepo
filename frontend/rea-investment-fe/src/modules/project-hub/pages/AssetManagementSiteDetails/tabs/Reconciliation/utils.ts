import type {
  ReconciliationCategory,
  ReconciliationRow,
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

/**
 * Per-status display metadata. The ladder runs from least-advanced (missing) to
 * most-advanced (in_active_baseline). `label`/`description` are UI fallbacks —
 * when the backend supplies `status_label`/`status_explanation` for a row those
 * take precedence (see {@link statusMeta} consumers).
 */
export const STATUS_META: Record<string, StatusMeta> = {
  missing: {
    label: 'Missing',
    color: 'default',
    description: 'No source-backed value has been captured anywhere in the chain for this field yet.'
  },
  ai_extracted_only: {
    label: 'AI extracted (unreviewed)',
    color: 'warning',
    description: 'The AI read a value from the document, but no reviewer has accepted it yet.'
  },
  accepted_document_value: {
    label: 'Accepted (no project fact)',
    color: 'warning',
    description: 'A reviewer accepted a document value, but no project fact was created from it.'
  },
  candidate_only: {
    label: 'Candidate (not accepted)',
    color: 'warning',
    description: 'A candidate fact exists from extraction, but no reviewer has accepted it yet.'
  },
  accepted_not_promoted: {
    label: 'Accepted, not promoted',
    color: 'info',
    description: 'A reviewer accepted or overrode this value, but it is not yet a promoted assumption.'
  },
  active_fact: {
    label: 'Promoted assumption',
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
  },
  superseded: {
    label: 'Superseded',
    color: 'default',
    description: 'Only superseded (retired) values remain; there is no current active value.'
  }
};

export const statusMeta = (status: string): StatusMeta =>
  STATUS_META[status] || { label: status, color: 'default', description: 'Unrecognized status.' };

/**
 * Statuses whose next step (acceptance / promotion) is performed in the Data
 * Room. Baseline-activation steps have no dedicated route, so callers show the
 * required-action text without a link rather than pointing at a non-existent
 * page. Shared by the Reconciliation table and the Overview ProtectedField note.
 */
export const ACTIONS_IN_DATA_ROOM = new Set<string>([
  'missing',
  'ai_extracted_only',
  'accepted_document_value',
  'candidate_only',
  'accepted_not_promoted',
  'superseded'
]);

export type BlockingColor = 'default' | 'info' | 'warning' | 'error';

export interface BlockingMeta {
  label: string;
  color: BlockingColor;
  description: string;
}

/**
 * The single most-severe impact a row's gaps currently have. Severity descends
 * from baseline-blocking (error) to purely informational (default).
 */
export const BLOCKING_META: Record<string, BlockingMeta> = {
  blocks_baseline: {
    label: 'Blocks baseline',
    color: 'error',
    description: 'A required value is missing, so the weather-adjusted baseline cannot be built.'
  },
  blocks_expected: {
    label: 'Blocks expected',
    color: 'error',
    description: 'Design-estimate points are missing, so expected production cannot be computed.'
  },
  blocks_reporting: {
    label: 'Blocks reporting',
    color: 'warning',
    description: 'The active baseline diverges from the latest values, so reporting may be stale.'
  },
  lowers_confidence: {
    label: 'Lowers confidence',
    color: 'warning',
    description: 'A divergence or unreviewed conflict reduces confidence in this value.'
  },
  informational: {
    label: 'Informational',
    color: 'default',
    description: 'A noted difference that does not block anything downstream.'
  }
};

export const blockingMeta = (level: string): BlockingMeta =>
  BLOCKING_META[level] || { label: level.replace(/_/g, ' '), color: 'default', description: 'Unrecognized impact.' };

/** Human labels for the ordered pipeline stages still pending for a row. */
export const MISSING_DEPENDENCY_LABELS: Record<string, string> = {
  source_value: 'Source value',
  acceptance: 'Acceptance',
  project_fact: 'Project fact',
  promotion: 'Promotion',
  baseline: 'Baseline',
  baseline_activation: 'Baseline activation',
  current_value: 'Current value'
};

export const missingDependencyLabel = (dep: string): string =>
  MISSING_DEPENDENCY_LABELS[dep] || dep.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

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

/**
 * The single status from which an in-place Promote action is genuinely the next
 * step. Acceptance/override still happen in the Data Room — Reconciliation only
 * ever offers the promote step, and only for an accepted-but-unpromoted value.
 */
export const PROMOTABLE_STATUS = 'accepted_not_promoted';

/**
 * Whether a row may launch the (file-version-scoped) Promote flow. Requires the
 * accepted-not-promoted status AND both ids the promote endpoint needs
 * (`document_id` + `document_version_id` → the source File). The caller must
 * still hold `Diligence:edit`; this predicate is permission-agnostic.
 */
export const canPromoteRow = (row: ReconciliationRow): boolean =>
  row.status === PROMOTABLE_STATUS && row.document_id != null && row.document_version_id != null;

/**
 * Whether a row can hand its next step off as a tracked task. Offered more
 * broadly than Promote — on any row that has a real next step (`required_action`
 * present), regardless of status. Permission-agnostic (caller gates on edit).
 */
export const canCreateTaskRow = (row: ReconciliationRow): boolean => Boolean(row.required_action);

/**
 * Map a failed promote request to an honest, user-facing message. The backend
 * raises every `PromotionError` as HTTP 400 with a human `detail` string (not a
 * code), so we match on status + message text. Validation mismatches mean the
 * version is stale; everything else means the atomic promotion rolled back and
 * nothing changed.
 */
export const promotionErrorMessage = (error: unknown): string => {
  const axiosError = error as { response?: { status?: number; data?: { detail?: string } } };
  const status = axiosError?.response?.status;
  const detail = axiosError?.response?.data?.detail ?? '';

  if (status === 403) {
    return 'You do not have permission to promote assumptions for this project.';
  }
  if (status === 404 || /file not found/i.test(detail) || /does not belong/i.test(detail)) {
    return 'This version is no longer valid for promotion; refresh and try again.';
  }
  return 'Promotion failed and nothing was changed.';
};

export type { ReconciliationStatus, ReconciliationWarning };
