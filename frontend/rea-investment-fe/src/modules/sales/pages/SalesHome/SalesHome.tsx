import React, { useState, useCallback, useEffect } from 'react';
import {
  Box,
  Typography,
  Card,
  CardContent,
  Chip,
  ToggleButtonGroup,
  ToggleButton,
  Tooltip,
  Paper,
  Stack,
  Avatar,
  LinearProgress,
  Button,
  Dialog,
  DialogTitle,
  DialogContent,
  DialogActions,
  TextField,
  Grid,
  MenuItem,
  InputAdornment,
  IconButton,
  Menu,
  ListItemIcon,
  ListItemText,
  Snackbar,
  Alert
} from '@mui/material';
import { useNavigate } from 'react-router-dom';
import ViewKanbanIcon from '@mui/icons-material/ViewKanban';
import ViewListIcon from '@mui/icons-material/ViewList';
import CalendarTodayIcon from '@mui/icons-material/CalendarToday';
import AddIcon from '@mui/icons-material/Add';
import MoreVertIcon from '@mui/icons-material/MoreVert';
import VisibilityIcon from '@mui/icons-material/Visibility';
import EditIcon from '@mui/icons-material/Edit';
import DragIndicatorIcon from '@mui/icons-material/DragIndicator';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  DndContext,
  DragOverlay,
  useDraggable,
  useDroppable,
  PointerSensor,
  useSensor,
  useSensors,
  DragStartEvent,
  DragEndEvent
} from '@dnd-kit/core';

import { useEntityContext } from '../../../../contexts/entityContext';
import { dealsApi } from '../../api/sales';
import {
  Deal,
  DealCreate,
  DealPipelineResponse,
  SalesStage,
  SALES_STAGE_LABELS,
  SALES_STAGE_COLORS,
  ACTIVE_PIPELINE_STAGES,
  CLOSED_STAGES,
  NextActionStatus,
  NEXT_ACTION_STATUS_LABELS
} from '../../types';

type ViewMode = 'kanban' | 'list';

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
    day: 'numeric'
  });
};

interface DealCardProps {
  deal: Deal;
  onView: () => void;
  onEdit: () => void;
  isDragging?: boolean;
}

