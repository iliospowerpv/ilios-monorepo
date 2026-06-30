import * as React from 'react';
import { useMutation, QueryClient } from '@tanstack/react-query';
import IconButton from '@mui/material/IconButton';
import Badge from '@mui/material/Badge';
import NotificationsIcon from '@mui/icons-material/Notifications';
import SettingsIcon from '@mui/icons-material/Settings';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import LightModeIcon from '@mui/icons-material/LightMode';
import DarkModeIcon from '@mui/icons-material/DarkMode';
import Box from '@mui/material/Box';
import Divider from '@mui/material/Divider';
import Stack from '@mui/material/Stack';
import MenuItem from '@mui/material/MenuItem';
import ListItemIcon from '@mui/material/ListItemIcon';
import Logout from '@mui/icons-material/Logout';
import PersonOutlineIcon from '@mui/icons-material/PersonOutline';
import SecurityOutlinedIcon from '@mui/icons-material/SecurityOutlined';
import HelpOutlineIcon from '@mui/icons-material/HelpOutline';
import PeopleOutlineIcon from '@mui/icons-material/PeopleOutline';
import SmartToyOutlinedIcon from '@mui/icons-material/SmartToyOutlined';
import { Link, useNavigate } from 'react-router-dom';
import Tooltip from '@mui/material/Tooltip';

import { HeaderMenuAvatar, HeaderToolbar, Header, MenuStyled } from './PageHeader.styles';
import { Breadcrumbs } from '../Breadcrumbs/Breadcrumbs';
import { EntityContextNav } from '../EntityContextNav/EntityContextNav';
import { ApiClient } from '../../../api';
import { useAuth } from '../../../contexts/auth/auth';
import { useNotify } from '../../../contexts/notifications/notifications';
import { useThemeMode } from '../../../contexts/theme/theme';
import { useSidebar } from '../../../contexts/sidebar';
import { useAssistantLauncher } from '../../../contexts/assistantLauncher';

export const PageHeader: React.FC = () => {
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);
  const notify = useNotify();
  const queryClient = new QueryClient();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { mode, toggleTheme } = useThemeMode();
  const { isOpen: sidebarOpen } = useSidebar();
  // Navigational entry to the single, already-mounted read-only AI Assistant drawer. Only shown when
  // the assistant is actually reachable; clicking only opens the drawer (never an action).
  const { available: assistantAvailable, requestOpen: openAssistant } = useAssistantLauncher();

  if (!user) {
    throw new Error('PageHeader component requires user authentication');
  }

  const { mutateAsync } = useMutation({
    mutationFn: ApiClient.user.logout
  });

  const handleClick = (event: React.MouseEvent<HTMLButtonElement>) => {
    setAnchorEl(event.currentTarget);
  };

  const handleClose = () => {
    setAnchorEl(null);
  };

  const onLogout = async () => {
    try {
      await mutateAsync();
      handleClose();
      ApiClient._tokenManager.revokeAuthToken();
      queryClient.removeQueries({ queryKey: ['user'] });
      navigate('/login');
    } catch (e: any) {
      notify(e?.response?.data?.message || 'Something went wrong ...');
    }
  };

  // System Settings is superuser-only. Non-superusers see no gear at all.
  const isSuperuser = Boolean(user?.is_system_user || user?.is_global_admin);

  return (
    <Header position="fixed" sidebarOpen={sidebarOpen}>
      <Box px={t => t.spacing(3)}>
        <HeaderToolbar>
          <Stack direction="row" alignItems="center" spacing={2} sx={{ flexGrow: 1 }}>
            <EntityContextNav />
            <Breadcrumbs />
          </Stack>
          <Stack direction="row" alignItems="center">
            {assistantAvailable && (
              <Tooltip title="Ask the AI Assistant">
                <IconButton
                  onClick={() => openAssistant('topbar')}
                  aria-label="Open AI Assistant"
                  sx={{ mr: t => t.spacing(2), color: 'text.secondary' }}
                >
                  <SmartToyOutlinedIcon />
                </IconButton>
              </Tooltip>
            )}
            <Tooltip title={mode === 'light' ? 'Switch to dark mode' : 'Switch to light mode'}>
              <IconButton onClick={toggleTheme} sx={{ mr: t => t.spacing(2), color: 'text.secondary' }}>
                {mode === 'light' ? <DarkModeIcon /> : <LightModeIcon />}
              </IconButton>
            </Tooltip>
            {isSuperuser && (
              <Link to="/settings">
                <Tooltip title="System Settings">
                  <IconButton sx={{ mr: t => t.spacing(2), color: 'text.secondary' }}>
                    <SettingsIcon />
                  </IconButton>
                </Tooltip>
              </Link>
            )}
            <IconButton sx={{ mr: t => t.spacing(2), color: 'text.secondary' }}>
              <Badge color="primary">
                <NotificationsIcon />
              </Badge>
            </IconButton>
            <HeaderMenuAvatar alt={user.first_name + ' ' + user.last_name}>
              {user.first_name.charAt(0) + user.last_name.charAt(0)}
            </HeaderMenuAvatar>
            <IconButton color="inherit" onClick={handleClick}>
              <KeyboardArrowDownIcon />
            </IconButton>
            <MenuStyled id="basic-menu" anchorEl={anchorEl} open={open} onClose={handleClose}>
              <MenuItem
                onClick={() => {
                  handleClose();
                  navigate('/account');
                }}
              >
                <ListItemIcon>
                  <PersonOutlineIcon fontSize="small" />
                </ListItemIcon>
                Account Settings
              </MenuItem>
              <MenuItem
                onClick={() => {
                  handleClose();
                  navigate('/security');
                }}
              >
                <ListItemIcon>
                  <SecurityOutlinedIcon fontSize="small" />
                </ListItemIcon>
                Security
              </MenuItem>
              {assistantAvailable && (
                <MenuItem
                  onClick={() => {
                    handleClose();
                    openAssistant('help_menu');
                  }}
                >
                  <ListItemIcon>
                    <SmartToyOutlinedIcon fontSize="small" />
                  </ListItemIcon>
                  Ask the AI Assistant
                </MenuItem>
              )}
              <MenuItem
                onClick={() => {
                  handleClose();
                  navigate('/help');
                }}
              >
                <ListItemIcon>
                  <HelpOutlineIcon fontSize="small" />
                </ListItemIcon>
                Help & Resources
              </MenuItem>
              <Divider />
              <MenuItem
                onClick={() => {
                  handleClose();
                  navigate('/portfolio-admin');
                }}
              >
                <ListItemIcon>
                  <PeopleOutlineIcon fontSize="small" />
                </ListItemIcon>
                Portfolio Admin
              </MenuItem>
              <Divider />
              <MenuItem onClick={onLogout}>
                <ListItemIcon>
                  <Logout fontSize="small" />
                </ListItemIcon>
                Logout
              </MenuItem>
            </MenuStyled>
          </Stack>
        </HeaderToolbar>
        <Divider />
      </Box>
    </Header>
  );
};
