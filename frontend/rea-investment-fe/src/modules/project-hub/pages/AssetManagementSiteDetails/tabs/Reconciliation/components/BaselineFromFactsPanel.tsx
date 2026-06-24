import React, { useMemo, useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import Grid from '@mui/material/Grid';
import Chip from '@mui/material/Chip';
import TextField from '@mui/material/TextField';
import Button from '@mui/material/Button';
import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import Divider from '@mui/material/Divider';
import FormControlLabel from '@mui/material/FormControlLabel';
import Checkbox from '@mui/material/Checkbox';
import CircularProgress from '@mui/material/CircularProgress';
import Tooltip from '@mui/material/Tooltip';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import LockOutlinedIcon from '@mui/icons-material/LockOutlined';
import AutoFixHighIcon from '@mui/icons-material/AutoFixHigh';

import { ApiClient } from '../../../../../../../api';
import type {
  BaselineReadinessFieldStatus,
  CreateDraftFromFactsRequest,
  CreateDraftFromFactsResponse,
  ExpectedBaselineListResponse,
  NormalizationConfirmationRequest,
  ReadinessFromFactsResponse
} from '../../../../../../../types/telemetryV2';
import { formatDateTime } from '../utils';

interface BaselineFromFactsPanelProps {
  siteId: number;
  /** Telemetry-admin (or system user). When false the panel is read-only. */
  canDraft: boolean;
}

// Physics inputs that come from promoted project_facts (never edited here).
const FACT_FIELDS = ['module_wattage', 'module_quantity', 'inverter_wattage', 'inverter_quantity'] as const;

// Reviewer-supplied datasheet constants with no fact source — all required.
const REQUIRED_CONSTANTS = [
  'thermal_coefficient_pct',
  'power_tolerance_min_pct',
  'year_1_degradation_pct',
  'annual_degradation_pct',
  'cec_efficiency_pct'
] as const;

// Optional numeric reviewer inputs — absence is a warning, not a blocker.
const OPTIONAL_NUMS = ['dc_loss_pct', 'ac_loss_pct', 'medium_voltage_loss_pct', 'soiling_factor'] as const;

type NumericField = (typeof REQUIRED_CONSTANTS)[number] | (typeof OPTIONAL_NUMS)[number];

// Mirrors the backend fail-closed thermal-coefficient classifier
// (`baseline_physics_validation._classify_thermal_coefficient`) so the reviewer
// gets the SAME verdict inline before submitting. The canonical contract is
// %/°C and crystalline-silicon coefficients are NEGATIVE (~ -0.35 %/°C). No
// value is ever auto-converted; this only advises (warning) or blocks
// (hard_invalid) — it never rewrites the entered number.
type ThermalLevel = 'plausible' | 'warning' | 'hard_invalid';

const classifyThermalCoefficientPct = (v: number): { level: ThermalLevel; message: string } => {
  if (v >= 0) {
    return {
      level: 'hard_invalid',
      message:
        'A zero or positive thermal coefficient is non-physical for a crystalline-silicon baseline (expected ~ -0.35 %/°C).'
    };
  }
  const av = Math.abs(v);
  if (av < 0.01) {
    return {
      level: 'warning',
      message: `Magnitude ${av} is near a decimal fraction per °C (e.g. -0.0035); confirm the value is %/°C, not a fraction.`
    };
  }
  if (av < 0.2) {
    return {
      level: 'warning',
      message: `Magnitude ${av} %/°C is unusually small for crystalline silicon; confirm against the module datasheet.`
    };
  }
  if (av <= 0.5) {
    return {
      level: 'plausible',
      message: `${v} %/°C is within the typical crystalline-silicon range (~ -0.20 to -0.50 %/°C).`
    };
  }
  if (av <= 0.8) {
    return {
      level: 'warning',
      message: `Magnitude ${av} %/°C resembles a %/°F coefficient copied into a %/°C field; confirm the unit (no automatic conversion is applied).`
    };
  }
  return {
    level: 'hard_invalid',
    message: `Magnitude ${av} %/°C is implausibly large for a thermal coefficient.`
  };
};

// Live derived temperature-factor preview at a hot operating point, using the
// SAME formula production uses: factor = 1 + (tc/100) * (cell_C - 25). It shows
// how the entered %/°C coefficient scales output away from the 25 °C reference.
const THERMAL_PREVIEW_CELL_C = 45;
const thermalFactorAt = (tcPct: number, cellC: number): number => 1 + (tcPct / 100) * (cellC - 25);

// Source statuses where the input is already usable and needs no reviewer action.
const USABLE_STATUSES = new Set<string>([
  'active_fact',
  'satisfied',
  'normalized_confirmed',
  'optional_default_applied'
]);

const readinessQueryKey = (siteId: number) => ['site', 'baseline-readiness-from-facts', { siteId }] as const;
// Shared with DraftBaselineReviewPanel so React Query dedupes the single fetch
// (keep this tuple identical to that panel's baselinesQueryKey).
const baselinesQueryKey = (siteId: number) => ['site', 'expected-baselines', { siteId }] as const;

// Only the weather-adjusted model drives the live expected calc (design-estimate
// is a separate track), so existing-baseline awareness is scoped to it.
const WEATHER_ADJUSTED = 'weather_adjusted_model';

const sourceStatusChip = (
  status: string
): { label: string; color: 'success' | 'warning' | 'error' | 'info' | 'default' } => {
  switch (status) {
    case 'active_fact':
    case 'satisfied':
      return { label: 'From facts', color: 'success' };
    case 'normalized_confirmed':
      return { label: 'Normalized', color: 'success' };
    case 'optional_default_applied':
      return { label: 'Default applied', color: 'info' };
    case 'reviewer_supplied':
      return { label: 'Reviewer value', color: 'success' };
    case 'reviewer_supplied_needed':
      return { label: 'Needs reviewer value', color: 'warning' };
    case 'active_fact_but_non_numeric':
      return { label: 'Needs normalization', color: 'warning' };
    case 'pre_pto_expected_suppressed':
      return { label: 'Pre-PTO (suppressed)', color: 'info' };
    case 'missing':
      return { label: 'Missing', color: 'error' };
    default:
      return { label: status, color: 'default' };
  }
};

const blockingChip = (level: string): { label: string; color: 'error' | 'warning' | 'default' } | null => {
  switch (level) {
    case 'blocks_draft_baseline':
      return { label: 'Blocks draft', color: 'error' };
    case 'blocks_expected':
      return { label: 'Lowers confidence', color: 'warning' };
    default:
      return null;
  }
};

/** Build the normalization-confirmation payload from a confirmed blocker. */
const buildNormalization = (b: BaselineReadinessFieldStatus): NormalizationConfirmationRequest | null => {
  const n = b.normalization;
  if (!n || n.blocked || n.proposed_value == null) return null;
  return {
    confirmed_value: n.proposed_value,
    unit: n.target_unit,
    allow_conversion: n.method === 'unit_convert' || n.requires_conversion_confirmation,
    source_fact_id: b.fact_id,
    raw_value: n.raw_value
  };
};

/**
 * Actionable "create a weather-adjusted DRAFT baseline from promoted facts"
 * surface. It reads the per-field readiness ladder, collects reviewer datasheet
 * constants + optional adjustments, lets a reviewer confirm (never auto-apply) a
 * unit normalization for a unit-qualified fact, and POSTs to create a DRAFT. It
 * never mutates project_facts and never activates a baseline.
 */
export const BaselineFromFactsPanel: React.FC<BaselineFromFactsPanelProps> = ({ siteId, canDraft }) => {
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery<ReadinessFromFactsResponse>({
    queryKey: readinessQueryKey(siteId),
    queryFn: () => ApiClient.telemetryV2.getReadinessFromFacts(siteId),
    enabled: canDraft && Number.isSafeInteger(siteId) && siteId > 0,
    retry: false
  });

  // Existing-baseline awareness: shares the review panel's query key so this is a
  // single cached fetch, not a duplicate request.
  const { data: baselinesData } = useQuery<ExpectedBaselineListResponse>({
    queryKey: baselinesQueryKey(siteId),
    queryFn: () => ApiClient.telemetryV2.listExpectedBaselines(siteId),
    enabled: canDraft && Number.isSafeInteger(siteId) && siteId > 0,
    retry: false
  });

  const [values, setValues] = useState<Record<string, string>>({});
  const [ptoDate, setPtoDate] = useState('');
  const [confirmedNorm, setConfirmedNorm] = useState<Record<string, boolean>>({});

  const blockersByField = useMemo(() => {
    const map = new Map<string, BaselineReadinessFieldStatus>();
    (data?.field_blockers ?? []).forEach(b => map.set(b.field, b));
    return map;
  }, [data]);

  const mutation = useMutation<CreateDraftFromFactsResponse, unknown, CreateDraftFromFactsRequest>({
    mutationFn: payload => ApiClient.telemetryV2.createDraftFromFacts(siteId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: readinessQueryKey(siteId) });
      queryClient.invalidateQueries({ queryKey: baselinesQueryKey(siteId) });
      queryClient.invalidateQueries({ queryKey: ['site', 'reconciliation', { siteId }] });
    }
  });

  if (!canDraft) {
    return (
      <Paper variant="outlined" sx={{ p: 2, mt: 2 }} data-testid="baseline-from-facts-readonly">
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <LockOutlinedIcon fontSize="small" color="disabled" />
          <Typography variant="body2" color="text.secondary">
            Building a weather-adjusted draft baseline from these facts requires telemetry-admin access.
          </Typography>
        </Box>
      </Paper>
    );
  }

  if (isLoading) {
    return (
      <Box display="flex" alignItems="center" gap={1} sx={{ mt: 2 }} data-testid="baseline-from-facts-loading">
        <CircularProgress size={18} />
        <Typography variant="body2" color="text.secondary">
          Checking baseline readiness from promoted facts…
        </Typography>
      </Box>
    );
  }

  if (error) {
    const status = (error as { response?: { status?: number } })?.response?.status;
    if (status === 401 || status === 403) {
      return (
        <Paper variant="outlined" sx={{ p: 2, mt: 2 }} data-testid="baseline-from-facts-forbidden">
          <Typography variant="body2" color="text.secondary">
            You don&apos;t have telemetry-admin access to draft a baseline for this project.
          </Typography>
        </Paper>
      );
    }
    return (
      <Alert severity="error" sx={{ mt: 2 }} data-testid="baseline-from-facts-error">
        Couldn&apos;t load baseline readiness from facts. Please try again later.
      </Alert>
    );
  }

  if (!data) return null;

  // Existing weather-adjusted baselines for honest status messaging.
  const baselines = baselinesData?.baselines ?? [];
  const activeBaseline = baselines.find(b => b.baseline_type === WEATHER_ADJUSTED && b.status === 'active') ?? null;
  const pendingDrafts = baselines.filter(
    b => b.baseline_type === WEATHER_ADJUSTED && (b.status === 'draft' || b.status === 'in_review')
  );

  const numField = (field: NumericField) => values[field] ?? '';
  const parseEntered = (raw: string): number | null | undefined => {
    const trimmed = raw.trim();
    if (trimmed === '') return undefined; // not entered
    const n = Number(trimmed);
    return Number.isFinite(n) ? n : null; // null === invalid
  };

  const invalidFields = ([...REQUIRED_CONSTANTS, ...OPTIONAL_NUMS] as NumericField[]).filter(
    f => parseEntered(numField(f)) === null
  );
  const missingRequired = REQUIRED_CONSTANTS.filter(f => parseEntered(numField(f)) === undefined);

  // Fact inputs that still need a reviewer action (confirm a normalization or fix
  // the source in the Data Room) before a draft can be built.
  const factBlockers = FACT_FIELDS.map(f => blockersByField.get(f)).filter((b): b is BaselineReadinessFieldStatus =>
    Boolean(b)
  );
  const factNeedsAction = factBlockers.filter(
    b =>
      b.required &&
      !USABLE_STATUSES.has(b.source_status) &&
      !(b.normalization && !b.normalization.blocked && confirmedNorm[b.field])
  );

  // PTO is required for the weather-adjusted model: without it the backend
  // suppresses the entire expected curve, so the draft would be unusable.
  const ptoMissing = ptoDate.trim() === '';

  // Fail-closed inline guard: a hard_invalid thermal coefficient (e.g. positive,
  // or a magnitude that is clearly a unit mistake) is non-physical, so block the
  // draft before it is ever created. Warnings do NOT block. The entered value is
  // never auto-converted.
  const thermalParsed = parseEntered(numField('thermal_coefficient_pct'));
  const thermalHardInvalid =
    typeof thermalParsed === 'number' && classifyThermalCoefficientPct(thermalParsed).level === 'hard_invalid';

  const canSubmit =
    invalidFields.length === 0 &&
    missingRequired.length === 0 &&
    factNeedsAction.length === 0 &&
    !ptoMissing &&
    !thermalHardInvalid &&
    !mutation.isPending;

  const handleSubmit = () => {
    const normalizations: Record<string, NormalizationConfirmationRequest> = {};
    factBlockers.forEach(b => {
      if (confirmedNorm[b.field]) {
        const norm = buildNormalization(b);
        if (norm) normalizations[b.field] = norm;
      }
    });

    const payload: CreateDraftFromFactsRequest = { baseline_type: 'weather_adjusted_model' };
    REQUIRED_CONSTANTS.forEach(f => {
      const v = parseEntered(numField(f));
      if (typeof v === 'number') payload[f] = v;
    });
    OPTIONAL_NUMS.forEach(f => {
      const v = parseEntered(numField(f));
      if (typeof v === 'number') payload[f] = v;
    });
    const pto = ptoDate.trim();
    if (pto) payload.pto_date = pto;
    if (Object.keys(normalizations).length > 0) payload.normalizations = normalizations;

    mutation.mutate(payload);
  };

  const result = mutation.data;
  const reviewBody = (() => {
    const data422 = (mutation.error as { response?: { data?: unknown } } | undefined)?.response?.data;
    if (
      data422 &&
      typeof data422 === 'object' &&
      (data422 as CreateDraftFromFactsResponse).status === 'review_required'
    ) {
      return data422 as CreateDraftFromFactsResponse;
    }
    return null;
  })();
  const genericError = mutation.isError && !reviewBody;

  const renderFactRow = (b: BaselineReadinessFieldStatus) => {
    const chip = sourceStatusChip(b.source_status);
    const blocking = blockingChip(b.blocking_level);
    const norm = b.normalization;
    const confirmable = Boolean(norm && !norm.blocked && norm.requires_confirmation);
    return (
      <Box key={b.field} sx={{ py: 1 }} data-testid={`fact-row-${b.field}`}>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 1 }}>
          <Typography variant="body2" sx={{ fontWeight: 600 }}>
            {b.display_label}
            {b.expected_unit ? ` (${b.expected_unit})` : ''}
          </Typography>
          <Chip size="small" variant="outlined" color={chip.color} label={chip.label} />
          {blocking && <Chip size="small" color={blocking.color} label={blocking.label} />}
          {b.current_normalized_value != null && (
            <Typography variant="caption" color="text.secondary">
              = {b.current_normalized_value}
            </Typography>
          )}
          {b.current_normalized_value == null && b.current_raw_value && (
            <Typography variant="caption" color="text.secondary">
              raw: {b.current_raw_value}
            </Typography>
          )}
        </Box>
        {b.reason && (
          <Typography variant="caption" color="text.secondary" display="block">
            {b.reason}
          </Typography>
        )}
        {norm && norm.blocked && (
          <Typography variant="caption" color="error.main" display="block">
            Cannot normalize automatically: {norm.reason}
            {b.recommended_action ? ` — ${b.recommended_action}` : ''}
          </Typography>
        )}
        {confirmable && norm && (
          <FormControlLabel
            sx={{ mt: 0.5 }}
            control={
              <Checkbox
                size="small"
                checked={Boolean(confirmedNorm[b.field])}
                onChange={e => setConfirmedNorm(prev => ({ ...prev, [b.field]: e.target.checked }))}
                data-testid={`confirm-norm-${b.field}`}
              />
            }
            label={
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                <AutoFixHighIcon fontSize="inherit" color="action" />
                <Typography variant="caption">
                  {norm.method === 'unit_convert'
                    ? `Convert ${norm.raw_value} → ${norm.proposed_value} ${norm.target_unit} (${norm.from_unit ?? '?'} → ${norm.target_unit})`
                    : `Use ${norm.raw_value} as ${norm.proposed_value} ${norm.target_unit}`}
                </Typography>
              </Box>
            }
          />
        )}
        {!USABLE_STATUSES.has(b.source_status) && !confirmable && b.recommended_action && !norm?.blocked && (
          <Typography variant="caption" color="warning.main" display="block">
            Next: {b.recommended_action}
          </Typography>
        )}
      </Box>
    );
  };

  // Thermal coefficient gets bespoke wording, a fail-closed inline verdict, and a
  // live derived temperature-factor preview (the other constants reuse the
  // generic renderer below).
  const renderThermalField = () => {
    const field: NumericField = 'thermal_coefficient_pct';
    const b = blockersByField.get(field);
    const raw = numField(field);
    const parsed = parseEntered(raw);
    const numericInvalid = parsed === null;
    const verdict = typeof parsed === 'number' ? classifyThermalCoefficientPct(parsed) : null;
    const isError = numericInvalid || verdict?.level === 'hard_invalid';
    const label = `${b?.display_label ?? 'Thermal coefficient'} (% per °C)`;
    const helper = numericInvalid
      ? 'Enter a number'
      : 'Negative for crystalline silicon, e.g. -0.35. Units are % per °C (not %/°F, not a decimal fraction); no conversion is applied.';
    const verdictColor =
      verdict?.level === 'hard_invalid' ? 'error.main' : verdict?.level === 'warning' ? 'warning.main' : 'success.main';
    const previewFactor = typeof parsed === 'number' ? thermalFactorAt(parsed, THERMAL_PREVIEW_CELL_C) : null;
    return (
      <Grid item xs={12} sm={6} md={4} key={field}>
        <TextField
          fullWidth
          size="small"
          type="number"
          required
          label={label}
          value={raw}
          onChange={e => setValues(prev => ({ ...prev, [field]: e.target.value }))}
          error={isError}
          helperText={helper}
          inputProps={{ 'data-testid': `input-${field}`, step: 'any' }}
        />
        {verdict && (
          <Typography
            variant="caption"
            sx={{ color: verdictColor, display: 'block', mt: 0.5 }}
            data-testid="thermal-verdict"
          >
            {verdict.message}
          </Typography>
        )}
        {previewFactor != null && (
          <Typography variant="caption" color="text.secondary" display="block" data-testid="thermal-preview">
            Derived temperature factor at {THERMAL_PREVIEW_CELL_C} °C: {previewFactor.toFixed(4)}× (output ≈{' '}
            {(previewFactor * 100).toFixed(1)}% of the 25 °C reference).
          </Typography>
        )}
      </Grid>
    );
  };

  const renderNumberField = (field: NumericField) => {
    if (field === 'thermal_coefficient_pct') return renderThermalField();
    const b = blockersByField.get(field);
    const isRequired = (REQUIRED_CONSTANTS as readonly string[]).includes(field);
    const invalid = parseEntered(numField(field)) === null;
    const label = `${b?.display_label ?? field}${b?.expected_unit ? ` (${b.expected_unit})` : ''}`;
    const helper = invalid
      ? 'Enter a number'
      : b?.default_value != null
        ? `Optional — defaults to ${b.default_value} if left blank`
        : (b?.recommended_action ?? '');
    return (
      <Grid item xs={12} sm={6} md={4} key={field}>
        <TextField
          fullWidth
          size="small"
          type="number"
          required={isRequired}
          label={label}
          value={numField(field)}
          onChange={e => setValues(prev => ({ ...prev, [field]: e.target.value }))}
          error={invalid}
          helperText={helper}
          inputProps={{ 'data-testid': `input-${field}`, step: 'any' }}
        />
      </Grid>
    );
  };

  return (
    <Paper variant="outlined" sx={{ p: 2, mt: 2 }} data-testid="baseline-from-facts-panel">
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
          Create weather-adjusted draft baseline
        </Typography>
        {activeBaseline ? (
          <Chip
            size="small"
            color="success"
            variant="outlined"
            icon={<CheckCircleOutlineIcon />}
            label={`Active baseline #${activeBaseline.id}`}
          />
        ) : pendingDrafts.length > 0 ? (
          <Chip size="small" color="info" variant="outlined" label={`Draft #${pendingDrafts[0].id} pending`} />
        ) : data.ready ? (
          <Chip size="small" color="success" variant="outlined" icon={<CheckCircleOutlineIcon />} label="Facts ready" />
        ) : (
          <Chip size="small" color="warning" variant="outlined" label="New draft inputs needed" />
        )}
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
        Physics inputs come from promoted facts (never edited here). Supply the datasheet constants below to build a{' '}
        <strong>draft</strong> baseline — it is never auto-activated, and existing facts and active baselines are never
        changed.
      </Typography>

      {activeBaseline && (
        <Alert severity="info" sx={{ mb: 1.5 }} data-testid="baseline-active-exists">
          <AlertTitle>An active weather-adjusted baseline already exists</AlertTitle>
          Baseline #{activeBaseline.id}
          {activeBaseline.baseline_name ? ` (${activeBaseline.baseline_name})` : ''} is active
          {activeBaseline.active_from ? ` from ${formatDateTime(activeBaseline.active_from)}` : ''}. The fields below
          are not pre-filled from it — creating a new draft here leaves the active baseline unchanged until you review
          and activate the new one.
        </Alert>
      )}
      {!activeBaseline && pendingDrafts.length > 0 && (
        <Alert severity="info" sx={{ mb: 1.5 }} data-testid="baseline-draft-exists">
          {pendingDrafts.length} draft weather-adjusted baseline(s) already await review or activation. Submitting
          identical inputs returns the existing draft rather than creating a duplicate.
        </Alert>
      )}

      <Typography variant="overline" color="text.secondary">
        From promoted facts
      </Typography>
      <Box sx={{ mb: 1 }}>
        {factBlockers.length > 0 ? (
          factBlockers.map(renderFactRow)
        ) : (
          <Typography variant="body2" color="text.secondary">
            No equipment facts are promoted yet.
          </Typography>
        )}
      </Box>

      <Divider sx={{ my: 1.5 }} />

      <Typography variant="overline" color="text.secondary">
        Reviewer datasheet constants (required)
      </Typography>
      <Grid container spacing={2} sx={{ mt: 0 }}>
        {REQUIRED_CONSTANTS.map(renderNumberField)}
      </Grid>

      <Typography variant="overline" color="text.secondary" sx={{ display: 'block', mt: 2 }}>
        Operation date (required)
      </Typography>
      <Grid container spacing={2} sx={{ mt: 0 }}>
        <Grid item xs={12} sm={6} md={4}>
          <TextField
            fullWidth
            size="small"
            type="date"
            required
            label="PTO Date"
            value={ptoDate}
            onChange={e => setPtoDate(e.target.value)}
            error={ptoMissing}
            InputLabelProps={{ shrink: true }}
            helperText="Required — expected production is suppressed before PTO"
            inputProps={{ 'data-testid': 'input-pto_date' }}
          />
        </Grid>
      </Grid>

      <Typography variant="overline" color="text.secondary" sx={{ display: 'block', mt: 2 }}>
        Optional adjustments
      </Typography>
      <Grid container spacing={2} sx={{ mt: 0 }}>
        {OPTIONAL_NUMS.map(renderNumberField)}
      </Grid>

      {factNeedsAction.length > 0 && (
        <Alert severity="warning" sx={{ mt: 2 }} data-testid="baseline-fact-action-needed">
          {factNeedsAction.length} equipment fact(s) need attention before a draft can be built — confirm the proposed
          normalization above, or promote the value in the Data Room.
        </Alert>
      )}

      {result && (result.status === 'draft' || result.draft_baseline_id != null) && (
        <Alert severity="success" sx={{ mt: 2 }} data-testid="baseline-create-success">
          <AlertTitle>{result.idempotent_existing ? 'Draft already exists' : 'Draft baseline created'}</AlertTitle>
          {result.idempotent_existing
            ? `An identical draft already exists (baseline #${result.draft_baseline_id}). Nothing was changed.`
            : `Draft baseline #${result.draft_baseline_id} created. It is not active — review and activate it separately.`}
          {result.warnings.length > 0 && (
            <Box component="ul" sx={{ pl: 3, mb: 0, mt: 1 }}>
              {result.warnings.map(w => (
                <li key={w}>
                  <Typography variant="caption">{w}</Typography>
                </li>
              ))}
            </Box>
          )}
        </Alert>
      )}

      {reviewBody && (
        <Alert severity="warning" sx={{ mt: 2 }} data-testid="baseline-create-review-required">
          <AlertTitle>Review required — nothing was created</AlertTitle>
          {reviewBody.missing_fields.length > 0 && <>Still missing: {reviewBody.missing_fields.join(', ')}.</>}
        </Alert>
      )}

      {genericError && (
        <Alert severity="error" sx={{ mt: 2 }} data-testid="baseline-create-error">
          Couldn&apos;t create the draft baseline. Please try again.
        </Alert>
      )}

      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mt: 2 }}>
        <Tooltip
          title={
            missingRequired.length > 0
              ? 'Fill in all required datasheet constants first.'
              : ptoMissing
                ? 'Set the PTO date — it is required for a weather-adjusted baseline.'
                : factNeedsAction.length > 0
                  ? 'Resolve the equipment facts that need attention first.'
                  : ''
          }
        >
          <span>
            <Button
              variant="contained"
              onClick={handleSubmit}
              disabled={!canSubmit}
              startIcon={mutation.isPending ? <CircularProgress size={16} color="inherit" /> : undefined}
              data-testid="baseline-create-button"
            >
              {mutation.isPending ? 'Creating…' : 'Create draft baseline'}
            </Button>
          </span>
        </Tooltip>
        <Typography variant="caption" color="text.secondary">
          Creates a draft only — activation happens elsewhere.
        </Typography>
      </Box>
    </Paper>
  );
};

export default BaselineFromFactsPanel;
