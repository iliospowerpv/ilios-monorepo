import * as React from 'react';
import Alert from '@mui/material/Alert';
import Stack from '@mui/material/Stack';
import Typography from '@mui/material/Typography';
import { useParams } from 'react-router-dom';
import { SiteForm } from '../../../../components/forms/SiteForm/SiteForm';

export const AddSitePage: React.FC = () => {
  const { companyId } = useParams();
  const isValidId = !!companyId && Number.isSafeInteger(Number.parseInt(companyId));

  return (
    <Stack minHeight="100%" justifyContent="flex-start" alignItems="center">
      <Typography my="64px" variant="h4" fontWeight={600} data-testid="add-site__form-title">
        Add Site
      </Typography>
      {!isValidId && (
        <Alert sx={{ minWidth: '300px', width: '40%', justifySelf: 'center' }} severity="error">
          {`Provided companyId "${companyId}" is invalid.`}
        </Alert>
      )}
      {isValidId && (
        <>
          <SiteForm mode="add" companyId={Number.parseInt(companyId)} />
        </>
      )}
    </Stack>
  );
};

export default AddSitePage;
