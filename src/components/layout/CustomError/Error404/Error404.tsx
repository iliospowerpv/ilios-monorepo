import React from 'react';
import { useNavigate } from 'react-router-dom';
import Button from '@mui/material/Button';
import Typography from '@mui/material/Typography';
import SearchIcon from '@mui/icons-material/Search';

import { SectionStyled, iconStyles } from '../CustomError.styles';

const Error404: React.FC = () => {
  const navigate = useNavigate();

  const handleBackClick = () => {
    navigate('/dashboard');
  };

  return (
    <SectionStyled data-testid="error-404__component">
      <SearchIcon sx={iconStyles} />
      <Typography variant="h4" fontWeight="600" color="text.primary" marginBottom="16px" gutterBottom>
        Page Not Found
      </Typography>
      <Typography variant="body2" color="text.secondary" marginBottom="32px" gutterBottom>
        The page you&#39;re looking for doesn&#39;t exist or is no longer available.
      </Typography>
      <Button variant="outlined" onClick={handleBackClick}>
        Go to Dashboard
      </Button>
    </SectionStyled>
  );
};

export default Error404;
