import React from 'react';
import { useQuery } from '@tanstack/react-query';
import {
  Box,
  Typography,
  Paper,
  Card,
  CardContent,
  CardHeader,
  Button,
  Chip,
  Alert,
  AlertTitle,
  CircularProgress,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Stack,
  Tooltip,
  Divider
} from '@mui/material';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import RefreshIcon from '@mui/icons-material/Refresh';
import HealthAndSafetyIcon from '@mui/icons-material/HealthAndSafety';

import { ApiClient, type ServiceStatus } from '../../../../api';

const formatTimestamp = (value: string | null): string => {
  if (!value) return '—';
  const parsed = new Date(value);
  return Number.isNaN(parsed.getTime()) ? '—' : parsed.toLocaleString();
};

const ReachabilityChip: React.FC<{ service: ServiceStatus }> = ({ service }) => {
  if (service.reachable === true) {
    return <Chip size="small" color="success" icon={<CheckCircleIcon />} label="Reachable" />;
  }
  if (service.reachable === false) {
    return <Chip size="small" color="error" icon={<ErrorIcon />} label="Unreachable" />;
  }
  return (
    <Tooltip title="No safe probe is available for this service, so reachability is not checked.">
      <Chip size="small" variant="outlined" icon={<HelpOutlineIcon />} label="Not probed" />
    </Tooltip>
  );
};

const ConfiguredChip: React.FC<{ service: ServiceStatus }> = ({ service }) => {
  if (service.configured) {
    return <Chip size="small" color="success" variant="outlined" label="Configured" />;
  }
  return (
    <Chip
      size="small"
      color={service.required ? 'error' : 'warning'}
      variant="outlined"
      label={service.required ? 'Missing (required)' : 'Not configured'}
    />
  );
};

const HealthChecksPage: React.FC = () => {
  const { data, isLoading, isFetching, error, refetch } = useQuery({
    queryKey: ['settings', 'service-health'],
    queryFn: () => ApiClient.systemSettings.getServiceHealth()
  });

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="50vh">
        <CircularProgress />
        <Typography variant="body1" sx={{ ml: 2 }}>
          Checking third-party services...
        </Typography>
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ m: 2 }}>
        <AlertTitle>Error</AlertTitle>
        Failed to load service status. You may not have permission to view this page.
      </Alert>
    );
  }

  const services = data?.services ?? [];

  return (
    <Box sx={{ p: 3 }}>
      <Card sx={{ mb: 3 }}>
        <CardHeader
          avatar={<HealthAndSafetyIcon color="primary" fontSize="large" />}
          title={
            <Typography variant="h5" fontWeight="medium">
              Third-Party Services
            </Typography>
          }
          subheader="Configuration and reachability of the external and infrastructure services this platform depends on."
          action={
            <Button variant="outlined" startIcon={<RefreshIcon />} onClick={() => refetch()} disabled={isFetching}>
              {isFetching ? 'Refreshing...' : 'Refresh'}
            </Button>
          }
        />
        <Divider />
        <CardContent>
          <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
            <Chip label={`${data?.total_count ?? 0} services`} variant="outlined" />
            <Chip label={`${data?.configured_count ?? 0} configured`} color="success" variant="outlined" />
            <Chip label={`${data?.probed_count ?? 0} actively probed`} color="primary" variant="outlined" />
          </Stack>
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1.5 }}>
            Generated {formatTimestamp(data?.generated_at ?? null)}. Only infrastructure services with a safe,
            side-effect-free probe (database, cache, object storage) report live reachability; external or billable
            providers report configuration status only. No secret values are ever shown.
          </Typography>
        </CardContent>
      </Card>

      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Service</TableCell>
              <TableCell>Category</TableCell>
              <TableCell>Requirement</TableCell>
              <TableCell>Configuration</TableCell>
              <TableCell>Reachability</TableCell>
              <TableCell>Last checked</TableCell>
              <TableCell>Configuration source</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {services.map(service => (
              <TableRow key={service.key} hover>
                <TableCell sx={{ maxWidth: 280 }}>
                  <Typography variant="body2" fontWeight="medium">
                    {service.name}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {service.purpose}
                  </Typography>
                  {service.notes && (
                    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
                      {service.notes}
                    </Typography>
                  )}
                  {service.error_summary && (
                    <Typography variant="caption" color="error" sx={{ display: 'block', mt: 0.5 }}>
                      {service.error_summary}
                    </Typography>
                  )}
                </TableCell>
                <TableCell>
                  <Chip size="small" label={service.category} variant="outlined" />
                </TableCell>
                <TableCell>
                  <Chip
                    size="small"
                    label={service.required ? 'Required' : 'Optional'}
                    color={service.required ? 'default' : 'default'}
                    variant="outlined"
                  />
                </TableCell>
                <TableCell>
                  <ConfiguredChip service={service} />
                </TableCell>
                <TableCell>
                  <ReachabilityChip service={service} />
                </TableCell>
                <TableCell>
                  <Typography variant="caption" color="text.secondary">
                    {formatTimestamp(service.last_checked)}
                  </Typography>
                </TableCell>
                <TableCell sx={{ maxWidth: 220 }}>
                  {service.config_source.length === 0 ? (
                    <Typography variant="caption" color="text.secondary">
                      —
                    </Typography>
                  ) : (
                    <Stack direction="row" spacing={0.5} flexWrap="wrap" useFlexGap>
                      {service.config_source.map(source => (
                        <Chip
                          key={source}
                          size="small"
                          label={source}
                          variant="outlined"
                          sx={{ fontFamily: 'monospace', fontSize: 11 }}
                        />
                      ))}
                    </Stack>
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default HealthChecksPage;
