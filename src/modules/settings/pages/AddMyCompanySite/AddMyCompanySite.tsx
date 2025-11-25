import * as React from 'react';
import { AxiosError } from 'axios';
import Alert from '@mui/material/Alert';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { SiteForm } from '../../../../components/forms/SiteForm/SiteForm';
import { useMyCompanySettings } from '../../../../hooks/settings/my-company';

export const AddMyCompanySite: React.FC = () => {
  const { data, isLoading, error } = useMyCompanySettings();

  if (isLoading) return null;

  return (
    <Stack minHeight="100%" justifyContent="flex-start" alignItems="center">
      <Typography my="64px" variant="h4" fontWeight={600} data-testid="add-site__form-title">
        Add Site
      </Typography>
      {error && (
        <Alert sx={{ minWidth: '300px', width: '40%', justifySelf: 'center' }} severity="error">
          {error instanceof AxiosError ? error.response?.data.message || error.message : error.message}
        </Alert>
      )}
      {!error && data && (
        <>
          <SiteForm mode="add" companyId={data.id} />
        </>
      )}
    </Stack>
  );
};

export default AddMyCompanySite;
