import React from 'react';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { buildTelemetryV2Api } from '../../../../../../../api/telemetryV2';
import type { ExpectedBaselineResponse } from '../../../../../../../types/telemetryV2';

// Mock the API client index so the panel resolves through our spies instead of
// hitting axios. The factory may only reference `mock`-prefixed outer variables.
const mockListExpectedBaselines = jest.fn();
const mockGetActiveExpectedBaseline = jest.fn();
const mockApproveExpectedBaseline = jest.fn();
const mockActivateExpectedBaseline = jest.fn();
jest.mock('../../../../../../../api', () => ({
  ApiClient: {
    telemetryV2: {
      listExpectedBaselines: (...args: unknown[]) => mockListExpectedBaselines(...args),
      getActiveExpectedBaseline: (...args: unknown[]) => mockGetActiveExpectedBaseline(...args),
      approveExpectedBaseline: (...args: unknown[]) => mockApproveExpectedBaseline(...args),
      activateExpectedBaseline: (...args: unknown[]) => mockActivateExpectedBaseline(...args)
    }
  }
}));

// Controllable permission mirror of the backend telemetry-admin/company-admin gate.
let mockCanManage = true;
jest.mock('../../../../../../../hooks/useTelemetryAdminPermission', () => ({
  __esModule: true,
  useTelemetryAdminPermission: () => mockCanManage,
  default: () => mockCanManage
}));

// Toast notifier — assert on the surfaced messages without a provider.
const mockNotify = jest.fn();
jest.mock('../../../../../../../contexts/notifications/notifications', () => ({
  __esModule: true,
  useNotify: () => mockNotify
}));

// Imported after jest.mock so the component picks up the mocked modules.
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
      module_wattage: {
        source: 'project_fact',
        fact_id: 42,
        document_id: 5,
        ai_confidence: 0.9,
        normalization: { raw_value: '0.4', normalized_value: 400, from_unit: 'kW', to_unit: 'W' }
      },
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
  supersedes_baseline_id: 800,
  pto_date: '2026-01-01'
};

const supersededBaseline: ExpectedBaselineResponse = {
  ...draftBaseline,
  id: 800,
  baseline_name: 'Diligence facts baseline v0',
  status: 'superseded',
  version: 0,
  active_from: '2026-05-01T00:00:00Z',
  active_to: '2026-06-13T10:00:00Z',
  pto_date: '2026-01-01'
};

const renderPanel = (siteId = 123) => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const invalidateSpy = jest.spyOn(queryClient, 'invalidateQueries');
  const utils = render(
    <QueryClientProvider client={queryClient}>
      <DraftBaselineReviewPanel siteId={siteId} />
    </QueryClientProvider>
  );
  return { ...utils, queryClient, invalidateSpy };
};

beforeEach(() => {
  jest.clearAllMocks();
  mockCanManage = true;
  mockGetActiveExpectedBaseline.mockResolvedValue(null);
});

