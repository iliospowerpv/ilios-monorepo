import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import Masonry from '@mui/lab/Masonry';
import Grid from '@mui/material/Grid';
import { useTheme } from '@mui/material';

import { DeviceDetailsTabProps } from '../types';
import { DeviceActionsPanel } from './components/DeviceActionsPanel';
import { GeneralDeviceInfoCard } from './components/GeneralDeviceInfoCard';
import ServiceDetailCard from './components/ServiceDetailCard/ServiceDetailCard';
import TechnicalDetailCard from './components/TechnicalDetailCard/TechnicalDetailCard';
import DocumentList from './components/DocumentList';

export const OverviewTab: React.FC<DeviceDetailsTabProps> = ({ deviceDetails, deviceId, siteId, companyId }) => {
  const { general_info, technical_details, service_detail, documents, telemetry_mapping } = deviceDetails;
  const theme = useTheme();
  const deviceCategory = general_info.category;

  return (
    <>
      <DeviceActionsPanel siteId={siteId} deviceId={deviceId} companyId={companyId} deviceDetails={deviceDetails} />
      <Box paddingTop={1} marginRight={-2} sx={{ flexGrow: 1 }}>
        <Grid container spacing={2}>
          <Grid item xs={12} md={12} lg={8}>
            <Masonry columns={{ xs: 1, md: 2 }} spacing={2}>
              <Paper elevation={0}>
                <GeneralDeviceInfoCard
                  siteId={siteId}
                  deviceId={deviceId}
                  deviceGeneralInfo={general_info}
                  telemetryMapping={telemetry_mapping}
                />
              </Paper>
              <Paper elevation={0}>
                <TechnicalDetailCard
                  siteId={siteId}
                  deviceId={deviceId}
                  deviceCategory={deviceCategory}
                  technicalDetailData={technical_details}
                />
              </Paper>
              <Paper elevation={0}>
                <ServiceDetailCard serviceDetailData={service_detail} siteId={siteId} deviceId={deviceId} />
              </Paper>
            </Masonry>
          </Grid>
          <Grid
            item
            xs={12}
            md={6}
            lg={4}
            sx={{
              [theme.breakpoints.up('xs')]: {
                marginLeft: 0,
                marginRight: '16px'
              },
              [theme.breakpoints.up('lg')]: {
                marginLeft: '-16px',
                marginRight: 0
              }
            }}
          >
            <Box display="flex" flexDirection="column" flexGrow={1} padding="16px" border="1px solid #0000003B">
              <Typography variant="h5" mb="16px">
                Documents
              </Typography>
              <DocumentList siteId={siteId} deviceId={deviceId} documents={documents} />
            </Box>
          </Grid>
        </Grid>
      </Box>
    </>
  );
};

export default OverviewTab;
