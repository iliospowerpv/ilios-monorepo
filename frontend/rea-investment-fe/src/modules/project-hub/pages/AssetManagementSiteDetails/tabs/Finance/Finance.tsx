import React from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Alert from '@mui/material/Alert';
import Skeleton from '@mui/material/Skeleton';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import ErrorIcon from '@mui/icons-material/Error';
import HourglassEmptyIcon from '@mui/icons-material/HourglassEmpty';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import ApprovalIcon from '@mui/icons-material/Approval';
import { useTheme } from '@mui/material/styles';

import type { AssetManagementSiteDetailsTabProps } from '../types';
import { useFocusHighlight } from '../../../../../../hooks/useFocusHighlight';
import { financeApi } from '../../../../../finance/api/finance';
import type { FinanceBudget, FinanceObligation, FinanceSiteSummary } from '../../../../../finance/types';
import { ApiClient } from '../../../../../../api';

const getHealthChipProps = (
  status: string
): { label: string; color: 'success' | 'error' | 'warning' | 'default'; icon: React.ReactElement } => {
  switch (status) {
    case 'healthy':
      return { label: 'Healthy', color: 'success', icon: <CheckCircleIcon fontSize="small" /> };
    case 'error':
      return { label: 'Attention Needed', color: 'error', icon: <ErrorIcon fontSize="small" /> };
    case 'running':
    case 'never_synced':
      return { label: 'In Progress', color: 'warning', icon: <HourglassEmptyIcon fontSize="small" /> };
    default:
      return { label: 'Not Configured', color: 'default', icon: <WarningIcon fontSize="small" /> };
  }
};

const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value);
};

const formatDate = (dateString: string): string => {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  });
};

