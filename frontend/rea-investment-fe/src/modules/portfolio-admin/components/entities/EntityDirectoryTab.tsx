import React, { useState, useMemo, useCallback } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';
import MenuItem from '@mui/material/MenuItem';
import Button from '@mui/material/Button';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import Chip from '@mui/material/Chip';
import IconButton from '@mui/material/IconButton';
import Skeleton from '@mui/material/Skeleton';
import Tooltip from '@mui/material/Tooltip';
import Switch from '@mui/material/Switch';
import FormControlLabel from '@mui/material/FormControlLabel';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import InputAdornment from '@mui/material/InputAdornment';
import AddIcon from '@mui/icons-material/Add';
import EditIcon from '@mui/icons-material/Edit';
import ArchiveIcon from '@mui/icons-material/Archive';
import UnarchiveIcon from '@mui/icons-material/Unarchive';
import SearchIcon from '@mui/icons-material/Search';
import { ApiClient } from '../../../../api';
import { useNotify } from '../../../../contexts/notifications/notifications';
import { EntityFormDialog } from './EntityFormDialog';
import type { ProjectEntity, EntityType } from '../../../../api/entities';

const ENTITY_TYPE_OPTIONS: { value: EntityType; label: string }[] = [
  { value: 'epc_contractor', label: 'EPC Contractor' },
  { value: 'om_provider', label: 'O&M Provider' },
  { value: 'utility', label: 'Utility' },
  { value: 'insurance', label: 'Insurance' },
  { value: 'engineering', label: 'Engineering' },
  { value: 'legal', label: 'Legal' },
  { value: 'accounting', label: 'Accounting' },
  { value: 'bank', label: 'Bank' },
  { value: 'investor', label: 'Investor' },
  { value: 'developer', label: 'Developer' },
  { value: 'offtaker', label: 'Offtaker' },
  { value: 'subscriber_manager', label: 'Subscriber Manager' },
  { value: 'vegetation', label: 'Vegetation' },
  { value: 'community_solar', label: 'Community Solar' },
  { value: 'tax_equity', label: 'Tax Equity' },
  { value: 'other', label: 'Other' }
];

const TYPE_LABEL_MAP: Record<EntityType, string> = Object.fromEntries(
  ENTITY_TYPE_OPTIONS.map(o => [o.value, o.label])
) as Record<EntityType, string>;

const TYPE_COLOR_MAP: Record<
  EntityType,
  'primary' | 'secondary' | 'success' | 'warning' | 'info' | 'error' | 'default'
> = {
  epc_contractor: 'primary',
  om_provider: 'info',
  utility: 'warning',
  insurance: 'secondary',
  engineering: 'primary',
  legal: 'default',
  accounting: 'default',
  bank: 'success',
  investor: 'success',
  developer: 'primary',
  offtaker: 'warning',
  subscriber_manager: 'info',
  vegetation: 'success',
  community_solar: 'info',
  tax_equity: 'secondary',
  other: 'default'
};

interface EntityDirectoryTabProps {
  portfolioId: number;
}

