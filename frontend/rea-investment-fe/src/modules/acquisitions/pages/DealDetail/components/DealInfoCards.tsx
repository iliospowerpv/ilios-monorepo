import React from 'react';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import MenuItem from '@mui/material/MenuItem';
import InputAdornment from '@mui/material/InputAdornment';
import Button from '@mui/material/Button';
import EditIcon from '@mui/icons-material/Edit';
import { Deal, DealUpdate, NextActionStatus, NEXT_ACTION_STATUS_LABELS } from '../../../types';
import { EntityPicker } from '../../../../../components/common/EntityPicker/EntityPicker';
import type { DealEntityAssignment, DealEntityRole, ProjectEntity } from '../../../../../api/entities';

interface InfoRowProps {
  label: string;
  value: React.ReactNode;
}

const InfoRow: React.FC<InfoRowProps> = ({ label, value }) => (
  <Box sx={{ py: 0.75 }}>
    <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.25 }}>
      {label}
    </Typography>
    <Typography variant="body2">{value || '—'}</Typography>
  </Box>
);

const formatCurrency = (value?: number): string => {
  if (value === undefined || value === null) return '—';
  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: 0,
    maximumFractionDigits: 0
  }).format(value);
};

const formatDate = (dateString?: string): string => {
  if (!dateString) return '—';
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  });
};

const getAssignmentForRole = (
  assignments: DealEntityAssignment[] | undefined,
  role: DealEntityRole
): DealEntityAssignment | undefined => {
  return assignments?.find(a => a.role === role);
};

interface DealCardContentProps {
  deal: Deal;
  isEditing: boolean;
  editForm: DealUpdate;
  onFormChange: (field: keyof DealUpdate, value: any) => void;
  onStartEdit?: () => void;
  showEditButton?: boolean;
  entityAssignments?: DealEntityAssignment[];
  onEntityChange?: (role: DealEntityRole, entityId: number | null, entity: ProjectEntity | null) => void;
  portfolioId?: number;
}

export const DealOverviewCard: React.FC<DealCardContentProps> = ({
  deal,
  isEditing,
  editForm,
  onFormChange,
  onStartEdit,
  showEditButton = true,
  entityAssignments,
  onEntityChange,
  portfolioId
}) => {
  const developerAssignment = getAssignmentForRole(entityAssignments, 'developer');
  const developerEntityId = developerAssignment?.entity_id ?? null;
  const developerDisplayName = developerAssignment?.entity_name || deal.developer_name;

  if (isEditing) {
    return (
      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          <TextField
            label="Deal Name"
            value={editForm.name ?? deal.name}
            onChange={e => onFormChange('name', e.target.value)}
            fullWidth
            size="small"
          />
        </Grid>
        <Grid item xs={12} md={6}>
          {portfolioId && onEntityChange ? (
            <EntityPicker
              portfolioId={portfolioId}
              entityType="developer"
              value={developerEntityId}
              onChange={(entityId, entity) => {
                onEntityChange('developer', entityId, entity);
                onFormChange('developer_name', entity?.name ?? '');
              }}
              label="Developer"
              size="small"
            />
          ) : (
            <TextField
              label="Developer Name"
              value={editForm.developer_name ?? deal.developer_name ?? ''}
              onChange={e => onFormChange('developer_name', e.target.value)}
              fullWidth
              size="small"
            />
          )}
        </Grid>
        <Grid item xs={12}>
          <TextField
            label="Sales Notes"
            value={editForm.sales_notes ?? deal.sales_notes ?? ''}
            onChange={e => onFormChange('sales_notes', e.target.value)}
            fullWidth
            multiline
            rows={3}
            size="small"
          />
        </Grid>
      </Grid>
    );
  }

  return (
    <Box>
      <Grid container spacing={2}>
        <Grid item xs={6} md={4}>
          <InfoRow label="Deal Name" value={deal.name} />
        </Grid>
        <Grid item xs={6} md={4}>
          <InfoRow label="Developer" value={developerDisplayName} />
        </Grid>
        <Grid item xs={6} md={4}>
          <InfoRow label="Company" value={deal.company_name || `Company ${deal.company_id}`} />
        </Grid>
        <Grid item xs={12}>
          <InfoRow label="Sales Notes" value={deal.sales_notes} />
        </Grid>
      </Grid>
      {showEditButton && !deal.is_converted && onStartEdit && (
        <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
          <Button size="small" startIcon={<EditIcon />} onClick={onStartEdit}>
            Edit
          </Button>
        </Box>
      )}
    </Box>
  );
};

