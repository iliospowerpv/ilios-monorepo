import React from 'react';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';

import { CompanyDetailsTabProps } from '../types';
import Alerts from './widgets/Alerts/Alerts';
import ActualProduction from './widgets/ActualProduction/ActualProduction';
import AlertsSummary from './widgets/AlertsSummary/AlertsSummary';
import ActualProductionVsProjected from './widgets/ProductionProjected/ProductionProjected';
import Losses from './widgets/Losses/Losses';

export const OverviewTab: React.FC<CompanyDetailsTabProps> = ({ companyDetails }) => {
  const alerts = {
    title: 'Alerts',
    data: companyDetails.alerts_section
  };

  const alertsSummary = {
    title: 'Alerts Summary',
    data: companyDetails.alerts_summary_section
  };

  return (
    <Box maxWidth="1600px" mx="auto" paddingTop={1} sx={{ flexGrow: 1 }}>
      <Grid container spacing={2} columns={20}>
        <Grid item xs={20} md={10} lg={8}>
          <ActualProduction companyId={companyDetails.id} />
        </Grid>
        <Grid item xs={20} md={10} lg={6}>
          <Alerts title={alerts.title} data={alerts.data} companyId={companyDetails.id} />
        </Grid>
        <Grid item xs={20} md={10} lg={6}>
          <AlertsSummary title={alertsSummary.title} data={alertsSummary.data} />
        </Grid>
        <Grid item xs={20} md={10} lg={12}>
          <ActualProductionVsProjected companyId={companyDetails.id} />
        </Grid>
        <Grid item xs={20} md={10} lg={8}>
          <Losses companyId={companyDetails.id} />
        </Grid>
      </Grid>
    </Box>
  );
};

export default OverviewTab;
