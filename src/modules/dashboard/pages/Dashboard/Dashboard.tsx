import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Grid from '@mui/material/Grid';

import TaskDashboardList from '../../components/TaskDashboardList/TaskDashboardList';
import NotificationList from '../../components/NotificationList/NotificationList';

export const DashboardPage: React.FC = () => {
  return (
    <Box>
      <Typography variant="h4" marginBottom="24px" sx={{ fontWeight: 600 }} fontSize="34px" lineHeight="42px">
        Dashboard
      </Typography>
      <Grid container spacing={2}>
        <Grid item xs={8}>
          <TaskDashboardList />
        </Grid>
        <Grid item xs={4}>
          <NotificationList />
        </Grid>
      </Grid>
    </Box>
  );
};

export default DashboardPage;
