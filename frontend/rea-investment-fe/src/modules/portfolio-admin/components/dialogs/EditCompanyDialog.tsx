import React, { useState, useEffect } from 'react';
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

import { ApiClient, CompanyAttributes } from '../../../../api';
import { COMPANY_TYPES } from '../../../../constants';
import { useNotify } from '../../../../contexts/notifications/notifications';

interface CompanyData {
  id: number;
  name: string;
  company_type: string;
  email?: string | null;
  phone?: string | null;
  address?: string | null;
}

interface EditCompanyDialogProps {
  open: boolean;
  onClose: () => void;
  company: CompanyData | null;
  onSuccess?: () => void;
}

interface CompanyFormFields {
  company_type: string;
  name: string;
  email?: string;
  phone?: string;
  address?: string;
}

export const EditCompanyDialog: React.FC<EditCompanyDialogProps> = ({ open, onClose, company, onSuccess }) => {
  const queryClient = useQueryClient();
  const notify = useNotify();
  const [error, setError] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors, isValid, isDirty },
    control,
    reset
  } = useForm<CompanyFormFields>({
    mode: 'onBlur',
    defaultValues: {
      company_type: '',
      name: '',
      email: '',
      phone: '',
      address: ''
    }
  });

  useEffect(() => {
    if (company && open) {
      reset({
        company_type: company.company_type || '',
        name: company.name || '',
        email: company.email || '',
        phone: company.phone || '',
        address: company.address || ''
      });
    }
  }, [company, open, reset]);

  const updateMutation = useMutation({
    mutationFn: (attributes: CompanyAttributes) => ApiClient.companies.update(company?.id, attributes),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['companies'] });
      queryClient.invalidateQueries({ queryKey: ['company', company?.id] });
      queryClient.invalidateQueries({ queryKey: ['workspace'] });
      notify('Company updated successfully');
      onSuccess?.();
      onClose();
    },
    onError: (err: any) => {
      setError(err.response?.data?.message || 'Failed to update company');
    }
  });

  const onSubmit: SubmitHandler<CompanyFormFields> = data => {
    setError(null);
    updateMutation.mutate({
      company_type: data.company_type,
      name: data.name,
      email: data.email || null,
      phone: data.phone || null,
      address: data.address || null
    });
  };

  const handleClose = () => {
    setError(null);
    onClose();
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth>
      <DialogTitle>Edit Company</DialogTitle>
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
                <SearchableSelect
                  options={(COMPANY_TYPES || []).map(type => ({
                    label: type,
                    value: type
                  }))}
                  value={field.value || null}
                  onChange={val => field.onChange(val)}
                  onBlur={field.onBlur}
                  inputRef={field.ref}
                  label="Type"
                  error={!!errors.company_type}
                  helperText={errors.company_type?.message}
                  required
                  fullWidth
                />
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
                pattern: {
                  value: /^\d{10}$/,
                  message: 'Phone must be 10 digits'
                }
              })}
            />

            <TextField
              label="Address"
              fullWidth
              multiline
              rows={2}
              error={!!errors.address}
              helperText={errors.address?.message}
              {...register('address', {
                maxLength: { value: 255, message: 'Address must be less than 255 characters' }
              })}
            />
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

export default EditCompanyDialog;
