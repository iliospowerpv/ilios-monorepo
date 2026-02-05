import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import Chip from '@mui/material/Chip';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import TextField from '@mui/material/TextField';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import Skeleton from '@mui/material/Skeleton';
import AddIcon from '@mui/icons-material/Add';
import SyncIcon from '@mui/icons-material/Sync';
import DeleteIcon from '@mui/icons-material/Delete';
import AccountBalanceIcon from '@mui/icons-material/AccountBalance';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty';
import BlockIcon from '@mui/icons-material/Block';

import { ApiClient } from '../../../../api';
import type { FinanceIntegrationCreatePayload } from '../../../../api/financeIntegrations';

interface FinanceIntegrationsSectionProps {
  companyId: number;
}

const getStatusIcon = (status: string) => {
  switch (status) {
    case 'configured':
      return <CheckCircleIcon color="success" fontSize="small" />;
    case 'error':
      return <ErrorIcon color="error" fontSize="small" />;
    case 'disabled':
      return <BlockIcon color="disabled" fontSize="small" />;
    default:
      return <HourglassEmptyIcon color="warning" fontSize="small" />;
  }
};

const getStatusColor = (status: string): 'success' | 'error' | 'warning' | 'default' => {
  switch (status) {
    case 'configured':
      return 'success';
    case 'error':
      return 'error';
    case 'disabled':
      return 'default';
    default:
      return 'warning';
  }
};

const getStatusLabel = (status: string): string => {
  switch (status) {
    case 'configured':
      return 'Connected';
    case 'error':
      return 'Error';
    case 'disabled':
      return 'Disabled';
    case 'pending':
      return 'Not Tested';
    default:
      return status;
  }
};

