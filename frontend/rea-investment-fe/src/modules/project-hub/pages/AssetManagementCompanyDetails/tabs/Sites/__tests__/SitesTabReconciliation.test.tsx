import React from 'react';
// Register the enterprise modules (serverSide row model) the same way the app
// does in index.tsx; without this the grid cannot drive its datasource.
import 'ag-grid-enterprise';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import SitesTab from '../Sites';
import { AuthProvider } from '../../../../../../../contexts/auth/auth';
import { ApiClient } from '../../../../../../../api';
import type { CompanyDetails } from '../../../../../../../api';
import { httpClient } from '../../../../../../../api/http-client';
import type {
  InventoryReconciliationSummary,
  InventoryReconciliationSummaryBatchResponse
} from '../../../../../../../types/telemetryV2';

// The company landing Projects tab renders SitesTable with a companyId, which in
// turn mounts the (closed) ProjectImportWizard. Stub it to a no-op so this test
// stays focused on reconciliation batching and never pulls the wizard's own
// react-query data. This is a test-only seam — no production code is changed.
jest.mock('../../../../../../../components/common/ProjectImport/ProjectImportWizard', () => ({
  __esModule: true,
  default: () => null
}));

const COMPANY_ID = 99;

const companyDetails = { id: COMPANY_ID, name: 'Acme Holdings' } as unknown as CompanyDetails;

const summary = (overrides: Partial<InventoryReconciliationSummary> = {}): InventoryReconciliationSummary => ({
  status: 'matched',
  status_label: 'Matched',
  status_explanation: 'Documented inventory matches telemetry.',
  has_blocking_mismatch: false,
  weather_dependency_unsatisfied: false,
  open_actionable_mismatch_count: 0,
  informational_mismatch_count: 0,
  ...overrides
});

const project = (id: number, name: string) => ({
  id,
  name,
  status: 'Placed in Service',
  company: { id: COMPANY_ID, name: 'Acme Holdings' }
});

const renderCompanyProjectsTab = () => {
  // A fresh QueryClient keeps the reconciliation cache from leaking across tests
  // so the call-count assertions stay honest.
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <SitesTab companyDetails={companyDetails} />
        </AuthProvider>
      </QueryClientProvider>
    </BrowserRouter>
  );
};

describe('Company landing Projects tab reconciliation batching', () => {
  let httpGetSpy: jest.SpyInstance;
  let summariesSpy: jest.SpyInstance;

  beforeEach(() => {
    // ApiClient.assetManagement is Object.freeze'd, so the page of projects is fed
    // by stubbing the shared httpClient.get for the /api/sites/ endpoint (the
    // company-scoped server-side grid datasource hits this with company_id).
    // AuthProvider's token is null in jsdom, so user.me is never requested.
    httpGetSpy = jest.spyOn(httpClient, 'get').mockImplementation((url: string) => {
      if (typeof url === 'string' && url.includes('/api/sites/')) {
        return Promise.resolve({
          data: {
            skip: 0,
            limit: 10,
            total: 3,
            // The grid renders a page of multiple projects in one server-side block.
            items: [project(1, 'Project One'), project(2, 'Project Two'), project(3, 'Project Three')]
          }
        }) as never;
      }
      return Promise.resolve({ data: {} }) as never;
    });
    summariesSpy = jest.spyOn(ApiClient.telemetryV2, 'getInventoryReconciliationSummaries');
  });

  afterEach(() => {
    httpGetSpy.mockRestore();
    summariesSpy.mockRestore();
  });

  test('fires exactly one batched summaries request for the visible projects', async () => {
    const response: InventoryReconciliationSummaryBatchResponse = {
      summaries: [
        { site_id: 1, summary: summary() },
        { site_id: 2, summary: summary({ status: 'needs_reconciliation', status_label: 'Needs reconciliation' }) },
        { site_id: 3, summary: summary() }
      ]
    };
    summariesSpy.mockResolvedValue(response);

    renderCompanyProjectsTab();

    // The tab loads one page of projects, collects that page's ids, and fetches
    // ALL summaries in a SINGLE batched call (never per-row / per-site).
    await waitFor(() => expect(summariesSpy).toHaveBeenCalledTimes(1));
    expect(summariesSpy).toHaveBeenCalledWith([1, 2, 3]);
  });

  test('renders every project chip from the single batched response', async () => {
    summariesSpy.mockResolvedValue({
      summaries: [
        { site_id: 1, summary: summary() },
        { site_id: 2, summary: summary({ status: 'needs_reconciliation', status_label: 'Needs reconciliation' }) },
        { site_id: 3, summary: summary() }
      ]
    });

    renderCompanyProjectsTab();

    // Every rendered row gets a chip fed from the one batched response. Wait for
    // the resolved labels so the grid's refreshCells has run after the single
    // query resolved.
    await waitFor(() => expect(screen.getAllByText('Matched').length).toBe(2));
    expect(screen.getByText('Needs reconciliation')).toBeInTheDocument();
    expect(screen.getAllByTestId('inventory-reconciliation-chip').length).toBe(3);
    expect(summariesSpy).toHaveBeenCalledTimes(1);
  });

  test('never issues a per-row / per-site reconciliation request', async () => {
    summariesSpy.mockResolvedValue({
      summaries: [
        { site_id: 1, summary: summary() },
        { site_id: 2, summary: summary() },
        { site_id: 3, summary: summary() }
      ]
    });

    renderCompanyProjectsTab();

    await waitFor(() => expect(screen.getAllByTestId('inventory-reconciliation-chip').length).toBe(3));

    // Exactly one call, and that call carried the full batch of ids — a per-row
    // implementation would instead produce 3 calls each with a single id.
    expect(summariesSpy).toHaveBeenCalledTimes(1);
    summariesSpy.mock.calls.forEach(call => {
      expect(Array.isArray(call[0])).toBe(true);
      expect(call[0]).toEqual([1, 2, 3]);
      // A single-id argument would signal a regression into per-site fetching.
      expect(call[0].length).toBeGreaterThan(1);
    });
  });
});
