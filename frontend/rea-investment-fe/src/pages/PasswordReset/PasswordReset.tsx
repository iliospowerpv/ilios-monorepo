import React, { useEffect } from 'react';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Link from '@mui/material/Link';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Divider from '@mui/material/Divider';
import { useForm } from 'react-hook-form';
import { Link as RouterLink, useNavigate } from 'react-router-dom';
import { AxiosError } from 'axios';

import { useReset } from '../../hooks/reset/reset';
import { useQuery } from '@tanstack/react-query';
import { ApiClient } from '../../api';
import { PasswordInputField } from '../../components/forms/PasswordInputField/PasswordInputField';

interface ResetFormInputs {
  password: string;
  confirmPassword: string;
}

const PasswordReset: React.FC = () => {
  const {
    register,
    handleSubmit,
    formState: { errors, isValid },
    watch,
    setError,
    clearErrors
  } = useForm<ResetFormInputs>({
    mode: 'onChange',
    criteriaMode: 'all',
    reValidateMode: 'onChange'
  });
  const navigate = useNavigate();
  const { mutation } = useReset();

  const queryParams = React.useMemo(() => new URLSearchParams(location.search), [location]);
  const email = queryParams.get('email') || '';
  const token = queryParams.get('token') || '';

  const { isError, isPending } = useQuery({
    queryFn: () => ApiClient.passwordRecovery.emailToken({ email, token }),
    queryKey: ['passwordRecovery', email, token],
    retry: 0
  });

  useEffect(() => {
    if (isError) {
      navigate('/password-reset-invalid');
    }
  }, [isError, navigate]);

  const password = watch('password');
  const confirmPassword = watch('confirmPassword');

  useEffect(() => {
    if (password && confirmPassword && password !== confirmPassword) {
      setError('confirmPassword', { type: 'manual', message: `The password doesn't match.` });
    } else {
      clearErrors('confirmPassword');
    }
  }, [password, confirmPassword, setError, clearErrors]);

  const onSubmit = async (data: ResetFormInputs) => {
    await mutation.mutateAsync({ email, token, password: data.password });
  };

  const isSubmitDisabled = !password || !confirmPassword || Object.keys(errors).length > 0 || !isValid;

  if (isPending || isError) {
    return (
      <Box
        data-testid="reset__password-reset-white-screen"
        position="fixed"
        top="0"
        left="0"
        height="100vh"
        width="100vw"
        sx={{ bgcolor: 'white', zIndex: theme => theme.zIndex.appBar }}
      />
    );
  }

  return (
    <>
      <Typography
        data-testid="reset__password-reset-title"
        component="h4"
        fontSize="34px"
        fontWeight={600}
        lineHeight="42px"
        textAlign="center"
        sx={{ mb: 2 }}
      >
        Password Recovery
      </Typography>
      <Typography variant="body2" fontSize="14px" color="text.secondary" lineHeight="20px" textAlign="center">
        Create new password for email:
      </Typography>
      <Typography variant="body2" fontSize="14px" color="text.secondary" lineHeight="20px" textAlign="center">
        <b>{email}</b>
      </Typography>
      <Box component="form" onSubmit={handleSubmit(onSubmit)} noValidate>
        <PasswordInputField
          variant="filled"
          label="New Password"
          id="password"
          data-testid="reset_password-field"
          helperText={
            errors.password?.message ||
            'Use at least 8 characters including uppercase and lowercase letters, numbers and symbols, avoid spaces'
          }
          error={!!errors.password}
          {...register('password', {
            required: true,
            minLength: {
              value: 8,
              message: 'Please use 8+ characters for password'
            },
            maxLength: {
              value: 255,
              message: 'Password length must not exceed 255 characters'
            },
            pattern: {
              value:
                /^(?=.*[0-9])(?=.*[a-z])(?=.*[A-Z])(?=.*[~`!@#$%^&*()_+={}[\]|\\;:"<>,./?-])[a-zA-Z0-9~`!@#$%^&*()_+={}[\]|\\;:"<>,./?-]{8,255}$/,
              message:
                'Password must contain at least 1 uppercase and lowercase letter, 1 digit, 1 special symbol (~`!@#$%^&*()-_+={}[]|\\;:"<>,./?), spaces are not allowed'
            }
          })}
        />
        <PasswordInputField
          variant="filled"
          label="Repeat New Password"
          id="confirm-password"
          data-testid="reset_confirm-password-field"
          error={!!errors.confirmPassword}
          helperText={errors.confirmPassword?.message}
          {...register('confirmPassword', {
            required: true,
            validate: value => value === password || `The password doesn't match.`
          })}
        />
        {mutation.error && (
          <Typography variant="caption" sx={{ color: 'error.main', display: 'block', margin: '3px 14px 0' }}>
            {(mutation.error instanceof AxiosError && mutation.error.response?.data?.message) || mutation.error.message}
          </Typography>
        )}
        <Button
          type="submit"
          fullWidth
          variant="contained"
          data-testid="reset_continue-btn"
          disabled={isSubmitDisabled || mutation.isPending}
          sx={{ mt: 2 }}
        >
          {mutation.isPending ? <CircularProgress size={24} /> : 'Update'}
        </Button>
        <Divider sx={{ mt: 2, mb: 2 }} />
        <Box sx={{ textAlign: 'center' }}>
          <Link component={RouterLink} to="/login" variant="body2">
            Back to Sign In
          </Link>
        </Box>
      </Box>
    </>
  );
};

export default PasswordReset;
