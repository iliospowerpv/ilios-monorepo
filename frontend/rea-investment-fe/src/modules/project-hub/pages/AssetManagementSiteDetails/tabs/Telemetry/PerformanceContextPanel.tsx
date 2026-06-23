import React, { useMemo, useState } from 'react';
import { Link as RouterLink } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Grid from '@mui/material/Grid';
import Typography from '@mui/material/Typography';
import Chip from '@mui/material/Chip';
import type { ChipProps } from '@mui/material/Chip';
import Alert from '@mui/material/Alert';
import Button from '@mui/material/Button';
import Divider from '@mui/material/Divider';
import Tooltip from '@mui/material/Tooltip';
import CircularProgress from '@mui/material/CircularProgress';
import ToggleButton from '@mui/material/ToggleButton';
import ToggleButtonGroup from '@mui/material/ToggleButtonGroup';
import InsightsIcon from '@mui/icons-material/Insights';
import OpenInNewIcon from '@mui/icons-material/OpenInNew';
import { AgChartsReact } from 'ag-charts-react';
import {
  AgBarSeriesOptions,
  AgCartesianAxisOptions,
  AgCartesianChartOptions,
  AgCartesianSeriesTooltipRendererParams
} from 'ag-charts-community';
import dayjs from 'dayjs';
import utc from 'dayjs/plugin/utc';

import { ApiClient } from '../../../../../../api';
import type {
  PerformanceContextPoint,
  PerformanceContextResponse,
  PerformanceTempUnit,
  PerformanceWindowPreset,
  TelemetryBucketSize
} from '../../../../../../types/telemetryV2';

dayjs.extend(utc);

const WINDOW_OPTIONS: { value: PerformanceWindowPreset; label: string }[] = [
  { value: 'today', label: 'Today' },
  { value: '24h', label: '24h' },
  { value: '7d', label: '7d' },
  { value: '30d', label: '30d' }
];

const BUCKET_OPTIONS: { value: TelemetryBucketSize; label: string }[] = [
  { value: '15m', label: '15m' },
  { value: '30m', label: '30m' },
  { value: '1h', label: '1h' },
  { value: '1d', label: '1d' }
];

const TEMP_UNIT_OPTIONS: { value: PerformanceTempUnit; label: string }[] = [
  { value: 'F', label: '°F' },
  { value: 'C', label: '°C' }
];

/**
 * Null-aware number formatter. `null`/`undefined`/`NaN` render as the honest
 * em-dash placeholder (never `0`); a real `0` renders as `0` and a negative
 * value is preserved verbatim.
 */
const fmtNum = (value: number | null | undefined, digits = 1, unit?: string): string => {
  if (value === null || value === undefined || Number.isNaN(value)) return '—';
  const text = value.toFixed(digits);
  return unit ? `${text} ${unit}` : text;
};

/** Humanize a backend snake_case state token (e.g. `no_baseline` -> `No baseline`). */
const humanizeState = (state: string | null | undefined): string => {
  if (!state) return '—';
  const spaced = state.replace(/_/g, ' ').trim();
  if (!spaced) return '—';
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
};

/** Pick a chip color for a coarse state token without inventing severity. */
const stateChipColor = (state: string | null | undefined): ChipProps['color'] => {
  const s = (state ?? '').toLowerCase();
  if (s.includes('available') || s === 'ok' || s === 'fresh' || s === 'healthy' || s === 'live') return 'success';
  if (s.includes('stale') || s.includes('partial') || s.includes('delayed')) return 'warning';
  if (s.includes('missing') || s.includes('invalid') || s.includes('no_') || s === 'no_data' || s === 'error') {
    return 'default';
  }
  return 'default';
};

/** Naive-UTC bucket label -> viewer-local label; granularity follows the bucket. */
const formatBucketLabel = (bucketStart: string, bucket: TelemetryBucketSize): string => {
  const local = dayjs.utc(bucketStart).local();
  if (bucket === '1d') return local.format('MMM D');
  if (bucket === '1h') return local.format('MMM D, h A');
  return local.format('MMM D, h:mm A');
};

