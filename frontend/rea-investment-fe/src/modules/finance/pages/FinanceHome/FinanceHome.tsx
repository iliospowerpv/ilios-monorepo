import React, { useEffect } from 'react';
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
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import { useTheme } from '@mui/material/styles';

import { financeApi } from '../../api/finance';
import type { FinanceSiteSummary } from '../../types';
import { useEntityContext } from '../../../../contexts/entityContext';

const formatCurrency = (value: number): string => {
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value);
};

const SummaryCard: React.FC<{
  title: string;
  value: string | number;
  subtitle?: string;
  color?: string;
}> = ({ title, value, subtitle, color }) => {
  const theme = useTheme();
  return (
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Typography variant="body2" color="text.secondary" gutterBottom>
          {title}
        </Typography>
        <Typography variant="h4" sx={{ color: color || theme.palette.text.primary, fontWeight: 600 }}>
          {typeof value === 'number' ? formatCurrency(value) : value}
        </Typography>
        {subtitle && (
          <Typography variant="caption" color="text.secondary">
            {subtitle}
          </Typography>
        )}
      </CardContent>
    </Card>
  );
};

const SiteRow: React.FC<{
  site: FinanceSiteSummary;
  companyId: number;
  onClick: () => void;
}> = ({ site, onClick }) => {
  const theme = useTheme();

  return (
    <TableRow
      hover
      onClick={onClick}
      sx={{ cursor: 'pointer', '&:hover': { backgroundColor: theme.palette.action.hover } }}
    >
      <TableCell>
        <Stack direction="row" alignItems="center" spacing={1}>
          {site.finance_ready ? (
            <CheckCircleIcon sx={{ color: theme.palette.success.main, fontSize: 20 }} />
          ) : (
            <WarningIcon sx={{ color: theme.palette.warning.main, fontSize: 20 }} />
          )}
          <Typography variant="body2">{site.site_name}</Typography>
        </Stack>
      </TableCell>
      <TableCell>
        <Chip
          label={site.finance_ready ? 'Ready' : 'Not Ready'}
          size="small"
          color={site.finance_ready ? 'success' : 'warning'}
          variant="outlined"
        />
      </TableCell>
      <TableCell align="right">{formatCurrency(site.total_budget_planned)}</TableCell>
      <TableCell align="right">{formatCurrency(site.total_budget_authorized)}</TableCell>
      <TableCell align="right">{formatCurrency(site.total_budget_actual)}</TableCell>
      <TableCell
        align="right"
        sx={{ color: site.budget_variance >= 0 ? theme.palette.success.main : theme.palette.error.main }}
      >
        {formatCurrency(site.budget_variance)}
      </TableCell>
      <TableCell align="right">{site.pending_obligations}</TableCell>
      <TableCell>
        {site.missing_prerequisites.length > 0 && (
          <Typography variant="caption" color="text.secondary">
            {site.missing_prerequisites.slice(0, 2).join(', ')}
            {site.missing_prerequisites.length > 2 && '...'}
          </Typography>
        )}
      </TableCell>
    </TableRow>
  );
};

export const FinanceHome: React.FC = () => {
  const { companyId } = useParams<{ companyId: string }>();
  const navigate = useNavigate();
  const theme = useTheme();
  const { setCurrentCompany, setCurrentProject } = useEntityContext();

  const { data, isLoading, error } = useQuery({
    queryKey: ['finance-portfolio', companyId],
    queryFn: () => financeApi.getPortfolioSummary(Number(companyId)),
    enabled: !!companyId
  });

  useEffect(() => {
    if (data && companyId) {
      setCurrentCompany({ id: Number(companyId), name: data.company_name || `Company ${companyId}` });
      setCurrentProject(null);
    }
  }, [data, companyId, setCurrentCompany, setCurrentProject]);

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  if (error || !data) {
    return (
      <Box p={3}>
        <Typography color="error">Failed to load finance data</Typography>
      </Box>
    );
  }

  const { summary, sites } = data;

  return (
    <Box p={3}>
      <Typography variant="h5" gutterBottom sx={{ fontWeight: 600, mb: 3 }}>
        Finance Overview
      </Typography>
      <Grid container spacing={2} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <SummaryCard title="Total Budget (Planned)" value={summary.total_budget_planned} />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <SummaryCard title="Total Authorized" value={summary.total_budget_authorized} />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <SummaryCard title="Total Actual" value={summary.total_budget_actual} />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <SummaryCard
            title="Variance"
            value={summary.total_variance}
            color={summary.total_variance >= 0 ? theme.palette.success.main : theme.palette.error.main}
          />
        </Grid>
      </Grid>
      <Grid container spacing={2} sx={{ mb: 4 }}>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Stack direction="row" alignItems="center" spacing={1}>
                <CheckCircleIcon sx={{ color: theme.palette.success.main }} />
                <Box>
                  <Typography variant="h5" sx={{ fontWeight: 600 }}>
                    {summary.sites_finance_ready}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Projects Finance Ready
                  </Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Stack direction="row" alignItems="center" spacing={1}>
                <WarningIcon sx={{ color: theme.palette.warning.main }} />
                <Box>
                  <Typography variant="h5" sx={{ fontWeight: 600 }}>
                    {summary.sites_not_ready}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Projects Not Ready
                  </Typography>
                </Box>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h5" sx={{ fontWeight: 600 }}>
                {summary.total_pending_obligations}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Pending Approvals
              </Typography>
            </CardContent>
          </Card>
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <Card>
            <CardContent>
              <Typography variant="h5" sx={{ fontWeight: 600 }}>
                {formatCurrency(summary.total_pending_amount)}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Pending Amount
              </Typography>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
      <Typography variant="h6" gutterBottom sx={{ fontWeight: 600, mt: 4, mb: 2 }}>
        Projects
      </Typography>
      <TableContainer component={Paper} variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Project</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="right">Planned</TableCell>
              <TableCell align="right">Authorized</TableCell>
              <TableCell align="right">Actual</TableCell>
              <TableCell align="right">Variance</TableCell>
              <TableCell align="right">Pending</TableCell>
              <TableCell>Missing Prerequisites</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {sites.map(site => (
              <SiteRow
                key={site.site_id}
                site={site}
                companyId={Number(companyId)}
                onClick={() => navigate(`/finance/companies/${companyId}/sites/${site.site_id}`)}
              />
            ))}
            {sites.length === 0 && (
              <TableRow>
                <TableCell colSpan={8} align="center">
                  <Typography color="text.secondary">No sites found</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  );
};

export default FinanceHome;
