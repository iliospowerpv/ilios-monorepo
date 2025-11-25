import * as React from 'react';
import { useParams } from 'react-router-dom';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { DeviceForm } from '../../../../components/forms/DeviceForm/DeviceForm';

export const AssetManagementAddDevicePage: React.FC = () => {
  const { siteId, companyId } = useParams();
  const isValidSiteId = !!siteId && Number.isSafeInteger(Number.parseInt(siteId));
  const isValidCompanyId = !!companyId && Number.isSafeInteger(Number.parseInt(companyId));

  if (!isValidSiteId) throw new Error(`Provided siteId "${siteId}" is invalid.`);
  if (!isValidCompanyId) throw new Error(`Provided companyId "${companyId}" is invalid.`);

  return (
    <Stack minHeight="100%" justifyContent="flex-start" alignItems="center">
      <Typography my="64px" variant="h4" fontWeight={600}>
        Add Device
      </Typography>
      <DeviceForm mode="add" siteId={Number.parseInt(siteId)} companyId={Number.parseInt(companyId)} />
    </Stack>
  );
};

export default AssetManagementAddDevicePage;