/** Naive-UTC instant -> viewer-local human timestamp, or "Never" when absent. */
const formatInstant = (instant: string | null | undefined): string => {
  if (!instant) return 'Never';
  return dayjs.utc(instant).local().format('MMM D, YYYY h:mm A');
};

/** A single grouped bar in the actual-vs-expected chart. `null` y = a gap. */
interface ActualExpectedRow {
  period: string;
  actual: number | null;
  expected: number | null;
}

/**
 * Map composed points into chart rows. Missing values stay `null` so the chart
 * renders a GAP (no bar) rather than a fabricated `0`; a genuine measured `0`
 * and a negative value are passed through verbatim.
 */
export const buildActualExpectedRows = (
  points: PerformanceContextPoint[] | undefined | null,
  bucket: TelemetryBucketSize
): ActualExpectedRow[] => {
  if (!points || points.length === 0) return [];
  return points.map(point => ({
    period: formatBucketLabel(point.bucket_start, bucket),
    actual: point.actual_kw,
    expected: point.expected_kw
  }));
};

const chartTooltip = ({ datum, xKey, yKey, yName }: AgCartesianSeriesTooltipRendererParams) => {
  const raw = datum[yKey];
  const value = raw === null || raw === undefined ? 'unavailable' : `${raw} kW`;
  return { content: `${yName} — ${datum[xKey]}: ${value}` };
};

interface StatTileProps {
  label: string;
  value: string;
  caption?: string;
}

const StatTile: React.FC<StatTileProps> = ({ label, value, caption }) => (
  <Box sx={{ p: 1.5, border: theme => `1px solid ${theme.palette.divider}`, borderRadius: 1, height: '100%' }}>
    <Typography variant="caption" color="text.secondary" sx={{ display: 'block' }}>
      {label}
    </Typography>
    <Typography variant="h6" sx={{ lineHeight: 1.3 }}>
      {value}
    </Typography>
    {caption && (
      <Typography variant="caption" color="text.secondary">
        {caption}
      </Typography>
    )}
  </Box>
);

interface SectionTitleProps {
  children: React.ReactNode;
}

const SectionTitle: React.FC<SectionTitleProps> = ({ children }) => (
  <Typography variant="subtitle1" sx={{ fontWeight: 600, mb: 1, mt: 2 }}>
    {children}
  </Typography>
);

interface PerformanceContextPanelProps {
  siteId: number;
}

/**
 * Read-only "Performance Context" panel (Project -> Telemetry tab).
 *
 * A strictly additive, read-only consumer of the composed V2 endpoint
 * `GET /api/telemetry/v2/sites/{id}/performance-context`. It NEVER writes,
 * edits, creates tickets/work-orders, generates AI summaries, or alters any
 * existing telemetry view, chart, widget, PowerBI report, or navigation. It
 * surfaces five sections — Performance Overview, an Actual-vs-Expected chart,
 * Weather Context (observed, contextual-only — never POA, never a root cause),
 * Baseline Status, and Telemetry Quality — with honest null/zero/negative
 * handling: `null` is rendered as a gap / "—", a real `0` is shown as `0`, and
 * negatives are preserved.
 */
