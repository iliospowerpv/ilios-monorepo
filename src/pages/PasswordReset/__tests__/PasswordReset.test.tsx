import React from 'react';
import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import PasswordReset from '../PasswordReset';

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn()
}));

describe('Password Reset page', () => {
  const queryClient = new QueryClient();

  test('renders the form', () => {
    render(
      <BrowserRouter>
        <QueryClientProvider client={queryClient}>
          <PasswordReset />
        </QueryClientProvider>
      </BrowserRouter>
    );

    expect(screen.getByTestId('reset__password-reset-white-screen')).toBeInTheDocument();
  });
});
