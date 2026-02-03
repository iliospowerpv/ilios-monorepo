import React, { useState, useEffect } from 'react';
import { useParams, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
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
import IconButton from '@mui/material/IconButton';
import Tooltip from '@mui/material/Tooltip';
import Snackbar from '@mui/material/Snackbar';
import Alert from '@mui/material/Alert';
import Accordion from '@mui/material/Accordion';
import AccordionSummary from '@mui/material/AccordionSummary';
import AccordionDetails from '@mui/material/AccordionDetails';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningIcon from '@mui/icons-material/Warning';
import DownloadIcon from '@mui/icons-material/Download';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import DeleteIcon from '@mui/icons-material/Delete';
import SendIcon from '@mui/icons-material/Send';
import CheckIcon from '@mui/icons-material/Check';
import CloseIcon from '@mui/icons-material/Close';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import { useTheme } from '@mui/material/styles';

import { financeApi } from '../../api/finance';
import type {
  FinanceBudget,
  FinanceObligation,
  FinanceVendor,
  FinanceActual,
  FinanceObligationStatus
} from '../../types';
import { useEntityContext } from '../../../../contexts/entityContext';
import {
  BudgetFormDialog,
  ObligationFormDialog,
  VendorFormDialog,
  ActualFormDialog,
  ApprovalDialog
} from '../../components';

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

interface BudgetsTabProps {
  companyId: number;
  siteId: number;
  onSuccess: (msg: string) => void;
  onError: (msg: string) => void;
}

const BudgetsTab: React.FC<BudgetsTabProps> = ({ companyId, siteId, onSuccess, onError }) => {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editBudget, setEditBudget] = useState<FinanceBudget | undefined>();

  const { data, isLoading } = useQuery({
    queryKey: ['finance-budgets', companyId, siteId],
    queryFn: () => financeApi.getBudgets(companyId, { site_id: siteId })
  });

  const createMutation = useMutation({
    mutationFn: (data: Partial<FinanceBudget>) => financeApi.createBudget(companyId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['finance-budgets', companyId, siteId] });
      queryClient.invalidateQueries({ queryKey: ['finance-site-summary'] });
      onSuccess('Budget created successfully');
    },
    onError: () => onError('Failed to create budget')
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<FinanceBudget> }) =>
      financeApi.updateBudget(companyId, id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['finance-budgets', companyId, siteId] });
      queryClient.invalidateQueries({ queryKey: ['finance-site-summary'] });
      onSuccess('Budget updated successfully');
    },
    onError: () => onError('Failed to update budget')
  });

  const deleteMutation = useMutation({
    mutationFn: (id: number) => financeApi.deleteBudget(companyId, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['finance-budgets', companyId, siteId] });
      queryClient.invalidateQueries({ queryKey: ['finance-site-summary'] });
      onSuccess('Budget deleted successfully');
    },
    onError: () => onError('Failed to delete budget')
  });

  const handleSubmit = async (data: Partial<FinanceBudget>) => {
    if (editBudget) {
      await updateMutation.mutateAsync({ id: editBudget.id, data });
    } else {
      await createMutation.mutateAsync(data);
    }
  };

  const handleEdit = (budget: FinanceBudget) => {
    setEditBudget(budget);
    setDialogOpen(true);
  };

  const handleDelete = (budget: FinanceBudget) => {
    if (window.confirm(`Delete budget "${budget.name}"?`)) {
      deleteMutation.mutate(budget.id);
    }
  };

  if (isLoading) return <CircularProgress size={24} />;

  const budgets = data?.items || [];

  return (
    <>
      <Box display="flex" justifyContent="flex-end" mb={2}>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => {
            setEditBudget(undefined);
            setDialogOpen(true);
          }}
        >
          Create Budget
        </Button>
      </Box>
      <TableContainer component={Paper} variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Budget Name</TableCell>
              <TableCell>Status</TableCell>
              <TableCell>Period</TableCell>
              <TableCell align="right">Planned</TableCell>
              <TableCell align="right">Authorized</TableCell>
              <TableCell align="right">Actual</TableCell>
              <TableCell align="right">Variance</TableCell>
              <TableCell align="center">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {budgets.map((budget: FinanceBudget) => (
              <TableRow key={budget.id} hover>
                <TableCell>{budget.name}</TableCell>
                <TableCell>
                  <Chip label={budget.status} size="small" variant="outlined" />
                </TableCell>
                <TableCell>
                  {budget.period_start && budget.period_end
                    ? `${formatDate(budget.period_start)} - ${formatDate(budget.period_end)}`
                    : '-'}
                </TableCell>
                <TableCell align="right">{formatCurrency(budget.total_planned)}</TableCell>
                <TableCell align="right">{formatCurrency(budget.total_authorized)}</TableCell>
                <TableCell align="right">{formatCurrency(budget.total_actual)}</TableCell>
                <TableCell align="right">{formatCurrency(budget.variance)}</TableCell>
                <TableCell align="center">
                  <Tooltip title="Edit">
                    <span>
                      <IconButton size="small" onClick={() => handleEdit(budget)} disabled={budget.status !== 'draft'}>
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </span>
                  </Tooltip>
                  <Tooltip title="Delete">
                    <span>
                      <IconButton
                        size="small"
                        onClick={() => handleDelete(budget)}
                        disabled={budget.status !== 'draft'}
                      >
                        <DeleteIcon fontSize="small" />
                      </IconButton>
                    </span>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
            {budgets.length === 0 && (
              <TableRow>
                <TableCell colSpan={8} align="center">
                  <Typography color="text.secondary">No budgets found</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
      <BudgetFormDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onSubmit={handleSubmit}
        budget={editBudget}
        siteId={siteId}
      />
    </>
  );
};

interface ObligationsTabProps {
  companyId: number;
  siteId: number;
  vendors: FinanceVendor[];
  onSuccess: (msg: string) => void;
  onError: (msg: string) => void;
}

const ObligationsTab: React.FC<ObligationsTabProps> = ({ companyId, siteId, vendors, onSuccess, onError }) => {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [approvalDialogOpen, setApprovalDialogOpen] = useState(false);
  const [selectedObligation, setSelectedObligation] = useState<FinanceObligation | null>(null);
  const [approvalAction, setApprovalAction] = useState<'approve' | 'reject' | null>(null);

  const { data, isLoading } = useQuery({
    queryKey: ['finance-obligations', companyId, siteId],
    queryFn: () => financeApi.getObligations(companyId, { site_id: siteId })
  });

  const createMutation = useMutation({
    mutationFn: (data: Partial<FinanceObligation>) => financeApi.createObligation(companyId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['finance-obligations', companyId, siteId] });
      onSuccess('Obligation created successfully');
    },
    onError: () => onError('Failed to create obligation')
  });

  const submitMutation = useMutation({
    mutationFn: (id: number) => financeApi.submitObligation(companyId, id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['finance-obligations', companyId, siteId] });
      onSuccess('Obligation submitted for approval');
    },
    onError: () => onError('Failed to submit obligation')
  });

  const approveMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: { decision: string; notes?: string; override_reason?: string } }) =>
      financeApi.approveObligation(companyId, id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['finance-obligations', companyId, siteId] });
      queryClient.invalidateQueries({ queryKey: ['finance-site-summary'] });
      onSuccess('Obligation processed successfully');
    },
    onError: () => onError('Failed to process obligation')
  });

  const handleSubmit = (obl: FinanceObligation) => {
    if (window.confirm('Submit this obligation for approval?')) {
      submitMutation.mutate(obl.id);
    }
  };

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

  if (isLoading) return <CircularProgress size={24} />;

  const obligations = data?.items || [];

  return (
    <>
      <Box display="flex" justifyContent="flex-end" mb={2}>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialogOpen(true)}>
          Create Obligation
        </Button>
      </Box>
      <TableContainer component={Paper} variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Type</TableCell>
              <TableCell>Vendor</TableCell>
              <TableCell>Reference</TableCell>
              <TableCell>Description</TableCell>
              <TableCell align="right">Amount</TableCell>
              <TableCell>Requested</TableCell>
              <TableCell>Due</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="center">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {obligations.map((obligation: FinanceObligation) => (
              <React.Fragment key={obligation.id}>
                <TableRow hover>
                  <TableCell>
                    <Chip label={obligation.obligation_type} size="small" variant="outlined" />
                  </TableCell>
                  <TableCell>{obligation.vendor_name || '-'}</TableCell>
                  <TableCell>{obligation.reference_number || '-'}</TableCell>
                  <TableCell>{obligation.description || '-'}</TableCell>
                  <TableCell align="right">{formatCurrency(obligation.amount_requested)}</TableCell>
                  <TableCell>{formatDate(obligation.requested_date)}</TableCell>
                  <TableCell>{obligation.due_date ? formatDate(obligation.due_date) : '-'}</TableCell>
                  <TableCell>
                    <Chip label={obligation.status} size="small" color={getStatusColor(obligation.status) as any} />
                  </TableCell>
                  <TableCell align="center">
                    {obligation.status === 'draft' && (
                      <Tooltip title="Submit for Approval">
                        <IconButton size="small" onClick={() => handleSubmit(obligation)}>
                          <SendIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                    {obligation.status === 'submitted' && (
                      <>
                        <Tooltip title="Approve">
                          <IconButton size="small" color="success" onClick={() => handleApprove(obligation)}>
                            <CheckIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                        <Tooltip title="Reject">
                          <IconButton size="small" color="error" onClick={() => handleReject(obligation)}>
                            <CloseIcon fontSize="small" />
                          </IconButton>
                        </Tooltip>
                      </>
                    )}
                  </TableCell>
                </TableRow>
                {obligation.prerequisite_snapshot && Object.keys(obligation.prerequisite_snapshot).length > 0 && (
                  <TableRow>
                    <TableCell colSpan={9} sx={{ py: 0, borderBottom: 'none' }}>
                      <Accordion elevation={0} sx={{ bgcolor: 'grey.50' }}>
                        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                          <Typography variant="caption">Prerequisite Snapshot</Typography>
                        </AccordionSummary>
                        <AccordionDetails>
                          <pre style={{ fontSize: '0.75rem', margin: 0 }}>
                            {JSON.stringify(obligation.prerequisite_snapshot, null, 2)}
                          </pre>
                        </AccordionDetails>
                      </Accordion>
                    </TableCell>
                  </TableRow>
                )}
              </React.Fragment>
            ))}
            {obligations.length === 0 && (
              <TableRow>
                <TableCell colSpan={9} align="center">
                  <Typography color="text.secondary">No obligations found</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
      <ObligationFormDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onSubmit={createMutation.mutateAsync}
        siteId={siteId}
        vendors={vendors}
      />
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

interface VendorsTabProps {
  companyId: number;
  onSuccess: (msg: string) => void;
  onError: (msg: string) => void;
}

const VendorsTab: React.FC<VendorsTabProps> = ({ companyId, onSuccess, onError }) => {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editVendor, setEditVendor] = useState<FinanceVendor | undefined>();

  const { data, isLoading } = useQuery({
    queryKey: ['finance-vendors', companyId],
    queryFn: () => financeApi.getVendors(companyId)
  });

  const createMutation = useMutation({
    mutationFn: (data: Partial<FinanceVendor>) => financeApi.createVendor(companyId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['finance-vendors', companyId] });
      onSuccess('Vendor created successfully');
    },
    onError: () => onError('Failed to create vendor')
  });

  const updateMutation = useMutation({
    mutationFn: ({ id, data }: { id: number; data: Partial<FinanceVendor> }) =>
      financeApi.updateVendor(companyId, id, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['finance-vendors', companyId] });
      onSuccess('Vendor updated successfully');
    },
    onError: () => onError('Failed to update vendor')
  });

  const handleSubmit = async (data: Partial<FinanceVendor>) => {
    if (editVendor) {
      await updateMutation.mutateAsync({ id: editVendor.id, data });
    } else {
      await createMutation.mutateAsync(data);
    }
  };

  const handleEdit = (vendor: FinanceVendor) => {
    setEditVendor(vendor);
    setDialogOpen(true);
  };

  if (isLoading) return <CircularProgress size={24} />;

  const vendors = data?.items || [];

  return (
    <>
      <Box display="flex" justifyContent="flex-end" mb={2}>
        <Button
          variant="contained"
          startIcon={<AddIcon />}
          onClick={() => {
            setEditVendor(undefined);
            setDialogOpen(true);
          }}
        >
          Create Vendor
        </Button>
      </Box>
      <TableContainer component={Paper} variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Vendor Name</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Contact</TableCell>
              <TableCell>Email</TableCell>
              <TableCell>Phone</TableCell>
              <TableCell>Status</TableCell>
              <TableCell align="center">Actions</TableCell>
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
                <TableCell>{vendor.contact_phone || '-'}</TableCell>
                <TableCell>
                  <Chip
                    label={vendor.is_active ? 'Active' : 'Inactive'}
                    size="small"
                    color={vendor.is_active ? 'success' : 'default'}
                    variant="outlined"
                  />
                </TableCell>
                <TableCell align="center">
                  <Tooltip title="Edit">
                    <IconButton size="small" onClick={() => handleEdit(vendor)}>
                      <EditIcon fontSize="small" />
                    </IconButton>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
            {vendors.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  <Typography color="text.secondary">No vendors found</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
      <VendorFormDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onSubmit={handleSubmit}
        vendor={editVendor}
      />
    </>
  );
};

