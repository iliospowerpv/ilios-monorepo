import React from 'react';
import dayjs from 'dayjs';
import Typography from '@mui/material/Typography';
import { AgChartsReact } from 'ag-charts-react';
import { AgChartOptions } from 'ag-charts-community';
import { AxiosError } from 'axios';
import { useQuery } from '@tanstack/react-query';
import { WidgetWrapper } from '../../Overview.style';
import { formatFloatValue } from '../../../../../../../../utils/formatters/formatFloatValue';
import { ApiClient } from '../../../../../../../../api';
import { useSiteLatestTelemetry } from '../../../../../../../../hooks/telemetryV2';
import { resolveExpectedState } from '../../../../../../../../utils/telemetry/expectedState';
import BaselineInvalidBanner from '../../../../../../../../components/telemetry/BaselineInvalidBanner';

interface ActualProjectedPowerProps {
  siteId: number;
}

// Render an absolute timestamp from the V2 /latest snapshot. Returns '' for a
// missing/invalid value so the caption can be hidden for non-V2 sites.
const formatWhen = (iso: string | null | undefined): string => {
  if (!iso) return '';
  const when = new Date(iso);
  return Number.isNaN(when.getTime()) ? '' : when.toLocaleString();
};

const ActualProjectedPower: React.FC<ActualProjectedPowerProps> = ({ siteId }) => {
  const { data, isFetching, error, refetch } = useQuery({
    queryFn: () => ApiClient.operationsAndMaintenance.siteActualVsExpectedProduction(siteId),
    queryKey: ['sites', 'actual-vs-projected-power', { siteId }],
    staleTime: 15 * 60 * 1000,
    refetchInterval: 15 * 60 * 1000
  });

  // Read-only freshness snapshot; empty (all-null) for non-V2 sites, in which
  // case the caption below is hidden.
  const { data: latestTelemetry } = useSiteLatestTelemetry(siteId);
  const dataAsOf = formatWhen(latestTelemetry?.latest_bucket_start);

  // `expected` is null for V2-driven points (no projected baseline); the AG line
  // series simply skips null y-values, leaving the Actual line intact.
  const formattedData = (data?.data ?? []).map(({ actual, expected, period }) => ({
    actual,
    expected,
    period: new Date(period)
  }));

  // V2 sites carry actual-only data: hide the Expected line + legend entry and
  // show an explanatory caption instead of a phantom empty series. The resolver
  // also covers partial/missing_inputs/pre_pto states via expected_state.
  const expectedState = resolveExpectedState(data);

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
        visible: expectedState.showExpected,
        showInLegend: expectedState.showExpected,
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
      {data?.baseline_invalid ? (
        <BaselineInvalidBanner
          siteId={siteId}
          invalidBaselineId={data.invalid_baseline_id}
          summary={data.baseline_validation_summary}
          requiredAction={data.required_action}
        />
      ) : (
        expectedState.reason && (
          <Typography
            variant="caption"
            color={theme => theme.palette.text.secondary}
            sx={{ display: 'block', mt: '4px' }}
          >
            {expectedState.reason}
          </Typography>
        )
      )}
      {dataAsOf && (
        <Typography
          variant="caption"
          color={theme => theme.palette.text.secondary}
          sx={{ display: 'block', mt: '4px' }}
        >
          Data as of {dataAsOf}
        </Typography>
      )}
    </WidgetWrapper>
  );
};

export default ActualProjectedPower;
