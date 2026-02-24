import React, { useState, useCallback, useEffect } from 'react';
import Autocomplete from '@mui/material/Autocomplete';
import TextField from '@mui/material/TextField';
import Chip from '@mui/material/Chip';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import MenuItem from '@mui/material/MenuItem';
import AddIcon from '@mui/icons-material/Add';
import { ApiClient } from '../../../api';
import type { ProjectEntity, EntityType, EntityRelationshipRole } from '../../../api/entities';

const ENTITY_TYPE_LABELS: Record<EntityType, string> = {
  epc_contractor: 'EPC Contractor',
  om_provider: 'O&M Provider',
  utility: 'Utility',
  insurance: 'Insurance',
  engineering: 'Engineering',
  legal: 'Legal',
  accounting: 'Accounting',
  bank: 'Bank',
  investor: 'Investor',
  developer: 'Developer',
  offtaker: 'Offtaker',
  subscriber_manager: 'Subscriber Manager',
  vegetation: 'Vegetation',
  community_solar: 'Community Solar',
  tax_equity: 'Tax Equity',
  other: 'Other'
};

const ALL_ENTITY_TYPES: EntityType[] = Object.keys(ENTITY_TYPE_LABELS) as EntityType[];

interface AddNewOption {
  id: -1;
  name: string;
  entity_type: EntityType | '';
  isAddNew: true;
}

type OptionType = ProjectEntity | AddNewOption;

function isAddNewOption(option: OptionType): option is AddNewOption {
  return 'isAddNew' in option && option.isAddNew === true;
}

interface EntityPickerProps {
  portfolioId: number;
  entityType?: EntityType;
  value: number | null;
  onChange: (entityId: number | null, entity: ProjectEntity | null) => void;
  label?: string;
  role?: EntityRelationshipRole;
  disabled?: boolean;
  size?: 'small' | 'medium';
}