export const EntityDirectoryTab: React.FC<EntityDirectoryTabProps> = ({ portfolioId }) => {
  const queryClient = useQueryClient();
  const notify = useNotify();
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState<EntityType | ''>('');
  const [showInactive, setShowInactive] = useState(false);
  const [formDialogOpen, setFormDialogOpen] = useState(false);
  const [editingEntity, setEditingEntity] = useState<ProjectEntity | null>(null);
  const [deactivateDialog, setDeactivateDialog] = useState<{ open: boolean; entity: ProjectEntity | null }>({
    open: false,
    entity: null
  });

  const searchTimerRef = React.useRef<ReturnType<typeof setTimeout> | null>(null);

  const handleSearchChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setSearch(value);
    if (searchTimerRef.current) {
      clearTimeout(searchTimerRef.current);
    }
    searchTimerRef.current = setTimeout(() => {
      setDebouncedSearch(value);
    }, 300);
  }, []);

  const { data, isLoading } = useQuery({
    queryKey: ['entity-directory', portfolioId, debouncedSearch, typeFilter, showInactive],
    queryFn: () =>
      ApiClient.entities.list({
        portfolio_id: portfolioId,
        search: debouncedSearch || undefined,
        entity_type: typeFilter || undefined,
        include_inactive: showInactive,
        page_size: 200
      }),
    staleTime: 30 * 1000
  });

  const deactivateMutation = useMutation({
    mutationFn: (entityId: number) => ApiClient.entities.update(entityId, { is_active: false }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['entity-directory'] });
      notify('Entity deactivated');
      setDeactivateDialog({ open: false, entity: null });
    },
    onError: () => {
      notify('Failed to deactivate entity');
    }
  });

  const reactivateMutation = useMutation({
    mutationFn: (entityId: number) => ApiClient.entities.update(entityId, { is_active: true }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['entity-directory'] });
      notify('Entity reactivated');
    },
    onError: () => {
      notify('Failed to reactivate entity');
    }
  });

  const entities = useMemo(() => data?.items || [], [data]);

  const handleAddEntity = () => {
    setEditingEntity(null);
    setFormDialogOpen(true);
  };

  const handleEditEntity = (entity: ProjectEntity) => {
    setEditingEntity(entity);
    setFormDialogOpen(true);
  };

  const handleFormSaved = () => {
    queryClient.invalidateQueries({ queryKey: ['entity-directory'] });
    notify(editingEntity ? 'Entity updated' : 'Entity created');
  };

  const formatLocation = (entity: ProjectEntity): string => {
    const parts = [entity.city, entity.state].filter(Boolean);
    return parts.join(', ') || '—';
  };

  return (
    <Box>
      <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mb: 2 }}>
        <Box sx={{ display: 'flex', gap: 2, alignItems: 'center', flexWrap: 'wrap' }}>
          <TextField
            placeholder="Search entities..."
            value={search}
            onChange={handleSearchChange}
            size="small"
            sx={{ minWidth: 240 }}
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              )
            }}
          />
          <TextField
            label="Type"
            value={typeFilter}
            onChange={e => setTypeFilter(e.target.value as EntityType | '')}
            select
            size="small"
            sx={{ minWidth: 160 }}
          >
            <MenuItem value="">All Types</MenuItem>
            {ENTITY_TYPE_OPTIONS.map(opt => (
              <MenuItem key={opt.value} value={opt.value}>
                {opt.label}
              </MenuItem>
            ))}
          </TextField>
          <FormControlLabel
            control={<Switch checked={showInactive} onChange={(_, checked) => setShowInactive(checked)} size="small" />}
            label="Show Inactive"
          />
        </Box>
        <Button variant="contained" startIcon={<AddIcon />} onClick={handleAddEntity}>
          Add Entity
        </Button>
      </Box>

      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Name</TableCell>
              <TableCell>Type</TableCell>
              <TableCell>Location</TableCell>
              <TableCell>Phone</TableCell>
              <TableCell>Email</TableCell>
              <TableCell align="center">Status</TableCell>
              <TableCell align="right">Actions</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {isLoading ? (
              [1, 2, 3, 4, 5].map(i => (
                <TableRow key={i}>
                  <TableCell>
                    <Skeleton width={120} />
                  </TableCell>
                  <TableCell>
                    <Skeleton width={80} />
                  </TableCell>
                  <TableCell>
                    <Skeleton width={100} />
                  </TableCell>
                  <TableCell>
                    <Skeleton width={90} />
                  </TableCell>
                  <TableCell>
                    <Skeleton width={120} />
                  </TableCell>
                  <TableCell align="center">
                    <Skeleton width={60} />
                  </TableCell>
                  <TableCell align="right">
                    <Skeleton width={60} />
                  </TableCell>
                </TableRow>
              ))
            ) : entities.length === 0 ? (
              <TableRow>
                <TableCell colSpan={7} align="center" sx={{ py: 4 }}>
                  <Typography color="text.secondary">
                    {debouncedSearch || typeFilter
                      ? 'No entities match your filters'
                      : 'No entities yet. Add one to get started.'}
                  </Typography>
                </TableCell>
              </TableRow>
            ) : (
              entities.map(entity => (
                <TableRow
                  key={entity.id}
                  hover
                  sx={{ cursor: 'pointer', opacity: entity.is_active ? 1 : 0.6 }}
                  onClick={() => handleEditEntity(entity)}
                >
                  <TableCell>
                    <Typography variant="body2" fontWeight={500}>
                      {entity.name}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Chip
                      label={TYPE_LABEL_MAP[entity.entity_type] || entity.entity_type}
                      size="small"
                      color={TYPE_COLOR_MAP[entity.entity_type] || 'default'}
                      variant="outlined"
                    />
                  </TableCell>
                  <TableCell>{formatLocation(entity)}</TableCell>
                  <TableCell>{entity.phone || '—'}</TableCell>
                  <TableCell>{entity.email || '—'}</TableCell>
                  <TableCell align="center">
                    <Chip
                      label={entity.is_active ? 'Active' : 'Inactive'}
                      size="small"
                      color={entity.is_active ? 'success' : 'default'}
                    />
                  </TableCell>
                  <TableCell align="right" onClick={e => e.stopPropagation()}>
                    <Tooltip title="Edit">
                      <IconButton size="small" onClick={() => handleEditEntity(entity)}>
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </Tooltip>
                    {entity.is_active ? (
                      <Tooltip title="Deactivate">
                        <IconButton size="small" onClick={() => setDeactivateDialog({ open: true, entity })}>
                          <ArchiveIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    ) : (
                      <Tooltip title="Reactivate">
                        <IconButton size="small" onClick={() => reactivateMutation.mutate(entity.id)}>
                          <UnarchiveIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    )}
                  </TableCell>
                </TableRow>
              ))
            )}
          </TableBody>
        </Table>
      </TableContainer>

      {data && data.total > 0 && (
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', mt: 1, px: 1 }}>
          <Typography variant="caption" color="text.secondary">
            Showing {entities.length} of {data.total} entities
          </Typography>
        </Box>
      )}

      <EntityFormDialog
        open={formDialogOpen}
        onClose={() => setFormDialogOpen(false)}
        onSaved={handleFormSaved}
        entity={editingEntity}
        portfolioId={portfolioId}
      />

      <Dialog
        open={deactivateDialog.open}
        onClose={() => setDeactivateDialog({ open: false, entity: null })}
        maxWidth="xs"
      >
        <DialogTitle>Deactivate Entity</DialogTitle>
        <DialogContent>
          <Typography>
            Are you sure you want to deactivate <strong>{deactivateDialog.entity?.name}</strong>? It will no longer
            appear in entity pickers, but existing project assignments will remain.
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeactivateDialog({ open: false, entity: null })}>Cancel</Button>
          <Button
            variant="contained"
            color="warning"
            onClick={() => deactivateDialog.entity && deactivateMutation.mutate(deactivateDialog.entity.id)}
            disabled={deactivateMutation.isPending}
          >
            Deactivate
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};
