import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import SpaceDashboardIcon from '@mui/icons-material/SpaceDashboard';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import WarningRoundedIcon from '@mui/icons-material/WarningRounded';
import { companyDetailsQuery } from './loader';
import Overview from './tabs/Overview/Overview';
import Sites from './tabs/Sites/Sites';
import Alerts from './tabs/Alerts/Alerts';
import type { CompanyDetailsTabProps } from './tabs/types';
import AssignmentTurnedInIcon from '@mui/icons-material/AssignmentTurnedIn';
import Tasks from './tabs/Tasks/Tasks';

interface TabData {
  id: string;
  label: string;
  link: string;
  disabled?: boolean;
  icon: React.ReactElement;
  content: React.FC<CompanyDetailsTabProps> | null;
}

type TabType = 'overview' | 'sites' | 'alerts' | 'tasks';

interface CompanyDetailsProps {
  tabId?: TabType;
}

const tabsData: TabData[] = [
  {
    id: 'overview',
    label: 'Overview',
    link: '/operations-and-maintenance/companies/:companyId/overview',
    disabled: false,
    icon: <SpaceDashboardIcon />,
    content: Overview
  },
  {
    id: 'sites',
    label: 'Sites',
    link: '/operations-and-maintenance/companies/:companyId/sites',
    disabled: false,
    icon: <LocationOnIcon />,
    content: Sites
  },
  {
    id: 'alerts',
    label: 'Alerts',
    link: '/operations-and-maintenance/companies/:companyId/alerts',
    disabled: false,
    icon: <WarningRoundedIcon />,
    content: Alerts
  },
  {
    id: 'tasks',
    label: 'Tasks',
    link: '/operations-and-maintenance/companies/:companyId/tasks',
    disabled: false,
    icon: <AssignmentTurnedInIcon />,
    content: Tasks
  }
];

export const CompanyDetailsPage: React.FC<CompanyDetailsProps> = ({ tabId }) => {
  const { companyId } = useParams();
  const isValidId = !!companyId && Number.isSafeInteger(Number.parseInt(companyId));
  const activeTab = tabId || 'overview';

  const {
    data: companyDetails,
    isLoading: isLoadingCompanyDetails,
    error: companyDetailsLoadingError
  } = useQuery(companyDetailsQuery(isValidId ? Number.parseInt(companyId) : -1, isValidId));

  React.useEffect(() => {
    if (companyDetailsLoadingError) {
      throw companyDetailsLoadingError;
    }
  }, [companyDetailsLoadingError]);

  const DisplayContent = React.useMemo(() => {
    const tab = tabsData.find(({ id }) => id === activeTab);
    return tab ? tab.content : null;
  }, [activeTab]);

  if (!DisplayContent || isLoadingCompanyDetails || !companyDetails) return null;

  return (
    <Box>
      <Typography variant="h4" marginBottom="24px" sx={{ fontWeight: 600 }} fontSize="34px" lineHeight="42px">
        {companyDetails.name}
      </Typography>
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={activeTab}>
          {tabsData.map(tab => (
            <Tab
              key={tab.id}
              label={tab.label}
              component={Link}
              to={tab.link.replace(':companyId', companyId as string)}
              value={tab.id}
              disabled={tab.disabled}
              icon={tab.icon}
            />
          ))}
        </Tabs>
      </Box>
      <div role="tabpanel">
        <Box sx={{ paddingTop: '24px' }}>
          <DisplayContent companyDetails={companyDetails} />
        </Box>
      </div>
    </Box>
  );
};

export default CompanyDetailsPage;
