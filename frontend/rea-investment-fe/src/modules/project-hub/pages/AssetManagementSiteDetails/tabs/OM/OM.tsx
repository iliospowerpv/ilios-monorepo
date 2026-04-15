import React from 'react';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import Divider from '@mui/material/Divider';
import Alert from '@mui/material/Alert';
import { useQuery } from '@tanstack/react-query';
import Devices from '../Devices/Devices';
import Telemetry from '../Telemetry/Telemetry';
import type { AssetManagementSiteDetailsTabProps } from '../types';
import { useFocusHighlight } from '../../../../../../hooks/useFocusHighlight';
import { ApiClient } from '../../../../../../api';
import ActualProduction from '../../../../../operations-and-maintenance/pages/SiteDetails/tabs/Overview/widgets/ActualProduction/ActualProduction';
import PastPerformance from '../../../../../operations-and-maintenance/pages/SiteDetails/tabs/Overview/widgets/PastPerformance/PastPerformance';
import ActualProjectedPower from '../../../../../operations-and-maintenance/pages/SiteDetails/tabs/Overview/widgets/ActualProjectedPower/ActualProjectedPower';
import InvertersPerformance from '../../../../../operations-and-maintenance/pages/SiteDetails/tabs/Overview/widgets/InvertersPerformance/InvertersPerformance';
import DevicesOverview from '../../../../../operations-and-maintenance/pages/SiteDetails/tabs/Overview/widgets/Devices/Devices';

export const OM: React.FC<AssetManagementSiteDetailsTabProps> = ({ siteDetails }) => {
  const { focusState } = useFocusHighlight();

  const { data: readiness } = useQuery({
    queryKey: ['telemetry-readiness', siteDetails.id],
    queryFn: () => ApiClient.connections.getTelemetryReadiness(siteDetails.id),
    enabled: !!siteDetails.id
  });

  const showPerformanceDashboard = readiness?.is_connected && readiness?.is_site_mapped && readiness?.is_data_flowing;

  return (
    <Box>
      {focusState.notFoundMessage && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {focusState.notFoundMessage}
        </Alert>
      )}
      <Typography variant="h5" sx={{ mb: 2, fontWeight: 500 }}>
        Operations & Maintenance
      </Typography>

      {readiness && !showPerformanceDashboard && (
        <Alert severity="info" sx={{ mb: 3 }}>
          Performance charts will appear here once telemetry is connected and data is flowing.
        </Alert>
      )}

      {showPerformanceDashboard && (
        <>
          <Typography variant="h6" sx={{ mb: 2 }}>
            Performance Dashboard
          </Typography>
          <Box maxWidth="1600px" mx="auto" mb={3} sx={{ flexGrow: 1 }}>
            <Grid container spacing={2} columns={20}>
              <Grid item xs={20} md={10} lg={8}>
                <ActualProduction siteId={siteDetails.id} />
              </Grid>
              <Grid item xs={20} md={10} lg={6}>
                <PastPerformance siteId={siteDetails.id} />
              </Grid>
              <Grid item xs={20} md={10} lg={6}>
                <DevicesOverview siteId={siteDetails.id} />
              </Grid>
              <Grid item xs={20} md={10} lg={10}>
                <ActualProjectedPower siteId={siteDetails.id} />
              </Grid>
              <Grid item xs={20} md={10} lg={10}>
                <InvertersPerformance siteId={siteDetails.id} />
              </Grid>
            </Grid>
          </Box>
          <Divider sx={{ my: 4 }} />
        </>
      )}

      <Telemetry siteDetails={siteDetails} />
      <Divider sx={{ my: 4 }} />
      <Devices siteDetails={siteDetails} />
      {focusState.focusId && (
        <Typography variant="body2" sx={{ mt: 2, fontStyle: 'italic', color: 'text.secondary' }}>
          Focus requested for {focusState.focusType} ID: {focusState.focusId}
        </Typography>
      )}
    </Box>
  );
};

export default OM;
