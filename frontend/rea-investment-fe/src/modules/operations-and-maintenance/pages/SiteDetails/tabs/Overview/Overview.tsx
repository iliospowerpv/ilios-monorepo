import React from 'react';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';

import { SiteDetailsTabProps } from '../types';
import ActualProduction from './widgets/ActualProduction/ActualProduction';
import PastPerformance from './widgets/PastPerformance/PastPerformance';
import Devices from './widgets/Devices/Devices';
import ActualProjectedPower from './widgets/ActualProjectedPower/ActualProjectedPower';
import InvertersPerformance from './widgets/InvertersPerformance/InvertersPerformance';

export const OverviewTab: React.FC<SiteDetailsTabProps> = ({ siteDetails }) => (
  <Box maxWidth="1600px" mx="auto" paddingTop={1} marginBottom={4} sx={{ flexGrow: 1 }}>
    <Grid container spacing={2} columns={20}>
      <Grid item xs={20} md={10} lg={8}>
        <ActualProduction siteId={siteDetails.id} />
      </Grid>
      <Grid item xs={20} md={10} lg={6}>
        <PastPerformance siteId={siteDetails.id} />
      </Grid>
      <Grid item xs={20} md={10} lg={6}>
        <Devices siteId={siteDetails.id} />
      </Grid>
      <Grid item xs={20} md={10} lg={10}>
        <ActualProjectedPower siteId={siteDetails.id} />
      </Grid>
      <Grid item xs={20} md={10} lg={10}>
        <InvertersPerformance siteId={siteDetails.id} />
      </Grid>
    </Grid>
  </Box>
);

export default OverviewTab;
