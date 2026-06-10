import React, { useEffect, useState } from 'react';
import Alert from '@mui/material/Alert';
import type { AlertColor } from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Divider from '@mui/material/Divider';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import type { SelectChangeEvent } from '@mui/material/Select';
import Snackbar from '@mui/material/Snackbar';
import Switch from '@mui/material/Switch';
import Tooltip from '@mui/material/Tooltip';
import Typography from '@mui/material/Typography';
import HistoryIcon from '@mui/icons-material/History';
import ScheduleIcon from '@mui/icons-material/Schedule';

import { useBackfillSiteReadings, useSiteScheduler, useUpdateSiteScheduler } from '../../../../../../hooks/telemetryV2';
import type {
  BackfillReadingsPayload,
  BackfillReadingsResponse,
  TelemetryCadence
} from '../../../../../../types/telemetryV2';
import { BackfillDialog } from './BackfillDialog';
import { formatUtc, isLockActive } from './telemetryTime';

interface SchedulerAdminCardProps {
  siteId: number;
}

interface Feedback {
  severity: AlertColor;
  message: string;
}

const CADENCE_OPTIONS: { value: TelemetryCadence; label: string }[] = [
  { value: 'PT15M', label: 'Every 15 minutes' },
  { value: 'PT30M', label: 'Every 30 minutes' },
  { value: 'PT1H', label: 'Every hour' },
  { value: 'PT6H', label: 'Every 6 hours' },
  { value: 'PT24H', label: 'Every 24 hours' }
];

const cadenceLabel = (cadence: string): string => CADENCE_OPTIONS.find(o => o.value === cadence)?.label ?? cadence;

const errorDetail = (err: unknown, fallback: string): string => {
  const e = err as { response?: { data?: { detail?: unknown } }; message?: string };
  const detail = e?.response?.data?.detail;
  if (typeof detail === 'string') return detail;
  return e?.message || fallback;
};

const errorStatus = (err: unknown): number | undefined => (err as { response?: { status?: number } })?.response?.status;

const humanizeStatus = (status: string): string => {
  const map: Record<string, string> = {
    succeeded: 'Succeeded',
    partial: 'Partial',
    failed: 'Failed',
    running: 'Running',
    queued: 'Queued',
    bf_succeeded: 'Backfill: succeeded',
    bf_partial: 'Backfill: partial',
    bf_failed: 'Backfill: failed'
  };
  return map[status] ?? status;
};

const statusColor = (status: string): 'success' | 'warning' | 'error' | 'default' => {
  if (status.includes('succeeded')) return 'success';
  if (status.includes('partial')) return 'warning';
  if (status.includes('failed')) return 'error';
  return 'default';
};

const summarizeBackfill = (r: BackfillReadingsResponse): Feedback => {
  if (r.status === 'succeeded') {
    return {
      severity: 'success',
      message: `Historical catch-up complete — ${r.readings_written} reading(s) written across ${r.chunks_succeeded} day-chunk(s).`
    };
  }
  if (r.status === 'partial') {
    return {
      severity: 'warning',
      message: `Partial catch-up — ${r.readings_written} reading(s) written; ${r.chunks_failed} chunk(s) failed and processing stopped. Existing data was left untouched.`
    };
  }
  return { severity: 'error', message: r.error || 'Historical catch-up failed. No data was changed.' };
};

const StatusRow: React.FC<{ label: string; children: React.ReactNode }> = ({ label, children }) => (
  <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 2, py: 0.5 }}>
    <Typography variant="body2" color="text.secondary">
      {label}
    </Typography>
    <Box sx={{ textAlign: 'right' }}>{children}</Box>
  </Box>
);

/**
 * Admin-only controls for one mapped project/site's automatic telemetry refresh
 * (scheduler) plus bounded historical catch-up (backfill). Rendered only when
 * the caller has confirmed telemetry-admin permission and the site is telemetry-
 * configured; the backend re-enforces both on every call. No credentials or
 * provider tokens are read or shown here.
 */
