import React from 'react';
import { screen, render, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import {
  DevicePerformanceCard,
  buildDevicePerformanceRows,
  DEVICE_POWER_METRIC
} from '../DevicePerformanceCard';
import type { TelemetrySeriesPoint } from '../../../../../../../../../types/telemetryV2';

// ag-charts-react renders to a canvas that jsdom cannot drive; stub it with a
// element that serializes the data it received so we can assert on the series.
jest.mock('ag-charts-react', () => ({
  __esModule: true,
  AgChartsReact: ({ options }: { options: { data?: unknown[]; series?: unknown[] } }) => (
    <div data-testid="ag-chart" data-options={JSON.stringify(options)} />
  )
}));

const mockGetSiteDeviceRollupSeries = jest.fn();

jest.mock('../../../../../../../../../api', () => ({
  ApiClient: {
    telemetryV2: {
      getSiteDeviceRollupSeries: (...args: unknown[]) => mockGetSiteDeviceRollupSeries(...args)
    }
  }
}));

const point = (bucket_start: string, value: number): TelemetrySeriesPoint => ({
  bucket_start,
  value,
  sample_count: 12,
  completeness: 1
});

const renderCard = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <DevicePerformanceCard siteId={4} deviceId={42} />
    </QueryClientProvider>
  );
};

beforeEach(() => {
  mockGetSiteDeviceRollupSeries.mockReset();
});

describe('buildDevicePerformanceRows', () => {
  it('returns an empty array for empty/null/undefined input (never fabricates rows)', () => {
    expect(buildDevicePerformanceRows([])).toEqual([]);
    expect(buildDevicePerformanceRows(null)).toEqual([]);
    expect(buildDevicePerformanceRows(undefined)).toEqual([]);
  });

  it('maps each returned point to an actual-only row with no projected key', () => {
    const rows = buildDevicePerformanceRows([
      point('2026-06-15T13:00:00', 120.5),
      point('2026-06-15T14:00:00', 0)
    ]);
    expect(rows).toHaveLength(2);
    expect(rows[0].actual).toBe(120.5);
    // A genuine 0 reading is preserved (real value), but it is the only row
    // shape — there is no projected/expected field anywhere.
    expect(rows[1].actual).toBe(0);
    rows.forEach(row => {
      expect(Object.keys(row).sort()).toEqual(['actual', 'period']);
      expect(row).not.toHaveProperty('projected');
      expect(row).not.toHaveProperty('expected');
    });
  });

  it('does not back-fill missing buckets with a fabricated 0', () => {
    // Only two buckets returned across a 24h window -> only two rows, the gaps
    // are simply absent (not zero-filled).
    const rows = buildDevicePerformanceRows([
      point('2026-06-15T08:00:00', 88),
      point('2026-06-15T20:00:00', 64)
    ]);
    expect(rows).toHaveLength(2);
    expect(rows.map(r => r.actual)).toEqual([88, 64]);
  });
});

describe('DevicePerformanceCard', () => {
  it('always shows the honest "projected unavailable" caption', async () => {
    mockGetSiteDeviceRollupSeries.mockResolvedValue({ devices: [] });
    renderCard();
    expect(
      await screen.findByText(/Projected unavailable: per-device expected baseline is not defined\./i)
    ).toBeInTheDocument();
  });

  it('requests the actual-only device power metric', async () => {
    mockGetSiteDeviceRollupSeries.mockResolvedValue({ devices: [] });
    renderCard();
    await waitFor(() => expect(mockGetSiteDeviceRollupSeries).toHaveBeenCalledTimes(1));
    const [siteId, query] = mockGetSiteDeviceRollupSeries.mock.calls[0];
    expect(siteId).toBe(4);
    expect(query.deviceId).toBe(42);
    expect(query.metric).toBe(DEVICE_POWER_METRIC);
    expect(query.bucketSize).toBe('1h');
  });

  it('renders an honest unavailable message and no chart when there are no readings', async () => {
    mockGetSiteDeviceRollupSeries.mockResolvedValue({ devices: [] });
    renderCard();
    expect(
      await screen.findByText(/No V2 telemetry readings for this device or the last 24 hours\./i)
    ).toBeInTheDocument();
    expect(screen.queryByTestId('ag-chart')).not.toBeInTheDocument();
  });

  it('renders an actual-only series (no projected) when readings exist', async () => {
    mockGetSiteDeviceRollupSeries.mockResolvedValue({
      devices: [{ device_id: 42, device_name: 'INV-01', unit: 'kW', count: 2, points: [point('2026-06-15T13:00:00', 120.5), point('2026-06-15T14:00:00', 95)] }]
    });
    renderCard();
    const chart = await screen.findByTestId('ag-chart');
    const options = JSON.parse(chart.getAttribute('data-options') as string);
    expect(options.data).toHaveLength(2);
    expect(options.series).toHaveLength(1);
    expect(options.series[0].yKey).toBe('actual');
    // No second (projected) series exists.
    expect(options.series.some((s: { yKey?: string }) => s.yKey === 'projected')).toBe(false);
  });
});
