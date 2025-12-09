import React, { useEffect, useRef } from 'react';
import Button from '@mui/material/Button';
import CircularProgress from '@mui/material/CircularProgress';
import TextField from '@mui/material/TextField';
import Link from '@mui/material/Link';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Divider from '@mui/material/Divider';
import { useForm, SubmitHandler } from 'react-hook-form';
import { Link as RouterLink } from 'react-router-dom';

import { useAuthLogin } from '../../hooks/login/auth';
import { PasswordInputField } from '../../components/forms/PasswordInputField/PasswordInputField';

type LoginFormInputs = {
  email: string;
  password: string;
};

const Login: React.FC = () => {
  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isValid }
  } = useForm<LoginFormInputs>({
    mode: 'onChange',
    criteriaMode: 'all',
    reValidateMode: 'onChange',
    defaultValues: {
      email: '',
      password: ''
    }
  });
  const email = watch('email');
  const password = watch('password');
  const emailRef = useRef<HTMLInputElement | null>(null);
  const passwordRef = useRef<HTMLInputElement | null>(null);
  const { mutation, serverError } = useAuthLogin();

  useEffect(() => {
    setTimeout(() => {
      if (emailRef.current && passwordRef.current) {
        setValue('email', emailRef.current.value);
        setValue('password', passwordRef.current.value);
      }
    }, 500);
  }, [setValue]);

  const onSubmit: SubmitHandler<LoginFormInputs> = (data: any) => {
    mutation.mutate(data);
  };

  const errorMsg = {
    email: 'Use the correct format of email: email@example.com',
    password: 'Password have to contain at least 1 character.'
  };

  const isSubmitDisabled = !email || !password || Object.keys(errors).length > 0 || !isValid;

  return (
    <>
      <Typography
        data-testid="login__signin-form-title"
        component="h4"
        fontSize="34px"
        fontWeight={600}
        lineHeight="42px"
        textAlign="center"
      >
        Sign In
      </Typography>
      <Box
        component="form"
        onSubmit={handleSubmit(onSubmit)}
        noValidate
        sx={{
          'input:-webkit-autofill': {
            WebkitBackgroundClip: 'text',
            WebkitTextFillColor: '#000',
            boxShadow: 'inset 0 0 20px 20px transparent',
            transition: 'background-color 5000s ease-in-out 0s'
          }
        }}
      >
        <TextField
          variant="filled"
          fullWidth
          id="email"
          label="Email"
          data-testid="login_email-field"
          inputRef={emailRef}
          autoComplete="off"
          {...register('email', {
            required: errorMsg.email,
            pattern: { value: /\S+@\S+\.\S+/, message: errorMsg.email }
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
        <PasswordInputField
          variant="filled"
          label="Password"
          id="password"
          data-testid="login_password-field"
          inputRef={passwordRef}
          autoComplete="off"
          helperText={errors.password?.message}
          error={!!errors.password}
          {...register('password', {
            required: errorMsg.password,
            minLength: { value: 1, message: errorMsg.password }
          })}
        />
        {serverError && (
          <Typography variant="caption" sx={{ color: 'error.main', display: 'block', margin: '3px 14px 0' }}>
            {serverError}
          </Typography>
        )}
        <Button
          type="submit"
          fullWidth
          variant="contained"
          data-testid="login_signin-btn"
          disabled={isSubmitDisabled || mutation.isPending}
          sx={{ mt: 2 }}
        >
          {mutation.isPending ? <CircularProgress size={24} /> : 'Sign In'}
        </Button>
        <Divider sx={{ mt: 2, mb: 2 }} />
        <Box sx={{ textAlign: 'center' }}>
          <Link component={RouterLink} to="/forgot-password" variant="body2">
            Forgot Password?
          </Link>
        </Box>
      </Box>
    </>
  );
};

export default Login;