export const EntityPicker: React.FC<EntityPickerProps> = ({
  portfolioId,
  entityType,
  value,
  onChange,
  label = 'Entity',
  disabled = false,
  size = 'small'
}) => {
  const [open, setOpen] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const [options, setOptions] = useState<ProjectEntity[]>([]);
  const [loading, setLoading] = useState(false);
  const [selectedEntity, setSelectedEntity] = useState<ProjectEntity | null>(null);
  const [createDialogOpen, setCreateDialogOpen] = useState(false);
  const [createForm, setCreateForm] = useState({
    name: '',
    entity_type: (entityType || '') as EntityType | '',
    address: '',
    phone: '',
    email: ''
  });
  const [creating, setCreating] = useState(false);

  const fetchOptions = useCallback(
    async (search: string) => {
      if (!portfolioId) return;
      setLoading(true);
      try {
        const result = await ApiClient.entities.list({
          portfolio_id: portfolioId,
          search: search || undefined,
          entity_type: entityType || undefined,
          page_size: 50
        });
        setOptions(result.items);
      } catch {
        setOptions([]);
      } finally {
        setLoading(false);
      }
    },
    [portfolioId, entityType]
  );

  useEffect(() => {
    if (open) {
      fetchOptions(inputValue);
    }
  }, [open, inputValue, fetchOptions]);

  useEffect(() => {
    if (value && !selectedEntity) {
      ApiClient.entities
        .get(value)
        .then(entity => {
          setSelectedEntity(entity);
        })
        .catch(() => {});
    } else if (!value) {
      setSelectedEntity(null);
    }
  }, [value, selectedEntity]);

  const handleChange = (_event: React.SyntheticEvent, newValue: OptionType | null) => {
    if (newValue && isAddNewOption(newValue)) {
      setCreateForm({
        name: '',
        entity_type: entityType || '',
        address: '',
        phone: '',
        email: ''
      });
      setCreateDialogOpen(true);
      return;
    }
    const entity = newValue as ProjectEntity | null;
    setSelectedEntity(entity);
    onChange(entity?.id ?? null, entity);
  };

  const handleCreate = async () => {
    if (!createForm.name || !createForm.entity_type) return;
    setCreating(true);
    try {
      const newEntity = await ApiClient.entities.create({
        name: createForm.name,
        entity_type: createForm.entity_type as EntityType,
        portfolio_id: portfolioId,
        address: createForm.address || undefined,
        phone: createForm.phone || undefined,
        email: createForm.email || undefined
      });
      setSelectedEntity(newEntity);
      onChange(newEntity.id, newEntity);
      setCreateDialogOpen(false);
      setOptions(prev => [newEntity, ...prev]);
    } catch {
      /* entity create non-blocking */
    } finally {
      setCreating(false);
    }
  };

  const addNewOption: AddNewOption = {
    id: -1,
    name: '+ Add New Entity',
    entity_type: '',
    isAddNew: true
  };

  const allOptions: OptionType[] = [...options, addNewOption];

  return (
    <>
      <Autocomplete<OptionType, false, false, false>
        open={open}
        onOpen={() => setOpen(true)}
        onClose={() => setOpen(false)}
        value={selectedEntity as OptionType | null}
        onChange={handleChange}
        inputValue={inputValue}
        onInputChange={(_event, newInputValue) => setInputValue(newInputValue)}
        options={allOptions}
        loading={loading}
        disabled={disabled}
        size={size}
        getOptionLabel={option => {
          if (isAddNewOption(option)) return option.name;
          return (option as ProjectEntity).name || '';
        }}
        isOptionEqualToValue={(option, val) => {
          if (isAddNewOption(option) || isAddNewOption(val)) return false;
          return (option as ProjectEntity).id === (val as ProjectEntity).id;
        }}
        filterOptions={x => x}
        renderOption={(props, option) => {
          if (isAddNewOption(option)) {
            return (
              <Box component="li" {...props} key="add-new" sx={{ color: 'primary.main', fontWeight: 600 }}>
                <AddIcon sx={{ mr: 1, fontSize: 20 }} />
                Add New Entity
              </Box>
            );
          }
          const entity = option as ProjectEntity;
          return (
            <Box component="li" {...props} key={entity.id}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, width: '100%' }}>
                <Typography variant="body2">{entity.name}</Typography>
                <Chip
                  label={ENTITY_TYPE_LABELS[entity.entity_type] || entity.entity_type}
                  size="small"
                  variant="outlined"
                  sx={{ ml: 'auto', fontSize: '0.7rem', height: 20 }}
                />
              </Box>
            </Box>
          );
        }}
        renderInput={params => (
          <TextField
            {...params}
            label={label}
            placeholder="Search entities..."
            InputProps={{
              ...params.InputProps,
              endAdornment: (
                <>
                  {loading ? <CircularProgress color="inherit" size={18} /> : null}
                  {params.InputProps.endAdornment}
                </>
              )
            }}
          />
        )}
      />

      <Dialog open={createDialogOpen} onClose={() => setCreateDialogOpen(false)} maxWidth="xs" fullWidth>
        <DialogTitle>Add New Entity</DialogTitle>
        <DialogContent>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2, mt: 1 }}>
            <TextField
              label="Name"
              required
              value={createForm.name}
              onChange={e => setCreateForm(prev => ({ ...prev, name: e.target.value }))}
              size="small"
              fullWidth
            />
            <TextField
              label="Entity Type"
              required
              select
              value={createForm.entity_type}
              onChange={e => setCreateForm(prev => ({ ...prev, entity_type: e.target.value as EntityType }))}
              size="small"
              fullWidth
            >
              {ALL_ENTITY_TYPES.map(type => (
                <MenuItem key={type} value={type}>
                  {ENTITY_TYPE_LABELS[type]}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label="Address"
              value={createForm.address}
              onChange={e => setCreateForm(prev => ({ ...prev, address: e.target.value }))}
              size="small"
              fullWidth
            />
            <TextField
              label="Phone"
              value={createForm.phone}
              onChange={e => setCreateForm(prev => ({ ...prev, phone: e.target.value }))}
              size="small"
              fullWidth
            />
            <TextField
              label="Email"
              value={createForm.email}
              onChange={e => setCreateForm(prev => ({ ...prev, email: e.target.value }))}
              size="small"
              fullWidth
            />
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setCreateDialogOpen(false)} disabled={creating}>
            Cancel
          </Button>
          <Button
            onClick={handleCreate}
            variant="contained"
            disabled={creating || !createForm.name || !createForm.entity_type}
          >
            {creating ? 'Creating...' : 'Create'}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default EntityPicker;
