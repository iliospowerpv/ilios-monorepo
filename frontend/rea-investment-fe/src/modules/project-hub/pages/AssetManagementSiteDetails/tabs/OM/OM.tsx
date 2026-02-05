import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Divider from '@mui/material/Divider';
import Alert from '@mui/material/Alert';
import Devices from '../Devices/Devices';
import Telemetry from '../Telemetry/Telemetry';
import type { AssetManagementSiteDetailsTabProps } from '../types';
import { useFocusHighlight } from '../../../../../../hooks/useFocusHighlight';

export const OM: React.FC<AssetManagementSiteDetailsTabProps> = ({ siteDetails }) => {
  const { focusState } = useFocusHighlight();

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
