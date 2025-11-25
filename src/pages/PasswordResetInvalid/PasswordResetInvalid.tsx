import React from 'react';
import Button from '@mui/material/Button';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { useNavigate } from 'react-router-dom';

const PasswordResetInvalid: React.FC = () => {
  const navigate = useNavigate();

  const handleBackBtnClick = () => {
    navigate('/forgot-password');
  };

  return (
    <>
      <Typography
        data-testid="reset__password-reset-invalid-title"
        component="h4"
        fontSize="34px"
        fontWeight={600}
        lineHeight="42px"
        textAlign="center"
        sx={{ mb: 2 }}
      >
        Invalid Password Reset Link
      </Typography>
      <Typography variant="body2" fontSize="14px" color="text.secondary" lineHeight="20px" textAlign="center">
        The password reset link is invalid, possibly because it was already used or expired. Please return to the
        password recovery page to request a new link.
      </Typography>
      <Box>
        <Button
          type="submit"
          fullWidth
          variant="contained"
          data-testid="reset_back-btn"
          onClick={handleBackBtnClick}
          sx={{ my: 2 }}
        >
          Back to Password Recovery
        </Button>
      </Box>
    </>
  );
};

export default PasswordResetInvalid;
