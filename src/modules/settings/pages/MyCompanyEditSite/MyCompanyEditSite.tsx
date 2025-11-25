import * as React from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import { SiteForm } from '../../../../components/forms/SiteForm/SiteForm';
import { ApiClient } from '../../../../api';

export const MyCompanyEditSitePage: React.FC = () => {
  const { siteId } = useParams();
  const isValidId = !!siteId && Number.isSafeInteger(Number.parseInt(siteId));
  const {
    data: siteData,
    isLoading: isLoadingCompanyData,
    error: companyDataLoadingError
  } = useQuery({
    queryFn: async () => {
      const id = isValidId ? Number.parseInt(siteId) : -1;
      return ApiClient.myCompany.getMyCompanySiteById(id);
    },
    queryKey: ['my-company-site', { siteId }],
    enabled: isValidId
  });

  if (isLoadingCompanyData) return null;

  return (
    <Stack minHeight="100%" justifyContent="flex-start" alignItems="center">
      <Typography my="64px" variant="h4" fontWeight={600} data-testid="edit-company__form-title">
        Edit Site
      </Typography>
      {(companyDataLoadingError || !isValidId) && (
        <Alert sx={{ minWidth: '300px', width: '40%', justifySelf: 'center' }} severity="error">
          {companyDataLoadingError?.message || `Provided userId "${siteId}" is invalid.`}
        </Alert>
      )}
      {!companyDataLoadingError && siteData && isValidId && (
        <>
          <SiteForm mode="edit" companyId={siteData.company.id} siteId={Number.parseInt(siteId)} siteData={siteData} />
        </>
      )}
    </Stack>
  );
};

export default MyCompanyEditSitePage;