export const LocationCard: React.FC<DealCardContentProps> = ({
  deal,
  isEditing,
  editForm,
  onFormChange,
  onStartEdit,
  showEditButton = true
}) => {
  if (isEditing) {
    return (
      <Grid container spacing={2}>
        <Grid item xs={12}>
          <TextField
            label="Address"
            value={editForm.address ?? deal.address ?? ''}
            onChange={e => onFormChange('address', e.target.value)}
            fullWidth
            size="small"
          />
        </Grid>
        <Grid item xs={6}>
          <TextField
            label="City"
            value={editForm.city ?? deal.city ?? ''}
            onChange={e => onFormChange('city', e.target.value)}
            fullWidth
            size="small"
          />
        </Grid>
        <Grid item xs={6}>
          <TextField
            label="State"
            value={editForm.state ?? deal.state ?? ''}
            onChange={e => onFormChange('state', e.target.value)}
            fullWidth
            size="small"
            inputProps={{ maxLength: 2 }}
            helperText="2-letter code"
          />
        </Grid>
        <Grid item xs={6}>
          <TextField
            label="Latitude"
            type="number"
            value={editForm.latitude ?? deal.latitude ?? ''}
            onChange={e => onFormChange('latitude', e.target.value ? parseFloat(e.target.value) : undefined)}
            fullWidth
            size="small"
          />
        </Grid>
        <Grid item xs={6}>
          <TextField
            label="Longitude"
            type="number"
            value={editForm.longitude ?? deal.longitude ?? ''}
            onChange={e => onFormChange('longitude', e.target.value ? parseFloat(e.target.value) : undefined)}
            fullWidth
            size="small"
          />
        </Grid>
      </Grid>
    );
  }

  return (
    <Box>
      <Grid container spacing={2}>
        <Grid item xs={12}>
          <InfoRow label="Address" value={deal.address} />
        </Grid>
        <Grid item xs={6} md={4}>
          <InfoRow label="City" value={deal.city} />
        </Grid>
        <Grid item xs={6} md={4}>
          <InfoRow label="State" value={deal.state} />
        </Grid>
        <Grid item xs={6} md={4}>
          <InfoRow
            label="Coordinates"
            value={deal.latitude && deal.longitude ? `${deal.latitude}, ${deal.longitude}` : undefined}
          />
        </Grid>
      </Grid>
      {showEditButton && !deal.is_converted && onStartEdit && (
        <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
          <Button size="small" startIcon={<EditIcon />} onClick={onStartEdit}>
            Edit
          </Button>
        </Box>
      )}
    </Box>
  );
};

export const SystemDetailsCard: React.FC<DealCardContentProps> = ({
  deal,
  isEditing,
  editForm,
  onFormChange,
  onStartEdit,
  showEditButton = true,
  entityAssignments,
  onEntityChange,
  portfolioId
}) => {
  const projectCoAssignment = getAssignmentForRole(entityAssignments, 'project_company');
  const projectCoEntityId = projectCoAssignment?.entity_id ?? null;
  const projectCoDisplayName = projectCoAssignment?.entity_name || deal.project_company;

  if (isEditing) {
    return (
      <Grid container spacing={2}>
        <Grid item xs={6}>
          <TextField
            label="System Size (AC)"
            type="number"
            value={editForm.system_size_ac ?? deal.system_size_ac ?? ''}
            onChange={e => onFormChange('system_size_ac', e.target.value ? parseFloat(e.target.value) : undefined)}
            fullWidth
            size="small"
            InputProps={{ endAdornment: <InputAdornment position="end">kW</InputAdornment> }}
          />
        </Grid>
        <Grid item xs={6}>
          <TextField
            label="System Size (DC)"
            type="number"
            value={editForm.system_size_dc ?? deal.system_size_dc ?? ''}
            onChange={e => onFormChange('system_size_dc', e.target.value ? parseFloat(e.target.value) : undefined)}
            fullWidth
            size="small"
            InputProps={{ endAdornment: <InputAdornment position="end">kW</InputAdornment> }}
          />
        </Grid>
        <Grid item xs={6}>
          <TextField
            label="Ownership Structure"
            value={editForm.ownership_structure ?? deal.ownership_structure ?? ''}
            onChange={e => onFormChange('ownership_structure', e.target.value)}
            fullWidth
            size="small"
          />
        </Grid>
        <Grid item xs={6}>
          {portfolioId && onEntityChange ? (
            <EntityPicker
              portfolioId={portfolioId}
              value={projectCoEntityId}
              onChange={(entityId, entity) => {
                onEntityChange('project_company', entityId, entity);
                onFormChange('project_company', entity?.name ?? '');
              }}
              label="Project Company"
              size="small"
            />
          ) : (
            <TextField
              label="Project Company"
              value={editForm.project_company ?? deal.project_company ?? ''}
              onChange={e => onFormChange('project_company', e.target.value)}
              fullWidth
              size="small"
            />
          )}
        </Grid>
      </Grid>
    );
  }

  return (
    <Box>
      <Grid container spacing={2}>
        <Grid item xs={6} md={3}>
          <InfoRow label="System Size (AC)" value={deal.system_size_ac ? `${deal.system_size_ac} kW` : undefined} />
        </Grid>
        <Grid item xs={6} md={3}>
          <InfoRow label="System Size (DC)" value={deal.system_size_dc ? `${deal.system_size_dc} kW` : undefined} />
        </Grid>
        <Grid item xs={6} md={3}>
          <InfoRow label="Ownership Structure" value={deal.ownership_structure} />
        </Grid>
        <Grid item xs={6} md={3}>
          <InfoRow label="Project Company" value={projectCoDisplayName} />
        </Grid>
      </Grid>
      {showEditButton && !deal.is_converted && onStartEdit && (
        <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
          <Button size="small" startIcon={<EditIcon />} onClick={onStartEdit}>
            Edit
          </Button>
        </Box>
      )}
    </Box>
  );
};

