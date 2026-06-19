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
import LockOutlinedIcon from '@mui/icons-material/LockOutlined';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import HistoryOutlinedIcon from '@mui/icons-material/HistoryOutlined';

import { ApiClient } from '../../../../../../../api';
import type {
  BaselineFieldSource,
  ExpectedBaselineListResponse,
  ExpectedBaselineResponse
} from '../../../../../../../types/telemetryV2';
import { useTelemetryAdminPermission } from '../../../../../../../hooks/useTelemetryAdminPermission';
import { useNotify } from '../../../../../../../contexts/notifications/notifications';
import { PLACEHOLDER, formatConfidence, formatDateTime } from '../utils';

interface DraftBaselineReviewPanelProps {
  siteId: number;
}

// Only the weather-adjusted model drives the live expected calc; the review
// panel is intentionally scoped to it (design-estimate is a separate track).
const WEATHER_ADJUSTED = 'weather_adjusted_model';

// Frontend mirror of the (stricter) backend approve/activate gate. The server
// still enforces telemetry_admin + company-admin + company visibility, so a user
// who slips past this check just gets a graceful 403 — never a silent mutation.
const PERMISSION_TOOLTIP = 'You need telemetry-admin (or company admin) access to approve or activate baselines.';

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

// Map a backend failure to a clear, action-specific message (Scope I).
const actionErrorMessage = (action: 'approve' | 'activate', err: unknown): string => {
  const status = (err as { response?: { status?: number } })?.response?.status;
  if (status === 401 || status === 403) return `You do not have permission to ${action} this baseline.`;
  if (status === 404) return 'Baseline not found. It may have been removed — refresh and try again.';
  if (status === 409) {
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
export const DraftBaselineReviewPanel: React.FC<DraftBaselineReviewPanelProps> = ({ siteId }) => {
  const enabled = Number.isSafeInteger(siteId) && siteId > 0;
  const canManage = useTelemetryAdminPermission();
  const notify = useNotify();
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery<ExpectedBaselineListResponse>({
    queryKey: baselinesQueryKey(siteId),
    queryFn: () => ApiClient.telemetryV2.listExpectedBaselines(siteId),
    enabled,
    retry: false
  });

  // Active baseline is fetched via the dedicated read endpoint and shown
  // separately. Its failure must not blank the whole panel, so it is handled
  // softly (the list still drives loading/error).
  const { data: activeBaseline } = useQuery<ExpectedBaselineResponse | null>({
    queryKey: activeBaselineQueryKey(siteId),
    queryFn: () => ApiClient.telemetryV2.getActiveExpectedBaseline(siteId),
    enabled,
    retry: false
  });

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

  const activateMutation = useMutation<ExpectedBaselineResponse, unknown, number>({
    mutationFn: (baselineId: number) => ApiClient.telemetryV2.activateExpectedBaseline(baselineId),
    onSuccess: () => {
      // Let the active read, the list, readiness, and the expected-bearing O&M
      // site charts refetch. We invalidate only — no recompute / backfill.
      queryClient.invalidateQueries({ queryKey: baselinesQueryKey(siteId) });
      queryClient.invalidateQueries({ queryKey: activeBaselineQueryKey(siteId) });
      queryClient.invalidateQueries({ queryKey: reconciliationQueryKey(siteId) });
      omExpectedQueryKeys(siteId).forEach(key => queryClient.invalidateQueries({ queryKey: key }));
      notify('Baseline activated. O&M expected values now use this baseline from its activation boundary forward.');
      setActivateTarget(null);
    },
    onError: err => {
      notify(actionErrorMessage('activate', err));
      setActivateTarget(null);
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
      {!canManage && (
        <Chip size="small" variant="outlined" color="default" icon={<LockOutlinedIcon />} label="View only" />
      )}
    </Box>
  );

  // A button that stays visible-but-disabled (with a tooltip) when the user
  // can't act, so lifecycle state is never fully hidden (Scope B).
  const renderActionButton = (props: { testId: string; label: string; onClick: () => void; disabled?: boolean }) => {
    const blockedByPermission = !canManage;
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

        {/* Draft expected preview is intentionally unavailable */}
        <Alert severity="info" sx={{ mt: 1.5 }} data-testid="draft-baseline-preview-unavailable">
          Expected preview not available for draft baseline yet. Preview is limited to approved, active, or superseded
          baselines so a never-approved draft can&apos;t render an expected curve.
        </Alert>

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
        onClose={() => !activateMutation.isPending && setActivateTarget(null)}
        maxWidth="sm"
        fullWidth
        data-testid="activate-confirm-dialog"
      >
        <DialogTitle>Activate expected baseline</DialogTitle>
        <DialogContent dividers>
          {activateTarget && <ActivateConfirmationSummary baseline={activateTarget} priorActive={active} />}
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setActivateTarget(null)}
            disabled={activateMutation.isPending}
            data-testid="activate-confirm-cancel"
          >
            Cancel
          </Button>
          <Button
            variant="contained"
            color="primary"
            onClick={() => activateTarget && activateMutation.mutate(activateTarget.id)}
            disabled={activateMutation.isPending}
            data-testid="activate-confirm-submit"
          >
            {activateMutation.isPending ? 'Activating…' : 'Activate baseline'}
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
