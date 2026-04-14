import React from 'react';
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
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import Skeleton from '@mui/material/Skeleton';
import AddIcon from '@mui/icons-material/Add';
import DeleteIcon from '@mui/icons-material/Delete';
import SensorsIcon from '@mui/icons-material/Sensors';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';

import { ApiClient } from '../../../../api';

interface TelemetryProvidersSectionProps {
  companyId: number;
}

const ALL_PROVIDERS = [
  { key: 'kmc', display: 'KMC' },
  { key: 'also_energy', display: 'Also Energy' }
];

export const TelemetryProvidersSection: React.FC<TelemetryProvidersSectionProps> = ({ companyId }) => {
  const queryClient = useQueryClient();
  const [isAddDialogOpen, setIsAddDialogOpen] = React.useState(false);
  const [selectedProvider, setSelectedProvider] = React.useState('');

  const { data, isLoading, error } = useQuery({
    queryKey: ['companyProviders', companyId],
    queryFn: () => ApiClient.connections.getCompanyProviders(companyId),
    staleTime: 5 * 60 * 1000
  });

  const assignMutation = useMutation({
    mutationFn: (provider: string) => ApiClient.connections.assignCompanyProvider(companyId, provider),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['companyProviders', companyId] });
      setIsAddDialogOpen(false);
      setSelectedProvider('');
    }
  });

  const removeMutation = useMutation({
    mutationFn: (provider: string) => ApiClient.connections.removeCompanyProvider(companyId, provider)
  });

  const handleRemove = async (provider: string) => {
    await removeMutation.mutateAsync(provider);
    queryClient.invalidateQueries({ queryKey: ['companyProviders', companyId] });
  };

  const assignedKeys = data?.items?.map(p => p.provider) || [];
  const availableToAssign = ALL_PROVIDERS.filter(p => !assignedKeys.includes(p.key));

  return (
    <>
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Box sx={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', mb: 2 }}>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <SensorsIcon color="primary" />
              <Typography variant="h6">Telemetry Providers</Typography>
            </Box>
            <Button
              size="small"
              startIcon={<AddIcon />}
              onClick={() => setIsAddDialogOpen(true)}
              disabled={availableToAssign.length === 0}
            >
              Assign Provider
            </Button>
          </Box>

          {isLoading ? (
            <Skeleton variant="rectangular" height={100} />
          ) : error ? (
            <Alert severity="error">Failed to load telemetry providers</Alert>
          ) : !data?.items?.length ? (
            <Alert severity="info">
              No telemetry providers assigned. Assign providers to allow this company to create telemetry connections.
            </Alert>
          ) : (
            <TableContainer>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Provider</TableCell>
                    <TableCell align="right">Actions</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {data.items.map(provider => (
                    <TableRow key={provider.provider}>
                      <TableCell>
                        <Chip label={provider.provider_display} color="primary" variant="outlined" size="small" />
                      </TableCell>
                      <TableCell align="right">
                        <IconButton
                          size="small"
                          color="error"
                          onClick={() => handleRemove(provider.provider)}
                          disabled={removeMutation.isPending}
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
        </CardContent>
      </Card>

      <Dialog open={isAddDialogOpen} onClose={() => setIsAddDialogOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>Assign Telemetry Provider</DialogTitle>
        <DialogContent>
          <FormControl fullWidth sx={{ mt: 1 }}>
            <InputLabel>Provider</InputLabel>
            <Select value={selectedProvider} label="Provider" onChange={e => setSelectedProvider(e.target.value)}>
              {availableToAssign.map(p => (
                <MenuItem key={p.key} value={p.key}>
                  {p.display}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setIsAddDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={() => assignMutation.mutate(selectedProvider)}
            disabled={!selectedProvider || assignMutation.isPending}
          >
            {assignMutation.isPending ? <CircularProgress size={20} /> : 'Assign'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};
