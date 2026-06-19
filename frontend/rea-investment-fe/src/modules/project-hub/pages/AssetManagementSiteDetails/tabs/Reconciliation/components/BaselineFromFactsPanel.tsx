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
  NormalizationConfirmationRequest,
  ReadinessFromFactsResponse
} from '../../../../../../../types/telemetryV2';

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

// Source statuses where the input is already usable and needs no reviewer action.
const USABLE_STATUSES = new Set<string>([
  'active_fact',
  'satisfied',
  'normalized_confirmed',
  'optional_default_applied'
]);

const readinessQueryKey = (siteId: number) => ['site', 'baseline-readiness-from-facts', { siteId }] as const;

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

  const canSubmit =
    invalidFields.length === 0 && missingRequired.length === 0 && factNeedsAction.length === 0 && !mutation.isPending;

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

  const renderNumberField = (field: NumericField) => {
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
        {data.ready ? (
          <Chip size="small" color="success" variant="outlined" icon={<CheckCircleOutlineIcon />} label="Facts ready" />
        ) : (
          <Chip size="small" color="warning" variant="outlined" label="Needs reviewer input" />
        )}
      </Box>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
        Physics inputs come from promoted facts (never edited here). Supply the datasheet constants below to build a{' '}
        <strong>draft</strong> baseline — it is never auto-activated, and existing facts and active baselines are never
        changed.
      </Typography>

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
        Optional adjustments
      </Typography>
      <Grid container spacing={2} sx={{ mt: 0 }}>
        {OPTIONAL_NUMS.map(renderNumberField)}
        <Grid item xs={12} sm={6} md={4}>
          <TextField
            fullWidth
            size="small"
            type="date"
            label="PTO Date"
            value={ptoDate}
            onChange={e => setPtoDate(e.target.value)}
            InputLabelProps={{ shrink: true }}
            helperText="Optional — expected production is NULL before PTO"
            inputProps={{ 'data-testid': 'input-pto_date' }}
          />
        </Grid>
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
