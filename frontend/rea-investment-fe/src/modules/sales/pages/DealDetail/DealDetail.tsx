import React, { useState, useEffect } from 'react';
import {
  Box,
  Typography,
  Paper,
  Grid,
  Chip,
  Button,
  Divider,
  TextField,
  MenuItem,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  Alert,
  CircularProgress,
  Card,
  CardContent,
  Stack,
  IconButton,
  Tooltip
} from '@mui/material';
import { useParams, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import EditIcon from '@mui/icons-material/Edit';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import SwapHorizIcon from '@mui/icons-material/SwapHoriz';

import { useEntityContext } from '../../../../contexts/entityContext';
import { dealsApi } from '../../api/sales';
import {
  DealUpdate,
  SalesStage,
  SALES_STAGE_LABELS,
  SALES_STAGE_COLORS,
  ACTIVE_PIPELINE_STAGES,
  CLOSED_STAGES,
  NEXT_ACTION_STATUS_LABELS,
  SalesStateTransition
} from '../../types';

const formatCurrency = (value?: number): string => {
  if (value === undefined || value === null) return '-';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value);
};

const formatDate = (dateString?: string): string => {
  if (!dateString) return '-';
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  });
};

interface InfoRowProps {
  label: string;
  value: React.ReactNode;
}

const InfoRow: React.FC<InfoRowProps> = ({ label, value }) => (
  <Box sx={{ py: 1 }}>
    <Typography variant="caption" color="text.secondary">
      {label}
    </Typography>
    <Typography variant="body2">{value || '-'}</Typography>
  </Box>
);

