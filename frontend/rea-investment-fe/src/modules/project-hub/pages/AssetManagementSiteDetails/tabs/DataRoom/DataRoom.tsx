import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import FolderIcon from '@mui/icons-material/Folder';
import type { AssetManagementSiteDetailsTabProps } from '../types';
import { useFocusHighlight } from '../../../../../../hooks/useFocusHighlight';

export const DataRoom: React.FC<AssetManagementSiteDetailsTabProps> = ({ siteDetails }) => {
  const { focusState } = useFocusHighlight();

  return (
    <Box>
      {focusState.notFoundMessage && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {focusState.notFoundMessage}
        </Alert>
      )}
      <Alert severity="info" icon={<FolderIcon />} sx={{ mb: 3 }}>
        Data Room for {siteDetails.name} - Documents and due diligence materials
      </Alert>
      <Typography variant="body1" color="text.secondary">
        Data room content will be integrated from Due Diligence module.
        {focusState.focusId && (
          <Box component="span" sx={{ display: 'block', mt: 1, fontStyle: 'italic' }}>
            Focus requested for {focusState.focusType} ID: {focusState.focusId}
          </Box>
        )}
      </Typography>
    </Box>
  );
};

export default DataRoom;
