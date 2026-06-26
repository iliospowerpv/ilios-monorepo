import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Divider from '@mui/material/Divider';

import type { BaselinePhysicsValidation, BaselineValidationFieldVerdict } from '../../../../../../../types/telemetryV2';
import {
  classificationColor,
  classificationLabel,
  groupFieldVerdicts,
  resolveValidationState
} from '../../../../../../../utils/baselineValidation';
import { PLACEHOLDER } from '../utils';

interface ValidationSummaryPanelProps {
  /** The fail-closed verdict to render (diff `to_validation` / `from_validation`). */
  validation: BaselinePhysicsValidation | null | undefined;
  /** Who this verdict describes, e.g. "Proposed baseline" / "Active baseline". */
  who: string;
  /** Unique testid prefix so two panels (proposed + active) can coexist. */
  testIdPrefix?: string;
}

const humanizeField = (field: string): string =>
  field
    .replace(/_pct$/i, ' %')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());

const fmtValue = (v: number | null | undefined, unit?: string): string => {
  if (v == null || !Number.isFinite(v)) return PLACEHOLDER;
  return `${v.toLocaleString()}${unit ? ` ${unit}` : ''}`;
};

/**
 * Read-only grouped validation panel (Phase B2.1 + B2.6). Consumes the verdict
 * the backend engine already produced (carried by the diff endpoint's
 * `from_validation` / `to_validation`) and renders the per-field results grouped
 * by severity — Blocking → Warnings → Plausible — with the engine's `reason` and
 * actionable `required_action` guidance. It computes NOTHING about physics and
 * never re-derives a classification; a missing verdict renders an honest neutral
 * state, never a fabricated pass/fail.
 */
export const ValidationSummaryPanel: React.FC<ValidationSummaryPanelProps> = ({
  validation,
  who,
  testIdPrefix = 'validation-summary'
}) => {
  const meta = resolveValidationState(validation);
  const groups = groupFieldVerdicts(validation);
  const hasFieldDetail = groups.blockingCount + groups.warningCount + groups.plausibleCount > 0;

  const stateChip = (
    <Chip size="small" color={meta.color} label={`${who}: ${meta.label}`} data-testid={`${testIdPrefix}-state-chip`} />
  );

  const renderField = (f: BaselineValidationFieldVerdict) => (
    <Box key={f.field} sx={{ py: 0.5 }} data-testid={`${testIdPrefix}-field-${f.field}`}>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 1 }}>
        <Typography variant="body2" sx={{ fontWeight: 600 }}>
          {humanizeField(f.field)}
        </Typography>
        <Typography variant="body2" color="text.secondary">
          {fmtValue(f.entered_value, f.expected_unit)}
        </Typography>
        <Chip
          size="small"
          variant="outlined"
          color={classificationColor(f.classification)}
          label={classificationLabel(f.classification)}
        />
      </Box>
      {f.reason && (
        <Typography variant="caption" color="text.secondary" display="block">
          {f.reason}
        </Typography>
      )}
      {f.required_action && (
        <Typography
          variant="caption"
          color="text.primary"
          display="block"
          sx={{ fontWeight: 600 }}
          data-testid={`${testIdPrefix}-action-${f.field}`}
        >
          Next: {f.required_action}
        </Typography>
      )}
    </Box>
  );

  return (
    <Box sx={{ my: 1 }} data-testid={`${testIdPrefix}-panel`}>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 1 }}>
        {stateChip}
        {(validation?.blocking_field_count ?? groups.blockingCount) > 0 && (
          <Chip
            size="small"
            color="error"
            variant="outlined"
            label={`${validation?.blocking_field_count ?? groups.blockingCount} blocking`}
          />
        )}
        {(validation?.warning_field_count ?? groups.warningCount) > 0 && (
          <Chip
            size="small"
            color="warning"
            variant="outlined"
            label={`${validation?.warning_field_count ?? groups.warningCount} warning`}
          />
        )}
      </Box>

      {validation?.summary && (
        <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 0.5 }}>
          {validation.summary}
        </Typography>
      )}

      {!validation ? (
        <Typography
          variant="caption"
          color="text.secondary"
          display="block"
          sx={{ mt: 0.5 }}
          data-testid={`${testIdPrefix}-unavailable`}
        >
          No validation verdict is available for this baseline.
        </Typography>
      ) : !hasFieldDetail ? (
        <Typography
          variant="caption"
          color="text.secondary"
          display="block"
          sx={{ mt: 0.5 }}
          data-testid={`${testIdPrefix}-summary-only`}
        >
          Per-field detail isn&apos;t available for this baseline (only a summary verdict).
        </Typography>
      ) : (
        <>
          {groups.blockingCount > 0 && (
            <Box sx={{ mt: 1 }} data-testid={`${testIdPrefix}-blocking`}>
              <Typography variant="overline" color="error">
                Blocking ({groups.blockingCount})
              </Typography>
              {groups.blocking.map(renderField)}
            </Box>
          )}
          {groups.warningCount > 0 && (
            <Box sx={{ mt: 1 }} data-testid={`${testIdPrefix}-warning`}>
              <Typography variant="overline" color="warning.main">
                Warnings ({groups.warningCount})
              </Typography>
              {groups.warning.map(renderField)}
            </Box>
          )}
          {groups.plausibleCount > 0 && (
            <Box sx={{ mt: 1 }} data-testid={`${testIdPrefix}-plausible`}>
              <Typography variant="overline" color="text.secondary">
                Validated ({groups.plausibleCount})
              </Typography>
              <Typography variant="caption" color="text.secondary" display="block">
                {groups.plausible.map(f => humanizeField(f.field)).join(', ')}
              </Typography>
            </Box>
          )}
        </>
      )}
      <Divider sx={{ mt: 1 }} />
    </Box>
  );
};

export default ValidationSummaryPanel;
