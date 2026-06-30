import React from 'react';
import { Link } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import { useQueryClient } from '@tanstack/react-query';
import AuditLogs from './tabs/AuditLogs/AuditLogs';
import HealthChecksPage from '../HealthChecks/HealthChecksPage';
import ArchitecturePage from '../Architecture/ArchitecturePage';
import { AssistantUsagePanel } from '../../../../components/assistant/admin/AssistantUsagePanel';
import { ApiClient } from '../../../../api';
import { auditLogQueryKeys, AUDIT_LOG_DEFAULT_PAGE_SIZE } from '../../../../api/audit-log';

interface TabInfo {
  id: string;
  label: string;
  disabled: boolean;
  link: string;
  content: React.ReactNode;
}

interface SettingsProps {
  tabId?: 'health-checks' | 'audit-logs' | 'architecture' | 'assistant-usage';
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
    id: 'architecture',
    link: '/settings/architecture',
    label: 'Architecture',
    disabled: false,
    content: <ArchitecturePage />
  },
  {
    id: 'assistant-usage',
    link: '/settings/assistant-usage',
    label: 'AI Assistant',
    disabled: false,
    content: <AssistantUsagePanel />
  }
];

const Settings: React.FC<SettingsProps> = ({ tabId }) => {
  const activeTab = tabId || 'audit-logs';
  const queryClient = useQueryClient();

  React.useEffect(() => {
    queryClient.prefetchQuery({
      queryKey: auditLogQueryKeys.page(0, AUDIT_LOG_DEFAULT_PAGE_SIZE),
      queryFn: () => ApiClient.auditLog.getAuditLogs({ skip: 0, limit: AUDIT_LOG_DEFAULT_PAGE_SIZE }),
      staleTime: 30_000
    });
  }, [queryClient]);

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
