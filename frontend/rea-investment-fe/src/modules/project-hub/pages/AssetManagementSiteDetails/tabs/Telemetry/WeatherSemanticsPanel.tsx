import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import type { ChipProps } from '@mui/material/Chip';
import Alert from '@mui/material/Alert';
import Collapse from '@mui/material/Collapse';
import Button from '@mui/material/Button';
import Tooltip from '@mui/material/Tooltip';
import Snackbar from '@mui/material/Snackbar';
import type { AlertColor } from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import TextField from '@mui/material/TextField';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ThermostatIcon from '@mui/icons-material/Thermostat';

import { ApiClient } from '../../../../../../api';
import type {
  WeatherSemanticsReconciliationResponse,
  WeatherSemanticsReconciliationRow
} from '../../../../../../types/weather';
import { useTelemetryAdminPermission } from '../../../../../../hooks/useTelemetryAdminPermission';
import { blockingMeta } from '../../../../../../utils/telemetry/deviceDiagnostics';
import { WeatherDeclareDialog } from './WeatherDeclareDialog';
import { WeatherDeclarationHistoryDialog } from './WeatherDeclarationHistoryDialog';

interface Feedback {
  severity: AlertColor;
  message: string;
}

const extractError = (err: unknown, fallback: string): string => {
  const e = err as { response?: { data?: { detail?: unknown } }; message?: string };
  const detail = e?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  if (detail && typeof detail === 'object') return JSON.stringify(detail);
  return e?.message || fallback;
};

interface SummaryStripProps {
  data: WeatherSemanticsReconciliationResponse;
}

const SummaryStrip: React.FC<SummaryStripProps> = ({ data }) => {
  const chips: Array<{ label: string; color?: ChipProps['color'] }> = [
    { label: `${data.total_weather_capable_devices} weather-capable device(s)` },
    { label: `${data.eligible_count} expected-eligible`, color: data.eligible_count > 0 ? 'success' : 'default' }
  ];
  if (data.needs_re_review_count) {
    chips.push({ label: `${data.needs_re_review_count} need re-review`, color: 'warning' });
  }
  chips.push({
    label: data.has_weather_source ? 'Weather source present' : 'No weather source',
    color: data.has_weather_source ? 'info' : 'default'
  });
  chips.push({
    label: data.has_active_weather_profile ? 'Active weather profile' : 'No active profile',
    color: data.has_active_weather_profile ? 'info' : 'default'
  });

  return (
    <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 1 }}>
      {chips.map(c => (
        <Chip key={c.label} size="small" label={c.label} color={c.color ?? 'default'} variant="outlined" />
      ))}
    </Box>
  );
};

const semanticsLabel = (row: WeatherSemanticsReconciliationRow): string => {
  const parts: string[] = [];
  if (row.irradiance_plane && row.irradiance_plane !== 'unknown') parts.push(`plane: ${row.irradiance_plane}`);
  if (row.temperature_type && row.temperature_type !== 'unknown') parts.push(`temp: ${row.temperature_type}`);
  if (row.calibration_status && row.calibration_status !== 'unknown') parts.push(`cal: ${row.calibration_status}`);
  return parts.length ? parts.join(', ') : 'Undeclared (unknown)';
};

interface WeatherSemanticsPanelProps {
  siteId: number;
}

/**
 * Read-only governed weather-semantics reconciliation panel (WS.4).
 *
 * Discloses each weather-source-capable device's position in the 8-state
 * governance taxonomy plus site-level counts, and (for telemetry admins) exposes
 * the additive declaration actions: declare/activate semantics, flag a stale
 * active declaration for re-review, and re-evaluate upstream drift. Nothing here
 * infers or converts semantics, touches the resolver/expected math, or mutates
 * baselines — it only declares what an operator states and reads back what the
 * governance layer recorded.
 */
