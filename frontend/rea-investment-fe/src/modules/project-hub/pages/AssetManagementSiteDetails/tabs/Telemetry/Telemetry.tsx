import React, { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Chip from '@mui/material/Chip';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import ErrorIcon from '@mui/icons-material/Error';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import SettingsInputAntennaIcon from '@mui/icons-material/SettingsInputAntenna';
import ScheduleIcon from '@mui/icons-material/Schedule';

import { ApiClient } from '../../../../../../api';
import type {
  TelemetryHealthStatus,
  TelemetryReadinessResponse,
  TelemetryHealthResponse
} from '../../../../../../api/connections';
import { useTelemetryAdminPermission } from '../../../../../../hooks/useTelemetryAdminPermission';
import { useTelemetryCooldown } from '../../../../../../hooks/useTelemetryCooldown';
import { AssetManagementSiteDetailsTabProps } from '../types';
import { TelemetryWizard } from './TelemetryWizard';
import { RefreshTelemetryButton } from './RefreshTelemetryButton';
import { ScheduleDialog } from './ScheduleDialog';
import { EligibilityDiagnosticsPanel } from './EligibilityDiagnosticsPanel';
import { WeatherSemanticsPanel } from './WeatherSemanticsPanel';

const getStatusColor = (status: TelemetryHealthStatus): 'success' | 'warning' | 'error' | 'default' => {
  switch (status) {
    case 'HEALTHY':
      return 'success';
    case 'WARN':
      return 'warning';
    case 'ERROR':
      return 'error';
    case 'NO_DATA':
    case 'NOT_CONFIGURED':
    default:
      return 'default';
  }
};

const getStatusIcon = (status: TelemetryHealthStatus) => {
  switch (status) {
    case 'HEALTHY':
      return <CheckCircleIcon fontSize="small" />;
    case 'WARN':
      return <WarningIcon fontSize="small" />;
    case 'ERROR':
      return <ErrorIcon fontSize="small" />;
    case 'NO_DATA':
    case 'NOT_CONFIGURED':
    default:
      return <HelpOutlineIcon fontSize="small" />;
  }
};

const getStatusLabel = (status: TelemetryHealthStatus, mappedDeviceCount: number): string => {
  switch (status) {
    case 'HEALTHY':
      return 'Healthy';
    case 'WARN':
      return 'Warning';
    case 'ERROR':
      return 'Error';
    case 'NO_DATA':
      return mappedDeviceCount === 0 ? 'Mapped, No Devices' : 'No Data Yet';
    case 'NOT_CONFIGURED':
      return 'Not Configured';
    default:
      return status;
  }
};

const formatTimestamp = (timestamp: string | null): string => {
  if (!timestamp) return 'Never';
  const date = new Date(timestamp);
  return date.toLocaleString();
};

interface ReadinessStripProps {
  readiness: TelemetryReadinessResponse;
}

const ReadinessStrip: React.FC<ReadinessStripProps> = ({ readiness }) => {
  const steps = [
    { label: 'Connected', done: readiness.is_connected },
    { label: 'Site Mapped', done: readiness.is_site_mapped },
    { label: 'Devices Mapped', done: readiness.is_devices_mapped },
    { label: 'Data Flowing', done: readiness.is_data_flowing }
  ];

  return (
    <Paper sx={{ p: 2, mb: 2 }}>
      <Typography variant="h6" gutterBottom>
        Telemetry Readiness
      </Typography>
      <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap' }}>
        {steps.map((step, index) => (
          <Chip
            key={step.label}
            label={`${index + 1}. ${step.label}`}
            color={step.done ? 'success' : 'default'}
            icon={step.done ? <CheckCircleIcon /> : undefined}
            variant={step.done ? 'filled' : 'outlined'}
          />
        ))}
      </Box>
      {readiness.is_connected && (
        <Box sx={{ mt: 2 }}>
          <Typography variant="body2" color="text.secondary">
            Connection: {readiness.connection_name} ({readiness.provider})
          </Typography>
          {readiness.is_site_mapped && (
            <Typography variant="body2" color="text.secondary">
              Mapped to: {readiness.telemetry_site_name}
            </Typography>
          )}
          <Typography variant="body2" color="text.secondary">
            Devices: {readiness.mapped_device_count} / {readiness.total_eligible_device_count} mapped
          </Typography>
        </Box>
      )}
    </Paper>
  );
};

interface HealthStripProps {
  health: TelemetryHealthResponse;
}

const HealthStrip: React.FC<HealthStripProps> = ({ health }) => {
  const statusLabel = getStatusLabel(health.status, health.mapped_device_count);

  if (health.status === 'NOT_CONFIGURED') {
    return (
      <Paper sx={{ p: 2, mb: 2 }}>
        <Typography variant="h6" gutterBottom>
          Data Health
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <Chip label={statusLabel} color="default" icon={getStatusIcon(health.status)} variant="outlined" />
          <Typography variant="body2" color="text.secondary">
            Connect to a DAS provider to start receiving telemetry data
          </Typography>
        </Box>
      </Paper>
    );
  }

  return (
    <Paper sx={{ p: 2, mb: 2 }}>
      <Typography variant="h6" gutterBottom>
        Data Health
      </Typography>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, mb: 1 }}>
        <Chip label={statusLabel} color={getStatusColor(health.status)} icon={getStatusIcon(health.status)} />
        <Typography variant="body2" color="text.secondary">
          Last data: {formatTimestamp(health.last_data_at)}
        </Typography>
        {health.data_delay_minutes !== null && (
          <Typography variant="body2" color="text.secondary">
            Delay: {health.data_delay_minutes} minutes
          </Typography>
        )}
      </Box>
      {health.last_error && (
        <Alert severity="error" sx={{ mt: 1 }}>
          {health.last_error}
        </Alert>
      )}
      <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
        {health.mapped_device_count} device(s) mapped | Expected interval: {health.expected_interval_label}
      </Typography>
    </Paper>
  );
};

