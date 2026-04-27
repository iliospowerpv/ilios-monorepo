import React from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import Typography from '@mui/material/Typography';

import type { ProviderAccount } from '../../../../../types/telemetryV2';
import { useProviderCatalog, useTelemetryAdminMutations } from '../../../../../hooks/telemetryV2';
import { CredentialFieldsForm, resolveCredentialFields } from './CredentialFieldsForm';

interface RotateCredentialsDialogProps {
  companyId: number;
  account: ProviderAccount | null;
  open: boolean;
  onClose: () => void;
}

export const RotateCredentialsDialog: React.FC<RotateCredentialsDialogProps> = ({
  companyId,
  account,
  open,
  onClose
}) => {
  const { data: catalog } = useProviderCatalog({ enabled: open });
  const { updateAccount } = useTelemetryAdminMutations(companyId);

  const [credValues, setCredValues] = React.useState<Record<string, string>>({});
  const [error, setError] = React.useState<string | null>(null);

  const catalogEntry = React.useMemo(
    () => (account && catalog ? (catalog.items.find(c => c.provider_key === account.provider_key) ?? null) : null),
    [account, catalog]
  );

  React.useEffect(() => {
    if (!open) {
      setCredValues({});
      setError(null);
    }
  }, [open]);

  const handleClose = () => {
    setCredValues({});
    onClose();
  };

  const handleSubmit = () => {
    if (!account) return;
    const fields = resolveCredentialFields(account.provider_key, catalogEntry?.config_schema);
    const trimmed: Record<string, string> = {};
    for (const field of fields) {
      const value = (credValues[field.key] ?? '').trim();
      if (value) trimmed[field.key] = value;
    }
    if (Object.keys(trimmed).length === 0) {
      setError('Enter the new credential values to rotate.');
      return;
    }
    setError(null);
    updateAccount.mutate(
      {
        accountId: account.id,
        payload: { credentials: { fields: trimmed } }
      },
      {
        onSuccess: () => {
          setCredValues({});
          onClose();
        },
        onError: (err: Error & { response?: { data?: { detail?: string } } }) => {
          setError(err.response?.data?.detail || err.message || 'Failed to rotate credentials.');
        }
      }
    );
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>
        Rotate Credentials
        {account && (
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
            {account.display_name} — {account.name}
          </Typography>
        )}
      </DialogTitle>
      <DialogContent>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
          {account && (
            <CredentialFieldsForm
              providerKey={account.provider_key}
              configSchema={catalogEntry?.config_schema}
              values={credValues}
              onChange={(key, value) => setCredValues(prev => ({ ...prev, [key]: value }))}
              disabled={updateAccount.isPending}
            />
          )}
          <Alert severity="info">
            After rotation, credential status returns to <strong>Not tested</strong>. Click{' '}
            <strong>Test Credentials</strong> on the account to verify the new values before syncing sites.
          </Alert>
          {error && <Alert severity="error">{error}</Alert>}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={handleClose}>Cancel</Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={updateAccount.isPending || !account}
          startIcon={updateAccount.isPending ? <CircularProgress size={16} color="inherit" /> : null}
        >
          {updateAccount.isPending ? 'Rotating…' : 'Rotate Credentials'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