interface ActualsTabProps {
  companyId: number;
  siteId: number;
  vendors: FinanceVendor[];
  onSuccess: (msg: string) => void;
  onError: (msg: string) => void;
}

const ActualsTab: React.FC<ActualsTabProps> = ({ companyId, siteId, vendors, onSuccess, onError }) => {
  const queryClient = useQueryClient();
  const [dialogOpen, setDialogOpen] = useState(false);

  const { data, isLoading } = useQuery({
    queryKey: ['finance-actuals', companyId, siteId],
    queryFn: () => financeApi.getActuals(companyId, { site_id: siteId })
  });

  const createMutation = useMutation({
    mutationFn: (data: Partial<FinanceActual>) => financeApi.createActual(companyId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['finance-actuals', companyId, siteId] });
      queryClient.invalidateQueries({ queryKey: ['finance-site-summary'] });
      queryClient.invalidateQueries({ queryKey: ['finance-budgets', companyId, siteId] });
      onSuccess('Actual recorded successfully');
    },
    onError: () => onError('Failed to record actual')
  });

  if (isLoading) return <CircularProgress size={24} />;

  const actuals = data?.items || [];

  return (
    <>
      <Box display="flex" justifyContent="flex-end" mb={2}>
        <Button variant="contained" startIcon={<AddIcon />} onClick={() => setDialogOpen(true)}>
          Record Actual
        </Button>
      </Box>
      <TableContainer component={Paper} variant="outlined">
        <Table>
          <TableHead>
            <TableRow>
              <TableCell>Date</TableCell>
              <TableCell>Category</TableCell>
              <TableCell>Vendor</TableCell>
              <TableCell>Description</TableCell>
              <TableCell>Reference ID</TableCell>
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
                <TableCell>{actual.reference_id || '-'}</TableCell>
                <TableCell align="right">{formatCurrency(actual.amount)}</TableCell>
                <TableCell>
                  <Chip label={actual.source_system} size="small" variant="outlined" />
                </TableCell>
              </TableRow>
            ))}
            {actuals.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} align="center">
                  <Typography color="text.secondary">No actuals found</Typography>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
      <ActualFormDialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        onSubmit={createMutation.mutateAsync}
        siteId={siteId}
        vendors={vendors}
      />
    </>
  );
};

