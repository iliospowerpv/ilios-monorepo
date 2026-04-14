import React, { useState, useMemo, useEffect } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Stepper from '@mui/material/Stepper';
import Step from '@mui/material/Step';
import StepLabel from '@mui/material/StepLabel';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import { SearchableSelect } from '../../../../../../components/common/SearchableSelect/SearchableSelect';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import Checkbox from '@mui/material/Checkbox';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import Chip from '@mui/material/Chip';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';

import { ApiClient } from '../../../../../../api';
import type { SiteDetailedInfo } from '../../../../../../api';
import type {
  TelemetryReadinessResponse,
  Connection,
  TelemetryDevice,
  DeviceMapping,
  CreateSiteMappingAttributes
} from '../../../../../../api/connections';

const STEPS = ['Connection', 'Site Mapping', 'Device Mapping', 'Confirm'];

interface TelemetryWizardProps {
  open: boolean;
  onClose: () => void;
  siteDetails: SiteDetailedInfo;
  readiness?: TelemetryReadinessResponse;
}

export const TelemetryWizard: React.FC<TelemetryWizardProps> = ({ open, onClose, siteDetails, readiness }) => {
  const queryClient = useQueryClient();
  const [activeStep, setActiveStep] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const [connectionMode, setConnectionMode] = useState<'existing' | 'new'>(
    readiness?.is_connected ? 'existing' : 'new'
  );
  const [selectedConnectionId, setSelectedConnectionId] = useState<number | null>(readiness?.connection_id || null);
  const [newConnectionForm, setNewConnectionForm] = useState({
    name: '',
    provider: '',
    token: '',
    username: '',
    password: ''
  });
  const [connectionTested, setConnectionTested] = useState(false);
  const [testResult, setTestResult] = useState<{ success: boolean; message: string } | null>(null);

  const [selectedDasSite, setSelectedDasSite] = useState<{ id: string; name: string } | null>(
    readiness?.telemetry_site_id && readiness?.telemetry_site_name
      ? { id: readiness.telemetry_site_id, name: readiness.telemetry_site_name }
      : null
  );

  const [deviceMappings, setDeviceMappings] = useState<
    Record<number, { telemetry_device_id: string; telemetry_device_name: string }>
  >({});
  const [selectedDevices, setSelectedDevices] = useState<Set<number>>(new Set());

  const companyId = siteDetails.company?.id;

  useEffect(() => {
    if (open) {
      setActiveStep(0);
      setError(null);
      setConnectionMode(readiness?.is_connected ? 'existing' : 'new');
      setSelectedConnectionId(readiness?.connection_id || null);
      setNewConnectionForm({
        name: '',
        provider: '',
        token: '',
        username: '',
        password: ''
      });
      setConnectionTested(false);
      setTestResult(null);
      setSelectedDasSite(
        readiness?.telemetry_site_id && readiness?.telemetry_site_name
          ? { id: readiness.telemetry_site_id, name: readiness.telemetry_site_name }
          : null
      );
      setDeviceMappings({});
      setSelectedDevices(new Set());
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const {
    data: companyProviders,
    isLoading: isLoadingProviders,
    isError: isProvidersError
  } = useQuery({
    queryKey: ['companyProviders', companyId],
    queryFn: () => ApiClient.connections.getCompanyProviders(companyId as number),
    enabled: !!companyId && open
  });

  const providers = useMemo(() => {
    if (companyProviders?.items?.length) {
      return companyProviders.items.map(p => ({ value: p.provider_display, label: p.provider_display }));
    }
    return [];
  }, [companyProviders]);

  const hasNoProviders = companyProviders !== undefined && providers.length === 0;

  const { data: connections, isLoading: isLoadingConnections } = useQuery({
    queryKey: ['connections', companyId],
    queryFn: () => ApiClient.connections.getConnections(companyId as number),
    enabled: !!companyId && open
  });

  const selectedConnection = useMemo(() => {
    if (connectionMode === 'existing' && selectedConnectionId) {
      return connections?.items.find(c => c.id === selectedConnectionId);
    }
    return null;
  }, [connectionMode, selectedConnectionId, connections]);

  const { data: dasSites, isLoading: isLoadingDasSites } = useQuery({
    queryKey: ['das-sites', companyId, selectedConnectionId],
    queryFn: () => ApiClient.connections.getSites(companyId as number, selectedConnectionId as number),
    enabled: !!companyId && !!selectedConnectionId && activeStep >= 1
  });

  const { data: dasDevices, isLoading: isLoadingDasDevices } = useQuery({
    queryKey: ['das-devices', siteDetails.id],
    queryFn: () => ApiClient.connections.getTelemetryDevices(siteDetails.id),
    enabled: !!siteDetails.id && !!selectedDasSite && activeStep >= 2
  });

  const { data: eligibleDevices, isLoading: isLoadingEligibleDevices } = useQuery({
    queryKey: ['eligible-devices', siteDetails.id],
    queryFn: () => ApiClient.connections.getEligibleDevices(siteDetails.id),
    enabled: !!siteDetails.id && activeStep >= 2
  });

  const testConnectionMutation = useMutation({
    mutationFn: (payload: { provider: string; token?: string; username?: string; password?: string }) =>
      ApiClient.connections.testConnection(payload),
    onSuccess: data => {
      setTestResult({ success: data.success, message: data.message });
      setConnectionTested(data.success);
    },
    onError: (err: Error) => {
      setTestResult({ success: false, message: err.message || 'Connection test failed' });
      setConnectionTested(false);
    }
  });

  const createConnectionMutation = useMutation({
    mutationFn: (attrs: Connection) => ApiClient.connections.createConnection(companyId as number, attrs),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['connections', companyId] });
    }
  });

  const createSiteMappingMutation = useMutation({
    mutationFn: (attrs: CreateSiteMappingAttributes) => ApiClient.connections.createSiteMapping(siteDetails.id, attrs)
  });

  const updateSiteMappingMutation = useMutation({
    mutationFn: (attrs: CreateSiteMappingAttributes) => ApiClient.connections.updateSiteMapping(siteDetails.id, attrs)
  });

  const bulkMapDevicesMutation = useMutation({
    mutationFn: (payload: { mappings: DeviceMapping[] }) =>
      ApiClient.connections.bulkMapDevices(siteDetails.id, payload)
  });

  const handleTestConnection = () => {
    const provider = newConnectionForm.provider;
    const payload = {
      provider,
      ...(provider === 'KMC' ? { token: newConnectionForm.token } : {}),
      ...(provider === 'Also Energy'
        ? { username: newConnectionForm.username, password: newConnectionForm.password }
        : {})
    };
    testConnectionMutation.mutate(payload);
  };

  const handleNext = async () => {
    setError(null);

    if (activeStep === 0) {
      if (connectionMode === 'new') {
        if (!connectionTested) {
          setError('Please test the connection before proceeding');
          return;
        }
        try {
          await createConnectionMutation.mutateAsync({
            name: newConnectionForm.name,
            provider: newConnectionForm.provider,
            ...(newConnectionForm.provider === 'KMC' ? { token: newConnectionForm.token } : {}),
            ...(newConnectionForm.provider === 'Also Energy'
              ? { username: newConnectionForm.username, password: newConnectionForm.password }
              : {})
          });
          const refreshedConnections = await ApiClient.connections.getConnections(companyId as number);
          const newConn = refreshedConnections.items.find(c => c.name === newConnectionForm.name);
          if (newConn?.id) {
            setSelectedConnectionId(newConn.id);
            setConnectionMode('existing');
          }
        } catch (err: unknown) {
          setError((err as Error).message || 'Failed to create connection');
          return;
        }
      } else if (!selectedConnectionId) {
        setError('Please select a connection');
        return;
      }
    }

    if (activeStep === 1) {
      if (!selectedDasSite) {
        setError('Please select a DAS site to map');
        return;
      }
      try {
        const mappingPayload: CreateSiteMappingAttributes = {
          connection_id: selectedConnectionId as number,
          telemetry_site_id: selectedDasSite.id,
          telemetry_site_name: selectedDasSite.name
        };
        if (readiness?.is_site_mapped) {
          await updateSiteMappingMutation.mutateAsync(mappingPayload);
        } else {
          await createSiteMappingMutation.mutateAsync(mappingPayload);
        }
      } catch (err: unknown) {
        setError((err as Error).message || 'Failed to map site');
        return;
      }
    }

    if (activeStep === 2) {
      const mappingsToCreate = Array.from(selectedDevices)
        .filter(deviceId => deviceMappings[deviceId])
        .map(deviceId => ({
          device_id: deviceId,
          telemetry_device_id: deviceMappings[deviceId].telemetry_device_id,
          telemetry_device_name: deviceMappings[deviceId].telemetry_device_name
        }));

      if (mappingsToCreate.length > 0) {
        try {
          await bulkMapDevicesMutation.mutateAsync({ mappings: mappingsToCreate });
        } catch (err: unknown) {
          setError((err as Error).message || 'Failed to map devices');
          return;
        }
      }
    }

    setActiveStep(prev => prev + 1);
  };

  const handleBack = () => {
    setActiveStep(prev => prev - 1);
  };

  const handleDeviceToggle = (deviceId: number) => {
    setSelectedDevices(prev => {
      const next = new Set(prev);
      if (next.has(deviceId)) {
        next.delete(deviceId);
      } else {
        next.add(deviceId);
      }
      return next;
    });
  };

  const handleDeviceMappingChange = (deviceId: number, telemetryDevice: TelemetryDevice | null) => {
    if (telemetryDevice) {
      setDeviceMappings(prev => ({
        ...prev,
        [deviceId]: {
          telemetry_device_id: telemetryDevice.id,
          telemetry_device_name: telemetryDevice.name
        }
      }));
    } else {
      setDeviceMappings(prev => {
        const next = { ...prev };
        delete next[deviceId];
        return next;
      });
    }
  };

  const renderStepContent = () => {
    switch (activeStep) {
      case 0:
        return (
          <Box>
            <Typography variant="body1" gutterBottom>
              Choose an existing connection or create a new one.
            </Typography>
            <SearchableSelect
              options={[
                { label: 'Use Existing Connection', value: 'existing' },
                { label: 'Create New Connection', value: 'new' }
              ]}
              value={connectionMode}
              onChange={val => setConnectionMode(val as 'existing' | 'new')}
              label="Connection Mode"
              disableClearable
              sx={{ mb: 2 }}
            />

            {connectionMode === 'existing' && (
              <SearchableSelect
                options={(connections?.items || []).filter(conn => conn.id != null).map(conn => ({
                  label: `${conn.name} (${conn.provider})`,
                  value: conn.id!
                }))}
                value={selectedConnectionId ?? null}
                onChange={val => setSelectedConnectionId(val ? Number(val) : null)}
                label="Select Connection"
                disabled={isLoadingConnections}
                loading={isLoadingConnections}
                sx={{ mb: 2 }}
              />
            )}

            {connectionMode === 'new' && isLoadingProviders && (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
                <CircularProgress size={24} />
              </Box>
            )}

            {connectionMode === 'new' && !isLoadingProviders && isProvidersError && (
              <Alert severity="warning" sx={{ mb: 2 }}>
                Unable to load available providers. Please try again or contact an administrator.
              </Alert>
            )}

            {connectionMode === 'new' && !isLoadingProviders && !isProvidersError && hasNoProviders && (
              <Alert severity="info" sx={{ mb: 2 }}>
                No telemetry providers have been assigned to this company. Please contact an administrator to configure
                available providers.
              </Alert>
            )}

            {connectionMode === 'new' && !isLoadingProviders && !isProvidersError && !hasNoProviders && (
              <Box>
                <TextField
                  fullWidth
                  label="Connection Name"
                  value={newConnectionForm.name}
                  onChange={e => setNewConnectionForm(prev => ({ ...prev, name: e.target.value }))}
                  sx={{ mb: 2 }}
                />
                <SearchableSelect
                  options={providers}
                  value={newConnectionForm.provider || null}
                  onChange={val => setNewConnectionForm(prev => ({ ...prev, provider: val as string }))}
                  label="Provider"
                  sx={{ mb: 2 }}
                />

                {newConnectionForm.provider === 'KMC' && (
                  <TextField
                    fullWidth
                    label="API Token"
                    type="password"
                    value={newConnectionForm.token}
                    onChange={e => setNewConnectionForm(prev => ({ ...prev, token: e.target.value }))}
                    sx={{ mb: 2 }}
                  />
                )}

                {newConnectionForm.provider === 'Also Energy' && (
                  <>
                    <TextField
                      fullWidth
                      label="Username"
                      value={newConnectionForm.username}
                      onChange={e => setNewConnectionForm(prev => ({ ...prev, username: e.target.value }))}
                      sx={{ mb: 2 }}
                    />
                    <TextField
                      fullWidth
                      label="Password"
                      type="password"
                      value={newConnectionForm.password}
                      onChange={e => setNewConnectionForm(prev => ({ ...prev, password: e.target.value }))}
                      sx={{ mb: 2 }}
                    />
                  </>
                )}

                <Button
                  variant="outlined"
                  onClick={handleTestConnection}
                  disabled={testConnectionMutation.isPending}
                  sx={{ mr: 2 }}
                >
                  {testConnectionMutation.isPending ? <CircularProgress size={20} /> : 'Test Connection'}
                </Button>

                {testResult && (
                  <Alert severity={testResult.success ? 'success' : 'error'} sx={{ mt: 2 }}>
                    {testResult.message}
                  </Alert>
                )}
              </Box>
            )}
          </Box>
        );

      case 1:
        return (
          <Box>
            <Typography variant="body1" gutterBottom>
              Select a DAS site to map to this project.
            </Typography>
            {isLoadingDasSites ? (
              <CircularProgress />
            ) : (
              <SearchableSelect
                options={(dasSites?.items || []).map(site => ({
                  label: site.name,
                  value: String(site.id)
                }))}
                value={selectedDasSite?.id || null}
                onChange={val => {
                  const site = dasSites?.items.find(s => String(s.id) === val);
                  if (site) {
                    setSelectedDasSite({ id: String(site.id), name: site.name });
                  }
                }}
                label="DAS Site"
                sx={{ mb: 2 }}
              />
            )}
          </Box>
        );

      case 2: {
        const unmappedDevices = eligibleDevices?.items.filter(d => !d.is_mapped) || [];

        return (
          <Box>
            <Typography variant="body1" gutterBottom>
              Map your devices to their DAS counterparts. Devices already mapped are shown below.
            </Typography>

            {isLoadingEligibleDevices || isLoadingDasDevices ? (
              <CircularProgress />
            ) : (
              <TableContainer component={Paper} sx={{ maxHeight: 400 }}>
                <Table stickyHeader size="small">
                  <TableHead>
                    <TableRow>
                      <TableCell padding="checkbox">
                        <Checkbox
                          checked={unmappedDevices.length > 0 && selectedDevices.size === unmappedDevices.length}
                          indeterminate={selectedDevices.size > 0 && selectedDevices.size < unmappedDevices.length}
                          onChange={() => {
                            if (selectedDevices.size === unmappedDevices.length) {
                              setSelectedDevices(new Set());
                            } else {
                              setSelectedDevices(new Set(unmappedDevices.map(d => d.id)));
                            }
                          }}
                        />
                      </TableCell>
                      <TableCell>Device</TableCell>
                      <TableCell>Category</TableCell>
                      <TableCell>Status</TableCell>
                      <TableCell>DAS Device</TableCell>
                    </TableRow>
                  </TableHead>
                  <TableBody>
                    {eligibleDevices?.items.map(device => (
                      <TableRow key={device.id}>
                        <TableCell padding="checkbox">
                          {!device.is_mapped && (
                            <Checkbox
                              checked={selectedDevices.has(device.id)}
                              onChange={() => handleDeviceToggle(device.id)}
                            />
                          )}
                        </TableCell>
                        <TableCell>
                          <Typography variant="body2">{device.name}</Typography>
                          <Typography variant="caption" color="text.secondary">
                            {device.serial_number}
                          </Typography>
                        </TableCell>
                        <TableCell>{device.category}</TableCell>
                        <TableCell>
                          {device.is_mapped ? (
                            <Chip size="small" color="success" icon={<CheckCircleIcon />} label="Mapped" />
                          ) : (
                            <Chip size="small" variant="outlined" label="Unmapped" />
                          )}
                        </TableCell>
                        <TableCell>
                          {device.is_mapped ? (
                            <Typography variant="body2">{device.telemetry_device_name}</Typography>
                          ) : (
                            <SearchableSelect
                              options={(dasDevices?.items || []).map(dasDevice => ({
                                label: dasDevice.name,
                                value: dasDevice.id
                              }))}
                              value={deviceMappings[device.id]?.telemetry_device_id || null}
                              onChange={val => {
                                const dasDevice = dasDevices?.items.find(d => d.id === val);
                                handleDeviceMappingChange(device.id, dasDevice || null);
                              }}
                              placeholder="Select DAS Device"
                              size="small"
                            />
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </TableContainer>
            )}
          </Box>
        );
      }

      case 3:
        return (
          <Box>
            <Alert severity="success" sx={{ mb: 2 }}>
              Telemetry setup is complete!
            </Alert>
            <Typography variant="body1" gutterBottom>
              Your project is now connected to your Data Acquisition System. Data is expected every 15 minutes.
            </Typography>
            <Typography variant="h6" sx={{ mt: 2 }}>
              Summary:
            </Typography>
            <ul>
              <li>Connection: {selectedConnection?.name || newConnectionForm.name}</li>
              <li>DAS Site: {selectedDasSite?.name}</li>
              <li>Devices mapped this session: {selectedDevices.size}</li>
            </ul>
            <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
              If data does not appear within 30 minutes, check your DAS provider for any issues.
            </Typography>
          </Box>
        );

      default:
        return null;
    }
  };

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>Telemetry Setup Wizard</DialogTitle>
      <DialogContent>
        <Stepper activeStep={activeStep} sx={{ mb: 3, mt: 1 }}>
          {STEPS.map(label => (
            <Step key={label}>
              <StepLabel>{label}</StepLabel>
            </Step>
          ))}
        </Stepper>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
            {error}
          </Alert>
        )}

        {renderStepContent()}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>Cancel</Button>
        {activeStep > 0 && activeStep < STEPS.length - 1 && <Button onClick={handleBack}>Back</Button>}
        {activeStep < STEPS.length - 1 ? (
          <Button
            variant="contained"
            onClick={handleNext}
            disabled={
              activeStep === 0 && connectionMode === 'new' && (isLoadingProviders || isProvidersError || hasNoProviders)
            }
          >
            Next
          </Button>
        ) : (
          <Button variant="contained" onClick={onClose}>
            Done
          </Button>
        )}
      </DialogActions>
    </Dialog>
  );
};

export default TelemetryWizard;
