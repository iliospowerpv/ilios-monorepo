import React from 'react';
import { useNavigate } from 'react-router-dom';
import LockIcon from '@mui/icons-material/Lock';
import Typography from '@mui/material/Typography';
import Button from '@mui/material/Button';

import { SectionStyled, iconStyles } from '../CustomError.styles';

const Error403: React.FC = () => {
  const navigate = useNavigate();

  const handleBackClick = () => {
    navigate('/dashboard');
  };

  return (
    <SectionStyled data-testid="error-403__component">
      <LockIcon sx={iconStyles} />
      <Typography variant="h4" fontWeight="600" color="text.primary" marginBottom="16px" gutterBottom>
        Access Denied
      </Typography>
      <Typography variant="body2" color="text.secondary" marginBottom="32px" gutterBottom>
        You don’t have permission to view this page. Please contact your administrator to request access.
      </Typography>
      <Button variant="outlined" onClick={handleBackClick}>
        Go to Dashboard
      </Button>
    </SectionStyled>
  );
};

export default Error403;
