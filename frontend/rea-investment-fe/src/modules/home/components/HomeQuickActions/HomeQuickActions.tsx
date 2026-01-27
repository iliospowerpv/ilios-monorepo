import React from 'react';
import { useNavigate } from 'react-router-dom';
import Box from '@mui/material/Box';
import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';
import Stack from '@mui/material/Stack';
import Divider from '@mui/material/Divider';
import AddBusinessIcon from '@mui/icons-material/AddBusiness';
import CreateNewFolderIcon from '@mui/icons-material/CreateNewFolder';
import PersonAddIcon from '@mui/icons-material/PersonAdd';
import AdminPanelSettingsIcon from '@mui/icons-material/AdminPanelSettings';

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
    <Card sx={{ height: '100%' }}>
      <CardContent>
        <Typography variant="h6" gutterBottom>
          Quick Actions
        </Typography>
        <Stack spacing={1.5}>
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
                  onClick={() => navigate('/company-admin')}
                  fullWidth
                  sx={{ justifyContent: 'flex-start' }}
                >
                  Manage Members
                </Button>
              </Box>
            </>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
};

export default HomeQuickActions;
