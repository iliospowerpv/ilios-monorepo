import React, { useState } from 'react';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Tooltip from '@mui/material/Tooltip';
import Snackbar from '@mui/material/Snackbar';
import Alert from '@mui/material/Alert';
import type { AlertColor } from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import RefreshIcon from '@mui/icons-material/Refresh';

import { useRefreshSiteReadings } from '../../../../../../hooks/telemetryV2';
import type { RefreshReadingsResponse } from '../../../../../../types/telemetryV2';

interface RefreshTelemetryButtonProps {
  siteId: number;
  disabled?: boolean;
  /**
   * When set, the button is disabled and this text is shown as the tooltip,
   * explaining why a refresh is not currently possible (e.g. the project is not
   * mapped to a telemetry site, or its credentials are not yet verified).
   */
  disabledReason?: string;
  onRefreshed?: (result: RefreshReadingsResponse) => void;
}

interface Feedback {
  severity: AlertColor;
  message: string;
}

const formatWhen = (iso: string | null): string => {
  if (!iso) return '';
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? '' : date.toLocaleString();
};

const summarizeResult = (result: RefreshReadingsResponse): Feedback => {
  if (result.status === 'succeeded') {
    return {
      severity: 'success',
      message: `Telemetry refreshed — ${result.readings_written} reading(s) written from ${result.targets_with_data} of ${result.targets_attempted} device metric(s).`
    };
  }

  if (result.status === 'partial') {
    const rateNote = result.rate_limited ? ' (provider rate limit reached)' : '';
    return {
      severity: 'warning',
      message: `Partial refresh — ${result.readings_written} reading(s) written; ${result.targets_failed} device metric(s) failed${rateNote}. Existing data was left untouched.`
    };
  }

  return {
    severity: 'error',
    message: result.error || 'Telemetry refresh failed. No data was changed.'
  };
};

/**
 * Reusable manual "Refresh Telemetry" control for a single mapped project/site.
 * Surfaces progress, success/partial/failure feedback, and the last-refreshed
 * time. The underlying mutation invalidates the site's readiness + health panels
 * on success, and the endpoint never wipes existing data on failure.
 */
export const RefreshTelemetryButton: React.FC<RefreshTelemetryButtonProps> = ({
  siteId,
  disabled,
  disabledReason,
  onRefreshed
}) => {
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<string | null>(null);

  const refresh = useRefreshSiteReadings(siteId, {
    onSuccess: result => {
      setFeedback(summarizeResult(result));
      setLastRefreshedAt(result.ended_at || new Date().toISOString());
      onRefreshed?.(result);
    },
    onError: (err: unknown) => {
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string };
      const message = axiosErr?.response?.data?.detail || axiosErr?.message || 'Telemetry refresh failed.';
      setFeedback({ severity: 'error', message });
    }
  });

  const isPending = refresh.isPending;
  const isBlocked = Boolean(disabledReason);
  const tooltipTitle =
    disabledReason || 'Pull the latest telemetry for every device on this project (most recent 24 hours).';

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 0.5 }}>
      <Tooltip title={tooltipTitle}>
        <span>
          <Button
            variant="outlined"
            color="primary"
            startIcon={isPending ? <CircularProgress size={16} color="inherit" /> : <RefreshIcon />}
            onClick={() => refresh.mutate({})}
            disabled={disabled || isBlocked || isPending}
          >
            {isPending ? 'Refreshing…' : 'Refresh Telemetry'}
          </Button>
        </span>
      </Tooltip>
      {lastRefreshedAt && !isPending && (
        <Typography variant="caption" color="text.secondary">
          Last refreshed: {formatWhen(lastRefreshedAt)}
        </Typography>
      )}
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
    </Box>
  );
};

export default RefreshTelemetryButton;
