import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import AssessmentIcon from '@mui/icons-material/Assessment';
import type { AssetManagementSiteDetailsTabProps } from '../types';

export const Reporting: React.FC<AssetManagementSiteDetailsTabProps> = ({ siteDetails }) => {
  return (
    <Box>
      <Alert severity="info" icon={<AssessmentIcon />} sx={{ mb: 3 }}>
        Reports for {siteDetails.name} - Performance and analytics
      </Alert>
      <Typography variant="body1" color="text.secondary">
        Reporting content will be integrated from Reports module.
      </Typography>
    </Box>
  );
};

export default Reporting;
