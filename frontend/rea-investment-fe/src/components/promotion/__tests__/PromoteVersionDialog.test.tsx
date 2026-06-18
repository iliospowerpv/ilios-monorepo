import React from 'react';
import { render, screen, fireEvent, waitFor, within } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const mockGetDiff = jest.fn();
const mockPromote = jest.fn();
jest.mock('../../../api', () => ({
  ApiClient: {
    assumptions: {
      getPromotionDiff: (...args: unknown[]) => mockGetDiff(...args),
      promoteVersion: (...args: unknown[]) => mockPromote(...args)
    }
  }
}));

const mockNotify = jest.fn();
jest.mock('../../../contexts/notifications/notifications', () => ({
  useNotify: () => mockNotify
}));

import { PromoteVersionDialog } from '../PromoteVersionDialog';
import type { PromoteVersionContext } from '../types';

const diff = {
  has_changes: true,
  summary: { changed: 1, added: 1, removed: 1 },
  changes: [
    { type: 'changed', field_id: 1, field_name: 'Module Capacity (kW)', current_value: '100', new_value: '120' },
    { type: 'added', field_id: 2, field_name: 'PPA Rate', current_value: null, new_value: '0.12' },
    { type: 'removed', field_id: 3, field_name: 'Old Field', current_value: '5', new_value: null }
  ]
};

const noChangesDiff = {
  has_changes: false,
  summary: { changed: 0, added: 0, removed: 0 },
  changes: []
};

const baseContext: PromoteVersionContext = {
  documentId: 5,
  fileId: 9,
  launchedFieldLabel: 'Module Capacity (kW)',
  documentName: 'Power Purchase Agreement',
  documentTypeLabel: 'PPA',
  fileName: 'PPA_v3.pdf',
  uploadedAt: '2026-01-15T10:00:00Z',
  isActual: true
};

const renderDialog = (props: Partial<React.ComponentProps<typeof PromoteVersionDialog>> = {}) => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <PromoteVersionDialog open siteId={123} context={baseContext} onClose={jest.fn()} {...props} />
    </QueryClientProvider>
  );
};

beforeEach(() => {
  jest.clearAllMocks();
  mockGetDiff.mockResolvedValue(diff);
  mockPromote.mockResolvedValue({ facts_promoted: 2, baseline_updated: false });
});

