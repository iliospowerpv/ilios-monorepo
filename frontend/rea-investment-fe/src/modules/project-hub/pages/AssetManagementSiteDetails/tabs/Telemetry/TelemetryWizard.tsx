import React, { useState, useMemo, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { useAuth } from '../../../../../../contexts/auth/auth';
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
import Radio from '@mui/material/Radio';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';

import { ApiClient } from '../../../../../../api';
import type { SiteDetailedInfo } from '../../../../../../api';
import { useExternalSites } from '../../../../../../hooks/telemetryV2';
import type {
  TelemetryReadinessResponse,
  Connection,
  TelemetryDevice,
  DeviceMapping
} from '../../../../../../api/connections';
import type { SiteMappingSavePayload } from '../../../../../../types/telemetryV2';
import { ConfirmationModal } from '../../../../../../components/modals/ConfirmationModal/ConfirmationModal';
import { EditConnectionDialog, ConnectionToEdit } from './EditConnectionDialog';

const STEPS = ['Connection', 'Site Mapping', 'Device Mapping', 'Confirm'];

interface TelemetryWizardProps {
  open: boolean;
  onClose: () => void;
  siteDetails: SiteDetailedInfo;
  readiness?: TelemetryReadinessResponse;
}

export const TelemetryWizard: React.FC<TelemetryWizardProps> = ({ open, onClose, siteDetails, readiness }) => {
  const queryClient = useQueryClient();
  const navigate = useNavigate();
  const { user } = useAuth();
  const canEditSettings = Boolean(user?.role?.permissions?.settings?.edit);
  const [activeStep, setActiveStep] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const [connectionMode, setConnectionMode] = useState<'existing' | 'new'>(
    readiness?.is_connected || !canEditSettings ? 'existing' : 'new'
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

  const [editingConnection, setEditingConnection] = useState<ConnectionToEdit | null>(null);
  const [deletingConnection, setDeletingConnection] = useState<ConnectionToEdit | null>(null);

  const companyId = siteDetails.company?.id;

  useEffect(() => {
    if (open) {
      setActiveStep(0);
      setError(null);
      setConnectionMode(readiness?.is_connected || !canEditSettings ? 'existing' : 'new');
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
      setEditingConnection(null);
      setDeletingConnection(null);
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

  const { data: availableConnections, isLoading: isLoadingConnections } = useQuery({
    queryKey: ['available-connections', companyId],
    queryFn: () => ApiClient.connections.getAvailableConnections(companyId as number),
    enabled: !!companyId && open
  });

  const allConnections = useMemo(
    () => [
      ...(availableConnections?.company_connections ?? []),
      ...(availableConnections?.portfolio_connections ?? [])
    ],
    [availableConnections]
  );

  const selectedConnection = useMemo(() => {
    if (connectionMode === 'existing' && selectedConnectionId) {
      return allConnections.find(c => c.id === selectedConnectionId);
    }
    return null;
  }, [connectionMode, selectedConnectionId, allConnections]);

  const {
    data: dasSites,
    isLoading: isLoadingDasSites,
    isError: isDasSitesError,
    error: dasSitesError
  } = useExternalSites(selectedConnectionId, {
    enabled: !!selectedConnectionId && activeStep >= 1,
    retry: 1
  });

  const {
    data: dasDevices,
    isLoading: isLoadingDasDevices,
    isError: isDasDevicesError,
    error: dasDevicesError
  } = useQuery({
    queryKey: ['das-devices', siteDetails.id],
    queryFn: () => ApiClient.connections.getTelemetryDevices(siteDetails.id),
    enabled: !!siteDetails.id && !!selectedDasSite && activeStep >= 2,
    retry: 1
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
      queryClient.invalidateQueries({ queryKey: ['available-connections', companyId] });
    }
  });

  const deleteConnectionMutation = useMutation({
    mutationFn: (connectionId: number) => ApiClient.connections.deleteConnection(companyId as number, connectionId),
    onSuccess: (_data, connectionId) => {
      queryClient.invalidateQueries({ queryKey: ['connections', companyId] });
      queryClient.invalidateQueries({ queryKey: ['available-connections', companyId] });
      if (selectedConnectionId === connectionId) {
        setSelectedConnectionId(null);
      }
      setDeletingConnection(null);
    },
    onError: (err: unknown) => {
      const message =
        err instanceof AxiosError
          ? err.response?.data?.message || err.message
          : (err as Error)?.message || 'Failed to delete connection';
      setError(message);
      setDeletingConnection(null);
    }
  });

  // V2 (DB-only) site mapping save. Upserts the mapping in the iliOS DB and
  // does not require a live provider call or any GCP/Firestore sync.
  const saveSiteMappingMutation = useMutation({
    mutationFn: (payload: SiteMappingSavePayload) => ApiClient.telemetryV2.saveSiteMapping(siteDetails.id, payload),
    onSuccess: () => {
      // Refresh the readiness strip so the new mapping is reflected immediately.
      queryClient.invalidateQueries({ queryKey: ['telemetry-readiness', siteDetails.id] });
    }
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
        if (!canEditSettings) {
          setError('You do not have permission to create connections. Contact a portfolio administrator.');
          return;
        }
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
          const refreshedConnections = await ApiClient.connections.getAvailableConnections(companyId as number);
          const newConn = refreshedConnections.company_connections.find(c => c.name === newConnectionForm.name);
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
      if (!selectedConnectionId) {
        setError('Please select a connection before mapping a site');
        return;
      }
      try {
        // Upsert handles both first-time mapping and re-mapping, so there is no
        // need to branch on readiness.is_site_mapped.
        await saveSiteMappingMutation.mutateAsync({
          provider_account_id: selectedConnectionId,
          external_site_id: selectedDasSite.id
        });
      } catch (err: unknown) {
        setError(getApiErrorMessage(err, 'Failed to map site'));
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

  const getApiErrorMessage = (err: unknown, fallback: string): string => {
    if (err instanceof AxiosError) {
      const detail = err.response?.data?.detail;
      const message = err.response?.data?.message;
      if (typeof detail === 'string') return detail;
      if (typeof message === 'string') return message;
      return err.message || fallback;
    }
    return (err as Error)?.message || fallback;
  };

  const renderStepContent = () => {
    switch (activeStep) {
      case 0:
        return (
          <Box>
            <Typography variant="body1" gutterBottom>
              {canEditSettings
                ? 'Choose an existing connection or create a new one.'
                : 'Choose a saved connection. Contact a portfolio administrator to add or change connections.'}
            </Typography>
            {canEditSettings && (
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
            )}

            {connectionMode === 'existing' && (
              <Box sx={{ mb: 2 }}>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  Select a saved connection:
                </Typography>
                {isLoadingConnections ? (
                  <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
                    <CircularProgress size={24} />
                  </Box>
                ) : (
                  <TableContainer component={Paper} variant="outlined">
                    <Table size="small">
                      <TableBody>
                        {allConnections.length === 0 && (
                          <TableRow>
                            <TableCell>
                              <Typography variant="body2" color="text.secondary" align="center">
                                {canEditSettings
                                  ? 'No saved connections yet. Switch to "Create New Connection" to add one.'
                                  : 'No saved connections yet. Contact a portfolio administrator to add one.'}
                              </Typography>
                            </TableCell>
                          </TableRow>
                        )}
                        {allConnections.map(conn => {
                          const isOwned = conn.company_id === companyId;
                          const isSelected = selectedConnectionId === conn.id;
                          return (
                            <TableRow
                              key={conn.id}
                              hover
                              selected={isSelected}
                              onClick={() => setSelectedConnectionId(conn.id)}
                              sx={{ cursor: 'pointer' }}
                            >
                              <TableCell padding="checkbox">
                                <Radio
                                  checked={isSelected}
                                  onChange={() => setSelectedConnectionId(conn.id)}
                                  inputProps={{ 'aria-label': `Select ${conn.name}` }}
                                />
                              </TableCell>
                              <TableCell>
                                <Typography variant="body2">{conn.name}</Typography>
                                <Typography variant="caption" color="text.secondary">
                                  {conn.provider}
                                  {!isOwned && conn.company_name && ` • Shared from ${conn.company_name}`}
                                  {isOwned && conn.owner_type === 'portfolio' && ' • Shared with portfolio'}
                                </Typography>
                              </TableCell>
                              <TableCell align="right" sx={{ width: 110 }}>
                                {canEditSettings && isOwned && (
                                  <>
                                    <Tooltip title="Edit connection">
                                      <span>
                                        <IconButton
                                          size="small"
                                          onClick={e => {
                                            e.stopPropagation();
                                            setEditingConnection({
                                              id: conn.id,
                                              name: conn.name,
                                              provider: conn.provider,
                                              owner_type: conn.owner_type
                                            });
                                          }}
                                          aria-label={`Edit ${conn.name}`}
                                        >
                                          <EditIcon fontSize="small" />
                                        </IconButton>
                                      </span>
                                    </Tooltip>
                                    <Tooltip title="Delete connection">
                                      <span>
                                        <IconButton
                                          size="small"
                                          onClick={e => {
                                            e.stopPropagation();
                                            setDeletingConnection({
                                              id: conn.id,
                                              name: conn.name,
                                              provider: conn.provider,
                                              owner_type: conn.owner_type
                                            });
                                          }}
                                          aria-label={`Delete ${conn.name}`}
                                        >
                                          <DeleteIcon fontSize="small" />
                                        </IconButton>
                                      </span>
                                    </Tooltip>
                                  </>
                                )}
                              </TableCell>
                            </TableRow>
                          );
                        })}
                      </TableBody>
                    </Table>
                  </TableContainer>
                )}
              </Box>
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
              <Alert
                severity="info"
                sx={{ mb: 2 }}
                action={
                  canEditSettings && companyId ? (
                    <Button
                      color="inherit"
                      size="small"
                      onClick={() => {
                        onClose();
                        navigate(`/portfolio-admin/companies/${companyId}`);
                      }}
                    >
                      Configure Providers
                    </Button>
                  ) : undefined
                }
              >
                {canEditSettings ? (
                  <>
                    No telemetry providers are licensed for this company yet. Configure providers in Portfolio Admin →
                    Company → Telemetry Providers, then return here to create a connection.
                  </>
                ) : (
                  <>
                    No telemetry providers are licensed for this company yet. Please contact a portfolio administrator
                    to enable a DAS provider (KMC or Also Energy) before connections can be created.
                  </>
                )}
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
            ) : isDasSitesError ? (
              <Alert severity="error" sx={{ mb: 2 }}>
                {getApiErrorMessage(dasSitesError, 'Unable to load sites for this account. Please try again.')}
              </Alert>
            ) : (dasSites?.items?.length || 0) === 0 ? (
              <Alert severity="info" sx={{ mb: 2 }}>
                No sites have been synced for this account yet. Sync sites for this provider account in the company
                telemetry settings, then return here.
              </Alert>
            ) : (
              <SearchableSelect
                options={(dasSites?.items || []).map(site => ({
                  label: site.external_site_name || site.external_site_id,
                  value: site.external_site_id
                }))}
                value={selectedDasSite?.id || null}
                onChange={val => {
                  const site = dasSites?.items.find(s => s.external_site_id === val);
                  if (site) {
                    setSelectedDasSite({
                      id: site.external_site_id,
                      name: site.external_site_name || site.external_site_id
                    });
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
            ) : isDasDevicesError ? (
              <Alert severity="error" sx={{ mb: 2 }}>
                {getApiErrorMessage(
                  dasDevicesError,
                  'Unable to fetch devices from the DAS provider. Check the connection credentials and try again.'
                )}
              </Alert>
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

      {editingConnection && companyId && (
        <EditConnectionDialog
          open={!!editingConnection}
          onClose={() => setEditingConnection(null)}
          companyId={companyId}
          connection={editingConnection}
        />
      )}

      <ConfirmationModal
        open={!!deletingConnection}
        confirmationTitle={deletingConnection ? `Delete "${deletingConnection.name}"?` : 'Delete Connection?'}
        confirmationMessage="This action cannot be undone. If this connection is currently used by any site mappings, deletion will be blocked."
        confirmationDisabled={deleteConnectionMutation.isPending}
        onClose={() => setDeletingConnection(null)}
        onConfirm={() => {
          if (deletingConnection) {
            deleteConnectionMutation.mutate(deletingConnection.id);
          }
        }}
      />
    </Dialog>
  );
};

export default TelemetryWizard;
