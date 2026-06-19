import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { buildTelemetryV2Api } from '../../../../../../../api/telemetryV2';
import type { ExpectedBaselineResponse } from '../../../../../../../types/telemetryV2';

// Mock the API client index so the panel resolves through our spies instead of
// hitting axios. The factory may only reference `mock`-prefixed outer variables.
const mockListExpectedBaselines = jest.fn();
const mockGetActiveExpectedBaseline = jest.fn();
jest.mock('../../../../../../../api', () => ({
  ApiClient: {
    telemetryV2: {
      listExpectedBaselines: (...args: unknown[]) => mockListExpectedBaselines(...args),
      getActiveExpectedBaseline: (...args: unknown[]) => mockGetActiveExpectedBaseline(...args)
    }
  }
}));

// Imported after jest.mock so the component picks up the mocked ApiClient.
import DraftBaselineReviewPanel from '../components/DraftBaselineReviewPanel';

const draftBaseline: ExpectedBaselineResponse = {
  id: 901,
  company_id: 1,
  site_id: 123,
  baseline_name: 'Diligence facts baseline v1',
  baseline_type: 'weather_adjusted_model',
  status: 'draft',
  source_type: 'diligence_ai_parse',
  source_document_id: 5,
  source_project_fact_id: 42,
  module_wattage: 400,
  module_quantity: 1000,
  inverter_wattage: 100,
  inverter_quantity: 8,
  thermal_coefficient_pct: -0.35,
  power_tolerance_min_pct: 0,
  year_1_degradation_pct: 2,
  annual_degradation_pct: 0.5,
  cec_efficiency_pct: 98,
  // dc_loss_pct supplied by reviewer; the rest fall back to documented defaults.
  dc_loss_pct: 2,
  ac_loss_pct: null,
  medium_voltage_loss_pct: null,
  mv_line_loss_pct: null,
  soiling_factor: null,
  pto_date: null,
  loss_assumptions_json: { dc_loss_pct: 2 },
  model_parameters_json: {
    source: 'diligence_ai_parse_bridge',
    created_from: 'promoted_project_facts',
    source_fact_signature: 'sig-abc',
    version: 1,
    field_sources: {
      module_wattage: { source: 'project_fact', fact_id: 42, document_id: 5, ai_confidence: 0.9 },
      thermal_coefficient_pct: { source: 'reviewer_supplied' },
      dc_loss_pct: { source: 'reviewer_supplied' }
    },
    source_facts: [{ canonical_name: 'module_wattage', column: 'module_wattage', fact_id: 42, value: 400 }],
    warnings: ['ac_loss_pct: not supplied — defaults to 0%']
  },
  ai_confidence_json: { module_wattage: 0.9 },
  version: 1,
  created_by_user_id: 7,
  supersedes_baseline_id: null,
  created_at: '2026-06-10T08:00:00Z'
};

const approvedBaseline: ExpectedBaselineResponse = {
  ...draftBaseline,
  id: 902,
  baseline_name: 'Diligence facts baseline v2',
  status: 'approved',
  version: 2,
  approved_at: '2026-06-12T09:00:00Z',
  pto_date: '2026-01-01'
};

const activeBaseline: ExpectedBaselineResponse = {
  ...draftBaseline,
  id: 903,
  baseline_name: 'Diligence facts baseline v3',
  status: 'active',
  version: 3,
  active_from: '2026-06-13T10:00:00Z',
  pto_date: '2026-01-01'
};

const renderPanel = (siteId = 123) => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <DraftBaselineReviewPanel siteId={siteId} />
    </QueryClientProvider>
  );
};

beforeEach(() => {
  jest.clearAllMocks();
  mockGetActiveExpectedBaseline.mockResolvedValue(null);
});

