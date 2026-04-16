import React, { useState, useEffect, useMemo, useCallback, useRef } from 'react';
import {
  Box,
  Typography,
  Paper,
  Button,
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
  Tooltip,
  Chip
} from '@mui/material';
import { useParams, useNavigate, useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import EditIcon from '@mui/icons-material/Edit';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import SwapHorizIcon from '@mui/icons-material/SwapHoriz';
import SaveIcon from '@mui/icons-material/Save';
import CancelIcon from '@mui/icons-material/Cancel';

import { useEntityContext } from '../../../../contexts/entityContext';
import { ApiClient } from '../../../../api';
import { dealsApi } from '../../api/sales';
import {
  Deal,
  DealUpdate,
  SalesStage,
  SALES_STAGE_LABELS,
  ACTIVE_PIPELINE_STAGES,
  CLOSED_STAGES,
  NEXT_ACTION_STATUS_LABELS,
  SalesStateTransition
} from '../../types';
import type { DealEntityRole, ProjectEntity } from '../../../../api/entities';
import {
  DealExecutiveSummary,
  DealReadinessWidget,
  DealDraggableCardLayout,
  DealCardItem,
  DealOverviewCard,
  LocationCard,
  SystemDetailsCard,
  FinancialsCard,
  OfftakerCard,
  TimelineCard
} from './components';

const formatDate = (dateString?: string): string => {
  if (!dateString) return '-';
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  });
};

const CARD_REQUIRED_FIELDS: Record<string, (keyof Deal)[]> = {
  overview: ['name', 'developer_name'],
  location: ['address', 'city', 'state'],
  system: ['system_size_ac', 'system_size_dc', 'ownership_structure'],
  financials: ['pipeline_value', 'probability', 'utility_rate'],
  offtaker: ['offtaker_name'],
  timeline: ['next_action_date']
};

const getMissingFields = (deal: Deal, fields: (keyof Deal)[]): string[] => {
  return fields.filter(field => {
    const value = deal[field];
    return value === null || value === undefined || value === '';
  });
};

const generateHeaderSummary = (cardId: string, deal: Deal): string => {
  switch (cardId) {
    case 'overview':
      return [deal.developer_name, deal.company_name].filter(Boolean).join(' | ');
    case 'location':
      return [deal.city, deal.state].filter(Boolean).join(', ') || deal.address || '';
    case 'system': {
      const parts = [];
      if (deal.system_size_ac) parts.push(`${deal.system_size_ac} kW AC`);
      if (deal.system_size_dc) parts.push(`${deal.system_size_dc} kW DC`);
      return parts.join(' / ');
    }
    case 'financials':
      if (deal.pipeline_value) {
        return `$${(deal.pipeline_value / 1000000).toFixed(1)}M pipeline`;
      }
      return '';
    case 'offtaker':
      return deal.offtaker_name || '';
    case 'timeline':
      return deal.next_action_date ? `Next: ${formatDate(deal.next_action_date)}` : '';
    default:
      return '';
  }
};

interface EntityChangeEntry {
  role: DealEntityRole;
  entityId: number | null;
  entityName: string | null;
}

