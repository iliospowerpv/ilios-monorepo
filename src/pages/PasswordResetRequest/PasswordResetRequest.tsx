import React from 'react';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import TextField from '@mui/material/TextField';
import Link from '@mui/material/Link';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Divider from '@mui/material/Divider';
import { useForm, SubmitHandler } from 'react-hook-form';
import { Link as RouterLink } from 'react-router-dom';
import { AxiosError } from 'axios';

import { useResetRequest } from '../../hooks/reset-request/reset-request';

type ResetFormInputs = {
  email: string;
};

const PasswordResetRequest: React.FC = () => {
  const {
    register,
    handleSubmit,
    formState: { errors, isValid }
  } = useForm<ResetFormInputs>({
    mode: 'onBlur',
    criteriaMode: 'all',
    reValidateMode: 'onBlur'
  });
  const { mutation } = useResetRequest();

  const onSubmit: SubmitHandler<ResetFormInputs> = (data: any) => {
    mutation.mutate(data);
  };

  return (
    <>
      <Typography
        data-testid="reset__request-password-reset-title"
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
        Enter the email you use for ilios
      </Typography>
      <Box component="form" onSubmit={handleSubmit(onSubmit)} noValidate>
        <TextField
          variant="filled"
          fullWidth
          id="email"
          label="Email"
          data-testid="login_email-field"
          {...register('email', {
            required: 'Use the correct format of email: email@example.com',
            pattern: { value: /\S+@\S+\.\S+/, message: 'Use the correct format of email: email@example.com' }
          })}
          error={!!errors.email}
          helperText={errors.email?.message}
          sx={{
            mt: 2,
            '& .MuiInputBase-root:not(.Mui-disabled, .Mui-error)': {
              '&::before, &:hover::before, &.Mui-focused::after': {
                borderBottomColor: 'transparent',
                transform: 'scaleX(0)'
              }
            }
          }}
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
          disabled={!isValid || mutation.isPending}
          sx={{ mt: 2 }}
        >
          {mutation.isPending ? <CircularProgress size={24} /> : 'Continue'}
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

export default PasswordResetRequest;