describe('DraftBaselineReviewPanel — read & lifecycle state', () => {
  it('renders the read-only review panel with the two-step lifecycle note', async () => {
    mockListExpectedBaselines.mockResolvedValue({ site_id: 123, baselines: [draftBaseline] });

    renderPanel();

    expect(await screen.findByTestId('draft-baseline-review-panel')).toBeInTheDocument();
    expect(screen.getByTestId('draft-baseline-lifecycle-note')).toBeInTheDocument();
    expect(screen.getByTestId('draft-baseline-design-estimate-note')).toBeInTheDocument();
  });

  it('renders draft provenance: fact origin, reviewer values, and applied defaults', async () => {
    mockListExpectedBaselines.mockResolvedValue({ site_id: 123, baselines: [draftBaseline] });

    renderPanel();

    expect(await screen.findByTestId('draft-baseline-detail')).toBeInTheDocument();
    expect(screen.getByText('From facts')).toBeInTheDocument();
    expect(screen.getByText('Inverter Wattage (kW)')).toBeInTheDocument();
    expect(screen.getByText('Module Wattage (W)')).toBeInTheDocument();
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

  it('lists approved-not-active, active (active_from + id), and superseded historical chips', async () => {
    mockListExpectedBaselines.mockResolvedValue({
      site_id: 123,
      baselines: [draftBaseline, approvedBaseline, activeBaseline, supersededBaseline]
    });
    mockGetActiveExpectedBaseline.mockResolvedValue(activeBaseline);

    renderPanel();

    // Approved-not-active row.
    expect(await screen.findByTestId('approved-row-902')).toBeInTheDocument();

    // Active summary shows active_from + id + active chip + period-effective note.
    const activeSummary = await screen.findByTestId('draft-baseline-active-summary');
    expect(activeSummary).toHaveTextContent('#903');
    expect(activeSummary).toHaveTextContent('Active from');
    expect(screen.getByTestId('active-period-effective-note')).toBeInTheDocument();
    expect(mockGetActiveExpectedBaseline).toHaveBeenCalledWith(123);

    // Superseded baseline shows the historical chip.
    expect(screen.getByTestId('baseline-superseded-800')).toBeInTheDocument();
    expect(screen.getByText('Superseded · historical')).toBeInTheDocument();
  });
});

describe('DraftBaselineReviewPanel — approve action', () => {
  it('shows an enabled Approve action for a permitted user', async () => {
    mockCanManage = true;
    mockListExpectedBaselines.mockResolvedValue({ site_id: 123, baselines: [draftBaseline] });

    renderPanel();

    const approve = await screen.findByTestId('approve-baseline-button');
    expect(approve).toBeEnabled();
  });

  it('shows a disabled (never misleading) Approve action for an unpermitted user', async () => {
    mockCanManage = false;
    mockListExpectedBaselines.mockResolvedValue({ site_id: 123, baselines: [draftBaseline] });

    renderPanel();

    const approve = await screen.findByTestId('approve-baseline-button');
    expect(approve).toBeDisabled();
    expect(screen.getByTestId('approve-baseline-button-disabled-wrap')).toBeInTheDocument();
  });

  it('approve confirmation summarizes provenance, defaults, normalization, PTO, and the design-estimate separation', async () => {
    mockListExpectedBaselines.mockResolvedValue({ site_id: 123, baselines: [draftBaseline] });

    renderPanel();

    fireEvent.click(await screen.findByTestId('approve-baseline-button'));

    expect(await screen.findByTestId('approve-confirm-dialog')).toBeInTheDocument();
    expect(screen.getByTestId('approve-confirm-summary')).toBeInTheDocument();
    expect(screen.getByText('Reviewer-supplied inputs')).toBeInTheDocument();
    expect(screen.getByText('Normalized values')).toBeInTheDocument();
    expect(screen.getByTestId('approve-confirm-defaults')).toBeInTheDocument();
    expect(screen.getByTestId('approve-confirm-pto-warning')).toBeInTheDocument();
    expect(screen.getByTestId('approve-confirm-statement')).toHaveTextContent(
      'Approval confirms the draft inputs, but does not make this baseline active.'
    );
    // Period-effective history language must appear in the approve dialog too.
    expect(screen.getByTestId('approve-confirm-period-effective')).toHaveTextContent('period-effective');
    expect(screen.getByText('It does not create or change design-estimate points.')).toBeInTheDocument();
    expect(screen.getByText('Design-estimate points remain a separate track.')).toBeInTheDocument();
  });

  it('maps approve 404 and generic failures to distinct, clear toasts', async () => {
    mockListExpectedBaselines.mockResolvedValue({ site_id: 123, baselines: [draftBaseline] });
    mockApproveExpectedBaseline.mockRejectedValueOnce({ response: { status: 404 } });

    renderPanel();

    fireEvent.click(await screen.findByTestId('approve-baseline-button'));
    fireEvent.click(await screen.findByTestId('approve-confirm-submit'));

    await waitFor(() =>
      expect(mockNotify).toHaveBeenCalledWith('Baseline not found. It may have been removed — refresh and try again.')
    );

    // Generic failure (no status) -> generic message.
    mockNotify.mockClear();
    mockApproveExpectedBaseline.mockRejectedValueOnce(new Error('network down'));
    fireEvent.click(await screen.findByTestId('approve-baseline-button'));
    fireEvent.click(await screen.findByTestId('approve-confirm-submit'));

    await waitFor(() => expect(mockNotify).toHaveBeenCalledWith("Couldn't approve the baseline. Please try again."));
  });

  it('on confirm, calls ONLY the approve endpoint, refetches baselines, and notifies', async () => {
    mockListExpectedBaselines.mockResolvedValue({ site_id: 123, baselines: [draftBaseline] });
    mockApproveExpectedBaseline.mockResolvedValue({ ...draftBaseline, status: 'approved' });

    const { invalidateSpy } = renderPanel();

    fireEvent.click(await screen.findByTestId('approve-baseline-button'));
    fireEvent.click(await screen.findByTestId('approve-confirm-submit'));

    await waitFor(() => expect(mockApproveExpectedBaseline).toHaveBeenCalledWith(901));
    // Never activates as a side effect of approval.
    expect(mockActivateExpectedBaseline).not.toHaveBeenCalled();
    // Refetches the baseline list (Scope C).
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['site', 'expected-baselines', { siteId: 123 }] });
    expect(mockNotify).toHaveBeenCalledWith('Baseline approved. It is not active yet.');
  });

  it('surfaces a clear permission error when approve returns 403', async () => {
    mockListExpectedBaselines.mockResolvedValue({ site_id: 123, baselines: [draftBaseline] });
    mockApproveExpectedBaseline.mockRejectedValue({ response: { status: 403 } });

    renderPanel();

    fireEvent.click(await screen.findByTestId('approve-baseline-button'));
    fireEvent.click(await screen.findByTestId('approve-confirm-submit'));

    await waitFor(() =>
      expect(mockNotify).toHaveBeenCalledWith('You do not have permission to approve this baseline.')
    );
    expect(mockActivateExpectedBaseline).not.toHaveBeenCalled();
  });
});

