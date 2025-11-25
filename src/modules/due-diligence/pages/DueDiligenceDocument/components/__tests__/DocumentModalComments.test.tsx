import { screen, render, fireEvent } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';

import DocumentModalComments from '../DocumentModalComments';

jest.mock('../../../../../../contexts/notifications/notifications', () => ({
  useNotify: () => jest.fn()
}));

jest.mock('../NewComment', () => ({
  __esModule: true,
  default: () => <div>NewComment-component-placeholder</div>
}));

jest.mock('../CommentsList', () => ({
  __esModule: true,
  default: () => <div>CommentsList-component-placeholder</div>
}));

describe('DocumentModalComments component', () => {
  it('should render component correctly', () => {
    const queryClient = new QueryClient();

    render(
      <QueryClientProvider client={queryClient}>
        <DocumentModalComments termId={2} termKey="Rent Amount" siteId={2} comments={null} documentId={22} />
      </QueryClientProvider>
    );

    const addCommentBtn = screen.getByTestId('add-comment__btn');
    fireEvent.click(addCommentBtn);

    expect(screen.getByText('Comments')).toBeInTheDocument();
    expect(screen.getByText('NewComment-component-placeholder')).toBeInTheDocument();
  });
});