export const FinancialsCard: React.FC<DealCardContentProps> = ({
  deal,
  isEditing,
  editForm,
  onFormChange,
  onStartEdit,
  showEditButton = true
}) => {
  if (isEditing) {
    return (
      <Grid container spacing={2}>
        <Grid item xs={6}>
          <TextField
            label="Pipeline Value"
            type="number"
            value={editForm.pipeline_value ?? deal.pipeline_value ?? ''}
            onChange={e => onFormChange('pipeline_value', e.target.value ? parseFloat(e.target.value) : undefined)}
            fullWidth
            size="small"
            InputProps={{ startAdornment: <InputAdornment position="start">$</InputAdornment> }}
          />
        </Grid>
        <Grid item xs={6}>
          <TextField
            label="Probability"
            type="number"
            value={editForm.probability ?? deal.probability ?? ''}
            onChange={e => onFormChange('probability', e.target.value ? parseInt(e.target.value) : undefined)}
            fullWidth
            size="small"
            InputProps={{ endAdornment: <InputAdornment position="end">%</InputAdornment> }}
          />
        </Grid>
        <Grid item xs={6}>
          <TextField
            label="MIPA $/Watt"
            type="number"
            value={editForm.mipa_per_watt ?? deal.mipa_per_watt ?? ''}
            onChange={e => onFormChange('mipa_per_watt', e.target.value ? parseFloat(e.target.value) : undefined)}
            fullWidth
            size="small"
            InputProps={{ startAdornment: <InputAdornment position="start">$</InputAdornment> }}
          />
        </Grid>
        <Grid item xs={6}>
          <TextField
            label="Utility Rate"
            value={editForm.utility_rate ?? deal.utility_rate ?? ''}
            onChange={e => onFormChange('utility_rate', e.target.value)}
            fullWidth
            size="small"
          />
        </Grid>
        <Grid item xs={6}>
          <TextField
            label="ITC Percent"
            type="number"
            value={editForm.itc_percent ?? deal.itc_percent ?? ''}
            onChange={e => onFormChange('itc_percent', e.target.value ? parseFloat(e.target.value) : undefined)}
            fullWidth
            size="small"
            InputProps={{ endAdornment: <InputAdornment position="end">%</InputAdornment> }}
          />
        </Grid>
        <Grid item xs={6}>
          <TextField
            label="ITC Amount"
            type="number"
            value={editForm.itc_amount ?? deal.itc_amount ?? ''}
            onChange={e => onFormChange('itc_amount', e.target.value ? parseFloat(e.target.value) : undefined)}
            fullWidth
            size="small"
            InputProps={{ startAdornment: <InputAdornment position="start">$</InputAdornment> }}
          />
        </Grid>
        <Grid item xs={6}>
          <TextField
            label="FMV"
            type="number"
            value={editForm.fmv ?? deal.fmv ?? ''}
            onChange={e => onFormChange('fmv', e.target.value ? parseFloat(e.target.value) : undefined)}
            fullWidth
            size="small"
            InputProps={{ startAdornment: <InputAdornment position="start">$</InputAdornment> }}
          />
        </Grid>
        <Grid item xs={6}>
          <TextField
            label="Tax Equity"
            type="number"
            value={editForm.tax_equity ?? deal.tax_equity ?? ''}
            onChange={e => onFormChange('tax_equity', e.target.value ? parseFloat(e.target.value) : undefined)}
            fullWidth
            size="small"
            InputProps={{ startAdornment: <InputAdornment position="start">$</InputAdornment> }}
          />
        </Grid>
      </Grid>
    );
  }

  return (
    <Box>
      <Grid container spacing={2}>
        <Grid item xs={6} md={3}>
          <InfoRow label="Pipeline Value" value={formatCurrency(deal.pipeline_value)} />
        </Grid>
        <Grid item xs={6} md={3}>
          <InfoRow label="Probability" value={deal.probability !== undefined ? `${deal.probability}%` : undefined} />
        </Grid>
        <Grid item xs={6} md={3}>
          <InfoRow label="MIPA $/Watt" value={deal.mipa_per_watt ? `$${deal.mipa_per_watt}` : undefined} />
        </Grid>
        <Grid item xs={6} md={3}>
          <InfoRow label="Utility Rate" value={deal.utility_rate} />
        </Grid>
        <Grid item xs={6} md={3}>
          <InfoRow label="ITC Percent" value={deal.itc_percent ? `${deal.itc_percent}%` : undefined} />
        </Grid>
        <Grid item xs={6} md={3}>
          <InfoRow label="ITC Amount" value={formatCurrency(deal.itc_amount)} />
        </Grid>
        <Grid item xs={6} md={3}>
          <InfoRow label="FMV" value={formatCurrency(deal.fmv)} />
        </Grid>
        <Grid item xs={6} md={3}>
          <InfoRow label="Tax Equity" value={formatCurrency(deal.tax_equity)} />
        </Grid>
      </Grid>
      {showEditButton && !deal.is_converted && onStartEdit && (
        <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
          <Button size="small" startIcon={<EditIcon />} onClick={onStartEdit}>
            Edit
          </Button>
        </Box>
      )}
    </Box>
  );
};