export const Telemetry: React.FC<AssetManagementSiteDetailsTabProps> = ({ siteDetails }) => {
  const [wizardOpen, setWizardOpen] = useState(false);
  const [scheduleOpen, setScheduleOpen] = useState(false);
  const cooldown = useTelemetryCooldown();

  const {
    data: readiness,
    isLoading: isLoadingReadiness,
    refetch: refetchReadiness
  } = useQuery({
    queryKey: ['telemetry-readiness', siteDetails.id],
    queryFn: () => ApiClient.connections.getTelemetryReadiness(siteDetails.id),
    enabled: !!siteDetails.id
  });

  const {
    data: health,
    isLoading: isLoadingHealth,
    refetch: refetchHealth
  } = useQuery({
    queryKey: ['telemetry-health', siteDetails.id],
    queryFn: () => ApiClient.connections.getTelemetryHealth(siteDetails.id),
    enabled: !!siteDetails.id
  });

  const isTelemetryAdmin = useTelemetryAdminPermission();

  const handleWizardClose = () => {
    setWizardOpen(false);
    refetchReadiness();
    refetchHealth();
  };

  if (isLoadingReadiness || isLoadingHealth) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
        <CircularProgress />
      </Box>
    );
  }

  const isConfigured = readiness?.is_connected && readiness?.is_site_mapped;

  // The refresh control appears whenever a telemetry provider is connected, but
  // is disabled with an explicit reason until the project is fully ready: it must
  // be mapped to a telemetry site and have verified credentials before a manual
  // refresh can re-present those credentials to the provider.
  const isConnected = Boolean(readiness?.is_connected);
  let refreshDisabledReason: string | undefined;
  if (!readiness?.is_site_mapped) {
    refreshDisabledReason = 'Map this project to a telemetry site before refreshing.';
  } else if (readiness?.credential_status && readiness.credential_status !== 'verified') {
    refreshDisabledReason = "Verify the telemetry connection's credentials before refreshing.";
  }

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 3 }}>
        <Typography variant="h5">
          <SettingsInputAntennaIcon sx={{ mr: 1, verticalAlign: 'middle' }} />
          Telemetry
        </Typography>
        <Box sx={{ display: 'flex', alignItems: 'flex-start', gap: 1 }}>
          {isConnected && (
            <RefreshTelemetryButton
              siteId={siteDetails.id}
              disabledReason={refreshDisabledReason}
              isCoolingDown={cooldown.isCoolingDown}
              cooldownSecondsRemaining={cooldown.secondsRemaining}
              onCooldown={cooldown.startCooldown}
              onRefreshed={() => {
                refetchReadiness();
                refetchHealth();
              }}
            />
          )}
          {isConfigured && isTelemetryAdmin && (
            <Button
              variant="outlined"
              color="primary"
              startIcon={<ScheduleIcon />}
              onClick={() => setScheduleOpen(true)}
            >
              Automatic Refresh Schedule
            </Button>
          )}
          <Button variant="contained" color="primary" onClick={() => setWizardOpen(true)}>
            {isConfigured ? 'Map Telemetry' : 'Connect Telemetry'}
          </Button>
        </Box>
      </Box>

      {readiness && <ReadinessStrip readiness={readiness} />}

      {health && <HealthStrip health={health} />}

      {isConfigured && <EligibilityDiagnosticsPanel siteId={siteDetails.id} />}

      {isConfigured && <WeatherSemanticsPanel siteId={siteDetails.id} />}

      {!isConfigured && (
        <Alert severity="info" sx={{ mt: 2 }}>
          <Typography variant="body2">
            This project is not yet connected to a Data Acquisition System (DAS). Click &quot;Connect Telemetry&quot; to
            set up real-time performance monitoring.
          </Typography>
        </Alert>
      )}

      {isConfigured && health?.status === 'NO_DATA' && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          <Typography variant="body2" fontWeight="bold" gutterBottom>
            Troubleshooting Steps:
          </Typography>
          <ul style={{ margin: 0, paddingLeft: 20 }}>
            <li>Data is expected every 15 minutes from your DAS provider</li>
            <li>Verify your DAS connection credentials are still valid</li>
            <li>Check that devices are correctly mapped to their DAS identifiers</li>
            <li>Contact your DAS provider if the issue persists</li>
          </ul>
        </Alert>
      )}

      <TelemetryWizard open={wizardOpen} onClose={handleWizardClose} siteDetails={siteDetails} readiness={readiness} />

      {isConfigured && isTelemetryAdmin && (
        <ScheduleDialog
          open={scheduleOpen}
          onClose={() => setScheduleOpen(false)}
          siteId={siteDetails.id}
          cooldown={cooldown}
        />
      )}
    </Box>
  );
};

export default Telemetry;
