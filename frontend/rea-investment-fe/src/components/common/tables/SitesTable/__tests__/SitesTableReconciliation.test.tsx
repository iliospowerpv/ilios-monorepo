import React from 'react';
// Register the enterprise modules (serverSide row model) the same way the app
// does in index.tsx; without this the grid cannot drive its datasource.
import 'ag-grid-enterprise';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import SitesTable from '../SitesTable';
import { AuthProvider } from '../../../../../contexts/auth/auth';
import { ApiClient } from '../../../../../api';
import { httpClient } from '../../../../../api/http-client';
import type {
  InventoryReconciliationSummary,
  InventoryReconciliationSummaryBatchResponse
} from '../../../../../types/telemetryV2';

const columns = [
  {
    headerName: 'Project Name',
    field: 'name',
    flex: 1,
    checked: true,
    isDefault: true
  },
  {
    headerName: 'Status',
    field: 'status',
    flex: 1,
    checked: true,
    isDefault: true
  }
];

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

const site = (id: number, name: string) => ({
  id,
  name,
  status: 'Operating',
  company: { id: 99, name: 'Acme' }
});

const renderTable = () => {
  // A fresh QueryClient keeps the reconciliation cache from leaking across
  // tests so the call-count assertions stay honest.
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <SitesTable columns={columns} />
        </AuthProvider>
      </QueryClientProvider>
    </BrowserRouter>
  );
};

describe('SitesTable reconciliation batching', () => {
  let httpGetSpy: jest.SpyInstance;
  let summariesSpy: jest.SpyInstance;

  beforeEach(() => {
    // ApiClient.assetManagement is Object.freeze'd, so the page of sites is fed
    // by stubbing the shared httpClient.get for the /api/sites/ endpoint (the
    // server-side grid datasource hits this). AuthProvider's token is null in
    // jsdom, so user.me is never requested.
    httpGetSpy = jest.spyOn(httpClient, 'get').mockImplementation((url: string) => {
      if (typeof url === 'string' && url.includes('/api/sites/')) {
        return Promise.resolve({
          data: {
            skip: 0,
            limit: 10,
            total: 3,
            // The grid renders a page of multiple sites in one server-side block.
            items: [site(1, 'Project One'), site(2, 'Project Two'), site(3, 'Project Three')]
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

  test('fires exactly one summaries request for a page of multiple sites', async () => {
    const response: InventoryReconciliationSummaryBatchResponse = {
      summaries: [
        { site_id: 1, summary: summary() },
        { site_id: 2, summary: summary({ status: 'needs_reconciliation', status_label: 'Needs reconciliation' }) },
        { site_id: 3, summary: summary() }
      ]
    };
    summariesSpy.mockResolvedValue(response);

    renderTable();

    // The grid loads the page (one sites request), then collects that page's
    // ids and fetches all summaries in a SINGLE batched call (never per-row).
    await waitFor(() => expect(summariesSpy).toHaveBeenCalledTimes(1));
    expect(summariesSpy).toHaveBeenCalledWith([1, 2, 3]);
  });

  test('renders each row chip from the single batched response', async () => {
    summariesSpy.mockResolvedValue({
      summaries: [
        { site_id: 1, summary: summary() },
        { site_id: 2, summary: summary({ status: 'needs_reconciliation', status_label: 'Needs reconciliation' }) },
        { site_id: 3, summary: summary() }
      ]
    });

    renderTable();

    // Every rendered row gets a chip fed from the one batched response. Wait for
    // the resolved labels so the grid's refreshCells has run after the single
    // query resolved.
    await waitFor(() => expect(screen.getAllByText('Matched').length).toBe(2));
    expect(screen.getByText('Needs reconciliation')).toBeInTheDocument();
    expect(screen.getAllByTestId('inventory-reconciliation-chip').length).toBe(3);
    // The batch endpoint is still only hit once across all three rows.
    expect(summariesSpy).toHaveBeenCalledTimes(1);
  });
});