export const WeatherSemanticsPanel: React.FC<WeatherSemanticsPanelProps> = ({ siteId }) => {
  const queryClient = useQueryClient();
  const isAdmin = useTelemetryAdminPermission();
  const [expanded, setExpanded] = useState(false);
  const [feedback, setFeedback] = useState<Feedback | null>(null);

  const [declareTarget, setDeclareTarget] = useState<{
    deviceId: number;
    deviceName: string | null;
    metric: string | null;
    supersedesMappingId: number | null;
  } | null>(null);
  const [historyTarget, setHistoryTarget] = useState<{ deviceId: number; deviceName: string | null } | null>(null);
  const [reReviewTarget, setReReviewTarget] = useState<{ mappingId: number; deviceName: string | null } | null>(null);
  const [reReviewReason, setReReviewReason] = useState('');

  const { data, isLoading, isError } = useQuery({
    queryKey: ['weather-semantics-reconciliation', siteId],
    queryFn: () => ApiClient.weather.getSemanticsReconciliation(siteId),
    enabled: !!siteId
  });

  const { data: drift } = useQuery({
    queryKey: ['weather-upstream-changes', siteId],
    queryFn: () => ApiClient.weather.previewUpstreamChanges(siteId),
    enabled: !!siteId
  });

  const invalidateAll = () => {
    queryClient.invalidateQueries({ queryKey: ['weather-semantics-reconciliation', siteId] });
    queryClient.invalidateQueries({ queryKey: ['weather-device-mappings', siteId] });
    queryClient.invalidateQueries({ queryKey: ['weather-upstream-changes', siteId] });
    // Broad prefix: refreshes any open per-device history dialog for this site.
    queryClient.invalidateQueries({ queryKey: ['weather-device-history', siteId] });
  };

  const activateMutation = useMutation({
    mutationFn: (mappingId: number) => ApiClient.weather.activateDeviceMapping(siteId, mappingId),
    onSuccess: () => {
      invalidateAll();
      setFeedback({ severity: 'success', message: 'Declaration activated.' });
    },
    onError: err => setFeedback({ severity: 'error', message: extractError(err, 'Failed to activate declaration.') })
  });

  const reReviewMutation = useMutation({
    mutationFn: (vars: { mappingId: number; reason: string }) =>
      ApiClient.weather.flagReReview(siteId, vars.mappingId, { reason: vars.reason }),
    onSuccess: () => {
      invalidateAll();
      setReReviewTarget(null);
      setReReviewReason('');
      setFeedback({ severity: 'success', message: 'Declaration flagged for re-review.' });
    },
    onError: err => setFeedback({ severity: 'error', message: extractError(err, 'Failed to flag for re-review.') })
  });

  const reEvaluateMutation = useMutation({
    mutationFn: () => ApiClient.weather.reEvaluateUpstreamChanges(siteId),
    onSuccess: report => {
      invalidateAll();
      setFeedback({
        severity: report.newly_flagged_count > 0 ? 'warning' : 'success',
        message:
          report.newly_flagged_count > 0
            ? `${report.newly_flagged_count} declaration(s) newly flagged for re-review.`
            : 'No new upstream drift detected.'
      });
    },
    onError: err => setFeedback({ severity: 'error', message: extractError(err, 'Failed to re-evaluate upstream drift.') })
  });

  if (isLoading) {
    return (
      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <CircularProgress size={18} />
          <Typography variant="body2" color="text.secondary">
            Loading weather-semantics reconciliation…
          </Typography>
        </Box>
      </Paper>
    );
  }

  if (isError) {
    return (
      <Paper sx={{ p: 2, mb: 2 }}>
        <Alert severity="error">
          Failed to load weather-semantics reconciliation. You may not have access, or the service is temporarily
          unavailable.
        </Alert>
      </Paper>
    );
  }

  if (!data) {
    return null;
  }

  const driftCount = drift?.would_flag_count ?? 0;

  return (
    <Paper sx={{ p: 2, mb: 2 }}>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 1 }}>
        <Typography variant="h6">
          <ThermostatIcon sx={{ mr: 1, verticalAlign: 'middle' }} fontSize="small" />
          Weather Semantics Governance
        </Typography>
        <Button
          size="small"
          onClick={() => setExpanded(prev => !prev)}
          endIcon={expanded ? <ExpandLessIcon /> : <ExpandMoreIcon />}
        >
          {expanded ? 'Hide devices' : `Show devices (${data.total_weather_capable_devices})`}
        </Button>
      </Box>

      <SummaryStrip data={data} />

      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
        Read-only governance view. Semantics are never guessed or converted — anything undeclared stays
        &quot;unknown&quot;. Declaring a value never alters expected math, the resolver, ingestion, or baselines.
      </Typography>

      {drift && driftCount > 0 && (
        <Alert
          severity="warning"
          sx={{ mb: 1 }}
          action={
            isAdmin ? (
              <Button
                color="inherit"
                size="small"
                onClick={() => reEvaluateMutation.mutate()}
                disabled={reEvaluateMutation.isPending}
              >
                {reEvaluateMutation.isPending ? 'Re-evaluating…' : 'Re-evaluate'}
              </Button>
            ) : undefined
          }
        >
          <Typography variant="body2">
            {driftCount} active declaration(s) have upstream-identity drift since they were declared. Re-evaluate to flag
            them for re-review; this never changes the declared semantics.
          </Typography>
        </Alert>
      )}

      <Collapse in={expanded} timeout="auto" unmountOnExit>
        <TableContainer sx={{ mt: 1 }}>
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Device</TableCell>
                <TableCell>Metric</TableCell>
                <TableCell>State</TableCell>
                <TableCell>Semantics</TableCell>
                <TableCell align="right">Actions</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {data.devices.map(row => {
                const meta = blockingMeta[row.blocking_level as keyof typeof blockingMeta] ?? blockingMeta.informational;
                const isDraft = row.declaration_status === 'draft' && row.mapping_id != null;
                const isActive = row.declaration_status === 'active' && row.mapping_id != null;
                return (
                  <TableRow key={`${row.device_id}-${row.metric ?? ''}`} hover>
                    <TableCell>
                      {row.device_name ?? `Device ${row.device_id}`}
                      {row.device_category && (
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                          {row.device_category}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>{row.metric ?? '—'}</TableCell>
                    <TableCell>
                      <Tooltip title={row.layer1_message ?? row.state_explanation} arrow>
                        <Chip size="small" variant="outlined" label={row.state_label} sx={{ mb: 0.5 }} />
                      </Tooltip>
                      {row.blocking_level !== 'informational' && (
                        <Chip size="small" color={meta.color} variant="outlined" label={meta.label} sx={{ ml: 0.5, mb: 0.5 }} />
                      )}
                      {row.needs_re_review && (
                        <Chip size="small" color="warning" variant="outlined" label="Needs re-review" sx={{ ml: 0.5, mb: 0.5 }} />
                      )}
                      {row.required_action && (
                        <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
                          Next: {row.required_action}
                        </Typography>
                      )}
                    </TableCell>
                    <TableCell>
                      <Typography variant="caption">{semanticsLabel(row)}</Typography>
                      {row.expected_model_eligible && (
                        <Chip size="small" color="success" variant="outlined" label="Expected-eligible" sx={{ ml: 0.5 }} />
                      )}
                    </TableCell>
                    <TableCell align="right">
                      <Box sx={{ display: 'flex', gap: 0.5, justifyContent: 'flex-end', flexWrap: 'wrap' }}>
                        {isAdmin && (
                          <Button
                            size="small"
                            onClick={() =>
                              setDeclareTarget({
                                deviceId: row.device_id,
                                deviceName: row.device_name,
                                metric: row.metric,
                                supersedesMappingId: isActive ? row.mapping_id : null
                              })
                            }
                          >
                            Declare
                          </Button>
                        )}
                        {isAdmin && isDraft && (
                          <Button
                            size="small"
                            color="primary"
                            onClick={() => activateMutation.mutate(row.mapping_id as number)}
                            disabled={activateMutation.isPending}
                          >
                            Activate
                          </Button>
                        )}
                        {isAdmin && isActive && !row.needs_re_review && (
                          <Button
                            size="small"
                            color="warning"
                            onClick={() =>
                              setReReviewTarget({ mappingId: row.mapping_id as number, deviceName: row.device_name })
                            }
                          >
                            Flag re-review
                          </Button>
                        )}
                        <Button
                          size="small"
                          onClick={() => setHistoryTarget({ deviceId: row.device_id, deviceName: row.device_name })}
                        >
                          History
                        </Button>
                      </Box>
                    </TableCell>
                  </TableRow>
                );
              })}
              {data.devices.length === 0 && (
                <TableRow>
                  <TableCell colSpan={5}>
                    <Typography variant="body2" color="text.secondary">
                      No weather-source-capable devices on this project.
                    </Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>
      </Collapse>

      {declareTarget && (
        <WeatherDeclareDialog
          open
          onClose={() => setDeclareTarget(null)}
          siteId={siteId}
          deviceId={declareTarget.deviceId}
          deviceName={declareTarget.deviceName}
          defaultMetric={declareTarget.metric}
          supersedesMappingId={declareTarget.supersedesMappingId}
        />
      )}

      {historyTarget && (
        <WeatherDeclarationHistoryDialog
          open
          onClose={() => setHistoryTarget(null)}
          siteId={siteId}
          deviceId={historyTarget.deviceId}
          deviceName={historyTarget.deviceName}
        />
      )}

      <Dialog open={!!reReviewTarget} onClose={() => setReReviewTarget(null)} maxWidth="sm" fullWidth>
        <DialogTitle>Flag declaration for re-review</DialogTitle>
        <DialogContent dividers>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            This sets a monotonic re-review flag on the active declaration for{' '}
            <strong>{reReviewTarget?.deviceName ?? 'this device'}</strong>. It never clears automatically and never
            changes the declared semantics — it only clears when a new activated declaration supersedes this one.
          </Typography>
          <TextField
            label="Reason"
            value={reReviewReason}
            onChange={e => setReReviewReason(e.target.value)}
            fullWidth
            required
            multiline
            minRows={2}
            size="small"
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setReReviewTarget(null)} disabled={reReviewMutation.isPending}>
            Cancel
          </Button>
          <Button
            variant="contained"
            color="warning"
            disabled={!reReviewReason.trim() || reReviewMutation.isPending}
            onClick={() =>
              reReviewTarget &&
              reReviewMutation.mutate({ mappingId: reReviewTarget.mappingId, reason: reReviewReason.trim() })
            }
          >
            Flag for re-review
          </Button>
        </DialogActions>
      </Dialog>

      {feedback && (
        <Snackbar
          open
          autoHideDuration={8000}
          onClose={() => setFeedback(null)}
          anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
        >
          <Alert severity={feedback.severity} onClose={() => setFeedback(null)} sx={{ maxWidth: 480 }}>
            {feedback.message}
          </Alert>
        </Snackbar>
      )}
    </Paper>
  );
};

export default WeatherSemanticsPanel;
