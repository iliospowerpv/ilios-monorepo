import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const mockGetFileParsingResult = jest.fn();
const mockDocumentParsingStatus = jest.fn();
const mockGetParseRunHistory = jest.fn();
const mockGetCandidateFacts = jest.fn();
const mockGetPromotionHistory = jest.fn();
jest.mock('../../../../../../api', () => ({
  ApiClient: {
    dueDiligence: {
      getFileParsingResult: (...args: unknown[]) => mockGetFileParsingResult(...args),
      documentParsingStatus: (...args: unknown[]) => mockDocumentParsingStatus(...args),
      getParseRunHistory: (...args: unknown[]) => mockGetParseRunHistory(...args),
      documentStartParsing: jest.fn(),
      bulkAcceptAIValues: jest.fn(),
      togglePoisonPill: jest.fn()
    },
    assumptions: {
      getCandidateFacts: (...args: unknown[]) => mockGetCandidateFacts(...args),
      getPromotionHistory: (...args: unknown[]) => mockGetPromotionHistory(...args)
    }
  }
}));

const mockUseAuth = jest.fn();
jest.mock('../../../../../../contexts/auth/auth', () => ({
  useAuth: () => mockUseAuth()
}));

const mockNotify = jest.fn();
jest.mock('../../../../../../contexts/notifications/notifications', () => ({
  useNotify: () => mockNotify
}));

// Stub the shared promote dialog so this suite exercises only the Data Room
// entry point (gating + context wiring + invalidation), not the dialog internals
// (covered by the shared PromoteVersionDialog suite).
jest.mock('../../../../../../components/promotion', () => {
  const ReactLib = jest.requireActual('react');
  return {
    PromoteVersionDialog: ({ open, context, onPromoted }: any) =>
      open
        ? ReactLib.createElement(
            'div',
            { 'data-testid': 'stub-promote-dialog' },
            ReactLib.createElement('span', { 'data-testid': 'stub-context' }, JSON.stringify(context)),
            ReactLib.createElement(
              'button',
              { 'data-testid': 'stub-onpromoted', onClick: () => onPromoted && onPromoted() },
              'promoted'
            )
          )
        : null
  };
});

jest.mock('../../../../../../components/common/ParsingStatus', () => ({
  ParsingStatusBadge: () => null,
  ParseErrorMessage: () => null,
  TruncationWarning: () => null,
  ParsingMetadata: () => null,
  ParsingProgressIndicator: () => null
}));

jest.mock('../PDFViewer', () => () => null);
// Stub the term field so we can fire its onValuePersisted callback (the signal
// the real accept/override flow emits) without standing up react-hook-form.
jest.mock('../DocumentTermUserInputField', () => {
  const ReactLib = jest.requireActual('react');
  return {
    __esModule: true,
    default: ReactLib.forwardRef((props: any) =>
      ReactLib.createElement(
        'button',
        {
          'data-testid': 'stub-accept-field',
          onClick: () => props.onValuePersisted && props.onValuePersisted()
        },
        'accept'
      )
    )
  };
});
jest.mock('../DocumentPoisonPill', () => () => null);
jest.mock('../DocumentModalComments', () => () => null);
jest.mock('@cyntler/react-doc-viewer', () => ({
  __esModule: true,
  default: () => null,
  DocViewerRenderers: []
}));

import DocumentModal from '../DocumentModal';

const file = {
  id: 9,
  author: 'Ada Lovelace',
  filename: 'PPA.pdf',
  extension: 'pdf',
  created_at: '2026-01-15T10:00:00Z',
  is_actual: true
};

const renderModal = (queryClient: QueryClient) =>
  render(
    <QueryClientProvider client={queryClient}>
      <DocumentModal
        open
        file={file as any}
        fileUrl="http://example.com/ppa.pdf"
        onClose={jest.fn()}
        documentId={2}
        siteId={1}
        boardId={7}
        taskId={3}
      />
    </QueryClientProvider>
  );

const makeClient = () => new QueryClient({ defaultOptions: { queries: { retry: false } } });

beforeEach(() => {
  jest.clearAllMocks();
  mockGetFileParsingResult.mockResolvedValue({ keys: [] });
  mockDocumentParsingStatus.mockResolvedValue({ status: 'completed' });
  mockGetParseRunHistory.mockResolvedValue({ runs: [] });
  mockGetCandidateFacts.mockResolvedValue({ total: 3 });
  mockGetPromotionHistory.mockResolvedValue({ promotions: [] });
  mockUseAuth.mockReturnValue({ user: { is_system_user: true } });
});

