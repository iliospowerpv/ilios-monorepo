import React from 'react';
import Button from '@mui/material/Button';
import Link from '@mui/material/Link';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { useNavigate, useLocation } from 'react-router-dom';
import { AxiosError } from 'axios';
import { useResetRequest } from '../../hooks/reset-request/reset-request';

const PasswordResetNotification: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const { mutation } = useResetRequest();
  const { email } = location.state || {};

  const handleBackBtnClick = () => {
    navigate('/login');
  };

  const handleResendBtnClick = () => {
    mutation.mutate({ email });
  };

  return (
    <>
      <Typography
        data-testid="reset__password-reset-notification-title"
        component="h4"
        fontSize="34px"
        fontWeight={600}
        lineHeight="42px"
        textAlign="center"
        sx={{ mb: 2 }}
      >
        Reset your Password
      </Typography>
      <Typography variant="body2" fontSize="14px" color="text.secondary" lineHeight="20px" textAlign="center">
        We&apos;ve sent instructions to {email}. If you didn&apos;t get the email, ask to resend the instructions.
      </Typography>
      <br />
      <Typography variant="body2" fontSize="14px" color="text.secondary" lineHeight="20px" textAlign="center">
        If you still haven&apos;t received the email, please contact:{` `}
        <Link href="mailto:support@iliospower.com" target="_blank" rel="noopener noreferrer">
          support@iliospower.com
        </Link>
        .
      </Typography>
      <Box>
        <Button
          type="submit"
          fullWidth
          variant="outlined"
          data-testid="reset_back-btn"
          onClick={handleBackBtnClick}
          sx={{ my: 2 }}
        >
          Back to Sign In
        </Button>
        {mutation.error && (
          <Typography variant="caption" sx={{ color: 'error.main', display: 'block', margin: '3px 14px 0' }}>
            {(mutation.error instanceof AxiosError && mutation.error.response?.data?.message) || mutation.error.message}
          </Typography>
        )}
        <Box sx={{ textAlign: 'center' }}>
          <Link component="button" variant="body2" onClick={handleResendBtnClick}>
            Resend the Instruction
          </Link>
        </Box>
      </Box>
    </>
  );
};

export default PasswordResetNotification;
