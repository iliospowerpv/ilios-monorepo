import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import type { AssetManagementSiteDetailsTabProps } from '../types';

export const Finance: React.FC<AssetManagementSiteDetailsTabProps> = ({ siteDetails }) => {
  return (
    <Box>
      <Alert severity="info" icon={<AccountBalanceWalletIcon />} sx={{ mb: 3 }}>
        Finance for {siteDetails.name} - Budget, obligations, and vendor management
      </Alert>
      <Typography variant="body1" color="text.secondary">
        Finance content will be integrated from Finance module.
      </Typography>
    </Box>
  );
};

export default Finance;
