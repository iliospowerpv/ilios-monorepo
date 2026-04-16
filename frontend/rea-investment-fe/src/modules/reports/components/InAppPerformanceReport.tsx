import React from 'react';
import { useQuery } from '@tanstack/react-query';
import Box from '@mui/material/Box';
import Paper from '@mui/material/Paper';
import Typography from '@mui/material/Typography';
import Grid from '@mui/material/Grid';
import CircularProgress from '@mui/material/CircularProgress';
import Alert from '@mui/material/Alert';
import Divider from '@mui/material/Divider';
import { AgChartsReact } from 'ag-charts-react';
import type { AgChartOptions } from 'ag-charts-community';
import dayjs from 'dayjs';
import { ApiClient } from '../../../api';
import type {
  PerformanceReportResponse,
  PerformanceReportDailyEntry,
  PerformanceReportMonthlyEntry
} from '../../../api/reports';

interface InAppPerformanceReportProps {
  siteId: number;
  siteName: string;
  startDate: string;
  endDate: string;
}

const MetricCard: React.FC<{ label: string; value: string | number; unit?: string; color?: string }> = ({
  label,
  value,
  unit,
  color
}) => (
  <Paper
    elevation={0}
    sx={{
      p: 2.5,
      border: '1px solid',
      borderColor: 'divider',
      borderRadius: 2,
      textAlign: 'center',
      height: '100%'
    }}
  >
    <Typography variant="body2" color="text.secondary" gutterBottom>
      {label}
    </Typography>
    <Typography variant="h5" fontWeight={600} color={color || 'text.primary'}>
      {value}
      {unit && (
        <Typography component="span" variant="body2" color="text.secondary" sx={{ ml: 0.5 }}>
          {unit}
        </Typography>
      )}
    </Typography>
  </Paper>
);

const DailyGenerationChart: React.FC<{ data: PerformanceReportDailyEntry[] }> = ({ data }) => {
  const chartData = data.map(d => ({
    date: new Date(d.date),
    actual: Math.round(d.actual_kwh / 1000),
    expected: Math.round(d.expected_kwh / 1000)
  }));

  const options: AgChartOptions = {
    autoSize: true,
    height: 380,
    data: chartData,
    title: { text: 'Daily Generation (MWh)', fontSize: 14, fontWeight: 'bold' },
    series: [
      {
        type: 'bar',
        xKey: 'date',
        yKey: 'actual',
        yName: 'Actual',
        fill: '#20AFE3',
        strokeWidth: 0,
        tooltip: {
          renderer: (params: any) => ({
            title: dayjs(params.datum.date).format('MMM D, YYYY'),
            content: `Actual: ${params.datum.actual.toLocaleString()} MWh`
          })
        }
      },
      {
        type: 'bar',
        xKey: 'date',
        yKey: 'expected',
        yName: 'Expected',
        fill: '#E26D69',
        strokeWidth: 0,
        tooltip: {
          renderer: (params: any) => ({
            title: dayjs(params.datum.date).format('MMM D, YYYY'),
            content: `Expected: ${params.datum.expected.toLocaleString()} MWh`
          })
        }
      }
    ],
    axes: [
      {
        type: 'time',
        position: 'bottom',
        label: { format: '%b %d' }
      },
      {
        type: 'number',
        position: 'left',
        title: { text: 'MWh' }
      }
    ],
    legend: { position: 'bottom' }
  };

  return <AgChartsReact options={options} />;
};

const PerformanceRatioChart: React.FC<{ data: PerformanceReportDailyEntry[] }> = ({ data }) => {
  const chartData = data.map(d => ({
    date: new Date(d.date),
    pr: d.performance_ratio
  }));

  const options: AgChartOptions = {
    autoSize: true,
    height: 350,
    data: chartData,
    title: { text: 'Daily Performance Ratio (%)', fontSize: 14, fontWeight: 'bold' },
    series: [
      {
        type: 'line',
        xKey: 'date',
        yKey: 'pr',
        yName: 'Performance Ratio',
        stroke: '#4CAF50',
        strokeWidth: 2,
        marker: { fill: '#4CAF50', stroke: '#4CAF50', size: 4 },
        tooltip: {
          renderer: (params: any) => ({
            title: dayjs(params.datum.date).format('MMM D, YYYY'),
            content: `PR: ${params.datum.pr}%`
          })
        }
      }
    ],
    axes: [
      {
        type: 'time',
        position: 'bottom',
        label: { format: '%b %d' }
      },
      {
        type: 'number',
        position: 'left',
        title: { text: '%' },
        min: 0,
        max: 110
      }
    ],
    legend: { enabled: false }
  };

  return <AgChartsReact options={options} />;
};

