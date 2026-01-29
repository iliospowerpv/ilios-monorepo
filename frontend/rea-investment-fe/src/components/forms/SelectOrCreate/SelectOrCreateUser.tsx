import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import Autocomplete from '@mui/material/Autocomplete';
import TextField from '@mui/material/TextField';
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import Divider from '@mui/material/Divider';
import AddIcon from '@mui/icons-material/Add';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';

import { ApiClient } from '../../../api';
import type { User, CreateUserAttributes } from '../../../api';
import { useNotify } from '../../../contexts/notifications/notifications';

const CREATE_NEW_SENTINEL = '__create_new__';

interface SelectOrCreateUserProps {
  value: number | null;
  onChange: (userId: number | null) => void;
  canCreate?: boolean;
  defaultCompanyId?: number;
  label?: string;
  required?: boolean;
  disabled?: boolean;
  helperText?: string;
  error?: boolean;
}

interface CreateUserFormData {
  email: string;
  first_name: string;
  last_name: string;
  phone: string;
}

type ViewMode = 'select' | 'create';

interface SentinelOption {
  id: typeof CREATE_NEW_SENTINEL;
  first_name: string;
  last_name: string;
  email: string;
}

type OptionType = User | SentinelOption;

const isSentinel = (option: OptionType): option is SentinelOption => {
  return option.id === CREATE_NEW_SENTINEL;
};

