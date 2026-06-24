import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import HomeProjects from '../HomeProjects';
import { ApiClient } from '../../../../../api';
import type { WorkspaceProject } from '../../../../../api/workspace';
import type {
  InventoryReconciliationSummary,
  InventoryReconciliationSummaryBatchResponse
} from '../../../../../types/telemetryV2';

const project = (overrides: Partial<WorkspaceProject> = {}): WorkspaceProject => ({
  project_id: 1,
  project_name: 'Project One',
  company_id: 10,
  company_name: 'Acme',
  address: null,
  city: null,
  state: null,
  system_size_ac: null,
  system_size_dc: null,
  ...overrides
});

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

const renderHomeProjects = (projects: WorkspaceProject[]) => {
  // A fresh QueryClient per render keeps the reconciliation cache from leaking
  // between tests (so the call-count assertions are honest).
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>
        <HomeProjects projects={projects} />
      </QueryClientProvider>
    </BrowserRouter>
  );
};

describe('HomeProjects reconciliation batching', () => {
  let summariesSpy: jest.SpyInstance;

  beforeEach(() => {
    summariesSpy = jest.spyOn(ApiClient.telemetryV2, 'getInventoryReconciliationSummaries');
  });

  afterEach(() => {
    summariesSpy.mockRestore();
  });

  test('fires exactly one summaries request for a card set of multiple projects', async () => {
    const projects = [
      project({ project_id: 1, project_name: 'Project One' }),
      project({ project_id: 2, project_name: 'Project Two' }),
      project({ project_id: 3, project_name: 'Project Three' })
    ];
    const response: InventoryReconciliationSummaryBatchResponse = {
      summaries: [
        { site_id: 1, summary: summary({ status_label: 'Matched' }) },
        { site_id: 2, summary: summary({ status: 'needs_reconciliation', status_label: 'Needs reconciliation' }) },
        { site_id: 3, summary: summary({ status_label: 'Matched' }) }
      ]
    };
    summariesSpy.mockResolvedValue(response);

    renderHomeProjects(projects);

    await waitFor(() => expect(summariesSpy).toHaveBeenCalledTimes(1));
    // The single batched request carries every card's site id (sorted), not one
    // request per card.
    expect(summariesSpy).toHaveBeenCalledWith([1, 2, 3]);
  });

  test('feeds every card chip from the single batched response', async () => {
    const projects = [
      project({ project_id: 1, project_name: 'Project One' }),
      project({ project_id: 2, project_name: 'Project Two' }),
      project({ project_id: 3, project_name: 'Project Three' })
    ];
    summariesSpy.mockResolvedValue({
      summaries: [
        { site_id: 1, summary: summary({ status_label: 'Matched' }) },
        { site_id: 2, summary: summary({ status: 'needs_reconciliation', status_label: 'Needs reconciliation' }) },
        { site_id: 3, summary: summary({ status_label: 'Matched' }) }
      ]
    });

    renderHomeProjects(projects);

    // Each of the three cards renders a chip fed from the one batched response.
    await waitFor(() => {
      const chips = screen.getAllByTestId('inventory-reconciliation-chip');
      expect(chips).toHaveLength(3);
      expect(chips.every(chip => chip.getAttribute('data-state') === 'ready')).toBe(true);
    });
    expect(screen.getAllByText('Matched')).toHaveLength(2);
    expect(screen.getByText('Needs reconciliation')).toBeInTheDocument();
    expect(summariesSpy).toHaveBeenCalledTimes(1);
  });

  test('each available chip deep-links to its project Reconciliation view', async () => {
    const projects = [
      project({ project_id: 1, project_name: 'Project One' }),
      project({ project_id: 2, project_name: 'Project Two' })
    ];
    summariesSpy.mockResolvedValue({
      summaries: [
        { site_id: 1, summary: summary({ status_label: 'Matched' }) },
        { site_id: 2, summary: summary({ status_label: 'Matched' }) }
      ]
    });

    renderHomeProjects(projects);

    // Each ready chip is a link routed to that site's Reconciliation tab.
    await waitFor(() => {
      const links = screen.getAllByTestId('inventory-reconciliation-chip-link');
      expect(links).toHaveLength(2);
    });
    const links = screen.getAllByTestId('inventory-reconciliation-chip-link');
    expect(links[0]).toHaveAttribute('href', '/project-hub/projects/1/reconciliation');
    expect(links[1]).toHaveAttribute('href', '/project-hub/projects/2/reconciliation');
    // The deep link adds no extra reconciliation request — still one batched call.
    expect(summariesSpy).toHaveBeenCalledTimes(1);
  });

  test('does not issue a request when there are no projects', () => {
    summariesSpy.mockResolvedValue({ summaries: [] });
    renderHomeProjects([]);
    expect(summariesSpy).not.toHaveBeenCalled();
  });
});