export const DealDetail: React.FC = () => {
  const { dealId } = useParams<{ dealId: string }>();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { currentCompany, setCurrentModule, setCurrentProject } = useEntityContext();
  const [isEditing, setIsEditing] = useState(searchParams.get('mode') === 'edit');
  const [editForm, setEditForm] = useState<DealUpdate>({});
  const [stageDialogOpen, setStageDialogOpen] = useState(false);
  const [newStage, setNewStage] = useState<SalesStage | ''>('');
  const [stageNotes, setStageNotes] = useState('');
  const [convertDialogOpen, setConvertDialogOpen] = useState(false);
  const [convertNotes, setConvertNotes] = useState('');
  const pendingEntityChangesRef = useRef<EntityChangeEntry[]>([]);

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

  const { data: entityAssignments } = useQuery({
    queryKey: ['deal-entity-assignments', dealId],
    queryFn: async () => {
      const result = await ApiClient.dealEntityAssignments.list(Number(dealId));
      return result.items;
    },
    enabled: !!dealId
  });

  const { data: transitions } = useQuery({
    queryKey: ['deal-transitions', dealId],
    queryFn: () => dealsApi.getTransitions(Number(dealId)),
    enabled: !!dealId
  });

  const portfolioId = deal?.company_id || currentCompany?.id || 0;

  const saveEntityAssignments = useCallback(async () => {
    const changes = pendingEntityChangesRef.current;
    if (changes.length === 0) return;

    for (const change of changes) {
      const existing = entityAssignments?.find(a => a.role === change.role);
      if (change.entityId) {
        if (existing) {
          await ApiClient.dealEntityAssignments.update(Number(dealId), existing.id, {
            entity_id: change.entityId,
            role: change.role
          });
        } else {
          await ApiClient.dealEntityAssignments.create(Number(dealId), {
            entity_id: change.entityId,
            role: change.role
          });
        }
      } else if (existing) {
        await ApiClient.dealEntityAssignments.delete(Number(dealId), existing.id);
      }
    }
    pendingEntityChangesRef.current = [];
  }, [dealId, entityAssignments]);

  const updateMutation = useMutation({
    mutationFn: async (data: DealUpdate) => {
      const result = await dealsApi.updateDeal(Number(dealId), data);
      await saveEntityAssignments();
      return result;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['deal', dealId] });
      queryClient.invalidateQueries({ queryKey: ['deal-entity-assignments', dealId] });
      queryClient.invalidateQueries({ queryKey: ['deals-pipeline'] });
      setIsEditing(false);
      setEditForm({});
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
    mutationFn: (data: { company_id: number; notes?: string }) =>
      dealsApi.convertToProject(Number(dealId), {
        company_id: data.company_id,
        additional_notes: data.notes
      }),
    onSuccess: response => {
      queryClient.invalidateQueries({ queryKey: ['deal', dealId] });
      queryClient.invalidateQueries({ queryKey: ['deals-pipeline'] });
      setConvertDialogOpen(false);
      navigate(`/project-hub/companies/${deal?.company_id || 1}/sites/${response.project_id}`);
    }
  });

  const handleStartEdit = React.useCallback(() => {
    if (deal) {
      setEditForm({});
      pendingEntityChangesRef.current = [];
      setIsEditing(true);
    }
  }, [deal]);

  const handleCancelEdit = () => {
    setIsEditing(false);
    setEditForm({});
    pendingEntityChangesRef.current = [];
  };

  const handleSaveEdit = () => {
    updateMutation.mutate(editForm);
  };

  const handleFormChange = (field: keyof DealUpdate, value: any) => {
    setEditForm(prev => ({ ...prev, [field]: value }));
  };

  const handleEntityChange = useCallback(
    (role: DealEntityRole, entityId: number | null, entity: ProjectEntity | null) => {
      const existing = pendingEntityChangesRef.current.findIndex(c => c.role === role);
      const entry: EntityChangeEntry = { role, entityId, entityName: entity?.name ?? null };
      if (existing >= 0) {
        pendingEntityChangesRef.current[existing] = entry;
      } else {
        pendingEntityChangesRef.current.push(entry);
      }
    },
    []
  );

  const handleStageTransition = () => {
    if (newStage) {
      stageMutation.mutate({ stage: newStage, notes: stageNotes || undefined });
    }
  };

  const handleConvert = () => {
    if (!deal?.company_id) return;
    convertMutation.mutate({
      company_id: deal.company_id,
      notes: convertNotes || undefined
    });
  };

  const entityCardProps = useMemo(
    () => ({
      entityAssignments: entityAssignments || [],
      onEntityChange: handleEntityChange,
      portfolioId
    }),
    [entityAssignments, handleEntityChange, portfolioId]
  );

  const cards: DealCardItem[] = useMemo(() => {
    if (!deal) return [];

    const cardConfigs = [
      {
        id: 'overview',
        title: 'Deal Overview',
        component: DealOverviewCard
      },
      {
        id: 'location',
        title: 'Location',
        component: LocationCard
      },
      {
        id: 'system',
        title: 'System Details',
        component: SystemDetailsCard
      },
      {
        id: 'financials',
        title: 'Financials',
        component: FinancialsCard
      },
      {
        id: 'offtaker',
        title: 'Offtaker',
        component: OfftakerCard
      },
      {
        id: 'timeline',
        title: 'Timeline & Dates',
        component: TimelineCard
      }
    ];

    return cardConfigs.map(config => {
      const requiredFields = CARD_REQUIRED_FIELDS[config.id] || [];
      const missingFields = getMissingFields(deal, requiredFields);
      const Component = config.component;

      return {
        id: config.id,
        title: config.title,
        hasMissingFields: missingFields.length > 0,
        missingFieldCount: missingFields.length,
        missingFieldNames: missingFields,
        headerSummary: generateHeaderSummary(config.id, deal),
        content: (
          <Component
            deal={deal}
            isEditing={isEditing}
            editForm={editForm}
            onFormChange={handleFormChange}
            onStartEdit={handleStartEdit}
            showEditButton={!isEditing}
            {...entityCardProps}
          />
        )
      };
    });
  }, [deal, isEditing, editForm, handleStartEdit, entityCardProps]);

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
        <Button startIcon={<ArrowBackIcon />} onClick={() => navigate('/acquisitions')} sx={{ mt: 2 }}>
          Back to Pipeline
        </Button>
      </Box>
    );
  }

  const allStages = [...ACTIVE_PIPELINE_STAGES, ...CLOSED_STAGES];
  const canConvert =
    !deal.is_converted &&
    (deal.sales_stage === SalesStage.MIPASigned || deal.sales_stage === SalesStage.TermSheetSigned);

  return (
    <Box sx={{ height: '100%', overflow: 'auto' }}>
      {deal.is_converted && (
        <Alert
          severity="info"
          sx={{ m: 2, borderRadius: 2, '& .MuiAlert-message': { width: '100%' } }}
          action={
            <Button
              color="inherit"
              size="small"
              variant="outlined"
              onClick={() => navigate(`/project-hub/companies/${deal.company_id}/sites/${deal.converted_project_id}`)}
            >
              Continue in Project Hub
            </Button>
          }
        >
          <Typography variant="subtitle1" fontWeight={600}>
            Deal Converted to Project
          </Typography>
          <Typography variant="body2">
            This deal has been converted and is now read-only. All further work should be done in the Project Hub.
          </Typography>
        </Alert>
      )}
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
          <Button
            variant="text"
            startIcon={<ArrowBackIcon />}
            onClick={() => navigate('/acquisitions')}
            sx={{ minWidth: 'auto' }}
          >
            Back to Pipeline
          </Button>
        </Box>
        <Stack direction="row" spacing={1}>
          {isEditing ? (
            <>
              <Button
                variant="outlined"
                startIcon={<CancelIcon />}
                onClick={handleCancelEdit}
                disabled={updateMutation.isPending}
              >
                Cancel
              </Button>
              <Button
                variant="contained"
                startIcon={<SaveIcon />}
                onClick={handleSaveEdit}
                disabled={updateMutation.isPending}
              >
                {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
              </Button>
            </>
          ) : (
            <>
              <Button
                variant="outlined"
                startIcon={<EditIcon />}
                onClick={handleStartEdit}
                disabled={deal.is_converted}
              >
                Edit Deal
              </Button>
              <Button
                variant="outlined"
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
                    startIcon={<CheckCircleIcon />}
                    onClick={() => setConvertDialogOpen(true)}
                    disabled={!canConvert}
                  >
                    Convert to Project
                  </Button>
                </span>
              </Tooltip>
            </>
          )}
        </Stack>
      </Box>

      <Box sx={{ p: 3 }}>
        <DealExecutiveSummary deal={deal} entityAssignments={entityAssignments} />

        {!deal.is_converted && <DealReadinessWidget deal={deal} entityAssignments={entityAssignments} />}

        <Box sx={{ display: 'flex', gap: 3 }}>
          <Box sx={{ flex: 1 }}>
            <DealDraggableCardLayout
              cards={cards}
              storageKey={`deal_cards_${dealId}`}
              columns={2}
              defaultOpenCards={['overview', 'location']}
            />
          </Box>

          <Box sx={{ width: 320, flexShrink: 0 }}>
            <Paper sx={{ p: 2, mb: 2 }}>
              <Typography variant="subtitle1" fontWeight={600} sx={{ mb: 1.5 }}>
                Stage History
              </Typography>
              {transitions && transitions.length > 0 ? (
                <Stack spacing={1}>
                  {transitions.slice(0, 8).map((t: SalesStateTransition) => (
                    <Card key={t.id} variant="outlined">
                      <CardContent sx={{ py: 1, px: 1.5, '&:last-child': { pb: 1 } }}>
                        <Typography variant="caption" color="text.secondary">
                          {formatDate(t.created_at)}
                        </Typography>
                        <Typography variant="body2" fontSize="0.85rem">
                          {t.from_state ? (
                            <>
                              <Chip
                                label={SALES_STAGE_LABELS[t.from_state as SalesStage] || t.from_state}
                                size="small"
                                sx={{ height: 18, fontSize: '0.65rem', mr: 0.5 }}
                              />
                              →
                              <Chip
                                label={SALES_STAGE_LABELS[t.to_state as SalesStage] || t.to_state}
                                size="small"
                                sx={{ height: 18, fontSize: '0.65rem', ml: 0.5 }}
                              />
                            </>
                          ) : (
                            <Chip
                              label={SALES_STAGE_LABELS[t.to_state as SalesStage] || t.to_state}
                              size="small"
                              sx={{ height: 18, fontSize: '0.65rem' }}
                            />
                          )}
                        </Typography>
                        {t.notes && (
                          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 0.5 }}>
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

            <Paper sx={{ p: 2 }}>
              <Typography variant="subtitle1" fontWeight={600} sx={{ mb: 1.5 }}>
                Next Action
              </Typography>
              <Box sx={{ py: 0.5 }}>
                <Typography variant="caption" color="text.secondary">
                  Action
                </Typography>
                <Typography variant="body2">{deal.next_action || '-'}</Typography>
              </Box>
              <Box sx={{ py: 0.5 }}>
                <Typography variant="caption" color="text.secondary">
                  Due Date
                </Typography>
                <Typography variant="body2">{formatDate(deal.next_action_date)}</Typography>
              </Box>
              <Box sx={{ py: 0.5 }}>
                <Typography variant="caption" color="text.secondary">
                  Status
                </Typography>
                <Typography variant="body2">
                  {deal.next_action_status ? NEXT_ACTION_STATUS_LABELS[deal.next_action_status] : '-'}
                </Typography>
              </Box>
            </Paper>
          </Box>
        </Box>
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
              System Size: {deal.system_size_ac || 'Not set'} kW AC / {deal.system_size_dc || 'Not set'} kW DC
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
