import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { useQuery } from '@tanstack/react-query';
import { styled, useTheme } from '@mui/material/styles';
import { WidgetWrapper } from '../../Overview.style';
import { ApiClient } from '../../../../../../../../api';
import { BootstrapTooltip } from '../../../../../../../../components/common/BootstrapTooltip/BootstrapTooltip';
import { AxiosError } from 'axios';

interface InvertersPerformanceProps {
  siteId: number;
}

interface ItemProps {
  color: string;
}

const Item = styled(Box)<ItemProps>(({ theme, color }) => ({
  width: 65,
  height: 48,
  fontSize: '12px',
  color: theme.palette.text.primary,
  backgroundColor: color,
  justifyContent: 'center',
  alignItems: 'center',
  padding: theme.spacing(0.5),
  animation: 'grow 0.5s ease-out',
  cursor: 'default',
  '@keyframes grow': {
    '0%': {
      transform: 'scale(0.5)'
    },
    '100%': {
      transform: 'scale(1)'
    }
  }
}));

export const InvertersPerformance: React.FC<InvertersPerformanceProps> = ({ siteId }) => {
  const theme = useTheme();

  const { data, isFetching, error, refetch } = useQuery({
    queryFn: () => ApiClient.operationsAndMaintenance.siteInvertersPerformanceData(siteId),
    queryKey: ['sites', 'inverters-performance', { siteId }],
    staleTime: 15 * 60 * 1000,
    refetchInterval: 15 * 60 * 1000
  });

  const derivePerformanceColorFromValue = (): string => {
    return theme.efficiencyColors.none;
  };

  return (
    <WidgetWrapper
      title="Inverters Actual Production"
      isLoading={isFetching}
      error={!!error}
      errorMsg={(error instanceof AxiosError && error.response?.data?.message) || error?.message}
      onClickRefetch={refetch}
      noData={!data || !data.data.length}
    >
      <Box
        sx={{
          display: 'flex',
          flexWrap: 'wrap',
          justifyContent: 'left',
          paddingY: theme.spacing(1),
          gap: '10px'
        }}
      >
        {data?.data.map(({ name, actual }) => (
          <BootstrapTooltip key={name} title={name} placement="top">
            <Item color={derivePerformanceColorFromValue()}>
              <Typography
                variant="body2"
                sx={{
                  fontSize: '12px',
                  fontWeight: 500,
                  display: 'block',
                  marginTop: '2px',
                  overflow: 'hidden',
                  whiteSpace: 'nowrap',
                  textOverflow: 'ellipsis'
                }}
              >
                {name}
              </Typography>
              <Typography
                variant="body2"
                sx={{
                  fontSize: '12px',
                  fontWeight: 500,
                  display: 'block',
                  marginTop: '2px'
                }}
              >
                {actual}
              </Typography>
            </Item>
          </BootstrapTooltip>
        ))}
      </Box>
    </WidgetWrapper>
  );
};

export default InvertersPerformance;
