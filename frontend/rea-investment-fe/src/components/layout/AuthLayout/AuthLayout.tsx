import * as React from 'react';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import { Navigate } from 'react-router-dom';

import { Header } from './Header/Header';
import { Main } from './Main/Main';
import { Copyright } from './Copyright/Copyright';
import { useAuth } from '../../../contexts/auth/auth';

export const AuthLayout: React.FC = () => {
  const { isAuthPending, isAuthenticated } = useAuth();

  if (isAuthPending) return null;

  if (isAuthenticated) {
    return <Navigate to="/dashboard" replace />;
  }

  return (
    <Box sx={{ display: 'flex' }}>
      <CssBaseline />
      <Header />
      <Main />
      <Copyright />
    </Box>
  );
};
