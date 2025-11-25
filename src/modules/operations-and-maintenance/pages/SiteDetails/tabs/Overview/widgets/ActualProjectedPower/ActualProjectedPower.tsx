import React from 'react';
import dayjs from 'dayjs';
import { AgChartsReact } from 'ag-charts-react';
import { AgChartOptions } from 'ag-charts-community';
import { AxiosError } from 'axios';
import { useQuery } from '@tanstack/react-query';
import { WidgetWrapper } from '../../Overview.style';
import { formatFloatValue } from '../../../../../../../../utils/formatters/formatFloatValue';
import { ApiClient } from '../../../../../../../../api';

interface ActualProjectedPowerProps {
  siteId: number;
}

const ActualProjectedPower: React.FC<ActualProjectedPowerProps> = ({ siteId }) => {
  const { data, isFetching, error, refetch } = useQuery({
    queryFn: () => ApiClient.operationsAndMaintenance.siteActualVsExpectedProduction(siteId),
    queryKey: ['sites', 'actual-vs-projected-power', { siteId }],
    staleTime: 15 * 60 * 1000,
    refetchInterval: 15 * 60 * 1000
  });

  const formattedData = (data?.data ?? []).map(({ actual, expected, period }) => ({
    actual,
    expected,
    period: new Date(period)
  }));

  const options: AgChartOptions = {
    autoSize: true,
    height: 350,
    data: formattedData,
    series: [
      {
        type: 'line',
        xKey: 'period',
        yKey: 'actual',
        yName: 'Actual',
        stroke: '#20AFE3',
        strokeWidth: 2,
        marker: {
          fill: '#20AFE3',
          stroke: '#20AFE3',
          strokeWidth: 2,
          size: 0
        },
        tooltip: {
          renderer: params => {
            const { datum, xKey, yKey, title } = params;
            const content = `
              ${dayjs(datum[xKey]).format('MM/DD/YY, HH:mm:ss')}: ${formatFloatValue(datum[yKey])} (kW)`;
            return {
              title,
              content
            };
          }
        }
      },
      {
        type: 'line',
        xKey: 'period',
        yKey: 'expected',
        yName: 'Expected',
        stroke: '#E26D69',
        strokeWidth: 2,
        marker: {
          fill: '#E26D69',
          stroke: '#E26D69',
          strokeWidth: 2,
          size: 0
        },
        tooltip: {
          renderer: params => {
            const { datum, xKey, yKey, title } = params;
            const content = `
              ${dayjs(datum[xKey]).format('MM/DD/YY, HH:mm:ss')}: ${formatFloatValue(datum[yKey])} (kW)`;
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
        type: 'time',
        position: 'bottom',
        label: {
          format: '%d %b'
        },
        title: {
          text: 'Period'
        }
      },
      {
        type: 'number',
        position: 'left',
        title: {
          text: 'Kilowatts'
        }
      }
    ]
  };

  return (
    <WidgetWrapper
      title="Actual Production vs Expected"
      isLoading={isFetching}
      error={!!error}
      errorMsg={(error instanceof AxiosError && error.response?.data?.message) || error?.message}
      onClickRefetch={refetch}
    >
      <AgChartsReact options={options} />
    </WidgetWrapper>
  );
};

export default ActualProjectedPower;
