import * as React from 'react';
import { useQuery } from '@tanstack/react-query';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import { CompanyForm } from '../../../../components/forms/CompanyForm/CompanyForm';
import { ApiClient } from '../../../../api';

export const EditMyCompanyPage: React.FC = () => {
  const {
    data: companyData,
    isLoading: isLoadingCompanyData,
    error: companyDataLoadingError
  } = useQuery({
    queryFn: ApiClient.myCompany.getMyCompany,
    queryKey: ['my-company']
  });

  if (isLoadingCompanyData) return null;

  return (
    <Stack minHeight="100%" justifyContent="flex-start" alignItems="center">
      <Typography my="64px" variant="h4" fontWeight={600} data-testid="edit-company__form-title">
        Edit Company
      </Typography>
      {companyDataLoadingError && (
        <Alert sx={{ minWidth: '300px', width: '40%', justifySelf: 'center' }} severity="error">
          {companyDataLoadingError?.message || 'Something went wrong.'}
        </Alert>
      )}
      {!companyDataLoadingError && companyData && (
        <>
          <CompanyForm mode="edit" companyData={companyData} companyId={companyData.id} />
        </>
      )}
    </Stack>
  );
};

export default EditMyCompanyPage;
