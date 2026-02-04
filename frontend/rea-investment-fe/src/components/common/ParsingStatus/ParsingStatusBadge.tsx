import React from 'react';
import Chip from '@mui/material/Chip';
import CircularProgress from '@mui/material/CircularProgress';
import Box from '@mui/material/Box';
import { getStatusDisplayInfo, ParsingStatus } from '../../../utils/parsing';

interface ParsingStatusBadgeProps {
  status: ParsingStatus | string;
  size?: 'small' | 'medium';
}

const ParsingStatusBadge: React.FC<ParsingStatusBadgeProps> = ({ status, size = 'small' }) => {
  const { label, color, isLoading } = getStatusDisplayInfo(status);

  return (
    <Chip
      size={size}
      color={color}
      label={
        <Box display="flex" alignItems="center" gap={1}>
          {isLoading && <CircularProgress size={12} color="inherit" />}
          {label}
        </Box>
      }
      sx={{
        fontWeight: 500,
        fontSize: size === 'small' ? '12px' : '14px'
      }}
    />
  );
};

export default ParsingStatusBadge;
