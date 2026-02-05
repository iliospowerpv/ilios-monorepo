import React from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import Typography from '@mui/material/Typography';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import Skeleton from '@mui/material/Skeleton';
import Alert from '@mui/material/Alert';
import Tooltip from '@mui/material/Tooltip';
import CircularProgress from '@mui/material/CircularProgress';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import ErrorIcon from '@mui/icons-material/Error';
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty';
import SyncIcon from '@mui/icons-material/Sync';
import SettingsSuggestIcon from '@mui/icons-material/SettingsSuggest';
import MonitorHeartIcon from '@mui/icons-material/MonitorHeart';
import AccountBalanceIcon from '@mui/icons-material/AccountBalance';
import ReceiptLongIcon from '@mui/icons-material/ReceiptLong';
import AccessTimeIcon from '@mui/icons-material/AccessTime';

import { ApiClient } from '../../../../api';

interface FinanceHealthCardProps {
  companyId: number;
  showActions?: boolean;
}

const statusConfig: Record<
  string,
  { label: string; color: 'success' | 'error' | 'warning' | 'default' | 'info'; icon: React.ReactElement }
> = {
  healthy: { label: 'Healthy', color: 'success', icon: <CheckCircleIcon fontSize="small" /> },
  error: { label: 'Attention Needed', color: 'error', icon: <ErrorIcon fontSize="small" /> },
  running: { label: 'In Progress', color: 'info', icon: <CircularProgress size={14} /> },
  never_synced: { label: 'In Progress', color: 'warning', icon: <HourglassEmptyIcon fontSize="small" /> },
  not_configured: { label: 'Not Configured', color: 'default', icon: <SettingsSuggestIcon fontSize="small" /> }
};

const formatRelativeTime = (dateStr: string | null): string => {
  if (!dateStr) return 'Never';
  const date = new Date(dateStr);
  const now = new Date();
  const diffMs = now.getTime() - date.getTime();
  const diffMin = Math.floor(diffMs / 60000);
  if (diffMin < 1) return 'Just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHrs = Math.floor(diffMin / 60);
  if (diffHrs < 24) return `${diffHrs}h ago`;
  const diffDays = Math.floor(diffHrs / 24);
  return `${diffDays}d ago`;
};

export const FinanceHealthCard: React.FC<FinanceHealthCardProps> = ({ companyId, showActions = true }) => {
  const queryClient = useQueryClient();

  const {
    data: summary,
    isLoading,
    error
  } = useQuery({
    queryKey: ['financeHealthSummary', companyId],
    queryFn: () => ApiClient.financeData.getSummary(companyId),
    staleTime: 60 * 1000,
    retry: 1
  });

  const syncMutation = useMutation({
    mutationFn: (providerKey: string) => ApiClient.financeData.triggerSync(companyId, providerKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['financeHealthSummary', companyId] });
      queryClient.invalidateQueries({ queryKey: ['financeIntegrations', companyId] });
    }
  });

  const testMutation = useMutation({
    mutationFn: (providerKey: string) => ApiClient.financeIntegrations.testIntegration(companyId, providerKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['financeHealthSummary', companyId] });
      queryClient.invalidateQueries({ queryKey: ['financeIntegrations', companyId] });
    }
  });

  if (error) {
    return null;
  }

  if (isLoading) {
    return (
      <Card sx={{ mt: 3 }}>
        <CardContent>
          <Skeleton variant="rectangular" height={80} />
        </CardContent>
      </Card>
    );
  }

  if (!summary || summary.sync_status === 'not_configured') {
    return null;
  }

  const config = statusConfig[summary.sync_status] || statusConfig.not_configured;

  return (
    <Card sx={{ mt: 3 }}>
      <CardContent>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', mb: 2 }}>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <MonitorHeartIcon color="primary" />
            <Typography variant="h6">Finance Health</Typography>
          </Box>
          <Chip icon={config.icon} label={config.label} color={config.color} size="small" variant="filled" />
        </Box>

        <Stack direction="row" spacing={3} sx={{ mb: 2 }}>
          <Tooltip title="Last successful sync">
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <AccessTimeIcon fontSize="small" color="action" />
              <Typography variant="body2" color="text.secondary">
                {formatRelativeTime(summary.last_sync_at)}
              </Typography>
            </Box>
          </Tooltip>

          <Tooltip title="Accounts synced">
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <AccountBalanceIcon fontSize="small" color="action" />
              <Typography variant="body2" color="text.secondary">
                {summary.accounts_count} accounts
              </Typography>
            </Box>
          </Tooltip>

          <Tooltip title="Transactions in last 30 days">
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
              <ReceiptLongIcon fontSize="small" color="action" />
              <Typography variant="body2" color="text.secondary">
                {summary.transactions_count_30d} txns (30d)
              </Typography>
            </Box>
          </Tooltip>
        </Stack>

        {summary.sync_status === 'error' && summary.last_sync_error && (
          <Alert severity="error" sx={{ mb: 2 }} variant="outlined">
            <Typography variant="body2">
              {summary.last_sync_error.length > 200
                ? summary.last_sync_error.substring(0, 200) + '...'
                : summary.last_sync_error}
            </Typography>
          </Alert>
        )}

        {showActions && summary.sync_status === 'error' && (
          <Stack direction="row" spacing={1}>
            <Button
              size="small"
              variant="outlined"
              startIcon={testMutation.isPending ? <CircularProgress size={14} /> : <SettingsSuggestIcon />}
              onClick={() => testMutation.mutate('gravity')}
              disabled={testMutation.isPending || syncMutation.isPending}
            >
              Test Connection
            </Button>
            <Button
              size="small"
              variant="outlined"
              startIcon={syncMutation.isPending ? <CircularProgress size={14} /> : <SyncIcon />}
              onClick={() => syncMutation.mutate('gravity')}
              disabled={syncMutation.isPending || testMutation.isPending}
            >
              Run Sync
            </Button>
          </Stack>
        )}

        {syncMutation.isError && (
          <Alert severity="error" sx={{ mt: 1 }} variant="outlined">
            Sync failed. You may not have permission to trigger a sync.
          </Alert>
        )}

        {syncMutation.isSuccess && (
          <Alert severity="success" sx={{ mt: 1 }} variant="outlined">
            Sync completed successfully.
          </Alert>
        )}
      </CardContent>
    </Card>
  );
};

export default FinanceHealthCard;
