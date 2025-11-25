import React from 'react';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { useForm } from 'react-hook-form';

import { PasswordInputField } from '../../../components/forms/PasswordInputField/PasswordInputField';

import { SignUpFormInputs, SignUpScreenProps } from './types';

export const SignUpFormScreen: React.FC<SignUpScreenProps> = ({ email, formSubmit, isSubmitPending, errorMessage }) => {
  const {
    register,
    handleSubmit,
    formState: { errors, isValid },
    watch,
    setError,
    clearErrors
  } = useForm<SignUpFormInputs>({
    mode: 'onChange',
    criteriaMode: 'all',
    reValidateMode: 'onChange'
  });

  const password = watch('password');
  const confirmPassword = watch('confirmPassword');

  React.useEffect(() => {
    if (password && confirmPassword && password !== confirmPassword) {
      setError('confirmPassword', { type: 'manual', message: `The password doesn't match.` });
    } else {
      clearErrors('confirmPassword');
    }
  }, [password, confirmPassword, setError, clearErrors]);

  const isSubmitDisabled = !password || !confirmPassword || Object.keys(errors).length > 0 || !isValid;

  return (
    <>
      <Typography
        data-testid="sign_up-account-creation-title"
        component="h4"
        fontSize="34px"
        fontWeight={600}
        lineHeight="42px"
        textAlign="center"
        sx={{ mb: 1 }}
      >
        Account Creation
      </Typography>
      <Typography
        variant="body2"
        fontSize="14px"
        fontWeight={400}
        color="text.secondary"
        lineHeight="20px"
        textAlign="center"
      >
        Finish profile creation for email:
      </Typography>
      <Typography
        variant="body2"
        fontSize="14px"
        fontWeight={700}
        color="text.secondary"
        lineHeight="20px"
        textAlign="center"
      >
        {email}
      </Typography>
      <Box sx={{ mt: 1 }} component="form" onSubmit={handleSubmit(formSubmit)} noValidate>
        <PasswordInputField
          variant="filled"
          label="Password"
          id="password"
          data-testid="sign_up_password-field"
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
          label="Repeat Password"
          id="confirm-password"
          data-testid="sign_up_confirm-password-field"
          error={!!errors.confirmPassword}
          helperText={errors.confirmPassword?.message}
          {...register('confirmPassword', {
            required: true,
            validate: value => value === password || `The password doesn't match.`
          })}
        />
        {errorMessage && (
          <Typography variant="caption" sx={{ color: 'error.main', display: 'block', margin: '3px 14px 0' }}>
            {errorMessage}
          </Typography>
        )}
        <Button
          type="submit"
          fullWidth
          variant="contained"
          data-testid="reset_continue-btn"
          disabled={isSubmitDisabled || isSubmitPending}
          sx={{ mt: 2 }}
        >
          <Typography
            px="10px"
            component="span"
            fontWeight={700}
            fontSize="15px"
            lineHeight="26px"
            variant="body2"
            textAlign="center"
          >
            Create
          </Typography>
          {isSubmitPending && <CircularProgress size={18} />}
        </Button>
      </Box>
    </>
  );
};
