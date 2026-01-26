import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import DownloadIcon from '@mui/icons-material/Download';
import { useTheme } from '@mui/material/styles';

import { financeApi } from '../../api/finance';
import type { FinanceBudget, FinanceObligation, FinanceVendor, FinanceActual } from '../../types';
import { useEntityContext } from '../../../../contexts/entityContext';

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

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => (
  <div role="tabpanel" hidden={value !== index}>
    {value === index && <Box sx={{ pt: 3 }}>{children}</Box>}
  </div>
);

const FinanceSummaryStrip: React.FC<{
  summary: {
    total_budget_planned: number;
    total_budget_authorized: number;
    total_budget_actual: number;
    budget_variance: number;
    finance_ready: boolean;
    missing_prerequisites: string[];
  };
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
        </Grid>
      </CardContent>
    </Card>
  );
};

const BudgetsTab: React.FC<{ companyId: number; siteId: number }> = ({ companyId, siteId }) => {
  const { data, isLoading } = useQuery({
    queryKey: ['finance-budgets', companyId, siteId],
    queryFn: () => financeApi.getBudgets(companyId, { site_id: siteId })
  });

  if (isLoading) return <CircularProgress size={24} />;

  const budgets = data?.items || [];

  return (
    <TableContainer component={Paper} variant="outlined">
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Budget Name</TableCell>
            <TableCell>Status</TableCell>
            <TableCell align="right">Planned</TableCell>
            <TableCell align="right">Authorized</TableCell>
            <TableCell align="right">Actual</TableCell>
            <TableCell align="right">Variance</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {budgets.map((budget: FinanceBudget) => (
            <TableRow key={budget.id} hover>
              <TableCell>{budget.name}</TableCell>
              <TableCell>
                <Chip label={budget.status} size="small" variant="outlined" />
              </TableCell>
              <TableCell align="right">{formatCurrency(budget.total_planned)}</TableCell>
              <TableCell align="right">{formatCurrency(budget.total_authorized)}</TableCell>
              <TableCell align="right">{formatCurrency(budget.total_actual)}</TableCell>
              <TableCell align="right">{formatCurrency(budget.variance)}</TableCell>
            </TableRow>
          ))}
          {budgets.length === 0 && (
            <TableRow>
              <TableCell colSpan={6} align="center">
                <Typography color="text.secondary">No budgets found</Typography>
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

const ObligationsTab: React.FC<{ companyId: number; siteId: number }> = ({ companyId, siteId }) => {
  const { data, isLoading } = useQuery({
    queryKey: ['finance-obligations', companyId, siteId],
    queryFn: () => financeApi.getObligations(companyId, { site_id: siteId })
  });

  if (isLoading) return <CircularProgress size={24} />;

  const obligations = data?.items || [];

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
    <TableContainer component={Paper} variant="outlined">
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Type</TableCell>
            <TableCell>Vendor</TableCell>
            <TableCell>Description</TableCell>
            <TableCell align="right">Amount</TableCell>
            <TableCell>Requested</TableCell>
            <TableCell>Due</TableCell>
            <TableCell>Status</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {obligations.map((obligation: FinanceObligation) => (
            <TableRow key={obligation.id} hover>
              <TableCell>
                <Chip label={obligation.obligation_type} size="small" variant="outlined" />
              </TableCell>
              <TableCell>{obligation.vendor_name || '-'}</TableCell>
              <TableCell>{obligation.description || '-'}</TableCell>
              <TableCell align="right">{formatCurrency(obligation.amount_requested)}</TableCell>
              <TableCell>{formatDate(obligation.requested_date)}</TableCell>
              <TableCell>{obligation.due_date ? formatDate(obligation.due_date) : '-'}</TableCell>
              <TableCell>
                <Chip label={obligation.status} size="small" color={getStatusColor(obligation.status) as any} />
              </TableCell>
            </TableRow>
          ))}
          {obligations.length === 0 && (
            <TableRow>
              <TableCell colSpan={7} align="center">
                <Typography color="text.secondary">No obligations found</Typography>
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

const VendorsTab: React.FC<{ companyId: number }> = ({ companyId }) => {
  const { data, isLoading } = useQuery({
    queryKey: ['finance-vendors', companyId],
    queryFn: () => financeApi.getVendors(companyId)
  });

  if (isLoading) return <CircularProgress size={24} />;

  const vendors = data?.items || [];

  return (
    <TableContainer component={Paper} variant="outlined">
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Vendor Name</TableCell>
            <TableCell>Type</TableCell>
            <TableCell>Contact</TableCell>
            <TableCell>Email</TableCell>
            <TableCell>Status</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {vendors.map((vendor: FinanceVendor) => (
            <TableRow key={vendor.id} hover>
              <TableCell>{vendor.name}</TableCell>
              <TableCell>
                <Chip label={vendor.vendor_type} size="small" variant="outlined" />
              </TableCell>
              <TableCell>{vendor.contact_name || '-'}</TableCell>
              <TableCell>{vendor.contact_email || '-'}</TableCell>
              <TableCell>
                <Chip
                  label={vendor.is_active ? 'Active' : 'Inactive'}
                  size="small"
                  color={vendor.is_active ? 'success' : 'default'}
                  variant="outlined"
                />
              </TableCell>
            </TableRow>
          ))}
          {vendors.length === 0 && (
            <TableRow>
              <TableCell colSpan={5} align="center">
                <Typography color="text.secondary">No vendors found</Typography>
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

const ActualsTab: React.FC<{ companyId: number; siteId: number }> = ({ companyId, siteId }) => {
  const { data, isLoading } = useQuery({
    queryKey: ['finance-actuals', companyId, siteId],
    queryFn: () => financeApi.getActuals(companyId, { site_id: siteId })
  });

  if (isLoading) return <CircularProgress size={24} />;

  const actuals = data?.items || [];

  return (
    <TableContainer component={Paper} variant="outlined">
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>Date</TableCell>
            <TableCell>Category</TableCell>
            <TableCell>Vendor</TableCell>
            <TableCell>Description</TableCell>
            <TableCell align="right">Amount</TableCell>
            <TableCell>Source</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {actuals.map((actual: FinanceActual) => (
            <TableRow key={actual.id} hover>
              <TableCell>{formatDate(actual.transaction_date)}</TableCell>
              <TableCell>
                <Chip label={actual.category} size="small" variant="outlined" />
              </TableCell>
              <TableCell>{actual.vendor_name || '-'}</TableCell>
              <TableCell>{actual.description || '-'}</TableCell>
              <TableCell align="right">{formatCurrency(actual.amount)}</TableCell>
              <TableCell>
                <Chip label={actual.source_system} size="small" variant="outlined" />
              </TableCell>
            </TableRow>
          ))}
          {actuals.length === 0 && (
            <TableRow>
              <TableCell colSpan={6} align="center">
                <Typography color="text.secondary">No actuals found</Typography>
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </TableContainer>
  );
};

export const SiteFinance: React.FC = () => {
  const { companyId, siteId } = useParams<{ companyId: string; siteId: string }>();
  const [tabValue, setTabValue] = useState(0);
  const { setCurrentCompany, setCurrentProject } = useEntityContext();

  const { data: summary, isLoading } = useQuery({
    queryKey: ['finance-site-summary', companyId, siteId],
    queryFn: () => financeApi.getSiteSummary(Number(companyId), Number(siteId)),
    enabled: !!companyId && !!siteId
  });

  useEffect(() => {
    if (summary && companyId && siteId) {
      setCurrentCompany({ id: Number(companyId), name: summary.company_name || `Company ${companyId}` });
      setCurrentProject({ id: Number(siteId), name: summary.site_name || `Site ${siteId}` });
    }
  }, [summary, companyId, siteId, setCurrentCompany, setCurrentProject]);

  const handleDownloadPackage = async () => {
    try {
      const blob = await financeApi.downloadDataRoomPackage(Number(companyId), Number(siteId));
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `finance_package_site_${siteId}.json`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
    } catch (error) {
      console.error('Failed to download package:', error);
    }
  };

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (!summary) {
    return (
      <Box p={3}>
        <Typography color="error">Failed to load finance data</Typography>
      </Box>
    );
  }

  return (
    <Box p={3}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Typography variant="h5" sx={{ fontWeight: 600 }}>
          Site Finance: {summary.site_name}
        </Typography>
        <Button variant="outlined" startIcon={<DownloadIcon />} onClick={handleDownloadPackage} size="small">
          Export Data Room Package
        </Button>
      </Stack>
      <FinanceSummaryStrip summary={summary} />
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)}>
          <Tab label="Budget & Forecast" />
          <Tab label="Obligations & Payments" />
          <Tab label="Vendors & Contracts" />
          <Tab label="Actuals" />
        </Tabs>
      </Box>
      <TabPanel value={tabValue} index={0}>
        <BudgetsTab companyId={Number(companyId)} siteId={Number(siteId)} />
      </TabPanel>
      <TabPanel value={tabValue} index={1}>
        <ObligationsTab companyId={Number(companyId)} siteId={Number(siteId)} />
      </TabPanel>
      <TabPanel value={tabValue} index={2}>
        <VendorsTab companyId={Number(companyId)} />
      </TabPanel>
      <TabPanel value={tabValue} index={3}>
        <ActualsTab companyId={Number(companyId)} siteId={Number(siteId)} />
      </TabPanel>
    </Box>
  );
};

export default SiteFinance;
