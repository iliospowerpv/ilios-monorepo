import * as React from 'react';
import { Instance } from '@popperjs/core';
import Grid from '@mui/material/Grid';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import Tooltip from '@mui/material/Tooltip';
import Fade from '@mui/material/Fade';
import WhatshotIcon from '@mui/icons-material/Whatshot';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import AccountBalanceIcon from '@mui/icons-material/AccountBalance';
import AssessmentIcon from '@mui/icons-material/Assessment';
import TrendingUpIcon from '@mui/icons-material/TrendingUp';
import HomeIcon from '@mui/icons-material/Home';
import AdminPanelSettingsIcon from '@mui/icons-material/AdminPanelSettings';
import FolderIcon from '@mui/icons-material/Folder';
import AssignmentTurnedInIcon from '@mui/icons-material/AssignmentTurnedIn';
import { NavMenuButtonContainer } from './NavMenu.styles';
import { useNavigate, useMatches, useParams } from 'react-router-dom';
import { RouteHandle } from '../../../handles';
import { useAuth } from '../../../contexts/auth/auth';
import { useTheme } from '@mui/material/styles';
import { ProjectPicker, ProjectHubTab } from '../../common/ProjectPicker';
import { useEntityContext } from '../../../contexts/entityContext';

interface AnchorElTooltipProps extends React.PropsWithChildren {
  anchor: React.RefObject<HTMLDivElement>;
  title: string;
}

