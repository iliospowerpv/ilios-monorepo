import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import { Link } from 'react-router-dom';
import Overview from './components/Overview/Overview';
import Sites from './components/Sites/Sites';
import SpaceDashboardIcon from '@mui/icons-material/SpaceDashboard';
import LocationOnIcon from '@mui/icons-material/LocationOn';

interface TabInfo {
  id: string;
  link: string;
  label: string;
  disabled?: boolean;
  icon?: React.ReactElement;
  content: React.ReactNode;
}

const tabData: TabInfo[] = [
  {
    id: 'overview',
    link: '/asset-management/overview',
    label: 'Overview',
    disabled: false,
    icon: <SpaceDashboardIcon />,
    content: <Overview />
  },
  {
    id: 'sites',
    link: '/asset-management/sites',
    label: 'Sites',
    disabled: false,
    icon: <LocationOnIcon />,
    content: <Sites />
  }
];

interface AssetManagementProps {
  tabId?: 'overview' | 'sites';
}

const AssetManagement: React.FC<AssetManagementProps> = ({ tabId }) => {
  const activeTab = tabId || 'overview';
  const title = activeTab === 'sites' ? 'Sites' : 'Companies';

  const content = React.useMemo(() => {
    const tab = tabData.find(({ id }) => id === activeTab);
    return tab ? <Box sx={{ padding: '16px 0' }}>{tab.content}</Box> : null;
  }, [activeTab]);

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ fontWeight: 600 }} data-testid="asset-management__title">
        {title}
      </Typography>
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={activeTab}>
          {tabData.map(tab => (
            <Tab
              key={tab.id}
              component={Link}
              to={tab.link}
              label={tab.label}
              value={tab.id}
              disabled={tab.disabled}
              icon={tab.icon}
            />
          ))}
        </Tabs>
      </Box>
      <div role="tabpanel">{content}</div>
    </Box>
  );
};

export default AssetManagement;
