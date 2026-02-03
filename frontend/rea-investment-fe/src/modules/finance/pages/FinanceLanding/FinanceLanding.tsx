import React, { useRef, useState, useCallback, useMemo, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Chip from '@mui/material/Chip';
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Paper from '@mui/material/Paper';
import Button from '@mui/material/Button';
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import Snackbar from '@mui/material/Snackbar';
import Alert from '@mui/material/Alert';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import CheckIcon from '@mui/icons-material/Check';
import CloseIcon from '@mui/icons-material/Close';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { ColDef, GridApi, RowClickedEvent } from 'ag-grid-community';
import { useTheme } from '@mui/material/styles';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import BaseTable from '../../../../components/common/tables/BaseTable/BaseTable';
import SearchAndActions from '../../../../components/common/tables/components/SearchAndActions/SearchAndActions';
import { ApiClient } from '../../../../api';
import { financeApi } from '../../api/finance';
import { ApprovalDialog } from '../../components';
import type { FinanceObligation, FinancePortfolioSummary } from '../../types';

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

const columns = [
  {
    headerName: 'Company Name',
    field: 'name',
    flex: 1,
    editable: false,
    filter: false,
    sortable: true
  },
  {
    headerName: 'Number of Projects',
    field: 'total_sites',
    flex: 1,
    editable: false,
    filter: false,
    sortable: true
  }
];

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

const KPIStrip: React.FC<{ summary: FinancePortfolioSummary | undefined; isLoading: boolean }> = ({
  summary,
  isLoading
}) => {
  const theme = useTheme();

  if (isLoading) {
    return (
      <Card sx={{ mb: 3 }}>
        <CardContent>
          <Box display="flex" justifyContent="center" py={2}>
            <CircularProgress size={24} />
          </Box>
        </CardContent>
      </Card>
    );
  }

  if (!summary) return null;

  return (
    <Card sx={{ mb: 3 }}>
      <CardContent>
        <Grid container spacing={2} alignItems="center">
          <Grid item xs={6} md={2}>
            <Typography variant="caption" color="text.secondary">
              Total Planned
            </Typography>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              {formatCurrency(summary.total_budget_planned)}
            </Typography>
          </Grid>
          <Grid item xs={6} md={2}>
            <Typography variant="caption" color="text.secondary">
              Total Authorized
            </Typography>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              {formatCurrency(summary.total_budget_authorized)}
            </Typography>
          </Grid>
          <Grid item xs={6} md={2}>
            <Typography variant="caption" color="text.secondary">
              Total Actual
            </Typography>
            <Typography variant="h6" sx={{ fontWeight: 600 }}>
              {formatCurrency(summary.total_budget_actual)}
            </Typography>
          </Grid>
          <Grid item xs={6} md={2}>
            <Typography variant="caption" color="text.secondary">
              Total Variance
            </Typography>
            <Typography
              variant="h6"
              sx={{
                fontWeight: 600,
                color: summary.total_variance >= 0 ? theme.palette.success.main : theme.palette.error.main
              }}
            >
              {formatCurrency(summary.total_variance)}
            </Typography>
          </Grid>
          <Grid item xs={6} md={2}>
            <Stack direction="row" alignItems="center" spacing={1}>
              <CheckCircleIcon sx={{ color: theme.palette.success.main, fontSize: 20 }} />
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Finance Ready
                </Typography>
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  {summary.sites_finance_ready}
                </Typography>
              </Box>
            </Stack>
          </Grid>
          <Grid item xs={6} md={2}>
            <Stack direction="row" alignItems="center" spacing={1}>
              <WarningIcon sx={{ color: theme.palette.warning.main, fontSize: 20 }} />
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Pending Approvals
                </Typography>
                <Typography variant="h6" sx={{ fontWeight: 600 }}>
                  {summary.total_pending_obligations} ({formatCurrency(summary.total_pending_amount)})
                </Typography>
              </Box>
            </Stack>
          </Grid>
        </Grid>
      </CardContent>
    </Card>
  );
};

interface ApprovalsQueueProps {
  companyId: number | null;
  onSuccess: (msg: string) => void;
  onError: (msg: string) => void;
}

const ApprovalsQueue: React.FC<ApprovalsQueueProps> = ({ companyId, onSuccess, onError }) => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [approvalDialogOpen, setApprovalDialogOpen] = useState(false);
  const [selectedObligation, setSelectedObligation] = useState<FinanceObligation | null>(null);
  const [approvalAction, setApprovalAction] = useState<'approve' | 'reject' | null>(null);
  const [typeFilter, setTypeFilter] = useState<string>('');

  const { data, isLoading } = useQuery({
    queryKey: ['finance-pending-obligations', companyId],
    queryFn: () => financeApi.getObligations(companyId!, { status: 'submitted', limit: 100 }),
    enabled: !!companyId
  });

  const approveMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: { decision: string; notes?: string; override_reason?: string } }) =>
      financeApi.approveObligation(companyId!, id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['finance-pending-obligations', companyId] });
      queryClient.invalidateQueries({ queryKey: ['finance-portfolio-summary'] });
      onSuccess('Obligation processed successfully');
    },
    onError: () => onError('Failed to process obligation')
  });

  const handleApprove = (obl: FinanceObligation) => {
    setSelectedObligation(obl);
    setApprovalAction('approve');
    setApprovalDialogOpen(true);
  };

  const handleReject = (obl: FinanceObligation) => {
    setSelectedObligation(obl);
    setApprovalAction('reject');
    setApprovalDialogOpen(true);
  };

  const handleApprovalSubmit = async (data: { decision: string; notes?: string; override_reason?: string }) => {
    if (selectedObligation) {
      await approveMutation.mutateAsync({ id: selectedObligation.id, data });
    }
  };

  const handleOpenSite = (obl: FinanceObligation) => {
    if (obl.site_id) {
      navigate(`/finance/scope/project/${obl.site_id}?tab=obligations&focusType=obligation&focusId=${obl.id}`);
    }
  };

  if (!companyId) {
    return (
      <Box py={4} textAlign="center">
        <Typography color="text.secondary">Select a company to view pending approvals</Typography>
      </Box>
    );
  }

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" py={4}>
        <CircularProgress size={24} />
      </Box>
    );
  }

  const allObligations = data?.items || [];
  const obligations = typeFilter
    ? allObligations.filter((o: FinanceObligation) => o.obligation_type === typeFilter)
    : allObligations;

  const uniqueTypes = Array.from(new Set(allObligations.map((o: FinanceObligation) => o.obligation_type)));

  return (
    <>
      <Box display="flex" gap={2} mb={2} alignItems="center">
        <FormControl size="small" sx={{ minWidth: 150 }}>
          <InputLabel>Type</InputLabel>
          <Select value={typeFilter} onChange={e => setTypeFilter(e.target.value)} label="Type">
            <MenuItem value="">
              <em>All Types</em>
            </MenuItem>
            {uniqueTypes.map(type => (
              <MenuItem key={type} value={type}>
                {type}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <Typography variant="body2" color="text.secondary">
          {obligations.length} pending approval{obligations.length !== 1 ? 's' : ''}
        </Typography>
      </Box>
      <TableContainer component={Paper} variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Project</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Vendor</TableCell>
              <TableCell>Reference</TableCell>
              <TableCell align="right">Amount</TableCell>
              <TableCell>Requested</TableCell>
              <TableCell>Due</TableCell>
              <TableCell align="center">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {obligations.map((obl: FinanceObligation) => (
              <TableRow key={obl.id} hover>
                <TableCell>
                  <Button size="small" endIcon={<OpenInNewIcon fontSize="small" />} onClick={() => handleOpenSite(obl)}>
                    {obl.site_name || `Site ${obl.site_id}`}
                  </Button>
                </TableCell>
                <TableCell>
                  <Chip label={obl.obligation_type} size="small" variant="outlined" />
                </TableCell>
                <TableCell>{obl.vendor_name || '-'}</TableCell>
                <TableCell>{obl.reference_number || '-'}</TableCell>
                <TableCell align="right">{formatCurrency(obl.amount_requested)}</TableCell>
                <TableCell>{formatDate(obl.requested_date)}</TableCell>
                <TableCell>{obl.due_date ? formatDate(obl.due_date) : '-'}</TableCell>
                <TableCell align="center">
                  <Tooltip title="Approve">
                    <IconButton size="small" color="success" onClick={() => handleApprove(obl)}>
                      <CheckIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                  <Tooltip title="Reject">
                    <IconButton size="small" color="error" onClick={() => handleReject(obl)}>
                      <CloseIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
            {obligations.length === 0 && (
              <TableRow>
                <TableCell colSpan={8} align="center">
                  <Typography color="text.secondary">No pending approvals</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
      <ApprovalDialog
        open={approvalDialogOpen}
        onClose={() => setApprovalDialogOpen(false)}
        onSubmit={handleApprovalSubmit}
        obligation={selectedObligation}
        action={approvalAction}
      />
    </>
  );
};

export const FinanceLanding: React.FC = () => {
  const navigate = useNavigate();
  const theme = useTheme();
  const [searchParams] = useSearchParams();
  const basicTableRef = useRef<{ getApi: () => GridApi | undefined }>(null);
  const [colDefs] = useState<ColDef[]>(columns);
  const [searchTerm, setSearchTerm] = useState<string>('');
  const [tabValue, setTabValue] = useState(0);
  const [selectedCompanyId, setSelectedCompanyId] = useState<number | null>(null);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success'
  });

  const siteIdParam = searchParams.get('siteId');
  const tabParam = searchParams.get('tab');

  const { data: siteData, isLoading: siteLoading } = useQuery({
    queryKey: ['site-lookup', siteIdParam],
    queryFn: () => ApiClient.assetManagement.getSiteById(Number(siteIdParam)),
    enabled: !!siteIdParam
  });

  const { data: companiesData } = useQuery({
    queryKey: ['finance-companies-list'],
    queryFn: () => ApiClient.assetManagement.companies({ skip: 0, limit: 100 })
  });

  const { data: portfolioSummary, isLoading: summaryLoading } = useQuery({
    queryKey: ['finance-portfolio-summary', selectedCompanyId],
    queryFn: () => financeApi.getPortfolioSummary(selectedCompanyId!),
    enabled: !!selectedCompanyId
  });

  useEffect(() => {
    if (siteData && siteIdParam) {
      const companyId = siteData.company?.id;
      if (companyId) {
        const tabQuery = tabParam ? `?tab=${tabParam}` : '';
        navigate(`/finance/companies/${companyId}/sites/${siteIdParam}${tabQuery}`, { replace: true });
      }
    }
  }, [siteData, siteIdParam, tabParam, navigate]);

  useEffect(() => {
    if (companiesData?.items?.length && !selectedCompanyId) {
      setSelectedCompanyId(Number(companiesData.items[0].id));
    }
  }, [companiesData, selectedCompanyId]);

  const serverSideDatasource = useMemo(
    () => ({
      getRows: (params: any) => {
        const api = basicTableRef.current?.getApi();
        const skip = params.request.startRow;
        const limit = params.request.endRow - params.request.startRow;
        const orderBy = params.request.sortModel.length > 0 ? params.request.sortModel[0].colId : null;
        const orderDirection = params.request.sortModel.length > 0 ? params.request.sortModel[0].sort : null;

        ApiClient.assetManagement
          .companies({
            skip,
            limit,
            ...(searchTerm && { search: searchTerm }),
            ...(orderBy && { order_by: orderBy }),
            ...(orderDirection && { order_direction: orderDirection })
          })
          .then(data => {
            if (!data.items.length) {
              api?.showNoRowsOverlay();
            } else {
              api?.hideOverlay();
            }
            params.success({
              rowData: data.items,
              rowCount: data.total
            });
          })
          .catch(() => {
            params?.fail();
          });
      }
    }),
    [searchTerm]
  );

  const handleSearch = (value: string) => {
    setSearchTerm(value);
  };

  const onRowClicked = useCallback(
    (e: RowClickedEvent) => {
      navigate(`/finance/companies/${e.data.id}`);
    },
    [navigate]
  );

  const handleSuccess = (message: string) => {
    setSnackbar({ open: true, message, severity: 'success' });
  };

  const handleError = (message: string) => {
    setSnackbar({ open: true, message, severity: 'error' });
  };

  if (siteIdParam && siteLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight="400px">
        <CircularProgress />
      </Box>
    );
  }

  const companies = companiesData?.items || [];

  return (
    <Box p={3}>
      <Typography variant="h4" marginBottom="24px" sx={{ fontWeight: 600 }} fontSize="34px" lineHeight="42px">
        Finance
      </Typography>

      <Box display="flex" alignItems="center" gap={2} mb={3}>
        <FormControl size="small" sx={{ minWidth: 250 }}>
          <InputLabel>Company</InputLabel>
          <Select<number | ''>
            value={selectedCompanyId ?? ''}
            onChange={e => setSelectedCompanyId(Number(e.target.value))}
            label="Company"
          >
            {companies.map((c: any) => (
              <MenuItem key={c.id} value={c.id}>
                {c.name}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Box>

      <KPIStrip summary={portfolioSummary?.summary} isLoading={summaryLoading} />

      <Box sx={{ borderBottom: 1, borderColor: 'divider', mb: 2 }}>
        <Tabs value={tabValue} onChange={(_, newValue) => setTabValue(newValue)}>
          <Tab label="Companies" />
          <Tab label="Approvals Queue" />
        </Tabs>
      </Box>

      <TabPanel value={tabValue} index={0}>
        <SearchAndActions
          showSearch={true}
          showExport={false}
          searchPlaceholder="Search by Name"
          onSearch={handleSearch}
        />
        <BaseTable
          ref={basicTableRef}
          rowModelType="serverSide"
          columnDefs={colDefs}
          serverSideDatasource={serverSideDatasource}
          onRowClicked={onRowClicked}
        />
      </TabPanel>

      <TabPanel value={tabValue} index={1}>
        <ApprovalsQueue companyId={selectedCompanyId} onSuccess={handleSuccess} onError={handleError} />
      </TabPanel>

      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={() => setSnackbar({ ...snackbar, open: false })}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
      >
        <Alert severity={snackbar.severity} onClose={() => setSnackbar({ ...snackbar, open: false })}>
          {snackbar.message}
        </Alert>
      </Snackbar>
    </Box>
  );
};

export default FinanceLanding;
