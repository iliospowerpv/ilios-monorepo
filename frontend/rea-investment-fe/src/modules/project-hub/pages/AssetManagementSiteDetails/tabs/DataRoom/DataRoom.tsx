import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import FolderIcon from '@mui/icons-material/Folder';
import type { AssetManagementSiteDetailsTabProps } from '../types';

export const DataRoom: React.FC<AssetManagementSiteDetailsTabProps> = ({ siteDetails }) => {
  return (
    <Box>
      <Alert severity="info" icon={<FolderIcon />} sx={{ mb: 3 }}>
        Data Room for {siteDetails.name} - Documents and due diligence materials
      </Alert>
      <Typography variant="body1" color="text.secondary">
        Data room content will be integrated from Due Diligence module.
      </Typography>
    </Box>
  );
};

export default DataRoom;