export const DealDetail: React.FC = () => {
  const { dealId } = useParams<{ dealId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { setCurrentModule, setCurrentProject } = useEntityContext();
  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState<DealUpdate>({});
  const [stageDialogOpen, setStageDialogOpen] = useState(false);
  const [newStage, setNewStage] = useState<SalesStage | ''>('');
  const [stageNotes, setStageNotes] = useState('');
  const [convertDialogOpen, setConvertDialogOpen] = useState(false);
  const [convertNotes, setConvertNotes] = useState('');

  useEffect(() => {
    setCurrentModule('sales');
    setCurrentProject(null);
  }, [setCurrentModule, setCurrentProject]);

  const {
    data: deal,
    isLoading,
    error
  } = useQuery({
    queryKey: ['deal', dealId],
    queryFn: () => dealsApi.getDeal(Number(dealId)),
    enabled: !!dealId
  });

  const { data: transitions } = useQuery({
    queryKey: ['deal-transitions', dealId],
    queryFn: () => dealsApi.getTransitions(Number(dealId)),
    enabled: !!dealId
  });

  const updateMutation = useMutation({
    mutationFn: (data: DealUpdate) => dealsApi.updateDeal(Number(dealId), data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deal', dealId] });
      queryClient.invalidateQueries({ queryKey: ['deals-pipeline'] });
      setIsEditing(false);
    }
  });

  const stageMutation = useMutation({
    mutationFn: ({ stage, notes }: { stage: SalesStage; notes?: string }) =>
      dealsApi.transitionStage(Number(dealId), stage, notes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deal', dealId] });
      queryClient.invalidateQueries({ queryKey: ['deal-transitions', dealId] });
      queryClient.invalidateQueries({ queryKey: ['deals-pipeline'] });
      setStageDialogOpen(false);
      setNewStage('');
      setStageNotes('');
    }
  });

  const convertMutation = useMutation({
    mutationFn: (notes?: string) => dealsApi.convertToProject(Number(dealId), { notes }),
    onSuccess: response => {
      queryClient.invalidateQueries({ queryKey: ['deal', dealId] });
      queryClient.invalidateQueries({ queryKey: ['deals-pipeline'] });
      setConvertDialogOpen(false);
      navigate(`/asset-management/site/${response.project_id}`);
    }
  });

  const handleStartEdit = () => {
    if (deal) {
      setEditForm({
        name: deal.name,
        developer_name: deal.developer_name,
        address: deal.address,
        city: deal.city,
        state: deal.state,
        system_size_ac: deal.system_size_ac,
        system_size_dc: deal.system_size_dc,
        mipa_per_watt: deal.mipa_per_watt,
        pipeline_value: deal.pipeline_value,
        probability: deal.probability,
        target_close_date: deal.target_close_date,
        next_action: deal.next_action,
        next_action_date: deal.next_action_date,
        next_action_status: deal.next_action_status,
        sales_notes: deal.sales_notes
      });
      setIsEditing(true);
    }
  };

  const handleSaveEdit = () => {
    updateMutation.mutate(editForm);
  };

  const handleStageTransition = () => {
    if (newStage) {
      stageMutation.mutate({ stage: newStage, notes: stageNotes || undefined });
    }
  };

  const handleConvert = () => {
    convertMutation.mutate(convertNotes || undefined);
  };

  if (isLoading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '100%' }}>
        <CircularProgress />
      </Box>
    );
  }

  if (error || !deal) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">Failed to load deal details</Alert>
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/sales')} sx={{ mt: 2 }}>
          Back to Pipeline
        </Button>
      </Box>
    );
  }

  const allStages = [...ACTIVE_PIPELINE_STAGES, ...CLOSED_STAGES];
  const canConvert = !deal.is_converted && deal.sales_stage === SalesStage.MIPASigned;

  return (
    <Box sx={{ height: '100%', overflow: 'auto' }}>
      <Box
        sx={{
          px: 3,
          py: 2,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: 1,
          borderColor: 'divider',
          bgcolor: 'background.paper'
        }}
      >
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
          <IconButton onClick={() => navigate('/sales')}>
            <ArrowBackIcon />
          </IconButton>
          <Box>
            <Typography variant="h5" fontWeight={600}>
              {deal.name}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {deal.company_name || `Company ${deal.company_id}`}
            </Typography>
          </Box>
        </Box>
        <Box sx={{ display: 'flex', gap: 1 }}>
          <Chip
            label={SALES_STAGE_LABELS[deal.sales_stage]}
            sx={{ bgcolor: SALES_STAGE_COLORS[deal.sales_stage], fontWeight: 500 }}
          />
          {deal.is_converted && <Chip label="Converted to Project" color="success" icon={<CheckCircleIcon />} />}
        </Box>
      </Box>

      <Box sx={{ p: 3 }}>
        <Grid container spacing={3}>
          <Grid item xs={12} md={8}>
            <Paper sx={{ p: 3, mb: 3 }}>
              <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
                <Typography variant="h6">Deal Information</Typography>
                {!isEditing ? (
                  <Button startIcon={<EditIcon />} onClick={handleStartEdit} disabled={deal.is_converted}>
                    Edit
                  </Button>
                ) : (
                  <Box sx={{ display: 'flex', gap: 1 }}>
                    <Button onClick={() => setIsEditing(false)}>Cancel</Button>
                    <Button variant="contained" onClick={handleSaveEdit} disabled={updateMutation.isPending}>
                      Save
                    </Button>
                  </Box>
                )}
              </Box>

              {isEditing ? (
                <Grid container spacing={2}>
                  <Grid item xs={12} md={6}>
                    <TextField
                      label="Deal Name"
                      value={editForm.name || ''}
                      onChange={e => setEditForm(prev => ({ ...prev, name: e.target.value }))}
                      fullWidth
                    />
                  </Grid>
                  <Grid item xs={12} md={6}>
                    <TextField
                      label="Developer Name"
                      value={editForm.developer_name || ''}
                      onChange={e => setEditForm(prev => ({ ...prev, developer_name: e.target.value }))}
                      fullWidth
                    />
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <TextField
                      label="Address"
                      value={editForm.address || ''}
                      onChange={e => setEditForm(prev => ({ ...prev, address: e.target.value }))}
                      fullWidth
                    />
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <TextField
                      label="City"
                      value={editForm.city || ''}
                      onChange={e => setEditForm(prev => ({ ...prev, city: e.target.value }))}
                      fullWidth
                    />
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <TextField
                      label="State"
                      value={editForm.state || ''}
                      onChange={e => setEditForm(prev => ({ ...prev, state: e.target.value }))}
                      fullWidth
                    />
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <TextField
                      label="System Size (AC MW)"
                      type="number"
                      value={editForm.system_size_ac || ''}
                      onChange={e =>
                        setEditForm(prev => ({
                          ...prev,
                          system_size_ac: e.target.value ? parseFloat(e.target.value) : undefined
                        }))
                      }
                      fullWidth
                    />
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <TextField
                      label="System Size (DC MW)"
                      type="number"
                      value={editForm.system_size_dc || ''}
                      onChange={e =>
                        setEditForm(prev => ({
                          ...prev,
                          system_size_dc: e.target.value ? parseFloat(e.target.value) : undefined
                        }))
                      }
                      fullWidth
                    />
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <TextField
                      label="MIPA $/Watt"
                      type="number"
                      value={editForm.mipa_per_watt || ''}
                      onChange={e =>
                        setEditForm(prev => ({
                          ...prev,
                          mipa_per_watt: e.target.value ? parseFloat(e.target.value) : undefined
                        }))
                      }
                      fullWidth
                    />
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <TextField
                      label="Pipeline Value"
                      type="number"
                      value={editForm.pipeline_value || ''}
                      onChange={e =>
                        setEditForm(prev => ({
                          ...prev,
                          pipeline_value: e.target.value ? parseFloat(e.target.value) : undefined
                        }))
                      }
                      fullWidth
                    />
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <TextField
                      label="Probability (%)"
                      type="number"
                      value={editForm.probability || ''}
                      onChange={e =>
                        setEditForm(prev => ({
                          ...prev,
                          probability: e.target.value ? parseInt(e.target.value) : undefined
                        }))
                      }
                      fullWidth
                    />
                  </Grid>
                  <Grid item xs={12} md={4}>
                    <TextField
                      label="Target Close Date"
                      type="date"
                      value={editForm.target_close_date || ''}
                      onChange={e => setEditForm(prev => ({ ...prev, target_close_date: e.target.value }))}
                      fullWidth
                      InputLabelProps={{ shrink: true }}
                    />
                  </Grid>
                  <Grid item xs={12}>
                    <TextField
                      label="Notes"
                      value={editForm.sales_notes || ''}
                      onChange={e => setEditForm(prev => ({ ...prev, sales_notes: e.target.value }))}
                      fullWidth
                      multiline
                      rows={3}
                    />
                  </Grid>
                </Grid>
              ) : (
                <Grid container spacing={2}>
                  <Grid item xs={6} md={3}>
                    <InfoRow label="Developer" value={deal.developer_name} />
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <InfoRow label="Quoted By" value={deal.quoted_by} />
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <InfoRow label="System Size (AC)" value={deal.system_size_ac ? `${deal.system_size_ac} MW` : '-'} />
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <InfoRow label="System Size (DC)" value={deal.system_size_dc ? `${deal.system_size_dc} MW` : '-'} />
                  </Grid>
                  <Grid item xs={12}>
                    <Divider sx={{ my: 1 }} />
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <InfoRow label="Address" value={deal.address} />
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <InfoRow label="City" value={deal.city} />
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <InfoRow label="State" value={deal.state} />
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <InfoRow label="Utility Zone" value={deal.utility_zone} />
                  </Grid>
                  <Grid item xs={12}>
                    <Divider sx={{ my: 1 }} />
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <InfoRow label="Pipeline Value" value={formatCurrency(deal.pipeline_value)} />
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <InfoRow label="Probability" value={deal.probability ? `${deal.probability}%` : '-'} />
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <InfoRow label="MIPA $/Watt" value={deal.mipa_per_watt ? `$${deal.mipa_per_watt}` : '-'} />
                  </Grid>
                  <Grid item xs={6} md={3}>
                    <InfoRow label="Target Close" value={formatDate(deal.target_close_date)} />
                  </Grid>
                  {deal.sales_notes && (
                    <Grid item xs={12}>
                      <Divider sx={{ my: 1 }} />
                      <InfoRow label="Notes" value={deal.sales_notes} />
                    </Grid>
                  )}
                </Grid>
              )}
            </Paper>

            <Paper sx={{ p: 3, mb: 3 }}>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Financial Details
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={6} md={3}>
                  <InfoRow label="ITC %" value={deal.itc_percent ? `${deal.itc_percent}%` : '-'} />
                </Grid>
                <Grid item xs={6} md={3}>
                  <InfoRow label="ITC Amount" value={formatCurrency(deal.itc_amount)} />
                </Grid>
                <Grid item xs={6} md={3}>
                  <InfoRow label="FMV" value={formatCurrency(deal.fmv)} />
                </Grid>
                <Grid item xs={6} md={3}>
                  <InfoRow label="Grant Amount" value={formatCurrency(deal.grant_amount)} />
                </Grid>
                <Grid item xs={6} md={3}>
                  <InfoRow label="Tax Equity" value={formatCurrency(deal.tax_equity)} />
                </Grid>
                <Grid item xs={6} md={3}>
                  <InfoRow label="Offtaker" value={deal.offtaker_name} />
                </Grid>
                <Grid item xs={6} md={3}>
                  <InfoRow label="Offtaker Legal Name" value={deal.offtaker_legal_name} />
                </Grid>
                <Grid item xs={6} md={3}>
                  <InfoRow label="Project Company" value={deal.project_company} />
                </Grid>
              </Grid>
            </Paper>

            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Key Dates
              </Typography>
              <Grid container spacing={2}>
                <Grid item xs={6} md={3}>
                  <InfoRow label="Notice to Proceed" value={formatDate(deal.notice_to_proceed_date)} />
                </Grid>
                <Grid item xs={6} md={3}>
                  <InfoRow label="Mechanical Completion" value={formatDate(deal.mechanical_completion_date)} />
                </Grid>
                <Grid item xs={6} md={3}>
                  <InfoRow label="Permission to Operate" value={formatDate(deal.permission_to_operate_date)} />
                </Grid>
                <Grid item xs={6} md={3}>
                  <InfoRow label="Substantial Completion" value={formatDate(deal.substantial_completion_date)} />
                </Grid>
              </Grid>
            </Paper>
          </Grid>

          <Grid item xs={12} md={4}>
            <Paper sx={{ p: 3, mb: 3 }}>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Actions
              </Typography>
              <Stack spacing={2}>
                <Button
                  variant="outlined"
                  fullWidth
                  startIcon={<SwapHorizIcon />}
                  onClick={() => setStageDialogOpen(true)}
                  disabled={deal.is_converted}
                >
                  Change Stage
                </Button>
                <Tooltip title={!canConvert ? 'Deal must be in MIPA Signed stage to convert' : ''}>
                  <span>
                    <Button
                      variant="contained"
                      color="success"
                      fullWidth
                      startIcon={<CheckCircleIcon />}
                      onClick={() => setConvertDialogOpen(true)}
                      disabled={!canConvert}
                    >
                      Convert to Project
                    </Button>
                  </span>
                </Tooltip>
              </Stack>
            </Paper>

            <Paper sx={{ p: 3, mb: 3 }}>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Next Action
              </Typography>
              <InfoRow label="Action" value={deal.next_action} />
              <InfoRow label="Due Date" value={formatDate(deal.next_action_date)} />
              <InfoRow
                label="Status"
                value={deal.next_action_status ? NEXT_ACTION_STATUS_LABELS[deal.next_action_status] : '-'}
              />
              <InfoRow label="Last Action" value={deal.last_action} />
            </Paper>

            <Paper sx={{ p: 3 }}>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Stage History
              </Typography>
              {transitions && transitions.length > 0 ? (
                <Stack spacing={1}>
                  {transitions.slice(0, 10).map((t: SalesStateTransition) => (
                    <Card key={t.id} variant="outlined">
                      <CardContent sx={{ py: 1, '&:last-child': { pb: 1 } }}>
                        <Typography variant="caption" color="text.secondary">
                          {formatDate(t.created_at)}
                        </Typography>
                        <Typography variant="body2">
                          {t.from_state ? `${t.from_state} → ` : ''}
                          {t.to_state}
                        </Typography>
                        {t.notes && (
                          <Typography variant="caption" color="text.secondary">
                            {t.notes}
                          </Typography>
                        )}
                      </CardContent>
                    </Card>
                  ))}
                </Stack>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No stage changes yet
                </Typography>
              )}
            </Paper>
          </Grid>
        </Grid>
      </Box>

      <Dialog open={stageDialogOpen} onClose={() => setStageDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Change Deal Stage</DialogTitle>
        <DialogContent>
          <TextField
            select
            label="New Stage"
            value={newStage}
            onChange={e => setNewStage(e.target.value as SalesStage)}
            fullWidth
            sx={{ mt: 2 }}
          >
            {allStages.map(stage => (
              <MenuItem key={stage} value={stage} disabled={stage === deal.sales_stage}>
                {SALES_STAGE_LABELS[stage]}
              </MenuItem>
            ))}
          </TextField>
          <TextField
            label="Notes (optional)"
            value={stageNotes}
            onChange={e => setStageNotes(e.target.value)}
            fullWidth
            multiline
            rows={2}
            sx={{ mt: 2 }}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setStageDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" onClick={handleStageTransition} disabled={!newStage || stageMutation.isPending}>
            {stageMutation.isPending ? 'Updating...' : 'Update Stage'}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog open={convertDialogOpen} onClose={() => setConvertDialogOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Convert Deal to Project</DialogTitle>
        <DialogContent>
          <Alert severity="info" sx={{ mb: 2 }}>
            This will create a new project in Asset Management based on this deal&apos;s information. The deal will be
            marked as converted and can no longer be modified.
          </Alert>
          <Typography variant="body2" sx={{ mb: 2 }}>
            The following information will be transferred:
          </Typography>
          <Box component="ul" sx={{ pl: 2, mb: 2 }}>
            <li>Name: {deal.name}</li>
            <li>Address: {deal.address || 'Not set'}</li>
            <li>City: {deal.city || 'Not set'}</li>
            <li>State: {deal.state || 'Not set'}</li>
            <li>
              System Size: {deal.system_size_ac || 'Not set'} MW AC / {deal.system_size_dc || 'Not set'} MW DC
            </li>
          </Box>
          <TextField
            label="Conversion Notes (optional)"
            value={convertNotes}
            onChange={e => setConvertNotes(e.target.value)}
            fullWidth
            multiline
            rows={2}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConvertDialogOpen(false)}>Cancel</Button>
          <Button variant="contained" color="success" onClick={handleConvert} disabled={convertMutation.isPending}>
            {convertMutation.isPending ? 'Converting...' : 'Convert to Project'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default DealDetail;
