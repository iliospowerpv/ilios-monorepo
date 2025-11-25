import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import SpaceDashboardIcon from '@mui/icons-material/SpaceDashboard';
import WarningRoundedIcon from '@mui/icons-material/WarningRounded';
import { siteDetailsQuery, companyDetailsQuery } from './loader';
import Alerts from './tabs/Alerts/Alerts';
import Overview from './tabs/Overview/Overview';
import Devices from './tabs/Devices/Devices';
import type { SiteDetailsTabProps } from './tabs/types';
import CastConnectedIcon from '@mui/icons-material/CastConnected';
import VideocamIcon from '@mui/icons-material/Videocam';
import { SecurityPage } from '../../../security';
import AssignmentTurnedInIcon from '@mui/icons-material/AssignmentTurnedIn';
import Tasks from './tabs/Tasks/Tasks';

interface TabData {
  id: string;
  label: string;
  link: string;
  disabled?: boolean;
  icon: React.ReactElement;
  content: React.FC<SiteDetailsTabProps> | null;
}

type TabType = 'overview' | 'devices' | 'alerts' | 'security' | 'tasks';

interface SiteDetailsProps {
  tabId?: TabType;
}

const tabsData: TabData[] = [
  {
    id: 'overview',
    label: 'Overview',
    link: '/operations-and-maintenance/companies/:companyId/sites/:siteId/overview',
    disabled: false,
    icon: <SpaceDashboardIcon />,
    content: Overview
  },
  {
    id: 'devices',
    label: 'Devices',
    link: '/operations-and-maintenance/companies/:companyId/sites/:siteId/devices',
    disabled: false,
    icon: <CastConnectedIcon />,
    content: Devices
  },
  {
    id: 'alerts',
    label: 'Alerts',
    link: '/operations-and-maintenance/companies/:companyId/sites/:siteId/alerts',
    disabled: false,
    icon: <WarningRoundedIcon />,
    content: Alerts
  },
  {
    id: 'security',
    label: 'Security',
    link: '/operations-and-maintenance/companies/:companyId/sites/:siteId/security',
    disabled: false,
    icon: <VideocamIcon />,
    content: SecurityPage
  },
  {
    id: 'tasks',
    label: 'Tasks',
    link: '/operations-and-maintenance/companies/:companyId/sites/:siteId/tasks',
    disabled: false,
    icon: <AssignmentTurnedInIcon />,
    content: Tasks
  }
];

export const SiteDetailsPage: React.FC<SiteDetailsProps> = ({ tabId }) => {
  const { companyId, siteId } = useParams();
  const isValidId = !!siteId && Number.isSafeInteger(Number.parseInt(siteId));
  const isValidCompanyId = !!companyId && Number.isSafeInteger(Number.parseInt(companyId));
  const activeTab = tabId || 'overview';

  const {
    data: siteDetails,
    isLoading: isLoadingSiteDetails,
    error: siteDetailsLoadingError
  } = useQuery(siteDetailsQuery(isValidId ? Number.parseInt(siteId) : -1, isValidId));

  const {
    data: companyDetails,
    isLoading: isLoadingComapnyDetails,
    error: companyDetailsLoadingError
  } = useQuery(companyDetailsQuery(isValidCompanyId ? Number.parseInt(companyId) : -1, isValidCompanyId));

  React.useEffect(() => {
    if (siteDetailsLoadingError) {
      throw siteDetailsLoadingError;
    }
  }, [siteDetailsLoadingError]);

  React.useEffect(() => {
    if (companyDetailsLoadingError) {
      throw companyDetailsLoadingError;
    }
  }, [companyDetailsLoadingError]);

  const DisplayContent = React.useMemo(() => {
    const tab = tabsData.find(({ id }) => id === activeTab);
    return tab ? tab.content : null;
  }, [activeTab]);

  if (!DisplayContent || isLoadingSiteDetails || isLoadingComapnyDetails || !siteDetails || !companyDetails) {
    return null;
  }

  return (
    <Box>
      <Typography variant="h4" marginBottom="24px" sx={{ fontWeight: 600 }} fontSize="34px" lineHeight="42px">
        {siteDetails.name}
      </Typography>
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={activeTab}>
          {tabsData.map(tab => (
            <Tab
              key={tab.id}
              label={tab.label}
              component={Link}
              to={tab.link.replace(':companyId', companyId as string).replace(':siteId', siteId as string)}
              value={tab.id}
              disabled={tab.disabled}
              icon={tab.icon}
            />
          ))}
        </Tabs>
      </Box>
      <div role="tabpanel">
        <Box sx={{ paddingTop: '24px' }}>
          <DisplayContent siteDetails={siteDetails} companyDetails={companyDetails} />
        </Box>
      </div>
    </Box>
  );
};

export default SiteDetailsPage;