export const PerformanceContextPanel: React.FC<PerformanceContextPanelProps> = ({ siteId }) => {
  const [windowPreset, setWindowPreset] = useState<PerformanceWindowPreset>('7d');
  const [bucket, setBucket] = useState<TelemetryBucketSize>('1h');
  const [tempUnit, setTempUnit] = useState<PerformanceTempUnit>('F');

  const { data, isLoading, isError } = useQuery<PerformanceContextResponse>({
    queryKey: ['telemetry-performance-context', siteId, windowPreset, bucket, tempUnit],
    queryFn: () => ApiClient.telemetryV2.getSitePerformanceContext(siteId, { window: windowPreset, bucket, tempUnit }),
    enabled: !!siteId
  });

  const rows = useMemo(() => buildActualExpectedRows(data?.series, bucket), [data, bucket]);

  const tempSymbol = tempUnit === 'C' ? '°C' : '°F';

  // Most-recent observed weather values in the window (latest non-null bucket).
  const latestIrradiance = useMemo(() => {
    if (!data?.series) return null;
    for (let i = data.series.length - 1; i >= 0; i -= 1) {
      const v = data.series[i].irradiance_wm2;
      if (v !== null && v !== undefined) return v;
    }
    return null;
  }, [data]);

  const latestTemperature = useMemo(() => {
    if (!data?.series) return null;
    for (let i = data.series.length - 1; i >= 0; i -= 1) {
      const v = data.series[i].temperature;
      if (v !== null && v !== undefined) return v;
    }
    return null;
  }, [data]);

  // Honest aggregate completeness: average of the buckets that reported one.
  const avgCompletenessPct = useMemo(() => {
    if (!data?.series) return null;
    const vals = data.series.map(p => p.completeness).filter((c): c is number => c !== null && c !== undefined);
    if (vals.length === 0) return null;
    const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
    // Completeness is a 0..1 ratio; show as a percentage but tolerate a value
    // that is already expressed as a percent without double-scaling.
    return avg <= 1 ? avg * 100 : avg;
  }, [data]);

  const actualSeries = useMemo<AgBarSeriesOptions>(
    () => ({
      type: 'bar',
      xKey: 'period',
      yKey: 'actual',
      yName: 'Actual',
      fill: '#1976d2',
      tooltip: { renderer: chartTooltip }
    }),
    []
  );

  const expectedSeries = useMemo<AgBarSeriesOptions>(
    () => ({
      type: 'bar',
      xKey: 'period',
      yKey: 'expected',
      yName: 'Expected',
      fill: '#9e9e9e',
      tooltip: { renderer: chartTooltip }
    }),
    []
  );

  const chartOptions = useMemo<AgCartesianChartOptions>(
    () => ({
      data: rows,
      series: [actualSeries, expectedSeries],
      height: 320,
      legend: { enabled: true, position: 'bottom' },
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
          keys: ['actual', 'expected'],
          label: { fontFamily: 'Lato, sans-serif' },
          title: { text: 'Power (kW)', fontFamily: 'Lato, sans-serif' },
          gridLine: { style: [{ stroke: 'lightgrey' }] }
        }
      ] as AgCartesianAxisOptions[]
    }),
    [rows, actualSeries, expectedSeries]
  );

  const overviewLink = `/project-hub/projects/${siteId}/overview`;
  const omLink = `/project-hub/projects/${siteId}/om`;

  // The backend rejects window=today + bucket=1d for non-UTC sites (422). Guard
  // the control combination so a normal user path can never hard-fail: disable
  // the daily bucket while "Today" is selected and auto-adjust if it was active.
  const isDailyDisabled = windowPreset === 'today';

  const handleWindowChange = (_e: React.MouseEvent<HTMLElement>, value: PerformanceWindowPreset | null) => {
    if (!value) return;
    setWindowPreset(value);
    if (value === 'today' && bucket === '1d') setBucket('1h');
  };

  const renderControls = () => (
    <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', alignItems: 'center' }}>
      <Box>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
          Window
        </Typography>
        <ToggleButtonGroup size="small" exclusive value={windowPreset} onChange={handleWindowChange}>
          {WINDOW_OPTIONS.map(opt => (
            <ToggleButton key={opt.value} value={opt.value}>
              {opt.label}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      </Box>
      <Box>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
          Bucket
        </Typography>
        <ToggleButtonGroup size="small" exclusive value={bucket} onChange={(_e, v) => v && setBucket(v)}>
          {BUCKET_OPTIONS.map(opt => (
            <ToggleButton key={opt.value} value={opt.value} disabled={opt.value === '1d' && isDailyDisabled}>
              {opt.label}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      </Box>
      <Box>
        <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mb: 0.5 }}>
          Temperature
        </Typography>
        <ToggleButtonGroup size="small" exclusive value={tempUnit} onChange={(_e, v) => v && setTempUnit(v)}>
          {TEMP_UNIT_OPTIONS.map(opt => (
            <ToggleButton key={opt.value} value={opt.value}>
              {opt.label}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      </Box>
    </Box>
  );

  const renderHeader = () => (
    <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 2, flexWrap: 'wrap' }}>
      <Box>
        <Typography variant="h6">
          <InsightsIcon sx={{ mr: 1, verticalAlign: 'middle' }} fontSize="small" />
          Performance Context
        </Typography>
        <Typography variant="caption" color="text.secondary">
          Read-only composed view. Actual telemetry vs the period-effective expected baseline, with contextual weather
          and data-quality signals. Missing values show as gaps / &quot;—&quot;, never as 0.
        </Typography>
      </Box>
      {renderControls()}
    </Box>
  );

  if (isLoading) {
    return (
      <Paper sx={{ p: 2, mb: 2 }}>
        {renderHeader()}
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mt: 2 }}>
          <CircularProgress size={18} />
          <Typography variant="body2" color="text.secondary">
            Loading performance context…
          </Typography>
        </Box>
      </Paper>
    );
  }

  if (isError || !data) {
    return (
      <Paper sx={{ p: 2, mb: 2 }}>
        {renderHeader()}
        <Alert severity="error" sx={{ mt: 2 }}>
          Failed to load performance context. You may not have access, or the service is temporarily unavailable.
        </Alert>
      </Paper>
    );
  }

  const summary = data.summary;
  const weather = data.weather_semantics;
  const baseline = data.baseline_status;
  const quality = data.telemetry_quality;

  return (
    <Paper sx={{ p: 2, mb: 2 }}>
      {renderHeader()}

      {/* 1. Performance Overview */}
      <SectionTitle>Performance Overview</SectionTitle>
      <Grid container spacing={2}>
        <Grid item xs={12} sm={6} md={3}>
          <StatTile
            label="Actual energy"
            value={fmtNum(summary.total_actual_kwh, 1, 'kWh')}
            caption={`State: ${humanizeState(summary.actual_state)}`}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatTile
            label="Expected energy"
            value={fmtNum(summary.total_expected_kwh, 1, 'kWh')}
            caption={`State: ${humanizeState(summary.expected_state)}`}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatTile label="Variance" value={fmtNum(summary.variance_kwh, 1, 'kWh')} caption="Actual − Expected" />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatTile
            label="Variance %"
            value={
              summary.variance_pct === null || summary.variance_pct === undefined
                ? '—'
                : fmtNum(summary.variance_pct, 1, '%')
            }
            caption={`${summary.bucket_count} bucket(s)`}
          />
        </Grid>
      </Grid>
      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1 }}>
        <Chip
          size="small"
          variant="outlined"
          color={stateChipColor(summary.actual_state)}
          label={`Actual: ${humanizeState(summary.actual_state)}`}
        />
        <Chip
          size="small"
          variant="outlined"
          color={stateChipColor(summary.expected_state)}
          label={`Expected: ${humanizeState(summary.expected_state)}`}
        />
      </Box>

      {/* 2. Actual vs Expected chart */}
      <SectionTitle>Actual vs Expected</SectionTitle>
      {rows.length === 0 ? (
        <Alert severity="info">No telemetry data for this window. Try a wider window or a different bucket.</Alert>
      ) : (
        <>
          <AgChartsReact options={chartOptions} />
          <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
            Gaps indicate missing data (not zero). A genuine measured 0 is plotted as 0; negative values are preserved.
            Expected bars are absent when no active baseline value exists for that bucket — never fabricated.
          </Typography>
        </>
      )}

      {/* 3. Weather Context */}
      <SectionTitle>Weather Context</SectionTitle>
      <Chip size="small" color="info" variant="outlined" label="Observed — contextual only" sx={{ mb: 1 }} />
      <Grid container spacing={2}>
        <Grid item xs={12} sm={6} md={3}>
          <StatTile
            label="Observed irradiance"
            value={fmtNum(latestIrradiance, 0, 'W/m²')}
            caption={weather.irradiance.label ?? 'Latest in window'}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatTile
            label="Observed temperature"
            value={fmtNum(latestTemperature, 1, tempSymbol)}
            caption={weather.temperature.label ?? 'Latest in window'}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatTile
            label="Weather state"
            value={humanizeState(weather.headline_state)}
            caption={weather.blocking_level ? humanizeState(weather.blocking_level) : 'Contextual'}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatTile
            label="Data freshness"
            value={humanizeState(quality.freshness_state)}
            caption={`Last reading: ${formatInstant(quality.latest_reading_at)}`}
          />
        </Grid>
      </Grid>
      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap', mt: 1 }}>
        <Tooltip title="Whether the governed weather semantics make this metric eligible for the expected model." arrow>
          <Chip
            size="small"
            variant="outlined"
            color={weather.irradiance.expected_model_eligible ? 'success' : 'default'}
            label={`Irradiance eligible: ${weather.irradiance.expected_model_eligible ? 'Yes' : 'No'}`}
          />
        </Tooltip>
        <Tooltip title="Whether the governed weather semantics make this metric eligible for the expected model." arrow>
          <Chip
            size="small"
            variant="outlined"
            color={weather.temperature.expected_model_eligible ? 'success' : 'default'}
            label={`Temperature eligible: ${weather.temperature.expected_model_eligible ? 'Yes' : 'No'}`}
          />
        </Tooltip>
      </Box>
      <Typography variant="caption" color="text.secondary" sx={{ display: 'block', mt: 1 }}>
        Weather values are observed measurements shown for context only. They are never interpreted as plane-of-array
        (POA), never used to attribute a cause, and never imply a weather-caused result.
      </Typography>

      {/* 4. Baseline Status */}
      <SectionTitle>Baseline Status</SectionTitle>
      <Grid container spacing={2}>
        <Grid item xs={12} sm={6} md={3}>
          <StatTile
            label="Baseline available"
            value={baseline.expected_baseline_available ? 'Yes' : 'No'}
            caption={baseline.baseline_type ? humanizeState(baseline.baseline_type) : 'No active baseline'}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatTile label="Expected state" value={humanizeState(baseline.expected_state)} />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatTile
            label="Selection mode"
            value={humanizeState(baseline.baseline_selection_mode)}
            caption={baseline.baseline_id ? `Baseline #${baseline.baseline_id}` : undefined}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatTile
            label="Validity"
            value={baseline.baseline_invalid ? 'Invalid' : 'OK'}
            caption={baseline.baseline_invalid ? 'Active baseline failed validation' : 'Validated on read'}
          />
        </Grid>
      </Grid>
      {baseline.baseline_invalid && baseline.required_action && (
        <Alert severity="warning" sx={{ mt: 1 }}>
          Next: {baseline.required_action}
        </Alert>
      )}

      {/* 5. Telemetry Quality */}
      <SectionTitle>Telemetry Quality</SectionTitle>
      <Grid container spacing={2}>
        <Grid item xs={12} sm={6} md={3}>
          <StatTile
            label="Freshness"
            value={humanizeState(quality.freshness_state)}
            caption={
              quality.data_delay_minutes === null || quality.data_delay_minutes === undefined
                ? `Last reading: ${formatInstant(quality.latest_reading_at)}`
                : `Delay: ${quality.data_delay_minutes} min`
            }
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatTile
            label="Completeness"
            value={avgCompletenessPct === null ? '—' : fmtNum(avgCompletenessPct, 0, '%')}
            caption="Avg across buckets"
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatTile
            label="Devices mapped"
            value={`${quality.mapped_count} / ${quality.mappable_count}`}
            caption={`${quality.expected_driving_count} drive expected`}
          />
        </Grid>
        <Grid item xs={12} sm={6} md={3}>
          <StatTile
            label="Weather sources"
            value={`${quality.weather_source_count}`}
            caption={`${quality.weather_unknown_semantics_count} unknown semantics`}
          />
        </Grid>
      </Grid>

      <Divider sx={{ my: 2 }} />

      <Box sx={{ display: 'flex', gap: 1, flexWrap: 'wrap' }}>
        <Button size="small" component={RouterLink} to={omLink} endIcon={<OpenInNewIcon fontSize="small" />}>
          View production details
        </Button>
        <Button size="small" component={RouterLink} to={omLink} endIcon={<OpenInNewIcon fontSize="small" />}>
          View telemetry
        </Button>
        <Button size="small" component={RouterLink} to={overviewLink} endIcon={<OpenInNewIcon fontSize="small" />}>
          View asset details
        </Button>
      </Box>
    </Paper>
  );
};

export default PerformanceContextPanel;
