import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

// --- mocks (hoisted) ---------------------------------------------------------------------------
const mockGetDocuments = jest.fn();
const mockGetGuidance = jest.fn();
const mockDocInfo = jest.fn();

jest.mock('../../../../../../../api', () => ({
  ApiClient: {
    dueDiligence: {
      getDocuments: (...args: unknown[]) => mockGetDocuments(...args),
      getDataRoomGuidance: (...args: unknown[]) => mockGetGuidance(...args),
      docInfo: (...args: unknown[]) => mockDocInfo(...args)
    }
  }
}));

jest.mock('../../../../../../../contexts/auth/auth', () => ({
  useAuth: () => ({ user: { is_system_user: true } })
}));

jest.mock('../../../../../../../hooks/useFocusHighlight', () => ({
  useFocusHighlight: () => ({ focusState: {} })
}));

// Heavy children that fetch on their own are stubbed so this test isolates the deep-link wiring.
jest.mock('../components/ProjectSummaryPanel', () => ({ __esModule: true, default: () => null }));
jest.mock('../components/ExpectedDocumentsPanel', () => ({ __esModule: true, default: () => null }));
jest.mock('../components/GuidanceDashboardPanel', () => ({ __esModule: true, default: () => null }));
jest.mock('../components/ManageTemplatesDialog', () => ({ __esModule: true, default: () => null }));
jest.mock('../../../../../../../components/common/tables/components/SearchAndActions/SearchAndActions', () => ({
  __esModule: true,
  default: () => null
}));
jest.mock(
  '../../../../../../../modules/due-diligence/pages/Site/tabs/Diligence/components/RecursiveAccordion/RecursiveAccordion',
  () => ({ __esModule: true, default: () => null })
);
jest.mock('../../../../../../../modules/due-diligence/pages/DueDiligenceDocument/components/DocumentList', () => ({
  __esModule: true,
  default: () => null
}));

// The Add Document dialog is the deep link's target: render a probe exposing its open state + prefill.
jest.mock('../components/AddDocumentDialog', () => ({
  __esModule: true,
  default: ({ open, prefill }: { open: boolean; prefill: { name?: string } | null }) => {
    if (!open) return null;
    const ReactLib = require('react');
    return ReactLib.createElement(
      'div',
      { 'data-testid': 'add-document-dialog' },
      prefill ? prefill.name : ''
    );
  }
}));

import DataRoom from '../DataRoom';

const guidanceStage = {
  section_id: 10,
  section_key: 'legal',
  section_name: 'Legal',
  expected: 2,
  present: 1,
  missing: 1,
  needs_update: 0,
  optional: 0,
  archived: 0,
  version_count: 0,
  promotion_status: 'in_progress' as const,
  missing_documents: [{ kind: 'title_policy', name: 'Title Policy', description: null, required: true, position: 1 }]
};

const renderAt = (search: string) => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[`/data-room${search}`]}>
        <DataRoom {...({ siteDetails: { id: 123, name: 'Test Project' } } as any)} />
      </MemoryRouter>
    </QueryClientProvider>
  );
};

beforeEach(() => {
  jest.clearAllMocks();
  mockGetDocuments.mockResolvedValue({ items: [] });
  mockDocInfo.mockResolvedValue(null);
  mockGetGuidance.mockResolvedValue({ items: [guidanceStage] });
});

describe('DataRoom assistant deep link (#107)', () => {
  it('opens the prefilled Add Document dialog for a still-missing target', async () => {
    renderAt('?addDocKind=title_policy&addDocSection=10');

    const dialog = await screen.findByTestId('add-document-dialog', {}, { timeout: 3000 });
    expect(dialog).toHaveTextContent('Title Policy');
    expect(mockGetGuidance).toHaveBeenCalledWith(123);
  });

  it('shows an honest notice and opens nothing when the target is no longer missing', async () => {
    renderAt('?addDocKind=ghost_doc&addDocSection=10');

    await screen.findByText(/no longer listed as missing/i, {}, { timeout: 3000 });
    expect(screen.queryByTestId('add-document-dialog')).not.toBeInTheDocument();
  });
});