const FinanceSummaryStrip: React.FC<{
  summary: FinanceSiteSummary;
}> = ({ summary }) => {
  const theme = useTheme();

  return (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={12} md={2}>
            <Stack direction="row" alignItems="center" spacing={1}>
              {summary.finance_ready ? (
                <CheckCircleIcon sx={{ color: theme.palette.success.main }} />
              ) : (
                <WarningIcon sx={{ color: theme.palette.warning.main }} />
              )}
              <Chip
                label={summary.finance_ready ? 'Finance Ready' : 'Not Ready'}
                color={summary.finance_ready ? 'success' : 'warning'}
                size="small"
              />
            </Stack>
            {summary.missing_prerequisites.length > 0 && (
              <Typography variant="caption" color="text.secondary" display="block" sx={{ mt: 1 }}>
                Missing: {summary.missing_prerequisites.slice(0, 3).join(', ')}
              </Typography>
            )}
          </Grid>
          <Grid item xs={6} md={2}>
            <Typography variant="caption" color="text.secondary">
              Budget (Planned)
            </Typography>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              {formatCurrency(summary.total_budget_planned)}
            </Typography>
          </Grid>
          <Grid item xs={6} md={2}>
            <Typography variant="caption" color="text.secondary">
              Authorized
            </Typography>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              {formatCurrency(summary.total_budget_authorized)}
            </Typography>
          </Grid>
          <Grid item xs={6} md={2}>
            <Typography variant="caption" color="text.secondary">
              Actual
            </Typography>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              {formatCurrency(summary.total_budget_actual)}
            </Typography>
          </Grid>
          <Grid item xs={6} md={2}>
            <Typography variant="caption" color="text.secondary">
              Variance
            </Typography>
            <Typography
              variant="h6"
              sx={{
                fontWeight: 600,
                color: summary.budget_variance >= 0 ? theme.palette.success.main : theme.palette.error.main
              }}
            >
              {formatCurrency(summary.budget_variance)}
            </Typography>
          </Grid>
          <Grid item xs={6} md={2}>
            <Typography variant="caption" color="text.secondary">
              Pending Obligations
            </Typography>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              {summary.pending_obligations} ({formatCurrency(summary.pending_obligations_amount)})
            </Typography>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
};

const BudgetsPreview: React.FC<{ budgets: FinanceBudget[] }> = ({ budgets }) => {
  const previewBudgets = budgets.slice(0, 5);

  return (
    <Card variant="outlined" sx={{ mb: 3 }}>
      <CardContent>
        <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
          Budgets Overview
        </Typography>
        {previewBudgets.length === 0 ? (
          <Typography color="text.secondary" variant="body2">
            No budgets configured for this project
          </Typography>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Budget Name</TableCell>
                  <TableCell>Status</TableCell>
                  <TableCell align="right">Planned</TableCell>
                  <TableCell align="right">Authorized</TableCell>
                  <TableCell align="right">Variance</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {previewBudgets.map((budget: FinanceBudget) => (
                  <TableRow key={budget.id}>
                    <TableCell>{budget.name}</TableCell>
                    <TableCell>
                      <Chip label={budget.status} size="small" variant="outlined" />
                    </TableCell>
                    <TableCell align="right">{formatCurrency(budget.total_planned)}</TableCell>
                    <TableCell align="right">{formatCurrency(budget.total_authorized)}</TableCell>
                    <TableCell align="right">{formatCurrency(budget.variance)}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
        {budgets.length > 5 && (
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            Showing 5 of {budgets.length} budgets
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

const ObligationsPreview: React.FC<{ obligations: FinanceObligation[] }> = ({ obligations }) => {
  const previewObligations = obligations.slice(0, 5);

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'approved':
        return 'success';
      case 'submitted':
        return 'info';
      case 'rejected':
        return 'error';
      case 'draft':
        return 'default';
      default:
        return 'default';
    }
  };

  return (
    <Card variant="outlined" sx={{ mb: 3 }}>
      <CardContent>
        <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 2 }}>
          Recent Obligations
        </Typography>
        {previewObligations.length === 0 ? (
          <Typography color="text.secondary" variant="body2">
            No obligations for this project
          </Typography>
        ) : (
          <TableContainer>
            <Table size="small">
              <TableHead>
                <TableRow>
                  <TableCell>Type</TableCell>
                  <TableCell>Vendor</TableCell>
                  <TableCell align="right">Amount</TableCell>
                  <TableCell>Due</TableCell>
                  <TableCell>Status</TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {previewObligations.map((obligation: FinanceObligation) => (
                  <TableRow key={obligation.id}>
                    <TableCell>
                      <Chip label={obligation.obligation_type} size="small" variant="outlined" />
                    </TableCell>
                    <TableCell>{obligation.vendor_name || '-'}</TableCell>
                    <TableCell align="right">{formatCurrency(obligation.amount_requested)}</TableCell>
                    <TableCell>{obligation.due_date ? formatDate(obligation.due_date) : '-'}</TableCell>
                    <TableCell>
                      <Chip label={obligation.status} size="small" color={getStatusColor(obligation.status) as any} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>
        )}
        {obligations.length > 5 && (
          <Typography variant="caption" color="text.secondary" sx={{ mt: 1, display: 'block' }}>
            Showing 5 of {obligations.length} obligations
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

export const Finance: React.FC<AssetManagementSiteDetailsTabProps> = ({ siteDetails }) => {
  const { focusState } = useFocusHighlight();
  const navigate = useNavigate();
  const theme = useTheme();
  const { siteId: routeSiteId } = useParams<{ siteId: string }>();

  const siteId = routeSiteId ? Number(routeSiteId) : siteDetails.id;
  const companyId = siteDetails.company.id;

  const {
    data: summary,
    isLoading: summaryLoading,
    error: summaryError
  } = useQuery({
    queryKey: ['finance-site-summary', companyId, siteId],
    queryFn: () => financeApi.getSiteSummary(companyId, siteId),
    enabled: !!companyId && !!siteId
  });

  const { data: budgetsData, isLoading: budgetsLoading } = useQuery({
    queryKey: ['finance-budgets-preview', companyId, siteId],
    queryFn: () => financeApi.getBudgets(companyId, { site_id: siteId, limit: 10 }),
    enabled: !!companyId && !!siteId
  });

  const { data: obligationsData, isLoading: obligationsLoading } = useQuery({
    queryKey: ['finance-obligations-preview', companyId, siteId],
    queryFn: () => financeApi.getObligations(companyId, { site_id: siteId, limit: 10 }),
    enabled: !!companyId && !!siteId
  });

  const { data: healthSummary, isLoading: healthLoading } = useQuery({
    queryKey: ['financeHealthSummary', companyId],
    queryFn: () => ApiClient.financeData.getSummary(companyId),
    enabled: !!companyId,
    staleTime: 60 * 1000,
    retry: 1
  });

  const handleOpenFinance = () => {
    navigate(`/finance/scope/project/${siteId}`);
  };

  const handleOpenApprovals = () => {
    navigate(`/finance/scope/project/${siteId}?tab=obligations`);
  };

  const isLoading = summaryLoading || budgetsLoading || obligationsLoading;

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="300px">
        <CircularProgress />
      </Box>
    );
  }

  if (summaryError) {
    return (
      <Box>
        <Alert severity="error" sx={{ mb: 2 }}>
          Failed to load finance data. Please try again.
        </Alert>
      </Box>
    );
  }

  return (
    <Box>
      {focusState.notFoundMessage && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {focusState.notFoundMessage}
        </Alert>
      )}

      <Box display="flex" alignItems="center" justifyContent="space-between" mb={3}>
        <Box display="flex" alignItems="center" gap={1}>
          <AccountBalanceWalletIcon color="primary" />
          <Typography variant="h5" sx={{ fontWeight: 500 }}>
            Finance Snapshot
          </Typography>
          <Chip label="Read-Only" size="small" variant="outlined" sx={{ ml: 1, color: theme.palette.text.secondary }} />
          {healthLoading ? (
            <Skeleton variant="rounded" width={100} height={24} sx={{ ml: 1 }} />
          ) : healthSummary && healthSummary.sync_status !== 'not_configured' ? (
            (() => {
              const chipProps = getHealthChipProps(healthSummary.sync_status);
              return (
                <Chip
                  icon={chipProps.icon}
                  label={chipProps.label}
                  color={chipProps.color}
                  size="small"
                  variant="filled"
                  sx={{ ml: 1 }}
                />
              );
            })()
          ) : null}
        </Box>
        <Stack direction="row" spacing={2}>
          <Button variant="outlined" startIcon={<ApprovalIcon />} onClick={handleOpenApprovals}>
            Open Approvals Queue
          </Button>
          <Button variant="contained" startIcon={<OpenInNewIcon />} onClick={handleOpenFinance}>
            Open Finance for this Project
          </Button>
        </Stack>
      </Box>

      <Alert severity="info" sx={{ mb: 3 }}>
        This is a read-only snapshot of finance data. To create or edit budgets, obligations, or vendors, use the full
        Finance module.
      </Alert>

      {summary && <FinanceSummaryStrip summary={summary} />}

      <Grid container spacing={3}>
        <Grid item xs={12} lg={6}>
          <BudgetsPreview budgets={budgetsData?.items || []} />
        </Grid>
        <Grid item xs={12} lg={6}>
          <ObligationsPreview obligations={obligationsData?.items || []} />
        </Grid>
      </Grid>

      {focusState.focusId && (
        <Typography variant="body2" sx={{ mt: 2, fontStyle: 'italic', color: 'text.secondary' }}>
          Focus requested for {focusState.focusType} ID: {focusState.focusId}
        </Typography>
      )}
    </Box>
  );
};

export default Finance;
