import * as React from 'react';
import CssBaseline from '@mui/material/CssBaseline';
import Box from '@mui/material/Box';
import { Navigate } from 'react-router-dom';

import { PageHeader } from '../PageHeader/PageHeader';
import { PageSidebar } from '../PageSidebar/PageSidebar';
import { Main } from '../Main/Main';
import { GlobalAdminBanner } from '../GlobalAdminBanner/GlobalAdminBanner';
import { useAuth } from '../../../contexts/auth/auth';
import { SidebarProvider } from '../../../contexts/sidebar';
import { EntityContextProvider } from '../../../contexts/entityContext';
import { AssistantWidget } from '../../assistant';

export const BaseLayout: React.FC = () => {
  const { isAuthPending, isAuthenticated } = useAuth();

  if (isAuthPending) return null;

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  return (
    <EntityContextProvider>
      <SidebarProvider>
        <Box sx={{ display: 'flex' }}>
          <CssBaseline />
          <GlobalAdminBanner />
          <PageHeader />
          <PageSidebar />
          <Main />
          <AssistantWidget />
        </Box>
      </SidebarProvider>
    </EntityContextProvider>
  );
};
