import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { AxiosError } from 'axios';
import { styled } from '@mui/material/styles';
import Box from '@mui/material/Box';
import LinearProgress, { linearProgressClasses, LinearProgressProps } from '@mui/material/LinearProgress';
import { WidgetWrapper } from '../../Overview.style';
import dayjs from 'dayjs';
import { ApiClient } from '../../../../../../../../api';

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

interface PastPerformanceProps {
  siteId: number;
}

export const PastPerformance: React.FC<PastPerformanceProps> = ({ siteId }) => {
  const {
    data: { data } = {},
    isFetching,
    error,
    refetch
  } = useQuery({
    queryFn: () => ApiClient.operationsAndMaintenance.sitePastPerformance(siteId),
    queryKey: ['sites', 'past-performance', { siteId }],
    staleTime: 15 * 60 * 1000,
    refetchInterval: 15 * 60 * 1000
  });

  const entries = typeof data === 'object' && data !== null ? Object.entries(data) : [];
  const isValueOutOfRange = (value: number) => value > 100;
  const formatDate = (date: string) => {
    return dayjs(date).format('DD MMM');
  };

  return (
    <WidgetWrapper
      title="Past Performance"
      isLoading={isFetching}
      error={!!error}
      errorMsg={(error instanceof AxiosError && error.response?.data?.message) || error?.message}
      onClickRefetch={refetch}
    >
      <Box display="flex" flexDirection="column" flexGrow="1" height="100%">
        {entries.map(item => (
          <Box
            key={item[0]}
            sx={{
              display: 'inline-flex',
              flexGrow: 1,
              alignItems: 'center',
              '& > span': { width: '75px', px: '8px', textAlign: 'center' }
            }}
          >
            <span>{formatDate(item[0])}</span>
            <Box flexGrow={1} my="auto">
              <BorderLinearProgress
                variant="determinate"
                value={isValueOutOfRange(item[1]) ? 100 : item[1]}
                beyondTheRange={isValueOutOfRange(item[1])}
              />
            </Box>
            <span>{item[1]}%</span>
          </Box>
        ))}
      </Box>
    </WidgetWrapper>
  );
};

export default PastPerformance;
