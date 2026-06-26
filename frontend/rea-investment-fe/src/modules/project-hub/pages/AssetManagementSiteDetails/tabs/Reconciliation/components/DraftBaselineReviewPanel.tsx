import React, { useEffect, useMemo, useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import Grid from '@mui/material/Grid';
import Chip from '@mui/material/Chip';
import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import Divider from '@mui/material/Divider';
import TextField from '@mui/material/TextField';
import MenuItem from '@mui/material/MenuItem';
import Tooltip from '@mui/material/Tooltip';
import Button from '@mui/material/Button';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import CircularProgress from '@mui/material/CircularProgress';
import Checkbox from '@mui/material/Checkbox';
import FormGroup from '@mui/material/FormGroup';
import FormControlLabel from '@mui/material/FormControlLabel';
import LockOutlinedIcon from '@mui/icons-material/LockOutlined';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import HistoryOutlinedIcon from '@mui/icons-material/HistoryOutlined';

import { ApiClient } from '../../../../../../../api';
import type { SourceBasisDrift } from '../../../../../../../api';
import type {
  ActiveExpectedBaselineResponse,
  BaselineDiffResponse,
  BaselineFieldDiff,
  BaselineFieldSource,
  BaselinePhysicsValidation,
  ExpectedBaselineListResponse,
  ExpectedBaselineResponse
} from '../../../../../../../types/telemetryV2';
import { useTelemetryAdminPermission } from '../../../../../../../hooks/useTelemetryAdminPermission';
import { useNotify } from '../../../../../../../contexts/notifications/notifications';
import { PLACEHOLDER, formatConfidence, formatDateTime } from '../utils';
import DraftPreviewOverlay from './DraftPreviewOverlay';
import ValidationSummaryPanel from './ValidationSummaryPanel';
import ActivationReadinessSummary from './ActivationReadinessSummary';
import ValidationHistoryPanel from './ValidationHistoryPanel';
import { blockReasonExplainer } from '../../../../../../../utils/baselineValidation';

interface DraftBaselineReviewPanelProps {
  siteId: number;
  /**
   * Backend-computed lifecycle capability (telemetry-admin AND company-admin),
   * threaded from the loaded active response. When omitted, the panel falls back
   * to the flag on its own active-baseline fetch. Approve/activate/acknowledge
   * are gated on this — never on a locally re-derived company-admin guess.
   */
  canManageLifecycle?: boolean;
  /**
   * Read-only source-basis drift verdict (Phase B4), threaded from the
   * reconciliation readiness so the version-history panel can badge the active
   * baseline row. Display only — introduces no mutation affordance.
   */
  sourceBasisDrift?: SourceBasisDrift | null;
}

// Only the weather-adjusted model drives the live expected calc; the review
// panel is intentionally scoped to it (design-estimate is a separate track).
const WEATHER_ADJUSTED = 'weather_adjusted_model';

// Approve/activate now require telemetry-admin AND company-admin (Phase 0). The
// disabled button keeps lifecycle state visible but never fires a doomed 403 —
// the read-only explanation below it spells out the missing access.
const PERMISSION_TOOLTIP =
  'Approving or activating requires Telemetry admin AND Company admin access for this company.';

interface FieldDef {
  col: keyof ExpectedBaselineResponse;
  label: string;
  unit?: string;
}

// Equipment physics that come from promoted project_facts.
const FACT_FIELDS: FieldDef[] = [
  { col: 'module_wattage', label: 'Module Wattage', unit: 'W' },
  { col: 'module_quantity', label: 'Module Quantity' },
  { col: 'inverter_wattage', label: 'Inverter Wattage', unit: 'kW' },
  { col: 'inverter_quantity', label: 'Inverter Quantity' }
];

// Datasheet constants the reviewer supplies (no fact source exists).
const REVIEWER_REQUIRED_FIELDS: FieldDef[] = [
  { col: 'thermal_coefficient_pct', label: 'Thermal Coefficient', unit: '%/°C' },
  { col: 'power_tolerance_min_pct', label: 'Power Tolerance (min)', unit: '%' },
  { col: 'year_1_degradation_pct', label: 'Year 1 Degradation', unit: '%' },
  { col: 'annual_degradation_pct', label: 'Annual Degradation', unit: '%' },
  { col: 'cec_efficiency_pct', label: 'CEC Efficiency', unit: '%' }
];

// Optional losses / soiling: when the reviewer leaves these blank the calc
// applies the documented default — which is reported here, NOT source-backed.
const OPTIONAL_DEFAULT_FIELDS: (FieldDef & { defaultLabel: string })[] = [
  { col: 'dc_loss_pct', label: 'DC Loss', unit: '%', defaultLabel: '0% (no loss)' },
  { col: 'ac_loss_pct', label: 'AC Loss', unit: '%', defaultLabel: '0% (no loss)' },
  { col: 'medium_voltage_loss_pct', label: 'Medium-Voltage Loss', unit: '%', defaultLabel: '0% (no loss)' },
  { col: 'mv_line_loss_pct', label: 'MV Line Loss', unit: '%', defaultLabel: '0% (no loss)' },
  { col: 'soiling_factor', label: 'Soiling Factor', defaultLabel: '1.0 (no soiling)' }
];

const baselinesQueryKey = (siteId: number) => ['site', 'expected-baselines', { siteId }] as const;
const activeBaselineQueryKey = (siteId: number) => ['site', 'expected-baseline-active', { siteId }] as const;
const reconciliationQueryKey = (siteId: number) => ['site', 'reconciliation', { siteId }] as const;

// O&M site-level queries whose expected/comparative series depend on the active
// weather-adjusted baseline. Activation must let them refetch (Scope G); we only
// invalidate (never recompute) — chart logic is untouched.
const omExpectedQueryKeys = (siteId: number) =>
  [
    ['telemetry-readiness', siteId],
    ['sites', 'past-performance', { siteId }],
    ['sites', 'actual-vs-projected-power', { siteId }]
  ] as const;

const statusChipColor = (status: string): 'default' | 'info' | 'primary' | 'success' | 'warning' | 'error' => {
  switch (status) {
    case 'active':
      return 'success';
    case 'approved':
      return 'primary';
    case 'in_review':
      return 'info';
    case 'rejected':
      return 'error';
    case 'draft':
    case 'superseded':
    default:
      return 'default';
  }
};

const statusLabel = (status: string): string => status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

const fmtNumber = (v: number | null | undefined): string =>
  v == null || !Number.isFinite(v) ? PLACEHOLDER : v.toLocaleString();

const fmtWithUnit = (v: number | null | undefined, unit?: string): string => {
  if (v == null || !Number.isFinite(v)) return PLACEHOLDER;
  return `${fmtNumber(v)}${unit ? ` ${unit}` : ''}`;
};

const originChip = (source: string | undefined): { label: string; color: 'success' | 'info' | 'default' } => {
  switch (source) {
    case 'project_fact':
      return { label: 'From facts', color: 'success' };
    case 'project_fact_normalized':
      return { label: 'Normalized', color: 'success' };
    case 'reviewer_supplied':
      return { label: 'Reviewer value', color: 'info' };
    default:
      return { label: source ?? 'Unknown source', color: 'default' };
  }
};

const numFieldOf = (b: ExpectedBaselineResponse, col: keyof ExpectedBaselineResponse): number | null => {
  const v = b[col];
  return typeof v === 'number' ? v : null;
};

// Structured 409 body returned by the fail-closed physics activation gate. A
// `hard_invalid` verdict can never be waived; the two `*_ack`/`*_note` reasons
// are warning-only and become activatable once the user acknowledges them with a
// source note.
type BaselineBlockBody = {
  reason?: string;
  blocking?: boolean;
  message?: string;
  summary?: string;
  warning_fields?: Array<{
    field?: string;
    reason?: string;
    required_action?: string | null;
    classification?: string;
  }>;
};

// Returns the structured physics-block body ONLY when it is a warning-only,
// acknowledgeable verdict (so the dialog can offer the ack + source-note path).
// `hard_invalid` and non-physics 409s return null and fall through to a notify.
const parseAcknowledgeableBlock = (err: unknown): BaselineBlockBody | null => {
  const resp = (err as { response?: { status?: number; data?: unknown } })?.response;
  if (resp?.status !== 409) return null;
  const data = resp.data as BaselineBlockBody | undefined;
  if (!data || typeof data !== 'object') return null;
  if (data.reason !== 'warnings_require_ack' && data.reason !== 'source_note_required') return null;
  return data;
};

// Map a backend failure to a clear, action-specific message (Scope I). Prefers
// the structured physics-gate message (e.g. a `hard_invalid` explanation) when
// the server provides one.
const actionErrorMessage = (action: 'approve' | 'activate', err: unknown): string => {
  const resp = (err as { response?: { status?: number; data?: { message?: string } } })?.response;
  const status = resp?.status;
  if (status === 401 || status === 403) return `You do not have permission to ${action} this baseline.`;
  if (status === 404) return 'Baseline not found. It may have been removed — refresh and try again.';
  if (status === 409) {
    if (resp?.data?.message) return resp.data.message;
    return action === 'activate'
      ? 'This baseline must be approved before activation. The baseline state changed — refresh and try again.'
      : 'The baseline state changed. Refresh and try again.';
  }
  return `Couldn't ${action} the baseline. Please try again.`;
};

// The design-estimate separation language required on every approve/activate
// confirmation (Scope H).
const DesignEstimateSeparationNote: React.FC = () => (
  <Alert severity="info" sx={{ mt: 1.5 }} data-testid="confirm-design-estimate-note">
    <Box component="ul" sx={{ pl: 3, mb: 0 }}>
      <li>
        <Typography variant="caption">This affects the weather-adjusted expected baseline only.</Typography>
      </li>
      <li>
        <Typography variant="caption">It does not create or change design-estimate points.</Typography>
      </li>
      <li>
        <Typography variant="caption">Design-estimate points remain a separate track.</Typography>
      </li>
    </Box>
  </Alert>
);

/**
 * Review + (permission-gated) approve / activate of weather-adjusted expected
 * baselines for a site.
 *
 * Surfaces draft, approved-not-active, active, and superseded baselines with
 * full provenance (promoted facts, reviewer constants, applied defaults, PTO
 * behavior, and `model_parameters_json` sources). Approve and Activate are two
 * SEPARATE explicit actions — each behind its own confirmation dialog. The panel
 * never previews a draft's expected curve (the preview endpoint refuses drafts),
 * never mutates project_facts / accepted values, never triggers a historical
 * backfill, and never touches design-estimate points.
 */
export const DraftBaselineReviewPanel: React.FC<DraftBaselineReviewPanelProps> = ({
  siteId,
  canManageLifecycle: canManageLifecycleProp,
  sourceBasisDrift = null
}) => {
  const enabled = Number.isSafeInteger(siteId) && siteId > 0;
  // Draft-authoring (create/preview a draft) is telemetry-admin + site access —
  // the FE mirrors it locally. This gates the now-tightened (telemetry-admin)
  // `list` query so a non-admin gets a clean read-only state, NOT a 403 toast.
  const canAuthorDraft = useTelemetryAdminPermission();
  const notify = useNotify();
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery<ExpectedBaselineListResponse>({
    queryKey: baselinesQueryKey(siteId),
    queryFn: () => ApiClient.telemetryV2.listExpectedBaselines(siteId),
    enabled: enabled && canAuthorDraft,
    retry: false
  });

  // Active baseline is fetched via the dedicated (site-access, NOT admin-gated)
  // read endpoint, enveloped with the backend capability flags. Its failure must
  // not blank the whole panel, so it is handled softly (the list drives
  // loading/error). Every site viewer can read this — so it is the source of
  // truth for `viewer_can_manage_lifecycle` even when `list` is forbidden.
  const { data: activeResponse } = useQuery<ActiveExpectedBaselineResponse>({
    queryKey: activeBaselineQueryKey(siteId),
    queryFn: () => ApiClient.telemetryV2.getActiveExpectedBaseline(siteId),
    enabled,
    retry: false
  });
  const activeBaseline = activeResponse?.baseline ?? null;

  // Approve / activate / acknowledge are gated on the BACKEND lifecycle flag
  // (telemetry-admin AND company-admin), preferring the value threaded from the
  // parent's loaded active response and falling back to this panel's own fetch.
  // The frontend never re-derives company-admin locally.
  const canManageLifecycle = canManageLifecycleProp ?? activeResponse?.viewer_can_manage_lifecycle ?? false;

  const drafts = useMemo(
    () =>
      (data?.baselines ?? []).filter(
        b => b.baseline_type === WEATHER_ADJUSTED && (b.status === 'draft' || b.status === 'in_review')
      ),
    [data]
  );
  const approvedNotActive = useMemo(
    () => (data?.baselines ?? []).filter(b => b.baseline_type === WEATHER_ADJUSTED && b.status === 'approved'),
    [data]
  );
  const listActive = useMemo(
    () => (data?.baselines ?? []).find(b => b.baseline_type === WEATHER_ADJUSTED && b.status === 'active') ?? null,
    [data]
  );
  const superseded = useMemo(
    () => (data?.baselines ?? []).filter(b => b.baseline_type === WEATHER_ADJUSTED && b.status === 'superseded'),
    [data]
  );
  const active = activeBaseline ?? listActive;

  const [selectedDraftId, setSelectedDraftId] = useState<number | null>(null);
  useEffect(() => {
    // Default to the most-recent draft (the list is newest-first) and keep a
    // valid selection if the chosen draft disappears on refetch.
    if (drafts.length === 0) {
      setSelectedDraftId(null);
      return;
    }
    setSelectedDraftId(prev => (prev != null && drafts.some(d => d.id === prev) ? prev : drafts[0].id));
  }, [drafts]);

  const selectedDraft = useMemo(() => drafts.find(d => d.id === selectedDraftId) ?? null, [drafts, selectedDraftId]);

  // Confirmation targets — approve and activate are intentionally separate.
  const [approveTarget, setApproveTarget] = useState<ExpectedBaselineResponse | null>(null);
  const [activateTarget, setActivateTarget] = useState<ExpectedBaselineResponse | null>(null);
  // Warning-only activation gate: when the server blocks activation with an
  // acknowledgeable verdict we keep the dialog open, surface the warnings, and
  // require a source note before re-submitting with `acknowledge_warnings`.
  const [activateWarnings, setActivateWarnings] = useState<BaselineBlockBody | null>(null);
  const [activateNote, setActivateNote] = useState('');
  // Per-warning acknowledgement checkboxes are VISUAL-ONLY (audit B2.7): they help
  // the reviewer read each warning deliberately but never gate submission. The
  // backend contract is unchanged — a single set-level `acknowledge_warnings`
  // plus the required source note below is what activates the baseline.
  const [ackedWarnings, setAckedWarnings] = useState<Record<string, boolean>>({});

  // All weather-adjusted versions (any status) for the read-only version history,
  // assembled from the EXISTING list rows — no new endpoint, no new fetch.
  const weatherAdjustedBaselines = useMemo(
    () => (data?.baselines ?? []).filter(b => b.baseline_type === WEATHER_ADJUSTED),
    [data]
  );

  // Replacement diff: compare the proposed replacement (the selected draft, or an
  // approved-but-not-active baseline) against the current active baseline. The
  // diff is read-only and carries the FULL fail-closed validation verdict for
  // BOTH baselines, so an invalid active baseline AND a valid replacement are
  // both visible. Skipped when there is no candidate or no active to compare.
  const diffCandidateId = selectedDraft?.id ?? approvedNotActive[0]?.id ?? null;
  const diffEnabled = enabled && diffCandidateId != null && active != null && diffCandidateId !== active.id;
  const {
    data: diff,
    isLoading: diffLoading,
    error: diffError
  } = useQuery<BaselineDiffResponse>({
    queryKey: ['site', 'expected-baseline-diff', { siteId, to: diffCandidateId, from: active?.id ?? null }],
    queryFn: () => ApiClient.telemetryV2.getBaselineDiff(diffCandidateId as number, active?.id),
    enabled: diffEnabled,
    retry: false
  });

  const approveMutation = useMutation<ExpectedBaselineResponse, unknown, number>({
    mutationFn: (baselineId: number) => ApiClient.telemetryV2.approveExpectedBaseline(baselineId),
    onSuccess: () => {
      // Approval only confirms inputs; it never activates. Refresh the baseline
      // list + readiness so the row moves to "approved (not yet active)".
      queryClient.invalidateQueries({ queryKey: baselinesQueryKey(siteId) });
      queryClient.invalidateQueries({ queryKey: reconciliationQueryKey(siteId) });
      notify('Baseline approved. It is not active yet.');
      setApproveTarget(null);
    },
    onError: err => {
      notify(actionErrorMessage('approve', err));
      setApproveTarget(null);
    }
  });

  const closeActivateDialog = () => {
    setActivateTarget(null);
    setActivateWarnings(null);
    setActivateNote('');
    setAckedWarnings({});
  };

  const activateMutation = useMutation<
    ExpectedBaselineResponse,
    unknown,
    { baselineId: number; acknowledgeWarnings?: boolean; activationSourceNote?: string }
  >({
    mutationFn: vars =>
      ApiClient.telemetryV2.activateExpectedBaseline(vars.baselineId, {
        acknowledgeWarnings: vars.acknowledgeWarnings,
        activationSourceNote: vars.activationSourceNote
      }),
    onSuccess: () => {
      // Let the active read, the list, readiness, and the expected-bearing O&M
      // site charts refetch. We invalidate only — no recompute / backfill.
      queryClient.invalidateQueries({ queryKey: baselinesQueryKey(siteId) });
      queryClient.invalidateQueries({ queryKey: activeBaselineQueryKey(siteId) });
      queryClient.invalidateQueries({ queryKey: reconciliationQueryKey(siteId) });
      omExpectedQueryKeys(siteId).forEach(key => queryClient.invalidateQueries({ queryKey: key }));
      notify('Baseline activated. O&M expected values now use this baseline from its activation boundary forward.');
      closeActivateDialog();
    },
    onError: err => {
      // A warning-only physics verdict is not a hard failure: keep the dialog
      // open, surface the warnings, and require an acknowledgment + source note
      // before re-submitting. Any other error (incl. `hard_invalid`) is final.
      const block = parseAcknowledgeableBlock(err);
      if (block) {
        setActivateWarnings(block);
        return;
      }
      notify(actionErrorMessage('activate', err));
      closeActivateDialog();
    }
  });

  if (!enabled) return null;

  if (isLoading) {
    return (
      <Box display="flex" alignItems="center" gap={1} sx={{ mt: 2 }} data-testid="draft-baseline-review-loading">
        <CircularProgress size={18} />
        <Typography variant="body2" color="text.secondary">
          Loading expected baselines…
        </Typography>
      </Box>
    );
  }

  if (error) {
    const status = (error as { response?: { status?: number } })?.response?.status;
    if (status === 401 || status === 403) {
      return (
        <Paper variant="outlined" sx={{ p: 2, mt: 2 }} data-testid="draft-baseline-review-forbidden">
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <LockOutlinedIcon fontSize="small" color="disabled" />
            <Typography variant="body2" color="text.secondary">
              You don&apos;t have access to view expected baselines for this project.
            </Typography>
          </Box>
        </Paper>
      );
    }
    return (
      <Alert severity="error" sx={{ mt: 2 }} data-testid="draft-baseline-review-error">
        Couldn&apos;t load expected baselines. Please try again later.
      </Alert>
    );
  }

  const headerRow = (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5, flexWrap: 'wrap' }}>
      <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
        Draft Baseline Review
      </Typography>
      {!canManageLifecycle && (
        <Chip size="small" variant="outlined" color="default" icon={<LockOutlinedIcon />} label="View only" />
      )}
    </Box>
  );

  // A button that stays visible-but-disabled (with a tooltip) when the user
  // can't act, so lifecycle state is never fully hidden (Scope B). The disabled
  // state mirrors the backend gate (telemetry-admin AND company-admin), so it
  // never fires a doomed 403; the read-only explanation below spells out why.
  const renderActionButton = (props: { testId: string; label: string; onClick: () => void; disabled?: boolean }) => {
    const blockedByPermission = !canManageLifecycle;
    const isDisabled = blockedByPermission || props.disabled;
    const button = (
      <Button
        size="small"
        variant="contained"
        color="primary"
        disabled={isDisabled}
        onClick={props.onClick}
        data-testid={props.testId}
        startIcon={blockedByPermission ? <LockOutlinedIcon /> : undefined}
      >
        {props.label}
      </Button>
    );
    if (blockedByPermission) {
      return (
        <Tooltip title={PERMISSION_TOOLTIP}>
          <span data-testid={`${props.testId}-disabled-wrap`}>{button}</span>
        </Tooltip>
      );
    }
    return button;
  };

  const renderProvenanceRow = (
    def: FieldDef,
    src: BaselineFieldSource | undefined,
    value: number | null | undefined
  ) => {
    const chip = originChip(src?.source);
    const norm = src?.normalization;
    return (
      <Box key={String(def.col)} sx={{ py: 0.75 }} data-testid={`draft-field-${String(def.col)}`}>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 1 }}>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            {def.label}
            {def.unit ? ` (${def.unit})` : ''}
          </Typography>
          <Typography variant="body2">{fmtWithUnit(value, def.unit)}</Typography>
          <Chip size="small" variant="outlined" color={chip.color} label={chip.label} />
          {src?.fact_id != null && (
            <Typography variant="caption" color="text.secondary">
              fact #{src.fact_id}
            </Typography>
          )}
          {src?.document_id != null && (
            <Typography variant="caption" color="text.secondary">
              doc #{src.document_id}
            </Typography>
          )}
          {src?.ai_confidence != null && (
            <Typography variant="caption" color="text.secondary">
              conf {formatConfidence(src.ai_confidence)}
            </Typography>
          )}
        </Box>
        {src?.source === 'reviewer_supplied' && src?.fact_id == null && src?.document_id == null && (
          <Typography
            variant="caption"
            color="text.secondary"
            display="block"
            data-testid={`draft-field-${String(def.col)}-no-document-source`}
          >
            Reviewer-supplied datasheet constant — no document source exists for this value.
          </Typography>
        )}
        {norm && norm.raw_value != null && norm.normalized_value != null && (
          <Typography variant="caption" color="text.secondary" display="block">
            Normalized {String(norm.raw_value)} → {norm.normalized_value}
            {norm.to_unit ? ` ${norm.to_unit}` : ''}
            {norm.from_unit ? ` (${norm.from_unit} → ${norm.to_unit ?? '?'})` : ''}
          </Typography>
        )}
      </Box>
    );
  };

  const renderDraftDetail = (draft: ExpectedBaselineResponse) => {
    const params = draft.model_parameters_json ?? {};
    const fieldSources = params.field_sources ?? {};
    const warnings = params.warnings ?? [];
    const numField = (col: keyof ExpectedBaselineResponse): number | null => numFieldOf(draft, col);
    const approvable = draft.status === 'draft' || draft.status === 'in_review';

    return (
      <Box data-testid="draft-baseline-detail">
        {/* Identity / provenance ids */}
        <Typography variant="overline" color="text.secondary">
          Draft identity
        </Typography>
        <Grid container spacing={1} sx={{ mb: 1 }}>
          <Grid item xs={12} sm={6}>
            <Typography variant="body2">
              <strong>{draft.baseline_name}</strong> (baseline #{draft.id}, v{draft.version})
            </Typography>
            <Typography variant="caption" display="block" color="text.secondary">
              Type: {draft.baseline_type} · Status:{' '}
              <Chip size="small" color={statusChipColor(draft.status)} label={statusLabel(draft.status)} />
            </Typography>
            <Typography variant="caption" display="block" color="text.secondary">
              Created: {formatDateTime(draft.created_at ?? null)}
              {draft.created_by_user_id != null ? ` · by user #${draft.created_by_user_id}` : ''}
            </Typography>
          </Grid>
          <Grid item xs={12} sm={6}>
            <Typography variant="caption" display="block" color="text.secondary">
              Source type: {draft.source_type ?? PLACEHOLDER}
            </Typography>
            <Typography variant="caption" display="block" color="text.secondary">
              Source document: {draft.source_document_id != null ? `#${draft.source_document_id}` : PLACEHOLDER} ·
              Source fact: {draft.source_project_fact_id != null ? `#${draft.source_project_fact_id}` : PLACEHOLDER}
            </Typography>
            <Typography variant="caption" display="block" color="text.secondary">
              Supersedes baseline:{' '}
              {draft.supersedes_baseline_id != null ? `#${draft.supersedes_baseline_id}` : PLACEHOLDER}
            </Typography>
          </Grid>
        </Grid>

        <Divider sx={{ my: 1 }} />

        {/* Fact-backed equipment physics */}
        <Typography variant="overline" color="text.secondary">
          From promoted facts
        </Typography>
        <Box sx={{ mb: 1 }}>
          {FACT_FIELDS.map(def => renderProvenanceRow(def, fieldSources[def.col as string], numField(def.col)))}
        </Box>

        <Divider sx={{ my: 1 }} />

        {/* Reviewer datasheet constants */}
        <Typography variant="overline" color="text.secondary">
          Reviewer datasheet constants
        </Typography>
        <Box sx={{ mb: 1 }}>
          {REVIEWER_REQUIRED_FIELDS.map(def =>
            renderProvenanceRow(def, fieldSources[def.col as string], numField(def.col))
          )}
        </Box>

        <Divider sx={{ my: 1 }} />

        {/* Optional losses / soiling — defaults are reported, not source-backed */}
        <Typography variant="overline" color="text.secondary">
          Optional adjustments
        </Typography>
        <Box sx={{ mb: 1 }}>
          {OPTIONAL_DEFAULT_FIELDS.map(def => {
            const value = numField(def.col);
            const supplied = value != null;
            return (
              <Box key={String(def.col)} sx={{ py: 0.75 }} data-testid={`draft-optional-${String(def.col)}`}>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 1 }}>
                  <Typography variant="body2" sx={{ fontWeight: 600 }}>
                    {def.label}
                    {def.unit ? ` (${def.unit})` : ''}
                  </Typography>
                  {supplied ? (
                    <>
                      <Typography variant="body2">{fmtWithUnit(value, def.unit)}</Typography>
                      <Chip size="small" variant="outlined" color="info" label="Reviewer value" />
                    </>
                  ) : (
                    <>
                      <Typography variant="body2" color="text.secondary">
                        {def.defaultLabel}
                      </Typography>
                      <Chip
                        size="small"
                        variant="outlined"
                        color="default"
                        label="Default applied — not source-backed"
                      />
                    </>
                  )}
                </Box>
              </Box>
            );
          })}
        </Box>

        {/* PTO behavior */}
        {draft.pto_date ? (
          <Typography variant="caption" color="text.secondary" display="block" data-testid="draft-baseline-pto">
            PTO date: {draft.pto_date} — expected production is suppressed (NULL) before this date.
          </Typography>
        ) : (
          <Alert severity="warning" sx={{ mt: 1 }} data-testid="draft-baseline-pto-suppressed">
            No PTO date is set on this draft — expected production stays suppressed (NULL) until a PTO date is provided.
          </Alert>
        )}

        {/* Persisted warnings + provenance summary */}
        {warnings.length > 0 && (
          <Alert severity="info" sx={{ mt: 1 }} data-testid="draft-baseline-warnings">
            <AlertTitle>Build notes</AlertTitle>
            <Box component="ul" sx={{ pl: 3, mb: 0 }}>
              {warnings.map(w => (
                <li key={w}>
                  <Typography variant="caption">{w}</Typography>
                </li>
              ))}
            </Box>
          </Alert>
        )}
        {params.source_fact_signature && (
          <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
            Source-fact signature: {params.source_fact_signature}
          </Typography>
        )}

        {/* Read-only draft-vs-active expected overlay (Phase 1) */}
        <DraftPreviewOverlay siteId={siteId} draftId={draft.id} baselineStatus={draft.status} />

        {/* Approve action (separate from activation) */}
        {approvable && (
          <Box sx={{ mt: 1.5, display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
            {renderActionButton({
              testId: 'approve-baseline-button',
              label: 'Approve',
              onClick: () => setApproveTarget(draft),
              disabled: approveMutation.isPending
            })}
            <Typography variant="caption" color="text.secondary">
              Approval confirms the draft inputs. It does not make this baseline active.
            </Typography>
          </Box>
        )}
      </Box>
    );
  };

  const renderSummaryLine = (b: ExpectedBaselineResponse) => (
    <Box key={b.id} sx={{ py: 0.5 }} data-testid={`baseline-summary-${b.id}`}>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 1 }}>
        <Chip
          size="small"
          color={statusChipColor(b.status)}
          icon={b.status === 'active' ? <CheckCircleOutlineIcon /> : undefined}
          label={statusLabel(b.status)}
        />
        <Typography variant="body2">
          {b.baseline_name} (#{b.id}, v{b.version})
        </Typography>
      </Box>
      <Typography variant="caption" display="block" color="text.secondary">
        Created: {formatDateTime(b.created_at ?? null)}
        {b.approved_at ? ` · Approved: ${formatDateTime(b.approved_at)}` : ''}
        {b.active_from ? ` · Active from: ${formatDateTime(b.active_from)}` : ''}
      </Typography>
    </Box>
  );

  // Compact fail-closed verdict chip for one baseline (proposed or active).
  const validationChip = (v: BaselinePhysicsValidation | null | undefined, who: string) => {
    if (!v) {
      return <Chip size="small" variant="outlined" color="default" label={`${who}: not evaluated`} />;
    }
    if (v.is_blocking) {
      return (
        <Chip
          size="small"
          color="error"
          label={`${who}: invalid${v.blocking_field_count ? ` (${v.blocking_field_count})` : ''}`}
        />
      );
    }
    if ((v.warning_field_count ?? 0) > 0) {
      return <Chip size="small" color="warning" label={`${who}: valid with warnings (${v.warning_field_count})`} />;
    }
    return <Chip size="small" color="success" label={`${who}: valid`} />;
  };

  const renderDiffRow = (d: BaselineFieldDiff) => {
    const oldText = d.old_display ?? fmtWithUnit(d.old_value, d.unit ?? undefined);
    const newText = d.new_display ?? fmtWithUnit(d.new_value, d.unit ?? undefined);
    const cls = d.new_validation_classification;
    const clsColor: 'error' | 'warning' | 'success' | 'default' =
      cls === 'hard_invalid'
        ? 'error'
        : cls === 'warning' || cls === 'implausible'
          ? 'warning'
          : cls === 'plausible'
            ? 'success'
            : 'default';
    return (
      <Box key={d.field} sx={{ py: 0.5 }} data-testid={`baseline-diff-row-${d.field}`}>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 1 }}>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            {d.label}
            {d.unit ? ` (${d.unit})` : ''}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {oldText} → {newText}
          </Typography>
          <Chip size="small" variant="outlined" color="default" label={d.source} />
          {cls && <Chip size="small" color={clsColor} label={cls.replace(/_/g, ' ')} />}
        </Box>
        {d.new_validation_reason && (
          <Typography variant="caption" color="text.secondary" display="block">
            {d.new_validation_reason}
          </Typography>
        )}
      </Box>
    );
  };

  // Read-only side-by-side comparison of the proposed replacement vs the active
  // baseline (changed physics fields, both fail-closed verdicts, and the expected
  // impact at fixed reference conditions). Never fabricates expected values — a
  // baseline that can't evaluate the reference point shows N/A, never 0.
  const renderReplacementDiff = () => {
    if (!diffEnabled) return null;
    if (diffLoading) {
      return (
        <Box display="flex" alignItems="center" gap={1} sx={{ my: 1 }} data-testid="baseline-diff-loading">
          <CircularProgress size={16} />
          <Typography variant="body2" color="text.secondary">
            Loading replacement comparison…
          </Typography>
        </Box>
      );
    }
    if (diffError || !diff) {
      return (
        <Alert severity="warning" sx={{ my: 1 }} data-testid="baseline-diff-error">
          Couldn&apos;t load the replacement comparison. The proposed and active baselines are unchanged.
        </Alert>
      );
    }
    const changed = diff.changed_fields ?? [];
    const impact = diff.expected_impact;
    return (
      <Box sx={{ my: 1 }} data-testid="baseline-diff">
        <Typography variant="overline" color="text.secondary">
          Replacement comparison (proposed #{diff.to_baseline_id} vs active
          {diff.from_baseline_id != null ? ` #${diff.from_baseline_id}` : ''})
        </Typography>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mb: 1 }}>
          {validationChip(diff.to_validation, 'Proposed')}
          {validationChip(diff.from_validation, 'Active')}
        </Box>
        <ValidationSummaryPanel
          validation={diff.to_validation}
          who="Proposed baseline"
          testIdPrefix="validation-summary-proposed"
        />
        {diff.from_validation && (
          <ValidationSummaryPanel
            validation={diff.from_validation}
            who="Active baseline"
            testIdPrefix="validation-summary-active"
          />
        )}
        <Typography variant="body2" sx={{ fontWeight: 600, mt: 0.5 }}>
          Changed physics fields
        </Typography>
        {changed.length === 0 ? (
          <Typography variant="body2" color="text.secondary" data-testid="baseline-diff-no-changes">
            No physics fields differ between the proposed and active baselines.
          </Typography>
        ) : (
          <Box data-testid="baseline-diff-changed">{changed.map(renderDiffRow)}</Box>
        )}
        {impact && (
          <Box sx={{ mt: 1 }} data-testid="baseline-diff-impact">
            <Typography variant="body2" sx={{ fontWeight: 600 }}>
              Expected impact at reference conditions
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block">
              Reference: {impact.reference_irradiance_wm2} W/m² · {impact.reference_cell_temperature_c} °C · age{' '}
              {impact.reference_age_years} yr
            </Typography>
            <Typography variant="body2">
              Active: {fmtWithUnit(impact.old_expected_power_kw, 'kW')} → Proposed:{' '}
              {fmtWithUnit(impact.new_expected_power_kw, 'kW')}
              {impact.delta_kw != null && Number.isFinite(impact.delta_kw)
                ? ` (${impact.delta_kw > 0 ? '+' : ''}${impact.delta_kw.toFixed(1)} kW${
                    impact.delta_pct != null && Number.isFinite(impact.delta_pct)
                      ? `, ${impact.delta_pct > 0 ? '+' : ''}${impact.delta_pct.toFixed(1)}%`
                      : ''
                  })`
                : ''}
            </Typography>
            <Typography variant="caption" color="text.secondary" display="block">
              {impact.note}
            </Typography>
          </Box>
        )}
      </Box>
    );
  };

  const nothingToShow =
    drafts.length === 0 && approvedNotActive.length === 0 && superseded.length === 0 && active == null;

  return (
    <Paper variant="outlined" sx={{ p: 2, mt: 2 }} data-testid="draft-baseline-review-panel">
      {headerRow}
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
        Review weather-adjusted expected baselines and their provenance, then approve and activate them in two
        deliberate steps. Nothing changes until you confirm.
      </Typography>

      <Alert severity="info" sx={{ mb: 1.5 }} data-testid="draft-baseline-lifecycle-note">
        <AlertTitle>Approve and activate are separate steps</AlertTitle>
        Approving a draft only confirms its inputs — it does not make the baseline active. Activating an approved
        baseline drives weather-adjusted expected/comparative performance from its activation boundary forward, while
        historical periods continue to use the baseline that was active during those periods (period-effective
        selection).
      </Alert>

      {/* Read-only explanation when the viewer can't run lifecycle actions */}
      {!canManageLifecycle && (
        <Alert
          severity="info"
          icon={<LockOutlinedIcon fontSize="inherit" />}
          sx={{ mb: 1.5 }}
          data-testid="lifecycle-readonly-explanation"
        >
          You can review this baseline. Approving or activating requires <strong>Telemetry admin</strong> and{' '}
          <strong>Company admin</strong> access for this project&apos;s company.
        </Alert>
      )}

      {diff?.from_validation?.is_blocking && (
        <Alert severity="error" sx={{ mb: 1.5 }} data-testid="active-baseline-invalid-banner">
          <AlertTitle>Expected comparison unavailable: active baseline requires replacement.</AlertTitle>
          {diff.from_validation.summary ||
            'The active expected baseline failed fail-closed physics validation, so O&M expected production is suppressed (shown as N/A, never 0).'}{' '}
          Approve and activate a corrected, source-backed replacement below to restore the expected comparison.
        </Alert>
      )}

      {nothingToShow ? (
        <Typography variant="body2" color="text.secondary" data-testid="draft-baseline-review-empty">
          No draft, approved, active, or superseded weather-adjusted baseline exists for this project yet.
        </Typography>
      ) : (
        <>
          {/* Draft selector + detail */}
          <Typography variant="overline" color="text.secondary">
            Draft baselines
          </Typography>
          {drafts.length === 0 ? (
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }} data-testid="draft-baseline-none">
              No draft weather-adjusted baseline yet.
            </Typography>
          ) : (
            <>
              {drafts.length > 1 && (
                <TextField
                  select
                  size="small"
                  label="Select draft"
                  value={selectedDraftId ?? ''}
                  onChange={e => setSelectedDraftId(Number(e.target.value))}
                  sx={{ minWidth: 280, my: 1 }}
                  data-testid="draft-baseline-selector"
                  SelectProps={{ inputProps: { 'data-testid': 'draft-baseline-selector-input' } }}
                >
                  {drafts.map(d => (
                    <MenuItem key={d.id} value={d.id}>
                      {d.baseline_name} (#{d.id}, v{d.version}) — {formatDateTime(d.created_at ?? null)}
                    </MenuItem>
                  ))}
                </TextField>
              )}
              {selectedDraft && renderDraftDetail(selectedDraft)}
            </>
          )}

          {/* Read-only replacement comparison vs the active baseline */}
          {renderReplacementDiff()}

          <Divider sx={{ my: 1.5 }} />

          {/* Approved-but-not-active */}
          <Typography variant="overline" color="text.secondary">
            Approved (not yet active)
          </Typography>
          <Box sx={{ mb: 1 }} data-testid="draft-baseline-approved-list">
            {approvedNotActive.length > 0 ? (
              approvedNotActive.map(b => (
                <Box
                  key={b.id}
                  sx={{ py: 0.5, display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 1 }}
                  data-testid={`approved-row-${b.id}`}
                >
                  {renderSummaryLine(b)}
                  <Box sx={{ flexShrink: 0, pt: 0.5 }}>
                    {renderActionButton({
                      testId: `activate-baseline-button-${b.id}`,
                      label: 'Activate',
                      onClick: () => setActivateTarget(b),
                      disabled: activateMutation.isPending
                    })}
                  </Box>
                </Box>
              ))
            ) : (
              <Typography variant="body2" color="text.secondary">
                No approved-but-inactive baselines.
              </Typography>
            )}
          </Box>

          <Divider sx={{ my: 1.5 }} />

          {/* Active baseline summary (separate read endpoint) */}
          <Typography variant="overline" color="text.secondary">
            Active baseline
          </Typography>
          <Box data-testid="draft-baseline-active-summary">
            {active ? (
              <>
                {renderSummaryLine(active)}
                <Typography variant="caption" display="block" color="text.secondary">
                  Type: {active.baseline_type}
                  {active.supersedes_baseline_id != null
                    ? ` · Supersedes baseline #${active.supersedes_baseline_id}`
                    : ''}
                </Typography>
                <Typography
                  variant="caption"
                  display="block"
                  color="text.secondary"
                  data-testid="active-period-effective-note"
                >
                  Historical expected uses period-effective baseline selection.
                </Typography>
              </>
            ) : (
              <Tooltip title="No active weather-adjusted baseline drives expected output for this project yet.">
                <Typography variant="body2" color="text.secondary">
                  No active baseline.
                </Typography>
              </Tooltip>
            )}
          </Box>

          {superseded.length > 0 && (
            <>
              <Divider sx={{ my: 1.5 }} />
              <Typography variant="overline" color="text.secondary">
                Superseded (historical)
              </Typography>
              <Box data-testid="draft-baseline-superseded-list">
                {superseded.map(b => (
                  <Box
                    key={b.id}
                    sx={{ py: 0.5, display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}
                    data-testid={`baseline-superseded-${b.id}`}
                  >
                    <Chip
                      size="small"
                      variant="outlined"
                      color="default"
                      icon={<HistoryOutlinedIcon />}
                      label="Superseded · historical"
                    />
                    <Typography variant="body2">
                      {b.baseline_name} (#{b.id}, v{b.version})
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {b.active_from ? `Active ${formatDateTime(b.active_from)}` : ''}
                      {b.active_to ? ` → ${formatDateTime(b.active_to)}` : ''}
                    </Typography>
                  </Box>
                ))}
              </Box>
            </>
          )}
        </>
      )}

      {/* Design-estimate separation */}
      <Alert severity="info" sx={{ mt: 1.5 }} data-testid="draft-baseline-design-estimate-note">
        Design-estimate baselines are a separate track and are neither reviewed nor changed here.
      </Alert>

      <ValidationHistoryPanel baselines={weatherAdjustedBaselines} sourceBasisDrift={sourceBasisDrift} />

      {/* Approve confirmation dialog */}
      <Dialog
        open={approveTarget != null}
        onClose={() => !approveMutation.isPending && setApproveTarget(null)}
        maxWidth="sm"
        fullWidth
        data-testid="approve-confirm-dialog"
      >
        <DialogTitle>Approve expected baseline</DialogTitle>
        <DialogContent dividers>
          {approveTarget && <ApproveConfirmationSummary baseline={approveTarget} />}
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setApproveTarget(null)}
            disabled={approveMutation.isPending}
            data-testid="approve-confirm-cancel"
          >
            Cancel
          </Button>
          <Button
            variant="contained"
            color="primary"
            onClick={() => approveTarget && approveMutation.mutate(approveTarget.id)}
            disabled={approveMutation.isPending}
            data-testid="approve-confirm-submit"
          >
            {approveMutation.isPending ? 'Approving…' : 'Approve baseline'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Activate confirmation dialog */}
      <Dialog
        open={activateTarget != null}
        onClose={() => !activateMutation.isPending && closeActivateDialog()}
        maxWidth="sm"
        fullWidth
        data-testid="activate-confirm-dialog"
      >
        <DialogTitle>Activate expected baseline</DialogTitle>
        <DialogContent dividers>
          {activateTarget && <ActivateConfirmationSummary baseline={activateTarget} priorActive={active} />}
          {activateTarget && (
            <ActivationReadinessSummary
              baseline={activateTarget}
              priorActive={active}
              validation={activateTarget.id === diff?.to_baseline_id ? diff?.to_validation : null}
            />
          )}
          {activateWarnings && (
            <Alert severity="warning" sx={{ mt: 2 }} data-testid="activate-warning-ack">
              <AlertTitle>Confirmation required before activation</AlertTitle>
              <Typography variant="caption" display="block">
                {activateWarnings.message ??
                  activateWarnings.summary ??
                  'This baseline has values that need confirmation before it can be activated.'}
              </Typography>
              {(() => {
                const explainer = blockReasonExplainer(activateWarnings.reason);
                return explainer ? (
                  <Typography variant="caption" display="block" color="text.secondary" sx={{ mt: 1 }}>
                    {explainer.detail}
                  </Typography>
                ) : null;
              })()}
              {Array.isArray(activateWarnings.warning_fields) && activateWarnings.warning_fields.length > 0 && (
                <FormGroup sx={{ mt: 1 }} data-testid="activate-warning-checklist">
                  {activateWarnings.warning_fields.map((w, i) => {
                    const key = `${w.field ?? 'field'}-${i}`;
                    return (
                      <Box key={key} sx={{ mb: 0.5 }} data-testid={`activate-warning-item-${w.field ?? i}`}>
                        <FormControlLabel
                          control={
                            <Checkbox
                              size="small"
                              checked={Boolean(ackedWarnings[key])}
                              onChange={e => setAckedWarnings(prev => ({ ...prev, [key]: e.target.checked }))}
                              data-testid={`activate-warning-check-${w.field ?? i}`}
                            />
                          }
                          label={
                            <Typography variant="caption" sx={{ fontWeight: 600 }}>
                              {w.field ?? 'value'}
                              {w.reason ? `: ${w.reason}` : ''}
                            </Typography>
                          }
                        />
                        {w.required_action && (
                          <Typography variant="caption" display="block" color="text.secondary" sx={{ pl: 4 }}>
                            Next: {w.required_action}
                          </Typography>
                        )}
                      </Box>
                    );
                  })}
                </FormGroup>
              )}
              <Typography variant="caption" display="block" color="text.secondary" sx={{ mt: 0.5 }}>
                Checking each item is optional — activation requires the source note below.
              </Typography>
              <TextField
                label="Source note (required)"
                helperText="Document the source / justification for activating despite these warnings."
                value={activateNote}
                onChange={e => setActivateNote(e.target.value)}
                fullWidth
                multiline
                minRows={2}
                required
                sx={{ mt: 1.5 }}
                inputProps={{ maxLength: 2000 }}
                data-testid="activate-source-note"
              />
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => closeActivateDialog()}
            disabled={activateMutation.isPending}
            data-testid="activate-confirm-cancel"
          >
            Cancel
          </Button>
          <Button
            variant="contained"
            color="primary"
            onClick={() =>
              activateTarget &&
              activateMutation.mutate(
                activateWarnings
                  ? {
                      baselineId: activateTarget.id,
                      acknowledgeWarnings: true,
                      activationSourceNote: activateNote.trim()
                    }
                  : { baselineId: activateTarget.id }
              )
            }
            disabled={activateMutation.isPending || (activateWarnings != null && activateNote.trim().length === 0)}
            data-testid="activate-confirm-submit"
          >
            {activateMutation.isPending
              ? 'Activating…'
              : activateWarnings
                ? 'Acknowledge & activate'
                : 'Activate baseline'}
          </Button>
        </DialogActions>
      </Dialog>
    </Paper>
  );
};

