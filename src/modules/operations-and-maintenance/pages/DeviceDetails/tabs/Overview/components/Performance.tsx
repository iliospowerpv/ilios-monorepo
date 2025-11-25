import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import { AgChartsReact } from 'ag-charts-react';
import {
  AgBarSeriesOptions,
  AgCartesianAxisOptions,
  AgCartesianChartOptions,
  AgCartesianSeriesTooltipRendererParams
} from 'ag-charts-community';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';

dayjs.extend(utc);

interface PerformanceProps {
  data: any[];
}

function tooltipRenderer({ datum, xKey, yKey }: AgCartesianSeriesTooltipRendererParams) {
  return { content: `${datum[xKey]}: ${datum[yKey]} kW` };
}
const ACTUAL: AgBarSeriesOptions = {
  type: 'bar',
  xKey: 'period',
  yKey: 'actual',
  yName: 'Actual',
  grouped: true,
  fill: '#8CD88A',
  tooltip: {
    renderer: tooltipRenderer
  }
};
const PROJECTED: AgBarSeriesOptions = {
  type: 'bar',
  xKey: 'period',
  yKey: 'projected',
  yName: 'Projected',
  grouped: true,
  fill: '#E0E0E0',
  tooltip: {
    renderer: tooltipRenderer
  }
};

export const Performance: React.FC<PerformanceProps> = ({ data }) => {
  let params: Array<any> = [];
  if (data && data.length > 0) {
    params = data.map(item => {
      const time = dayjs.utc(item.period, 'hA').valueOf();
      return {
        ...item,
        period: dayjs.utc(time).local().format('hA')
      };
    });
  }
  const chartRef = React.useRef(null);
  const options = React.useMemo<AgCartesianChartOptions>(
    () => ({
      data: params,
      series: [ACTUAL, PROJECTED],
      height: 450,
      legend: {
        position: 'bottom',
        item: {
          label: {
            fontFamily: 'Lato, sans-serif'
          },
          marker: {
            shape: 'circle'
          }
        }
      },
      axes: [
        {
          type: 'category',
          position: 'bottom',
          gridLine: {
            style: [
              {
                stroke: 'lightgray'
              }
            ]
          },
          line: {
            enabled: false
          },
          label: {
            formatter: ({ index }) => {
              if (index === 0) return '24 hrs ago';
              if (index === params.length - 1) return '1 hr ago';
              return '';
            },
            fontFamily: 'Lato, sans-serif'
          }
        },
        {
          type: 'number',
          position: 'left',
          keys: ['actual', 'projected'],
          label: {
            fontFamily: 'Lato, sans-serif'
          },
          title: {
            text: 'Energy (kW)',
            fontFamily: 'Lato, sans-serif'
          },
          gridLine: {
            style: [
              {
                stroke: 'lightgrey'
              }
            ]
          }
        }
      ] as AgCartesianAxisOptions[]
    }),
    [params]
  );

  return (
    <Box display="flex" flexDirection="column" flexGrow={1} padding="16px" border="1px solid #0000003B">
      <Typography variant="h6" mb="10px">
        Performance
      </Typography>
      <AgChartsReact ref={chartRef} options={options} />
    </Box>
  );
};

export default Performance;
