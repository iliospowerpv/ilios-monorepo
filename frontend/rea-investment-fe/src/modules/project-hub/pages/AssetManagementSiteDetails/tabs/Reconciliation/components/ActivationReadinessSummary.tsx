import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';

import type { BaselinePhysicsValidation, ExpectedBaselineResponse } from '../../../../../../../types/telemetryV2';
import { groupFieldVerdicts } from '../../../../../../../utils/baselineValidation';

interface ActivationReadinessSummaryProps {
  baseline: ExpectedBaselineResponse;
  priorActive: ExpectedBaselineResponse | null;
  /** Proposed verdict (diff `to_validation`) when it matches this baseline. */
  validation?: BaselinePhysicsValidation | null;
  testId?: string;
}

type Tone = 'success' | 'error' | 'warning' | 'info';

const TONE_ICON: Record<Tone, React.ReactNode> = {
  success: <CheckCircleOutlineIcon fontSize="small" color="success" />,
  error: <ErrorOutlineIcon fontSize="small" color="error" />,
  warning: <WarningAmberIcon fontSize="small" color="warning" />,
  info: <InfoOutlinedIcon fontSize="small" color="info" />
};

/**
 * Pre-activation "what happens if I activate now" summary (Phase B2.9). Assembled
 * ENTIRELY from existing responses — it computes nothing and changes nothing. It
 * surfaces the blocking count (must be 0), warnings to acknowledge, PTO presence,
 * which baseline gets superseded, and the design-estimate separation. When no
 * verdict is available here, the blocking/warning lines render an honest neutral
 * note (the server re-checks fail-closed on activate) rather than a fabricated
 * pass.
 */
export const ActivationReadinessSummary: React.FC<ActivationReadinessSummaryProps> = ({
  baseline,
  priorActive,
  validation,
  testId = 'activation-readiness-summary'
}) => {
  const groups = groupFieldVerdicts(validation);
  const blockingCount = validation?.blocking_field_count ?? groups.blockingCount;
  const warningCount = validation?.warning_field_count ?? groups.warningCount;

  const Item: React.FC<{ tone: Tone; testid: string; children: React.ReactNode }> = ({ tone, testid, children }) => (
    <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1, py: 0.5 }} data-testid={testid}>
      <Box sx={{ pt: '2px' }}>{TONE_ICON[tone]}</Box>
      <Typography variant="caption">{children}</Typography>
    </Box>
  );

  return (
    <Box sx={{ mt: 1 }} data-testid={testId}>
      <Typography variant="overline" color="text.secondary">
        If you activate now
      </Typography>

      {/* Blocking */}
      {!validation ? (
        <Item tone="info" testid={`${testId}-blocking-unknown`}>
          The fail-closed physics verdict isn&apos;t loaded here; the server re-checks it on activate and will block a
          physically invalid baseline.
        </Item>
      ) : blockingCount > 0 ? (
        <Item tone="error" testid={`${testId}-blocking`}>
          <strong>{blockingCount}</strong> blocking value{blockingCount === 1 ? '' : 's'} — activation is not possible
          until a corrected, source-backed replacement is created.
        </Item>
      ) : (
        <Item tone="success" testid={`${testId}-blocking`}>
          No blocking values.
        </Item>
      )}

      {/* Warnings */}
      {validation &&
        (warningCount > 0 ? (
          <Item tone="warning" testid={`${testId}-warnings`}>
            <strong>{warningCount}</strong> warning{warningCount === 1 ? '' : 's'} must be acknowledged with a required
            source note to proceed.
          </Item>
        ) : (
          <Item tone="success" testid={`${testId}-warnings`}>
            No warnings to acknowledge.
          </Item>
        ))}

      {/* PTO presence */}
      {baseline.pto_date ? (
        <Item tone="info" testid={`${testId}-pto`}>
          PTO date set ({baseline.pto_date}); expected production is computed from the PTO boundary.
        </Item>
      ) : (
        <Item tone="warning" testid={`${testId}-pto`}>
          No PTO date is set — expected production stays suppressed (NULL, never 0) until one is provided.
        </Item>
      )}

      {/* Supersession */}
      {priorActive ? (
        <Item tone="info" testid={`${testId}-supersedes`}>
          The current active baseline (<strong>{priorActive.baseline_name}</strong>, #{priorActive.id}) will be
          superseded and kept for audit.
        </Item>
      ) : (
        <Item tone="info" testid={`${testId}-supersedes`}>
          There is no current active baseline — this will become the first active one.
        </Item>
      )}

      {/* Design-estimate separation */}
      <Item tone="info" testid={`${testId}-design-points`}>
        Design-estimate points are a separate track and are not created or changed by activation.
      </Item>

      <Box sx={{ mt: 0.5 }}>
        <Chip
          size="small"
          variant="outlined"
          color="default"
          label="Historical periods keep their period-effective baseline"
        />
      </Box>
    </Box>
  );
};

export default ActivationReadinessSummary;
