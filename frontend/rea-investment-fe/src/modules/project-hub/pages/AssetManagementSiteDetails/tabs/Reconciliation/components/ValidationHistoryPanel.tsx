import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import HistoryOutlinedIcon from '@mui/icons-material/HistoryOutlined';

import type { ExpectedBaselineResponse } from '../../../../../../../types/telemetryV2';
import { formatDateTime } from '../utils';

interface ValidationHistoryPanelProps {
  /** Weather-adjusted baselines (any status), as returned by the list endpoint. */
  baselines: ExpectedBaselineResponse[];
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
          </Box>
        );
      })}
    </Box>
  );
};

export default ValidationHistoryPanel;
