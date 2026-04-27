import React from 'react';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import CircularProgress from '@mui/material/CircularProgress';
import Dialog from '@mui/material/Dialog';
import DialogActions from '@mui/material/DialogActions';
import DialogContent from '@mui/material/DialogContent';
import DialogTitle from '@mui/material/DialogTitle';
import FormControlLabel from '@mui/material/FormControlLabel';
import Radio from '@mui/material/Radio';
import RadioGroup from '@mui/material/RadioGroup';
import Skeleton from '@mui/material/Skeleton';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';

import { useProviderCatalog, useLicensedProviders, useTelemetryAdminMutations } from '../../../../../hooks/telemetryV2';

interface AddLicensedProviderDialogProps {
  companyId: number;
  open: boolean;
  onClose: () => void;
}

export const AddLicensedProviderDialog: React.FC<AddLicensedProviderDialogProps> = ({ companyId, open, onClose }) => {
  const { data: catalog, isLoading: catalogLoading } = useProviderCatalog({
    enabled: open
  });
  const { data: licensed } = useLicensedProviders(companyId, {
    enabled: open
  });
  const { grantLicense } = useTelemetryAdminMutations(companyId);

  const [providerKey, setProviderKey] = React.useState('');
  const [notes, setNotes] = React.useState('');
  const [error, setError] = React.useState<string | null>(null);

  const licensedKeys = React.useMemo(() => new Set((licensed?.items ?? []).map(l => l.provider_key)), [licensed]);
  const available = React.useMemo(
    () => (catalog?.items ?? []).filter(entry => entry.is_enabled && !licensedKeys.has(entry.provider_key)),
    [catalog, licensedKeys]
  );

  React.useEffect(() => {
    if (open) {
      setProviderKey(available[0]?.provider_key ?? '');
      setNotes('');
      setError(null);
    } else {
      setProviderKey('');
      setNotes('');
      setError(null);
    }
  }, [open, available]);

  const handleSubmit = () => {
    if (!providerKey) return;
    setError(null);
    grantLicense.mutate(
      { provider_key: providerKey, notes: notes.trim() || null },
      {
        onSuccess: () => {
          onClose();
        },
        onError: (err: Error & { response?: { data?: { detail?: string } } }) => {
          setError(err.response?.data?.detail || err.message || 'Failed to grant license.');
        }
      }
    );
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Add Licensed Provider</DialogTitle>
      <DialogContent>
        {catalogLoading ? (
          <Skeleton variant="rectangular" height={120} />
        ) : available.length === 0 ? (
          <Alert severity="success">All catalog providers are already licensed for this company.</Alert>
        ) : (
          <>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
              Pick a provider type to license for this company. Provider Accounts can then be created against it.
            </Typography>
            <RadioGroup value={providerKey} onChange={e => setProviderKey(e.target.value)}>
              {available.map(entry => (
                <Card key={entry.provider_key} variant="outlined" sx={{ mb: 1 }}>
                  <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                    <FormControlLabel
                      value={entry.provider_key}
                      control={<Radio />}
                      sx={{ alignItems: 'flex-start', m: 0 }}
                      label={
                        <Box sx={{ ml: 1 }}>
                          <Typography variant="subtitle2">{entry.display_name}</Typography>
                          <Typography variant="caption" color="text.secondary">
                            {entry.provider_key}
                          </Typography>
                          {entry.docs_url && (
                            <Typography
                              variant="caption"
                              component="a"
                              href={entry.docs_url}
                              target="_blank"
                              rel="noopener"
                              sx={{ display: 'block', mt: 0.5 }}
                            >
                              Provider documentation →
                            </Typography>
                          )}
                        </Box>
                      }
                    />
                  </CardContent>
                </Card>
              ))}
            </RadioGroup>
            <TextField
              label="Notes (optional)"
              value={notes}
              onChange={e => setNotes(e.target.value)}
              fullWidth
              multiline
              rows={2}
              sx={{ mt: 2 }}
            />
            {error && (
              <Alert severity="error" sx={{ mt: 2 }}>
                {error}
              </Alert>
            )}
          </>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{available.length === 0 ? 'Close' : 'Cancel'}</Button>
        {available.length > 0 && (
          <Button
            variant="contained"
            onClick={handleSubmit}
            disabled={!providerKey || grantLicense.isPending}
            startIcon={grantLicense.isPending ? <CircularProgress size={16} color="inherit" /> : null}
          >
            {grantLicense.isPending ? 'Adding…' : 'Add License'}
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};