const DealCardContent: React.FC<DealCardProps & { dragHandleProps?: any }> = ({
  deal,
  onView,
  onEdit,
  isDragging,
  dragHandleProps
}) => {
  const [anchorEl, setAnchorEl] = useState<null | HTMLElement>(null);
  const menuOpen = Boolean(anchorEl);
  const isOverdue = deal.next_action_date && new Date(deal.next_action_date) < new Date();

  const handleMenuClick = (event: React.MouseEvent<HTMLElement>) => {
    event.stopPropagation();
    setAnchorEl(event.currentTarget);
  };

  const handleMenuClose = () => {
    setAnchorEl(null);
  };

  const handleView = () => {
    handleMenuClose();
    onView();
  };

  const handleEdit = () => {
    handleMenuClose();
    onEdit();
  };

  return (
    <Card
      sx={{
        mb: 1,
        transition: 'box-shadow 0.2s',
        '&:hover': { boxShadow: 3 },
        opacity: isDragging ? 0.5 : deal.is_converted ? 0.6 : 1,
        cursor: deal.is_converted ? 'default' : 'grab'
      }}
    >
      <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          {!deal.is_converted && (
            <Box {...dragHandleProps} sx={{ cursor: 'grab', mr: 0.5, mt: 0.25, color: 'text.secondary' }}>
              <DragIndicatorIcon fontSize="small" />
            </Box>
          )}
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography variant="subtitle2" fontWeight={600} noWrap>
              {deal.name}
            </Typography>
            <Typography variant="caption" color="text.secondary" noWrap>
              {deal.company_name || `Company ${deal.company_id}`}
            </Typography>
          </Box>
          <IconButton size="small" onClick={handleMenuClick} sx={{ ml: 0.5, mt: -0.5 }}>
            <MoreVertIcon fontSize="small" />
          </IconButton>
          <Menu
            anchorEl={anchorEl}
            open={menuOpen}
            onClose={handleMenuClose}
            anchorOrigin={{ vertical: 'bottom', horizontal: 'right' }}
            transformOrigin={{ vertical: 'top', horizontal: 'right' }}
          >
            <MenuItem onClick={handleView}>
              <ListItemIcon>
                <VisibilityIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText>View</ListItemText>
            </MenuItem>
            <MenuItem onClick={handleEdit} disabled={deal.is_converted}>
              <ListItemIcon>
                <EditIcon fontSize="small" />
              </ListItemIcon>
              <ListItemText>Edit</ListItemText>
            </MenuItem>
          </Menu>
        </Box>

        <Box sx={{ mt: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography variant="body2" fontWeight={500}>
            {formatCurrency(deal.pipeline_value)}
          </Typography>
          {deal.probability !== undefined && (
            <Chip label={`${deal.probability}%`} size="small" sx={{ height: 20, fontSize: '0.7rem' }} />
          )}
        </Box>

        {deal.system_size_ac && (
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
            {deal.system_size_ac} MW AC
          </Typography>
        )}

        <Box sx={{ mt: 1, display: 'flex', gap: 1, alignItems: 'center', flexWrap: 'wrap' }}>
          {deal.assigned_owner && (
            <Tooltip title={`${deal.assigned_owner.first_name} ${deal.assigned_owner.last_name}`}>
              <Avatar sx={{ width: 20, height: 20, fontSize: '0.7rem' }}>{deal.assigned_owner.first_name[0]}</Avatar>
            </Tooltip>
          )}
          {deal.next_action_date && (
            <Chip
              icon={<CalendarTodayIcon sx={{ fontSize: 12 }} />}
              label={formatDate(deal.next_action_date)}
              size="small"
              color={isOverdue ? 'error' : 'default'}
              sx={{ height: 20, fontSize: '0.65rem' }}
            />
          )}
          {deal.is_converted && (
            <Chip label="Converted" size="small" color="success" sx={{ height: 20, fontSize: '0.65rem' }} />
          )}
        </Box>
      </CardContent>
    </Card>
  );
};

const DraggableDealCard: React.FC<DealCardProps> = ({ deal, onView, onEdit }) => {
  const { attributes, listeners, setNodeRef, transform, isDragging } = useDraggable({
    id: `deal-${deal.id}`,
    data: { deal },
    disabled: deal.is_converted
  });

  const style = transform
    ? {
        transform: `translate3d(${transform.x}px, ${transform.y}px, 0)`
      }
    : undefined;

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <DealCardContent deal={deal} onView={onView} onEdit={onEdit} isDragging={isDragging} />
    </div>
  );
};

interface KanbanColumnProps {
  stage: SalesStage;
  deals: Deal[];
  onDealView: (dealId: number) => void;
  onDealEdit: (dealId: number) => void;
}

const DroppableKanbanColumn: React.FC<KanbanColumnProps> = ({ stage, deals, onDealView, onDealEdit }) => {
  const { isOver, setNodeRef } = useDroppable({
    id: `stage-${stage}`,
    data: { stage }
  });

  const totalValue = deals.reduce((sum, d) => sum + (d.pipeline_value || 0), 0);
  const isClosed = CLOSED_STAGES.includes(stage);

  return (
    <Paper
      ref={setNodeRef}
      sx={{
        flex: '0 0 200px',
        minWidth: 180,
        maxWidth: 220,
        bgcolor: isOver ? 'primary.50' : isClosed ? 'grey.100' : 'grey.50',
        p: 1.5,
        display: 'flex',
        flexDirection: 'column',
        border: isOver ? '2px dashed' : '2px solid transparent',
        borderColor: isOver ? 'primary.main' : 'transparent',
        transition: 'all 0.2s ease'
      }}
      elevation={0}
    >
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          mb: 1.5,
          pb: 1,
          borderBottom: 3,
          borderColor: SALES_STAGE_COLORS[stage]
        }}
      >
        <Typography variant="caption" fontWeight={600} sx={{ flex: 1 }} noWrap>
          {SALES_STAGE_LABELS[stage]}
        </Typography>
        <Chip label={deals.length} size="small" sx={{ height: 18, minWidth: 24, fontSize: '0.65rem' }} />
      </Box>

      <Typography variant="caption" color="text.secondary" sx={{ mb: 1 }}>
        {formatCurrency(totalValue)}
      </Typography>

      <Box sx={{ flex: 1, overflowY: 'auto', maxHeight: 'calc(100vh - 300px)', minHeight: 100 }}>
        {deals.map(deal => (
          <DraggableDealCard
            key={deal.id}
            deal={deal}
            onView={() => onDealView(deal.id)}
            onEdit={() => onDealEdit(deal.id)}
          />
        ))}
        {deals.length === 0 && (
          <Typography variant="caption" color="text.secondary" sx={{ textAlign: 'center', display: 'block', py: 2 }}>
            {isOver ? 'Drop here' : 'No deals'}
          </Typography>
        )}
      </Box>
    </Paper>
  );
};

