import React from 'react';
import { Link } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import SpaceDashboardIcon from '@mui/icons-material/SpaceDashboard';
import LocationOnIcon from '@mui/icons-material/LocationOn';
import PeopleAltIcon from '@mui/icons-material/PeopleAlt';

import Overview from './tabs/Overview/Overview';
import Sites from './tabs/Sites/Sites';
import Users from './tabs/Users/Users';
import { useMyCompanySettings } from '../../../../hooks/settings/my-company';
import type { CompanyDetailsTabProps } from './tabs/Overview/Overview';

interface TabData {
  id: string;
  label: string;
  link: string;
  disabled?: boolean;
  icon: React.ReactElement;
  content: React.FC<CompanyDetailsTabProps> | null;
}

type TabType = 'overview' | 'sites' | 'users';

interface MyCompanyProps {
  tabId?: TabType;
}

const tabsData: TabData[] = [
  {
    id: 'overview',
    label: 'Overview',
    link: '/settings/my-company/overview',
    disabled: false,
    icon: <SpaceDashboardIcon />,
    content: Overview
  },
  {
    id: 'sites',
    label: 'Sites',
    link: '/settings/my-company/sites',
    disabled: false,
    icon: <LocationOnIcon />,
    content: Sites
  },
  {
    id: 'users',
    label: 'Users',
    link: '/settings/my-company/users',
    disabled: false,
    icon: <PeopleAltIcon />,
    content: Users
  }
];

export const MyCompany: React.FC<MyCompanyProps> = ({ tabId }) => {
  const { data, isLoading } = useMyCompanySettings();
  const activeTab = tabId || 'overview';

  const DisplayContent = React.useMemo(() => {
    const tab = tabsData.find(({ id }) => id === activeTab);
    return tab ? tab.content : null;
  }, [activeTab]);

  if (!DisplayContent || isLoading || !data) return null;

  return (
    <Box>
      <Typography variant="h4" marginBottom="24px" sx={{ fontWeight: 600 }} fontSize="34px" lineHeight="42px">
        {data?.name}
      </Typography>
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={activeTab}>
          {tabsData.map(tab => (
            <Tab
              key={tab.id}
              label={tab.label}
              component={Link}
              to={tab.link}
              value={tab.id}
              disabled={tab.disabled}
              icon={tab.icon}
            />
          ))}
        </Tabs>
      </Box>
      <div role="tabpanel">
        <Box sx={{ paddingTop: '24px' }}>
          <DisplayContent companyDetails={data} />
        </Box>
      </div>
    </Box>
  );
};

export default MyCompany;
