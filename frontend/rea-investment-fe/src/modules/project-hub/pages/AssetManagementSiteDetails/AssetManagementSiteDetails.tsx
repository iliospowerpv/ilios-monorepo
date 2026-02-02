import React, { useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import SpaceDashboardIcon from '@mui/icons-material/SpaceDashboard';
import FolderIcon from '@mui/icons-material/Folder';
import WhatshotIcon from '@mui/icons-material/Whatshot';
import AccountBalanceWalletIcon from '@mui/icons-material/AccountBalanceWallet';
import AssignmentTurnedInIcon from '@mui/icons-material/AssignmentTurnedIn';
import AssessmentIcon from '@mui/icons-material/Assessment';
import { siteDetailsQuery } from './loader';
import Overview from './tabs/Overview/Overview';
import DataRoom from './tabs/DataRoom/DataRoom';
import OM from './tabs/OM/OM';
import Finance from './tabs/Finance/Finance';
import Tasks from './tabs/Tasks/Tasks';
import Reporting from './tabs/Reporting/Reporting';
import type { AssetManagementSiteDetailsTabProps } from './tabs/types';
import { useEntityContext } from '../../../../contexts/entityContext';

interface TabData {
  id: string;
  label: string;
  link: string;
  disabled?: boolean;
  icon: React.ReactElement;
  content: React.FC<AssetManagementSiteDetailsTabProps> | null;
}

type TabType = 'overview' | 'data-room' | 'om' | 'finance' | 'tasks' | 'reporting';

interface AssetManagementSiteDetailsProps {
  tabId?: TabType;
}

const tabsData: TabData[] = [
  {
    id: 'overview',
    label: 'Overview',
    link: '/project-hub/projects/:siteId/overview',
    disabled: false,
    icon: <SpaceDashboardIcon />,
    content: Overview
  },
  {
    id: 'data-room',
    label: 'Data Room',
    link: '/project-hub/projects/:siteId/data-room',
    disabled: false,
    icon: <FolderIcon />,
    content: DataRoom
  },
  {
    id: 'om',
    label: 'O&M',
    link: '/project-hub/projects/:siteId/om',
    disabled: false,
    icon: <WhatshotIcon />,
    content: OM
  },
  {
    id: 'finance',
    label: 'Finance',
    link: '/project-hub/projects/:siteId/finance',
    disabled: false,
    icon: <AccountBalanceWalletIcon />,
    content: Finance
  },
  {
    id: 'tasks',
    label: 'Tasks',
    link: '/project-hub/projects/:siteId/tasks',
    disabled: false,
    icon: <AssignmentTurnedInIcon />,
    content: Tasks
  },
  {
    id: 'reporting',
    label: 'Reporting',
    link: '/project-hub/projects/:siteId/reporting',
    disabled: false,
    icon: <AssessmentIcon />,
    content: Reporting
  }
];

const legacyTabAliases: Record<string, TabType> = {
  devices: 'om',
  telemetry: 'om',
  diligence: 'data-room'
};

export const AssetManagementSiteDetails: React.FC<AssetManagementSiteDetailsProps> = ({ tabId }) => {
  const { siteId } = useParams();
  const isValidId = !!siteId && Number.isSafeInteger(Number.parseInt(siteId));
  const { setCurrentCompany, setCurrentProject } = useEntityContext();

  const resolvedTab = tabId ? legacyTabAliases[tabId] || tabId : 'overview';
  const activeTab = resolvedTab as TabType;

  const { data: siteDetails, isLoading: isLoadingSiteDetails } = useQuery(
    siteDetailsQuery(isValidId ? Number.parseInt(siteId) : -1, isValidId, true)
  );

  useEffect(() => {
    if (siteDetails) {
      setCurrentCompany({ id: siteDetails.company.id, name: siteDetails.company.name });
      setCurrentProject({ id: siteDetails.id, name: siteDetails.name });
    }
  }, [siteDetails, setCurrentCompany, setCurrentProject]);

  const DisplayContent = React.useMemo(() => {
    const tab = tabsData.find(({ id }) => id === activeTab);
    return tab ? tab.content : tabsData[0].content;
  }, [activeTab]);

  if (!DisplayContent || isLoadingSiteDetails || !siteDetails) return null;

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
              to={tab.link.replace(':siteId', String(siteId))}
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