const MonthlyBreakdownChart: React.FC<{ data: PerformanceReportMonthlyEntry[] }> = ({ data }) => {
  const chartData = data.map(d => ({
    month: dayjs(d.month + '-01').format('MMM YYYY'),
    actual: Math.round(d.actual_kwh / 1000),
    expected: Math.round(d.expected_kwh / 1000),
    pr: d.performance_ratio
  }));

  const options: AgChartOptions = {
    autoSize: true,
    height: 350,
    data: chartData,
    title: { text: 'Monthly Generation Summary (MWh)', fontSize: 14, fontWeight: 'bold' },
    series: [
      {
        type: 'bar',
        xKey: 'month',
        yKey: 'actual',
        yName: 'Actual',
        fill: '#20AFE3',
        strokeWidth: 0
      },
      {
        type: 'bar',
        xKey: 'month',
        yKey: 'expected',
        yName: 'Expected',
        fill: '#E26D69',
        strokeWidth: 0
      }
    ],
    axes: [
      {
        type: 'category',
        position: 'bottom'
      },
      {
        type: 'number',
        position: 'left',
        title: { text: 'MWh' }
      }
    ],
    legend: { position: 'bottom' }
  };

  return <AgChartsReact options={options} />;
};

const InAppPerformanceReport: React.FC<InAppPerformanceReportProps> = ({ siteId, siteName, startDate, endDate }) => {
  const { data, isLoading, error } = useQuery({
    queryFn: () => ApiClient.reports.getPerformanceReport(siteId, startDate, endDate),
    queryKey: ['performance-report', { siteId, startDate, endDate }],
    staleTime: 5 * 60 * 1000
  });

  if (isLoading) {
    return (
      <Box display="flex" justifyContent="center" alignItems="center" minHeight={400}>
        <CircularProgress />
      </Box>
    );
  }

  if (error) {
    return (
      <Alert severity="error" sx={{ mt: 2 }}>
        Failed to load performance report. Please try again.
      </Alert>
    );
  }

  if (!data?.available) {
    return (
      <Alert severity="info" sx={{ mt: 2 }}>
        {data?.message || 'Performance report data is not available for this site.'}
      </Alert>
    );
  }

  const { summary, daily = [], monthly = [] } = data as PerformanceReportResponse;

  return (
    <Box sx={{ mt: 3 }}>
      <Paper elevation={0} sx={{ p: 3, border: '1px solid', borderColor: 'divider', borderRadius: 2, mb: 3 }}>
        <Box display="flex" justifyContent="space-between" alignItems="center" mb={2}>
          <Box>
            <Typography variant="h6" fontWeight={600}>
              Performance Report
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {siteName} &bull; {dayjs(startDate).format('MMM D, YYYY')} – {dayjs(endDate).format('MMM D, YYYY')}
            </Typography>
          </Box>
          <Typography variant="body2" color="text.secondary">
            {summary?.num_days} days &bull; {summary?.system_capacity_kw?.toLocaleString()} kW DC
          </Typography>
        </Box>
        <Divider sx={{ mb: 2 }} />

        <Grid container spacing={2} sx={{ mb: 3 }}>
          <Grid item xs={12} sm={6} md={3}>
            <MetricCard
              label="Total Generation"
              value={summary?.total_actual_mwh?.toLocaleString() ?? '—'}
              unit="MWh"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <MetricCard
              label="Expected Generation"
              value={summary?.total_expected_mwh?.toLocaleString() ?? '—'}
              unit="MWh"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <MetricCard
              label="Performance Ratio"
              value={summary?.performance_ratio ?? '—'}
              unit="%"
              color={
                (summary?.performance_ratio ?? 0) >= 90
                  ? '#4CAF50'
                  : (summary?.performance_ratio ?? 0) >= 70
                    ? '#FF9800'
                    : '#F44336'
              }
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <MetricCard label="Capacity Factor" value={summary?.capacity_factor ?? '—'} unit="%" />
          </Grid>
        </Grid>

        <Grid container spacing={2} sx={{ mb: 1 }}>
          <Grid item xs={12} sm={6} md={3}>
            <MetricCard
              label="Avg. Daily Generation"
              value={
                summary?.avg_daily_generation_kwh
                  ? Math.round(summary.avg_daily_generation_kwh / 1000).toLocaleString()
                  : '—'
              }
              unit="MWh"
            />
          </Grid>
          <Grid item xs={12} sm={6} md={3}>
            <MetricCard label="Availability" value={summary?.availability ?? '—'} unit="%" />
          </Grid>
        </Grid>
      </Paper>

      <Grid container spacing={3}>
        <Grid item xs={12}>
          <Paper elevation={0} sx={{ p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
            <DailyGenerationChart data={daily} />
          </Paper>
        </Grid>
        <Grid item xs={12} md={6}>
          <Paper elevation={0} sx={{ p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
            <PerformanceRatioChart data={daily} />
          </Paper>
        </Grid>
        <Grid item xs={12} md={6}>
          <Paper elevation={0} sx={{ p: 2, border: '1px solid', borderColor: 'divider', borderRadius: 2 }}>
            <MonthlyBreakdownChart data={monthly} />
          </Paper>
        </Grid>
      </Grid>
    </Box>
  );
};

export default InAppPerformanceReport;
