import React from 'react';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import { buildReconciliationApi } from '../../../../../../../api/reconciliation';
import type { SiteReconciliationResponse } from '../../../../../../../api/reconciliation';

// Mock the API client index so the component resolves through our spy instead of
// hitting axios. The factory may only reference `mock`-prefixed outer variables.
const mockGetSiteReconciliation = jest.fn();
jest.mock('../../../../../../../api', () => ({
  ApiClient: {
    reconciliation: {
      getSiteReconciliation: (...args: unknown[]) => mockGetSiteReconciliation(...args)
    }
  }
}));

// Imported after jest.mock so the component picks up the mocked ApiClient.
import Reconciliation from '../Reconciliation';

const siteDetails = { id: 123, name: 'Riverside Solar' } as any;

const baseReadiness: SiteReconciliationResponse['readiness'] = {
  facts_to_draft_ready: false,
  missing_required_physics_fields: ['tilt_deg'],
  facts_to_draft_warnings: [],
  active_baseline_available: true,
  active_baseline_id: 7,
  active_baseline_created_at: '2026-01-02T10:00:00Z',
  design_estimate_baseline_id: null,
  design_estimate_baseline_status: null,
  design_points_ready: null,
  design_points_present_months: [],
  design_points_missing: [],
  design_points_parse_errors: []
};

const baseTelemetry: SiteReconciliationResponse['telemetry_reality'] = {
  available: false,
  note: 'No telemetry readings have been ingested for this project yet.',
  last_reading_at: null
};

const fullRow: SiteReconciliationResponse['rows'][number] = {
  canonical_field: 'module_capacity_kw',
  display_label: 'Module Capacity (kW)',
  category: 'baseline_physics',
  baseline_target: 'header_column',
  status: 'in_active_baseline',
  status_label: 'In active baseline',
  status_explanation: 'This promoted assumption is on the active baseline driving expected output.',
  required_action: null,
  blocking_level: 'blocks_reporting',
  missing_dependencies: [],
  ai_extracted_value: 1200,
  accepted_value: 1200,
  active_fact_value: 1200,
  draft_baseline_value: 1200,
  active_baseline_value: 1100,
  legacy_value: 1000,
  fact_id: 42,
  project_fact_id: 42,
  source_file_id: 9,
  source_document_type: 'Engineering Report',
  source_run_id: 3,
  evidence_page: 12,
  evidence_snippet: 'Total module capacity is 1,200 kW.',
  confidence: 0.92,
  effective_from: '2026-01-01T00:00:00Z',
  effective_to: null,
  document_id: 5,
  document_version_id: 9,
  ai_run_id: 3,
  document_key_id: 11,
  baseline_id: 7,
  baseline_point_id: null,
  aliases_matched: ['Module Capacity (kW)', 'module_capacity_kw'],
  supersedes_fact_id: null,
  candidate_count: 2,
  required_for_baseline: true,
  warnings: ['fact_differs_from_legacy', 'draft_differs_from_active']
};

// A row with every provenance/value field null to prove the panel never crashes
// on sparse backend payloads.
const nullProvenanceRow: SiteReconciliationResponse['rows'][number] = {
  canonical_field: 'inverter_efficiency',
  display_label: 'Inverter Efficiency',
  category: 'equipment',
  baseline_target: 'none',
  status: 'missing',
  status_label: 'Missing',
  status_explanation: 'No value has been extracted, accepted, or promoted for this field yet.',
  required_action: null,
  blocking_level: null,
  missing_dependencies: ['source_value', 'acceptance', 'promotion', 'baseline'],
  ai_extracted_value: null,
  accepted_value: null,
  active_fact_value: null,
  draft_baseline_value: null,
  active_baseline_value: null,
  legacy_value: null,
  fact_id: null,
  project_fact_id: null,
  source_file_id: null,
  source_document_type: null,
  source_run_id: null,
  evidence_page: null,
  evidence_snippet: null,
  confidence: null,
  effective_from: null,
  effective_to: null,
  document_id: null,
  document_version_id: null,
  ai_run_id: null,
  document_key_id: null,
  baseline_id: null,
  baseline_point_id: null,
  aliases_matched: [],
  supersedes_fact_id: null,
  candidate_count: 0,
  required_for_baseline: false,
  warnings: []
};

