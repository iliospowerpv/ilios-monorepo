import React from 'react';
import Box from '@mui/material/Box';
import Typography from '@mui/material/Typography';
import CircularProgress from '@mui/material/CircularProgress';
import { useQuery } from '@tanstack/react-query';
import { AgChartsReact } from 'ag-charts-react';
import {
  AgBarSeriesOptions,
  AgCartesianAxisOptions,
  AgCartesianChartOptions,
  AgCartesianSeriesTooltipRendererParams
} from 'ag-charts-community';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';

import { ApiClient } from '../../../../../../../../api';
import type { TelemetrySeriesPoint } from '../../../../../../../../types/telemetryV2';

dayjs.extend(utc);

/**
 * Normalized V2 metric for a single device's average AC power. Mirrors the
 * server-side `DEVICE_POWER_METRIC` (`device_power_ac_kw`) read by the O&M
 * charts. This is the ONLY series this card renders — it is actual-only.
 */
export const DEVICE_POWER_METRIC = 'device_power_ac_kw';

/** Hourly rollup bucket — matches the legacy hourly device series. */
export const PERFORMANCE_BUCKET_SIZE = '1h';

/** Rolling window the card shows. */
export const PERFORMANCE_WINDOW_HOURS = 24;

/** A single actual-only bar in the device performance chart. */
export interface DevicePerformanceRow {
  /** Local, human-readable bucket label (also the category-axis key). */
  period: string;
  /** Actual average AC power for the bucket; always a real reading value. */
  actual: number;
}

/**
 * Map raw V2 rollup points into actual-only chart rows.
 *
 * `bucket_start` is stored naive-UTC (no timezone suffix); we parse it with
 * `dayjs.utc` so the instant is interpreted as UTC and then converted to the
 * viewer's local time for display. Only the buckets the backend actually
 * returned are mapped — missing buckets are NEVER back-filled with a fabricated
 * 0, and no projected/expected value is ever synthesized.
 */
export const buildDevicePerformanceRows = (
  points: TelemetrySeriesPoint[] | undefined | null
): DevicePerformanceRow[] => {
  if (!points || points.length === 0) return [];
  return points.map(point => ({
    period: dayjs.utc(point.bucket_start).local().format('MMM D, h A'),
    actual: point.value
  }));
};

function tooltipRenderer(unit: string) {
  return ({ datum, xKey, yKey }: AgCartesianSeriesTooltipRendererParams) => ({
    content: `${datum[xKey]}: ${datum[yKey]} ${unit}`
  });
}

interface DevicePerformanceCardProps {
  siteId: number;
  deviceId: number;
}

/**
 * Project Hub Device Details "Performance" card.
 *
 * Renders the device's last-24h actual AC power from V2-native PostgreSQL
 * rollups as actual-only green bars. There is intentionally no projected /
 * expected series: per-device expected baselines are not defined, so we show an
 * honest caption rather than a fabricated 0 or a misleading projected line.
 * When the device has no readings for the window we render an explicit
 * "unavailable" message instead of an empty/zeroed chart.
 */
export const DevicePerformanceCard: React.FC<DevicePerformanceCardProps> = ({ siteId, deviceId }) => {
  const { data, isLoading, isError } = useQuery({
    queryKey: ['telemetry', 'v2', 'device-series', { siteId, deviceId, metric: DEVICE_POWER_METRIC }],
    queryFn: () => {
      const to = dayjs();
      const from = to.subtract(PERFORMANCE_WINDOW_HOURS, 'hour');
      return ApiClient.telemetryV2.getSiteDeviceRollupSeries(siteId, {
        deviceId,
        metric: DEVICE_POWER_METRIC,
        bucketSize: PERFORMANCE_BUCKET_SIZE,
        from: from.toISOString(),
        to: to.toISOString()
      });
    }
  });

  const deviceSeries = data?.devices?.[0];
  const unit = deviceSeries?.unit ?? 'kW';
  const rows = React.useMemo(() => buildDevicePerformanceRows(deviceSeries?.points), [deviceSeries]);

  const actualSeries = React.useMemo<AgBarSeriesOptions>(
    () => ({
      type: 'bar',
      xKey: 'period',
      yKey: 'actual',
      yName: 'Actual',
      fill: '#8CD88A',
      tooltip: { renderer: tooltipRenderer(unit) }
    }),
    [unit]
  );

  const options = React.useMemo<AgCartesianChartOptions>(
    () => ({
      data: rows,
      series: [actualSeries],
      height: 320,
      legend: { enabled: false },
      axes: [
        {
          type: 'category',
          position: 'bottom',
          gridLine: { style: [{ stroke: 'lightgray' }] },
          line: { enabled: false },
          label: { fontFamily: 'Lato, sans-serif', rotation: -30 }
        },
        {
          type: 'number',
          position: 'left',
          keys: ['actual'],
          label: { fontFamily: 'Lato, sans-serif' },
          title: { text: `AC Power (${unit})`, fontFamily: 'Lato, sans-serif' },
          gridLine: { style: [{ stroke: 'lightgrey' }] }
        }
      ] as AgCartesianAxisOptions[]
    }),
    [rows, actualSeries, unit]
  );

  return (
    <Box
      display="flex"
      flexDirection="column"
      flexGrow={1}
      padding="16px"
      sx={{ border: theme => `1px solid ${theme.palette.divider}` }}
    >
      <Typography variant="h6" mb="2px">
        Performance
      </Typography>
      <Typography variant="caption" color={theme => theme.palette.text.secondary} mb="12px">
        Last 24 hours · actual AC power (hourly)
      </Typography>

      {isLoading && (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="240px">
          <CircularProgress />
        </Box>
      )}

      {!isLoading && isError && (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="240px" px="16px">
          <Typography variant="body2" textAlign="center" color={theme => theme.palette.text.secondary}>
            Unable to load telemetry for this device right now.
          </Typography>
        </Box>
      )}

      {!isLoading && !isError && rows.length === 0 && (
        <Box display="flex" justifyContent="center" alignItems="center" minHeight="240px" px="16px">
          <Typography variant="body2" textAlign="center" color={theme => theme.palette.text.secondary}>
            No V2 telemetry readings for this device or the last 24 hours.
          </Typography>
        </Box>
      )}

      {!isLoading && !isError && rows.length > 0 && <AgChartsReact options={options} />}

      <Typography variant="caption" color={theme => theme.palette.text.secondary} mt="12px">
        Projected unavailable: per-device expected baseline is not defined.
      </Typography>
    </Box>
  );
};

export default DevicePerformanceCard;
