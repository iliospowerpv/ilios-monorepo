import React from 'react';
import { styled } from '@mui/material/styles';
import Box from '@mui/material/Box';
import LinearProgress, { linearProgressClasses, LinearProgressProps } from '@mui/material/LinearProgress';

interface BorderLinearProgressProps extends LinearProgressProps {
  beyondTheRange?: boolean;
}

const BorderLinearProgress = styled(LinearProgress, {
  shouldForwardProp: prop => prop !== 'beyondTheRange'
})<BorderLinearProgressProps>(({ theme, beyondTheRange, value }) => {
  const { efficiencyColors } = theme;
  const progress = typeof value === 'number' ? value : 0;

  const deriveProgressBarColorFromValue = (progress: number): string => {
    if (progress < 51) return efficiencyColors.low;
    if (progress < 90) return efficiencyColors.mediocre;
    return efficiencyColors.good;
  };

  return {
    height: '20px',
    borderRadius: 2,
    [`&.${linearProgressClasses.colorPrimary}`]: {
      backgroundColor: 'rgba(64, 66, 81, 0.08)'
    },
    [`& .${linearProgressClasses.bar}`]: {
      borderRadius: 0,
      backgroundColor: beyondTheRange ? efficiencyColors.outstanding : deriveProgressBarColorFromValue(progress)
    }
  };
});

interface EfficiencyRateBarProps {
  percentage: number;
}

export const EfficiencyRateBar: React.FC<EfficiencyRateBarProps> = ({ percentage: value }) => {
  const isValueOutOfRange = value > 100;

  return (
    <Box display="inline-flex" flexGrow={1} sx={{ '& > span': { width: '60px', px: '12px', textAlign: 'center' } }}>
      <Box flexGrow={1} my="auto">
        <BorderLinearProgress
          variant="determinate"
          value={isValueOutOfRange ? 100 : value}
          beyondTheRange={isValueOutOfRange}
        />
      </Box>
      <span>{value}%</span>
    </Box>
  );
};

export default EfficiencyRateBar;