describe('DocumentModal — Data Room promote entry point', () => {
  it('shows an enabled Promote button when the version has promotable candidates', async () => {
    renderModal(makeClient());
    const button = await screen.findByTestId('dataroom-promote-btn');
    await waitFor(() => expect(button).toBeEnabled());
    expect(mockGetCandidateFacts).toHaveBeenCalledWith(1, 9);
  });

  it('disables the Promote button when there are no candidates to promote', async () => {
    mockGetCandidateFacts.mockResolvedValue({ total: 0 });
    renderModal(makeClient());
    await waitFor(() => expect(screen.getByTestId('dataroom-promote-btn')).toBeDisabled());
  });

  it('shows the Promote button as completed (disabled) when this version was already promoted', async () => {
    mockGetCandidateFacts.mockResolvedValue({ total: 0 });
    mockGetPromotionHistory.mockResolvedValue({ promotions: [{ id: 1, document_id: 2, file_id: 9 }] });
    renderModal(makeClient());
    const button = await screen.findByTestId('dataroom-promote-btn');
    await waitFor(() => expect(button).toHaveTextContent('Promoted'));
    expect(button).toBeDisabled();
  });

  it('always renders the Accept All button, disabled when there is nothing to accept', async () => {
    renderModal(makeClient());
    await waitFor(() => expect(screen.getByTestId('dataroom-accept-all-btn')).toBeDisabled());
  });

  it('shows Accept All as completed when the latest successful run has no pending values', async () => {
    mockGetParseRunHistory.mockResolvedValue({ runs: [{ id: 50, is_latest: true, status: 'completed' }] });
    mockGetFileParsingResult.mockResolvedValue({
      keys: [
        {
          id: 201,
          name: 'ppa_rate',
          value: '0.12',
          ai_value: '0.12',
          is_poison_pill: false,
          poison_pill_detailed: null,
          legal_term: null,
          comments: null,
          evidence: null,
          is_baseline_driving: false
        }
      ]
    });
    renderModal(makeClient());
    const acceptBtn = await screen.findByTestId('dataroom-accept-all-btn');
    await waitFor(() => expect(acceptBtn).toHaveTextContent('Accepted'));
    expect(acceptBtn).toBeDisabled();
  });

  it('does not show Accept All as completed when extracted values fail to load', async () => {
    mockGetParseRunHistory.mockResolvedValue({ runs: [{ id: 50, is_latest: true, status: 'completed' }] });
    mockGetFileParsingResult.mockRejectedValue(new Error('boom'));
    renderModal(makeClient());
    const acceptBtn = await screen.findByTestId('dataroom-accept-all-btn');
    await waitFor(() => expect(acceptBtn).toBeDisabled());
    expect(acceptBtn).not.toHaveTextContent('Accepted');
  });

  it('hides the Promote button when the user lacks Diligence edit rights', async () => {
    mockUseAuth.mockReturnValue({
      user: { is_system_user: false, role: { permissions: { Diligence: { edit: false } } } }
    });
    renderModal(makeClient());
    await screen.findByText('Document Details');
    expect(screen.queryByTestId('dataroom-promote-btn')).not.toBeInTheDocument();
    expect(mockGetCandidateFacts).not.toHaveBeenCalled();
  });

  it('shows the Promote button for a non-system user who holds Diligence edit rights', async () => {
    mockUseAuth.mockReturnValue({
      user: { is_system_user: false, role: { permissions: { Diligence: { edit: true } } } }
    });
    renderModal(makeClient());
    expect(await screen.findByTestId('dataroom-promote-btn')).toBeInTheDocument();
  });

  it('opens the shared dialog with file-version context derived from the FileItem', async () => {
    renderModal(makeClient());
    const button = await screen.findByTestId('dataroom-promote-btn');
    await waitFor(() => expect(button).toBeEnabled());
    fireEvent.click(button);

    const context = JSON.parse((await screen.findByTestId('stub-context')).textContent || '{}');
    expect(context).toMatchObject({
      documentId: 2,
      fileId: 9,
      fileName: 'PPA.pdf',
      uploadedAt: '2026-01-15T10:00:00Z',
      isActual: true
    });
  });

  it('re-enables Promote after a value is accepted/overridden in the same modal', async () => {
    // A version that starts with no candidates: Promote is disabled until the
    // user accepts a value here, which must refresh eligibility in place.
    mockGetCandidateFacts.mockResolvedValueOnce({ total: 0 }).mockResolvedValue({ total: 1 });
    mockGetFileParsingResult.mockResolvedValue({
      keys: [
        {
          id: 101,
          name: 'module_capacity_kw',
          value: '120',
          ai_value: '120',
          is_poison_pill: false,
          poison_pill_detailed: null,
          legal_term: null,
          comments: null,
          evidence: null,
          is_baseline_driving: false
        }
      ]
    });
    renderModal(makeClient());

    const button = await screen.findByTestId('dataroom-promote-btn');
    await waitFor(() => expect(button).toBeDisabled());

    fireEvent.click(await screen.findByTestId('stub-accept-field'));

    await waitFor(() => expect(button).toBeEnabled());
    expect(mockGetCandidateFacts.mock.calls.length).toBeGreaterThanOrEqual(2);
  });

  it('invalidates the document terms and candidate caches after a successful promotion', async () => {
    const queryClient = makeClient();
    const invalidateSpy = jest.spyOn(queryClient, 'invalidateQueries');
    renderModal(queryClient);

    const button = await screen.findByTestId('dataroom-promote-btn');
    await waitFor(() => expect(button).toBeEnabled());
    fireEvent.click(button);
    fireEvent.click(await screen.findByTestId('stub-onpromoted'));

    await waitFor(() =>
      expect(invalidateSpy).toHaveBeenCalledWith({
        queryKey: ['document-terms', { siteId: 1, documentId: 2, fileId: 9 }]
      })
    );
    expect(invalidateSpy).toHaveBeenCalledWith({
      queryKey: ['site', 'assumptions', 'candidates', { siteId: 1, fileId: 9 }]
    });
  });
});
