import React, { useState, useCallback, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';

import { ApiClient } from '../../../../api';
import { HomeSummaryCards } from '../../components/HomeSummaryCards';
import { HomeTasks } from '../../components/HomeTasks';
import { HomeNotifications } from '../../components/HomeNotifications';
import { HomeCompanies } from '../../components/HomeCompanies';
import { HomeQuickActions } from '../../components/HomeQuickActions';
import { DashboardGrid } from '../../components/Dashboard/DashboardGrid';
import { CreateCompanyDialog, CreateProjectDialog, InviteUserDialog } from './dialogs';

export const HomePage: React.FC = () => {
  const [notificationsCount, setNotificationsCount] = useState(0);
  const [createCompanyOpen, setCreateCompanyOpen] = useState(false);
  const [createProjectOpen, setCreateProjectOpen] = useState(false);
  const [inviteUserOpen, setInviteUserOpen] = useState(false);

  const {
    data: workspace,
    isLoading: isLoadingWorkspace,
    error: workspaceError,
    refetch: refetchWorkspace
  } = useQuery({
    queryKey: ['home-workspace'],
    queryFn: () => ApiClient.workspace.getWorkspace(),
    staleTime: 5 * 60 * 1000
  });

  const handleNotificationsLoaded = useCallback((count: number) => {
    setNotificationsCount(count);
  }, []);

  const handleCompanyCreated = useCallback(() => {
    setCreateCompanyOpen(false);
    refetchWorkspace();
  }, [refetchWorkspace]);

  const handleProjectCreated = useCallback(() => {
    setCreateProjectOpen(false);
    refetchWorkspace();
  }, [refetchWorkspace]);

  const handleUserInvited = useCallback(() => {
    setInviteUserOpen(false);
  }, []);

  const widgetComponents = useMemo(
    () => ({
      tasks: <HomeTasks />,
      notifications: <HomeNotifications onNotificationsLoaded={handleNotificationsLoaded} />,
      quickActions: (
        <HomeQuickActions
          onCreateCompany={() => setCreateCompanyOpen(true)}
          onCreateProject={() => setCreateProjectOpen(true)}
          onInviteUser={() => setInviteUserOpen(true)}
        />
      ),
      companies: <HomeCompanies companies={workspace?.companies ?? []} isLoading={isLoadingWorkspace} />
    }),
    [workspace?.companies, isLoadingWorkspace, handleNotificationsLoaded]
  );

  if (workspaceError) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">Failed to load home data. Please try again later.</Alert>
      </Box>
    );
  }

  const summary = workspace?.summary ?? {
    companies_count: 0,
    projects_count: 0,
    pending_tasks_count: 0,
    needs_attention_count: 0
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" component="h1" gutterBottom sx={{ mb: 3 }}>
        Home
      </Typography>

      <Box sx={{ mb: 4 }}>
        <HomeSummaryCards
          companiesCount={summary.companies_count}
          projectsCount={summary.projects_count}
          pendingTasksCount={summary.pending_tasks_count}
          notificationsCount={notificationsCount}
          isLoading={isLoadingWorkspace}
        />
      </Box>

      <DashboardGrid widgetComponents={widgetComponents} />

      <CreateCompanyDialog
        open={createCompanyOpen}
        onClose={() => setCreateCompanyOpen(false)}
        onSuccess={handleCompanyCreated}
      />

      <CreateProjectDialog
        open={createProjectOpen}
        onClose={() => setCreateProjectOpen(false)}
        onSuccess={handleProjectCreated}
      />

      <InviteUserDialog open={inviteUserOpen} onClose={() => setInviteUserOpen(false)} onSuccess={handleUserInvited} />
    </Box>
  );
};

export default HomePage;
