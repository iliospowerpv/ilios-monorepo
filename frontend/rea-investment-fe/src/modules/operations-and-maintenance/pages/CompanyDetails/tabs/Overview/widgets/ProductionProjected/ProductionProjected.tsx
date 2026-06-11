import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { AgChartOptions } from 'ag-charts-community';
import { AgChartsReact } from 'ag-charts-react';
import { useQuery } from '@tanstack/react-query';
import { WidgetWrapper } from '../../Overview.style';
import { formatFloatValue } from '../../../../../../../../utils/formatters/formatFloatValue';
import { ApiClient } from '../../../../../../../../api';
import { resolveExpectedState } from '../../../../../../../../utils/telemetry/expectedState';

interface InfoBoxProps {
  companyId: number;
}

const ActualProductionVsProjected: React.FC<InfoBoxProps> = ({ companyId }) => {
  const { data, isFetching, error, refetch } = useQuery({
    queryFn: () => ApiClient.operationsAndMaintenance.companyActualVsExpectedProductionData(companyId),
    queryKey: ['companies', 'actual-vs-expected-production-data', { companyId }],
    refetchInterval: 15 * 60 * 1000
  });

  // V2 companies have no expected baseline, so an actual-vs-expected bubble chart
  // is not meaningful; show a reason note instead of plotting every site at
  // expected = 0. Partial rollups also carry null per-site expected, so the
  // bubble chart is only plotted when the state is fully `available`.
  const expectedState = resolveExpectedState(data);

  const options: AgChartOptions = {
    autoSize: true,
    height: 350,
    series: [
      {
        type: 'bubble',
        title: 'Energy',
        data: data ? data.items : undefined,
        xKey: 'expected_kw',
        xName: 'Expected Energy (kW)',
        yKey: 'actual_kw',
        yName: 'Actual Energy (kW)',
        sizeKey: '',
        sizeName: '',
        labelKey: 'name',
        labelName: 'Name',
        marker: {
          size: 20
        },
        label: {
          enabled: true
        },
        tooltip: {
          renderer: params => {
            const { datum, xKey, yKey, xName, yName, title, labelName, labelKey } = params;
            const content = `
              <b>${labelName}: </b>${datum[labelKey || ''] ?? ''}<br />
              <b>${xName}: </b>${formatFloatValue(datum[xKey])}<br />
              <b>${yName}: </b>${formatFloatValue(datum[yKey])}`;
            return {
              title,
              content
            };
          }
        }
      }
    ],
    axes: [
      {
        type: 'number',
        position: 'bottom',
        title: {
          text: 'Expected Energy (kW)'
        },
        label: {
          formatter: params => `${params.value}`
        }
      },
      {
        type: 'number',
        position: 'left',
        title: {
          text: 'Actual Energy (kW)'
        },
        label: {
          formatter: params => `${params.value}`
        }
      }
    ]
  };

  return (
    <WidgetWrapper
      title="Actual Production vs Expected"
      isLoading={isFetching}
      onClickRefetch={refetch}
      error={!!error}
      errorMsg={error?.message}
    >
      {data && expectedState.state !== 'available' ? (
        <Box display="flex" alignItems="center" justifyContent="center" minHeight={350}>
          <Typography variant="body1" textAlign="center" width="70%" color={theme => theme.palette.text.secondary}>
            {expectedState.reason || 'Projected production has not been configured for this company yet.'}
          </Typography>
        </Box>
      ) : (
        <AgChartsReact options={options} />
      )}
    </WidgetWrapper>
  );
};

export default ActualProductionVsProjected;
