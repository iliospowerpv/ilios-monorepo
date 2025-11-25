import React from 'react';
import { Link } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import Users from './tabs/Users/Users';
import Companies from './tabs/Companies/Companies';
import Sites from './tabs/Sites/Sites';
import AuditLogs from './tabs/AuditLogs/AuditLogs';

interface TabInfo {
  id: string;
  label: string;
  disabled: boolean;
  link: string;
  content: React.ReactNode;
}

interface SettingsProps {
  tabId?: 'users' | 'companies' | 'sites' | 'audit-logs';
}

const tabData: TabInfo[] = [
  { id: 'users', link: '/settings/users', label: 'Users', disabled: false, content: <Users /> },
  { id: 'companies', link: '/settings/companies', label: 'Companies', disabled: false, content: <Companies /> },
  { id: 'sites', link: '/settings/sites', label: 'Sites', disabled: false, content: <Sites /> },
  { id: 'audit-logs', link: '/settings/audit-logs', label: 'Audit Logs', disabled: false, content: <AuditLogs /> },
  { id: 'notification', link: '/', label: 'Notification', disabled: true, content: <Box>Notification Tab</Box> },
  { id: 'alerts', link: '/', label: 'Alerts', disabled: true, content: <Box>Alerts</Box> }
];

const Settings: React.FC<SettingsProps> = ({ tabId }) => {
  const activeTab = tabId || 'users';

  const content = React.useMemo(() => {
    const tab = tabData.find(({ id }) => id === activeTab);
    return tab ? <Box sx={{ padding: '16px 0' }}>{tab.content}</Box> : null;
  }, [activeTab]);

  return (
    <Box>
      <Typography variant="h4" gutterBottom sx={{ fontWeight: 600 }}>
        Settings
      </Typography>
      <Box>
        <Tabs value={activeTab}>
          {tabData.map(tab => (
            <Tab
              key={tab.id}
              component={Link}
              to={tab.link}
              data-testid={`tab__${tab.id}`}
              label={tab.label}
              value={tab.id}
              disabled={tab.disabled}
            />
          ))}
        </Tabs>
      </Box>
      <div role="tabpanel">{content}</div>
    </Box>
  );
};

export default Settings;
