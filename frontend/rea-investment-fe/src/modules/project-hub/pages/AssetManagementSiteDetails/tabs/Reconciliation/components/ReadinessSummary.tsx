import React from 'react';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import HighlightOffIcon from '@mui/icons-material/HighlightOff';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import type { ReconciliationReadiness } from '../../../../../../../api';
import { PLACEHOLDER, formatDateTime } from '../utils';
import BaselineFromFactsPanel from './BaselineFromFactsPanel';

interface ReadinessSummaryProps {
  readiness: ReconciliationReadiness;
  /** Site whose promoted facts feed the actionable draft-baseline panel. */
  siteId?: number;
  /** Telemetry-admin (or system user) — gates the actionable create form. */
  canDraft?: boolean;
}

const BoolPill: React.FC<{ value: boolean | null; trueLabel: string; falseLabel: string; unknownLabel?: string }> = ({
  value,
  trueLabel,
  falseLabel,
  unknownLabel = 'Not applicable'
}) => {
  if (value === null || value === undefined) {
    return <Chip icon={<HelpOutlineIcon />} label={unknownLabel} size="small" variant="outlined" color="default" />;
  }
  return value ? (
    <Chip icon={<CheckCircleOutlineIcon />} label={trueLabel} size="small" color="success" variant="outlined" />
  ) : (
    <Chip icon={<HighlightOffIcon />} label={falseLabel} size="small" color="warning" variant="outlined" />
  );
};

const StatTile: React.FC<{ title: string; children: React.ReactNode }> = ({ title, children }) => (
  <Paper variant="outlined" sx={{ p: 2, height: '100%' }}>
    <Typography variant="subtitle2" color="text.secondary" gutterBottom>
      {title}
    </Typography>
    {children}
  </Paper>
);

export const ReadinessSummary: React.FC<ReadinessSummaryProps> = ({ readiness, siteId, canDraft = false }) => {
  const hasSite = Number.isSafeInteger(siteId) && (siteId as number) > 0;
  return (
    <Box sx={{ mb: 3 }} data-testid="reconciliation-readiness">
      <Typography variant="h6" sx={{ fontWeight: 600, mb: 1.5 }}>
        Baseline Readiness
      </Typography>
      <Grid container spacing={2}>
        <Grid item xs={12} md={4}>
          <StatTile title="Draft baseline (weather-adjusted)">
            <BoolPill value={readiness.facts_to_draft_ready} trueLabel="Ready to draft" falseLabel="Not ready" />
            {readiness.missing_required_physics_fields.length > 0 && (
              <Box sx={{ mt: 1 }}>
                <Typography variant="caption" color="text.secondary">
                  Missing required physics fields:
                </Typography>
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.5 }}>
                  {readiness.missing_required_physics_fields.map(field => (
                    <Chip key={field} label={field} size="small" color="warning" variant="outlined" />
                  ))}
                </Box>
              </Box>
            )}
            {readiness.facts_to_draft_warnings.length > 0 && (
              <Box sx={{ mt: 1 }}>
                {readiness.facts_to_draft_warnings.map(warning => (
                  <Typography key={warning} variant="caption" display="block" color="text.secondary">
                    • {warning}
                  </Typography>
                ))}
              </Box>
            )}
          </StatTile>
        </Grid>

        <Grid item xs={12} md={4}>
          <StatTile title="Active baseline">
            <BoolPill
              value={readiness.active_baseline_available}
              trueLabel="Active baseline exists"
              falseLabel="No active baseline"
            />
            <Box sx={{ mt: 1 }}>
              <Typography variant="caption" display="block" color="text.secondary">
                Baseline ID: {readiness.active_baseline_id ?? PLACEHOLDER}
              </Typography>
              <Typography variant="caption" display="block" color="text.secondary">
                Created: {formatDateTime(readiness.active_baseline_created_at)}
              </Typography>
            </Box>
          </StatTile>
        </Grid>

        <Grid item xs={12} md={4}>
          <StatTile title="Design-estimate points">
            <BoolPill
              value={readiness.design_points_ready}
              trueLabel="Points ready"
              falseLabel="Points incomplete"
              unknownLabel="No design baseline"
            />
            <Box sx={{ mt: 1 }}>
              <Typography variant="caption" display="block" color="text.secondary">
                Baseline: {readiness.design_estimate_baseline_id ?? PLACEHOLDER}
                {readiness.design_estimate_baseline_status ? ` (${readiness.design_estimate_baseline_status})` : ''}
              </Typography>
              <Typography variant="caption" display="block" color="text.secondary">
                Months present: {readiness.design_points_present_months.length}/12
              </Typography>
              {readiness.design_points_missing.length > 0 && (
                <Typography variant="caption" display="block" color="warning.main">
                  Missing: {readiness.design_points_missing.join(', ')}
                </Typography>
              )}
              {readiness.design_points_parse_errors.length > 0 && (
                <Typography variant="caption" display="block" color="error.main">
                  Parse errors: {readiness.design_points_parse_errors.length}
                </Typography>
              )}
            </Box>
          </StatTile>
        </Grid>
      </Grid>

      {hasSite && <BaselineFromFactsPanel siteId={siteId as number} canDraft={canDraft} />}
    </Box>
  );
};

export default ReadinessSummary;
