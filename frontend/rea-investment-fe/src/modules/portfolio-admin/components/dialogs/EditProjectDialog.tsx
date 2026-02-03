import React, { useState, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm, SubmitHandler, Controller } from 'react-hook-form';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Select from '@mui/material/Select';
import MenuItem from '@mui/material/MenuItem';
import FormControl from '@mui/material/FormControl';
import FormHelperText from '@mui/material/FormHelperText';
import InputLabel from '@mui/material/InputLabel';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';

import { ApiClient, CreateSiteAttributes } from '../../../../api';
import { State } from '../../../../utils/asset-managment';
import { useNotify } from '../../../../contexts/notifications/notifications';

interface ProjectData {
  id: number;
  name: string;
  address: string;
  city: string;
  state: string;
  zip_code: string;
  system_size_ac?: number | null;
  system_size_dc?: number | null;
  company_id: number;
  lon_lat_url?: string;
}

interface EditProjectDialogProps {
  open: boolean;
  onClose: () => void;
  project: ProjectData | null;
  onSuccess?: () => void;
}

interface ProjectFormFields {
  name: string;
  address: string;
  city: string;
  state: string;
  zip_code: string;
  system_size_ac?: string;
  system_size_dc?: string;
}

export const EditProjectDialog: React.FC<EditProjectDialogProps> = ({ open, onClose, project, onSuccess }) => {
  const queryClient = useQueryClient();
  const notify = useNotify();
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isValid, isDirty },
    control,
    reset
  } = useForm<ProjectFormFields>({
    mode: 'onBlur',
    defaultValues: {
      name: '',
      address: '',
      city: '',
      state: '',
      zip_code: '',
      system_size_ac: '',
      system_size_dc: ''
    }
  });

  useEffect(() => {
    if (project && open) {
      reset({
        name: project.name || '',
        address: project.address || '',
        city: project.city || '',
        state: project.state || '',
        zip_code: project.zip_code || '',
        system_size_ac: project.system_size_ac?.toString() || '',
        system_size_dc: project.system_size_dc?.toString() || ''
      });
    }
  }, [project, open, reset]);

  const updateMutation = useMutation({
    mutationFn: (attributes: CreateSiteAttributes) => ApiClient.assetManagement.updateSite(project?.id, attributes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sites'] });
      queryClient.invalidateQueries({ queryKey: ['site', project?.id] });
      queryClient.invalidateQueries({ queryKey: ['company'] });
      queryClient.invalidateQueries({ queryKey: ['workspace'] });
      notify('Project updated successfully');
      onSuccess?.();
      onClose();
    },
    onError: (err: any) => {
      setError(err.response?.data?.message || 'Failed to update project');
    }
  });

  const onSubmit: SubmitHandler<ProjectFormFields> = data => {
    if (!project) return;
    setError(null);
    updateMutation.mutate({
      company_id: project.company_id,
      name: data.name,
      address: data.address,
      city: data.city,
      state: data.state,
      zip_code: data.zip_code,
      system_size_ac: data.system_size_ac ? parseFloat(data.system_size_ac) : 0,
      system_size_dc: data.system_size_dc ? parseFloat(data.system_size_dc) : 0,
      lon_lat_url: project.lon_lat_url || ''
    });
  };

  const handleClose = () => {
    setError(null);
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Edit Project</DialogTitle>
      <form onSubmit={handleSubmit(onSubmit)}>
        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Project Name"
              required
              fullWidth
              error={!!errors.name}
              helperText={errors.name?.message}
              {...register('name', {
                required: 'Name is required',
                minLength: { value: 2, message: 'Name must be at least 2 characters' },
                maxLength: { value: 100, message: 'Name must be less than 100 characters' }
              })}
            />

            <TextField
              label="Address"
              required
              fullWidth
              error={!!errors.address}
              helperText={errors.address?.message}
              {...register('address', {
                required: 'Address is required',
                maxLength: { value: 255, message: 'Address must be less than 255 characters' }
              })}
            />

            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                label="City"
                required
                fullWidth
                error={!!errors.city}
                helperText={errors.city?.message}
                {...register('city', {
                  required: 'City is required',
                  maxLength: { value: 100, message: 'City must be less than 100 characters' }
                })}
              />

              <Controller
                name="state"
                control={control}
                rules={{ required: 'State is required' }}
                render={({ field }) => (
                  <FormControl error={!!errors.state} fullWidth required>
                    <InputLabel>State</InputLabel>
                    <Select {...field} label="State">
                      {Object.entries(State).map(([code, name]) => (
                        <MenuItem key={code} value={code}>
                          {name}
                        </MenuItem>
                      ))}
                    </Select>
                    {errors.state && <FormHelperText>{errors.state.message}</FormHelperText>}
                  </FormControl>
                )}
              />
            </Box>

            <TextField
              label="ZIP Code"
              required
              fullWidth
              error={!!errors.zip_code}
              helperText={errors.zip_code?.message}
              {...register('zip_code', {
                required: 'ZIP code is required',
                pattern: {
                  value: /^\d{5}(-\d{4})?$/,
                  message: 'Invalid ZIP code format'
                }
              })}
            />

            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                label="System Size AC (MW)"
                fullWidth
                error={!!errors.system_size_ac}
                helperText={errors.system_size_ac?.message}
                {...register('system_size_ac', {
                  pattern: {
                    value: /^\d*\.?\d*$/,
                    message: 'Must be a valid number'
                  }
                })}
              />

              <TextField
                label="System Size DC (MW)"
                fullWidth
                error={!!errors.system_size_dc}
                helperText={errors.system_size_dc?.message}
                {...register('system_size_dc', {
                  pattern: {
                    value: /^\d*\.?\d*$/,
                    message: 'Must be a valid number'
                  }
                })}
              />
            </Box>
          </Box>
        </DialogContent>
        <DialogActions>
          <Button onClick={handleClose} disabled={updateMutation.isPending}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="contained"
            disabled={!isValid || !isDirty || updateMutation.isPending}
            startIcon={updateMutation.isPending ? <CircularProgress size={16} /> : null}
          >
            {updateMutation.isPending ? 'Saving...' : 'Save Changes'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

export default EditProjectDialog;