const buildResponse = (overrides: Partial<SiteReconciliationResponse> = {}): SiteReconciliationResponse => ({
  site_id: 123,
  generated_at: '2026-06-12T08:00:00Z',
  rows: [fullRow, nullProvenanceRow],
  readiness: baseReadiness,
  telemetry_reality: baseTelemetry,
  help_targets: {},
  schema_expansion_recommended: true,
  ...overrides
});

const renderPanel = () => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <Reconciliation siteDetails={siteDetails} />
    </QueryClientProvider>
  );
};

describe('Reconciliation panel', () => {
  it('renders the panel with readiness, table, and rows for a permitted user', async () => {
    mockGetSiteReconciliation.mockResolvedValue(buildResponse());

    renderPanel();

    expect(await screen.findByTestId('reconciliation-tab')).toBeInTheDocument();
    expect(screen.getByTestId('reconciliation-readiness')).toBeInTheDocument();
    expect(screen.getByTestId('reconciliation-disclaimer')).toBeInTheDocument();
    expect(screen.getByTestId('reconciliation-table')).toBeInTheDocument();
    expect(screen.getAllByTestId('reconciliation-row')).toHaveLength(2);
    expect(screen.getAllByTestId('reconciliation-status-chip').length).toBeGreaterThanOrEqual(1);
    expect(mockGetSiteReconciliation).toHaveBeenCalledTimes(1);
    expect(mockGetSiteReconciliation).toHaveBeenCalledWith(123);
  });

  it('renders warning chips and the schema-expansion note when present', async () => {
    mockGetSiteReconciliation.mockResolvedValue(buildResponse());

    renderPanel();

    expect(await screen.findByTestId('reconciliation-tab')).toBeInTheDocument();
    expect(screen.getByTestId('reconciliation-schema-note')).toBeInTheDocument();
    expect(screen.getAllByTestId('reconciliation-warning-chips').length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText('Differs from legacy')).toBeInTheDocument();
    expect(screen.getByText('Draft ≠ active')).toBeInTheDocument();
  });

  it('shows an explicit unauthorized state on a 403 response', async () => {
    mockGetSiteReconciliation.mockRejectedValue({ response: { status: 403 } });

    renderPanel();

    expect(await screen.findByTestId('reconciliation-unauthorized')).toBeInTheDocument();
    expect(screen.queryByTestId('reconciliation-tab')).not.toBeInTheDocument();
  });

  it('shows a generic error state on a non-auth failure', async () => {
    mockGetSiteReconciliation.mockRejectedValue({ response: { status: 500 } });

    renderPanel();

    expect(await screen.findByTestId('reconciliation-error')).toBeInTheDocument();
    expect(screen.queryByTestId('reconciliation-tab')).not.toBeInTheDocument();
  });

  it('shows the empty state when there are no rows', async () => {
    mockGetSiteReconciliation.mockResolvedValue(buildResponse({ rows: [] }));

    renderPanel();

    expect(await screen.findByTestId('reconciliation-empty')).toBeInTheDocument();
    expect(screen.queryByTestId('reconciliation-table')).not.toBeInTheDocument();
  });

  it('renders without crashing when a row has fully null provenance and values', async () => {
    mockGetSiteReconciliation.mockResolvedValue(buildResponse({ rows: [nullProvenanceRow] }));

    renderPanel();

    expect(await screen.findByTestId('reconciliation-tab')).toBeInTheDocument();
    expect(screen.getAllByTestId('reconciliation-row')).toHaveLength(1);
    // A row with no warnings renders the placeholder rather than warning chips.
    expect(screen.queryByTestId('reconciliation-warning-chips')).not.toBeInTheDocument();
  });
});

describe('buildReconciliationApi', () => {
  it('issues only a GET to the correct URL and never a mutation verb', async () => {
    const response = buildResponse();
    const httpClient = {
      get: jest.fn().mockResolvedValue({ data: response }),
      post: jest.fn(),
      put: jest.fn(),
      patch: jest.fn(),
      delete: jest.fn()
    };

    const api = buildReconciliationApi(httpClient as any);
    const result = await api.getSiteReconciliation(123);

    expect(httpClient.get).toHaveBeenCalledTimes(1);
    expect(httpClient.get).toHaveBeenCalledWith('/api/due-diligence/sites/123/reconciliation');
    expect(result).toEqual(response);
    expect(httpClient.post).not.toHaveBeenCalled();
    expect(httpClient.put).not.toHaveBeenCalled();
    expect(httpClient.patch).not.toHaveBeenCalled();
    expect(httpClient.delete).not.toHaveBeenCalled();
  });
});
