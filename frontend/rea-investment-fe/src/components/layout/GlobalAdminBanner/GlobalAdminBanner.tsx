import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';

import { useAuth } from '../../../contexts/auth/auth';

/**
 * Persistent header banner shown to users with the platform-wide
 * Global Admin privilege. Reminds the user that their session bypasses
 * per-company access checks and that all actions are audited.
 *
 * Hidden for the internal system_user account (which is automation).
 */
export const GlobalAdminBanner: React.FC = () => {
  const { user } = useAuth();

  if (!user?.is_global_admin || user?.is_system_user) {
    return null;
  }

  return (
    <Box
      role="status"
      aria-label="Global admin session"
      sx={{
        position: 'fixed',
        top: 0,
        left: 0,
        right: 0,
        zIndex: theme => theme.zIndex.appBar + 2,
        bgcolor: '#FFF4CE',
        borderBottom: '1px solid #E0B400',
        color: '#5C4400',
        px: 2,
        py: 0.5,
        display: 'flex',
        alignItems: 'center',
        gap: 1
      }}
    >
      <WarningAmberIcon fontSize="small" sx={{ color: '#B45309' }} />
      <Typography variant="body2" sx={{ fontWeight: 600 }}>
        Global Admin session
      </Typography>
      <Typography variant="body2">
        — you have platform-wide access. All actions are audited and your session expires after 15 minutes of
        inactivity.
      </Typography>
    </Box>
  );
};

export default GlobalAdminBanner;
