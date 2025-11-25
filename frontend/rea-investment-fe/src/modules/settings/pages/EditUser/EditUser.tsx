import * as React from 'react';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import Alert from '@mui/material/Alert';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { ApiClient } from '../../../../api';
import { UserForm } from '../../../../components/forms/UserForm/UserForm';

export const EditUserPage: React.FC = () => {
  const { id: userId } = useParams();
  const isValidId = !!userId && Number.isSafeInteger(Number.parseInt(userId));

  const {
    data: userData,
    isLoading: isLoadingUserData,
    error: userDataLoadingError
  } = useQuery({
    queryFn: async () => {
      const id = isValidId ? Number.parseInt(userId) : -1;
      return ApiClient.user.getById(id);
    },
    queryKey: ['users', { userId }],
    enabled: isValidId
  });

  if (isLoadingUserData) return null;

  return (
    <Stack minHeight="100%" justifyContent="flex-start" alignItems="center">
      <Typography my="64px" variant="h4" fontWeight={600} data-testid="edit-user__form-title">
        Edit User
      </Typography>
      {(userDataLoadingError || !isValidId) && (
        <Alert sx={{ minWidth: '300px', width: '40%', justifySelf: 'center' }} severity="error">
          {userDataLoadingError?.message || `Provided userId "${userId}" is invalid.`}
        </Alert>
      )}
      {!userDataLoadingError && userData && isValidId && (
        <>
          <UserForm mode="edit" userData={userData} userId={Number.parseInt(userId)} />
        </>
      )}
    </Stack>
  );
};

export default EditUserPage;
