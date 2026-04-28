import React from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import MenuItem from '@mui/material/MenuItem';
import Select from '@mui/material/Select';
import TextField from '@mui/material/TextField';

import { useLicensedProviders, useProviderCatalog, useTelemetryAdminMutations } from '../../../../../hooks/telemetryV2';
import { CredentialFieldsForm, resolveCredentialFields } from './CredentialFieldsForm';

interface AddProviderAccountDialogProps {
  companyId: number;
  open: boolean;
  onClose: () => void;
  onCreated?: (accountId: number) => void;
}

export const AddProviderAccountDialog: React.FC<AddProviderAccountDialogProps> = ({
  companyId,
  open,
  onClose,
  onCreated
}) => {
  const { data: licensed } = useLicensedProviders(companyId, { enabled: open });
  const { data: catalog } = useProviderCatalog({ enabled: open });
  const { createAccount } = useTelemetryAdminMutations(companyId);

  const [providerKey, setProviderKey] = React.useState('');
  const [name, setName] = React.useState('');
  const [label, setLabel] = React.useState('');
  const [credValues, setCredValues] = React.useState<Record<string, string>>({});
  const [error, setError] = React.useState<string | null>(null);

  const licensedItems = licensed?.items ?? [];
  const catalogItems = React.useMemo(() => catalog?.items ?? [], [catalog]);

  const selectedCatalog = React.useMemo(
    () => catalogItems.find(c => c.provider_key === providerKey) ?? null,
    [catalogItems, providerKey]
  );

  // Reset all local state on close so credential values never linger.
  React.useEffect(() => {
    if (!open) {
      setProviderKey('');
      setName('');
      setLabel('');
      setCredValues({});
      setError(null);
    }
  }, [open]);

  React.useEffect(() => {
    // When provider changes, drop any previously-entered credential values
    // so they cannot leak across providers via component state.
    setCredValues({});
  }, [providerKey]);

  const handleClose = () => {
    setCredValues({});
    onClose();
  };

  const handleSubmit = () => {
    if (!providerKey || !name.trim()) return;
    const fields = resolveCredentialFields(providerKey, selectedCatalog?.config_schema);
    const trimmed: Record<string, string> = {};
    for (const field of fields) {
      const value = (credValues[field.key] ?? '').trim();
      if (value) trimmed[field.key] = value;
    }
    if (Object.keys(trimmed).length === 0) {
      setError('Enter the required credential fields before saving.');
      return;
    }
    setError(null);
    createAccount.mutate(
      {
        name: name.trim(),
        provider_key: providerKey,
        external_account_label: label.trim() || null,
        credentials: { fields: trimmed }
      },
      {
        onSuccess: account => {
          // Wipe local credential state immediately so it never lingers
          // in any later-mounted component or React DevTools.
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
      <DialogTitle>Add Provider Account</DialogTitle>
      <DialogContent>
        {licensedItems.length === 0 ? (
          <Alert severity="warning">No licensed providers. License a provider type first.</Alert>
        ) : (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <FormControl fullWidth>
              <InputLabel id="add-account-provider">Provider</InputLabel>
              <Select
                labelId="add-account-provider"
                label="Provider"
                value={providerKey}
                onChange={e => setProviderKey(e.target.value as string)}
              >
                {licensedItems.map(license => (
                  <MenuItem key={license.id} value={license.provider_key}>
                    {license.display_name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              label="Account name *"
              value={name}
              onChange={e => setName(e.target.value)}
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

            {providerKey && (
              <CredentialFieldsForm
                providerKey={providerKey}
                configSchema={selectedCatalog?.config_schema}
                values={credValues}
                onChange={(key, value) => setCredValues(prev => ({ ...prev, [key]: value }))}
                disabled={createAccount.isPending}
              />
            )}

            <Alert severity="info">
              The account will be created with credentials saved write-only and{' '}
              <strong>credentials marked as not tested</strong>. iliOS will not contact the provider until you click{' '}
              <strong>Test Credentials</strong>.
            </Alert>

            {error && <Alert severity="error">{error}</Alert>}
          </Box>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button
          variant="contained"
          disabled={licensedItems.length === 0 || !providerKey || !name.trim() || createAccount.isPending}
          onClick={handleSubmit}
          startIcon={createAccount.isPending ? <CircularProgress size={16} color="inherit" /> : null}
        >
          {createAccount.isPending ? 'Saving…' : 'Save Account'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
