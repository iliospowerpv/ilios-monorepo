import React, { useState } from 'react';
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

import { ApiClient, CompanyAttributes } from '../../../../api';
import { COMPANY_TYPES } from '../../../../constants';
import { useNotify } from '../../../../contexts/notifications/notifications';
import { US_STATES } from '../../../../constants/usStates';

interface AddCompanyDialogProps {
  open: boolean;
  onClose: () => void;
  onSuccess?: () => void;
}

interface CompanyFormFields {
  company_type: string;
  name: string;
  address: string;
  city: string;
  state: string;
  county?: string;
  zip_code: string;
  email?: string;
  phone?: string;
}

export const AddCompanyDialog: React.FC<AddCompanyDialogProps> = ({ open, onClose, onSuccess }) => {
  const queryClient = useQueryClient();
  const notify = useNotify();
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isValid },
    control,
    reset
  } = useForm<CompanyFormFields>({
    mode: 'onBlur',
    defaultValues: {
      company_type: '',
      name: '',
      address: '',
      city: '',
      state: '',
      county: '',
      zip_code: '',
      email: '',
      phone: ''
    }
  });

  const createMutation = useMutation({
    mutationFn: (attributes: CompanyAttributes) => ApiClient.companies.create(attributes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['companies'] });
      queryClient.invalidateQueries({ queryKey: ['workspace'] });
      notify('Company created successfully');
      reset();
      onSuccess?.();
      onClose();
    },
    onError: (err: any) => {
      setError(err.response?.data?.message || 'Failed to create company');
    }
  });

  const onSubmit: SubmitHandler<CompanyFormFields> = data => {
    setError(null);
    createMutation.mutate({
      company_type: data.company_type,
      name: data.name,
      address: data.address,
      city: data.city,
      state: data.state,
      county: data.county || null,
      zip_code: data.zip_code,
      email: data.email || null,
      phone: data.phone ? data.phone.replace(/\D/g, '').replace(/^1(\d{10})$/, '$1') : null
    });
  };

  const handleClose = () => {
    reset();
    setError(null);
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Add Company</DialogTitle>
      <form onSubmit={handleSubmit(onSubmit)}>
        <DialogContent>
          {error && (
            <Alert severity="error" sx={{ mb: 2 }} onClose={() => setError(null)}>
              {error}
            </Alert>
          )}

          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Controller
              name="company_type"
              control={control}
              rules={{ required: 'Company type is required' }}
              render={({ field }) => (
                <FormControl error={!!errors.company_type} fullWidth required>
                  <InputLabel>Type</InputLabel>
                  <Select {...field} label="Type">
                    {COMPANY_TYPES?.map(type => (
                      <MenuItem key={type} value={type}>
                        {type}
                      </MenuItem>
                    ))}
                  </Select>
                  {errors.company_type && <FormHelperText>{errors.company_type.message}</FormHelperText>}
                </FormControl>
              )}
            />

            <TextField
              label="Company Name"
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
                  <FormControl error={!!errors.state} required sx={{ minWidth: 120 }}>
                    <InputLabel>State</InputLabel>
                    <Select {...field} label="State">
                      {US_STATES.map(st => (
                        <MenuItem key={st} value={st}>
                          {st}
                        </MenuItem>
                      ))}
                    </Select>
                    {errors.state && <FormHelperText>{errors.state.message}</FormHelperText>}
                  </FormControl>
                )}
              />

              <TextField
                label="Zip Code"
                required
                sx={{ width: 120 }}
                error={!!errors.zip_code}
                helperText={errors.zip_code?.message}
                inputProps={{ maxLength: 5 }}
                {...register('zip_code', {
                  required: 'Zip code is required',
                  pattern: {
                    value: /^\d{5}$/,
                    message: 'Must be 5 digits'
                  }
                })}
              />
            </Box>

            <TextField
              label="County (optional)"
              fullWidth
              error={!!errors.county}
              helperText={errors.county?.message}
              {...register('county', {
                maxLength: { value: 100, message: 'County must be less than 100 characters' }
              })}
            />

            <TextField
              label="Email"
              fullWidth
              error={!!errors.email}
              helperText={errors.email?.message}
              {...register('email', {
                pattern: {
                  value: /^[^\s@]+@[^\s@]+\.[^\s@]+$/,
                  message: 'Invalid email format'
                }
              })}
            />

            <TextField
              label="Phone"
              fullWidth
              error={!!errors.phone}
              helperText={errors.phone?.message}
              {...register('phone', {
                validate: value => {
                  if (!value) return true;
                  const digits = value.replace(/\D/g, '').replace(/^1(\d{10})$/, '$1');
                  return digits.length === 10 || 'Phone number must contain exactly 10 digits';
                }
              })}
            />
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
            {createMutation.isPending ? 'Creating...' : 'Add Company'}
          </Button>
        </DialogActions>
      </form>
    </Dialog>
  );
};

export default AddCompanyDialog;
