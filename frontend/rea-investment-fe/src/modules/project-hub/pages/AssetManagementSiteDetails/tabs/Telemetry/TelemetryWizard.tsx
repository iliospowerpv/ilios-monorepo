import React, { useState, useMemo, useEffect, useRef } from 'react';
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
import RefreshIcon from '@mui/icons-material/Refresh';

import { ApiClient } from '../../../../../../api';
import type { SiteDetailedInfo } from '../../../../../../api';
import { useExternalSites, useExternalDevices } from '../../../../../../hooks/telemetryV2';
import type { TelemetryReadinessResponse, Connection } from '../../../../../../api/connections';
import type { SiteMappingSavePayload, DeviceMappingBulkPayload } from '../../../../../../types/telemetryV2';
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

  // Tracks which (connection, site) pairs we have already auto-synced devices
  // for this session, so an empty cache triggers at most one automatic live
  // sync. Manual "Refresh" is always allowed.
  const autoSyncedDevicesRef = useRef<Set<string>>(new Set());

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
      autoSyncedDevicesRef.current = new Set();
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

  // V2 (DB-backed) device cache read. This is cache-only: opening the Device
  // Mapping step never makes a live provider call, so it cannot raise the
  // "Network Error" the legacy v1 GET .../devices produced. A live refresh is
  // performed only via an explicit/auto sync (see syncDevicesMutation below).
  const {
    data: dasDevices,
    isLoading: isLoadingDasDevices,
    isFetching: isFetchingDasDevices,
    isError: isDasDevicesError,
    error: dasDevicesError,
    refetch: refetchDasDevices
  } = useExternalDevices(selectedConnectionId, selectedDasSite?.id ?? null, {
    enabled: !!selectedConnectionId && !!selectedDasSite && activeStep >= 2,
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

  // V2 explicit device sync. Makes a single live provider call and refreshes
  // the DB-backed device cache. On failure the backend never wipes the existing
  // cache or mappings; we simply surface the error and re-read the cache.
  const syncDevicesMutation = useMutation({
    mutationFn: () => {
      if (!selectedConnectionId || !selectedDasSite) {
        return Promise.reject(new Error('Select a connection and DAS site first'));
      }
      return ApiClient.telemetryV2.syncProviderAccountDevices(selectedConnectionId, selectedDasSite.id);
    },
    onSuccess: () => {
      refetchDasDevices();
    }
  });

  // V2 (DB-only) device mapping save. Persists iliOS device -> external device
  // pairings directly in the iliOS DB; no live provider call, no GCP/Firestore.
  const saveDeviceMappingsMutation = useMutation({
    mutationFn: (payload: DeviceMappingBulkPayload) =>
      ApiClient.telemetryV2.saveDeviceMappings(siteDetails.id, payload),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['eligible-devices', siteDetails.id] });
      queryClient.invalidateQueries({ queryKey: ['telemetry-readiness', siteDetails.id] });
    }
  });

  // Auto-trigger a single live sync only when the device cache is empty for the
  // selected (connection, site). If cached devices already exist, opening the
  // step never makes a live call.
  useEffect(() => {
    if (activeStep < 2 || !selectedConnectionId || !selectedDasSite) return;
    if (isLoadingDasDevices || isFetchingDasDevices) return;
    if (isDasDevicesError || !dasDevices) return;
    const key = `${selectedConnectionId}:${selectedDasSite.id}`;
    if (dasDevices.items.length === 0 && !autoSyncedDevicesRef.current.has(key) && !syncDevicesMutation.isPending) {
      autoSyncedDevicesRef.current.add(key);
      syncDevicesMutation.mutate();
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [
    activeStep,
    selectedConnectionId,
    selectedDasSite,
    dasDevices,
    isLoadingDasDevices,
    isFetchingDasDevices,
    isDasDevicesError
  ]);

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
          external_device_id: deviceMappings[deviceId].telemetry_device_id
        }));

      // Guard against silently advancing with unsaved work: if DAS devices were
      // picked but every row ended up unchecked (e.g. the header select-all was
      // cleared after picking), surface an error instead of skipping the save.
      if (mappingsToCreate.length === 0 && Object.keys(deviceMappings).length > 0) {
        setError(
          'You picked DAS devices but no rows are checked. Check the rows you want to map (or clear the DAS device selections) before continuing.'
        );
        return;
      }

      if (mappingsToCreate.length > 0) {
        if (!selectedConnectionId || !selectedDasSite) {
          setError('Please select a connection and DAS site before mapping devices');
          return;
        }
        try {
          // V2 (DB-only) save. Names are resolved server-side from the synced
          // device cache, so only the device id pairs are sent.
          const result = await saveDeviceMappingsMutation.mutateAsync({
            provider_account_id: selectedConnectionId,
            external_site_id: selectedDasSite.id,
            mappings: mappingsToCreate
          });
          if (result.failed_count > 0) {
            setError(
              result.errors?.length
                ? result.errors.join('; ')
                : `${result.failed_count} device mapping(s) could not be saved.`
            );
            return;
          }
        } catch (err: unknown) {
          setError(getApiErrorMessage(err, 'Failed to map devices'));
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

  const handleDeviceMappingChange = (deviceId: number, selection: { id: string; name: string } | null) => {
    if (selection) {
      setDeviceMappings(prev => ({
        ...prev,
        [deviceId]: {
          telemetry_device_id: selection.id,
          telemetry_device_name: selection.name
        }
      }));
      // Picking a DAS device is the mapping intent: auto-select the row so the
      // mapping is actually persisted on "Next" (the save payload is the
      // intersection of selectedDevices and deviceMappings).
      setSelectedDevices(prev => {
        const next = new Set(prev);
        next.add(deviceId);
        return next;
      });
    } else {
      setDeviceMappings(prev => {
        const next = { ...prev };
        delete next[deviceId];
        return next;
      });
      // Clearing the DAS device unmaps the row; drop it from the selection too.
      setSelectedDevices(prev => {
        const next = new Set(prev);
        next.delete(deviceId);
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
        const dasDeviceItems = dasDevices?.items || [];
        const eligibleItems = eligibleDevices?.items || [];
        const isSyncingDevices = syncDevicesMutation.isPending;
        const devicesLoading = isLoadingEligibleDevices || isLoadingDasDevices || isSyncingDevices;
        // The cache read is 200 even when the provider is down; a failed *sync*
        // is reported either as a thrown error or as a 200 with an error field.
        const syncErrorMessage =
          (syncDevicesMutation.isError ? getApiErrorMessage(syncDevicesMutation.error, 'Device sync failed') : null) ||
          syncDevicesMutation.data?.error ||
          null;

        return (
          <Box>
            <Box sx={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 2 }}>
              <Typography variant="body1" gutterBottom>
                Map your devices to their DAS counterparts. Devices already mapped are shown below.
              </Typography>
              <Tooltip title="Refresh the device list from the provider">
                <span>
                  <Button
                    size="small"
                    startIcon={isSyncingDevices ? <CircularProgress size={16} /> : <RefreshIcon />}
                    onClick={() => syncDevicesMutation.mutate()}
                    disabled={isSyncingDevices || !selectedConnectionId || !selectedDasSite}
                  >
                    {isSyncingDevices ? 'Refreshing…' : 'Refresh'}
                  </Button>
                </span>
              </Tooltip>
            </Box>

            {/* A failed cache read (e.g. site no longer synced) -- still never wipes cache. */}
            {isDasDevicesError && (
              <Alert severity="error" sx={{ mb: 2 }}>
                {getApiErrorMessage(
                  dasDevicesError,
                  'Unable to read the synced device cache. Try Refresh to sync devices from the provider.'
                )}
              </Alert>
            )}

            {/* A failed live sync is non-fatal: any previously cached devices remain usable. */}
            {syncErrorMessage && (
              <Alert severity="warning" sx={{ mb: 2 }}>
                {`Could not refresh devices from the provider: ${syncErrorMessage}. `}
                {dasDeviceItems.length > 0
                  ? 'Showing the last synced devices.'
                  : 'No previously synced devices are available.'}
              </Alert>
            )}

            {devicesLoading ? (
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, py: 3 }}>
                <CircularProgress size={24} />
                <Typography variant="body2" color="text.secondary">
                  {isSyncingDevices ? 'Syncing devices from the provider…' : 'Loading devices…'}
                </Typography>
              </Box>
            ) : !isDasDevicesError && dasDeviceItems.length === 0 ? (
              <Alert severity="info" sx={{ mb: 2 }}>
                No devices are available for this DAS site yet. Use Refresh to pull the latest device list from the
                provider.
              </Alert>
            ) : eligibleItems.length === 0 ? (
              <Alert severity="info" sx={{ mb: 2 }}>
                This project has no telemetry-eligible devices to map yet. Add devices in the Inverter, Module, or
                Weather Station category to this project, then return here to map them
                {dasDeviceItems.length > 0
                  ? ` to the ${dasDeviceItems.length} DAS device${
                      dasDeviceItems.length === 1 ? '' : 's'
                    } already synced for this site.`
                  : '.'}
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
                              options={dasDeviceItems.map(dasDevice => ({
                                label: dasDevice.external_device_name || dasDevice.external_device_id,
                                value: dasDevice.external_device_id
                              }))}
                              value={deviceMappings[device.id]?.telemetry_device_id || null}
                              onChange={val => {
                                const dasDevice = dasDeviceItems.find(d => d.external_device_id === val);
                                handleDeviceMappingChange(
                                  device.id,
                                  dasDevice
                                    ? {
                                        id: dasDevice.external_device_id,
                                        name: dasDevice.external_device_name || dasDevice.external_device_id
                                      }
                                    : null
                                );
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
