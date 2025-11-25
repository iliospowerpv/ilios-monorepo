import React from 'react';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import PasswordResetRequest from '../PasswordResetRequest';

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn()
}));

jest.mock('../../../contexts/notifications/notifications', () => ({
  useNotify: jest.fn(() => jest.fn())
}));

describe('Request Password Reset page', () => {
  const queryClient = new QueryClient();

  test('renders the form', () => {
    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <PasswordResetRequest />
        </QueryClientProvider>
      </BrowserRouter>
    );

    expect(screen.getByTestId('reset__request-password-reset-title')).toBeInTheDocument();
  });
});