describe('DraftBaselineReviewPanel — activate action', () => {
  it('shows an enabled Activate action for a permitted user on an approved baseline', async () => {
    mockListExpectedBaselines.mockResolvedValue({ site_id: 123, baselines: [approvedBaseline] });

    renderPanel();

    const activate = await screen.findByTestId('activate-baseline-button-902');
    expect(activate).toBeEnabled();
  });

  it('shows a disabled Activate action for an unpermitted user', async () => {
    mockCanManage = false;
    mockListExpectedBaselines.mockResolvedValue({ site_id: 123, baselines: [approvedBaseline] });

    renderPanel();

    const activate = await screen.findByTestId('activate-baseline-button-902');
    expect(activate).toBeDisabled();
  });

  it('activate confirmation explains period-effective history, supersession, and design-estimate separation', async () => {
    mockListExpectedBaselines.mockResolvedValue({ site_id: 123, baselines: [approvedBaseline, activeBaseline] });
    mockGetActiveExpectedBaseline.mockResolvedValue(activeBaseline);

    renderPanel();

    fireEvent.click(await screen.findByTestId('activate-baseline-button-902'));

    expect(await screen.findByTestId('activate-confirm-dialog')).toBeInTheDocument();
    expect(screen.getByTestId('activate-confirm-period-effective')).toHaveTextContent('period-effective');
    expect(screen.getByTestId('activate-confirm-prior-active')).toHaveTextContent('#903');
    expect(screen.getByTestId('activate-confirm-statement')).toHaveTextContent(
      'From activation forward, this baseline will drive weather-adjusted expected/comparative performance.'
    );
    expect(screen.getByText('This affects the weather-adjusted expected baseline only.')).toBeInTheDocument();
  });

  it('on confirm, calls ONLY the activate endpoint and refetches active + O&M expected queries', async () => {
    mockListExpectedBaselines.mockResolvedValue({ site_id: 123, baselines: [approvedBaseline] });
    mockActivateExpectedBaseline.mockResolvedValue({ ...approvedBaseline, status: 'active' });

    const { invalidateSpy } = renderPanel();

    fireEvent.click(await screen.findByTestId('activate-baseline-button-902'));
    fireEvent.click(await screen.findByTestId('activate-confirm-submit'));

    await waitFor(() => expect(mockActivateExpectedBaseline).toHaveBeenCalledWith(902));
    // No approve, no facts/accepted mutation, no backfill — only activate exists in the surface.
    expect(mockApproveExpectedBaseline).not.toHaveBeenCalled();
    // Refetches the active baseline + the expected-bearing O&M site charts (Scope G).
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['site', 'expected-baseline-active', { siteId: 123 }] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['sites', 'past-performance', { siteId: 123 }] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['sites', 'actual-vs-projected-power', { siteId: 123 }] });
    expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['telemetry-readiness', 123] });
    expect(mockNotify).toHaveBeenCalledWith(
      'Baseline activated. O&M expected values now use this baseline from its activation boundary forward.'
    );
  });

  it('surfaces a clear "must be approved" error when activate returns 409', async () => {
    mockListExpectedBaselines.mockResolvedValue({ site_id: 123, baselines: [approvedBaseline] });
    mockActivateExpectedBaseline.mockRejectedValue({ response: { status: 409 } });

    renderPanel();

    fireEvent.click(await screen.findByTestId('activate-baseline-button-902'));
    fireEvent.click(await screen.findByTestId('activate-confirm-submit'));

    await waitFor(() =>
      expect(mockNotify).toHaveBeenCalledWith(
        'This baseline must be approved before activation. The baseline state changed — refresh and try again.'
      )
    );
  });

  it('surfaces a clear permission error when activate returns 403', async () => {
    mockListExpectedBaselines.mockResolvedValue({ site_id: 123, baselines: [approvedBaseline] });
    mockActivateExpectedBaseline.mockRejectedValue({ response: { status: 403 } });

    renderPanel();

    fireEvent.click(await screen.findByTestId('activate-baseline-button-902'));
    fireEvent.click(await screen.findByTestId('activate-confirm-submit'));

    await waitFor(() =>
      expect(mockNotify).toHaveBeenCalledWith('You do not have permission to activate this baseline.')
    );
    expect(mockApproveExpectedBaseline).not.toHaveBeenCalled();
  });

  it('cancelling the activate dialog calls no endpoint', async () => {
    mockListExpectedBaselines.mockResolvedValue({ site_id: 123, baselines: [approvedBaseline] });

    renderPanel();

    fireEvent.click(await screen.findByTestId('activate-baseline-button-902'));
    fireEvent.click(await screen.findByTestId('activate-confirm-cancel'));

    await waitFor(() => expect(screen.queryByTestId('activate-confirm-dialog')).not.toBeNull());
    expect(mockActivateExpectedBaseline).not.toHaveBeenCalled();
    expect(mockApproveExpectedBaseline).not.toHaveBeenCalled();
  });
});

