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
import { formatCooldown, parseRetryAfterSeconds } from '../../../../../../hooks/useTelemetryCooldown';
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
  /** True while the shared per-project manual cooldown is still counting down. */
  isCoolingDown?: boolean;
  /** Whole seconds left on that cooldown (drives the disabled-state countdown). */
  cooldownSecondsRemaining?: number;
  /**
   * Called with the cooldown length (seconds) whenever the backend reports one —
   * after a successful refresh (response `cooldown_seconds`) or a 429 rejection
   * (`Retry-After`). Lets the parent share one cooldown across Refresh + Catch-up.
   */
  onCooldown?: (seconds: number) => void;
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
  onRefreshed,
  isCoolingDown = false,
  cooldownSecondsRemaining = 0,
  onCooldown
}) => {
  const [feedback, setFeedback] = useState<Feedback | null>(null);
  const [lastRefreshedAt, setLastRefreshedAt] = useState<string | null>(null);

  const refresh = useRefreshSiteReadings(siteId, {
    onSuccess: result => {
      setFeedback(summarizeResult(result));
      setLastRefreshedAt(result.ended_at || new Date().toISOString());
      onCooldown?.(result.cooldown_seconds);
      onRefreshed?.(result);
    },
    onError: (err: unknown) => {
      // A 429 means the shared per-project cooldown is still active; surface it
      // as a soft warning and arm the countdown rather than a hard error.
      const retryAfter = parseRetryAfterSeconds(err);
      if (retryAfter !== null) {
        onCooldown?.(retryAfter);
        setFeedback({
          severity: 'warning',
          message: `Telemetry was refreshed recently. Try again in ${formatCooldown(retryAfter)}.`
        });
        return;
      }
      const axiosErr = err as { response?: { data?: { detail?: string } }; message?: string };
      const message = axiosErr?.response?.data?.detail || axiosErr?.message || 'Telemetry refresh failed.';
      setFeedback({ severity: 'error', message });
    }
  });

  const isPending = refresh.isPending;
  const isBlocked = Boolean(disabledReason);
  let tooltipTitle: string;
  if (disabledReason) {
    tooltipTitle = disabledReason;
  } else if (isCoolingDown) {
    tooltipTitle = `Telemetry was refreshed recently. Available again in ${formatCooldown(cooldownSecondsRemaining)}.`;
  } else {
    tooltipTitle = 'Pull the latest telemetry for every device on this project (most recent 24 hours).';
  }

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 0.5 }}>
      <Tooltip title={tooltipTitle}>
        <span>
          <Button
            variant="outlined"
            color="primary"
            startIcon={isPending ? <CircularProgress size={16} color="inherit" /> : <RefreshIcon />}
            onClick={() => refresh.mutate({})}
            disabled={disabled || isBlocked || isPending || isCoolingDown}
          >
            {isPending
              ? 'Refreshing…'
              : isCoolingDown
                ? `Available in ${formatCooldown(cooldownSecondsRemaining)}`
                : 'Refresh Telemetry'}
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
