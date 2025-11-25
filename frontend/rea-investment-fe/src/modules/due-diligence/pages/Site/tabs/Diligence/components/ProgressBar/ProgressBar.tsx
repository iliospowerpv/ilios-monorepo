import React from 'react';
import LinearProgress, { linearProgressClasses } from '@mui/material/LinearProgress';
import Typography from '@mui/material/Typography';
import Box from '@mui/material/Box';
import { styled } from '@mui/material/styles';

interface ProgressBarProps {
  value: number;
}

const StyledLinearProgress = styled(LinearProgress)(() => ({
  [`&.${linearProgressClasses.colorPrimary}`]: {
    backgroundColor: '#CEEFCD'
  },
  [`& .${linearProgressClasses.bar}`]: {
    backgroundColor: '#83D681'
  }
}));

export const ProgressBar: React.FC<ProgressBarProps> = ({ value }) => (
  <Box sx={{ display: 'flex', alignItems: 'center' }} data-testid="progress-bar__component">
    <Box sx={{ width: '100%', mr: 1 }}>
      <StyledLinearProgress variant="determinate" value={value} />
    </Box>
    <Box sx={{ minWidth: 35 }}>
      <Typography variant="body2" color="text.secondary">{`${Math.round(value)}%`}</Typography>
    </Box>
  </Box>
);

export default ProgressBar;
