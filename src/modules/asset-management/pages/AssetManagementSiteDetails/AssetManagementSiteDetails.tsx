import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import SpaceDashboardIcon from '@mui/icons-material/SpaceDashboard';
import CastConnectedIcon from '@mui/icons-material/CastConnected';
import { siteDetailsQuery } from './loader';
import Overview from './tabs/Overview/Overview';
import Devices from './tabs/Devices/Devices';
import Tasks from './tabs/Tasks/Tasks';
import type { AssetManagementSiteDetailsTabProps } from './tabs/types';
import AssignmentTurnedInIcon from '@mui/icons-material/AssignmentTurnedIn';

interface TabData {
  id: string;
  label: string;
  link: string;
  disabled?: boolean;
  icon: React.ReactElement;
  content: React.FC<AssetManagementSiteDetailsTabProps> | null;
}

type TabType = 'overview' | 'devices' | 'diligence' | 'tasks';

interface AssetManagementSiteDetailsProps {
  tabId?: TabType;
}

const tabsData: TabData[] = [
  {
    id: 'overview',
    label: 'Overview',
    link: '/asset-management/companies/:companyId/sites/:siteId/overview',
    disabled: false,
    icon: <SpaceDashboardIcon />,
    content: Overview
  },
  {
    id: 'devices',
    label: 'Devices',
    link: '/asset-management/companies/:companyId/sites/:siteId/devices',
    disabled: false,
    icon: <CastConnectedIcon />,
    content: Devices
  },
  {
    id: 'tasks',
    label: 'Tasks',
    link: '/asset-management/companies/:companyId/sites/:siteId/tasks',
    disabled: false,
    icon: <AssignmentTurnedInIcon />,
    content: Tasks
  }
];

export const AssetManagementSiteDetails: React.FC<AssetManagementSiteDetailsProps> = ({ tabId }) => {
  const { siteId } = useParams();
  const isValidId = !!siteId && Number.isSafeInteger(Number.parseInt(siteId));
  const activeTab = tabId || 'overview';

  const { data: siteDetails, isLoading: isLoadingSiteDetails } = useQuery(
    siteDetailsQuery(isValidId ? Number.parseInt(siteId) : -1, isValidId, true)
  );

  const DisplayContent = React.useMemo(() => {
    const tab = tabsData.find(({ id }) => id === activeTab);
    return tab ? tab.content : null;
  }, [activeTab]);

  if (!DisplayContent || isLoadingSiteDetails || !siteDetails) return null;

  const companyId = siteDetails?.company.id;

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
              to={tab.link.replace(':siteId', String(siteId)).replace(':companyId', String(companyId))}
              value={tab.id}
              disabled={tab.disabled}
              icon={tab.icon}
            />
          ))}
        </Tabs>
      </Box>
      <div role="tabpanel">
        <Box sx={{ paddingTop: '24px' }}>
          <DisplayContent siteDetails={siteDetails} />
        </Box>
      </div>
    </Box>
  );
};

export default AssetManagementSiteDetails;
