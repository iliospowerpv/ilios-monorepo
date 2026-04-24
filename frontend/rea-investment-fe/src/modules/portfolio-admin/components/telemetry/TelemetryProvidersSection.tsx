import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import Chip from '@mui/material/Chip';
import Stack from '@mui/material/Stack';
import Skeleton from '@mui/material/Skeleton';
import Alert from '@mui/material/Alert';
import Tooltip from '@mui/material/Tooltip';
import CircularProgress from '@mui/material/CircularProgress';
import AddIcon from '@mui/icons-material/Add';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import SensorsIcon from '@mui/icons-material/Sensors';
import LinkIcon from '@mui/icons-material/Link';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogContentText from '@mui/material/DialogContentText';
import DialogActions from '@mui/material/DialogActions';
import RadioGroup from '@mui/material/RadioGroup';
import FormControlLabel from '@mui/material/FormControlLabel';
import Radio from '@mui/material/Radio';

import { ApiClient } from '../../../../api';

interface TelemetryProvidersSectionProps {
  companyId: number;
}

interface ProviderCatalogEntry {
  key: string;
  display: string;
  description: string;
}

const PROVIDER_CATALOG: ProviderCatalogEntry[] = [
  {
    key: 'kmc',
    display: 'KMC',
    description: 'KMC Controls — token-based telemetry feed. Best for sites already provisioned in the KMC portal.'
  },
  {
    key: 'also_energy',
    display: 'Also Energy',
    description: 'Also Energy (PowerTrack) — username/password telemetry feed. Used for inverter and meter monitoring.'
  }
];

const getProviderMeta = (key: string): ProviderCatalogEntry =>
  PROVIDER_CATALOG.find(p => p.key === key) ?? {
    key,
    display: key,
    description: 'Telemetry provider.'
  };