describe('PromoteVersionDialog (shared)', () => {
  it('renders the Scope D document-version context block from metadata', async () => {
    renderDialog();
    const context = await screen.findByTestId('promote-version-context');
    expect(within(context).getByText('Power Purchase Agreement')).toBeInTheDocument();
    expect(within(context).getByText('PPA')).toBeInTheDocument();
    expect(within(context).getByText('Actual')).toBeInTheDocument();
    expect(within(context).getByText(/File: PPA_v3\.pdf/)).toBeInTheDocument();
    expect(within(context).getByText(/Uploaded:/)).toBeInTheDocument();
    expect(within(context).getByText('Document #5 · Version #9')).toBeInTheDocument();
  });

  it('names the launched field in the scope warning when one is provided', async () => {
    renderDialog();
    const warning = await screen.findByTestId('promote-scope-warning');
    expect(warning).toHaveTextContent('every accepted value on it');
    expect(warning).toHaveTextContent('not just');
    expect(warning).toHaveTextContent('Module Capacity (kW)');
  });

  it('uses a generic scope warning when no launched field is provided', async () => {
    renderDialog({ context: { documentId: 5, fileId: 9 } });
    const warning = await screen.findByTestId('promote-scope-warning');
    expect(warning).toHaveTextContent('every accepted value on it');
    expect(warning).not.toHaveTextContent('not just');
  });

  it('shows the diff summary, grouped rows, removed note, and highlights the launched field', async () => {
    renderDialog();
    const summary = await screen.findByTestId('promote-summary');
    expect(summary).toHaveTextContent('Changed: 1');
    expect(summary).toHaveTextContent('Added: 1');
    expect(summary).toHaveTextContent('No longer carried: 1');

    const rows = screen.getAllByTestId('promote-change-row');
    expect(rows).toHaveLength(3);
    expect(screen.getByTestId('promote-removed-note')).toBeInTheDocument();

    const highlighted = rows.find(row => within(row).queryByText('Module Capacity (kW)'));
    expect(highlighted).toHaveClass('Mui-selected');
  });

  it('shows a loading indicator and disables confirm while the diff loads', async () => {
    mockGetDiff.mockReturnValue(new Promise(() => undefined));
    renderDialog();
    expect(await screen.findByTestId('promote-diff-loading')).toBeInTheDocument();
    expect(screen.getByTestId('promote-confirm-btn')).toBeDisabled();
  });

  it('shows an honest error state and disables confirm when the diff fails to load', async () => {
    mockGetDiff.mockRejectedValue(new Error('boom'));
    renderDialog();
    expect(await screen.findByTestId('promote-diff-error')).toBeInTheDocument();
    expect(screen.getByTestId('promote-confirm-btn')).toBeDisabled();
  });

  it('disables confirm and shows the no-changes message when nothing would change', async () => {
    mockGetDiff.mockResolvedValue(noChangesDiff);
    renderDialog();
    expect(await screen.findByTestId('promote-no-changes')).toBeInTheDocument();
    expect(screen.getByTestId('promote-confirm-btn')).toBeDisabled();
  });

  it('promotes the whole version with a null-trimmed payload and runs success callbacks', async () => {
    const onClose = jest.fn();
    const onPromoted = jest.fn();
    renderDialog({ onClose, onPromoted });

    await screen.findByTestId('promote-summary');
    fireEvent.click(screen.getByTestId('promote-confirm-btn'));

    await waitFor(() => expect(mockPromote).toHaveBeenCalledTimes(1));
    expect(mockPromote).toHaveBeenCalledWith(123, { document_id: 5, file_id: 9, notes: null });
    await waitFor(() => expect(onPromoted).toHaveBeenCalled());
    expect(onClose).toHaveBeenCalled();
    expect(mockNotify).toHaveBeenCalled();
  });

  it('passes trimmed promotion notes through to the payload', async () => {
    renderDialog();
    await screen.findByTestId('promote-summary');
    fireEvent.change(screen.getByTestId('promote-notes'), { target: { value: '  lender approved  ' } });
    fireEvent.click(screen.getByTestId('promote-confirm-btn'));

    await waitFor(() => expect(mockPromote).toHaveBeenCalledTimes(1));
    expect(mockPromote).toHaveBeenCalledWith(123, { document_id: 5, file_id: 9, notes: 'lender approved' });
  });

  it('requires a re-confirmation when the diff changes between open and confirm', async () => {
    const diff2 = {
      has_changes: true,
      summary: { changed: 2, added: 0, removed: 0 },
      changes: [
        { type: 'changed', field_id: 1, field_name: 'Module Capacity (kW)', current_value: '100', new_value: '130' },
        { type: 'changed', field_id: 4, field_name: 'Tilt', current_value: '10', new_value: '15' }
      ]
    };
    mockGetDiff.mockResolvedValueOnce(diff).mockResolvedValue(diff2);
    renderDialog();

    await screen.findByTestId('promote-summary');
    fireEvent.click(screen.getByTestId('promote-confirm-btn'));

    expect(await screen.findByTestId('promote-reconfirm-warning')).toBeInTheDocument();
    expect(mockPromote).not.toHaveBeenCalled();

    fireEvent.click(screen.getByTestId('promote-confirm-btn'));
    await waitFor(() => expect(mockPromote).toHaveBeenCalledTimes(1));
  });

  it('cancels without promoting', async () => {
    const onClose = jest.fn();
    renderDialog({ onClose });
    await screen.findByTestId('promote-summary');
    fireEvent.click(screen.getByTestId('promote-cancel-btn'));
    expect(onClose).toHaveBeenCalled();
    expect(mockPromote).not.toHaveBeenCalled();
  });
});
