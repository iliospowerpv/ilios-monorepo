import React from 'react';
import Paper from '@mui/material/Paper';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Tooltip from '@mui/material/Tooltip';
import CloudOutlinedIcon from '@mui/icons-material/CloudOutlined';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';

import { useExternalWeatherContext } from '../../../../../../hooks/weatherProvider';
import type { ExternalWeatherContextSource } from '../../../../../../types/weather';

/**
 * D2 — read-only external-weather context panel.
 *
 * This is purely additive and provenance-only: it renders the third-party
 * weather observations that have been imported for a site WITHOUT touching the
 * telemetry readiness/health verdicts above it. The panel always shows an
 * honest, prominent "context only — not expected-eligible" banner so no operator
 * can mistake imported GHI/ambient for plane-of-array / cell inputs. Absence of
 * a reading is rendered as an absent row, never a fabricated 0.
 */

// Observations are stored naive-UTC; append a Z so the browser renders them in
// the viewer's local timezone instead of treating them as local wall-clock.
const fmtInstant = (raw: string | null | undefined): string => {
  if (!raw) return '—';
  const hasTz = /[zZ]$|[+-]\d{2}:?\d{2}$/.test(raw);
  const d = new Date(hasTz ? raw : `${raw}Z`);
  return Number.isNaN(d.getTime()) ? 'Unavailable' : d.toLocaleString();
};

const fmtCount = (n: number | null | undefined): string =>
  typeof n === 'number' && Number.isFinite(n) ? n.toLocaleString() : '—';

const SourceRow: React.FC<{ source: ExternalWeatherContextSource }> = ({ source }) => {
  const metricSummary =
    source.metrics.length > 0
      ? source.metrics.map(m => `${m.metric} (${fmtCount(m.observation_count)})`).join(', ')
      : '—';
  return (
    <TableRow>
      <TableCell>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Typography variant="body2" fontWeight={600}>
            {source.display_name}
          </Typography>
          {source.is_modeled && (
            <Tooltip title="Modeled / reanalysis data — not a physical on-site sensor.">
              <Chip size="small" label="Modeled" color="default" variant="outlined" />
            </Tooltip>
          )}
          {!source.active && <Chip size="small" label="Inactive" color="default" variant="outlined" />}
        </Box>
        <Typography variant="caption" color="text.secondary">
          {source.provider_key || source.source_type}
          {source.default_confidence ? ` · confidence: ${source.default_confidence}` : ''}
        </Typography>
      </TableCell>
      <TableCell align="right">{fmtCount(source.observation_count)}</TableCell>
      <TableCell>
        {fmtInstant(source.earliest_obs)}
        {source.earliest_obs || source.latest_obs ? ' → ' : ''}
        {fmtInstant(source.latest_obs)}
      </TableCell>
      <TableCell>
        <Typography variant="caption" color="text.secondary">
          {metricSummary}
        </Typography>
      </TableCell>
    </TableRow>
  );
};

interface ExternalWeatherContextPanelProps {
  siteId: number;
}

export const ExternalWeatherContextPanel: React.FC<ExternalWeatherContextPanelProps> = ({ siteId }) => {
  const { data, isLoading, isError, error } = useExternalWeatherContext(siteId);

  const banner =
    data?.banner ||
    'External weather is stored as CONTEXT ONLY. It is never used for expected-production or loss math, and is never converted to plane-of-array irradiance or cell temperature.';

  return (
    <Paper sx={{ p: 2, mb: 2 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
        <CloudOutlinedIcon fontSize="small" />
        <Typography variant="h6">External Weather (Context)</Typography>
      </Box>

      <Alert severity="info" icon={<InfoOutlinedIcon fontSize="inherit" />} sx={{ mb: 2 }}>
        {banner}
      </Alert>

      {isLoading && (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 1 }}>
          <CircularProgress size={18} />
          <Typography variant="body2" color="text.secondary">
            Loading external weather context…
          </Typography>
        </Box>
      )}

      {isError && (
        <Alert severity="error">
          {(error as Error & { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
            (error as Error)?.message ||
            'Failed to load external weather context.'}
        </Alert>
      )}

      {!isLoading && !isError && data && data.source_count === 0 && (
        <Typography variant="body2" color="text.secondary">
          No external weather has been imported for this project yet.
        </Typography>
      )}

      {!isLoading && !isError && data && data.source_count > 0 && (
        <Box>
          <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 1.5 }}>
            <Chip size="small" label={`${data.source_count} source(s)`} />
            <Chip size="small" label={`${fmtCount(data.total_observation_count)} observation(s)`} variant="outlined" />
            <Chip size="small" color="default" variant="outlined" label="Not expected-eligible" />
          </Box>

          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Source</TableCell>
                <TableCell align="right">Observations</TableCell>
                <TableCell>Coverage</TableCell>
                <TableCell>Metrics</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.sources.map(source => (
                <SourceRow key={source.weather_source_id} source={source} />
              ))}
            </TableBody>
          </Table>

          {data.last_pull && (
            <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1.5 }}>
              Last import: {data.last_pull.pull_status || 'unknown'} · {fmtCount(data.last_pull.row_count)} row(s) ·{' '}
              {fmtInstant(data.last_pull.created_at)}
            </Typography>
          )}
        </Box>
      )}
    </Paper>
  );
};

export default ExternalWeatherContextPanel;
