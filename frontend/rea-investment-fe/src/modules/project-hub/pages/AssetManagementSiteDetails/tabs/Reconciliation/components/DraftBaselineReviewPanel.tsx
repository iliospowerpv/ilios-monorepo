import React, { useEffect, useMemo, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
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
import CircularProgress from '@mui/material/CircularProgress';
import LockOutlinedIcon from '@mui/icons-material/LockOutlined';

import { ApiClient } from '../../../../../../../api';
import type {
  BaselineFieldSource,
  ExpectedBaselineListResponse,
  ExpectedBaselineResponse
} from '../../../../../../../types/telemetryV2';
import { PLACEHOLDER, formatConfidence, formatDateTime } from '../utils';

interface DraftBaselineReviewPanelProps {
  siteId: number;
}

// Only the weather-adjusted model drives the live expected calc; the review
// panel is intentionally scoped to it (design-estimate is a separate track).
const WEATHER_ADJUSTED = 'weather_adjusted_model';

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

/**
 * READ-ONLY review of weather-adjusted expected baselines for a site.
 *
 * Surfaces draft, approved-not-active, and active baselines with full
 * provenance (promoted facts, reviewer constants, applied defaults, PTO
 * behavior, and `model_parameters_json` sources). It exposes NO approve /
 * activate controls and performs ZERO mutations — every query is a GET. It also
 * never previews a draft's expected curve: the preview endpoint refuses drafts,
 * so the panel only states that preview is unavailable for drafts.
 */
export const DraftBaselineReviewPanel: React.FC<DraftBaselineReviewPanelProps> = ({ siteId }) => {
  const enabled = Number.isSafeInteger(siteId) && siteId > 0;

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
    () => (data?.baselines ?? []).filter(b => b.baseline_type === WEATHER_ADJUSTED && b.status === 'draft'),
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
      <Chip size="small" variant="outlined" color="default" icon={<LockOutlinedIcon />} label="Read-only" />
    </Box>
  );

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
    const numField = (col: keyof ExpectedBaselineResponse): number | null => {
      const v = draft[col];
      return typeof v === 'number' ? v : null;
    };

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
      </Box>
    );
  };

  const renderSummaryLine = (b: ExpectedBaselineResponse) => (
    <Box key={b.id} sx={{ py: 0.5 }} data-testid={`baseline-summary-${b.id}`}>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 1 }}>
        <Chip size="small" color={statusChipColor(b.status)} label={statusLabel(b.status)} />
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

  const nothingToShow = drafts.length === 0 && approvedNotActive.length === 0 && active == null;

  return (
    <Paper variant="outlined" sx={{ p: 2, mt: 2 }} data-testid="draft-baseline-review-panel">
      {headerRow}
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
        A strictly read-only view of weather-adjusted expected baselines and their provenance. Nothing here is approved,
        activated, or changed.
      </Typography>

      <Alert severity="info" sx={{ mb: 1.5 }} data-testid="draft-baseline-activation-note">
        <AlertTitle>Activation is intentionally not available here</AlertTitle>
        Activating a baseline can silently rewrite historical expected values, because O&amp;M reads a single active
        baseline without an effective-date filter. Activation will return once period-effective baseline selection
        exists — for now this panel only reviews baselines.
      </Alert>

      {nothingToShow ? (
        <Typography variant="body2" color="text.secondary" data-testid="draft-baseline-review-empty">
          No draft, approved, or active weather-adjusted baseline exists for this project yet.
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
              approvedNotActive.map(renderSummaryLine)
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
              renderSummaryLine(active)
            ) : (
              <Tooltip title="No active weather-adjusted baseline drives expected output for this project yet.">
                <Typography variant="body2" color="text.secondary">
                  No active baseline.
                </Typography>
              </Tooltip>
            )}
          </Box>
        </>
      )}

      {/* Design-estimate separation */}
      <Alert severity="info" sx={{ mt: 1.5 }} data-testid="draft-baseline-design-estimate-note">
        Design-estimate baselines are a separate track and are neither reviewed nor changed here.
      </Alert>
    </Paper>
  );
};

export default DraftBaselineReviewPanel;
