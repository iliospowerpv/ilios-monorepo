import * as React from 'react';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { CompanyForm } from '../../../../components/forms/CompanyForm/CompanyForm';

export const AddCompanyPage: React.FC = () => (
  <Stack minHeight="100%" justifyContent="flex-start" alignItems="center">
    <Typography my="64px" variant="h4" fontWeight={600} data-testid="add-company__form-title">
      Add Company
    </Typography>
    <CompanyForm mode="add" />
  </Stack>
);

export default AddCompanyPage;
