import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import EditMyCompany from '../EditMyCompany';
import { NotificationsProvider } from '../../../../../contexts/notifications/notifications';

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn()
}));

const createTestQueryClient = () => {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false
      }
    }
  });
};

describe('Edit My company page', () => {
  const queryClient = createTestQueryClient();

  test('renders the form', async () => {
    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <NotificationsProvider>
            <EditMyCompany />
          </NotificationsProvider>
        </QueryClientProvider>
      </BrowserRouter>
    );

    await waitFor(() => expect(screen.getByTestId('edit-company__form-title')).toBeInTheDocument());
  });
});
