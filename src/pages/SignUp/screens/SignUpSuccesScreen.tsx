import React from 'react';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { useNavigate } from 'react-router-dom';

import type { SignUpScreenProps } from './types';

export const SignUpSuccesScreen: React.FC<SignUpScreenProps> = () => {
  const navigate = useNavigate();

  const handleBackBtnClick = () => {
    navigate('/login');
  };

  return (
    <>
      <Typography
        data-testid="sign_up-success-title"
        component="h4"
        fontSize="34px"
        fontWeight={600}
        lineHeight="42px"
        textAlign="center"
        sx={{ mb: 2 }}
      >
        Success
      </Typography>
      <Typography variant="body2" fontSize="14px" color="text.secondary" lineHeight="20px" textAlign="center">
        Your password has been changed.
      </Typography>
      <Box>
        <Button
          type="submit"
          fullWidth
          variant="contained"
          data-testid="sign-up_back-btn"
          onClick={handleBackBtnClick}
          sx={{ my: 2 }}
        >
          Back to Sign In
        </Button>
      </Box>
    </>
  );
};
