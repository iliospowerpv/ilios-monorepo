import React from 'react';
import Typography from '@mui/material/Typography';

import { SignUpScreenProps } from './types';

export const SignUpFailedScreen: React.FC<SignUpScreenProps> = ({ errorMessage, failureReason }) => (
  <>
    <Typography
      data-testid="sign_up-failed-title"
      component="h4"
      fontSize="34px"
      fontWeight={600}
      lineHeight="42px"
      textAlign="center"
      sx={{ mb: 1 }}
    >
      Failure
    </Typography>
    <Typography
      variant="body2"
      fontSize="14px"
      fontWeight={400}
      color="text.secondary"
      lineHeight="20px"
      textAlign="center"
    >
      {failureReason || ''}
    </Typography>
    <Typography
      variant="body2"
      fontSize="14px"
      fontWeight={700}
      color="text.secondary"
      lineHeight="20px"
      textAlign="center"
    >
      {errorMessage || ''}
    </Typography>
  </>
);
