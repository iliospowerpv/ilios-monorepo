import * as React from 'react';
import { useMutation, QueryClient } from '@tanstack/react-query';
import IconButton from '@mui/material/IconButton';
import Badge from '@mui/material/Badge';
import NotificationsIcon from '@mui/icons-material/Notifications';
import SettingsIcon from '@mui/icons-material/Settings';
import KeyboardArrowDownIcon from '@mui/icons-material/KeyboardArrowDown';
import Box from '@mui/material/Box';
import Divider from '@mui/material/Divider';
import Stack from '@mui/material/Stack';
import MenuItem from '@mui/material/MenuItem';
import ListItemIcon from '@mui/material/ListItemIcon';
import Logout from '@mui/icons-material/Logout';
import { Link, useNavigate } from 'react-router-dom';
import Tooltip from '@mui/material/Tooltip';

import { HeaderMenuAvatar, HeaderToolbar, Header, MenuStyled } from './PageHeader.styles';
import { Breadcrumbs } from '../Breadcrumbs/Breadcrumbs';
import { ApiClient } from '../../../api';
import { useAuth } from '../../../contexts/auth/auth';
import { useNotify } from '../../../contexts/notifications/notifications';

export const PageHeader: React.FC = () => {
  const [anchorEl, setAnchorEl] = React.useState<null | HTMLElement>(null);
  const open = Boolean(anchorEl);
  const notify = useNotify();
  const queryClient = new QueryClient();
  const navigate = useNavigate();
  const { user } = useAuth();

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

  const isDisabled = !user?.is_system_user && !user?.role?.permissions?.['Settings Page']?.view;

  return (
    <Header position="fixed">
      <Box px={t => t.spacing(3)}>
        <HeaderToolbar>
          <Breadcrumbs />
          <Stack direction="row" alignItems="center">
            <Link to="/settings">
              <Tooltip title={isDisabled ? 'You don’t have permission to view this page.' : ''}>
                <span>
                  <IconButton disabled={isDisabled} sx={{ mr: t => t.spacing(2), color: 'rgba(0, 0, 0, 0.4)' }}>
                    <SettingsIcon />
                  </IconButton>
                </span>
              </Tooltip>
            </Link>
            <IconButton sx={{ mr: t => t.spacing(2), color: 'rgba(0, 0, 0, 0.4)' }}>
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
