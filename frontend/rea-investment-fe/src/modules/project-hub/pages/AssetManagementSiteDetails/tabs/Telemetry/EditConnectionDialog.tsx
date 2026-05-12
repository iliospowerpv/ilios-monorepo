import React, { useEffect, useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Alert from '@mui/material/Alert';
import FormControlLabel from '@mui/material/FormControlLabel';
import Checkbox from '@mui/material/Checkbox';
import CircularProgress from '@mui/material/CircularProgress';
import Typography from '@mui/material/Typography';

import { ApiClient } from '../../../../../../api';
import type { Connection } from '../../../../../../api/connections';

export interface ConnectionToEdit {
  id: number;
  name: string;
  provider: string;
  owner_type: string;
}

interface EditConnectionDialogProps {
  open: boolean;
  onClose: () => void;
  companyId: number;
  connection: ConnectionToEdit | null;
}

export const EditConnectionDialog: React.FC<EditConnectionDialogProps> = ({ open, onClose, companyId, connection }) => {
  const queryClient = useQueryClient();
  const [name, setName] = useState('');
  const [shareWithPortfolio, setShareWithPortfolio] = useState(false);
  const [token, setToken] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (open && connection) {
      setName(connection.name);
      setShareWithPortfolio(connection.owner_type === 'portfolio');
      setToken('');
      setUsername('');
      setPassword('');
      setTestResult(null);
      setError(null);
    }
  }, [open, connection]);

  const provider = connection?.provider ?? '';
  const credsTouched = provider === 'KMC' ? !!token : provider === 'Also Energy' ? !!username || !!password : false;
  const credsComplete = provider === 'KMC' ? !!token : provider === 'Also Energy' ? !!username && !!password : false;
  const partialCreds = credsTouched && !credsComplete;

  const testMutation = useMutation({
    mutationFn: () =>
      ApiClient.connections.testConnection({
        provider,
        ...(provider === 'KMC' ? { token } : {}),
        ...(provider === 'Also Energy' ? { username, password } : {})
      }),
    onSuccess: data => setTestResult({ success: data.success, message: data.message }),
    onError: (err: unknown) => {
      const message =
        err instanceof AxiosError
          ? err.response?.data?.message || err.message
          : (err as Error)?.message || 'Connection test failed';
      setTestResult({ success: false, message });
    }
  });

  const updateMutation = useMutation({
    mutationFn: (attrs: Connection) => ApiClient.connections.updateConnection(companyId, connection?.id, attrs),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connections', companyId] });
      queryClient.invalidateQueries({ queryKey: ['available-connections', companyId] });
      onClose();
    },
    onError: (err: unknown) => {
      const message =
        err instanceof AxiosError
          ? err.response?.data?.message || err.message
          : (err as Error)?.message || 'Failed to update connection';
      setError(message);
    }
  });

  const handleSave = () => {
    if (!connection) return;
    setError(null);
    const attrs: Connection = {
      name: name.trim(),
      share_with_portfolio: shareWithPortfolio
    };
    if (credsComplete) {
      if (provider === 'KMC') attrs.token = token;
      if (provider === 'Also Energy') {
        attrs.username = username;
        attrs.password = password;
      }
    }
    updateMutation.mutate(attrs);
  };

  const handleTest = () => {
    setError(null);
    testMutation.mutate();
  };

  const trimmedName = name.trim();
  const nameValid = trimmedName.length >= 2 && trimmedName.length <= 100;
  const saveDisabled =
    !nameValid || updateMutation.isPending || partialCreds || (credsComplete && !testResult?.success);

  return (
    <Dialog open={open} onClose={onClose} maxWidth="sm" fullWidth>
      <DialogTitle>Edit Connection</DialogTitle>
      <DialogContent>
        <Box sx={{ pt: 1 }}>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Provider: {provider}
          </Typography>
          <TextField
            fullWidth
            label="Connection Name"
            value={name}
            onChange={e => setName(e.target.value)}
            error={!!name && !nameValid}
            helperText={!!name && !nameValid ? 'Name must be 2-100 characters.' : ' '}
            sx={{ mb: 1 }}
          />
          <FormControlLabel
            control={<Checkbox checked={shareWithPortfolio} onChange={e => setShareWithPortfolio(e.target.checked)} />}
            label="Share with portfolio hub"
            sx={{ mb: 2 }}
          />

          <Typography variant="subtitle2">Update credentials (optional)</Typography>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 1 }}>
            Leave blank to keep the existing credentials. To replace them, enter new values and test before saving.
          </Typography>

          {provider === 'KMC' && (
            <TextField
              fullWidth
              label="API Token"
              type="password"
              value={token}
              onChange={e => {
                setToken(e.target.value);
                setTestResult(null);
              }}
              sx={{ mb: 2 }}
              autoComplete="new-password"
            />
          )}

          {provider === 'Also Energy' && (
            <>
              <TextField
                fullWidth
                label="Username"
                value={username}
                onChange={e => {
                  setUsername(e.target.value);
                  setTestResult(null);
                }}
                sx={{ mb: 2 }}
                autoComplete="off"
              />
              <TextField
                fullWidth
                label="Password"
                type="password"
                value={password}
                onChange={e => {
                  setPassword(e.target.value);
                  setTestResult(null);
                }}
                sx={{ mb: 2 }}
                autoComplete="new-password"
              />
            </>
          )}

          {credsComplete && (
            <Button
              variant="outlined"
              size="small"
              onClick={handleTest}
              disabled={testMutation.isPending}
              sx={{ mb: 2 }}
            >
              {testMutation.isPending ? <CircularProgress size={16} /> : 'Test Connection'}
            </Button>
          )}

          {partialCreds && (
            <Alert severity="warning" sx={{ mb: 2 }}>
              Enter both username and password (and test) to update credentials, or clear both fields to keep the
              existing ones.
            </Alert>
          )}

          {testResult && (
            <Alert severity={testResult.success ? 'success' : 'error'} sx={{ mb: 2 }}>
              {testResult.message}
            </Alert>
          )}

          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}
        </Box>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={updateMutation.isPending}>
          Cancel
        </Button>
        <Button variant="contained" onClick={handleSave} disabled={saveDisabled}>
          {updateMutation.isPending ? <CircularProgress size={20} /> : 'Save'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};

export default EditConnectionDialog;
