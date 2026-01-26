import React from 'react';
import { useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import IconButton from '@mui/material/IconButton';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import Alert from '@mui/material/Alert';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import Stack from '@mui/material/Stack';
import Chip from '@mui/material/Chip';
import LockOutlinedIcon from '@mui/icons-material/LockOutlined';
import PhonelinkLockIcon from '@mui/icons-material/PhonelinkLock';
import DevicesIcon from '@mui/icons-material/Devices';
import HistoryIcon from '@mui/icons-material/History';

interface SecuritySectionProps {
  title: string;
  description: string;
  icon: React.ReactNode;
}

const SecuritySection: React.FC<SecuritySectionProps> = ({ title, description, icon }) => (
  <Paper
    variant="outlined"
    sx={{
      p: 3,
      backgroundColor: 'action.hover',
      opacity: 0.7
    }}
  >
    <Stack direction="row" alignItems="flex-start" spacing={2}>
      <Box
        sx={{
          p: 1,
          borderRadius: 1,
          backgroundColor: 'background.paper',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center'
        }}
      >
        {icon}
      </Box>
      <Box sx={{ flex: 1 }}>
        <Stack direction="row" alignItems="center" spacing={1}>
          <Typography variant="subtitle1" fontWeight={600}>
            {title}
          </Typography>
          <Chip label="Coming Soon" size="small" color="default" />
        </Stack>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          {description}
        </Typography>
      </Box>
    </Stack>
  </Paper>
);

const SecuritySettings: React.FC = () => {
  const navigate = useNavigate();

  return (
    <Box sx={{ p: 4, maxWidth: 900, mx: 'auto' }}>
      <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 3 }}>
        <IconButton onClick={() => navigate(-1)} size="small">
          <ArrowBackIcon />
        </IconButton>
        <Typography variant="h4" fontWeight={600}>
          Security
        </Typography>
      </Stack>

      <Alert severity="info" icon={<InfoOutlinedIcon />} sx={{ mb: 4 }}>
        Security controls are managed centrally during this phase of the platform.
      </Alert>

      <Stack spacing={2}>
        <SecuritySection
          title="Password Management"
          description="Change your password or set up password recovery options"
          icon={<LockOutlinedIcon color="action" />}
        />
        <SecuritySection
          title="Multi-Factor Authentication"
          description="Add an extra layer of security with two-factor authentication"
          icon={<PhonelinkLockIcon color="action" />}
        />
        <SecuritySection
          title="Active Sessions"
          description="View and manage devices where you're currently logged in"
          icon={<DevicesIcon color="action" />}
        />
        <SecuritySection
          title="Audit Activity"
          description="Review your recent account activity and security events"
          icon={<HistoryIcon color="action" />}
        />
      </Stack>
    </Box>
  );
};

export default SecuritySettings;
