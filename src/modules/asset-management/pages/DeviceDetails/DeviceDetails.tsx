import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import SpaceDashboardIcon from '@mui/icons-material/SpaceDashboard';
import { deviceDetailsQuery } from './loader';
import type { DeviceDetailsTabProps } from './tabs/types';
import Overview from './tabs/Overview/Overview';

interface TabData {
  id: string;
  label: string;
  link: string;
  disabled?: boolean;
  icon: React.ReactElement;
  content: React.FC<DeviceDetailsTabProps> | null;
}

type TabType = 'overview' | 'tasks';

interface DeviceDetailsProps {
  tabId?: TabType;
}

const tabsData: TabData[] = [
  {
    id: 'overview',
    label: 'Overview',
    link: '/asset-management/companies/:companyId/sites/:siteId/devices/:deviceId/overview',
    disabled: false,
    icon: <SpaceDashboardIcon />,
    content: Overview
  }
];

export const DeviceDetails: React.FC<DeviceDetailsProps> = ({ tabId }) => {
  const { deviceId, siteId, companyId } = useParams();
  const isValidDeviceId = !!deviceId && Number.isSafeInteger(Number.parseInt(deviceId));
  const isValidSiteId = !!siteId && Number.isSafeInteger(Number.parseInt(siteId));
  const isValidCompanyId = !!companyId && Number.isSafeInteger(Number.parseInt(companyId));
  const activeTab = tabId || 'overview';

  if (!isValidDeviceId) throw new Error(`Provided deviceId "${deviceId}" is invalid.`);
  if (!isValidSiteId) throw new Error(`Provided siteId "${siteId}" is invalid.`);
  if (!isValidCompanyId) throw new Error(`Provided companyId "${companyId}" is invalid.`);

  const { data: deviceDetails, isLoading: isLoadingDeviceDetails } = useQuery(
    deviceDetailsQuery(
      isValidSiteId ? Number.parseInt(siteId) : -1,
      isValidDeviceId ? Number.parseInt(deviceId) : -1,
      isValidSiteId && isValidDeviceId,
      true
    )
  );

  const DisplayContent = React.useMemo(() => {
    const tab = tabsData.find(({ id }) => id === activeTab);
    return tab ? tab.content : null;
  }, [activeTab]);

  if (isLoadingDeviceDetails || !deviceDetails) return null;

  return (
    <Box>
      <Typography variant="h4" marginBottom="24px" sx={{ fontWeight: 600 }} fontSize="34px" lineHeight="42px">
        {deviceDetails.general_info.name}
      </Typography>
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={activeTab}>
          {tabsData.map(tab => (
            <Tab
              key={tab.id}
              label={tab.label}
              component={Link}
              to={tab.link
                .replace(':companyId', companyId || '')
                .replace(':siteId', siteId || '')
                .replace(':deviceId', deviceId || '')}
              value={tab.id}
              disabled={tab.disabled}
              icon={tab.icon}
            />
          ))}
        </Tabs>
      </Box>
      <div role="tabpanel">
        <Box sx={{ paddingTop: '24px' }}>
          {DisplayContent && (
            <DisplayContent
              deviceDetails={deviceDetails}
              siteId={Number.parseInt(siteId)}
              deviceId={Number.parseInt(deviceId)}
              companyId={Number.parseInt(companyId)}
            />
          )}
        </Box>
      </div>
    </Box>
  );
};

export default DeviceDetails;
