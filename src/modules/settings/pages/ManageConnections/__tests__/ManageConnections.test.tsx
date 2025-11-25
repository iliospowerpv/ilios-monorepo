import React from 'react';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { NotificationsProvider } from '../../../../../contexts/notifications/notifications';
import ManageConnectionsPage from '../ManageConnections';

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn()
}));

describe('Manage Connection page', () => {
  const queryClient = new QueryClient();

  test('renders the form', () => {
    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <NotificationsProvider>
            <ManageConnectionsPage />
          </NotificationsProvider>
        </QueryClientProvider>
      </BrowserRouter>
    );

    expect(screen.getByTestId('manage-connection__form-title')).toBeInTheDocument();
  });
});