const AnchorElTooltip: React.FC<AnchorElTooltipProps> = ({ children, anchor, title }) => {
  const elementRef = React.useRef<HTMLDivElement>(null);
  const popperRef = React.useRef<Instance>(null);
  const theme = useTheme();

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
        tooltip: {
          sx: {
            bgcolor: '#FFFFFF',
            color: theme.custom.accent.main,
            padding: '8px 12px',
            fontSize: '0.8rem',
            fontWeight: 500,
            boxShadow: '0px 2px 8px rgba(0,0,0,0.15)'
          }
        },
        arrow: { sx: { color: '#FFFFFF' } }
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

interface MenuItemConfig {
  key: string;
  icon: React.ReactNode;
  title: string;
  route: string;
  disabled: boolean;
  requiresProject: boolean;
  projectHubTab?: ProjectHubTab;
}

const menuItems: MenuItemConfig[] = [
  {
    key: 'home',
    icon: <HomeIcon key="home" />,
    title: 'Home',
    route: '/home',
    disabled: false,
    requiresProject: false
  },
  {
    key: 'acquisitions',
    icon: <TrendingUpIcon key="acquisitions" />,
    title: 'Acquisitions',
    route: '/acquisitions',
    disabled: false,
    requiresProject: false
  },
  {
    key: 'project-hub',
    icon: <AccountBalanceIcon key="project-hub" />,
    title: 'Project Hub',
    route: '/project-hub',
    disabled: false,
    requiresProject: true,
    projectHubTab: 'overview'
  },
  {
    key: 'data-room',
    icon: <FolderIcon key="data-room" />,
    title: 'Data Room',
    route: '/project-hub',
    disabled: false,
    requiresProject: true,
    projectHubTab: 'data-room'
  },
  {
    key: 'operations-and-maintenance',
    icon: <WhatshotIcon key="operations-and-maintenance" />,
    title: 'O&M',
    route: '/project-hub',
    disabled: false,
    requiresProject: true,
    projectHubTab: 'om'
  },
  {
    key: 'finance',
    icon: <AccountBalanceWalletIcon key="finance" />,
    title: 'Finance',
    route: '/finance',
    disabled: false,
    requiresProject: false
  },
  {
    key: 'tasks',
    icon: <AssignmentTurnedInIcon key="tasks" />,
    title: 'Tasks',
    route: '/project-hub',
    disabled: false,
    requiresProject: true,
    projectHubTab: 'tasks'
  },
  {
    key: 'reports',
    icon: <AssessmentIcon key="reports" />,
    title: 'Reports',
    route: '/reports',
    disabled: false,
    requiresProject: false
  },
  {
    key: 'portfolio-admin',
    icon: <AdminPanelSettingsIcon key="portfolio-admin" />,
    title: 'Portfolio Admin',
    route: '/portfolio-admin',
    disabled: false,
    requiresProject: false
  }
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
}

export const NavMenu: React.FC<NavMenuProps> = ({ containerRef, isMenuOpen }) => {
  const navigate = useNavigate();
  const matches = useMatches();
  const { user } = useAuth();
  const params = useParams<{ siteId?: string }>();
  const { currentProject } = useEntityContext();
  const [pickerOpen, setPickerOpen] = React.useState(false);
  const [pendingTab, setPendingTab] = React.useState<ProjectHubTab | null>(null);

  // Get project from route params or entity context (persisted selection)
  const currentProjectId = params.siteId ? parseInt(params.siteId, 10) : currentProject?.id ?? null;

  const navigateToProjectHub = React.useCallback(
    (projectId: number, tab: ProjectHubTab = 'overview') => {
      const tabPath = tab === 'overview' ? '' : `/${tab}`;
      navigate(`/project-hub/projects/${projectId}${tabPath}`);
    },
    [navigate]
  );

  const currentModuleId =
    matches
      .map(({ handle }) => (handle instanceof RouteHandle ? handle.getModuleId() : null))
      .find(el => el !== null) || '';

  const handleMenuItemClick = (item: MenuItemConfig) => () => {
    if (item.requiresProject && item.projectHubTab) {
      if (currentProjectId) {
        navigateToProjectHub(currentProjectId, item.projectHubTab);
      } else {
        setPendingTab(item.projectHubTab);
        setPickerOpen(true);
      }
    } else {
      navigate(item.route);
    }
  };

  const handleProjectSelect = (project: { id: number; name: string }) => {
    if (pendingTab) {
      navigateToProjectHub(project.id, pendingTab);
    }
    setPendingTab(null);
  };

  const disableModule = (disabled: boolean, title: string) => {
    if (user?.is_system_user) return disabled;
    switch (title) {
      case 'O&M':
        return !user?.role?.permissions?.['O&M (Production Monitoring)']?.view;
      case 'Finance':
        return !user?.role?.permissions?.['Finance']?.view;
      case 'Acquisitions':
        return !user?.role?.permissions?.['Acquisitions']?.view && !user?.role?.permissions?.['Sales']?.view;
      case 'Project Hub':
        return !user?.role?.permissions?.['Project Hub']?.view && !user?.role?.permissions?.['Asset Management']?.view;
      case 'Data Room':
        return !user?.role?.permissions?.['Project Hub']?.view && !user?.role?.permissions?.['Asset Management']?.view;
      case 'Tasks':
        return !user?.role?.permissions?.['Project Hub']?.view && !user?.role?.permissions?.['Asset Management']?.view;
      case 'Reports':
        return !user?.role?.permissions?.['Reports']?.view;
      case 'Health Checks':
        return !user?.is_system_user;
      default:
        return disabled;
    }
  };

  const showModule = (moduleKey: string): boolean => {
    const hasPortfolioAccess = user?.role?.permissions?.['Investor Dashboard']?.view;
    if (moduleKey === 'dashboard') return !hasPortfolioAccess;
    if (moduleKey === 'portfolio') return !!hasPortfolioAccess;
    if (moduleKey === 'health-checks') return !!user?.is_system_user;
    return true;
  };

  const getPickerTitle = (tab: ProjectHubTab | null): string => {
    if (!tab) return 'Select a Project';
    const tabLabels: Record<ProjectHubTab, string> = {
      overview: 'Overview',
      'data-room': 'Data Room',
      om: 'O&M',
      finance: 'Finance',
      tasks: 'Tasks',
      reporting: 'Reporting'
    };
    return `Select Project for ${tabLabels[tab]}`;
  };

  return (
    <>
      <Stack direction="column" width={t => t.spacing(30)}>
        {menuItems.map(item =>
          showModule(item.key) ? (
            <AnchorElTooltip
              title={
                item.disabled
                  ? `${item.title} (coming soon)`
                  : disableModule(item.disabled, item.title)
                    ? "You don't have permission to view this page."
                    : isMenuOpen
                      ? ''
                      : item.title
              }
              key={item.key}
              anchor={containerRef}
            >
              <MenuItem
                title={item.title}
                icon={item.icon}
                onClick={handleMenuItemClick(item)}
                active={item.key === currentModuleId}
                disabled={disableModule(item.disabled, item.title)}
              />
            </AnchorElTooltip>
          ) : null
        )}
      </Stack>
      <ProjectPicker
        open={pickerOpen}
        onClose={() => {
          setPickerOpen(false);
          setPendingTab(null);
        }}
        onSelect={handleProjectSelect}
        title={getPickerTitle(pendingTab)}
      />
    </>
  );
};
