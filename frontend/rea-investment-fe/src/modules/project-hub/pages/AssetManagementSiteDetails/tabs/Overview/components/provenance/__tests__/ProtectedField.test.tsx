import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';

import { ApiClient } from '../../../../../../../../../api';
import type { ReconciliationRow } from '../../../../../../../../../api';
import { OverviewProvenanceProvider } from '../ReconciliationProvenanceContext';
import { ProtectedField } from '../ProtectedField';

let mockUser: any = { is_system_user: true };

jest.mock('../../../../../../../../../contexts/auth/auth', () => ({
  useAuth: () => ({ user: mockUser })
}));

jest.mock('../../../../../../../../../api', () => ({
  ApiClient: {
    reconciliation: {
      getSiteReconciliation: jest.fn()
    }
  }
}));

const makeRow = (overrides: Partial<ReconciliationRow>): ReconciliationRow =>
  ({
    canonical_field: 'x',
    display_label: 'X',
    category: 'baseline_physics',
    baseline_target: 'header_column',
    status: 'missing',
    status_label: null,
    status_explanation: null,
    required_action: null,
    blocking_level: null,
    missing_dependencies: [],
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
    warnings: [],
    ...overrides
  } as ReconciliationRow);

const mockRecon = () => ApiClient.reconciliation.getSiteReconciliation as unknown as jest.Mock;

const renderInProvider = (ui: React.ReactNode, siteId = 5) =>
  render(
    <BrowserRouter>
      <QueryClientProvider client={new QueryClient()}>
        <OverviewProvenanceProvider siteId={siteId}>{ui}</OverviewProvenanceProvider>
      </QueryClientProvider>
    </BrowserRouter>
  );

describe('ProtectedField — live reconciliation provenance', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUser = { is_system_user: true };
  });

  it('renders live status, precedence value, qualifier, action, and deep links for diligence users', async () => {
    mockRecon().mockResolvedValue({
      rows: [
        makeRow({
          canonical_field: 'dc_loss_pct',
          status: 'accepted_not_promoted',
          status_label: 'Accepted candidate',
          status_explanation: 'Accepted but not promoted to an active fact.',
          accepted_value: 2.5,
          blocking_level: 'blocks_baseline',
          required_action: 'Promote in the Data Room',
          missing_dependencies: ['promotion']
        })
      ]
    });

    renderInProvider(
      <ProtectedField field="dc_wiring_loss" variant="baseline" fallback={1.5} format={value => String(value)} />
    );

    // Live status chip appears once the query resolves.
    await waitFor(() => expect(screen.getByTestId('reconciliation-status-chip')).toBeTruthy());

    // Precedence: accepted_value (2.5) wins over the card fallback (1.5).
    expect(screen.getByText('2.5')).toBeTruthy();
    // Qualifier caption for an accepted-but-unpromoted value.
    expect(screen.getByText(/not promoted/i)).toBeTruthy();
    // Required-action ("Next: …") caption.
    expect(screen.getByText(/Promote in the Data Room/i)).toBeTruthy();
    // Deep links: status is in ACTIONS_IN_DATA_ROOM, so both links render.
    expect(screen.getByRole('link', { name: /open data room/i })).toBeTruthy();
    expect(screen.getByRole('link', { name: /view reconciliation/i })).toBeTruthy();
  });

  it('does not fetch and shows the static fallback for users without diligence access', async () => {
    mockUser = { is_system_user: false, role: { permissions: {} } };

    renderInProvider(
      <ProtectedField field="dc_wiring_loss" variant="baseline" fallback={1.5} format={value => String(value)} />
    );

    // No reconciliation request is made (query disabled).
    expect(mockRecon()).not.toHaveBeenCalled();
    // Static provenance label is shown and the card value is preserved exactly.
    expect(screen.getByText(/Baseline-driving/i)).toBeTruthy();
    expect(screen.getByText('1.5')).toBeTruthy();
    expect(screen.queryByTestId('reconciliation-status-chip')).toBeNull();
  });
});

describe('ProtectedField — without a provider (safe default)', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    mockUser = { is_system_user: true };
  });

  it('degrades to the static label and card value, never throwing', () => {
    render(
      <BrowserRouter>
        <ProtectedField field="dc_wiring_loss" variant="baseline" fallback={1.5} format={value => String(value)} />
      </BrowserRouter>
    );

    expect(mockRecon()).not.toHaveBeenCalled();
    expect(screen.getByText(/Baseline-driving/i)).toBeTruthy();
    expect(screen.getByText('1.5')).toBeTruthy();
    expect(screen.queryByTestId('reconciliation-status-chip')).toBeNull();
  });
});
