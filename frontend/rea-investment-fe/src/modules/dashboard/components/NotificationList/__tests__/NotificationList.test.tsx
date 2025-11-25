import React from 'react';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import NotificationList from '../NotificationList';

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn()
}));

describe('Notification List component', () => {
  const queryClient = new QueryClient();

  test('renders the component', () => {
    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <NotificationList />
        </QueryClientProvider>
      </BrowserRouter>
    );

    expect(screen.getByTestId('notification-list__component')).toBeInTheDocument();
  });
});
