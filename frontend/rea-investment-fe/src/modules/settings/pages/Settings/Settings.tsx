import React from 'react';
import { Link } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import AuditLogs from './tabs/AuditLogs/AuditLogs';
import HealthChecksPage from '../HealthChecks/HealthChecksPage';
import ExtractionRegistry from './tabs/ExtractionRegistry';

interface TabInfo {
  id: string;
  label: string;
  disabled: boolean;
  link: string;
  content: React.ReactNode;
}

interface SettingsProps {
  tabId?: 'health-checks' | 'audit-logs' | 'notification' | 'alerts' | 'extraction-registry';
}

const tabData: TabInfo[] = [
  {
    id: 'health-checks',
    link: '/settings/health-checks',
    label: 'Health Checks',
    disabled: false,
    content: <HealthChecksPage />
  },
  { id: 'audit-logs', link: '/settings/audit-logs', label: 'Audit Logs', disabled: false, content: <AuditLogs /> },
  {
    id: 'extraction-registry',
    link: '/settings/extraction-registry',
    label: 'Extraction Registry',
    disabled: false,
    content: <ExtractionRegistry />
  },
  { id: 'notification', link: '/', label: 'Notification', disabled: true, content: <Box>Notification Tab</Box> },
  { id: 'alerts', link: '/', label: 'Alerts', disabled: true, content: <Box>Alerts</Box> }
];

const Settings: React.FC<SettingsProps> = ({ tabId }) => {
  const activeTab = tabId || 'health-checks';

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
