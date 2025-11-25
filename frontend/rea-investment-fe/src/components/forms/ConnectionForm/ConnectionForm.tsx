import React, { useState } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { useForm, SubmitHandler, Controller } from 'react-hook-form';
import Stack from '@mui/material/Stack';
import Button from '@mui/material/Button';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';

import { ApiClient, Connection } from '../../../api';
import { useNotify } from '../../../contexts/notifications/notifications';
import FormControl from '@mui/material/FormControl';
import InputLabel from '@mui/material/InputLabel';
import Select from '@mui/material/Select';
import { DAS_CONNECTION } from '../../../utils/asset-managment';
import MenuItem from '@mui/material/MenuItem';
import FormHelperText from '@mui/material/FormHelperText';
import CircularProgress from '@mui/material/CircularProgress';
import { PasswordInputField } from '../PasswordInputField/PasswordInputField';

const noBottomLineStyles = {
  '& .MuiInputBase-root:not(.Mui-disabled, .Mui-error)': {
    '&::before, &:hover::before, &.Mui-focused::after': {
      borderBottomColor: 'transparent',
      transform: 'scaleX(0)'
    }
  }
};

interface ConnectionFormFields {
  provider: string;
  name: string;
  token: string;
  username: string;
  password: string;
}

type ConnectionFormProps = {
  companyId: number;
  connection: Connection;
  onCancel: () => void;
  onSave: (c: ConnectionFormFields) => void;
};