export const SelectOrCreateUser: React.FC<SelectOrCreateUserProps> = ({
  value,
  onChange,
  canCreate = true,
  defaultCompanyId,
  label = 'Select User',
  required = false,
  disabled = false,
  helperText,
  error = false
}) => {
  const queryClient = useQueryClient();
  const notify = useNotify();
  const [mode, setMode] = useState<ViewMode>('select');
  const [createError, setCreateError] = useState<string | null>(null);
  const [formData, setFormData] = useState<CreateUserFormData>({
    email: '',
    first_name: '',
    last_name: '',
    phone: ''
  });

  const canShowCreateOption = canCreate && defaultCompanyId !== undefined && defaultCompanyId > 0;

  const { data: usersData, isLoading: isLoadingUsers } = useQuery({
    queryKey: ['users'],
    queryFn: () => ApiClient.user.users({ skip: 0, limit: 100 })
  });

  const { data: rolesData } = useQuery({
    queryKey: ['roles'],
    queryFn: () => ApiClient.user.roles(),
    enabled: mode === 'create'
  });

  const createUserMutation = useMutation({
    mutationFn: (attributes: CreateUserAttributes) => ApiClient.user.create(attributes),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['users'] });
      const updatedUsers = await queryClient.fetchQuery({
        queryKey: ['users'],
        queryFn: () => ApiClient.user.users({ skip: 0, limit: 100 })
      });
      const newUser = updatedUsers.items.find((u: User) => u.email.toLowerCase() === formData.email.toLowerCase());
      if (newUser) {
        onChange(newUser.id);
      }
      notify('User created successfully');
      setFormData({ email: '', first_name: '', last_name: '', phone: '' });
      setCreateError(null);
      setMode('select');
    },
    onError: (err: any) => {
      setCreateError(err.response?.data?.detail || err.response?.data?.message || 'Failed to create user');
    }
  });

  const selectedUser = usersData?.items.find((u: User) => u.id === value) || null;

  const handleAutocompleteChange = (_: any, option: OptionType | null) => {
    if (option && isSentinel(option)) {
      setMode('create');
      return;
    }
    onChange((option?.id as number) ?? null);
  };

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setCreateError(null);

    if (!formData.email.trim()) {
      setCreateError('Email is required');
      return;
    }
    if (!formData.first_name.trim()) {
      setCreateError('First name is required');
      return;
    }
    if (!formData.last_name.trim()) {
      setCreateError('Last name is required');
      return;
    }

    if (!defaultCompanyId || defaultCompanyId <= 0) {
      setCreateError('A company must be selected before creating a user');
      return;
    }

    const defaultRole = rolesData?.find(r => r.name.toLowerCase() === 'read only') || rolesData?.[0];
    if (!defaultRole) {
      setCreateError('No roles available');
      return;
    }

    const attributes: CreateUserAttributes = {
      email: formData.email.trim(),
      first_name: formData.first_name.trim(),
      last_name: formData.last_name.trim(),
      phone: formData.phone.trim() || '',
      parent_company_id: defaultCompanyId,
      role_id: defaultRole.id,
      sites_ids: []
    };

    createUserMutation.mutate(attributes);
  };

  const handleBackToSelect = () => {
    setMode('select');
    setFormData({ email: '', first_name: '', last_name: '', phone: '' });
    setCreateError(null);
  };

  const options: OptionType[] = [
    ...(canShowCreateOption
      ? [
          {
            id: CREATE_NEW_SENTINEL as typeof CREATE_NEW_SENTINEL,
            first_name: '+ Create',
            last_name: 'New User',
            email: ''
          }
        ]
      : []),
    ...(usersData?.items || [])
  ];

  if (mode === 'create') {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Button
            size="small"
            startIcon={<ArrowBackIcon />}
            onClick={handleBackToSelect}
            disabled={createUserMutation.isPending}
          >
            Back to selection
          </Button>
        </Box>

        <Typography variant="subtitle2" color="primary">
          Create New User
        </Typography>

        {createError && (
          <Alert severity="error" onClose={() => setCreateError(null)}>
            {createError}
          </Alert>
        )}

        <form onSubmit={handleCreateSubmit}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <TextField
              label="Email"
              type="email"
              value={formData.email}
              onChange={e => setFormData(prev => ({ ...prev, email: e.target.value }))}
              required
              fullWidth
              size="small"
              disabled={createUserMutation.isPending}
            />

            <Box sx={{ display: 'flex', gap: 2 }}>
              <TextField
                label="First Name"
                value={formData.first_name}
                onChange={e => setFormData(prev => ({ ...prev, first_name: e.target.value }))}
                required
                fullWidth
                size="small"
                disabled={createUserMutation.isPending}
              />
              <TextField
                label="Last Name"
                value={formData.last_name}
                onChange={e => setFormData(prev => ({ ...prev, last_name: e.target.value }))}
                required
                fullWidth
                size="small"
                disabled={createUserMutation.isPending}
              />
            </Box>

            <TextField
              label="Phone (optional)"
              value={formData.phone}
              onChange={e => setFormData(prev => ({ ...prev, phone: e.target.value }))}
              fullWidth
              size="small"
              disabled={createUserMutation.isPending}
            />

            <Button
              type="submit"
              variant="contained"
              disabled={createUserMutation.isPending}
              startIcon={createUserMutation.isPending ? <CircularProgress size={16} /> : <AddIcon />}
            >
              {createUserMutation.isPending ? 'Creating...' : 'Create User'}
            </Button>
          </Box>
        </form>
      </Box>
    );
  }

  return (
    <Autocomplete
      value={selectedUser}
      options={options}
      getOptionLabel={option => {
        if (isSentinel(option)) {
          return '+ Create New User...';
        }
        return `${option.first_name} ${option.last_name} (${option.email})`;
      }}
      isOptionEqualToValue={(option, val) => {
        if (isSentinel(option) || isSentinel(val)) return false;
        return option.id === val.id;
      }}
      loading={isLoadingUsers}
      disabled={disabled}
      onChange={handleAutocompleteChange}
      renderOption={(props, option) => {
        if (isSentinel(option)) {
          return (
            <Box component="li" {...props} key="create-new">
              <Divider sx={{ width: '100%', my: 1 }} />
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, color: 'primary.main', fontWeight: 600 }}>
                <AddIcon fontSize="small" />
                <Typography variant="body2" sx={{ fontWeight: 600 }}>
                  Create New User...
                </Typography>
              </Box>
            </Box>
          );
        }
        return (
          <Box component="li" {...props} key={option.id}>
            <Box>
              <Typography variant="body2">
                {option.first_name} {option.last_name}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {option.email}
              </Typography>
            </Box>
          </Box>
        );
      }}
      renderInput={params => (
        <TextField
          {...params}
          label={label}
          required={required}
          error={error}
          helperText={helperText}
          InputProps={{
            ...params.InputProps,
            endAdornment: (
              <>
                {isLoadingUsers ? <CircularProgress color="inherit" size={20} /> : null}
                {params.InputProps.endAdornment}
              </>
            )
          }}
        />
      )}
    />
  );
};

export default SelectOrCreateUser;
