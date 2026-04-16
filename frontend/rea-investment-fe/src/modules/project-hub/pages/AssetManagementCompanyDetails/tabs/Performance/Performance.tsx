import React from 'react';
import Box from '@mui/material/Box';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import { useQuery } from '@tanstack/react-query';
import type { AssetManagementCompanyDetailsTabProps } from '../types';
import { ApiClient } from '../../../../../../api';
import ActualProductionVsProjected from '../../../../../operations-and-maintenance/pages/CompanyDetails/tabs/Overview/widgets/ProductionProjected/ProductionProjected';
import Losses from '../../../../../operations-and-maintenance/pages/CompanyDetails/tabs/Overview/widgets/Losses/Losses';

export const Performance: React.FC<AssetManagementCompanyDetailsTabProps> = ({ companyDetails }) => {
  const { data: chartData, isLoading, isError } = useQuery({
    queryFn: () => ApiClient.operationsAndMaintenance.companyActualVsExpectedProductionData(companyDetails.id),
    queryKey: ['companies', 'actual-vs-expected-production-data', { companyId: companyDetails.id }],
    refetchInterval: 15 * 60 * 1000
  });

  const hasTelemetryData =
    !isLoading &&
    !isError &&
    chartData?.items?.some(
      (item) => (item.actual_kw ?? 0) !== 0 || (item.expected_kw ?? 0) !== 0
    );
  const showEmptyState = !isLoading && !isError && !hasTelemetryData;

  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 2, fontWeight: 500 }}>
        Portfolio Performance
      </Typography>

      {showEmptyState && (
        <Alert severity="info" sx={{ mb: 3 }}>
          Performance charts will appear here once telemetry data is available for this portfolio's sites.
        </Alert>
      )}

      {(hasTelemetryData || isLoading || isError) && (
        <Box maxWidth="1600px" mx="auto" mb={3} sx={{ flexGrow: 1 }}>
          <Grid container spacing={2}>
            <Grid item xs={12} lg={7}>
              <ActualProductionVsProjected companyId={companyDetails.id} />
            </Grid>
            <Grid item xs={12} lg={5}>
              <Losses companyId={companyDetails.id} />
            </Grid>
          </Grid>
        </Box>
      )}
    </Box>
  );
};

export default Performance;
