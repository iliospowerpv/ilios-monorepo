import React from 'react';
import { useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
import Divider from '@mui/material/Divider';
import AddBusinessIcon from '@mui/icons-material/AddBusiness';
import CreateNewFolderIcon from '@mui/icons-material/CreateNewFolder';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import AdminPanelSettingsIcon from '@mui/icons-material/AdminPanelSettings';
import RocketLaunchIcon from '@mui/icons-material/RocketLaunch';

import { useAuth } from '../../../../contexts/auth/auth';
import { useEntityContext } from '../../../../contexts/entityContext/entityContext';

interface HomeQuickActionsProps {
  onCreateCompany: () => void;
  onCreateProject: () => void;
  onInviteUser: () => void;
}

export const HomeQuickActions: React.FC<HomeQuickActionsProps> = ({
  onCreateCompany,
  onCreateProject,
  onInviteUser
}) => {
  const navigate = useNavigate();
  const { user } = useAuth();
  const { currentCompany } = useEntityContext();

  const isSystemUser = user?.is_system_user ?? false;
  const canCreateCompany = isSystemUser;
  const hasCompanyContext = !!currentCompany;

  return (
    <Box sx={{ height: '100%', minHeight: 0, overflow: 'auto', p: 2 }}>
      <Stack spacing={1.5}>
        <Button
          variant="contained"
          color="primary"
          startIcon={<RocketLaunchIcon />}
          onClick={() => navigate('/onboarding')}
          fullWidth
          size="large"
          sx={{ mb: 1 }}
        >
          Set Up a New Project
        </Button>

        <Divider sx={{ my: 0.5 }} />

        {canCreateCompany && (
          <Button
            variant="outlined"
            startIcon={<AddBusinessIcon />}
            onClick={onCreateCompany}
            fullWidth
            sx={{ justifyContent: 'flex-start' }}
          >
            Create Company
          </Button>
        )}

        <Button
          variant="outlined"
          startIcon={<CreateNewFolderIcon />}
          onClick={onCreateProject}
          fullWidth
          sx={{ justifyContent: 'flex-start' }}
        >
          Create Project
        </Button>

        <Button
          variant="outlined"
          startIcon={<PersonAddIcon />}
          onClick={onInviteUser}
          fullWidth
          sx={{ justifyContent: 'flex-start' }}
        >
          Invite User
        </Button>

        {hasCompanyContext && (
          <>
            <Divider sx={{ my: 1 }} />
            <Box>
              <Typography variant="caption" color="text.secondary" sx={{ mb: 1, display: 'block' }}>
                Current Company
              </Typography>
              <Button
                variant="text"
                startIcon={<AdminPanelSettingsIcon />}
                onClick={() => navigate('/portfolio-admin')}
                fullWidth
                sx={{ justifyContent: 'flex-start' }}
              >
                Manage Members
              </Button>
            </Box>
          </>
        )}
      </Stack>
    </Box>
  );
};

export default HomeQuickActions;
