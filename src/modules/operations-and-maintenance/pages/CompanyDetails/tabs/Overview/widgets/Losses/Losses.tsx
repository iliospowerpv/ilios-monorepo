import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Grid from '@mui/material/Grid';
import { AgChartsReact } from 'ag-charts-react';
import { AgChartOptions } from 'ag-charts-community';
import { WidgetWrapper } from '../../Overview.style';
import { useQuery } from '@tanstack/react-query';
import { ApiClient } from '../../../../../../../../api';

interface LossesProps {
  companyId: number;
}

const Losses: React.FC<LossesProps> = ({ companyId }) => {
  const { data, isFetching, error, refetch } = useQuery({
    queryFn: () => ApiClient.operationsAndMaintenance.companyLosesData(companyId),
    queryKey: ['companies', 'loses-data', { companyId }],
    refetchInterval: 15 * 60 * 1000
  });

  const { cumulative = 0, expected = 0, loss = 0 } = data || {};

  const options: AgChartOptions = {
    autoSize: true,
    height: 350,
    data: [
      {
        expected: expected,
        cumulative: cumulative,
        loss: loss
      }
    ],
    series: [
      {
        type: 'bar',
        xKey: '',
        yKey: 'expected',
        yName: 'Expected (kWh)',
        stackGroup: 'Expected',
        fill: '#E0E0E0',
        tooltip: {
          renderer: params => {
            return {
              content: `Expected: ${params.datum.expected}`
            };
          }
        }
      },
      {
        type: 'bar',
        xKey: '',
        yKey: 'cumulative',
        yName: 'Cumulative (kWh)',
        stackGroup: 'Other',
        fill: '#8CD88A',
        tooltip: {
          renderer: params => {
            return {
              content: `Cumulative: ${params.datum.cumulative}`
            };
          }
        }
      },
      {
        type: 'bar',
        xKey: '',
        yKey: 'loss',
        yName: 'Energy loss (kWh)',
        stackGroup: 'Other',
        fill: '#F1B8B6',
        tooltip: {
          renderer: params => {
            return {
              content: `Energy loss: ${params.datum.loss}`
            };
          }
        }
      }
    ],
    axes: [
      {
        type: 'number',
        position: 'left'
      },
      {
        type: 'category',
        position: 'bottom',
        label: {
          enabled: false
        }
      }
    ],
    legend: {
      maxHeight: 70,
      position: 'right',
      item: {
        marker: {
          shape: 'circle'
        }
      }
    }
  };

  return (
    <WidgetWrapper
      title="Display Losses for a Day"
      isLoading={isFetching}
      onClickRefetch={refetch}
      error={!!error}
      errorMsg={error?.message}
    >
      <Box display="flex" flexDirection="row" flexGrow={1}>
        <Grid container spacing={1}>
          <Grid item xs={12} md={12}>
            {!data ? (
              <Typography
                variant="h6"
                fontWeight={500}
                fontSize={20}
                lineHeight="32px"
                textAlign="center"
                marginY="70px"
              >
                No Losses Today
              </Typography>
            ) : (
              <AgChartsReact options={options} />
            )}
          </Grid>
        </Grid>
      </Box>
    </WidgetWrapper>
  );
};

export default Losses;
