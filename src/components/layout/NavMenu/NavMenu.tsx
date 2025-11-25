import * as React from 'react';
import { Instance } from '@popperjs/core';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Tooltip from '@mui/material/Tooltip';
import Fade from '@mui/material/Fade';
import FactCheckIcon from '@mui/icons-material/FactCheck';
import WhatshotIcon from '@mui/icons-material/Whatshot';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import AccountBalanceIcon from '@mui/icons-material/AccountBalance';
import DashboardIcon from '@mui/icons-material/Dashboard';
import AssessmentIcon from '@mui/icons-material/Assessment';
import { NavMenuButtonContainer } from './NavMenu.styles';
import { useNavigate, useMatches } from 'react-router-dom';
import { RouteHandle } from '../../../handles';
import { useAuth } from '../../../contexts/auth/auth';
import { useTheme } from '@mui/material/styles';

interface AnchorElTooltip extends React.PropsWithChildren {
  anchor: React.RefObject<HTMLDivElement>;
  title: string;
}

const AnchorElTooltip: React.FC<AnchorElTooltip> = ({ children, anchor, title }) => {
  const elementRef = React.useRef<HTMLDivElement>(null);
  const popperRef = React.useRef<Instance>(null);
  const { color } = useTheme();

  const handleMouseMove = () => {
    if (popperRef.current != null) {
      popperRef.current.update();
    }
  };

  return (
    <Tooltip
      title={title}
      placement="right"
      arrow
      slotProps={{
        tooltip: { sx: { bgcolor: color.black, padding: '8px 12px', fontSize: '0.8rem', fontWeight: 500 } },
        arrow: { sx: { color: color.black } }
      }}
      TransitionComponent={Fade}
      TransitionProps={{ timeout: { enter: 700 } }}
      PopperProps={{
        popperRef,
        anchorEl: {
          getBoundingClientRect: () =>
            new DOMRect(
              0,
              elementRef.current ? elementRef.current.getBoundingClientRect().top : 0,
              anchor.current ? anchor.current.getBoundingClientRect().width : 0,
              elementRef.current ? elementRef.current.getBoundingClientRect().height : 0
            )
        }
      }}
    >
      <Box ref={elementRef} onMouseMove={handleMouseMove}>
        {children}
      </Box>
    </Tooltip>
  );
};

const menuItems: [string, React.ReactNode, string, string, boolean][] = [
  ['my-portfolio', <DashboardIcon key="my-portfolio" />, 'My Portfolio', '/my-portfolio', false],
  ['dashboard', <DashboardIcon key="dashboard" />, 'Dashboard', '/dashboard', false],
  [
    'operations-and-maintenance',
    <WhatshotIcon key="operations-and-maintenance" />,
    'O&M',
    '/operations-and-maintenance',
    false
  ],
  ['due-diligence', <FactCheckIcon key="due-diligence" />, 'Diligence', '/due-diligence', false],
  ['finance', <AccountBalanceWalletIcon key="finance" />, 'Finance', '/', true],
  ['asset-management', <AccountBalanceIcon key="asset-management" />, 'Asset Management', '/asset-management', false],
  ['reports', <AssessmentIcon key="reports" />, 'Reports', '/reports', false]
];

interface MenuItemProps {
  icon: React.ReactNode;
  title: string;
  disabled?: boolean;
  active?: boolean;
  onClick?: () => void;
}

const MenuItem: React.FC<MenuItemProps> = ({ icon, title, active, disabled, onClick }) => (
  <NavMenuButtonContainer className={active ? 'active' : undefined} disabled={disabled} onClick={onClick}>
    <Grid container columns={15} alignItems="center">
      <Grid item xs={4} display="flex" justifyContent="center" alignItems="center">
        {icon}
      </Grid>
      <Grid item xs={11} display="flex" justifyContent="flex-start" alignItems="center">
        <Typography noWrap fontSize="16px" fontWeight="400" letterSpacing="0.15px">
          {title}
        </Typography>
      </Grid>
    </Grid>
  </NavMenuButtonContainer>
);

interface NavMenuProps {
  containerRef: React.RefObject<HTMLDivElement>;
  isMenuOpen: boolean;
  closeMenu: () => void;
}

export const NavMenu: React.FC<NavMenuProps> = ({ containerRef, isMenuOpen, closeMenu }) => {
  const navigate = useNavigate();
  const matches = useMatches();
  const { user } = useAuth();

  const currentModuleId =
    matches
      .map(({ handle }) => (handle instanceof RouteHandle ? handle.getModuleId() : null))
      .find(el => el !== null) || '';

  const menuItemClickHandler = (navigateTo: string) => () => {
    navigate(navigateTo);
    setTimeout(closeMenu, 100);
  };

  const disableModule = (disabled: boolean, title: string) => {
    if (user?.is_system_user) return disabled;
    switch (title) {
      case 'O&M':
        return !user?.role?.permissions?.['O&M (Production Monitoring)']?.view;
      case 'Diligence':
        return !user?.role?.permissions?.['Diligence']?.view;
      case 'Asset Management':
        return !user?.role?.permissions?.['Asset Management']?.view;
      case 'Reports':
        return !user?.role?.permissions?.['Reports']?.view;
      default:
        return disabled;
    }
  };

  const showModule = (moduleKey: string): boolean => {
    const hasMyPortfolioAccess = user?.role?.permissions?.['Investor Dashboard']?.view;
    if (moduleKey === 'dashboard') return !hasMyPortfolioAccess;
    if (moduleKey === 'my-portfolio') return !!hasMyPortfolioAccess;
    return true;
  };

  return (
    <Stack direction="column" width={t => t.spacing(30)}>
      {menuItems.map(
        ([key, icon, title, route, disabled]) =>
          showModule(key) &&
          (isMenuOpen ? (
            <AnchorElTooltip
              title={
                disabled
                  ? `${title} (coming soon)`
                  : disableModule(disabled, title)
                    ? 'You don’t have permission to view this page.'
                    : ''
              }
              key={key}
              anchor={containerRef}
            >
              <MenuItem
                key={title}
                title={title}
                icon={icon}
                onClick={menuItemClickHandler(route)}
                active={key === currentModuleId}
                disabled={disableModule(disabled, title)}
              />
            </AnchorElTooltip>
          ) : (
            <AnchorElTooltip
              title={
                disabled
                  ? `${title} (coming soon)`
                  : disableModule(disabled, title)
                    ? 'You don’t have permission to view this page.'
                    : title
              }
              key={key}
              anchor={containerRef}
            >
              <MenuItem
                title={title}
                icon={icon}
                onClick={menuItemClickHandler(route)}
                active={key === currentModuleId}
                disabled={disableModule(disabled, title)}
              />
            </AnchorElTooltip>
          ))
      )}
    </Stack>
  );
};
