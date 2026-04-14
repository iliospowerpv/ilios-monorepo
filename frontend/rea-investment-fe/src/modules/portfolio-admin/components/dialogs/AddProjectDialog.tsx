import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm, SubmitHandler, Controller } from 'react-hook-form';
import Dialog from '@mui/material/Dialog';
import DialogTitle from '@mui/material/DialogTitle';
import DialogContent from '@mui/material/DialogContent';
import DialogActions from '@mui/material/DialogActions';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import { SearchableSelect } from '../../../../components/common/SearchableSelect/SearchableSelect';
import Alert from '@mui/material/Alert';
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';

import { ApiClient, CreateSiteAttributes } from '../../../../api';
import { State } from '../../../../utils/asset-managment';
import { useNotify } from '../../../../contexts/notifications/notifications';

interface AddProjectDialogProps {
  open: boolean;
  onClose: () => void;
  companyId: number;
  companyName: string;
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

export const AddProjectDialog: React.FC<AddProjectDialogProps> = ({
  open,
  onClose,
  companyId,
  companyName,
  onSuccess
}) => {
  const queryClient = useQueryClient();
  const notify = useNotify();
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isValid },
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

  const createMutation = useMutation({
    mutationFn: (attributes: CreateSiteAttributes) => ApiClient.assetManagement.createSite(attributes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sites'] });
      queryClient.invalidateQueries({ queryKey: ['company'] });
      queryClient.invalidateQueries({ queryKey: ['workspace'] });
      notify('Project created successfully');
      reset();
      onSuccess?.();
      onClose();
    },
    onError: (err: any) => {
      setError(err.response?.data?.message || 'Failed to create project');
    }
  });

  const onSubmit: SubmitHandler<ProjectFormFields> = data => {
    setError(null);
    createMutation.mutate({
      company_id: companyId,
      name: data.name,
      address: data.address,
      city: data.city,
      state: data.state,
      zip_code: data.zip_code,
      system_size_ac: data.system_size_ac ? parseFloat(data.system_size_ac) : 0,
      system_size_dc: data.system_size_dc ? parseFloat(data.system_size_dc) : 0,
      lon_lat_url: ''
    });
  };

  const handleClose = () => {
    reset();
    setError(null);
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Add Project</DialogTitle>
      <form onSubmit={handleSubmit(onSubmit)}>
        <DialogContent>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
            Adding a project to <strong>{companyName}</strong>
          </Typography>

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
                  <SearchableSelect
                    options={Object.entries(State).map(([code, name]) => ({
                      label: name,
                      value: code
                    }))}
                    value={field.value || null}
                    onChange={val => field.onChange(val)}
                    onBlur={field.onBlur}
                    inputRef={field.ref}
                    label="State"
                    error={!!errors.state}
                    helperText={errors.state?.message}
                    required
                  />
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
                label="System Size AC (kW)"
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
                label="System Size DC (kW)"
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
          <Button onClick={handleClose} disabled={createMutation.isPending}>
            Cancel
          </Button>
          <Button
            type="submit"
            variant="contained"
            disabled={!isValid || createMutation.isPending}
            startIcon={createMutation.isPending ? <CircularProgress size={16} /> : null}
          >
            {createMutation.isPending ? 'Creating...' : 'Add Project'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

export default AddProjectDialog;