export const SiteFinance: React.FC = () => {
  const { companyId, siteId } = useParams<{ companyId: string; siteId: string }>();
  const [searchParams] = useSearchParams();
  const [tabValue, setTabValue] = useState(0);
  const { setCurrentCompany, setCurrentProject } = useEntityContext();
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success'
  });

  const tabParam = searchParams.get('tab');

  useEffect(() => {
    if (tabParam === 'obligations') {
      setTabValue(1);
    }
  }, [tabParam]);

  const { data: summary, isLoading } = useQuery({
    queryKey: ['finance-site-summary', companyId, siteId],
    queryFn: () => financeApi.getSiteSummary(Number(companyId), Number(siteId)),
    enabled: !!companyId && !!siteId
  });

  const { data: vendorsData } = useQuery({
    queryKey: ['finance-vendors', companyId],
    queryFn: () => financeApi.getVendors(Number(companyId)),
    enabled: !!companyId
  });

  useEffect(() => {
    if (summary && companyId && siteId) {
      setCurrentCompany({ id: Number(companyId), name: summary.company_name || `Company ${companyId}` });
      setCurrentProject({ id: Number(siteId), name: summary.site_name || `Project ${siteId}` });
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

  const handleSuccess = (message: string) => {
    setSnackbar({ open: true, message, severity: 'success' });
  };

  const handleError = (message: string) => {
    setSnackbar({ open: true, message, severity: 'error' });
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

  const vendors = vendorsData?.items || [];

  return (
    <Box p={3}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" sx={{ mb: 3 }}>
        <Typography variant="h5" sx={{ fontWeight: 600 }}>
          Project Finance: {summary.site_name}
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
        <BudgetsTab
          companyId={Number(companyId)}
          siteId={Number(siteId)}
          onSuccess={handleSuccess}
          onError={handleError}
        />
      </TabPanel>
      <TabPanel value={tabValue} index={1}>
        <ObligationsTab
          companyId={Number(companyId)}
          siteId={Number(siteId)}
          vendors={vendors}
          onSuccess={handleSuccess}
          onError={handleError}
        />
      </TabPanel>
      <TabPanel value={tabValue} index={2}>
        <VendorsTab companyId={Number(companyId)} onSuccess={handleSuccess} onError={handleError} />
      </TabPanel>
      <TabPanel value={tabValue} index={3}>
        <ActualsTab
          companyId={Number(companyId)}
          siteId={Number(siteId)}
          vendors={vendors}
          onSuccess={handleSuccess}
          onError={handleError}
        />
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

export default SiteFinance;
