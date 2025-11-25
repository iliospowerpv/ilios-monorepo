import { screen, render, act, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { CommentsList } from '../CommentsList';

jest.mock('../../../../../../contexts/notifications/notifications', () => ({
  useNotify: jest.fn(() => jest.fn())
}));

jest.mock('../../../../../../api', () => ({
  ApiClient: {
    dueDiligence: {
      documentComments: () => {
        return Promise.resolve({
          items: [
            {
              id: 6,
              entity_id: 22,
              text: 'and another one',
              created_at: '2024-04-22T13:04:23.245422',
              updated_at: '2024-04-22T13:04:23.245422',
              first_name: 'Oleksii',
              last_name: 'Bohdan'
            },
            {
              id: 5,
              entity_id: 22,
              text: 'One more test comment',
              created_at: '2024-04-22T09:00:28.466108',
              updated_at: '2024-04-22T09:00:28.466108',
              first_name: 'Yulian',
              last_name: 'Terletskyi'
            }
          ]
        });
      }
    }
  }
}));

jest.mock('../../../../../../components/forms/CommentListItem/CommentListItem', () => ({
  __esModule: true,
  default: ({
    user,
    text
  }: {
    user: {
      first_name: string;
      last_name: string;
    };
    text: string;
  }) => <div>{user.first_name + ' ' + user.last_name + ': "' + text + '"'}</div>
}));

describe('CommentsList component', () => {
  it('should render component correctly', async () => {
    const queryClient = new QueryClient();
    await act(() =>
      render(
        <QueryClientProvider client={queryClient}>
          <CommentsList documentId={22} />
        </QueryClientProvider>
      )
    );
    await waitFor(() => {
      expect(screen.getByText('Oleksii Bohdan: "and another one"')).toBeInTheDocument();
      expect(screen.getByText('Yulian Terletskyi: "One more test comment"')).toBeInTheDocument();
    });
  });
});
