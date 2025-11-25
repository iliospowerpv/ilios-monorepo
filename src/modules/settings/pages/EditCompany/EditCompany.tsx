import * as React from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import { CompanyForm } from '../../../../components/forms/CompanyForm/CompanyForm';
import { ApiClient } from '../../../../api';

export const EditCompanyPage: React.FC = () => {
  const { companyId } = useParams();
  const isValidId = !!companyId && Number.isSafeInteger(Number.parseInt(companyId));
  const {
    data: companyData,
    isLoading: isLoadingCompanyData,
    error: companyDataLoadingError
  } = useQuery({
    queryFn: async () => {
      const id = isValidId ? Number.parseInt(companyId) : -1;
      return ApiClient.companies.company(id);
    },
    queryKey: ['company', { companyId }],
    enabled: isValidId
  });

  if (isLoadingCompanyData) return null;

  return (
    <Stack minHeight="100%" justifyContent="flex-start" alignItems="center">
      <Typography my="64px" variant="h4" fontWeight={600} data-testid="edit-company__form-title">
        Edit Company
      </Typography>
      {(companyDataLoadingError || !isValidId) && (
        <Alert sx={{ minWidth: '300px', width: '40%', justifySelf: 'center' }} severity="error">
          {companyDataLoadingError?.message || `Provided companyId "${companyId}" is invalid.`}
        </Alert>
      )}
      {!companyDataLoadingError && companyData && isValidId && (
        <>
          <CompanyForm mode="edit" companyData={companyData} companyId={Number.parseInt(companyId)} />
        </>
      )}
    </Stack>
  );
};

export default EditCompanyPage;
