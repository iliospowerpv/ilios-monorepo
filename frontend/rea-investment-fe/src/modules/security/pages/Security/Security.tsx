import React from 'react';
import { useSearchParams } from 'react-router-dom';
import { SiteDetailsTabProps } from '../../../operations-and-maintenance/pages/SiteDetails/tabs/types';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import CamerasTab from '../components/Cameras/Cameras';
import AlertsTab from '../components/Alerts/Alerts';

export const Security: React.FC<SiteDetailsTabProps> = ({ siteDetails, companyDetails }) => {
  const [searchParams, setSearchParams] = useSearchParams();

  const parsedTabIdValue = (searchParams.has('tabId') && searchParams.get('tabId')) || 'cameras';
  const tabId = ['cameras', 'alerts'].includes(parsedTabIdValue) ? parsedTabIdValue : 'cameras';

  const handleToggleButtonChange = React.useCallback(
    (event: React.MouseEvent<HTMLElement>, newTabId: string) => {
      if (newTabId !== null) {
        setSearchParams(
          searchParams => {
            const newParams = new URLSearchParams(searchParams);
            newParams.set('tabId', newTabId);
            return newParams;
          },
          { replace: true }
        );
      }
    },
    [setSearchParams]
  );

  return (
    <>
      <ToggleButtonGroup
        size="small"
        data-testid="toggle__group"
        value={tabId}
        exclusive
        onChange={handleToggleButtonChange}
        sx={{ height: '40px', marginBottom: '24px' }}
      >
        <ToggleButton value="cameras" sx={{ width: '104px' }}>
          Cameras
        </ToggleButton>
        <ToggleButton value="alerts" sx={{ width: '104px' }}>
          Alerts
        </ToggleButton>
      </ToggleButtonGroup>
      {tabId === 'cameras' && <CamerasTab siteDetails={siteDetails} companyDetails={companyDetails} />}
      {tabId === 'alerts' && <AlertsTab siteDetails={siteDetails} companyDetails={companyDetails} />}
    </>
  );
};

export default Security;
