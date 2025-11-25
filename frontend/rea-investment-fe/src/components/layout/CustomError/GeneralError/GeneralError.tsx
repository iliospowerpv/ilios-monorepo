import React from 'react';
import WarningIcon from '@mui/icons-material/Warning';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';

import { SectionStyled, iconStyles } from '../CustomError.styles';

const GeneralError: React.FC<{ message?: string }> = ({ message }) => {
  const handleReload = () => {
    window.location.reload();
  };

  return (
    <SectionStyled data-testid="general-error__component">
      <WarningIcon sx={iconStyles} />
      <Typography variant="h4" fontWeight="600" color="text.primary" marginBottom="16px" gutterBottom>
        {message ? message : 'Something Went Wrong'}
      </Typography>
      <Typography variant="body2" color="text.secondary" marginBottom="32px" gutterBottom>
        Please reload the page or try again later.
      </Typography>
      <Button variant="outlined" onClick={handleReload}>
        Reload page
      </Button>
    </SectionStyled>
  );
};

export default GeneralError;
