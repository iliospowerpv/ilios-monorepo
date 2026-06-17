import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const mockGetDiff = jest.fn();
const mockPromote = jest.fn();
jest.mock('../../../../../../../api', () => ({
  ApiClient: {
    assumptions: {
      getPromotionDiff: (...args: unknown[]) => mockGetDiff(...args),
      promoteVersion: (...args: unknown[]) => mockPromote(...args)
    }
  }
}));

const mockNotify = jest.fn();
jest.mock('../../../../../../../contexts/notifications/notifications', () => ({
  useNotify: () => mockNotify
}));

import PromoteVersionDialog from '../components/PromoteVersionDialog';

const row = {
  canonical_field: 'module_capacity_kw',
  display_label: 'Module Capacity (kW)',
  status: 'accepted_not_promoted',
  document_id: 5,
  document_version_id: 9
} as any;

const diffWithChanges = {
  has_changes: true,
  summary: { added: 1, changed: 1, removed: 1 },
  changes: [
    {
      type: 'changed',
      field_name: 'Module Capacity (kW)',
      field_id: 1,
      current_value: '1000',
      new_value: '1200',
      current_source_file_id: 8,
      new_source_file_id: 9
    },
    {
      type: 'added',
      field_name: 'Tilt (deg)',
      field_id: 2,
      current_value: null,
      new_value: '25',
      current_source_file_id: null,
      new_source_file_id: 9
    },
    {
      type: 'removed',
      field_name: 'Old Field',
      field_id: 3,
      current_value: '5',
      new_value: null,
      current_source_file_id: 7,
      new_source_file_id: null
    }
  ]
};

const diffChangedAtConfirm = {
  ...diffWithChanges,
  summary: { added: 2, changed: 1, removed: 1 },
  changes: [
    ...diffWithChanges.changes,
    {
      type: 'added',
      field_name: 'Azimuth (deg)',
      field_id: 4,
      current_value: null,
      new_value: '180',
      current_source_file_id: null,
      new_source_file_id: 9
    }
  ]
};

const diffNoChanges = { has_changes: false, summary: { added: 0, changed: 0, removed: 0 }, changes: [] };

const renderDialog = (props: Partial<React.ComponentProps<typeof PromoteVersionDialog>> = {}) => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={queryClient}>
      <PromoteVersionDialog open siteId={123} row={row} onClose={jest.fn()} {...props} />
    </QueryClientProvider>
  );
};

beforeEach(() => {
  jest.clearAllMocks();
});

describe('PromoteVersionDialog', () => {
  it('always shows the version-scope warning naming the launched field', async () => {
    mockGetDiff.mockResolvedValue(diffWithChanges);
    renderDialog();

    expect(screen.getByTestId('promote-scope-warning')).toHaveTextContent('every accepted value');
    expect(screen.getByTestId('promote-scope-warning')).toHaveTextContent('Module Capacity (kW)');
    await screen.findByTestId('promote-diff-table');
  });

  it('renders the grouped diff with the removed group flagged informational', async () => {
    mockGetDiff.mockResolvedValue(diffWithChanges);
    renderDialog();

    await screen.findByTestId('promote-diff-table');
    expect(screen.getAllByTestId('promote-change-row')).toHaveLength(3);
    expect(screen.getByTestId('promote-removed-note')).toHaveTextContent(/does not.*delete or retire/i);
    expect(screen.getByTestId('promote-confirm-btn')).not.toBeDisabled();
  });

  it('disables confirm and shows a no-changes message when nothing would change', async () => {
    mockGetDiff.mockResolvedValue(diffNoChanges);
    renderDialog();

    await screen.findByTestId('promote-no-changes');
    expect(screen.getByTestId('promote-confirm-btn')).toBeDisabled();
  });

  it('promotes with the correct payload and notifies about the unchanged baseline', async () => {
    mockGetDiff.mockResolvedValue(diffWithChanges);
    mockPromote.mockResolvedValue({
      promoted: true,
      file_id: 9,
      document_id: 5,
      promotion_id: 100,
      facts_promoted: 2,
      diff: diffWithChanges
    });
    const onClose = jest.fn();
    renderDialog({ onClose });

    await screen.findByTestId('promote-diff-table');
    // The diff is scoped to the file version (file_id <- document_version_id).
    expect(mockGetDiff).toHaveBeenCalledWith(123, 9);
    fireEvent.click(screen.getByTestId('promote-confirm-btn'));

    await waitFor(() => expect(mockPromote).toHaveBeenCalledTimes(1));
    expect(mockPromote).toHaveBeenCalledWith(123, { document_id: 5, file_id: 9, notes: null });
    await waitFor(() => expect(onClose).toHaveBeenCalled());
    expect(mockNotify).toHaveBeenCalledWith(expect.stringMatching(/baseline was NOT updated/i));
    expect(mockNotify).toHaveBeenCalledWith(expect.stringMatching(/Promoted 2 values/i));
  });

  it('requires a re-confirm when the diff changes at confirm time', async () => {
    mockGetDiff
      .mockResolvedValueOnce(diffWithChanges)
      .mockResolvedValueOnce(diffChangedAtConfirm)
      .mockResolvedValue(diffChangedAtConfirm);
    mockPromote.mockResolvedValue({
      promoted: true,
      file_id: 9,
      document_id: 5,
      promotion_id: 101,
      facts_promoted: 3,
      diff: diffChangedAtConfirm
    });
    renderDialog();

    await screen.findByTestId('promote-diff-table');
    fireEvent.click(screen.getByTestId('promote-confirm-btn'));

    // The refetch returned a different blast radius, so promotion is held.
    await screen.findByTestId('promote-reconfirm-warning');
    expect(mockPromote).not.toHaveBeenCalled();
    await waitFor(() => expect(screen.getAllByTestId('promote-change-row')).toHaveLength(4));

    // Second confirm — diff now matches what the user reviewed.
    fireEvent.click(screen.getByTestId('promote-confirm-btn'));
    await waitFor(() => expect(mockPromote).toHaveBeenCalledTimes(1));
  });

  it('maps a stale-version promotion failure to a refresh message', async () => {
    mockGetDiff.mockResolvedValue(diffWithChanges);
    mockPromote.mockRejectedValue({ response: { status: 400, data: { detail: 'File not found' } } });
    renderDialog();

    await screen.findByTestId('promote-diff-table');
    fireEvent.click(screen.getByTestId('promote-confirm-btn'));

    await waitFor(() => expect(mockNotify).toHaveBeenCalledWith(expect.stringMatching(/no longer valid/i)));
  });
});
