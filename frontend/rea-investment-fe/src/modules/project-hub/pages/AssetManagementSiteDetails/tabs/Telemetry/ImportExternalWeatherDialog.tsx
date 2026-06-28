import React from 'react';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import Typography from '@mui/material/Typography';
import Divider from '@mui/material/Divider';

import {
  useWeatherProviders,
  useWeatherProviderAccounts,
  useProviderImport
} from '../../../../../../hooks/weatherProvider';
import type {
  ProviderImportPreviewResponse,
  ProviderImportRequest,
  ProviderImportResponse
} from '../../../../../../types/weather';

/**
 * D4 — site-scoped external-weather import dialog (preview → run).
 *
 * Every external pull is CONTEXT ONLY: the dialog shows that verdict
 * prominently and never offers an "expected-eligible" path. Preview is a pure
 * dry-run (no writes); run executes a bounded, gap-only, idempotent pull. The
 * window is sent as naive-UTC ISO to match the storage convention.
 */

const WINDOW_OPTIONS: { label: string; days: number }[] = [
  { label: 'Last 24 hours', days: 1 },
  { label: 'Last 7 days', days: 7 },
  { label: 'Last 30 days', days: 30 }
];

// toISOString() yields e.g. 2026-06-28T12:34:56.789Z; strip the fractional
// seconds + Z to produce the naive-UTC string the backend stores.
const toNaiveUtcIso = (d: Date): string => d.toISOString().replace(/\.\d+Z$/, '');

const errorDetail = (err: unknown, fallback: string): string => {
  const e = err as Error & { response?: { data?: { detail?: string } } };
  return e?.response?.data?.detail || e?.message || fallback;
};

interface ImportExternalWeatherDialogProps {
  open: boolean;
  onClose: () => void;
  siteId: number;
  companyId: number;
}

