import { screen, render, act, waitFor, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { NewComment } from '../NewComment';
import { ApiClient } from '../../../../../../api';

jest.mock('../../../../../../contexts/notifications/notifications', () => ({
  useNotify: () => jest.fn()
}));

jest.mock('../../../../../../contexts/auth/auth', () => ({
  useAuth: () => ({
    user: {
      first_name: 'Rob',
      last_name: 'Pike'
    }
  })
}));

jest.mock('../../../../../../api', () => ({
  ApiClient: {
    dueDiligence: {
      postDocumentComment: jest.fn()
    }
  }
}));

describe('NewComment component', () => {
  class ResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  }

  beforeAll(() => {
    global.ResizeObserver = ResizeObserver;
  });

  it('should render component correctly', async () => {
    const queryClient = new QueryClient();
    await act(() =>
      render(
        <QueryClientProvider client={queryClient}>
          <NewComment entityId={22} boardId={7} entityType="document" fileId={122} />
        </QueryClientProvider>
      )
    );

    const avatarNode = screen.getByTestId('document-new_comment-avatar');
    expect(avatarNode).toBeInTheDocument();
    expect(avatarNode.innerHTML).toBe('RP');

    const descriptionInputArea = screen.getByPlaceholderText('Add a comment…');
    expect(descriptionInputArea).toBeInTheDocument();

    fireEvent.change(descriptionInputArea, { target: { value: 'A plain comment' } });

    await waitFor(() => {
      const saveButton = screen.getByText('Save');
      expect(saveButton).toBeEnabled();
      fireEvent.click(saveButton);
    });

    await waitFor(() => {
      expect(ApiClient.dueDiligence.postDocumentComment).toHaveBeenCalledTimes(1);
      expect(ApiClient.dueDiligence.postDocumentComment).toHaveBeenCalledWith(
        22,
        'A plain comment',
        [],
        'document',
        122,
        'Diligence'
      );
    });
  });
});