/**
 * Approve dialog body — summarizes the exact inputs the reviewer is confirming
 * (Scope C) plus the design-estimate separation language (Scope H). Read-only;
 * it computes nothing and changes nothing.
 */
const ApproveConfirmationSummary: React.FC<{ baseline: ExpectedBaselineResponse }> = ({ baseline }) => {
  const params = baseline.model_parameters_json ?? {};
  const fieldSources = params.field_sources ?? {};
  const warnings = params.warnings ?? [];

  const normalizedEntries = Object.entries(fieldSources).filter(
    ([, src]) => src?.normalization?.raw_value != null && src?.normalization?.normalized_value != null
  );
  const appliedDefaults = OPTIONAL_DEFAULT_FIELDS.filter(def => numFieldOf(baseline, def.col) == null);

  return (
    <Box data-testid="approve-confirm-summary">
      <Typography variant="body2" sx={{ fontWeight: 600 }}>
        {baseline.baseline_name} (baseline #{baseline.id}, v{baseline.version})
      </Typography>
      <Typography variant="caption" display="block" color="text.secondary">
        Type: {baseline.baseline_type} · Status: {statusLabel(baseline.status)}
      </Typography>
      <Typography variant="caption" display="block" color="text.secondary">
        Source: document {baseline.source_document_id != null ? `#${baseline.source_document_id}` : PLACEHOLDER} · fact{' '}
        {baseline.source_project_fact_id != null ? `#${baseline.source_project_fact_id}` : PLACEHOLDER}
        {params.source_fact_signature ? ` · signature ${params.source_fact_signature}` : ''}
      </Typography>

      <Divider sx={{ my: 1 }} />

      <Typography variant="overline" color="text.secondary">
        From promoted facts
      </Typography>
      <Box sx={{ mb: 1 }}>
        {FACT_FIELDS.map(def => (
          <Typography variant="caption" display="block" key={String(def.col)}>
            {def.label}: {fmtWithUnit(numFieldOf(baseline, def.col), def.unit)}
          </Typography>
        ))}
      </Box>

      <Typography variant="overline" color="text.secondary">
        Reviewer-supplied inputs
      </Typography>
      <Box sx={{ mb: 1 }}>
        {REVIEWER_REQUIRED_FIELDS.map(def => (
          <Typography variant="caption" display="block" key={String(def.col)}>
            {def.label}: {fmtWithUnit(numFieldOf(baseline, def.col), def.unit)}
          </Typography>
        ))}
      </Box>

      <Typography variant="overline" color="text.secondary">
        Normalized values
      </Typography>
      <Box sx={{ mb: 1 }} data-testid="approve-confirm-normalized">
        {normalizedEntries.length > 0 ? (
          normalizedEntries.map(([col, src]) => (
            <Typography variant="caption" display="block" key={col}>
              {col}: {String(src?.normalization?.raw_value)} → {src?.normalization?.normalized_value}
              {src?.normalization?.to_unit ? ` ${src.normalization.to_unit}` : ''}
            </Typography>
          ))
        ) : (
          <Typography variant="caption" color="text.secondary">
            No unit normalization was applied.
          </Typography>
        )}
      </Box>

      <Typography variant="overline" color="text.secondary">
        Optional defaults
      </Typography>
      <Box sx={{ mb: 1 }} data-testid="approve-confirm-defaults">
        {appliedDefaults.length > 0 ? (
          appliedDefaults.map(def => (
            <Typography variant="caption" display="block" key={String(def.col)}>
              {def.label}: {def.defaultLabel} — default applied, not source-backed.
            </Typography>
          ))
        ) : (
          <Typography variant="caption" color="text.secondary">
            All optional adjustments were supplied by the reviewer.
          </Typography>
        )}
      </Box>

      {baseline.pto_date ? (
        <Typography variant="caption" display="block" color="text.secondary">
          PTO date: {baseline.pto_date} — expected production is suppressed before this date.
        </Typography>
      ) : (
        <Alert severity="warning" sx={{ mt: 1 }} data-testid="approve-confirm-pto-warning">
          No PTO date is set — expected production stays suppressed (NULL) until a PTO date is provided.
        </Alert>
      )}

      {warnings.length > 0 && (
        <Alert severity="info" sx={{ mt: 1 }} data-testid="approve-confirm-warnings">
          <AlertTitle>Persisted build notes</AlertTitle>
          <Box component="ul" sx={{ pl: 3, mb: 0 }}>
            {warnings.map(w => (
              <li key={w}>
                <Typography variant="caption">{w}</Typography>
              </li>
            ))}
          </Box>
        </Alert>
      )}

      <Alert severity="info" sx={{ mt: 1.5 }} data-testid="approve-confirm-statement">
        Approval confirms the draft inputs, but does not make this baseline active.
      </Alert>

      <Typography
        variant="caption"
        display="block"
        color="text.secondary"
        sx={{ mt: 1 }}
        data-testid="approve-confirm-period-effective"
      >
        Approval changes no O&amp;M output and backfills no history. Only a later, separate activation applies this
        baseline from its activation boundary forward; historical periods keep using the baseline active during those
        periods (period-effective selection).
      </Typography>

      <DesignEstimateSeparationNote />
    </Box>
  );
};

/**
 * Activate dialog body — explains the forward-only effect, supersession, and the
 * period-effective history guarantee (Scope D) plus design-estimate separation
 * (Scope H).
 */
const ActivateConfirmationSummary: React.FC<{
  baseline: ExpectedBaselineResponse;
  priorActive: ExpectedBaselineResponse | null;
}> = ({ baseline, priorActive }) => (
  <Box data-testid="activate-confirm-summary">
    <Typography variant="body2" sx={{ fontWeight: 600 }}>
      {baseline.baseline_name} (baseline #{baseline.id}, v{baseline.version})
    </Typography>
    <Typography variant="caption" display="block" color="text.secondary">
      Type: {baseline.baseline_type} · Status: {statusLabel(baseline.status)}
    </Typography>

    <Divider sx={{ my: 1 }} />

    <Box component="ul" sx={{ pl: 3, mb: 0 }}>
      <li>
        <Typography variant="caption">
          Activation stamps <strong>active_from</strong> at the activation moment; the baseline drives expected output
          from that boundary forward.
        </Typography>
      </li>
      <li>
        <Typography variant="caption" data-testid="activate-confirm-prior-active">
          {priorActive
            ? `The current active baseline (${priorActive.baseline_name}, #${priorActive.id}) will be superseded and kept for audit.`
            : 'There is no current active baseline; this will become the first active one.'}
        </Typography>
      </li>
      <li>
        <Typography variant="caption" data-testid="activate-confirm-period-effective">
          Historical periods continue to use the baseline active during those periods (period-effective selection); no
          historical expected values are backfilled or regenerated.
        </Typography>
      </li>
    </Box>

    <Alert severity="info" sx={{ mt: 1.5 }} data-testid="activate-confirm-statement">
      From activation forward, this baseline will drive weather-adjusted expected/comparative performance. Historical
      periods continue to use the baseline active during those periods.
    </Alert>

    <DesignEstimateSeparationNote />
  </Box>
);

export default DraftBaselineReviewPanel;