export const ImportExternalWeatherDialog: React.FC<ImportExternalWeatherDialogProps> = ({
  open,
  onClose,
  siteId,
  companyId
}) => {
  const { data: providerData } = useWeatherProviders({ includeDisabled: false }, { enabled: open });
  const { data: accountData } = useWeatherProviderAccounts(companyId, {}, { enabled: open });
  const { preview, run } = useProviderImport(siteId);

  const [providerKey, setProviderKey] = React.useState('');
  const [accountId, setAccountId] = React.useState<number | ''>('');
  const [windowDays, setWindowDays] = React.useState(1);
  const [previewResult, setPreviewResult] = React.useState<ProviderImportPreviewResponse | null>(null);
  const [runResult, setRunResult] = React.useState<ProviderImportResponse | null>(null);
  const [errorMsg, setErrorMsg] = React.useState<string | null>(null);

  const providers = React.useMemo(() => providerData?.items ?? [], [providerData]);
  const selectedProvider = React.useMemo(
    () => providers.find(p => p.provider_key === providerKey) ?? null,
    [providers, providerKey]
  );
  const requiresCredentials = selectedProvider?.requires_credentials ?? false;

  // Only accounts for the selected provider that are usable for a pull.
  const eligibleAccounts = React.useMemo(
    () =>
      (accountData?.items ?? []).filter(
        a => a.provider_key === providerKey && a.status === 'active' && a.has_stored_credentials
      ),
    [accountData, providerKey]
  );

  // Reset every piece of local state when the dialog closes.
  React.useEffect(() => {
    if (!open) {
      setProviderKey('');
      setAccountId('');
      setWindowDays(1);
      setPreviewResult(null);
      setRunResult(null);
      setErrorMsg(null);
    }
  }, [open]);

  // Changing provider/window invalidates any prior preview or run summary.
  React.useEffect(() => {
    setPreviewResult(null);
    setRunResult(null);
    setErrorMsg(null);
    setAccountId('');
  }, [providerKey]);

  React.useEffect(() => {
    setPreviewResult(null);
    setRunResult(null);
  }, [windowDays, accountId]);

  const buildRequest = (): ProviderImportRequest => {
    const end = new Date();
    const start = new Date(end.getTime() - windowDays * 24 * 60 * 60 * 1000);
    return {
      provider_key: providerKey,
      account_id: requiresCredentials && accountId !== '' ? accountId : null,
      window_start: toNaiveUtcIso(start),
      window_end: toNaiveUtcIso(end),
      granularity: 'hourly'
    };
  };

  const canSubmit = Boolean(providerKey) && (!requiresCredentials || accountId !== '');

  const handlePreview = () => {
    if (!canSubmit) return;
    setErrorMsg(null);
    setRunResult(null);
    preview.mutate(buildRequest(), {
      onSuccess: setPreviewResult,
      onError: err => setErrorMsg(errorDetail(err, 'Preview failed.'))
    });
  };

  const handleRun = () => {
    if (!canSubmit) return;
    setErrorMsg(null);
    run.mutate(buildRequest(), {
      onSuccess: setRunResult,
      onError: err => setErrorMsg(errorDetail(err, 'Import failed.'))
    });
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Import External Weather</DialogTitle>
      <DialogContent>
        <Alert severity="info" sx={{ mt: 1, mb: 2 }}>
          <AlertTitle>Context only — not expected-eligible</AlertTitle>
          Imported weather is stored for context and provenance. It is never used for expected-production or loss math,
          and is never converted to plane-of-array irradiance or cell temperature.
        </Alert>

        {providers.length === 0 ? (
          <Alert severity="warning">
            No enabled weather providers are available. An administrator must enable a provider in the company weather
            settings first.
          </Alert>
        ) : (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <FormControl fullWidth>
              <InputLabel id="weather-import-provider">Provider</InputLabel>
              <Select
                labelId="weather-import-provider"
                label="Provider"
                value={providerKey}
                onChange={e => setProviderKey(e.target.value as string)}
              >
                {providers.map(p => (
                  <MenuItem key={p.provider_key} value={p.provider_key}>
                    {p.display_name}
                    {p.requires_credentials ? '' : ' (keyless)'}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {requiresCredentials && (
              <FormControl fullWidth>
                <InputLabel id="weather-import-account">Account</InputLabel>
                <Select
                  labelId="weather-import-account"
                  label="Account"
                  value={accountId === '' ? '' : String(accountId)}
                  onChange={e => setAccountId(e.target.value === '' ? '' : Number(e.target.value))}
                >
                  {eligibleAccounts.length === 0 ? (
                    <MenuItem value="" disabled>
                      No active, credentialed accounts for this provider
                    </MenuItem>
                  ) : (
                    eligibleAccounts.map(a => (
                      <MenuItem key={a.id} value={String(a.id)}>
                        {a.display_name}
                      </MenuItem>
                    ))
                  )}
                </Select>
              </FormControl>
            )}

            <FormControl fullWidth>
              <InputLabel id="weather-import-window">Window</InputLabel>
              <Select
                labelId="weather-import-window"
                label="Window"
                value={String(windowDays)}
                onChange={e => setWindowDays(Number(e.target.value))}
              >
                {WINDOW_OPTIONS.map(opt => (
                  <MenuItem key={opt.days} value={String(opt.days)}>
                    {opt.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            {previewResult && (
              <Box>
                <Divider sx={{ mb: 1.5 }} />
                <Alert severity="info" sx={{ mb: 1.5 }}>
                  <AlertTitle>Preview — {previewResult.verdict}</AlertTitle>
                  <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mb: 1 }}>
                    <Chip size="small" label="Context only" />
                    <Chip size="small" variant="outlined" label={`Plane: ${previewResult.native_plane}`} />
                    <Chip size="small" variant="outlined" label={`Temp: ${previewResult.native_temperature_type}`} />
                    {previewResult.is_modeled && <Chip size="small" variant="outlined" label="Modeled" />}
                  </Box>
                  <Typography variant="body2">
                    {previewResult.chunks_to_pull} chunk(s) to pull · {previewResult.chunks_already_covered} already
                    covered · ~{previewResult.estimated_provider_calls} provider call(s)
                  </Typography>
                  {previewResult.existing_observation_count > 0 && (
                    <Typography variant="body2" color="text.secondary">
                      {previewResult.existing_observation_count.toLocaleString()} existing observation(s) in window
                    </Typography>
                  )}
                </Alert>
                {previewResult.warnings.length > 0 && (
                  <Alert severity="warning" sx={{ mb: 1 }}>
                    {previewResult.warnings.map((w, i) => (
                      <div key={i}>{w}</div>
                    ))}
                  </Alert>
                )}
              </Box>
            )}

            {runResult && (
              <Box>
                <Divider sx={{ mb: 1.5 }} />
                <Alert severity={runResult.errors.length > 0 ? 'warning' : 'success'}>
                  <AlertTitle>Import {runResult.pull_status || runResult.status}</AlertTitle>
                  <Typography variant="body2">
                    {runResult.rows_inserted.toLocaleString()} inserted · {runResult.rows_duplicate.toLocaleString()}{' '}
                    duplicate · {runResult.rows_pulled.toLocaleString()} pulled
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    Stored as context ({runResult.stored_not_usable_rows.toLocaleString()} not expected-usable). These
                    readings never feed expected math.
                  </Typography>
                  {runResult.warnings.map((w, i) => (
                    <div key={`w${i}`}>{w}</div>
                  ))}
                  {runResult.errors.map((e, i) => (
                    <div key={`e${i}`}>{e}</div>
                  ))}
                </Alert>
              </Box>
            )}

            {errorMsg && <Alert severity="error">{errorMsg}</Alert>}
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Close</Button>
        <Button
          onClick={handlePreview}
          disabled={!canSubmit || preview.isPending || run.isPending}
          startIcon={preview.isPending ? <CircularProgress size={16} color="inherit" /> : null}
        >
          {preview.isPending ? 'Previewing…' : 'Preview'}
        </Button>
        <Button
          variant="contained"
          onClick={handleRun}
          disabled={!canSubmit || !previewResult || run.isPending || preview.isPending}
          startIcon={run.isPending ? <CircularProgress size={16} color="inherit" /> : null}
        >
          {run.isPending ? 'Importing…' : 'Run Import'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default ImportExternalWeatherDialog;
