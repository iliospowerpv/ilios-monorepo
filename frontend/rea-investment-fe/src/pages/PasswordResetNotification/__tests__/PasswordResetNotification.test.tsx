import React from 'react';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import PasswordResetNotification from '../PasswordResetNotification';

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn()
}));

jest.mock('../../../contexts/notifications/notifications', () => ({
  useNotify: jest.fn(() => jest.fn())
}));

describe('Password Reset Notification page', () => {
  const queryClient = new QueryClient();

  test('renders the page', () => {
    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <PasswordResetNotification />
        </QueryClientProvider>
      </BrowserRouter>
    );

    expect(screen.getByTestId('reset__password-reset-notification-title')).toBeInTheDocument();
  });
});