describe('telemetryV2 expected-baseline API', () => {
  const makeHttp = (payload: unknown) => ({
    get: jest.fn().mockResolvedValue({ data: payload }),
    post: jest.fn().mockResolvedValue({ data: payload }),
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
  });

  it('approveExpectedBaseline issues a single POST to the approve URL (no other verbs)', async () => {
    const http = makeHttp(approvedBaseline);

    const api = buildTelemetryV2Api(http as never);
    const result = await api.approveExpectedBaseline(902);

    expect(http.post).toHaveBeenCalledTimes(1);
    expect(http.post).toHaveBeenCalledWith('/api/telemetry/v2/expected-baselines/902/approve');
    expect(result).toEqual(approvedBaseline);
    expect(http.get).not.toHaveBeenCalled();
    expect(http.put).not.toHaveBeenCalled();
    expect(http.patch).not.toHaveBeenCalled();
    expect(http.delete).not.toHaveBeenCalled();
  });

  it('activateExpectedBaseline issues a single POST to the activate URL (no other verbs)', async () => {
    const http = makeHttp(activeBaseline);

    const api = buildTelemetryV2Api(http as never);
    const result = await api.activateExpectedBaseline(902);

    expect(http.post).toHaveBeenCalledTimes(1);
    expect(http.post).toHaveBeenCalledWith('/api/telemetry/v2/expected-baselines/902/activate');
    expect(result).toEqual(activeBaseline);
    expect(http.get).not.toHaveBeenCalled();
    expect(http.put).not.toHaveBeenCalled();
    expect(http.patch).not.toHaveBeenCalled();
    expect(http.delete).not.toHaveBeenCalled();
  });
});