const initialDealForm: DealCreate = {
  name: '',
  company_id: 0,
  sales_stage: SalesStage.Prospect,
  developer_name: '',
  address: '',
  city: '',
  state: '',
  system_size_ac: undefined,
  system_size_dc: undefined,
  mipa_per_watt: undefined,
  pipeline_value: undefined,
  probability: undefined,
  target_close_date: '',
  next_action: '',
  next_action_date: '',
  next_action_status: NextActionStatus.None,
  sales_notes: ''
};

export const SalesHome: React.FC = () => {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { currentCompany, setCurrentProject, setCurrentModule } = useEntityContext();
  const [viewMode, setViewMode] = useState<ViewMode>('kanban');
  const [addDialogOpen, setAddDialogOpen] = useState(false);
  const [dealForm, setDealForm] = useState<DealCreate>(initialDealForm);
  const [activeDeal, setActiveDeal] = useState<Deal | null>(null);
  const [snackbar, setSnackbar] = useState<{ open: boolean; message: string; severity: 'success' | 'error' }>({
    open: false,
    message: '',
    severity: 'success'
  });

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 8
      }
    })
  );

  useEffect(() => {
    setCurrentModule('sales');
    setCurrentProject(null);
  }, [setCurrentModule, setCurrentProject]);

  const { data: pipeline, isLoading } = useQuery({
    queryKey: ['deals-pipeline', currentCompany?.id],
    queryFn: () => dealsApi.getPipeline(currentCompany?.id)
  });

  const createDealMutation = useMutation({
    mutationFn: (data: DealCreate) => dealsApi.createDeal(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deals-pipeline'] });
      setAddDialogOpen(false);
      setDealForm({ ...initialDealForm, company_id: currentCompany?.id || 0 });
    }
  });

  const stageTransitionMutation = useMutation({
    mutationFn: ({ dealId, newStage }: { dealId: number; newStage: SalesStage }) =>
      dealsApi.transitionStage(dealId, newStage),
    onSuccess: (_, { newStage }) => {
      queryClient.invalidateQueries({ queryKey: ['deals-pipeline'] });
      setSnackbar({
        open: true,
        message: `Deal moved to ${SALES_STAGE_LABELS[newStage]}`,
        severity: 'success'
      });
    },
    onError: (error: any) => {
      setSnackbar({
        open: true,
        message: error?.response?.data?.detail || 'Failed to move deal',
        severity: 'error'
      });
    }
  });

  const handleDragStart = useCallback((event: DragStartEvent) => {
    const { active } = event;
    const deal = active.data.current?.deal as Deal;
    if (deal) {
      setActiveDeal(deal);
    }
  }, []);

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      setActiveDeal(null);

      if (!over) return;

      const deal = active.data.current?.deal as Deal;
      const targetStage = over.data.current?.stage as SalesStage;

      if (!deal || !targetStage) return;
      if (deal.sales_stage === targetStage) return;
      if (deal.is_converted) return;

      stageTransitionMutation.mutate({ dealId: deal.id, newStage: targetStage });
    },
    [stageTransitionMutation]
  );

  const handleCloseSnackbar = () => {
    setSnackbar(prev => ({ ...prev, open: false }));
  };

  const handleDealView = useCallback(
    (dealId: number) => {
      navigate(`/sales/deal/${dealId}`);
    },
    [navigate]
  );

  const handleDealEdit = useCallback(
    (dealId: number) => {
      navigate(`/sales/deal/${dealId}?mode=edit`);
    },
    [navigate]
  );

  const handleOpenAddDialog = () => {
    setDealForm({ ...initialDealForm, company_id: currentCompany?.id || 0 });
    setAddDialogOpen(true);
  };

  const handleFormChange = (field: keyof DealCreate, value: any) => {
    setDealForm(prev => ({ ...prev, [field]: value }));
  };

  const handleSubmitDeal = () => {
    if (!dealForm.name || !dealForm.company_id) return;
    createDealMutation.mutate(dealForm);
  };

  const allStages = [...ACTIVE_PIPELINE_STAGES, ...CLOSED_STAGES];

  const totalDeals = pipeline
    ? Object.values(pipeline).reduce((sum, stage) => sum + (Array.isArray(stage) ? stage.length : 0), 0)
    : 0;

  const totalValue = pipeline
    ? Object.values(pipeline)
        .flat()
        .reduce((sum, d: Deal) => sum + (d.pipeline_value || 0), 0)
    : 0;

  const stageKeyMap: Record<SalesStage, keyof DealPipelineResponse> = {
    [SalesStage.Prospect]: 'prospect',
    [SalesStage.NDASigned]: 'nda_signed',
    [SalesStage.InputsReceived]: 'inputs_received',
    [SalesStage.Modeling]: 'modeling',
    [SalesStage.ModelReview]: 'model_review',
    [SalesStage.ModelApproved]: 'model_approved',
    [SalesStage.Quoted]: 'quoted',
    [SalesStage.TermSheetNeg]: 'term_sheet_neg',
    [SalesStage.TermSheetSigned]: 'term_sheet_signed',
    [SalesStage.Phase1Diligence]: 'phase_1_diligence',
    [SalesStage.MIPANegotiating]: 'mipa_negotiating',
    [SalesStage.MIPASigned]: 'mipa_signed',
    [SalesStage.Passed]: 'passed',
    [SalesStage.Dead]: 'dead'
  };

  return (
    <Box sx={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      <Box
        sx={{
          px: 3,
          py: 2,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          borderBottom: 1,
          borderColor: 'divider'
        }}
      >
        <Typography variant="h5" fontWeight={600}>
          Deal Pipeline
        </Typography>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
          <Button variant="contained" startIcon={<AddIcon />} onClick={handleOpenAddDialog} size="small">
            Add Deal
          </Button>
          <ToggleButtonGroup value={viewMode} exclusive onChange={(_, v) => v && setViewMode(v)} size="small">
            <ToggleButton value="kanban">
              <ViewKanbanIcon fontSize="small" />
            </ToggleButton>
            <ToggleButton value="list">
              <ViewListIcon fontSize="small" />
            </ToggleButton>
          </ToggleButtonGroup>
        </Box>
      </Box>

      <Box sx={{ px: 3, py: 2, borderBottom: 1, borderColor: 'divider' }}>
        <Stack direction="row" spacing={3}>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Total Deals
            </Typography>
            <Typography variant="h6">{totalDeals}</Typography>
          </Box>
          <Box>
            <Typography variant="caption" color="text.secondary">
              Total Pipeline Value
            </Typography>
            <Typography variant="h6">{formatCurrency(totalValue)}</Typography>
          </Box>
        </Stack>
      </Box>

      {isLoading && <LinearProgress />}

      {!isLoading && pipeline && (
        <Box sx={{ flex: 1, p: 2, overflow: 'auto' }}>
          {viewMode === 'kanban' ? (
            <DndContext sensors={sensors} onDragStart={handleDragStart} onDragEnd={handleDragEnd}>
              <Box sx={{ display: 'flex', gap: 1.5, height: '100%', overflowX: 'auto', pb: 2 }}>
                {allStages.map(stage => (
                  <DroppableKanbanColumn
                    key={stage}
                    stage={stage}
                    deals={(pipeline[stageKeyMap[stage]] as Deal[]) || []}
                    onDealView={handleDealView}
                    onDealEdit={handleDealEdit}
                  />
                ))}
              </Box>
              <DragOverlay>
                {activeDeal ? (
                  <Card
                    sx={{
                      width: 200,
                      boxShadow: 6,
                      opacity: 0.9,
                      transform: 'rotate(3deg)'
                    }}
                  >
                    <CardContent sx={{ py: 1.5, '&:last-child': { pb: 1.5 } }}>
                      <Typography variant="subtitle2" fontWeight={600} noWrap>
                        {activeDeal.name}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {formatCurrency(activeDeal.pipeline_value)}
                      </Typography>
                    </CardContent>
                  </Card>
                ) : null}
              </DragOverlay>
            </DndContext>
          ) : (
            <Paper sx={{ p: 2 }}>
              <Typography variant="body2" color="text.secondary">
                List view coming soon...
              </Typography>
            </Paper>
          )}
        </Box>
      )}

      <Snackbar
        open={snackbar.open}
        autoHideDuration={4000}
        onClose={handleCloseSnackbar}
        anchorOrigin={{ vertical: 'bottom', horizontal: 'center' }}
      >
        <Alert onClose={handleCloseSnackbar} severity={snackbar.severity} sx={{ width: '100%' }}>
          {snackbar.message}
        </Alert>
      </Snackbar>

      <Dialog open={addDialogOpen} onClose={() => setAddDialogOpen(false)} maxWidth="md" fullWidth>
        <DialogTitle>Add New Deal</DialogTitle>
        <DialogContent>
          <Grid container spacing={2} sx={{ mt: 1 }}>
            <Grid item xs={12} md={6}>
              <TextField
                label="Deal Name"
                value={dealForm.name}
                onChange={e => handleFormChange('name', e.target.value)}
                fullWidth
                required
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                label="Developer Name"
                value={dealForm.developer_name}
                onChange={e => handleFormChange('developer_name', e.target.value)}
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                label="Address"
                value={dealForm.address}
                onChange={e => handleFormChange('address', e.target.value)}
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                label="City"
                value={dealForm.city}
                onChange={e => handleFormChange('city', e.target.value)}
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                label="State"
                value={dealForm.state}
                onChange={e => handleFormChange('state', e.target.value)}
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                label="System Size (AC MW)"
                type="number"
                value={dealForm.system_size_ac || ''}
                onChange={e =>
                  handleFormChange('system_size_ac', e.target.value ? parseFloat(e.target.value) : undefined)
                }
                fullWidth
                InputProps={{ endAdornment: <InputAdornment position="end">MW</InputAdornment> }}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                label="System Size (DC MW)"
                type="number"
                value={dealForm.system_size_dc || ''}
                onChange={e =>
                  handleFormChange('system_size_dc', e.target.value ? parseFloat(e.target.value) : undefined)
                }
                fullWidth
                InputProps={{ endAdornment: <InputAdornment position="end">MW</InputAdornment> }}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                label="MIPA $/Watt"
                type="number"
                value={dealForm.mipa_per_watt || ''}
                onChange={e =>
                  handleFormChange('mipa_per_watt', e.target.value ? parseFloat(e.target.value) : undefined)
                }
                fullWidth
                InputProps={{ startAdornment: <InputAdornment position="start">$</InputAdornment> }}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                label="Pipeline Value"
                type="number"
                value={dealForm.pipeline_value || ''}
                onChange={e =>
                  handleFormChange('pipeline_value', e.target.value ? parseFloat(e.target.value) : undefined)
                }
                fullWidth
                InputProps={{ startAdornment: <InputAdornment position="start">$</InputAdornment> }}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                label="Probability"
                type="number"
                value={dealForm.probability || ''}
                onChange={e => handleFormChange('probability', e.target.value ? parseInt(e.target.value) : undefined)}
                fullWidth
                InputProps={{ endAdornment: <InputAdornment position="end">%</InputAdornment> }}
              />
            </Grid>
            <Grid item xs={12} md={4}>
              <TextField
                label="Target Close Date"
                type="date"
                value={dealForm.target_close_date || ''}
                onChange={e => handleFormChange('target_close_date', e.target.value)}
                fullWidth
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={12} md={6}>
              <TextField
                label="Next Action"
                value={dealForm.next_action || ''}
                onChange={e => handleFormChange('next_action', e.target.value)}
                fullWidth
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField
                label="Next Action Date"
                type="date"
                value={dealForm.next_action_date || ''}
                onChange={e => handleFormChange('next_action_date', e.target.value)}
                fullWidth
                InputLabelProps={{ shrink: true }}
              />
            </Grid>
            <Grid item xs={12} md={3}>
              <TextField
                select
                label="Action Status"
                value={dealForm.next_action_status || NextActionStatus.None}
                onChange={e => handleFormChange('next_action_status', e.target.value)}
                fullWidth
              >
                {Object.entries(NEXT_ACTION_STATUS_LABELS).map(([value, label]) => (
                  <MenuItem key={value} value={value}>
                    {label}
                  </MenuItem>
                ))}
              </TextField>
            </Grid>
            <Grid item xs={12}>
              <TextField
                label="Notes"
                value={dealForm.sales_notes || ''}
                onChange={e => handleFormChange('sales_notes', e.target.value)}
                fullWidth
                multiline
                rows={3}
              />
            </Grid>
          </Grid>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setAddDialogOpen(false)}>Cancel</Button>
          <Button
            variant="contained"
            onClick={handleSubmitDeal}
            disabled={!dealForm.name || !dealForm.company_id || createDealMutation.isPending}
          >
            {createDealMutation.isPending ? 'Creating...' : 'Create Deal'}
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default SalesHome;
