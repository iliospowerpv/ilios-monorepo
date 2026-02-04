import React from 'react';
import Alert from '@mui/material/Alert';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import { formatCharCount } from '../../../utils/parsing';

interface TruncationWarningProps {
  wasTruncated: boolean;
  truncatedCharCount?: number;
  charCount?: number;
  pageCount?: number;
}

const TruncationWarning: React.FC<TruncationWarningProps> = ({
  wasTruncated,
  truncatedCharCount,
  charCount,
  pageCount,
}) => {
  if (!wasTruncated) return null;

  return (
    <Alert severity="warning" sx={{ mb: 2 }}>
      <Typography variant="body2">
        This document is long. Analysis was performed on the first{' '}
        {charCount ? formatCharCount(charCount) : 'portion of'} characters.
        {truncatedCharCount && truncatedCharCount > 0 && (
          <> ({formatCharCount(truncatedCharCount)} characters were not analyzed.)</>
        )}
      </Typography>
    </Alert>
  );
};

export default TruncationWarning;
