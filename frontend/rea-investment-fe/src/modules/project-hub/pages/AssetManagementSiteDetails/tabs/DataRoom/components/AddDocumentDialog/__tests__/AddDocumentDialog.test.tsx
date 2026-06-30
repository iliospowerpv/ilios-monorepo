import React from 'react';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

const mockCheck = jest.fn();
const mockCreate = jest.fn();
jest.mock('../../../../../../../../../api', () => ({
  ApiClient: {
    dueDiligence: {
      checkDuplicateDocument: (...args: unknown[]) => mockCheck(...args),
      createCustomDocument: (...args: unknown[]) => mockCreate(...args)
    }
  }
}));

const mockNotify = jest.fn();
jest.mock('../../../../../../../../../contexts/notifications/notifications', () => ({
  useNotify: () => mockNotify
}));

import AddDocumentDialog from '../AddDocumentDialog';

const exactCandidate = {
  document_id: 7,
  name: 'PVsyst Final',
  kind: 'pvsyst',
  section_id: 10,
  section_name: 'Engineering',
  files_count: 2,
  is_archived: false,
  match_type: 'exact' as const,
  score: 0.99
};

type DialogProps = React.ComponentProps<typeof AddDocumentDialog>;

const renderDialog = (props: Partial<DialogProps> = {}) => {
  const queryClient = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  const merged: DialogProps = {
    open: true,
    onClose: jest.fn(),
    siteId: 123,
    sections: [{ id: 10, name: 'Engineering' }],
    onNavigateToDocument: jest.fn(),
    ...props
  };
  const utils = render(
    <QueryClientProvider client={queryClient}>
      <AddDocumentDialog {...merged} />
    </QueryClientProvider>
  );
  return { ...utils, props: merged };
};

beforeEach(() => {
  jest.clearAllMocks();
});

describe('AddDocumentDialog duplicate guidance', () => {
  it('surfaces a match and gates creation behind explicit confirmation', async () => {
    mockCheck.mockResolvedValue({ proposed_name: 'PVsyst', has_match: true, candidates: [exactCandidate] });
    renderDialog({ prefill: { sectionId: 10 } });

    fireEvent.change(screen.getByTestId('add-document-name'), { target: { value: 'PVsyst' } });

    await screen.findByTestId('add-document-match-alert', {}, { timeout: 3000 });
    expect(mockCheck).toHaveBeenCalledWith(123, 'PVsyst');
    expect(screen.getByText('PVsyst Final')).toBeInTheDocument();

    const submit = screen.getByTestId('add-document-submit');
    expect(submit).toBeDisabled();

    fireEvent.click(screen.getByTestId('add-document-confirm-separate'));
    await waitFor(() => expect(submit).not.toBeDisabled());
    expect(mockCreate).not.toHaveBeenCalled();
  });

  it('routes Upload version into the existing document version path without creating a duplicate', async () => {
    mockCheck.mockResolvedValue({ proposed_name: 'PVsyst', has_match: true, candidates: [exactCandidate] });
    const { props } = renderDialog();

    fireEvent.change(screen.getByTestId('add-document-name'), { target: { value: 'PVsyst' } });
    await screen.findByTestId('add-document-match-alert', {}, { timeout: 3000 });

    fireEvent.click(screen.getByTestId('add-document-upload-version-7'));

    expect(props.onNavigateToDocument).toHaveBeenCalledWith(7);
    expect(props.onClose).toHaveBeenCalled();
    expect(mockCreate).not.toHaveBeenCalled();
  });

  it('creates immediately when no similar document exists', async () => {
    mockCheck.mockResolvedValue({ proposed_name: 'Unique Doc', has_match: false, candidates: [] });
    mockCreate.mockResolvedValue({ message: 'created' });
    const { props } = renderDialog({ prefill: { sectionId: 10 } });

    fireEvent.change(screen.getByTestId('add-document-name'), { target: { value: 'Unique Doc' } });
    await waitFor(() => expect(mockCheck).toHaveBeenCalledWith(123, 'Unique Doc'), { timeout: 3000 });
    expect(screen.queryByTestId('add-document-match-alert')).not.toBeInTheDocument();

    const submit = screen.getByTestId('add-document-submit');
    expect(submit).not.toBeDisabled();
    fireEvent.click(submit);

    await waitFor(() => expect(mockCreate).toHaveBeenCalledWith(123, 10, 'Unique Doc', undefined));
    await waitFor(() => expect(props.onClose).toHaveBeenCalled());
  });

  it('prefills the name and section for a missing expected document', async () => {
    mockCheck.mockResolvedValue({ proposed_name: 'Title Policy', has_match: false, candidates: [] });
    mockCreate.mockResolvedValue({ message: 'created' });
    renderDialog({ prefill: { name: 'Title Policy', sectionId: 10 } });

    const nameInput = screen.getByTestId('add-document-name') as HTMLInputElement;
    expect(nameInput.value).toBe('Title Policy');

    await waitFor(() => expect(mockCheck).toHaveBeenCalledWith(123, 'Title Policy'), { timeout: 3000 });

    fireEvent.click(screen.getByTestId('add-document-submit'));
    await waitFor(() => expect(mockCreate).toHaveBeenCalledWith(123, 10, 'Title Policy', undefined));
  });
});
