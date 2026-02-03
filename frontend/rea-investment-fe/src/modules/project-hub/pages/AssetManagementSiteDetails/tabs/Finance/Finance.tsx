import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import type { AssetManagementSiteDetailsTabProps } from '../types';
import { useFocusHighlight } from '../../../../../../hooks/useFocusHighlight';

export const Finance: React.FC<AssetManagementSiteDetailsTabProps> = ({ siteDetails }) => {
  const { focusState } = useFocusHighlight();

  return (
    <Box>
      {focusState.notFoundMessage && (
        <Alert severity="warning" sx={{ mb: 2 }}>
          {focusState.notFoundMessage}
        </Alert>
      )}
      <Alert severity="info" icon={<AccountBalanceWalletIcon />} sx={{ mb: 3 }}>
        Finance for {siteDetails.name} - Budget, obligations, and vendor management
      </Alert>
      <Typography variant="body1" color="text.secondary">
        Finance content will be integrated from Finance module.
        {focusState.focusId && (
          <Box component="span" sx={{ display: 'block', mt: 1, fontStyle: 'italic' }}>
            Focus requested for {focusState.focusType} ID: {focusState.focusId}
          </Box>
        )}
      </Typography>
    </Box>
  );
};

export default Finance;
