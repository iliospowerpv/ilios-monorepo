import * as React from 'react';
import { useQuery } from '@tanstack/react-query';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import { ApiClient } from '../../../../api';
import { UserForm } from '../../../../components/forms/UserForm/UserForm';

export const AddMyCompanyUserPage: React.FC = () => {
  const {
    data: myCompanyData,
    isLoading: isLoadingMyCompanyData,
    error: myCompanyDataLoadingError
  } = useQuery({
    queryFn: ApiClient.myCompany.getMyCompany,
    queryKey: ['my-company-data']
  });

  if (myCompanyDataLoadingError) {
    return (
      <Stack minHeight="100%" justifyContent="flex-start" alignItems="center">
        <Alert sx={{ minWidth: '300px', width: '40%', justifySelf: 'center' }} severity="error">
          {myCompanyDataLoadingError?.message}
        </Alert>
      </Stack>
    );
  }

  if (isLoadingMyCompanyData || !myCompanyData) return null;

  return (
    <Stack minHeight="100%" justifyContent="flex-start" alignItems="center">
      <Typography my="64px" variant="h4" fontWeight={600}>
        Add User
      </Typography>
      <UserForm mode="add" level="company" companyData={myCompanyData} />
    </Stack>
  );
};

export default AddMyCompanyUserPage;
