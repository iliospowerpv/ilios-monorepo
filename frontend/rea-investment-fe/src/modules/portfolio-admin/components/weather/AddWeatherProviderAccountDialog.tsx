import React from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Checkbox from '@mui/material/Checkbox';
import CircularProgress from '@mui/material/CircularProgress';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import FormControl from '@mui/material/FormControl';
import FormControlLabel from '@mui/material/FormControlLabel';
import InputLabel from '@mui/material/InputLabel';
import Link from '@mui/material/Link';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import TextField from '@mui/material/TextField';

import { useWeatherProviders, useWeatherProviderAccountMutations } from '../../../../hooks/weatherProvider';
import { CredentialFieldsForm, resolveCredentialFields } from '../telemetry/v2/CredentialFieldsForm';

/**
 * Company-level "add weather provider account" dialog.
 *
 * Mirrors the telemetry AddProviderAccountDialog but for the context-only
 * weather framework. Differences: the weather account uses `display_name`, the
 * provider list comes from the weather catalog (enabled only), credentials are
 * optional (keyless providers like Open-Meteo need none), and licensing must be
 * acknowledged before saving — there is no separate "licensed provider" concept.
 */
interface AddWeatherProviderAccountDialogProps {
  companyId: number;
  open: boolean;
  onClose: () => void;
  onCreated?: (accountId: number) => void;
}

export const AddWeatherProviderAccountDialog: React.FC<AddWeatherProviderAccountDialogProps> = ({
  companyId,
  open,
  onClose,
  onCreated
}) => {
  const { data: catalog } = useWeatherProviders({ includeDisabled: false }, { enabled: open });
  const { createAccount } = useWeatherProviderAccountMutations(companyId);

  const [providerKey, setProviderKey] = React.useState('');
  const [displayName, setDisplayName] = React.useState('');
  const [label, setLabel] = React.useState('');
  const [credValues, setCredValues] = React.useState<Record<string, string>>({});
  const [licenseAck, setLicenseAck] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const providers = React.useMemo(() => catalog?.items ?? [], [catalog]);
  const selected = React.useMemo(
    () => providers.find(p => p.provider_key === providerKey) ?? null,
    [providers, providerKey]
  );
  const requiresCredentials = selected?.requires_credentials ?? false;

  React.useEffect(() => {
    if (!open) {
      setProviderKey('');
      setDisplayName('');
      setLabel('');
      setCredValues({});
      setLicenseAck(false);
      setError(null);
    }
  }, [open]);

  // Drop any entered credentials when switching providers so they never leak.
  React.useEffect(() => {
    setCredValues({});
  }, [providerKey]);

  const handleClose = () => {
    setCredValues({});
    onClose();
  };

  const handleSubmit = () => {
    if (!providerKey || !displayName.trim() || !licenseAck) return;

    let credentials: { fields: Record<string, string> } | null = null;
    if (requiresCredentials) {
      const fields = resolveCredentialFields(providerKey, selected?.config_schema);
      const trimmed: Record<string, string> = {};
      for (const field of fields) {
        const value = (credValues[field.key] ?? '').trim();
        if (value) trimmed[field.key] = value;
      }
      if (Object.keys(trimmed).length === 0) {
        setError('Enter the required credential fields before saving.');
        return;
      }
      credentials = { fields: trimmed };
    }

    setError(null);
    createAccount.mutate(
      {
        provider_key: providerKey,
        display_name: displayName.trim(),
        external_account_label: label.trim() || null,
        credentials,
        licensing_acknowledged: true
      },
      {
        onSuccess: account => {
          setCredValues({});
          onCreated?.(account.id);
          onClose();
        },
        onError: (err: Error & { response?: { data?: { detail?: string } } }) => {
          setError(err.response?.data?.detail || err.message || 'Failed to create account.');
        }
      }
    );
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Add Weather Provider Account</DialogTitle>
      <DialogContent>
        {providers.length === 0 ? (
          <Alert severity="warning" sx={{ mt: 1 }}>
            No enabled weather providers are available in the catalog.
          </Alert>
        ) : (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <FormControl fullWidth>
              <InputLabel id="add-weather-provider">Provider</InputLabel>
              <Select
                labelId="add-weather-provider"
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

            <TextField
              label="Account name *"
              value={displayName}
              onChange={e => setDisplayName(e.target.value)}
              fullWidth
              autoFocus
              helperText="Internal label that identifies this account inside iliOS."
            />

            <TextField
              label="External account label (optional)"
              value={label}
              onChange={e => setLabel(e.target.value)}
              fullWidth
              helperText="The provider-side username or account identifier, for operator reference."
            />

            {providerKey && requiresCredentials && (
              <CredentialFieldsForm
                providerKey={providerKey}
                configSchema={selected?.config_schema}
                values={credValues}
                onChange={(key, value) => setCredValues(prev => ({ ...prev, [key]: value }))}
                disabled={createAccount.isPending}
              />
            )}

            {providerKey && !requiresCredentials && (
              <Alert severity="info">This provider is keyless — no credentials are required.</Alert>
            )}

            {providerKey && (
              <FormControlLabel
                control={<Checkbox checked={licenseAck} onChange={e => setLicenseAck(e.target.checked)} />}
                label={
                  <span>
                    I confirm this company is licensed to use{' '}
                    <strong>{selected?.display_name || 'this provider'}</strong>
                    {selected?.licensing_class ? ` (${selected.licensing_class})` : ''} and accept its terms.
                    {selected?.docs_url ? (
                      <>
                        {' '}
                        <Link href={selected.docs_url} target="_blank" rel="noopener noreferrer">
                          Provider terms
                        </Link>
                      </>
                    ) : null}
                  </span>
                }
              />
            )}

            <Alert severity="info">
              The account will be created with any credentials saved <strong>write-only</strong> and marked{' '}
              <strong>not tested</strong>. iliOS will not contact the provider until you click <strong>Test</strong>.
              External weather is stored as context only and never drives expected math.
            </Alert>

            {error && <Alert severity="error">{error}</Alert>}
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button
          variant="contained"
          disabled={
            providers.length === 0 || !providerKey || !displayName.trim() || !licenseAck || createAccount.isPending
          }
          onClick={handleSubmit}
          startIcon={createAccount.isPending ? <CircularProgress size={16} color="inherit" /> : null}
        >
          {createAccount.isPending ? 'Saving…' : 'Save Account'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default AddWeatherProviderAccountDialog;
