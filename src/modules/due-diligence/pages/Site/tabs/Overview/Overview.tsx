import React from 'react';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';

import { SiteDetailsTabProps } from '../types';
import TermsAndValuesList from './components/TermsAndValuesList/TermsAndValuesList';
import CoTerminusChecksPanel from './components/CoTerminusChecksPanel/CoTerminusChecksPanel';

const OverviewTab: React.FC<SiteDetailsTabProps> = ({ siteId, companyId }) => {
  if (!siteId || !companyId) {
    return null;
  }
  return (
    <Box sx={{ flexGrow: 1 }} data-testid="overview-tab__component">
      <Grid container spacing={2}>
        <Grid item xs={12} md={8}>
          <TermsAndValuesList siteId={Number.parseInt(siteId)} companyId={Number.parseInt(companyId)} />
        </Grid>
        <Grid item xs={12} md={4}>
          <CoTerminusChecksPanel siteId={Number.parseInt(siteId)} />
        </Grid>
      </Grid>
    </Box>
  );
};

export default OverviewTab;