export const ConnectionForm: React.FC<ConnectionFormProps> = props => {
  const { connection, companyId, onCancel, onSave } = props;
  const { mutateAsync, isPending } = useMutation({
    mutationFn: (attributes: Connection) =>
      connection.isNotSaved
        ? ApiClient.connections.createConnection(companyId, attributes)
        : ApiClient.connections.updateConnection(companyId, connection.id, attributes)
  });
  const notify = useNotify();
  const queryClient = useQueryClient();
  const [showToken, setShowToken] = useState(!connection.isEditing || connection.isNotSaved);
  const [invalidToken, setInvalidToken] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors, isValid, isDirty, touchedFields },
    setError,
    control,
    clearErrors,
    trigger,
    setValue,
    watch
  } = useForm<ConnectionFormFields>({
    mode: 'all',
    criteriaMode: 'all',
    reValidateMode: 'onChange',
    defaultValues: {
      provider: connection.provider || '',
      name: connection.name || '',
      token: (connection.isNotSaved ? connection.token : '') ?? '',
      username: (connection.isNotSaved ? connection.username : '') ?? '',
      password: (connection.isNotSaved ? connection.password : '') ?? ''
    }
  });

  const provider = watch('provider');

  React.useEffect(() => {
    const subscription = watch((_value, { name, type }) => {
      if (name === 'provider' && ['change', 'changeText', 'valueChange', 'selectionChange'].includes(type || '')) {
        setValue('token', '');
        setValue('username', '');
        setValue('password', '');
        clearErrors('token');
        clearErrors('username');
        clearErrors('password');
        setInvalidToken(false);
      }
    });

    return () => subscription.unsubscribe();
  }, [watch, setValue, connection, clearErrors]);

  const onSubmit: SubmitHandler<ConnectionFormFields> = async data => {
    setIsSaving(true);

    try {
      clearErrors('root');
      await mutateAsync({
        name: data.name,
        ...(connection.isNotSaved && { provider: data.provider }),
        ...(data.provider === 'Also Energy'
          ? {
              username: data.username || null,
              password: data.password || null
            }
          : { token: data.token || null })
      });
      queryClient.removeQueries({ queryKey: ['connections'] });
      notify(
        connection.isNotSaved ? 'Connection has been successfully created' : 'Connection has been successfully updated'
      );
      onSave(data);
    } catch (e: any) {
      if (e.response?.data?.message?.includes('Invalid credentials')) {
        setInvalidToken(true);
        clearErrors('root');
      } else {
        setError('root', {
          message: e.response?.data?.message
        });

        setTimeout(() => {
          clearErrors('root');
          trigger();
        }, 5000);
      }
    } finally {
      setIsSaving(false);
      setTimeout(() => trigger(), 150);
    }
  };

  const handleFocus = (field: 'password' | 'token' | 'username') => () => {
    if (connection.isEditing && !connection.isNotSaved && !touchedFields[field]) {
      setValue(field, '');
      setShowToken(true);
    }
  };

  return (
    <Stack component="form" data-testid="connection__form" noValidate spacing={2} onSubmit={handleSubmit(onSubmit)}>
      <Typography variant="h6" gutterBottom>
        New Connection
      </Typography>
      <Controller
        name="provider"
        control={control}
        rules={{ required: 'Data Provider is required field.' }}
        render={({ field }) => (
          <FormControl error={!!errors.provider} variant="filled" required sx={noBottomLineStyles}>
            <InputLabel error={!!errors.provider}>Data Provider</InputLabel>
            <Select
              ref={field.ref}
              value={field.value}
              error={!!errors.provider}
              disabled={!connection.isNotSaved}
              label="Data Provider"
              onBlur={field.onBlur}
              onChange={event => {
                field.onChange(event.target.value);
                invalidToken && setInvalidToken(false);
                clearErrors('token');
              }}
            >
              {Object.entries(DAS_CONNECTION).map(([key, value]) => (
                <MenuItem key={key} value={value}>
                  {value}
                </MenuItem>
              ))}
            </Select>
            {errors.provider?.message && <FormHelperText error>{errors.provider.message}</FormHelperText>}
          </FormControl>
        )}
      />
      <TextField
        variant="filled"
        required
        label="Connection Name"
        sx={noBottomLineStyles}
        helperText={errors.name?.message}
        error={!!errors.name}
        {...register('name', {
          required: 'Connection Name is required field.',
          minLength: {
            value: 2,
            message: 'Connection Name length should be between 2 and 100 characters.'
          },
          maxLength: {
            value: 100,
            message: 'Connection Name length should be between 2 and 100 characters.'
          }
        })}
      />
      {provider === 'Also Energy' ? (
        <>
          <Controller
            name="username"
            control={control}
            rules={{
              validate: value => {
                if (invalidToken) return '';
                if (
                  connection.isEditing &&
                  !connection.isNotSaved &&
                  !touchedFields['password'] &&
                  !touchedFields['username']
                )
                  return true;
                return !!value || 'Login is required field.';
              }
            }}
            render={({ field }) => (
              <TextField
                {...field}
                onChange={evt => {
                  invalidToken && setInvalidToken(false);
                  trigger('password');
                  field.onChange(evt);
                }}
                onBlur={() => {
                  setTimeout(() => trigger(['password', 'username']), 150);
                  field.onBlur();
                }}
                value={showToken ? field.value : '<<hidden>>'}
                variant="filled"
                required
                fullWidth
                label="Login"
                type={showToken ? 'text' : 'password'}
                id="field1"
                error={!!errors.username}
                helperText={errors.username?.message}
                sx={noBottomLineStyles}
                onFocus={handleFocus('username')}
                inputProps={{
                  autoComplete: 'new-password',
                  form: {
                    autoComplete: 'off'
                  }
                }}
              />
            )}
          />
          <Controller
            name="password"
            control={control}
            rules={{
              validate: value => {
                if (invalidToken) return 'Invalid credentials. Please check and try again.';
                if (
                  connection.isEditing &&
                  !connection.isNotSaved &&
                  !touchedFields['password'] &&
                  !touchedFields['username']
                )
                  return true;
                return !!value || 'Password is required field.';
              }
            }}
            render={({ field }) => (
              <PasswordInputField
                {...field}
                onChange={evt => {
                  invalidToken && setInvalidToken(false);
                  trigger('username');
                  field.onChange(evt);
                }}
                onBlur={() => {
                  setTimeout(() => trigger(['password', 'username']), 150);
                  field.onBlur();
                }}
                value={showToken ? field.value : '1234567890'}
                variant="filled"
                required
                fullWidth
                label="Password"
                id="field2"
                helperText={errors.password?.message}
                error={!!errors.password}
                onFocus={handleFocus('password')}
                inputProps={{
                  autoComplete: 'new-password',
                  form: {
                    autoComplete: 'off'
                  }
                }}
              />
            )}
          />
        </>
      ) : (
        <Controller
          name="token"
          control={control}
          rules={{
            validate: value => {
              if (invalidToken) return 'Invalid credentials. Please check and try again.';
              if (connection.isEditing && !connection.isNotSaved && !touchedFields['token']) return true;
              return !!value || 'Auth Token is required field.';
            }
          }}
          render={({ field }) => (
            <TextField
              {...field}
              onChange={evt => {
                invalidToken && setInvalidToken(false);
                field.onChange(evt);
              }}
              value={showToken ? field.value : '1234567890'}
              variant="filled"
              required
              fullWidth
              label="Auth Token"
              type={showToken ? 'text' : 'password'}
              sx={noBottomLineStyles}
              helperText={errors.token?.message}
              error={!!errors.token}
              onFocus={handleFocus('token')}
            />
          )}
        />
      )}
      <Stack direction="row" width="100%" spacing={3} justifyContent="end">
        <Button variant="outlined" disabled={isSaving || isPending} onClick={onCancel}>
          Cancel
        </Button>
        <Button
          variant="contained"
          type="submit"
          disabled={!isValid || !!errors.root || !isDirty || isSaving || isPending}
          sx={{ width: '112px' }}
        >
          {isSaving ? <CircularProgress color="inherit" size={20} /> : 'Verify & Add'}
        </Button>
      </Stack>
      {errors.root && (
        <Typography px="4px" color="error">
          {errors.root?.message}
        </Typography>
      )}
    </Stack>
  );
};
