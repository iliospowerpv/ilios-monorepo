import React, { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import MenuItem from '@mui/material/MenuItem';
import Grid from '@mui/material/Grid';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import Divider from '@mui/material/Divider';
import CircularProgress from '@mui/material/CircularProgress';
import Table from '@mui/material/Table';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableHead from '@mui/material/TableHead';
import TableRow from '@mui/material/TableRow';
import { ApiClient } from '../../../../api';
import { US_STATES } from '../../../../constants/usStates';
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

const ROLE_LABELS: Record<string, string> = {
  epc_contractor: 'EPC Contractor',
  om_provider: 'O&M Provider',
  interconnection_utility: 'Interconnection Utility',
  insurance_provider: 'Insurance Provider',
  community_solar_manager: 'Community Solar Manager',
  vegetation_vendor: 'Vegetation Vendor',
  offtaker: 'Offtaker',
  tax_equity_provider: 'Tax Equity Provider',
  developer: 'Developer',
  compliance_entity: 'Compliance Entity',
  compliance_bank: 'Compliance Bank',
  hold_co: 'Hold Co',
  project_co: 'Project Co',
  landlord: 'Landlord',
  tenant: 'Tenant'
};

interface EntityFormDialogProps {
  open: boolean;
  onClose: () => void;
  onSaved: () => void;
  entity?: ProjectEntity | null;
  portfolioId: number;
}

interface FormState {
  name: string;
  entity_type: EntityType | '';
  address: string;
  city: string;
  state: string;
  zip_code: string;
  phone: string;
  email: string;
  website: string;
  notes: string;
}

const initialForm: FormState = {
  name: '',
  entity_type: '',
  address: '',
  city: '',
  state: '',
  zip_code: '',
  phone: '',
  email: '',
  website: '',
  notes: ''
};

export const EntityFormDialog: React.FC<EntityFormDialogProps> = ({ open, onClose, onSaved, entity, portfolioId }) => {
  const isEdit = !!entity;
  const [form, setForm] = useState<FormState>(initialForm);
  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<Partial<Record<keyof FormState, string>>>({});

  const { data: assignmentsData, isLoading: isLoadingAssignments } = useQuery({
    queryKey: ['entity-assignments', entity?.id],
    queryFn: () => ApiClient.entities.getAssignments(entity!.id),
    enabled: isEdit && !!entity?.id
  });

  useEffect(() => {
    if (open && entity) {
      setForm({
        name: entity.name || '',
        entity_type: entity.entity_type || '',
        address: entity.address || '',
        city: entity.city || '',
        state: entity.state || '',
        zip_code: entity.zip_code || '',
        phone: entity.phone || '',
        email: entity.email || '',
        website: entity.website || '',
        notes: entity.notes || ''
      });
    } else if (open) {
      setForm(initialForm);
    }
    setErrors({});
  }, [open, entity]);

  const validate = (): boolean => {
    const newErrors: Partial<Record<keyof FormState, string>> = {};
    if (!form.name.trim()) {
      newErrors.name = 'Name is required';
    }
    if (!form.entity_type) {
      newErrors.entity_type = 'Entity type is required';
    }
    if (form.email && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
      newErrors.email = 'Invalid email format';
    }
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleChange = (field: keyof FormState) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm(prev => ({ ...prev, [field]: e.target.value }));
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: undefined }));
    }
  };

  const handleSave = async () => {
    if (!validate()) return;
    setSaving(true);
    try {
      if (isEdit && entity) {
        await ApiClient.entities.update(entity.id, {
          name: form.name.trim(),
          entity_type: form.entity_type as EntityType,
          address: form.address || null,
          city: form.city || null,
          state: form.state || null,
          zip_code: form.zip_code || null,
          phone: form.phone || null,
          email: form.email || null,
          website: form.website || null,
          notes: form.notes || null
        });
      } else {
        await ApiClient.entities.create({
          name: form.name.trim(),
          entity_type: form.entity_type as EntityType,
          portfolio_id: portfolioId,
          address: form.address || null,
          city: form.city || null,
          state: form.state || null,
          zip_code: form.zip_code || null,
          phone: form.phone || null,
          email: form.email || null,
          website: form.website || null,
          notes: form.notes || null
        });
      }
      onSaved();
      onClose();
    } catch (err: any) {
      const detail = err?.response?.data?.detail || err?.response?.data?.message || err?.message || '';
      console.error('Entity save error:', err?.response?.status, detail);
      if (err?.response?.status === 409 || detail.toLowerCase().includes('already exists')) {
        setErrors({ name: 'An entity with this name already exists in this portfolio.' });
      } else {
        setErrors({ name: `Failed to save: ${detail || 'Unknown error'}` });
      }
    } finally {
      setSaving(false);
    }
  };

  const assignments = assignmentsData?.items || [];

  return (
    <Dialog open={open} onClose={onClose} maxWidth="md" fullWidth>
      <DialogTitle>{isEdit ? 'Edit Entity' : 'Add Entity'}</DialogTitle>
      <DialogContent>
        <Grid container spacing={2} sx={{ mt: 0.5 }}>
          <Grid item xs={12} sm={8}>
            <TextField
              label="Name"
              value={form.name}
              onChange={handleChange('name')}
              fullWidth
              required
              error={!!errors.name}
              helperText={errors.name}
              size="small"
            />
          </Grid>
          <Grid item xs={12} sm={4}>
            <TextField
              label="Entity Type"
              value={form.entity_type}
              onChange={handleChange('entity_type')}
              fullWidth
              required
              select
              error={!!errors.entity_type}
              helperText={errors.entity_type}
              size="small"
            >
              {ENTITY_TYPE_OPTIONS.map(opt => (
                <MenuItem key={opt.value} value={opt.value}>
                  {opt.label}
                </MenuItem>
              ))}
            </TextField>
          </Grid>
          <Grid item xs={12}>
            <TextField label="Address" value={form.address} onChange={handleChange('address')} fullWidth size="small" />
          </Grid>
          <Grid item xs={12} sm={4}>
            <TextField label="City" value={form.city} onChange={handleChange('city')} fullWidth size="small" />
          </Grid>
          <Grid item xs={12} sm={4}>
            <TextField label="State" value={form.state} onChange={handleChange('state')} fullWidth select size="small">
              <MenuItem value="">
                <em>None</em>
              </MenuItem>
              {US_STATES.map(st => (
                <MenuItem key={st} value={st}>
                  {st}
                </MenuItem>
              ))}
            </TextField>
          </Grid>
          <Grid item xs={12} sm={4}>
            <TextField
              label="Zip Code"
              value={form.zip_code}
              onChange={handleChange('zip_code')}
              fullWidth
              size="small"
            />
          </Grid>
          <Grid item xs={12} sm={4}>
            <TextField label="Phone" value={form.phone} onChange={handleChange('phone')} fullWidth size="small" />
          </Grid>
          <Grid item xs={12} sm={4}>
            <TextField
              label="Email"
              value={form.email}
              onChange={handleChange('email')}
              fullWidth
              size="small"
              error={!!errors.email}
              helperText={errors.email}
            />
          </Grid>
          <Grid item xs={12} sm={4}>
            <TextField label="Website" value={form.website} onChange={handleChange('website')} fullWidth size="small" />
          </Grid>
          <Grid item xs={12}>
            <TextField
              label="Notes"
              value={form.notes}
              onChange={handleChange('notes')}
              fullWidth
              multiline
              rows={3}
              size="small"
            />
          </Grid>
        </Grid>

        {isEdit && (
          <>
            <Divider sx={{ my: 3 }} />
            <Typography variant="subtitle2" sx={{ mb: 1 }}>
              Project Assignments
            </Typography>
            {isLoadingAssignments ? (
              <Box sx={{ display: 'flex', justifyContent: 'center', py: 2 }}>
                <CircularProgress size={24} />
              </Box>
            ) : assignments.length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                Not assigned to any projects
              </Typography>
            ) : (
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Project</TableCell>
                    <TableCell>Role</TableCell>
                    <TableCell>Effective Date</TableCell>
                    <TableCell>Termination Date</TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {assignments.map(a => (
                    <TableRow key={a.relationship_id}>
                      <TableCell>{a.site_name}</TableCell>
                      <TableCell>
                        <Chip label={ROLE_LABELS[a.role] || a.role} size="small" variant="outlined" />
                      </TableCell>
                      <TableCell>{a.effective_date || '—'}</TableCell>
                      <TableCell>{a.termination_date || '—'}</TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </>
        )}
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose} disabled={saving}>
          Cancel
        </Button>
        <Button onClick={handleSave} variant="contained" disabled={saving}>
          {saving ? <CircularProgress size={20} /> : isEdit ? 'Save Changes' : 'Create Entity'}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