export const TelemetryProvidersSection: React.FC<TelemetryProvidersSectionProps> = ({ companyId }) => {
  const queryClient = useQueryClient();
  const [isAddDialogOpen, setIsAddDialogOpen] = React.useState(false);
  const [selectedProvider, setSelectedProvider] = React.useState('');
  const [removeTarget, setRemoveTarget] = React.useState<{ key: string; display: string; count: number } | null>(null);
  const [actionError, setActionError] = React.useState<string | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ['companyProviders', companyId],
    queryFn: () => ApiClient.connections.getCompanyProviders(companyId),
    staleTime: 60 * 1000
  });

  const assignMutation = useMutation({
    mutationFn: (provider: string) => ApiClient.connections.assignCompanyProvider(companyId, provider),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['companyProviders', companyId] });
      queryClient.invalidateQueries({ queryKey: ['connections', companyId] });
      setIsAddDialogOpen(false);
      setSelectedProvider('');
      setActionError(null);
    },
    onError: (err: Error & { response?: { data?: { detail?: string } } }) => {
      setActionError(err.response?.data?.detail || err.message || 'Failed to assign provider.');
    }
  });

  const removeMutation = useMutation({
    mutationFn: (provider: string) => ApiClient.connections.removeCompanyProvider(companyId, provider),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['companyProviders', companyId] });
      queryClient.invalidateQueries({ queryKey: ['connections', companyId] });
      setRemoveTarget(null);
      setActionError(null);
    },
    onError: (err: Error & { response?: { data?: { detail?: string } } }) => {
      setActionError(err.response?.data?.detail || err.message || 'Failed to remove provider.');
    }
  });

  const assignedProviders = data?.items ?? [];
  const assignedKeys = assignedProviders.map(p => p.provider);
  const availableToAssign = PROVIDER_CATALOG.filter(p => !assignedKeys.includes(p.key));
  const allAssigned = availableToAssign.length === 0;

  const openAddDialog = () => {
    setActionError(null);
    setSelectedProvider(availableToAssign[0]?.key ?? '');
    setIsAddDialogOpen(true);
  };

  const closeAddDialog = () => {
    setIsAddDialogOpen(false);
    setSelectedProvider('');
    setActionError(null);
  };

  const closeRemoveDialog = () => {
    setRemoveTarget(null);
    setActionError(null);
  };

  return (
    <>
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 1 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <SensorsIcon color="primary" />
              <Typography variant="h6">Telemetry Providers</Typography>
            </Box>
            <Button size="small" variant="contained" startIcon={<AddIcon />} onClick={openAddDialog}>
              Add Provider
            </Button>
          </Box>

          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            License the data acquisition systems (DAS) this company is allowed to use. Project users can then create
            telemetry connections in the project Telemetry tab using any provider listed here.
          </Typography>

          {actionError && !isAddDialogOpen && !removeTarget && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setActionError(null)}>
              {actionError}
            </Alert>
          )}

          {isLoading ? (
            <Skeleton variant="rectangular" height={120} />
          ) : error ? (
            <Alert severity="error">Failed to load telemetry providers.</Alert>
          ) : assignedProviders.length === 0 ? (
            <Alert severity="info" icon={<SensorsIcon />}>
              No telemetry providers assigned yet. Click <strong>Add Provider</strong> above to license one for this
              company.
            </Alert>
          ) : (
            <Stack spacing={1.5}>
              {assignedProviders.map(p => {
                const meta = getProviderMeta(p.provider);
                const count = p.connection_count ?? 0;
                return (
                  <Card key={p.provider} variant="outlined">
                    <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                        <CheckCircleIcon color="success" fontSize="small" />
                        <Box sx={{ flex: 1, minWidth: 0 }}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, flexWrap: 'wrap' }}>
                            <Typography variant="subtitle1" fontWeight={600}>
                              {p.provider_display || meta.display}
                            </Typography>
                            <Chip
                              size="small"
                              icon={<LinkIcon sx={{ fontSize: 14 }} />}
                              label={`${count} connection${count === 1 ? '' : 's'}`}
                              color={count > 0 ? 'primary' : 'default'}
                              variant={count > 0 ? 'filled' : 'outlined'}
                            />
                          </Box>
                          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
                            {meta.description}
                          </Typography>
                        </Box>
                        <Tooltip
                          title={
                            count > 0
                              ? `Cannot remove — ${count} connection${count === 1 ? '' : 's'} still use this provider. Delete those connections first.`
                              : 'Remove this provider from the company'
                          }
                        >
                          <span>
                            <IconButton
                              size="small"
                              color="error"
                              disabled={count > 0 || removeMutation.isPending}
                              onClick={() =>
                                setRemoveTarget({
                                  key: p.provider,
                                  display: p.provider_display || meta.display,
                                  count
                                })
                              }
                            >
                              <DeleteOutlineIcon fontSize="small" />
                            </IconButton>
                          </span>
                        </Tooltip>
                      </Box>
                    </CardContent>
                  </Card>
                );
              })}
            </Stack>
          )}
        </CardContent>
      </Card>

      <Dialog open={isAddDialogOpen} onClose={closeAddDialog} maxWidth="sm" fullWidth>
        <DialogTitle>Add Telemetry Provider</DialogTitle>
        <DialogContent>
          {allAssigned ? (
            <Alert severity="success">
              All supported providers are already assigned to this company. There&apos;s nothing more to add.
            </Alert>
          ) : (
            <>
              <DialogContentText sx={{ mb: 2 }}>
                Pick a provider to license for this company. Once added, project users can create connections that use
                it.
              </DialogContentText>
              <RadioGroup value={selectedProvider} onChange={e => setSelectedProvider(e.target.value)}>
                {availableToAssign.map(p => (
                  <Card key={p.key} variant="outlined" sx={{ mb: 1 }}>
                    <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                      <FormControlLabel
                        value={p.key}
                        control={<Radio />}
                        sx={{ alignItems: 'flex-start', m: 0 }}
                        label={
                          <Box sx={{ ml: 1 }}>
                            <Typography variant="subtitle1" fontWeight={600}>
                              {p.display}
                            </Typography>
                            <Typography variant="body2" color="text.secondary">
                              {p.description}
                            </Typography>
                          </Box>
                        }
                      />
                    </CardContent>
                  </Card>
                ))}
              </RadioGroup>
              {actionError && (
                <Alert severity="error" sx={{ mt: 2 }}>
                  {actionError}
                </Alert>
              )}
            </>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={closeAddDialog}>{allAssigned ? 'Close' : 'Cancel'}</Button>
          {!allAssigned && (
            <Button
              variant="contained"
              onClick={() => assignMutation.mutate(selectedProvider)}
              disabled={!selectedProvider || assignMutation.isPending}
              startIcon={assignMutation.isPending ? <CircularProgress size={16} color="inherit" /> : <AddIcon />}
            >
              {assignMutation.isPending ? 'Adding…' : 'Add Provider'}
            </Button>
          )}
        </DialogActions>
      </Dialog>

      <Dialog open={removeTarget !== null} onClose={closeRemoveDialog} maxWidth="xs" fullWidth>
        <DialogTitle>Remove {removeTarget?.display}?</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Project users in this company will no longer be able to create new connections using{' '}
            <strong>{removeTarget?.display}</strong>. Existing connections (if any) won&apos;t be deleted, but they
            should be removed from the project Telemetry tab before you proceed.
          </DialogContentText>
          {actionError && (
            <Alert severity="error" sx={{ mt: 2 }}>
              {actionError}
            </Alert>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={closeRemoveDialog}>Cancel</Button>
          <Button
            variant="contained"
            color="error"
            onClick={() => removeTarget && removeMutation.mutate(removeTarget.key)}
            disabled={removeMutation.isPending}
            startIcon={
              removeMutation.isPending ? <CircularProgress size={16} color="inherit" /> : <DeleteOutlineIcon />
            }
          >
            {removeMutation.isPending ? 'Removing…' : 'Remove'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};