export const OfftakerCard: React.FC<DealCardContentProps> = ({
  deal,
  isEditing,
  editForm,
  onFormChange,
  onStartEdit,
  showEditButton = true,
  entityAssignments,
  onEntityChange,
  portfolioId
}) => {
  const offtakerAssignment = getAssignmentForRole(entityAssignments, 'offtaker');
  const offtakerEntityId = offtakerAssignment?.entity_id ?? null;
  const offtakerDisplayName = offtakerAssignment?.entity_name || deal.offtaker_name;

  if (isEditing) {
    return (
      <Grid container spacing={2}>
        <Grid item xs={12} md={6}>
          {portfolioId && onEntityChange ? (
            <EntityPicker
              portfolioId={portfolioId}
              entityType="offtaker"
              value={offtakerEntityId}
              onChange={(entityId, entity) => {
                onEntityChange('offtaker', entityId, entity);
                onFormChange('offtaker_name', entity?.name ?? '');
              }}
              label="Offtaker"
              size="small"
            />
          ) : (
            <TextField
              label="Offtaker Name"
              value={editForm.offtaker_name ?? deal.offtaker_name ?? ''}
              onChange={e => onFormChange('offtaker_name', e.target.value)}
              fullWidth
              size="small"
            />
          )}
        </Grid>
        <Grid item xs={12} md={6}>
          <TextField
            label="Offtaker Legal Name"
            value={editForm.offtaker_legal_name ?? deal.offtaker_legal_name ?? ''}
            onChange={e => onFormChange('offtaker_legal_name', e.target.value)}
            fullWidth
            size="small"
          />
        </Grid>
        <Grid item xs={12} md={6}>
          <TextField
            label="Utility Zone"
            value={editForm.utility_zone ?? deal.utility_zone ?? ''}
            onChange={e => onFormChange('utility_zone', e.target.value)}
            fullWidth
            size="small"
          />
        </Grid>
      </Grid>
    );
  }

  return (
    <Box>
      <Grid container spacing={2}>
        <Grid item xs={6} md={4}>
          <InfoRow label="Offtaker Name" value={offtakerDisplayName} />
        </Grid>
        <Grid item xs={6} md={4}>
          <InfoRow label="Offtaker Legal Name" value={deal.offtaker_legal_name} />
        </Grid>
        <Grid item xs={6} md={4}>
          <InfoRow label="Utility Zone" value={deal.utility_zone} />
        </Grid>
      </Grid>
      {showEditButton && !deal.is_converted && onStartEdit && (
        <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
          <Button size="small" startIcon={<EditIcon />} onClick={onStartEdit}>
            Edit
          </Button>
        </Box>
      )}
    </Box>
  );
};

