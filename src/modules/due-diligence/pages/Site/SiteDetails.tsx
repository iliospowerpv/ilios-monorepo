import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link, useParams } from 'react-router-dom';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Tabs from '@mui/material/Tabs';
import Tab from '@mui/material/Tab';
import SpaceDashboardIcon from '@mui/icons-material/SpaceDashboard';
import Overview from './tabs/Overview/Overview';
import type { SiteDetailsTabProps } from './tabs/types';
import DescriptionIcon from '@mui/icons-material/Description';
import Diligence from './tabs/Diligence/DiligenceList';
import { useAuth } from '../../../../contexts/auth/auth';
import { BootstrapTooltip } from '../../../../components/common/BootstrapTooltip/BootstrapTooltip';
import { siteCrumbsQuery } from './loader';

interface TabData {
  id: string;
  label: string;
  link: string;
  disabled?: boolean;
  icon: React.ReactElement;
  content: React.FC<SiteDetailsTabProps> | null;
}

type TabType = 'overview' | 'diligence';

interface SiteDetailsProps {
  tabId?: TabType;
}

export const SiteDetailsPage: React.FC<SiteDetailsProps> = ({ tabId }) => {
  const { companyId, siteId } = useParams();
  const isValidId = !!siteId && Number.isSafeInteger(Number.parseInt(siteId));
  const { user } = useAuth();
  const access = user?.diligence_overview_access || user?.is_system_user;
  let activeTab = tabId || 'overview';
  if (!access) {
    activeTab = 'diligence';
  }

  const tabsData: TabData[] = [
    {
      id: 'overview',
      label: 'Overview',
      link: '/due-diligence/companies/:companyId/sites/:siteId/overview',
      disabled: !access,
      icon: <SpaceDashboardIcon />,
      content: Overview
    },
    {
      id: 'diligence',
      label: 'Diligence',
      link: '/due-diligence/companies/:companyId/sites/:siteId/due-diligence',
      disabled: false,
      icon: <DescriptionIcon />,
      content: Diligence
    }
  ];

  const {
    data: siteDetails,
    isLoading: isLoadingSiteDetails,
    error: siteDetailsLoadingError
  } = useQuery(siteCrumbsQuery(isValidId ? Number.parseInt(siteId) : -1, isValidId));

  React.useEffect(() => {
    if (siteDetailsLoadingError) {
      throw siteDetailsLoadingError;
    }
  }, [siteDetailsLoadingError]);

  const DisplayContent = React.useMemo(() => {
    const tab = tabsData.find(({ id }) => id === activeTab);
    return tab ? tab.content : null;
  }, [activeTab]);

  if (!DisplayContent || isLoadingSiteDetails || !siteDetails) {
    return null;
  }

  return (
    <Box>
      <Typography variant="h4" marginBottom="24px" sx={{ fontWeight: 600 }} fontSize="34px" lineHeight="42px">
        {siteDetails.name}
      </Typography>
      <Box sx={{ borderBottom: 1, borderColor: 'divider' }}>
        <Tabs value={activeTab}>
          {tabsData.map(tab =>
            !tab.disabled ? (
              <Tab
                key={tab.id}
                label={tab.label}
                component={Link}
                to={tab.link.replace(':companyId', companyId as string).replace(':siteId', siteId as string)}
                value={tab.id}
                disabled={tab.disabled}
                icon={tab.icon}
              />
            ) : (
              <BootstrapTooltip key={tab.id} title="You don’t have permission to view this page." placement="top">
                <span>
                  <Tab
                    key={tab.id}
                    label={tab.label}
                    component={Link}
                    to={tab.link.replace(':companyId', companyId as string).replace(':siteId', siteId as string)}
                    value={tab.id}
                    disabled={tab.disabled}
                    icon={tab.icon}
                  />
                </span>
              </BootstrapTooltip>
            )
          )}
        </Tabs>
      </Box>
      <div role="tabpanel">
        <Box sx={{ paddingTop: '24px' }}>
          <DisplayContent siteId={siteId} companyId={companyId} />
        </Box>
      </div>
    </Box>
  );
};

export default SiteDetailsPage;
