import React from 'react';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';

import { GeneralInfo } from './components/GeneralInfo';
import { Performance } from './components/Performance';

import { DeviceDetailsTabProps } from '../types';

const OverviewTab: React.FC<DeviceDetailsTabProps> = ({ deviceDetails }) => {
  const { general_info, performance_details } = deviceDetails;

  return (
    <Box maxWidth="1600px" mx="auto" paddingTop={1} sx={{ flexGrow: 1 }}>
      <Grid container spacing={2}>
        <Grid item xs={12} lg={4}>
          <GeneralInfo data={general_info} />
        </Grid>
        <Grid item xs={12} lg={8}>
          <Performance data={performance_details} />
        </Grid>
      </Grid>
    </Box>
  );
};

export default OverviewTab;