export const TimelineCard: React.FC<DealCardContentProps> = ({
  deal,
  isEditing,
  editForm,
  onFormChange,
  onStartEdit,
  showEditButton = true
}) => {
  if (isEditing) {
    return (
      <Grid container spacing={2}>
        <Grid item xs={6}>
          <TextField
            label="Next Action Date"
            type="date"
            value={editForm.next_action_date ?? deal.next_action_date ?? ''}
            onChange={e => onFormChange('next_action_date', e.target.value || undefined)}
            fullWidth
            size="small"
            InputLabelProps={{ shrink: true }}
          />
        </Grid>
        <Grid item xs={6}>
          <TextField
            label="Next Action Status"
            select
            value={editForm.next_action_status ?? deal.next_action_status ?? ''}
            onChange={e => onFormChange('next_action_status', e.target.value as NextActionStatus)}
            fullWidth
            size="small"
          >
            {Object.entries(NEXT_ACTION_STATUS_LABELS).map(([value, label]) => (
              <MenuItem key={value} value={value}>
                {label}
              </MenuItem>
            ))}
          </TextField>
        </Grid>
        <Grid item xs={6}>
          <TextField
            label="Target Close Date"
            type="date"
            value={editForm.target_close_date ?? deal.target_close_date ?? ''}
            onChange={e => onFormChange('target_close_date', e.target.value || undefined)}
            fullWidth
            size="small"
            InputLabelProps={{ shrink: true }}
          />
        </Grid>
        <Grid item xs={6}>
          <TextField
            label="Notice to Proceed"
            type="date"
            value={editForm.notice_to_proceed_date ?? deal.notice_to_proceed_date ?? ''}
            onChange={e => onFormChange('notice_to_proceed_date', e.target.value || undefined)}
            fullWidth
            size="small"
            InputLabelProps={{ shrink: true }}
          />
        </Grid>
        <Grid item xs={6}>
          <TextField
            label="Mechanical Completion"
            type="date"
            value={editForm.mechanical_completion_date ?? deal.mechanical_completion_date ?? ''}
            onChange={e => onFormChange('mechanical_completion_date', e.target.value || undefined)}
            fullWidth
            size="small"
            InputLabelProps={{ shrink: true }}
          />
        </Grid>
        <Grid item xs={6}>
          <TextField
            label="Permission to Operate"
            type="date"
            value={editForm.permission_to_operate_date ?? deal.permission_to_operate_date ?? ''}
            onChange={e => onFormChange('permission_to_operate_date', e.target.value || undefined)}
            fullWidth
            size="small"
            InputLabelProps={{ shrink: true }}
          />
        </Grid>
        <Grid item xs={6}>
          <TextField
            label="Substantial Completion"
            type="date"
            value={editForm.substantial_completion_date ?? deal.substantial_completion_date ?? ''}
            onChange={e => onFormChange('substantial_completion_date', e.target.value || undefined)}
            fullWidth
            size="small"
            InputLabelProps={{ shrink: true }}
          />
        </Grid>
      </Grid>
    );
  }

  return (
    <Box>
      <Grid container spacing={2}>
        <Grid item xs={6} md={3}>
          <InfoRow label="Next Action Date" value={formatDate(deal.next_action_date)} />
        </Grid>
        <Grid item xs={6} md={3}>
          <InfoRow
            label="Next Action Status"
            value={deal.next_action_status ? NEXT_ACTION_STATUS_LABELS[deal.next_action_status] : undefined}
          />
        </Grid>
        <Grid item xs={6} md={3}>
          <InfoRow label="Target Close" value={formatDate(deal.target_close_date)} />
        </Grid>
        <Grid item xs={6} md={3}>
          <InfoRow label="Notice to Proceed" value={formatDate(deal.notice_to_proceed_date)} />
        </Grid>
        <Grid item xs={6} md={3}>
          <InfoRow label="Mech Completion" value={formatDate(deal.mechanical_completion_date)} />
        </Grid>
        <Grid item xs={6} md={3}>
          <InfoRow label="PTO Date" value={formatDate(deal.permission_to_operate_date)} />
        </Grid>
        <Grid item xs={6} md={3}>
          <InfoRow label="Subst Completion" value={formatDate(deal.substantial_completion_date)} />
        </Grid>
        <Grid item xs={6} md={3}>
          <InfoRow label="Last Updated" value={formatDate(deal.updated_at)} />
        </Grid>
      </Grid>
      {showEditButton && !deal.is_converted && onStartEdit && (
        <Box sx={{ mt: 2, display: 'flex', justifyContent: 'flex-end' }}>
          <Button size="small" startIcon={<EditIcon />} onClick={onStartEdit}>
            Edit
          </Button>
        </Box>
      )}
    </Box>
  );
};