export const FinanceIntegrationsSection: React.FC<FinanceIntegrationsSectionProps> = ({ companyId }) => {
  const queryClient = useQueryClient();
  const [isAddDialogOpen, setIsAddDialogOpen] = useState(false);
  const [selectedProvider, setSelectedProvider] = useState('');
  const [apiKey, setApiKey] = useState('');
  const [apiSecret, setApiSecret] = useState('');
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ['financeIntegrations', companyId],
    queryFn: () => ApiClient.financeIntegrations.getCompanyIntegrations(companyId),
    staleTime: 5 * 60 * 1000
  });

  const createMutation = useMutation({
    mutationFn: (payload: FinanceIntegrationCreatePayload) =>
      ApiClient.financeIntegrations.createIntegration(companyId, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['financeIntegrations', companyId] });
      handleCloseDialog();
    }
  });

  const testMutation = useMutation({
    mutationFn: (providerKey: string) => ApiClient.financeIntegrations.testIntegration(companyId, providerKey),
    onSuccess: result => {
      setTestResult({ success: result.success, message: result.message });
      queryClient.invalidateQueries({ queryKey: ['financeIntegrations', companyId] });
    },
    onError: (err: Error) => {
      setTestResult({ success: false, message: err.message });
    }
  });

  const deleteMutation = useMutation({
    mutationFn: (providerKey: string) => ApiClient.financeIntegrations.deleteIntegration(companyId, providerKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['financeIntegrations', companyId] });
    }
  });

  const handleCloseDialog = () => {
    setIsAddDialogOpen(false);
    setSelectedProvider('');
    setApiKey('');
    setApiSecret('');
    setTestResult(null);
  };

  const handleSaveIntegration = () => {
    if (!selectedProvider || !apiKey) return;

    createMutation.mutate({
      provider_key: selectedProvider,
      credentials: {
        api_key: apiKey,
        api_secret: apiSecret || undefined
      }
    });
  };

  const handleTestConnection = (providerKey: string) => {
    testMutation.mutate(providerKey);
  };

  const handleDeleteIntegration = (providerKey: string) => {
    if (window.confirm('Are you sure you want to remove this finance integration?')) {
      deleteMutation.mutate(providerKey);
    }
  };

  const integrations = data?.integrations || [];
  const availableProviders = data?.available_providers || [];
  const unconfiguredProviders = availableProviders.filter(p => !integrations.some(i => i.provider_key === p.key));

  if (error) {
    return (
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Alert severity="error">
            Unable to load finance integrations. You may not have permission to access this feature.
          </Alert>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card sx={{ mt: 3 }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <AccountBalanceIcon color="primary" />
            <Typography variant="h6">Finance Integrations</Typography>
          </Box>
          {unconfiguredProviders.length > 0 && (
            <Button variant="outlined" size="small" startIcon={<AddIcon />} onClick={() => setIsAddDialogOpen(true)}>
              Add Integration
            </Button>
          )}
        </Box>

        {isLoading ? (
          <Skeleton variant="rectangular" height={100} />
        ) : integrations.length === 0 ? (
          <Box sx={{ textAlign: 'center', py: 3 }}>
            <Typography color="text.secondary" sx={{ mb: 2 }}>
              No finance integrations configured for this company.
            </Typography>
            {unconfiguredProviders.length > 0 && (
              <Button variant="contained" startIcon={<AddIcon />} onClick={() => setIsAddDialogOpen(true)}>
                Configure Finance Integration
              </Button>
            )}
          </Box>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Provider</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell>Last Tested</TableCell>
                  <TableCell align="right">Actions</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {integrations.map(integration => (
                  <TableRow key={integration.id}>
                    <TableCell>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                        <AccountBalanceIcon fontSize="small" color="action" />
                        <Typography variant="body2">
                          {integration.provider_display_name || integration.provider_key}
                        </Typography>
                      </Box>
                    </TableCell>
                    <TableCell>
                      <Chip
                        icon={getStatusIcon(integration.status)}
                        label={getStatusLabel(integration.status)}
                        size="small"
                        color={getStatusColor(integration.status)}
                        variant="outlined"
                      />
                    </TableCell>
                    <TableCell>
                      <Typography variant="body2" color="text.secondary">
                        {integration.last_tested_at
                          ? new Date(integration.last_tested_at).toLocaleDateString()
                          : 'Never'}
                      </Typography>
                    </TableCell>
                    <TableCell align="right">
                      <IconButton
                        size="small"
                        onClick={() => handleTestConnection(integration.provider_key)}
                        disabled={testMutation.isPending}
                        title="Test Connection"
                      >
                        {testMutation.isPending && testMutation.variables === integration.provider_key ? (
                          <CircularProgress size={16} />
                        ) : (
                          <SyncIcon fontSize="small" />
                        )}
                      </IconButton>
                      <IconButton
                        size="small"
                        onClick={() => handleDeleteIntegration(integration.provider_key)}
                        disabled={deleteMutation.isPending}
                        title="Remove Integration"
                        color="error"
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}

        {testResult && (
          <Alert severity={testResult.success ? 'success' : 'error'} sx={{ mt: 2 }}>
            {testResult.message}
          </Alert>
        )}
      </CardContent>

      <Dialog open={isAddDialogOpen} onClose={handleCloseDialog} maxWidth="sm" fullWidth>
        <DialogTitle>Add Finance Integration</DialogTitle>
        <DialogContent>
          <FormControl fullWidth sx={{ mt: 2 }}>
            <InputLabel>Provider</InputLabel>
            <Select value={selectedProvider} onChange={e => setSelectedProvider(e.target.value)} label="Provider">
              {unconfiguredProviders.map(provider => (
                <MenuItem key={provider.key} value={provider.key}>
                  {provider.display_name}
                  {provider.supports_budgets && <Chip label="Budgets" size="small" sx={{ ml: 1 }} />}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <TextField
            fullWidth
            label="API Key"
            value={apiKey}
            onChange={e => setApiKey(e.target.value)}
            sx={{ mt: 2 }}
            type="password"
            required
          />

          <TextField
            fullWidth
            label="API Secret"
            value={apiSecret}
            onChange={e => setApiSecret(e.target.value)}
            sx={{ mt: 2 }}
            type="password"
            helperText="Optional, depending on provider requirements"
          />

          {createMutation.isError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              Failed to create integration. Please check your credentials.
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={handleCloseDialog}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleSaveIntegration}
            disabled={!selectedProvider || !apiKey || createMutation.isPending}
          >
            {createMutation.isPending ? <CircularProgress size={20} /> : 'Save'}
          </Button>
        </DialogActions>
      </Dialog>
    </Card>
  );
};

export default FinanceIntegrationsSection;
