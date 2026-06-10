import React, { useEffect, useMemo, useState } from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import FormControlLabel from '@mui/material/FormControlLabel';
import Radio from '@mui/material/Radio';
import RadioGroup from '@mui/material/RadioGroup';
import TextField from '@mui/material/TextField';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';

import type { BackfillPreset, BackfillReadingsPayload } from '../../../../../../types/telemetryV2';

const MAX_DAYS = 30;
const DAY_MS = 24 * 60 * 60 * 1000;

type Mode = 'preset' | 'custom';

interface BackfillDialogProps {
  open: boolean;
  onClose: () => void;
  onConfirm: (payload: BackfillReadingsPayload) => void;
  /** True while the backfill request is in flight; locks the form + buttons. */
  isPending: boolean;
}

/** A date-only (yyyy-mm-dd) value interpreted as midnight UTC. */
const toUtcMidnightIso = (yyyyMmDd: string): string => new Date(`${yyyyMmDd}T00:00:00Z`).toISOString();

/**
 * Confirmation dialog for a bounded historical backfill. Offers 7d/30d presets
 * or a custom date range, enforces the 30-day cap client-side (the server also
 * enforces it), and warns that the run uses provider API calls and can take
 * several minutes. The dialog itself is the confirmation step — submitting it
 * starts the run.
 */
export const BackfillDialog: React.FC<BackfillDialogProps> = ({ open, onClose, onConfirm, isPending }) => {
  const [mode, setMode] = useState<Mode>('preset');
  const [preset, setPreset] = useState<BackfillPreset>('7d');
  const [startDate, setStartDate] = useState('');
  const [endDate, setEndDate] = useState('');

  const todayStr = useMemo(() => new Date().toISOString().slice(0, 10), []);

  // Reset to defaults whenever the dialog is reopened so a prior aborted attempt
  // never leaves stale dates behind.
  useEffect(() => {
    if (open) {
      setMode('preset');
      setPreset('7d');
      setStartDate('');
      setEndDate('');
    }
  }, [open]);

  const customError = useMemo<string | null>(() => {
    if (mode !== 'custom') return null;
    if (!startDate || !endDate) return 'Choose both a start and end date.';
    const start = new Date(`${startDate}T00:00:00Z`).getTime();
    const end = new Date(`${endDate}T00:00:00Z`).getTime();
    if (!Number.isFinite(start) || !Number.isFinite(end)) return 'Enter valid dates.';
    if (end <= start) return 'The end date must be after the start date.';
    if (end - start > MAX_DAYS * DAY_MS) return `The window cannot exceed ${MAX_DAYS} days.`;
    return null;
  }, [mode, startDate, endDate]);

  const canSubmit = !isPending && (mode === 'preset' || customError === null);

  const handleConfirm = () => {
    if (!canSubmit) return;
    if (mode === 'preset') {
      onConfirm({ preset });
      return;
    }
    onConfirm({
      window_start: toUtcMidnightIso(startDate),
      window_end: toUtcMidnightIso(endDate)
    });
  };

  return (
    <Dialog open={open} onClose={isPending ? undefined : onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Historical catch-up</DialogTitle>
      <DialogContent>
        <Alert severity="warning" sx={{ mb: 2 }}>
          Historical catch-up pulls telemetry from your provider in 24-hour chunks and can take several minutes. It uses
          provider API calls and may hit provider rate limits. Existing readings are never overwritten — the backfill
          only adds missing data and does not change the live refresh schedule.
        </Alert>

        <RadioGroup value={mode} onChange={e => setMode(e.target.value as Mode)}>
          <FormControlLabel value="preset" control={<Radio />} label="Preset window" disabled={isPending} />
          {mode === 'preset' && (
            <Box sx={{ pl: 4, mb: 1 }}>
              <ToggleButtonGroup
                exclusive
                size="small"
                value={preset}
                onChange={(_, value) => value && setPreset(value as BackfillPreset)}
                disabled={isPending}
              >
                <ToggleButton value="7d">Last 7 days</ToggleButton>
                <ToggleButton value="30d">Last 30 days</ToggleButton>
              </ToggleButtonGroup>
            </Box>
          )}

          <FormControlLabel
            value="custom"
            control={<Radio />}
            label="Custom date range (max 30 days)"
            disabled={isPending}
          />
          {mode === 'custom' && (
            <Box sx={{ pl: 4, display: 'flex', gap: 2, flexWrap: 'wrap' }}>
              <TextField
                type="date"
                label="Start (UTC)"
                size="small"
                InputLabelProps={{ shrink: true }}
                inputProps={{ max: todayStr }}
                value={startDate}
                onChange={e => setStartDate(e.target.value)}
                disabled={isPending}
              />
              <TextField
                type="date"
                label="End (UTC)"
                size="small"
                InputLabelProps={{ shrink: true }}
                inputProps={{ max: todayStr }}
                value={endDate}
                onChange={e => setEndDate(e.target.value)}
                disabled={isPending}
              />
            </Box>
          )}
        </RadioGroup>

        {mode === 'custom' && customError && (
          <Alert severity="error" sx={{ mt: 1 }}>
            {customError}
          </Alert>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={isPending}>
          Cancel
        </Button>
        <Button
          variant="contained"
          onClick={handleConfirm}
          disabled={!canSubmit}
          startIcon={isPending ? <CircularProgress size={16} color="inherit" /> : undefined}
        >
          {isPending ? 'Running…' : 'Start catch-up'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default BackfillDialog;
