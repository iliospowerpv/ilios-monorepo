import React from 'react';
import { useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Paper from '@mui/material/Paper';
import Divider from '@mui/material/Divider';
import IconButton from '@mui/material/IconButton';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import Alert from '@mui/material/Alert';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import Stack from '@mui/material/Stack';
import Chip from '@mui/material/Chip';
import { useAuth } from '../../contexts/auth/auth';

const ComingSoonSection: React.FC<{ title: string; description?: string }> = ({ title, description }) => (
  <Paper
    variant="outlined"
    sx={{
      p: 3,
      backgroundColor: 'action.hover',
      opacity: 0.7
    }}
  >
    <Stack direction="row" alignItems="center" spacing={1}>
      <Typography variant="subtitle1" fontWeight={600}>
        {title}
      </Typography>
      <Chip label="Coming Soon" size="small" color="default" />
    </Stack>
    {description && (
      <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
        {description}
      </Typography>
    )}
  </Paper>
);

const AccountSettings: React.FC = () => {
  const navigate = useNavigate();
  const { user } = useAuth();

  const userRoles = user?.role?.name ? [user.role.name] : [];

  return (
    <Box sx={{ p: 4, maxWidth: 900, mx: 'auto' }}>
      <Stack direction="row" alignItems="center" spacing={2} sx={{ mb: 3 }}>
        <IconButton onClick={() => navigate(-1)} size="small">
          <ArrowBackIcon />
        </IconButton>
        <Typography variant="h4" fontWeight={600}>
          Account Settings
        </Typography>
      </Stack>

      <Alert severity="info" icon={<InfoOutlinedIcon />} sx={{ mb: 4 }}>
        Account management features will be enabled in a future release.
      </Alert>

      <Paper elevation={0} sx={{ p: 3, mb: 4, border: 1, borderColor: 'divider' }}>
        <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>
          Your Information
        </Typography>
        <Divider sx={{ mb: 2 }} />

        <Stack spacing={2}>
          <Box>
            <Typography variant="body2" color="text.secondary">
              Name
            </Typography>
            <Typography variant="body1" fontWeight={500}>
              {user?.first_name} {user?.last_name}
            </Typography>
          </Box>

          <Box>
            <Typography variant="body2" color="text.secondary">
              Email
            </Typography>
            <Typography variant="body1" fontWeight={500}>
              {user?.email}
            </Typography>
          </Box>

          <Box>
            <Typography variant="body2" color="text.secondary">
              Role(s)
            </Typography>
            <Stack direction="row" spacing={1} sx={{ mt: 0.5 }}>
              {userRoles.length > 0 ? (
                userRoles.map(role => <Chip key={role} label={role} size="small" color="primary" variant="outlined" />)
              ) : (
                <Typography variant="body2" color="text.secondary">
                  No roles assigned
                </Typography>
              )}
            </Stack>
          </Box>

          <Box>
            <Typography variant="body2" color="text.secondary">
              Company
            </Typography>
            <Typography variant="body1" fontWeight={500}>
              {user?.parent_company_id ? `Company ID: ${user.parent_company_id}` : 'No company assigned'}
            </Typography>
          </Box>
        </Stack>
      </Paper>

      <Typography variant="h6" fontWeight={600} sx={{ mb: 2 }}>
        Future Features
      </Typography>

      <Stack spacing={2}>
        <ComingSoonSection
          title="Profile Information"
          description="Edit your name, contact details, and profile photo"
        />
        <ComingSoonSection
          title="Notification Preferences"
          description="Manage email and in-app notification settings"
        />
        <ComingSoonSection title="Timezone & Locale" description="Set your preferred timezone and language" />
        <ComingSoonSection title="Account Deactivation" description="Request to deactivate your account" />
      </Stack>
    </Box>
  );
};

export default AccountSettings;
