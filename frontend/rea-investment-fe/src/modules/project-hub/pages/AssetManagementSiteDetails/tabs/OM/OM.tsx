import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Divider from '@mui/material/Divider';
import Devices from '../Devices/Devices';
import Telemetry from '../Telemetry/Telemetry';
import type { AssetManagementSiteDetailsTabProps } from '../types';

export const OM: React.FC<AssetManagementSiteDetailsTabProps> = ({ siteDetails }) => {
  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 2, fontWeight: 500 }}>
        Operations & Maintenance
      </Typography>
      <Telemetry siteDetails={siteDetails} />
      <Divider sx={{ my: 4 }} />
      <Devices siteDetails={siteDetails} />
    </Box>
  );
};

export default OM;
