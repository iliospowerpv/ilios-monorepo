import * as React from 'react';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ApiClient } from '../../../../api';
import { UserForm } from '../../../../components/forms/UserForm/UserForm';

export const EditMyCompanyUserPage: React.FC = () => {
  const { userId } = useParams();
  const isUserIdValid = !!userId && Number.isSafeInteger(Number.parseInt(userId));

  const {
    data: companyUsersResponse,
    isLoading: isLoadingCompanyUsers,
    error: companyUsersLoadingError
  } = useQuery({
    queryFn: () => ApiClient.myCompany.getMyCompanyUsers({ limit: 10000 }),
    queryKey: ['my-company-users'],
    enabled: isUserIdValid
  });

  const {
    data: myCompanyData,
    isLoading: isLoadingMyCompanyData,
    error: myCompanyDataLoadingError
  } = useQuery({
    queryFn: ApiClient.myCompany.getMyCompany,
    queryKey: ['my-company-data'],
    enabled: isUserIdValid
  });

  const userBelongsToCompany = React.useMemo(() => {
    if (!companyUsersResponse || !isUserIdValid) return false;

    const numericUserId = Number.parseInt(userId);
    const { items: companyUsers } = companyUsersResponse;

    return companyUsers.some(companyUser => companyUser.id === numericUserId);
  }, [companyUsersResponse, isUserIdValid, userId]);

  const {
    data: userData,
    isLoading: isLoadingUserData,
    error: userDataLoadingError
  } = useQuery({
    queryFn: async () => {
      const id = userId && isUserIdValid ? Number.parseInt(userId) : -1;
      return ApiClient.user.getById(id);
    },
    queryKey: ['users', { userId }],
    enabled: isUserIdValid && !!companyUsersResponse && userBelongsToCompany
  });

  if (isLoadingUserData || isLoadingCompanyUsers || isLoadingMyCompanyData) return null;

  if (!isUserIdValid) {
    return (
      <Stack minHeight="100%" justifyContent="flex-start" alignItems="center">
        <Alert sx={{ minWidth: '300px', width: '40%', justifySelf: 'center' }} severity="error">
          {`Provided userId "${userId}" is invalid.`}
        </Alert>
      </Stack>
    );
  }

  if (companyUsersResponse && !userBelongsToCompany) {
    return (
      <Stack minHeight="100%" justifyContent="flex-start" alignItems="center">
        <Alert sx={{ minWidth: '300px', width: '40%', justifySelf: 'center' }} severity="error">
          {`User with provided userId "${userId}" doesn't belong to your company.`}
        </Alert>
      </Stack>
    );
  }

  if (userDataLoadingError) {
    return (
      <Stack minHeight="100%" justifyContent="flex-start" alignItems="center">
        <Alert sx={{ minWidth: '300px', width: '40%', justifySelf: 'center' }} severity="error">
          {userDataLoadingError?.message}
        </Alert>
      </Stack>
    );
  }

  if (companyUsersLoadingError) {
    return (
      <Stack minHeight="100%" justifyContent="flex-start" alignItems="center">
        <Alert sx={{ minWidth: '300px', width: '40%', justifySelf: 'center' }} severity="error">
          {companyUsersLoadingError?.message}
        </Alert>
      </Stack>
    );
  }

  if (myCompanyDataLoadingError) {
    return (
      <Stack minHeight="100%" justifyContent="flex-start" alignItems="center">
        <Alert sx={{ minWidth: '300px', width: '40%', justifySelf: 'center' }} severity="error">
          {myCompanyDataLoadingError?.message}
        </Alert>
      </Stack>
    );
  }

  return (
    <Stack minHeight="100%" justifyContent="flex-start" alignItems="center">
      <Typography my="64px" variant="h4" fontWeight={600}>
        Edit User
      </Typography>
      {userData && userId && myCompanyData && (
        <>
          <UserForm
            mode="edit"
            userData={userData}
            userId={Number.parseInt(userId)}
            level="company"
            companyData={myCompanyData}
          />
        </>
      )}
    </Stack>
  );
};

export default EditMyCompanyUserPage;