export const SchedulerAdminCard: React.FC<SchedulerAdminCardProps> = ({ siteId }) => {
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [backfillOpen, setBackfillOpen] = useState(false);

  const scheduler = useSiteScheduler(siteId);
  const update = useUpdateSiteScheduler(siteId, {
    onError: err =>
      setFeedback({ severity: 'error', message: errorDetail(err, 'Could not update the telemetry schedule.') })
  });
  const backfill = useBackfillSiteReadings(siteId);

  const state = scheduler.data;
  const isLocked = isLockActive(state?.locked_until);
  const isBusy = isLocked || backfill.isPending;
  const isMapped = !!state?.provider_account_id;

  // While a run holds the per-site lease lock (a scheduled run, or our own
  // backfill), poll so the "running" indicator and lock clear on their own.
  const { refetch } = scheduler;
  useEffect(() => {
    if (!isBusy) return undefined;
    const id = window.setInterval(() => {
      void refetch();
    }, 10000);
    return () => window.clearInterval(id);
  }, [isBusy, refetch]);

  const handleToggle = (_e: React.ChangeEvent<HTMLInputElement>, checked: boolean) => {
    update.mutate(
      { enabled: checked },
      {
        onSuccess: data =>
          setFeedback({
            severity: 'success',
            message: data.enabled
              ? `Automatic refresh enabled — running ${cadenceLabel(data.cadence).toLowerCase()}.`
              : 'Automatic refresh disabled.'
          })
      }
    );
  };

  const handleCadence = (e: SelectChangeEvent) => {
    const value = e.target.value as TelemetryCadence;
    update.mutate(
      { cadence: value },
      {
        onSuccess: data =>
          setFeedback({
            severity: 'success',
            message: `Refresh cadence set to ${cadenceLabel(data.cadence).toLowerCase()}.`
          })
      }
    );
  };

  const handleBackfillConfirm = (payload: BackfillReadingsPayload) => {
    backfill.mutate(payload, {
      onSuccess: res => setFeedback(summarizeBackfill(res)),
      onError: err => {
        if (errorStatus(err) === 409) {
          setFeedback({ severity: 'warning', message: 'Telemetry sync is already running for this site.' });
        } else {
          setFeedback({
            severity: 'error',
            message: errorDetail(err, 'Historical catch-up failed. No data was changed.')
          });
        }
      },
      onSettled: () => setBackfillOpen(false)
    });
  };

  return (
    <Card sx={{ mb: 2 }}>
      <CardContent>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5 }}>
          <ScheduleIcon color="primary" />
          <Typography variant="h6">Automatic Refresh &amp; Catch-up</Typography>
          <Chip label="Admin" size="small" variant="outlined" sx={{ ml: 1 }} />
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          Control scheduled telemetry pulls for this project and run a bounded historical catch-up. Enabling records the
          schedule; the platform runs scheduled pulls in the background when telemetry automation is active.
        </Typography>

        {scheduler.isLoading && (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
            <CircularProgress size={28} />
          </Box>
        )}

        {scheduler.isError && (
          <Alert severity="error">{errorDetail(scheduler.error, 'Could not load the scheduler state.')}</Alert>
        )}

        {state && !scheduler.isLoading && (
          <>
            {!isMapped && (
              <Alert severity="info" sx={{ mb: 2 }}>
                Map this project to a telemetry provider account before configuring automatic refresh.
              </Alert>
            )}

            <StatusRow label="Automatic refresh">
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <Chip
                  size="small"
                  label={state.enabled ? 'Enabled' : 'Disabled'}
                  color={state.enabled ? 'success' : 'default'}
                  variant={state.enabled ? 'filled' : 'outlined'}
                />
                <Switch
                  checked={state.enabled}
                  onChange={handleToggle}
                  disabled={update.isPending || !isMapped}
                  inputProps={{ 'aria-label': 'Enable automatic telemetry refresh' }}
                />
              </Box>
            </StatusRow>

            <StatusRow label="Refresh cadence">
              <Select
                size="small"
                value={state.cadence}
                onChange={handleCadence}
                disabled={update.isPending || !isMapped}
                sx={{ minWidth: 180 }}
              >
                {CADENCE_OPTIONS.map(o => (
                  <MenuItem key={o.value} value={o.value}>
                    {o.label}
                  </MenuItem>
                ))}
              </Select>
            </StatusRow>

            <Divider sx={{ my: 1.5 }} />

            <StatusRow label="Currently running">
              {isLocked ? (
                <Chip
                  size="small"
                  color="info"
                  icon={<CircularProgress size={12} color="inherit" />}
                  label={`Running (until ${formatUtc(state.locked_until)})`}
                />
              ) : (
                <Typography variant="body2">No</Typography>
              )}
            </StatusRow>

            <StatusRow label="Last status">
              {state.last_status ? (
                <Chip size="small" label={humanizeStatus(state.last_status)} color={statusColor(state.last_status)} />
              ) : (
                <Typography variant="body2">—</Typography>
              )}
            </StatusRow>

            <StatusRow label="Last successful pull">
              <Typography variant="body2">{formatUtc(state.last_successful_pull_at)}</Typography>
            </StatusRow>

            <StatusRow label="Last attempted">
              <Typography variant="body2">{formatUtc(state.last_run_at)}</Typography>
            </StatusRow>

            <StatusRow label="Next due">
              <Typography variant="body2">{state.enabled ? formatUtc(state.next_due_at, '—') : 'Paused'}</Typography>
            </StatusRow>

            {state.last_error && (
              <Alert severity="error" sx={{ mt: 1 }}>
                {state.last_error}
              </Alert>
            )}

            <Divider sx={{ my: 1.5 }} />

            <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 2 }}>
              <Typography variant="body2" color="text.secondary">
                Pull missing historical readings (up to 30 days) without changing the live schedule.
              </Typography>
              <Tooltip
                title={
                  !isMapped
                    ? 'Map this project to a telemetry provider first.'
                    : isBusy
                      ? 'A telemetry sync is already in progress for this site.'
                      : 'Run a bounded historical catch-up.'
                }
              >
                <span>
                  <Button
                    variant="outlined"
                    startIcon={<HistoryIcon />}
                    onClick={() => setBackfillOpen(true)}
                    disabled={isBusy || !isMapped}
                  >
                    Historical catch-up
                  </Button>
                </span>
              </Tooltip>
            </Box>
          </>
        )}
      </CardContent>

      <BackfillDialog
        open={backfillOpen}
        onClose={() => setBackfillOpen(false)}
        onConfirm={handleBackfillConfirm}
        isPending={backfill.isPending}
      />

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
    </Card>
  );
};

export default SchedulerAdminCard;
