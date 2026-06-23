import React from 'react';
import { screen, render } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ThemeProvider } from '@mui/material/styles';

import ActualProduction from '../ActualProduction';
import theme from '../../../../../../../../../utils/styles/theme';

// react-chartjs-2 renders to a canvas jsdom cannot drive; stub the Doughnut with
// an element that serializes the dataset so we can assert on the ring values.
jest.mock('react-chartjs-2', () => ({
  __esModule: true,
  Doughnut: ({ data }: { data: { datasets: { data: unknown[] }[] } }) => (
    <div data-testid="doughnut" data-datasets={JSON.stringify(data.datasets)} />
  )
}));

// chart.js/auto is imported only for its registration side-effect; neutralize it.
jest.mock('chart.js/auto', () => ({}));

const mockGetSiteDashboardProduction = jest.fn();

jest.mock('../../../../../../../../../api', () => ({
  ApiClient: {
    operationsAndMaintenance: {
      getSiteDashboardProduction: (...args: unknown[]) => mockGetSiteDashboardProduction(...args)
    }
  }
}));

jest.mock('../../../../../../../../../hooks/telemetryV2', () => ({
  useSiteLatestTelemetry: () => ({ data: undefined })
}));

type ProductionResponse = Record<string, unknown>;

const baseResponse: ProductionResponse = {
  actual_kw: 50,
  actual_vs_expected: 87,
  expected_kw: 100,
  performance_index: 0.87,
  system_size_ac: 200,
  system_size_dc: 250,
  weather: null,
  cumulative_actual_kw: 500,
  cumulative_expected_kw: 600,
  cumulative_actual_vs_expected: 83,
  expected_baseline_available: true,
  expected_state: 'available'
};

const renderWidget = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <ThemeProvider theme={theme}>
        <ActualProduction siteId={4} />
      </ThemeProvider>
    </QueryClientProvider>
  );
};

beforeEach(() => {
  mockGetSiteDashboardProduction.mockReset();
});

describe('ActualProduction honest null display', () => {
  it('renders N/A (never 0) and an explanatory caption when the actual is null', async () => {
    mockGetSiteDashboardProduction.mockResolvedValue({ ...baseResponse, actual_kw: null });
    renderWidget();

    expect(
      await screen.findByText(/Actual production is unavailable for this period .* shown as N\/A\./i)
    ).toBeInTheDocument();
    // The actual tile shows N/A, not a fabricated 0.00.
    expect(screen.getByText('N/A')).toBeInTheDocument();
    expect(screen.queryByText('0.00')).not.toBeInTheDocument();
  });

  it('preserves a genuine measured 0 (renders 0.00, not N/A)', async () => {
    mockGetSiteDashboardProduction.mockResolvedValue({ ...baseResponse, actual_kw: 0 });
    renderWidget();

    expect(await screen.findByText('0.00')).toBeInTheDocument();
    expect(screen.queryByText(/Actual production is unavailable/i)).not.toBeInTheDocument();
  });

  it('preserves a negative night-time tare value (no negatives->0 rule)', async () => {
    mockGetSiteDashboardProduction.mockResolvedValue({ ...baseResponse, actual_kw: -5 });
    renderWidget();

    expect(await screen.findByText('-5.00')).toBeInTheDocument();
  });

  it('shows the real variance percent when both actual and expected are present', async () => {
    mockGetSiteDashboardProduction.mockResolvedValue(baseResponse);
    renderWidget();

    expect(await screen.findByText('87')).toBeInTheDocument();
    expect(screen.getByText('from Expected')).toBeInTheDocument();
    expect(screen.queryByText('Variance N/A')).not.toBeInTheDocument();

    const doughnut = screen.getByTestId('doughnut');
    const datasets = JSON.parse(doughnut.getAttribute('data-datasets') as string);
    // A real variance fills the ring (87 + 13), never the neutral [0, 100].
    expect(datasets[0].data).toEqual([87, 13]);
  });

  it('shows "Variance N/A" with a neutral ring when the actual is missing', async () => {
    mockGetSiteDashboardProduction.mockResolvedValue({ ...baseResponse, actual_kw: null });
    renderWidget();

    expect(await screen.findByText('Variance N/A')).toBeInTheDocument();
    expect(screen.getByText('Actual unavailable')).toBeInTheDocument();

    const doughnut = screen.getByTestId('doughnut');
    const datasets = JSON.parse(doughnut.getAttribute('data-datasets') as string);
    expect(datasets[0].data).toEqual([0, 100]);
  });

  it('shows "Variance N/A" when the expected baseline is unavailable', async () => {
    mockGetSiteDashboardProduction.mockResolvedValue({
      ...baseResponse,
      expected_kw: null,
      expected_baseline_available: false,
      expected_state: 'baseline_not_available'
    });
    renderWidget();

    expect(await screen.findByText('Variance N/A')).toBeInTheDocument();
    // Expected-side term surfaces as the reason caption.
    expect(screen.getByText('Baseline not available')).toBeInTheDocument();
  });

  it('hides the weather chip entirely when no descriptor is returned', async () => {
    mockGetSiteDashboardProduction.mockResolvedValue({ ...baseResponse, weather: null });
    renderWidget();

    await screen.findByTestId('doughnut');
    expect(screen.queryByText('Observed')).not.toBeInTheDocument();
  });

  it('renders an observed/contextual weather chip when a descriptor is present', async () => {
    mockGetSiteDashboardProduction.mockResolvedValue({
      ...baseResponse,
      weather: { weather_description: 'Cloudy', weather_icon_url: 'http://example.com/cloud.png' }
    });
    renderWidget();

    expect(await screen.findByText('Observed')).toBeInTheDocument();
    expect(screen.getByText('Cloudy')).toBeInTheDocument();
  });
});
