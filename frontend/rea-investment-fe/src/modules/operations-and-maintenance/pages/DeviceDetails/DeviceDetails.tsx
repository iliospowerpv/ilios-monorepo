import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import SpaceDashboardIcon from '@mui/icons-material/SpaceDashboard';
import WarningRoundedIcon from '@mui/icons-material/WarningRounded';
import { deviceDetailsQuery } from './loader';
import Alerts from './tabs/Alerts/Alerts';
import Overview from './tabs/Overview/Overview';
import type { DeviceDetailsTabProps } from './tabs/types';

interface TabData {
  id: string;
  label: string;
  link: string;
  disabled?: boolean;
  icon: React.ReactElement;
  content: React.FC<DeviceDetailsTabProps> | null;
}

type TabType = 'overview' | 'alerts';

interface DeviceDetailsProps {
  tabId?: TabType;
}

const tabsData: TabData[] = [
  {
    id: 'overview',
    label: 'Overview',
    link: '/operations-and-maintenance/companies/:companyId/sites/:siteId/device/:deviceId/overview',
    disabled: false,
    icon: <SpaceDashboardIcon />,
    content: Overview
  },
  {
    id: 'alerts',
    label: 'Alerts',
    link: '/operations-and-maintenance/companies/:companyId/sites/:siteId/device/:deviceId/alerts',
    disabled: false,
    icon: <WarningRoundedIcon />,
    content: Alerts
  }
];

export const DeviceDetailsPage: React.FC<DeviceDetailsProps> = ({ tabId }) => {
  //TODO: this component currently abbadoned, its regarding devise info for O&M module.
  const { companyId, siteId, deviceId } = useParams();
  const isValidId = !!deviceId && Number.isSafeInteger(Number.parseInt(deviceId));
  const activeTab = tabId || 'overview';

  const {
    data: deviceDetails,
    isLoading: isLoadingDeviceDetails,
    error: deviceDetailsLoadingError
  } = useQuery(deviceDetailsQuery(isValidId ? Number.parseInt(deviceId) : -1, isValidId));

  React.useEffect(() => {
    if (deviceDetailsLoadingError) {
      throw deviceDetailsLoadingError;
    }
  }, [deviceDetailsLoadingError]);

  const DisplayContent = React.useMemo(() => {
    const tab = tabsData.find(({ id }) => id === activeTab);
    return tab ? tab.content : null;
  }, [activeTab]);

  if (!DisplayContent || isLoadingDeviceDetails || !deviceDetails) return null;

  return (
    <Box>
      <Typography variant="h4" marginBottom="24px" sx={{ fontWeight: 600 }} fontSize="34px" lineHeight="42px">
        {deviceDetails.name}
      </Typography>
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={activeTab}>
          {tabsData.map(tab => (
            <Tab
              key={tab.id}
              label={tab.label}
              component={Link}
              to={tab.link
                .replace(':companyId', companyId as string)
                .replace(':siteId', siteId as string)
                .replace(':deviceId', deviceId as string)}
              value={tab.id}
              disabled={tab.disabled}
              icon={tab.icon}
            />
          ))}
        </Tabs>
      </Box>
      <div role="tabpanel">
        <Box sx={{ paddingTop: '24px' }}>
          <DisplayContent deviceDetails={deviceDetails} />
        </Box>
      </div>
    </Box>
  );
};

export default DeviceDetailsPage;
