import * as React from 'react';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import { Navigate } from 'react-router-dom';

import { PageHeader } from '../PageHeader/PageHeader';
import { PageSidebar } from '../PageSidebar/PageSidebar';
import { useAuth } from '../../../contexts/auth/auth';
import CustomError from '../CustomError/CustomError';

export const ErrorLayout: React.FC = () => {
  const { isAuthPending, isAuthenticated } = useAuth();

  if (isAuthPending) return null;

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <Box sx={{ display: 'flex' }}>
      <CssBaseline />
      <PageHeader />
      <PageSidebar />
      <CustomError />
    </Box>
  );
};
