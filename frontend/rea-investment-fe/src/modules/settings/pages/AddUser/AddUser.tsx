import * as React from 'react';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { UserForm } from '../../../../components/forms/UserForm/UserForm';

export const AddUserPage: React.FC = () => (
  <Stack minHeight="100%" justifyContent="flex-start" alignItems="center">
    <Typography my="64px" variant="h4" fontWeight={600}>
      Add User
    </Typography>
    <UserForm mode="add" />
  </Stack>
);

export default AddUserPage;
