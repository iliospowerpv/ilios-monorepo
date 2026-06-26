import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Tooltip from '@mui/material/Tooltip';
import HistoryOutlinedIcon from '@mui/icons-material/HistoryOutlined';

import type { ExpectedBaselineResponse } from '../../../../../../../types/telemetryV2';
import type { SourceBasisDrift } from '../../../../../../../api';
import { formatDateTime } from '../utils';

interface ValidationHistoryPanelProps {
  /** Weather-adjusted baselines (any status), as returned by the list endpoint. */
  baselines: ExpectedBaselineResponse[];
  /**
   * Read-only, value-based source-basis verdict for the ACTIVE baseline
   * (Phase B4). Drives a baseline-level chip on the matching active row. When
   * omitted/null no chip is rendered. `basis_unknown` is ALWAYS neutral, never red.
   */
  sourceBasisDrift?: SourceBasisDrift | null;
  testId?: string;
}

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
    default:
      return 'default';
  }
};

const statusLabel = (status: string): string => status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());

/**
 * Baseline-level source-basis chip for the active row (Phase B4, audit gap G5).
 * Read-only display of `sourceBasisDrift.state` — the only call-to-action is the
 * pre-existing manual rebuild path; no mutation affordance is introduced.
 */
const SourceBasisChip: React.FC<{ drift: SourceBasisDrift; testId: string }> = ({ drift, testId }) => {
  if (drift.state === 'drifted') {
    const fields = drift.drifted_fields.map(f => f.field);
    return (
      <Box sx={{ mt: 0.5 }} data-testid={testId}>
        <Tooltip title={fields.length > 0 ? `Drifted fields: ${fields.join(', ')}` : ''}>
          <Chip size="small" color="warning" label={`Source basis drifted (${drift.drifted_fields.length})`} />
        </Tooltip>
        <Typography variant="caption" display="block" color="warning.main" sx={{ mt: 0.25 }}>
          Rebuild the active baseline to include the latest promoted value.
        </Typography>
      </Box>
    );
  }
  if (drift.state === 'source_retired') {
    return (
      <Box sx={{ mt: 0.5 }} data-testid={testId}>
        <Chip size="small" color="warning" label="Source fact retired" />
      </Box>
    );
  }
  if (drift.state === 'basis_unknown') {
    // Neutral by design — never red. The basis simply was not recorded.
    return (
      <Box sx={{ mt: 0.5 }} data-testid={testId}>
        <Chip size="small" color="default" variant="outlined" label="Source basis not recorded" />
      </Box>
    );
  }
  // up_to_date (and any unknown future state) → subtle success/neutral chip.
  return (
    <Box sx={{ mt: 0.5 }} data-testid={testId}>
      <Chip size="small" color="success" variant="outlined" label="Source basis: up to date" />
    </Box>
  );
};

/**
 * Read-only version history (Phase B2.10). Assembled ENTIRELY from the existing
 * baseline list rows — NO new endpoint, NO new fetch. It surfaces every
 * weather-adjusted version's status and lifecycle timeline (created → approved →
 * active window) plus the supersession chain and persisted build notes.
 *
 * The per-activation waiver trail (who acknowledged which warnings, with what
 * source note) is recorded server-side on the activated row's
 * `validation_result_json` and is NOT carried on the list response, so it is not
 * shown here rather than fabricated — surfacing it would require a dedicated
 * read endpoint (intentionally out of scope for this sprint).
 */
export const ValidationHistoryPanel: React.FC<ValidationHistoryPanelProps> = ({
  baselines,
  sourceBasisDrift = null,
  testId = 'validation-history-panel'
}) => {
  if (!baselines || baselines.length === 0) return null;

  const ordered = [...baselines].sort((a, b) => {
    if (b.version !== a.version) return b.version - a.version;
    return (b.created_at ?? '').localeCompare(a.created_at ?? '');
  });

  return (
    <Box sx={{ mt: 1 }} data-testid={testId}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <HistoryOutlinedIcon fontSize="small" color="disabled" />
        <Typography variant="overline" color="text.secondary">
          Version history
        </Typography>
      </Box>
      {ordered.map(b => {
        const warnings = b.model_parameters_json?.warnings ?? [];
        const showDrift = sourceBasisDrift != null && sourceBasisDrift.baseline_id === b.id;
        return (
          <Box key={b.id} sx={{ py: 0.5 }} data-testid={`${testId}-row-${b.id}`}>
            <Box sx={{ display: 'flex', flexWrap: 'wrap', alignItems: 'center', gap: 1 }}>
              <Chip size="small" color={statusChipColor(b.status)} label={statusLabel(b.status)} />
              <Typography variant="body2">
                {b.baseline_name} (#{b.id}, v{b.version})
              </Typography>
              {b.supersedes_baseline_id != null && (
                <Chip
                  size="small"
                  variant="outlined"
                  color="default"
                  label={`Supersedes #${b.supersedes_baseline_id}`}
                />
              )}
            </Box>
            <Typography variant="caption" display="block" color="text.secondary">
              Created: {formatDateTime(b.created_at ?? null)}
              {b.approved_at ? ` · Approved: ${formatDateTime(b.approved_at)}` : ''}
              {b.active_from ? ` · Active from: ${formatDateTime(b.active_from)}` : ''}
              {b.active_to ? ` · Active to: ${formatDateTime(b.active_to)}` : ''}
            </Typography>
            {warnings.length > 0 && (
              <Typography variant="caption" display="block" color="text.secondary">
                {warnings.length} build note{warnings.length === 1 ? '' : 's'} recorded at draft time.
              </Typography>
            )}
            {showDrift && sourceBasisDrift != null && (
              <SourceBasisChip drift={sourceBasisDrift} testId={`${testId}-source-basis-${b.id}`} />
            )}
          </Box>
        );
      })}
    </Box>
  );
};

export default ValidationHistoryPanel;
