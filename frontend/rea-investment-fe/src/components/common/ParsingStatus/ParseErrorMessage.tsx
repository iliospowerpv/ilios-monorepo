import React from 'react';
import Alert from '@mui/material/Alert';
import AlertTitle from '@mui/material/AlertTitle';
import Box from '@mui/material/Box';
import { extractReasonCode, getErrorMessageForReasonCode } from '../../../utils/parsing';

interface ParseErrorMessageProps {
  errorMessage?: string;
  onRetry?: () => void;
}

const ParseErrorMessage: React.FC<ParseErrorMessageProps> = ({ errorMessage, onRetry }) => {
  const reasonCode = extractReasonCode(errorMessage);
  const userFriendlyMessage = getErrorMessageForReasonCode(reasonCode);

  return (
    <Alert 
      severity="error" 
      sx={{ mb: 2 }}
      action={
        onRetry && (
          <Box
            component="span"
            sx={{
              cursor: 'pointer',
              textDecoration: 'underline',
              fontSize: '14px',
              '&:hover': { opacity: 0.8 },
            }}
            onClick={onRetry}
          >
            Retry
          </Box>
        )
      }
    >
      <AlertTitle>Parsing Failed</AlertTitle>
      {userFriendlyMessage}
    </Alert>
  );
};

export default ParseErrorMessage;
