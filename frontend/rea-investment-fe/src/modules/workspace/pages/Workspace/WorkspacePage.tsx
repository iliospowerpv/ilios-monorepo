import React from 'react';
import { useQuery } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';

import { ApiClient } from '../../../../api';
import { SummaryCards } from '../../components/SummaryCards';
import { CompanyList } from '../../components/CompanyList';

export const WorkspacePage: React.FC = () => {
  const {
    data: workspace,
    isLoading,
    error
  } = useQuery({
    queryKey: ['workspace'],
    queryFn: () => ApiClient.workspace.getWorkspace(),
    staleTime: 5 * 60 * 1000
  });

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Alert severity="error">Failed to load workspace data. Please try again later.</Alert>
      </Box>
    );
  }

  const defaultSummary = {
    companies_count: 0,
    projects_count: 0,
    pending_tasks_count: 0,
    needs_attention_count: 0
  };

  return (
    <Box sx={{ p: 3 }}>
      <Typography variant="h4" component="h1" gutterBottom sx={{ mb: 3 }}>
        Workspace
      </Typography>

      <Box sx={{ mb: 4 }}>
        <SummaryCards summary={workspace?.summary ?? defaultSummary} isLoading={isLoading} />
      </Box>

      <CompanyList companies={workspace?.companies ?? []} isLoading={isLoading} />
    </Box>
  );
};

export default WorkspacePage;
