import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import Grid from '@mui/material/Grid';
import { AgChartsReact } from 'ag-charts-react';
import { AgChartOptions } from 'ag-charts-community';
import { WidgetWrapper } from '../../Overview.style';
import { useQuery } from '@tanstack/react-query';
import { ApiClient } from '../../../../../../../../api';
import { formatFloatValue } from '../../../../../../../../utils/formatters/formatFloatValue';
import { resolveExpectedState } from '../../../../../../../../utils/telemetry/expectedState';

interface LossesProps {
  companyId: number;
}

const Losses: React.FC<LossesProps> = ({ companyId }) => {
  const { data, isFetching, error, refetch } = useQuery({
    queryFn: () => ApiClient.operationsAndMaintenance.companyLosesData(companyId),
    queryKey: ['companies', 'loses-data', { companyId }],
    refetchInterval: 15 * 60 * 1000
  });

  // V2 companies report actual cumulative energy only; expected/loss are null
  // because there is no baseline, so we show the cumulative figure plus a note
  // instead of a stacked expected/loss chart with fabricated zeros. Partial
  // rollups also carry null expected/loss, so we gate on real numbers below.
  const expectedState = resolveExpectedState(data);
  const { cumulative = 0 } = data || {};
  const expected = data?.expected ?? 0;
  const loss = data?.loss ?? 0;
  const canPlotExpected =
    expectedState.showExpected && typeof data?.expected === 'number' && typeof data?.loss === 'number';

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
            ) : !canPlotExpected ? (
              <Box textAlign="center" marginY="50px">
                <Typography variant="h6" fontWeight={700} fontSize={28} lineHeight="40px">
                  {formatFloatValue(cumulative ?? 0)}
                </Typography>
                <Typography variant="caption" color={theme => theme.palette.text.secondary}>
                  Cumulative actual production today (kWh)
                </Typography>
                <Typography variant="body2" marginTop="16px" color={theme => theme.palette.text.secondary}>
                  {expectedState.reason || 'Expected production and loss cannot be calculated for this company yet.'}
                </Typography>
              </Box>
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