describe('DraftBaselineReviewPanel', () => {
  it('renders the read-only panel with the activation note and never an approve/activate control', async () => {
    mockListExpectedBaselines.mockResolvedValue({ site_id: 123, baselines: [draftBaseline] });

    renderPanel();

    expect(await screen.findByTestId('draft-baseline-review-panel')).toBeInTheDocument();
    expect(screen.getByTestId('draft-baseline-activation-note')).toBeInTheDocument();
    expect(screen.getByText('Read-only')).toBeInTheDocument();

    // The hard constraint: no approve / activate affordance of any kind.
    expect(screen.queryByRole('button', { name: /approve|activate/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/^Approve$/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/^Activate$/i)).not.toBeInTheDocument();
  });

  it('renders draft provenance: fact origin, reviewer values, and applied defaults', async () => {
    mockListExpectedBaselines.mockResolvedValue({ site_id: 123, baselines: [draftBaseline] });

    renderPanel();

    expect(await screen.findByTestId('draft-baseline-detail')).toBeInTheDocument();
    // Fact-backed field shows a "From facts" origin chip.
    expect(screen.getByText('From facts')).toBeInTheDocument();
    // Inverter wattage is stored/calculated in kW (module wattage stays W).
    expect(screen.getByText('Inverter Wattage (kW)')).toBeInTheDocument();
    expect(screen.getByText('Module Wattage (W)')).toBeInTheDocument();
    // A supplied optional renders a reviewer value; an unsupplied one shows the
    // documented default explicitly flagged as not source-backed.
    expect(screen.getAllByText('Reviewer value').length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText('Default applied — not source-backed').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('1.0 (no soiling)')).toBeInTheDocument();
  });

  it('warns that expected is suppressed when the draft has no PTO date', async () => {
    mockListExpectedBaselines.mockResolvedValue({ site_id: 123, baselines: [draftBaseline] });

    renderPanel();

    expect(await screen.findByTestId('draft-baseline-pto-suppressed')).toBeInTheDocument();
  });

  it('states that a draft expected preview is unavailable (never calls a preview endpoint)', async () => {
    mockListExpectedBaselines.mockResolvedValue({ site_id: 123, baselines: [draftBaseline] });

    renderPanel();

    expect(await screen.findByTestId('draft-baseline-preview-unavailable')).toBeInTheDocument();
  });

  it('shows a draft selector when more than one draft exists', async () => {
    const secondDraft = { ...draftBaseline, id: 905, baseline_name: 'Diligence facts baseline (newer)' };
    mockListExpectedBaselines.mockResolvedValue({ site_id: 123, baselines: [secondDraft, draftBaseline] });

    renderPanel();

    expect(await screen.findByTestId('draft-baseline-selector')).toBeInTheDocument();
  });

  it('lists approved-but-inactive baselines and the active baseline summary separately', async () => {
    mockListExpectedBaselines.mockResolvedValue({
      site_id: 123,
      baselines: [draftBaseline, approvedBaseline, activeBaseline]
    });
    mockGetActiveExpectedBaseline.mockResolvedValue(activeBaseline);

    renderPanel();

    expect(await screen.findByTestId('draft-baseline-approved-list')).toBeInTheDocument();
    expect(screen.getByTestId('baseline-summary-902')).toBeInTheDocument();
    await waitFor(() => expect(screen.getByTestId('baseline-summary-903')).toBeInTheDocument());
    // The active summary uses the dedicated active read endpoint.
    expect(mockGetActiveExpectedBaseline).toHaveBeenCalledWith(123);
  });

  it('shows the empty state when no weather-adjusted baselines exist', async () => {
    mockListExpectedBaselines.mockResolvedValue({ site_id: 123, baselines: [] });

    renderPanel();

    expect(await screen.findByTestId('draft-baseline-review-empty')).toBeInTheDocument();
    expect(screen.queryByTestId('draft-baseline-detail')).not.toBeInTheDocument();
  });

  it('shows an unauthorized state on a 403 from the list endpoint', async () => {
    mockListExpectedBaselines.mockRejectedValue({ response: { status: 403 } });

    renderPanel();

    expect(await screen.findByTestId('draft-baseline-review-forbidden')).toBeInTheDocument();
  });

  it('shows a generic error state on a non-auth failure', async () => {
    mockListExpectedBaselines.mockRejectedValue({ response: { status: 500 } });

    renderPanel();

    expect(await screen.findByTestId('draft-baseline-review-error')).toBeInTheDocument();
  });
});

describe('telemetryV2 expected-baseline read API', () => {
  const makeHttp = (payload: unknown) => ({
    get: jest.fn().mockResolvedValue({ data: payload }),
    post: jest.fn(),
    put: jest.fn(),
    patch: jest.fn(),
    delete: jest.fn()
  });

  it('listExpectedBaselines issues only a GET to the correct URL', async () => {
    const payload = { site_id: 123, baselines: [draftBaseline] };
    const http = makeHttp(payload);

    const api = buildTelemetryV2Api(http as never);
    const result = await api.listExpectedBaselines(123);

    expect(http.get).toHaveBeenCalledTimes(1);
    expect(http.get).toHaveBeenCalledWith('/api/telemetry/v2/sites/123/expected-baselines');
    expect(result).toEqual(payload);
    expect(http.post).not.toHaveBeenCalled();
    expect(http.put).not.toHaveBeenCalled();
    expect(http.patch).not.toHaveBeenCalled();
    expect(http.delete).not.toHaveBeenCalled();
  });

  it('getActiveExpectedBaseline issues only a GET and returns null when none is active', async () => {
    const http = makeHttp(null);

    const api = buildTelemetryV2Api(http as never);
    const result = await api.getActiveExpectedBaseline(123);

    expect(http.get).toHaveBeenCalledTimes(1);
    expect(http.get).toHaveBeenCalledWith('/api/telemetry/v2/sites/123/expected-baselines/active', undefined);
    expect(result).toBeNull();
    expect(http.post).not.toHaveBeenCalled();
    expect(http.put).not.toHaveBeenCalled();
    expect(http.patch).not.toHaveBeenCalled();
    expect(http.delete).not.toHaveBeenCalled();
  });
});
