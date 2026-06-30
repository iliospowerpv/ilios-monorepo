import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const mockGuidance = jest.fn();
jest.mock('../../../../../../../../../api', () => ({
  ApiClient: {
    dueDiligence: {
      getDataRoomGuidance: (...args: unknown[]) => mockGuidance(...args)
    }
  }
}));

import GuidanceDashboardPanel from '../GuidanceDashboardPanel';

const stage = {
  section_id: 10,
  section_key: 'legal',
  section_name: 'Legal',
  expected: 2,
  present: 1,
  missing: 1,
  needs_update: 0,
  optional: 0,
  archived: 0,
  version_count: 3,
  promotion_status: 'in_progress' as const,
  missing_documents: [{ kind: 'title_policy', name: 'Title Policy', description: null, required: true, position: 1 }]
};

const renderPanel = (onAddMissingDocument = jest.fn()) => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <GuidanceDashboardPanel siteId={123} onAddMissingDocument={onAddMissingDocument} />
    </QueryClientProvider>
  );
  return onAddMissingDocument;
};

beforeEach(() => {
  jest.clearAllMocks();
  mockGuidance.mockResolvedValue({ items: [stage] });
});

describe('GuidanceDashboardPanel actionable missing documents', () => {
  it('routes a missing expected document into the Add Document flow with identity and stage', async () => {
    const onAdd = renderPanel();

    fireEvent.click(screen.getByText('Data Room Guidance'));

    const link = await screen.findByTestId('guidance-add-missing-legal-title_policy', {}, { timeout: 3000 });
    fireEvent.click(link);

    expect(onAdd).toHaveBeenCalledTimes(1);
    const [docArg, stageArg] = onAdd.mock.calls[0];
    expect(docArg.name).toBe('Title Policy');
    expect(stageArg.section_id).toBe(10);
    expect(stageArg.section_key).toBe('legal');
  });
});
